"""Travel Assistant API router.

This module defines the main /travel-assistant endpoint that processes
travel requests using both Gemini Flash and Pro models.
"""

import time
from fastapi import APIRouter, HTTPException
from app.models import TravelRequest, TravelAssistantResponse
from app.services.travel_service_new import process_travel_request_new
from app.utils.logging_utils import (
    log_request,
    log_response,
    log_error,
    log_info,
)

router = APIRouter(tags=["travel"])


@router.post("/travel-assistant", response_model=TravelAssistantResponse)
async def travel_assistant(request: TravelRequest):
    """Generate travel recommendations using LangChain and Gemini Flash.

    This endpoint:
    1. Accepts a travel request with destination, dates, preferences, and user_id
    2. Retrieves user history and selects relevant few-shot examples
    3. Calls flight, hotel, and itinerary templates in parallel
    4. Tracks token usage and latency for each component
    5. Saves trip to user history for future few-shot learning

    Args:
        request: TravelRequest containing destination, travel_dates, preferences, user_id

    Returns:
        TravelAssistantResponse with flight_recommendations, hotel_recommendations,
        itinerary, token_usage, and latency_ms

    Raises:
        HTTPException: If there's an error processing the request
    """
    start_time = time.time()

    # Log incoming request
    request_id = log_request(
        endpoint="/travel-assistant",
        method="POST",
        request_data=request.model_dump(mode="json"),
    )

    try:
        # Process the travel request using the new service layer
        response = await process_travel_request_new(request)

        # Calculate total latency
        total_latency_ms = int((time.time() - start_time) * 1000)

        # Log detailed metrics
        log_info(
            "Travel Assistant Metrics",
            request_id=request_id,
            total_latency_ms=total_latency_ms,
            service_latency_ms=response.total_latency_ms,
            total_tokens=response.token_metrics.total_tokens,
            user_id=request.user_id,
            destination=request.destination,
        )

        # Log successful response
        response_json = response.model_dump_json()
        log_response(
            endpoint="/travel-assistant",
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
            additional_data={
                "destination": request.destination,
                "user_id": request.user_id,
            },
            request_id=request_id,
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing travel request: {str(e)}"
        )
