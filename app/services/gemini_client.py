"""Gemini AI Client Module.

Initializes and manages Google Gemini Flash model.
Provides access to the model instance for travel assistance.
"""

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from app.config import settings
from functools import lru_cache


# Lazy initialization with caching to avoid slow startup
_flash_model = None


@lru_cache(maxsize=1)
def get_flash_model():
    """Get the Gemini Flash model instance (lazy loaded).

    Returns:
        GenerativeModel: The initialized Flash model for quick responses.
    """
    global _flash_model
    if _flash_model is None:
        genai.configure(api_key=settings.google_api_key)

        # Configure safety settings to reduce blocking
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        _flash_model = genai.GenerativeModel(
            "gemini-2.5-flash",  # Latest stable flash model
            generation_config={
                "temperature": settings.model_temperature,
                "max_output_tokens": settings.max_output_tokens,
            },
            safety_settings=safety_settings,
        )
    return _flash_model
