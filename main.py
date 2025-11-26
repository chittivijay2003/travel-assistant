"""Travel Assistant API - Main Application Entry Point.

AI-powered travel assistant using LangChain prompt templates with few-shot learning.

Features:
- 3 specialized LangChain PromptTemplates (flight, hotel, itinerary)
- Smart few-shot example selection from user history
- Token optimization with similarity-based selection
- Comprehensive metrics tracking (tokens, costs, quality)
- Parallel execution with asyncio

Run with: uvicorn main:app --reload

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from app.config import settings
from app.routers import travel_router
from app.routers.dashboard import router as dashboard_router

# Initialize FastAPI application with comprehensive metadata
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    🌍 **AI-Powered Travel Assistant** using Google Gemini Flash via LangChain
    
    ## 🎯 Key Features
    
    ### **Smart Few-Shot Learning**
    - Personalized recommendations based on user travel history
    - Dynamic example selection (HIGH/MEDIUM/LOW similarity)
    - 60-80% token optimization vs naive approach
    
    ### **Specialized LangChain Templates**
    - ✈️ Flight Search & Recommendations
    - 🏨 Hotel Suggestions
    - 📅 Day-by-Day Itinerary Planning
    
    ### **Comprehensive Metrics**
    - Input/Output token tracking per component
    - Cost estimation (Gemini Flash pricing)
    - AI quality measurements (completeness, relevance)
    - Token savings calculation with baseline comparison
    
    ### **Performance Optimized**
    - Parallel execution of all 3 components (asyncio)
    - Smart history caching
    - Automatic trip storage for future learning
    
    ## 📊 Assignment Requirements
    
    ✅ **Task 1:** 3 separate LangChain PromptTemplates (flight, hotel, itinerary)  
    ✅ **Task 2:** Single Gemini Flash model via LangChain  
    ✅ **Task 3:** Dynamic few-shot examples from user history  
    ✅ **Task 4:** Detailed token usage & latency tracking  
    ✅ **Bonus 1:** Smart context optimization (similarity-based selection)  
    ✅ **Bonus 2:** Dashboard with metrics visualization  
    
    ## 🚀 Quick Start
    
    **POST /travel-assistant**
    ```json
    {
      "user_id": "user_001",
      "destination": "Paris, France",
      "travel_dates": "March 15-20, 2025",
      "preferences": "art museums, cafes, romantic walks"
    }
    ```
    
    **View Dashboard:** [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Travel Assistant API",
        "url": "https://github.com/chittivijay2003/travel-assistant",
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
app.include_router(dashboard_router)


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
        "model": settings.gemini_flash_model,
        "features": [
            "LangChain Prompt Templates",
            "Few-Shot Learning",
            "Token Optimization",
            "Quality Metrics",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
