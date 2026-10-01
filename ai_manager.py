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