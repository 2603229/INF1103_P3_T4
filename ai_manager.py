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