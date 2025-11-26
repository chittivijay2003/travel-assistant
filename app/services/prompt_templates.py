"""LangChain Prompt Templates for Travel Assistant.

This module defines three separate prompt templates for:
1. Flight Search
2. Hotel Recommendations
3. Itinerary Planning

Each template supports dynamic few-shot examples based on user history.

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant - Task 1
"""

from langchain_core.prompts import PromptTemplate


# ============================================================================
# FLIGHT SEARCH TEMPLATE
# ============================================================================

FLIGHT_SEARCH_TEMPLATE = """You are an expert flight booking specialist with deep knowledge of airlines, routes, and pricing strategies.

{few_shot_examples}

USER REQUEST:
Destination: {destination}
Travel Dates: {travel_dates}
Preferences: {preferences}

TASK: Provide comprehensive flight recommendations including:
- Recommended airlines and specific flight options
- Direct vs connecting flight comparisons
- Class options (economy, premium economy, business) with pricing estimates
- Best departure/arrival times considering user preferences
- Booking strategies and tips (best time to book, flexible dates savings)
- Baggage policies and additional fees to consider

Provide actionable flight recommendations:"""

flight_search_prompt = PromptTemplate(
    input_variables=["destination", "travel_dates", "preferences", "few_shot_examples"],
    template=FLIGHT_SEARCH_TEMPLATE,
)


# ============================================================================
# HOTEL RECOMMENDATIONS TEMPLATE
# ============================================================================

HOTEL_RECOMMENDATIONS_TEMPLATE = """You are an expert hotel booking specialist with extensive knowledge of accommodations worldwide.

{few_shot_examples}

USER REQUEST:
Destination: {destination}
Travel Dates: {travel_dates}
Preferences: {preferences}

TASK: Provide detailed hotel recommendations including:
- 3-5 specific hotel names with exact locations/neighborhoods
- Hotel categories (budget, mid-range, luxury, boutique) based on preferences
- Key amenities (breakfast, WiFi, pool, gym, spa, etc.)
- Neighborhood descriptions and proximity to attractions
- Estimated pricing per night in local currency and USD
- Booking tips and best platforms to use
- Alternative accommodation options (Airbnb, hostels, etc.) if relevant

Provide specific hotel recommendations:"""

hotel_recommendations_prompt = PromptTemplate(
    input_variables=["destination", "travel_dates", "preferences", "few_shot_examples"],
    template=HOTEL_RECOMMENDATIONS_TEMPLATE,
)


# ============================================================================
# ITINERARY PLANNING TEMPLATE
# ============================================================================

ITINERARY_PLANNING_TEMPLATE = """You are an expert travel planner specializing in creating detailed, personalized day-by-day itineraries.

{few_shot_examples}

USER REQUEST:
Destination: {destination}
Travel Dates: {travel_dates}
Preferences: {preferences}

TASK: Create a comprehensive day-by-day itinerary including:
- Daily schedule with morning, afternoon, and evening activities
- Specific attractions, museums, restaurants, and experiences
- Realistic timing with travel time between locations
- Meal recommendations (breakfast, lunch, dinner) aligned with preferences
- Cultural experiences and local insider tips
- Flexible alternatives for weather or personal preference changes
- Budget estimates for activities and dining
- Transportation tips for each day

Provide a detailed day-by-day itinerary:"""

itinerary_planning_prompt = PromptTemplate(
    input_variables=["destination", "travel_dates", "preferences", "few_shot_examples"],
    template=ITINERARY_PLANNING_TEMPLATE,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_flight_prompt() -> PromptTemplate:
    """Get the flight search prompt template.

    Returns:
        PromptTemplate: Flight search prompt template
    """
    return flight_search_prompt


def get_hotel_prompt() -> PromptTemplate:
    """Get the hotel recommendations prompt template.

    Returns:
        PromptTemplate: Hotel recommendations prompt template
    """
    return hotel_recommendations_prompt


def get_itinerary_prompt() -> PromptTemplate:
    """Get the itinerary planning prompt template.

    Returns:
        PromptTemplate: Itinerary planning prompt template
    """
    return itinerary_planning_prompt
