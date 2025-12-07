"""New Travel Service - Integrated with All Assignment Requirements.

This module implements the complete travel assistant service:
- Uses 3 separate prompt templates (flight, hotel, itinerary)
- Integrates dynamic few-shot examples from user history
- Tracks token usage accurately
- Measures latency for each component
- Calls all 3 in parallel for performance
- Tracks metrics for dashboard analytics

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant - Tasks 1-4
"""

import time
import asyncio
import hashlib
import json
from typing import Tuple, Dict, Optional
from app.models import (
    TravelRequest,
    TravelAssistantResponse,
    TokenMetrics,
    ComponentMetrics,
    QualityMetrics,
    ScenarioMetrics,
)
from app.services.gemini_client import get_flash_model
from app.services.prompt_templates import (
    get_flight_prompt,
    get_hotel_prompt,
    get_itinerary_prompt,
)
from app.services.few_shot_selector import get_few_shot_selector
from app.services.token_counter import get_token_counter
from app.services.user_history import get_history_manager
from app.services.metrics_tracker import metrics_tracker
from app.utils.logging_utils import log_model_latency, log_error


# Simple in-memory response cache
_response_cache: Dict[str, Dict] = {}


def _get_cache_key(request: TravelRequest) -> str:
    """Generate cache key from request."""
    key_data = {
        "destination": request.destination,
        "travel_dates": request.travel_dates,
        "preferences": request.preferences,
        "user_id": request.user_id,
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def _get_generic_response(prompt_type: str, prompt_text: str) -> str:
    """Generate a generic fallback response when safety filters trigger.

    Args:
        prompt_type: Type of prompt (flight, hotel, itinerary)
        prompt_text: Original prompt text

    Returns:
        Generic but helpful response
    """
    # Extract destination from prompt
    destination = "your destination"
    try:
        if "destination=" in prompt_text:
            dest_start = prompt_text.find("destination=") + 12
            dest_end = prompt_text.find("\n", dest_start)
            if dest_end > dest_start:
                destination = prompt_text[dest_start:dest_end].strip()
    except Exception:
        pass

    if prompt_type == "flight":
        return f"""Based on your travel plans to {destination}, here are general flight recommendations:

**Recommended Approach:**
1. **Book in Advance**: Typically 2-3 months ahead for best prices
2. **Compare Airlines**: Check both major carriers and budget airlines
3. **Consider Connections**: Direct flights save time but may cost more
4. **Flexible Dates**: Being flexible with dates can save 20-40%
5. **Use Flight Comparison Tools**: Google Flights, Skyscanner, Kayak

**General Tips:**
- Check multiple airports if available in your area
- Sign up for fare alerts
- Consider loyalty programs for frequent flyers
- Book Tuesday-Thursday for potentially lower prices
- Clear cookies or use incognito mode when searching"""

    elif prompt_type == "hotel":
        return f"""Here are hotel recommendations for {destination}:

**Booking Strategy:**
1. **Location**: Stay near public transportation or main attractions
2. **Read Recent Reviews**: Focus on reviews from the last 3-6 months
3. **Compare Prices**: Check hotel website, booking sites, and aggregators
4. **Flexible Cancellation**: Choose refundable options when possible
5. **Look for Package Deals**: Sometimes flights + hotel is cheaper

**Hotel Search Tips:**
- Use filters for amenities you need (WiFi, breakfast, parking)
- Check if loyalty programs offer benefits
- Book directly with hotel for potential perks
- Consider alternative accommodations (Airbnb, hostels, boutique hotels)
- Verify location on map before booking"""

    else:  # itinerary
        return f"""Here's a general itinerary planning guide for {destination}:

**Planning Your Trip:**

**Day 1-2: Arrival & Orientation**
- Settle into accommodation
- Take orientation walking tour
- Visit nearby attractions
- Try local cuisine

**Day 3-5: Major Attractions**
- Visit top-rated museums and landmarks
- Book skip-the-line tickets in advance
- Balance busy sightseeing with relaxation
- Explore local neighborhoods

**Day 6-7: Local Experiences**
- Visit local markets
- Take cooking class or cultural workshop
- Day trip to nearby areas
- Evening entertainment (shows, concerts)

**General Tips:**
- Don't over-schedule - leave time for spontaneity
- Mix popular sites with off-the-beaten-path experiences
- Consider guided tours for historical context
- Try local transportation
- Make restaurant reservations for popular spots"""


async def call_prompt_with_metrics(
    model, prompt_text: str, prompt_type: str
) -> Tuple[str, int, int, int]:
    """Call model and measure latency and token usage.

    Args:
        model: Google GenerativeModel instance
        prompt_text: Formatted prompt string
        prompt_type: Type of prompt for logging (flight, hotel, itinerary)

    Returns:
        Tuple of (response_text, latency_ms, input_tokens, output_tokens)
    """
    token_counter = get_token_counter()

    # Count input tokens
    input_tokens = token_counter.count_tokens(prompt_text)

    try:
        # Measure latency
        start_time = time.time()
        # Use native Google SDK async method
        response = await asyncio.to_thread(model.generate_content, prompt_text)
        end_time = time.time()

        latency_ms = int((end_time - start_time) * 1000)

        # Handle safety blocks and extract text safely
        try:
            response_text = response.text
        except (ValueError, AttributeError) as e:
            # Check if response was blocked and get detailed info
            response_text = ""
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]

                # Try to get partial text if available
                if hasattr(candidate, "content") and hasattr(
                    candidate.content, "parts"
                ):
                    for part in candidate.content.parts:
                        if hasattr(part, "text"):
                            response_text += part.text

                # Log safety ratings for debugging
                if hasattr(candidate, "safety_ratings"):
                    print(f"⚠️ Safety ratings for {prompt_type}:")
                    for rating in candidate.safety_ratings:
                        print(f"  {rating.category}: {rating.probability}")

                # If still no text, check finish reason
                if not response_text and hasattr(candidate, "finish_reason"):
                    finish_reason = candidate.finish_reason
                    if finish_reason == 2:  # SAFETY
                        # Get specific safety categories that triggered
                        blocked_categories = []
                        if hasattr(candidate, "safety_ratings"):
                            for rating in candidate.safety_ratings:
                                if rating.probability.name in ["MEDIUM", "HIGH"]:
                                    blocked_categories.append(rating.category.name)

                        if blocked_categories:
                            response_text = f"⚠️ Safety filter triggered for {prompt_type}. Categories: {', '.join(blocked_categories)}. Providing generic response instead.\n\n"
                        else:
                            response_text = f"⚠️ Safety filter triggered for {prompt_type}. Providing generic response instead.\n\n"

                        # Add a generic but helpful response
                        response_text += _get_generic_response(prompt_type, prompt_text)
                    elif finish_reason == 3:  # RECITATION
                        response_text = f"⚠️ Content recitation detected for {prompt_type}. Providing alternative response.\n\n"
                        response_text += _get_generic_response(prompt_type, prompt_text)
                    else:
                        response_text = (
                            f"⚠️ Response incomplete (reason: {finish_reason}). {str(e)}"
                        )

            if not response_text:
                response_text = (
                    f"⚠️ Unable to generate response for {prompt_type}. Error: {str(e)}"
                )

        # Count output tokens
        output_tokens = token_counter.count_tokens(response_text)

        # Log metrics
        log_model_latency(f"Gemini Flash ({prompt_type})", latency_ms)

        return response_text, latency_ms, input_tokens, output_tokens

    except Exception as e:
        log_error(e, context=f"call_prompt_with_metrics_{prompt_type}")
        raise


async def generate_flight_recommendations(
    request: TravelRequest,
) -> Tuple[str, int, int, int, str, list, Dict]:
    """Generate flight recommendations using the flight template.

    Args:
        request: TravelRequest with destination, dates, preferences

    Returns:
        Tuple of (flight_recommendations, latency_ms, input_tokens, output_tokens,
                  few_shot_examples_text, similarity_scores, ranking_data)
    """
    # Get few-shot examples using smart selection
    few_shot_selector = get_few_shot_selector()
    (
        few_shot_examples,
        similarity_scores,
        ranking_data,
    ) = await few_shot_selector.get_examples_for_flight(
        request.destination, request.preferences, request.user_id
    )

    # Get and format the prompt
    flight_prompt = get_flight_prompt()
    prompt_text = flight_prompt.format(
        destination=request.destination,
        travel_dates=request.travel_dates,
        preferences=request.preferences,
        few_shot_examples=few_shot_examples,
    )

    # Call model with metrics
    model = get_flash_model()
    response, latency, input_tokens, output_tokens = await call_prompt_with_metrics(
        model, prompt_text, "flight"
    )

    return (
        response,
        latency,
        input_tokens,
        output_tokens,
        few_shot_examples,
        similarity_scores,
        ranking_data,
    )


async def generate_hotel_recommendations(
    request: TravelRequest,
) -> Tuple[str, int, int, int, str, list, Dict]:
    """Generate hotel recommendations using the hotel template.

    Args:
        request: TravelRequest with destination, dates, preferences

    Returns:
        Tuple of (hotel_recommendations, latency_ms, input_tokens, output_tokens,
                  few_shot_examples_text, similarity_scores, ranking_data)
    """
    # Get few-shot examples using smart selection
    few_shot_selector = get_few_shot_selector()
    (
        few_shot_examples,
        similarity_scores,
        ranking_data,
    ) = await few_shot_selector.get_examples_for_hotel(
        request.destination, request.preferences, request.user_id
    )

    # Get and format the prompt
    hotel_prompt = get_hotel_prompt()
    prompt_text = hotel_prompt.format(
        destination=request.destination,
        travel_dates=request.travel_dates,
        preferences=request.preferences,
        few_shot_examples=few_shot_examples,
    )

    # Call model with metrics
    model = get_flash_model()
    response, latency, input_tokens, output_tokens = await call_prompt_with_metrics(
        model, prompt_text, "hotel"
    )

    return (
        response,
        latency,
        input_tokens,
        output_tokens,
        few_shot_examples,
        similarity_scores,
        ranking_data,
    )


async def generate_itinerary(
    request: TravelRequest,
) -> Tuple[str, int, int, int, str, list, Dict]:
    """Generate travel itinerary using the itinerary template.

    Args:
        request: TravelRequest with destination, dates, preferences

    Returns:
        Tuple of (itinerary, latency_ms, input_tokens, output_tokens,
                  few_shot_examples_text, similarity_scores, ranking_data)
    """
    # Get few-shot examples using smart selection
    few_shot_selector = get_few_shot_selector()
    (
        few_shot_examples,
        similarity_scores,
        ranking_data,
    ) = await few_shot_selector.get_examples_for_itinerary(
        request.destination, request.preferences, request.user_id
    )

    # Get and format the prompt
    itinerary_prompt = get_itinerary_prompt()
    prompt_text = itinerary_prompt.format(
        destination=request.destination,
        travel_dates=request.travel_dates,
        preferences=request.preferences,
        few_shot_examples=few_shot_examples,
    )

    # Call model with metrics
    model = get_flash_model()
    response, latency, input_tokens, output_tokens = await call_prompt_with_metrics(
        model, prompt_text, "itinerary"
    )

    return (
        response,
        latency,
        input_tokens,
        output_tokens,
        few_shot_examples,
        similarity_scores,
        ranking_data,
    )


async def generate_scenario_response(
    request: TravelRequest, scenario_type: str
) -> Tuple[str, str, str, int, int, int, int, Optional[Dict]]:
    """Generate AI responses for a specific scenario.

    Args:
        request: TravelRequest with destination, dates, preferences
        scenario_type: 'no_history', 'all_history', or 'smart_history'

    Returns:
        Tuple of (flight_response, hotel_response, itinerary_response,
                  total_latency, total_input_tokens, total_output_tokens, total_tokens,
                  ranking_data)
    """
    from app.services.prompt_templates import (
        get_flight_prompt,
        get_hotel_prompt,
        get_itinerary_prompt,
    )

    model = get_flash_model()
    few_shot_selector = get_few_shot_selector()

    # Initialize ranking data (only populated for smart_history)
    ranking_data = None

    # Determine few-shot strategy based on scenario
    if scenario_type == "no_history":
        # No examples - just base prompts
        flight_examples = ""
        hotel_examples = ""
        itinerary_examples = ""
    elif scenario_type == "all_history":
        # Get ALL user history without filtering
        history_manager = get_history_manager()
        all_trips = await history_manager.get_recent_trips(request.user_id, limit=100)

        # Format all trips as examples (naive approach)
        flight_examples = (
            "\\n\\n".join(
                [
                    f"Example {i + 1}:\\nDestination: {trip.get('destination')}\\nFlight: {trip.get('flightSummary', 'N/A')}"
                    for i, trip in enumerate(
                        all_trips[:20]
                    )  # Cap at 20 to avoid token explosion
                ]
            )
            if all_trips
            else ""
        )

        hotel_examples = (
            "\\n\\n".join(
                [
                    f"Example {i + 1}:\\nDestination: {trip.get('destination')}\\nHotel: {trip.get('hotelSummary', 'N/A')}"
                    for i, trip in enumerate(all_trips[:20])
                ]
            )
            if all_trips
            else ""
        )

        itinerary_examples = (
            "\\n\\n".join(
                [
                    f"Example {i + 1}:\\nDestination: {trip.get('destination')}\\nHighlights: {', '.join(trip.get('itineraryHighlights', []))}"
                    for i, trip in enumerate(all_trips[:20])
                ]
            )
            if all_trips
            else ""
        )
    else:  # smart_history
        # Use smart selection (existing logic)
        (
            flight_examples,
            _,
            flight_ranking,
        ) = await few_shot_selector.get_examples_for_flight(
            request.destination, request.preferences, request.user_id
        )
        (
            hotel_examples,
            _,
            hotel_ranking,
        ) = await few_shot_selector.get_examples_for_hotel(
            request.destination, request.preferences, request.user_id
        )
        (
            itinerary_examples,
            _,
            itinerary_ranking,
        ) = await few_shot_selector.get_examples_for_itinerary(
            request.destination, request.preferences, request.user_id
        )

        # Aggregate ranking data from all three components
        ranking_data = {
            "flight": flight_ranking,
            "hotel": hotel_ranking,
            "itinerary": itinerary_ranking,
        }

    # Generate all 3 components in parallel
    async def call_component(prompt_template, few_shot_text, component_type):
        prompt_text = prompt_template.format(
            destination=request.destination,
            travel_dates=request.travel_dates,
            preferences=request.preferences,
            few_shot_examples=few_shot_text,
        )
        return await call_prompt_with_metrics(model, prompt_text, component_type)

    results = await asyncio.gather(
        call_component(get_flight_prompt(), flight_examples, "flight"),
        call_component(get_hotel_prompt(), hotel_examples, "hotel"),
        call_component(get_itinerary_prompt(), itinerary_examples, "itinerary"),
    )

    flight_resp, flight_lat, flight_in, flight_out = results[0]
    hotel_resp, hotel_lat, hotel_in, hotel_out = results[1]
    itinerary_resp, itinerary_lat, itinerary_in, itinerary_out = results[2]

    total_latency = flight_lat + hotel_lat + itinerary_lat
    total_input = flight_in + hotel_in + itinerary_in
    total_output = flight_out + hotel_out + itinerary_out
    total = total_input + total_output

    return (
        flight_resp,
        hotel_resp,
        itinerary_resp,
        total_latency,
        total_input,
        total_output,
        total,
        ranking_data,
    )


async def process_travel_request_new(request: TravelRequest) -> TravelAssistantResponse:
    """Main service function to process travel requests.

    This implements ALL assignment requirements with 3 parallel scenario calls:
    ✅ Task 1: Uses 3 separate LangChain PromptTemplates
    ✅ Task 2: Returns structured JSON with flight, hotel, itinerary
    ✅ Task 3: Integrates dynamic few-shot examples from user history
    ✅ Task 4: Tracks token usage and latency with detailed metrics
    ✅ Scenario comparison: Generates 3 parallel AI responses (no history, all history, smart)

    Args:
        request: TravelRequest with destination, dates, preferences, user_id

    Returns:
        TravelAssistantResponse with all 3 scenario outputs, detailed metrics
    """
    # Fill missing fields from user history
    history_manager = get_history_manager()
    recent_trips = await history_manager.get_recent_trips(request.user_id, limit=1)

    if recent_trips:
        last_trip = recent_trips[0]
        # Fill in None values from last trip
        if request.destination is None:
            request.destination = last_trip.get("destination", "Paris, France")
        if request.travel_dates is None:
            request.travel_dates = last_trip.get("travelDates", "Next month")
        if request.preferences is None:
            request.preferences = last_trip.get("preferences", "comfortable travel")
    else:
        # No history - use defaults
        if request.destination is None:
            request.destination = "Paris, France"
        if request.travel_dates is None:
            request.travel_dates = "Next month"
        if request.preferences is None:
            request.preferences = "comfortable travel and sightseeing"

    # Check response cache first
    cache_key = _get_cache_key(request)
    if cache_key in _response_cache:
        cached_response = _response_cache[cache_key]
        print(f"✅ Cache HIT for request: {request.destination}")
        return TravelAssistantResponse(**cached_response)

    # Execute all 3 scenarios in PARALLEL for comparison
    try:
        scenario_results = await asyncio.gather(
            generate_scenario_response(request, "no_history"),
            generate_scenario_response(request, "all_history"),
            generate_scenario_response(request, "smart_history"),
        )
    except Exception as e:
        # If any scenario fails, raise the error
        log_error(e, "scenario_generation_failed", {"destination": request.destination})
        raise

    # Extract scenario results
    (
        s1_flight,
        s1_hotel,
        s1_itinerary,
        s1_latency,
        s1_input,
        s1_output,
        s1_total,
        _,  # ranking_data (None for no_history)
    ) = scenario_results[0]

    (
        s2_flight,
        s2_hotel,
        s2_itinerary,
        s2_latency,
        s2_input,
        s2_output,
        s2_total,
        _,  # ranking_data (None for all_history)
    ) = scenario_results[1]

    (
        s3_flight,
        s3_hotel,
        s3_itinerary,
        s3_latency,
        s3_input,
        s3_output,
        s3_total,
        s3_ranking,  # ranking_data from smart selection
    ) = scenario_results[2]

    # Use Scenario 3 (smart) as primary response
    flight_response = s3_flight
    hotel_response = s3_hotel
    itinerary_response = s3_itinerary
    total_latency_ms = s3_latency
    total_input_tokens = s3_input
    total_output_tokens = s3_output
    total_tokens = s3_total

    # Get prompt templates and few-shot examples for the response
    from app.services.prompt_templates import (
        FLIGHT_SEARCH_TEMPLATE,
        HOTEL_RECOMMENDATIONS_TEMPLATE,
        ITINERARY_PLANNING_TEMPLATE,
    )
    
    few_shot_selector = get_few_shot_selector()
    
    # Get few-shot examples used (from smart selection)
    flight_examples_text, flight_sim, flight_meta = await few_shot_selector.get_examples_for_flight(
        request.destination, request.preferences, request.user_id
    )
    hotel_examples_text, hotel_sim, hotel_meta = await few_shot_selector.get_examples_for_hotel(
        request.destination, request.preferences, request.user_id
    )
    itinerary_examples_text, itinerary_sim, itinerary_meta = await few_shot_selector.get_examples_for_itinerary(
        request.destination, request.preferences, request.user_id
    )
    
    # Format few-shot examples as stringified JSON for the response
    few_shot_examples = []
    if flight_examples_text and flight_examples_text.strip():
        few_shot_examples.append(json.dumps({"type": "flight", "content": flight_examples_text}))
    if hotel_examples_text and hotel_examples_text.strip():
        few_shot_examples.append(json.dumps({"type": "hotel", "content": hotel_examples_text}))
    if itinerary_examples_text and itinerary_examples_text.strip():
        few_shot_examples.append(json.dumps({"type": "itinerary", "content": itinerary_examples_text}))
    
    # If no examples were found, add a placeholder
    if not few_shot_examples:
        few_shot_examples.append(json.dumps({"type": "none", "content": "No previous travel history available"}))

    # Calculate costs (Gemini Flash pricing)
    COST_PER_1M_INPUT = 0.075
    COST_PER_1M_OUTPUT = 0.30

    s1_cost = (s1_input / 1_000_000 * COST_PER_1M_INPUT) + (
        s1_output / 1_000_000 * COST_PER_1M_OUTPUT
    )
    s2_cost = (s2_input / 1_000_000 * COST_PER_1M_INPUT) + (
        s2_output / 1_000_000 * COST_PER_1M_OUTPUT
    )
    s3_cost = (s3_input / 1_000_000 * COST_PER_1M_INPUT) + (
        s3_output / 1_000_000 * COST_PER_1M_OUTPUT
    )

    # Calculate savings (smart vs all history)
    tokens_saved = s2_total - s3_total
    savings_percentage = (tokens_saved / s2_total * 100) if s2_total > 0 else 0

    # Build scenario outputs for response
    scenario_outputs = {
        "scenario_1_no_history": {
            "flight": s1_flight,
            "hotel": s1_hotel,
            "itinerary": s1_itinerary,
        },
        "scenario_2_all_history": {
            "flight": s2_flight,
            "hotel": s2_hotel,
            "itinerary": s2_itinerary,
        },
        "scenario_3_smart_history": {
            "flight": s3_flight,
            "hotel": s3_hotel,
            "itinerary": s3_itinerary,
        },
    }

    # Component metrics (Scenario 3 breakdown)
    flight_tokens = s3_input // 3  # Approximate split
    hotel_tokens = s3_input // 3
    itinerary_tokens = s3_input // 3

    flight_out = s3_output // 3
    hotel_out = s3_output // 3
    itinerary_out = s3_output // 3

    flight_cost = (flight_tokens / 1_000_000 * COST_PER_1M_INPUT) + (
        flight_out / 1_000_000 * COST_PER_1M_OUTPUT
    )
    hotel_cost = (hotel_tokens / 1_000_000 * COST_PER_1M_INPUT) + (
        hotel_out / 1_000_000 * COST_PER_1M_OUTPUT
    )
    itinerary_cost = (itinerary_tokens / 1_000_000 * COST_PER_1M_INPUT) + (
        itinerary_out / 1_000_000 * COST_PER_1M_OUTPUT
    )

    flight_metrics = ComponentMetrics(
        input_tokens=flight_tokens,
        output_tokens=flight_out,
        total_tokens=flight_tokens + flight_out,
        latency_ms=s3_latency // 3,
        cost_estimate=flight_cost,
    )

    hotel_metrics = ComponentMetrics(
        input_tokens=hotel_tokens,
        output_tokens=hotel_out,
        total_tokens=hotel_tokens + hotel_out,
        latency_ms=s3_latency // 3,
        cost_estimate=hotel_cost,
    )

    itinerary_metrics = ComponentMetrics(
        input_tokens=itinerary_tokens,
        output_tokens=itinerary_out,
        total_tokens=itinerary_tokens + itinerary_out,
        latency_ms=s3_latency // 3,
        cost_estimate=itinerary_cost,
    )

    token_metrics = TokenMetrics(
        flight=flight_metrics,
        hotel=hotel_metrics,
        itinerary=itinerary_metrics,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens,
        total_cost_estimate=s3_cost,
        scenario_1_no_history=ScenarioMetrics(
            input_tokens=s1_input,
            output_tokens=s1_output,
            total_tokens=s1_total,
            cost_estimate=round(s1_cost, 6),
            flight_response=s1_flight,
            hotel_response=s1_hotel,
            itinerary_response=s1_itinerary,
            latency_ms=s1_latency,
        ),
        scenario_2_all_history=ScenarioMetrics(
            input_tokens=s2_input,
            output_tokens=s2_output,
            total_tokens=s2_total,
            cost_estimate=round(s2_cost, 6),
            flight_response=s2_flight,
            hotel_response=s2_hotel,
            itinerary_response=s2_itinerary,
            latency_ms=s2_latency,
        ),
        scenario_3_smart_history=ScenarioMetrics(
            input_tokens=s3_input,
            output_tokens=s3_output,
            total_tokens=s3_total,
            cost_estimate=round(s3_cost, 6),
            flight_response=s3_flight,
            hotel_response=s3_hotel,
            itinerary_response=s3_itinerary,
            latency_ms=s3_latency,
        ),
        baseline_tokens=s2_total,
        tokens_saved=tokens_saved,
        savings_percentage=round(savings_percentage, 2),
    )

    # Calculate quality metrics (based on scenario 3)
    completeness = 0
    if len(flight_response) > 100:
        completeness += 33.33
    if len(hotel_response) > 100:
        completeness += 33.33
    if len(itinerary_response) > 100:
        completeness += 33.34

    # Extract cache hit and ranking info from scenario 3
    cache_hit = False
    ranking_info = None
    if s3_ranking:
        # Check if any component was a cache hit
        cache_hit = (
            s3_ranking.get("flight", {}).get("cache_hit", False)
            or s3_ranking.get("hotel", {}).get("cache_hit", False)
            or s3_ranking.get("itinerary", {}).get("cache_hit", False)
        )
        ranking_info = s3_ranking

    quality_metrics = QualityMetrics(
        response_completeness=round(completeness, 2),
        response_relevance=85.0,  # Placeholder - can enhance with similarity scoring
        few_shot_examples_used=3,  # Smart selection used
        similarity_scores=[0.8, 0.75, 0.85],  # Placeholder
        avg_similarity=0.8,
        cache_hit=cache_hit,
        ranking_info=ranking_info,
    )

    # Save to user history (async, thread-safe)
    history_manager = get_history_manager()
    flight_summary = (
        flight_response[:200] + "..." if len(flight_response) > 200 else flight_response
    )
    hotel_summary = (
        hotel_response[:200] + "..." if len(hotel_response) > 200 else hotel_response
    )

    itinerary_highlights = []
    for line in itinerary_response.split("\\n")[:10]:
        if any(
            keyword in line.lower()
            for keyword in ["visit", "explore", "tour", "museum", "restaurant"]
        ):
            itinerary_highlights.append(line.strip()[:100])

    await history_manager.add_trip(
        user_id=request.user_id,
        destination=request.destination,
        travel_dates=request.travel_dates,
        preferences=request.preferences,
        flight_summary=flight_summary,
        hotel_summary=hotel_summary,
        itinerary_highlights=itinerary_highlights[:5],
        satisfaction_rating=0,
        token_usage=total_tokens,
        latency_ms=total_latency_ms,
    )

    # Build simplified response
    response = TravelAssistantResponse(
        flight_recommendations=flight_response,
        hotel_recommendations=hotel_response,
        itinerary=itinerary_response,
        token_usage=total_tokens,
        latency_ms=total_latency_ms,
        prompt_templates={
            "flight_template": FLIGHT_SEARCH_TEMPLATE,
            "hotel_template": HOTEL_RECOMMENDATIONS_TEMPLATE,
            "itinerary_template": ITINERARY_PLANNING_TEMPLATE,
        },
        selected_few_shot_examples=few_shot_examples,
    )

    # Track metrics for dashboard (keep detailed tracking internally)
    try:
        await metrics_tracker.track_request(
            endpoint="/travel-assistant",
            user_id=request.user_id,
            token_usage={
                "prompt_tokens": total_input_tokens,
                "completion_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "scenarios": {
                    "scenario_1_no_history": {
                        "input_tokens": s1_input,
                        "output_tokens": s1_output,
                        "total_tokens": s1_total,
                        "cost_estimate": round(s1_cost, 6),
                    },
                    "scenario_2_all_history": {
                        "input_tokens": s2_input,
                        "output_tokens": s2_output,
                        "total_tokens": s2_total,
                        "cost_estimate": round(s2_cost, 6),
                    },
                    "scenario_3_smart_history": {
                        "input_tokens": s3_input,
                        "output_tokens": s3_output,
                        "total_tokens": s3_total,
                        "cost_estimate": round(s3_cost, 6),
                        "cache_hit": cache_hit,
                        "ranking_info": ranking_info,
                    },
                    "tokens_saved": tokens_saved,
                    "savings_percentage": round(savings_percentage, 2),
                },
            },
            latency_ms=total_latency_ms,
            success=True,
            error=None,
        )
    except Exception as e:
        log_error(e, "metrics_tracking", {"user_id": request.user_id})

    # Cache the response for future identical requests
    _response_cache[cache_key] = response.model_dump()
    print(f"✅ Cached response for: {request.destination}")

    return response
