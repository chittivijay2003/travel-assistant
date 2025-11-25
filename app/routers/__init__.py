"""Routers package for Travel Assistant API.

Contains all API endpoint routers.
"""

from app.routers.travel import router as travel_router

__all__ = ["travel_router"]
