"""
Module Name: ai_manager.py
Purpose: Connects to Google Gemini using the official google-genai SDK,
         with automated fallback for 429 rate limits, 503 network congestion,
         and a 300-second timeout for multimodal image uploads with strict type annotations.
"""

import json
import os
import time
import concurrent.futures
from typing import Any, Optional
from google import genai
from google.genai import types

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
    if not image_path or image_path.strip().lower() in ["none", "", "n/a"]:
        return None, None
        
    if not os.path.exists(image_path):
        return None, None
        
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/jpeg"
    if ext == ".png":
        mime_type = "image/png"
    elif ext == ".webp":
        mime_type = "image/webp"
        
    try:
        with open(image_path, "rb") as image_file:
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