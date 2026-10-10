"""
Module Name: ai_manager.py
Purpose: Integrates Google Gemini for campus hazard assessment.
         Supports multimodal image input, structured JSON validation,
         HTTP request timeouts, retry handling, model fallback,
         and controlled error handling.
"""

import json
import os
import time
import logging
from typing import Any, Optional
from google import genai
from google.genai import types, errors

# Configure logging for status messages and errors.
# Logging is used instead of print() to keep output consistent and controllable.
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
                - str: The detected MIME type for JPEG, PNG, or WebP,
                    or None if processing failed.
    """
    if image_path is None:
        return None, None
            
    cleaned_path = str(image_path).strip()
    if not cleaned_path or cleaned_path.lower() in ["none", "", "n/a"]:
        return None, None
            
    if not os.path.exists(cleaned_path):
        return None, None
            
    ext = os.path.splitext(cleaned_path)[1].lower()

    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    mime_type = mime_types.get(ext)

    if mime_type is None:
        logger.warning("Unsupported image format: %s", ext)
        return None, None
                
    try:
        with open(cleaned_path, "rb") as image_file:
            return image_file.read(), mime_type
    except (IOError, OSError):
            return None, None

def build_prompt(record: dict[str, Any]) -> str:
    """Constructs a structured prompt for Gemini to analyze a campus safety hazard report.

        Args:
            record (dict[str, Any]): A dictionary containing hazard details, expected to include:
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

    Return exactly these five keys:
    "risk_summary", "category", "severity", "operational_impact", "contextual_insights"

    Required JSON keys:
    - "risk_summary": A concise, bulleted risk summary text.
    - "category": Must be exactly one of: Electrical, Plumbing, Structural, HVAC, IT/Equipment.
    - "severity": Must be exactly one of: Low, Medium, High, Critical.
    - "operational_impact": Must be exactly one of: Minor, Moderate, Severe, Catastrophic.
    - "contextual_insights": Explanations and safety insights.

    Input Data:
    Location: {record.get('location')}
    Impact Headcount: {record.get('impact_headcount')}
    Asset Information: {record.get('asset_info')}
    Description: {record.get('description')}
    """
    return prompt.strip()

def call_api(
    prompt: str,
    visual_evidence_path: Optional[str] = None
) -> str:
    """
    Sends a hazard report to Gemini using the official Google GenAI SDK.

    Supports HTTP timeouts, retry handling, model fallback,
    optional image evidence, and JSON response validation.
    """

    # Step 1: Verify API key
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        logger.error("GEMINI_API_KEY is not configured.")
        return json.dumps({
            "error": "AI processing unavailable"
        })

    # Step 2: Prepare prompt and optional image evidence
    contents: list[Any] = [prompt]

    if (
        visual_evidence_path
        and str(visual_evidence_path).strip().lower()
        not in ("none", "n/a")
    ):
        img_bytes, mime_type = encode_image(visual_evidence_path)

        if not img_bytes or not mime_type:
            logger.warning("Image evidence could not be processed.")
            return json.dumps({
                "error": "Image evidence unavailable"
            })

        contents.append(
            types.Part.from_bytes(
                data=img_bytes,
                mime_type=mime_type
            )
        )

    logger.info("Analyzing hazard report with Gemini AI...")

    # Step 3: Define model fallback order
    target_models = (
        "gemini-3.8-flash",
        "gemini-3.6-flash"
    )

    try:
        # Step 4: Initialize Gemini client with HTTP timeout
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=60_000,
                retry_options=types.HttpRetryOptions(
                    attempts=1
                )
            )
        ) as client:

            for model_name in target_models:

                # Maximum two attempts per model
                for attempt in range(2):

                    try:
                        # Step 5: Request structured JSON response
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                automatic_function_calling=(
                                    types.AutomaticFunctionCallingConfig(
                                        disable=True
                                    )
                                )
                            )
                        )

                        raw_text = response.text or ""

                        # Step 6: Parse and validate response
                        parsed = parse_response(raw_text)

                        if (
                            parsed is not None
                            and validate_response(parsed)
                        ):
                            return raw_text

                        logger.warning(
                            "Invalid JSON/schema from %s "
                            "(attempt %d/2).",
                            model_name,
                            attempt + 1
                        )

                    except errors.APIError as error:
                        error_code = error.code

                        # Rate limit: switch to next model
                        if error_code == 429:
                            logger.warning(
                                "Rate limit on %s. Switching model.",
                                model_name
                            )
                            break

                        # Model unavailable: try backup model
                        if error_code == 404:
                            logger.warning(
                                "Model %s unavailable.",
                                model_name
                            )
                            break

                        # Temporary errors: retry once
                        if error_code in (408, 500, 502, 503, 504):
                            if attempt == 0:
                                logger.warning(
                                    "HTTP %s on %s. Retrying...",
                                    error_code,
                                    model_name
                                )
                                time.sleep(2)
                                continue

                            logger.warning(
                                "Model %s failed after two attempts.",
                                model_name
                            )
                            break

                        # Other API errors: stop
                        logger.error(
                            "Non-retryable Gemini API error: %s",
                            error_code
                        )
                        return json.dumps({
                            "error": "AI processing unavailable"
                        })

                    except Exception as error:
                        logger.warning(
                            "Request failed on %s (%s).",
                            model_name,
                            type(error).__name__
                        )
                        break

    except Exception as error:
        logger.error(
            "Gemini client error (%s).",
            type(error).__name__
        )

    # Step 7: Return controlled error for offline fallback
    return json.dumps({
        "error": "AI processing unavailable"
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
        
        # Remove optional Markdown code-block wrappers before parsing JSON
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        # Parse the cleaned string as JSON
        parsed_data = json.loads(cleaned.strip())
        
        # Ensure the parsed result is a dictionary before returning
        if isinstance(parsed_data, dict):
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

    # Reject categories outside the project's required classification list
    if data["category"] not in [
        "Electrical",
        "Plumbing",
        "Structural",
        "HVAC",
        "IT/Equipment"
    ]:
        return False

   # Reject values outside the project's required severity levels
    if data["severity"] not in [
        "Low",
        "Medium",
        "High",
        "Critical"
    ]:
        return False

    # Reject values outside the project's required operational impact levels
    if data["operational_impact"] not in [
        "Minor",
        "Moderate",
        "Severe",
        "Catastrophic"
    ]:
        return False

    return True