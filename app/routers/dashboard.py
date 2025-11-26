"""Dashboard router for Travel Assistant.

This module provides endpoints for the analytics dashboard.
Serves dashboard UI and provides real-time metrics data.

Bonus Feature 2: Analytics Dashboard
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.metrics_tracker import metrics_tracker
from app.services.example_cache import example_cache

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the analytics dashboard UI.

    Returns:
        HTML page with metrics visualization
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/metrics")
async def get_metrics():
    """Get comprehensive metrics data for dashboard.

    Returns:
        JSON with all dashboard metrics including:
        - 24h and 1h summaries
        - Hourly breakdown
        - Top users
        - Endpoint statistics
        - Overall totals
    """
    return await metrics_tracker.get_dashboard_data()


@router.get("/api/metrics/summary")
async def get_metrics_summary(hours: int = 24):
    """Get metrics summary for specified time period.

    Args:
        hours: Number of hours to include (default 24)

    Returns:
        JSON with summary statistics
    """
    return await metrics_tracker.get_summary(hours=hours)


@router.get("/api/metrics/user/{user_id}")
async def get_user_metrics(user_id: str):
    """Get metrics for a specific user.

    Args:
        user_id: User ID to get stats for

    Returns:
        JSON with user statistics
    """
    return await metrics_tracker.get_user_stats(user_id=user_id)


@router.get("/api/cache/stats")
async def get_cache_stats():
    """Get example cache statistics.

    Returns:
        JSON with cache usage stats
    """
    return example_cache.get_stats()


@router.get("/api/scenarios/latest")
async def get_latest_scenarios():
    """Get scenario comparison data from the most recent request.

    Returns:
        JSON with scenario comparison metrics
    """
    return await metrics_tracker.get_latest_scenario_data()


@router.post("/api/metrics/reset")
async def reset_metrics():
    """Reset all metrics (admin function).

    Returns:
        Success message
    """
    await metrics_tracker.reset()
    return {"message": "Metrics reset successfully"}


@router.post("/api/cache/clear")
async def clear_cache():
    """Clear example cache (admin function).

    Returns:
        Success message
    """
    example_cache.clear()
    return {"message": "Cache cleared successfully"}
