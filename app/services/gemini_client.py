"""Gemini AI Client Module.

Initializes and manages Google Gemini models via LangChain.
Provides access to both Flash and Pro model instances for travel assistance.

Models:
    - Gemini Flash: Fast, concise responses optimized for speed
    - Gemini Pro: Detailed, comprehensive responses with richer context
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings


# Initialize Gemini Flash model
# Optimized for speed with concise, quick responses
flash_model = ChatGoogleGenerativeAI(
    model=settings.gemini_flash_model,
    google_api_key=settings.google_api_key,
    temperature=settings.model_temperature,  # Configurable from .env
    max_output_tokens=settings.flash_max_tokens,  # Configurable from .env
)

# Initialize Gemini Pro model
# Optimized for detail with comprehensive, context-rich responses
pro_model = ChatGoogleGenerativeAI(
    model=settings.gemini_pro_model,
    google_api_key=settings.google_api_key,
    temperature=settings.model_temperature,  # Configurable from .env
    max_output_tokens=settings.pro_max_tokens,  # Configurable from .env
)


def get_flash_model() -> ChatGoogleGenerativeAI:
    """Get the Gemini Flash model instance.

    Returns:
        ChatGoogleGenerativeAI: The initialized Flash model for quick responses.
    """
    return flash_model


def get_pro_model() -> ChatGoogleGenerativeAI:
    """Get the Gemini Pro model instance.

    Returns:
        ChatGoogleGenerativeAI: The initialized Pro model for detailed responses.
    """
    return pro_model
