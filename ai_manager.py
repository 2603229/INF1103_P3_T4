"""
Module Name: ai_manager.py
Purpose: Connects to Google Gemini using the official google-genai SDK,
         with automated fallback for 429 rate limits, 503 network congestion,
         and a 300-second timeout for multimodal image uploads with strict type annotations.
"""

import json
import os
import time
import logging
import concurrent.futures
from typing import Any, Optional
from google import genai
from google.genai import types

# Configure standard module-level logging for background notices and errors.
# Using logging instead of print() keeps terminal output controlled
# and avoids direct console output from this module.
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def encode_image(image_path: Optional[str]) -> tuple[Optional[bytes], Optional[str]]:
    """
        Safely encodes a local image file into raw bytes and determines its MIME type 
        for multimodal analysis with Google Gemini.

        Args:
            image_path (str, optional): The file path to the local image. 

        Returns:
            tuple: A 2-element tuple containing:
                - bytes: The raw binary data of the image (or None if invalid).
                - str: The detected MIME type ('image/png', 'image/webp', or defaults 
                    to 'image/jpeg'), or None if processing failed.
    """
    if image_path is None:
        return None, None
            
    cleaned_path = str(image_path).strip()
    if not cleaned_path or cleaned_path.lower() in ["none", "", "n/a"]:
        return None, None
            
    if not os.path.exists(cleaned_path):
        return None, None
            
    ext = os.path.splitext(cleaned_path)[1].lower()
    mime_type = "image/jpeg"
    if ext == ".png":
        mime_type = "image/png"
    elif ext == ".webp":
        mime_type = "image/webp"
            
    try:
        with open(cleaned_path, "rb") as image_file:
            return image_file.read(), mime_type
    except (IOError, OSError):
            return None, None

def build_prompt(record: dict[str, Any]) -> str:
    """Constructs a structured prompt for Gemini to analyze a campus safety hazard report.

        Args:
            record (dict[str, Any]): A dictionary containing hazard details, expected to include:
                - 'reporter_name' (str)
                - 'location' (str)
                - 'impact_headcount' (int/str)
                - 'asset_info' (str)
                - 'description' (str)

        Returns:
            str: A formatted prompt instructing the model to evaluate the hazard and return 
            strictly formatted JSON matching the required schema keys ('risk_summary', 
            'category', 'severity', 'operational_impact', 'contextual_insights') without 
            markdown code blocks.
    """
    prompt = f"""
    Analyze the following campus safety hazard report and respond strictly in valid JSON format without markdown code blocks.
    Required JSON keys:
    - "risk_summary": A concise, bulleted risk summary text.
    - "category": The category of the problem (e.g., Electrical, Plumbing, Structural, HVAC, IT/Equipment).
    - "severity": Severity level (Low, Medium, High, Critical).
    - "operational_impact": Assessment of impact (Minor, Moderate, Severe, Catastrophic).
    - "contextual_insights": Explanations and safety insights.

    Input Data:
    Reporter Name: {record.get('reporter_name')}
    Location: {record.get('location')}
    Impact Headcount: {record.get('impact_headcount')}
    Asset Information: {record.get('asset_info')}
    Description: {record.get('description')}
    """
    return prompt.strip()

def call_api(prompt: str, visual_evidence_path: Optional[str] = None) -> str:
    """
    Sends the prompt to Gemini using the official Google GenAI SDK client,
    featuring a multi-model fallback cascade, retry backoffs for 429/503 errors,
    and a 300-second execution timeout.
    """
    # 1. Verify that the Gemini API key is configured in the environment variables
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please check your .env file.")
    
    logger.info("Analyzing hazard report with Gemini AI...")
    
    try:
        # Initialize the official Google GenAI client and setup prompt contents
        client = genai.Client(api_key=api_key)
        contents: list[Any] = [prompt]
        
        # Encode and attach visual evidence (image) as a multimodal part if available
        img_bytes, mime_type = encode_image(visual_evidence_path)
        if img_bytes and mime_type:
            contents.append(
                types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            )

        def _make_api_call() -> Optional[str]:
                # Define the multi-model fallback cascade order
                target_models = ['gemini-3.8-flash', 'gemini-3.6-flash'] 
                
                for model_name in target_models:
                    # Allow up to 2 attempts per model
                    for attempt in range(2):
                        try:
                            # Send content generation request to the current model with enforced JSON MIME type
                            response = client.models.generate_content(
                                model=model_name,
                                contents=contents,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json"
                                )
                            )
                            raw_text = str(response.text)
                            
                            # Parse and validate response structure/schema
                            parsed = parse_response(raw_text)
                            if parsed and validate_response(parsed):
                                return raw_text  # Return valid response text
                            else:
                                logger.warning(f"Invalid JSON or schema from {model_name}. Retrying...")
                                continue
                                
                        except Exception as e:
                            err_str = str(e)
                            
                            # Handle rate limits / quota exhaustion (429) -> immediately switch model
                            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                                logger.warning(f"Quota limit reached on {model_name} (429). Switching model...")
                                break
                                
                            # Handle high-demand errors (503) -> wait 2 seconds and retry on the same model
                            if "503" in err_str and attempt < 1:
                                logger.warning(f"High demand on {model_name} (503). Retrying...")
                                time.sleep(2)
                                continue
                                
                            # If all models in the cascade fail, raise the exception
                            if model_name == target_models[-1]:
                                raise e
                            break
                return None

        # Execute the API call inside a ThreadPoolExecutor to enforce a strict timeout limit
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_make_api_call)
            res = future.result(timeout=300)  # 300-second execution timeout
            if res:
                return res

    except concurrent.futures.TimeoutError:
        logger.warning("API call timed out after 300 seconds.")
        return json.dumps({
            "error": "AI processing timed out"
        })

    except Exception as e:
        logger.error(f"AI API error: {e}")
        return json.dumps({
            "error": "AI processing unavailable"
        })

    return json.dumps({
        "error": "AI processing failed"
    })

def parse_response(raw: Any) -> Optional[dict[str, Any]]:
    """
    Extracts and parses JSON from raw API text strings, 
    safely stripping markdown code wrappers (e.g., ```json ... ```).
    """
    # Return None immediately if the input is empty or None
    if not raw:
        return None
        
    try:
        # Convert input to string and remove leading/trailing whitespace
        cleaned = str(raw).strip()
        
        # Strip standard markdown code block formatting if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        # Parse the cleaned string as JSON
        parsed_data = json.loads(cleaned.strip())
        
        # Ensure the parsed result is a dictionary before returning
        if type(parsed_data) is dict:
            return parsed_data  # type: ignore[reportUnknownVariableType]
            
        return None
        
    except json.JSONDecodeError as e:
        # Catch and report any JSON decoding errors gracefully
        logger.error(f"Failed to parse JSON response: {e}")
        return None

def validate_response(data: dict[str, Any]) -> bool:
    """
    Validates that the AI response contains the required schema,
    uses the correct data types, and contains valid categorical values.
    """
    required_keys = [
        "risk_summary",
        "category",
        "severity",
        "operational_impact",
        "contextual_insights"
    ]

    # Check that all required keys are present
    if not all(key in data for key in required_keys):
        return False

    # Check that all required fields are strings
    for key in required_keys:
        if not isinstance(data[key], str):
            return False

    # Check allowed severity values
    if data["severity"] not in ["Low", "Medium", "High", "Critical"]:
        return False

    # Check allowed operational impact values
    if data["operational_impact"] not in [
        "Minor",
        "Moderate",
        "Severe",
        "Catastrophic"
    ]:
        return False

    return True