"""Travel Assistant API router.

This module defines the main /travel-assistant endpoint that processes
travel requests using both Gemini Flash and Pro models.
"""

import time
from fastapi import APIRouter, HTTPException
from app.models import TravelRequest, TravelAssistantResponse
from app.services.travel_service import process_travel_request
from app.utils.logging_utils import (
    log_request,
    log_response,
    log_error,
    log_info,
)

router = APIRouter(prefix="/api", tags=["travel"])


@router.post("/travel-assistant", response_model=TravelAssistantResponse)
async def travel_assistant(request: TravelRequest):
    """Generate travel itinerary using Gemini Flash and Pro models.

    This endpoint:
    1. Accepts a travel request with destination, dates, and preferences
    2. Calls both Gemini Flash and Pro models in parallel
    3. Measures latency for each model
    4. Compares the responses
    5. Returns both responses with comparison metrics

    Args:
        request: TravelRequest containing destination, travel_dates, and preferences

    Returns:
        TravelAssistantResponse with flash_response, pro_response, and comparison

    Raises:
        HTTPException: If there's an error calling the models
    """
    start_time = time.time()

    # Log incoming request
    request_id = log_request(
        endpoint="/api/travel-assistant",
        method="POST",
        request_data=request.model_dump(mode="json"),
    )

    try:
        # Process the travel request using the service layer
        response = await process_travel_request(request)

        # Calculate total latency
        total_latency_ms = int((time.time() - start_time) * 1000)

        # Log detailed latency metrics
        log_info(
            "Latency Metrics Summary",
            request_id=request_id,
            total_latency_ms=total_latency_ms,
            flash_latency_ms=response.flash.latency_ms,
            pro_latency_ms=response.pro.latency_ms,
            latency_difference_ms=abs(
                response.flash.latency_ms - response.pro.latency_ms
            ),
            faster_model="Flash"
            if response.flash.latency_ms < response.pro.latency_ms
            else "Pro",
            destination=request.destination,
        )

        # Log successful response
        response_json = response.model_dump_json()
        log_response(
            endpoint="/api/travel-assistant",
            status_code=200,
            latency_ms=total_latency_ms,
            response_size=len(response_json),
            request_id=request_id,
        )

        return response

    except Exception as e:
        # Log error
        log_error(
            error=e,
            context="travel_assistant_endpoint",
            additional_data={"destination": request.destination},
            request_id=request_id,
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing travel request: {str(e)}"
        )
