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

    At least one of destination, travel_dates, or preferences must be provided.
    Missing fields will be filled from user history.

    Example:
        {
            "destination": "Paris, France",
            "travel_dates": "June 1 - June 10, 2025",
            "preferences": "art museums, local food, and boutique hotels",
            "user_id": "user_001"  # Optional
        }
    """

    destination: Optional[str] = Field(
        default=None, description="Travel destination (e.g., 'Paris, France')"
    )
    travel_dates: Optional[str] = Field(
        default=None,
        description="Travel dates in natural language (e.g., 'June 1 - June 10, 2025')",
    )
    preferences: Optional[str] = Field(
        default=None, description="Travel preferences and interests as free text"
    )
    user_id: Optional[str] = Field(
        default="default_user",
        description="User ID for personalized few-shot examples (optional)",
    )

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        """Validate that at least one of destination, travel_dates, or preferences is provided."""
        if not any([self.destination, self.travel_dates, self.preferences]):
            raise ValueError(
                "At least one of 'destination', 'travel_dates', or 'preferences' must be provided. "
                "Missing fields will be filled from user history."
            )
        return self


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


# New response format for Assignment
class TravelAssistantResponse(BaseModel):
    """Complete response from travel assistant endpoint.

    New format matching assignment requirements with detailed metrics:
        {
            "flight_recommendations": "Round-trip flights...",
            "hotel_recommendations": "3 boutique hotels...",
            "itinerary": "Day 1: Visit...",
            "scenario_outputs": {...},
            "token_metrics": {...},
            "quality_metrics": {...},
            "total_latency_ms": 890
        }
    """

    # Primary response (Scenario 3 - Smart optimized)
    flight_recommendations: str = Field(
        ..., description="Flight search results and recommendations (Scenario 3)"
    )
    hotel_recommendations: str = Field(
        ..., description="Hotel suggestions based on preferences (Scenario 3)"
    )
    itinerary: str = Field(..., description="Day-by-day travel itinerary (Scenario 3)")

    # Scenario comparison outputs
    scenario_outputs: Dict[str, Dict[str, str]] = Field(
        ..., description="AI responses for all 3 scenarios"
    )

    token_metrics: TokenMetrics = Field(..., description="Detailed token usage metrics")
    quality_metrics: QualityMetrics = Field(..., description="AI quality measurements")
    total_latency_ms: int = Field(
        ..., description="Total response time in milliseconds"
    )
