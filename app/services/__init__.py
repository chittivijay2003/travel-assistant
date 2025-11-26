"""Services package for Travel Assistant API.

Contains business logic and external service integrations.
"""

from app.services.gemini_client import get_flash_model
from app.services.travel_service_new import process_travel_request_new

__all__ = [
    "get_flash_model",
    "process_travel_request_new",
]
