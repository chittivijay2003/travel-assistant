"""Pydantic models for request and response schemas.

This module defines all the data models used in the Travel Assistant API
for request validation and response serialization.
"""

from pydantic import BaseModel, Field
from typing import List


class TravelRequest(BaseModel):
    """Request schema for travel assistant endpoint.

    Example:
        {
            "destination": "Tokyo, Japan",
            "travel_dates": "May 10 - May 20, 2025",
            "preferences": "I love sushi, anime, and traditional temples"
        }
    """

    destination: str = Field(
        ..., description="Travel destination (e.g., 'Tokyo, Japan')"
    )
    travel_dates: str = Field(
        ...,
        description="Travel dates in natural language (e.g., 'May 10 - May 20, 2025')",
    )
    preferences: str = Field(
        ..., description="Travel preferences and interests as free text"
    )


class ModelResponse(BaseModel):
    """Response from a single Gemini model.

    Attributes:
        model: Model name used
        latency_ms: Response time in milliseconds
        itinerary: Generated day-wise itinerary
        highlights: Key attractions and activities
        raw_response: Complete raw response from the model
    """

    model: str = Field(..., description="Model name (e.g., 'gemini-1.5-flash')")
    latency_ms: int = Field(..., description="Response time in milliseconds")
    itinerary: str = Field(..., description="Day-wise travel itinerary")
    highlights: str = Field(..., description="Key attractions and activities")
    raw_response: str = Field(..., description="Complete raw response from model")


class ComparisonData(BaseModel):
    """Comparison between Flash and Pro model responses.

    Attributes:
        summary: Text summary comparing both responses
        flash_strengths: List of Flash model's strengths
        pro_strengths: List of Pro model's strengths
        recommended_plan: Recommended itinerary (Flash, Pro, or merged)
    """

    summary: str = Field(..., description="Comparison summary of both responses")
    flash_strengths: List[str] = Field(
        ..., description="Strengths of Gemini Flash response"
    )
    pro_strengths: List[str] = Field(
        ..., description="Strengths of Gemini Pro response"
    )
    recommended_plan: str = Field(
        ..., description="Recommended plan: Flash, Pro, or best-of-both merged"
    )


class TravelAssistantResponse(BaseModel):
    """Complete response from travel assistant endpoint.

    Example:
        {
            "request": {...},
            "flash": {...},
            "pro": {...},
            "comparison": {...}
        }
    """

    request: TravelRequest = Field(..., description="Original travel request")
    flash: ModelResponse = Field(..., description="Gemini Flash model response")
    pro: ModelResponse = Field(..., description="Gemini Pro model response")
    comparison: ComparisonData = Field(
        ..., description="Comparison between both models"
    )
