"""Travel Assistant API - Main Application Entry Point.

This module initializes the FastAPI application and registers all routers.

Assignment Implementation Details:
- Uses Google Gemini Flash and Pro models via LangChain
- Implements parallel model execution with asyncio.gather()
- Measures and compares latency between models
- Returns structured responses with comprehensive travel itineraries
- Includes structured JSON logging for monitoring

Run with: uvicorn main:app --reload

Author: Chitti Vijay
Date: November 24, 2025
Course: Python Programming Assignment
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from app.config import settings
from app.routers import travel_router

# Initialize FastAPI application with comprehensive metadata
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI-powered travel assistant using Google Gemini Flash and Pro models via LangChain.
    
    Features:
    - Parallel execution of two Gemini models (Flash for speed, Pro for detail)
    - Latency measurement and comparison
    - Structured itinerary generation with highlights
    - Intelligent model comparison and recommendations
    - Comprehensive logging system
    
    Assignment Compliance:
    ✓ API key configuration via environment variables
    ✓ LangChain integration with ChatGoogleGenerativeAI
    ✓ Dual model initialization (Flash & Pro)
    ✓ Parallel model execution with asyncio
    ✓ Latency measurement for both models
    ✓ Structured response with comparison
    ✓ Bonus: JSON logging system
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Travel Assistant API",
        "url": "https://github.com/yourusername/travel-assistant-api",
    },
    license_info={
        "name": "Educational Use",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(travel_router)


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - Serve HTML interface.

    Returns the HTML travel assistant interface.
    """
    html_path = os.path.join("app", "templates", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {
        "message": "Travel Assistant API",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint.

    Returns API health status and configuration.
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "models": {
            "flash": settings.gemini_flash_model,
            "pro": settings.gemini_pro_model,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
