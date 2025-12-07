"""Pydantic models for request and response schemas.

This module defines all the data models used in the Travel Assistant API
for request validation and response serialization.

Updated for Assignment: Generative AI Travel Assistant
Author: Chitti Vijay
Date: November 25, 2025
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict


class TravelRequest(BaseModel):
    """Request schema for travel assistant endpoint.

    All three fields (destination, travel_dates, preferences) are required.
    User ID is optional and defaults to "default_user".

    Example:
        {
            "destination": "Paris, France",
            "travel_dates": "June 1 - June 10, 2025",
            "preferences": "art museums, local food, and boutique hotels",
            "user_id": "user_001"  # Optional
        }
    """

    destination: str = Field(
        ..., description="Travel destination (e.g., 'Paris, France')"
    )
    travel_dates: str = Field(
        ...,
        description="Travel dates in natural language (e.g., 'June 1 - June 10, 2025')",
    )
    preferences: str = Field(
        ..., description="Travel preferences and interests as free text"
    )
    user_id: Optional[str] = Field(
        default="guest_user",
        description="User ID for personalized few-shot examples (defaults to guest_user)",
    )


# Detailed metrics for individual components
class ComponentMetrics(BaseModel):
    """Metrics for individual component (flight/hotel/itinerary)."""

    input_tokens: int = Field(..., description="Input/prompt tokens used")
    output_tokens: int = Field(..., description="Output/completion tokens generated")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    latency_ms: int = Field(..., description="Response time in milliseconds")
    cost_estimate: float = Field(..., description="Estimated cost in USD")


class ScenarioMetrics(BaseModel):
    """Token metrics and response for a specific scenario."""

    input_tokens: int = Field(..., description="Input/prompt tokens")
    output_tokens: int = Field(..., description="Output/completion tokens")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    cost_estimate: float = Field(..., description="Estimated cost in USD")
    flight_response: str = Field(..., description="AI-generated flight recommendations")
    hotel_response: str = Field(..., description="AI-generated hotel recommendations")
    itinerary_response: str = Field(..., description="AI-generated itinerary")
    latency_ms: int = Field(..., description="Total latency for this scenario")


class TokenMetrics(BaseModel):
    """Detailed token usage breakdown with scenario comparison."""

    flight: ComponentMetrics = Field(..., description="Flight component metrics")
    hotel: ComponentMetrics = Field(..., description="Hotel component metrics")
    itinerary: ComponentMetrics = Field(..., description="Itinerary component metrics")

    total_input_tokens: int = Field(
        ..., description="Total input tokens across all components"
    )
    total_output_tokens: int = Field(
        ..., description="Total output tokens across all components"
    )
    total_tokens: int = Field(..., description="Grand total tokens")
    total_cost_estimate: float = Field(..., description="Total estimated cost in USD")

    # Scenario-based comparison
    scenario_1_no_history: ScenarioMetrics = Field(
        ..., description="Scenario 1: No history baseline (what if no examples used)"
    )
    scenario_2_all_history: ScenarioMetrics = Field(
        ..., description="Scenario 2: All history naive (what if ALL examples included)"
    )
    scenario_3_smart_history: ScenarioMetrics = Field(
        ...,
        description="Scenario 3: Smart optimized (actual usage with smart selection)",
    )

    # Legacy fields for backward compatibility
    baseline_tokens: int = Field(
        ..., description="Tokens if ALL history was included (baseline)"
    )
    tokens_saved: int = Field(..., description="Tokens saved via smart selection")
    savings_percentage: float = Field(..., description="Percentage of tokens saved")


class QualityMetrics(BaseModel):
    """AI quality measurement metrics."""

    response_completeness: float = Field(..., description="Completeness score (0-100)")
    response_relevance: float = Field(..., description="Relevance to request (0-100)")
    few_shot_examples_used: int = Field(..., description="Number of examples included")
    similarity_scores: List[float] = Field(
        ..., description="Similarity scores of selected examples"
    )
    avg_similarity: float = Field(..., description="Average similarity score")
    cache_hit: bool = Field(
        default=False, description="Whether examples came from cache"
    )
    ranking_info: Optional[Dict] = Field(
        default=None,
        description="Example ranking details (satisfaction, popularity, recency scores)",
    )


# Simplified response format for end users
class TravelAssistantResponse(BaseModel):
    """Simplified response from travel assistant endpoint.

    Clean, user-friendly format:
        {
            "flight_recommendations": "Round-trip flights from New York to Paris...",
            "hotel_recommendations": "3 boutique hotels near Montmartre...",
            "itinerary": "Day 1: Visit the Louvre and Seine cruise...",
            "token_usage": 1450,
            "latency_ms": 890,
            "prompt_templates": {...},
            "selected_few_shot_examples": [...]
        }
    """

    flight_recommendations: str = Field(
        ..., description="Flight search results and recommendations"
    )
    hotel_recommendations: str = Field(
        ..., description="Hotel suggestions based on preferences"
    )
    itinerary: str = Field(..., description="Day-by-day travel itinerary")
    
    token_usage: int = Field(..., description="Total tokens used")
    latency_ms: int = Field(..., description="Response time in milliseconds")
    
    prompt_templates: Dict[str, str] = Field(
        ..., description="LangChain prompt templates used (flight, hotel, itinerary)"
    )
    selected_few_shot_examples: List[str] = Field(
        ..., description="Few-shot examples selected for this request"
    )
