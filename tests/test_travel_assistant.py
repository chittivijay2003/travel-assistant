"""Unit and integration tests for Travel Assistant API.

This module tests:
- Request/response validation
- Endpoint functionality
- Error handling
- Model integration
"""

import pytest
from fastapi.testclient import TestClient
from main import app

# Create test client
client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert "Travel Assistant API" in response.json()["message"]

    def test_health_endpoint(self):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestTravelAssistantEndpoint:
    """Test the main travel assistant endpoint."""

    @pytest.fixture
    def valid_request_data(self):
        """Provide valid request data for tests."""
        return {
            "destination": "Paris, France",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget": "medium",
            "traveler_profile": "couple",
            "preferences": ["culture", "food", "art"],
            "language": "en",
        }

    def test_valid_request(self, valid_request_data):
        """Test endpoint with valid request data."""
        response = client.post("/api/travel-assistant", json=valid_request_data)

        # Should return 200 OK
        assert response.status_code == 200

        # Check response structure
        data = response.json()
        assert "request" in data
        assert "flash" in data
        assert "pro" in data
        assert "comparison" in data

        # Validate flash response
        assert "model" in data["flash"]
        assert "latency_ms" in data["flash"]
        assert "itinerary" in data["flash"]
        assert "highlights" in data["flash"]
        assert "raw_response" in data["flash"]
        assert isinstance(data["flash"]["latency_ms"], int)
        assert data["flash"]["latency_ms"] > 0

        # Validate pro response
        assert "model" in data["pro"]
        assert "latency_ms" in data["pro"]
        assert isinstance(data["pro"]["latency_ms"], int)

        # Validate comparison
        assert "summary" in data["comparison"]
        assert "flash_strengths" in data["comparison"]
        assert "pro_strengths" in data["comparison"]
        assert "recommended_plan" in data["comparison"]
        assert isinstance(data["comparison"]["flash_strengths"], list)
        assert isinstance(data["comparison"]["pro_strengths"], list)

    def test_minimal_request(self):
        """Test endpoint with minimal required fields only."""
        minimal_data = {
            "destination": "London, UK",
            "start_date": "2025-07-15",
            "end_date": "2025-07-20",
        }
        response = client.post("/api/travel-assistant", json=minimal_data)

        # Should still work with optional fields missing
        assert response.status_code == 200
        data = response.json()
        assert "flash" in data
        assert "pro" in data

    def test_missing_required_fields(self):
        """Test endpoint returns 422 when required fields are missing."""
        # Missing destination
        invalid_data = {"start_date": "2025-06-01", "end_date": "2025-06-07"}
        response = client.post("/api/travel-assistant", json=invalid_data)
        assert response.status_code == 422

        # Missing dates
        invalid_data = {"destination": "Rome, Italy"}
        response = client.post("/api/travel-assistant", json=invalid_data)
        assert response.status_code == 422

    def test_invalid_date_format(self):
        """Test endpoint rejects invalid date formats."""
        invalid_data = {
            "destination": "Barcelona, Spain",
            "start_date": "2025-13-40",  # Invalid date
            "end_date": "2025-06-07",
        }
        response = client.post("/api/travel-assistant", json=invalid_data)
        assert response.status_code == 422

    def test_end_date_before_start_date(self):
        """Test that end_date before start_date is handled."""
        # Note: This would require additional validation in the API
        # For now, we just check the API doesn't crash
        invalid_data = {
            "destination": "Tokyo, Japan",
            "start_date": "2025-06-10",
            "end_date": "2025-06-05",  # Before start_date
        }
        response = client.post("/api/travel-assistant", json=invalid_data)
        # API should either validate this (422) or handle gracefully (200)
        assert response.status_code in [200, 422]

    def test_preferences_as_list(self, valid_request_data):
        """Test that preferences field accepts a list."""
        valid_request_data["preferences"] = ["adventure", "nature", "photography"]
        response = client.post("/api/travel-assistant", json=valid_request_data)
        assert response.status_code == 200

    def test_empty_preferences(self, valid_request_data):
        """Test that empty preferences list is valid."""
        valid_request_data["preferences"] = []
        response = client.post("/api/travel-assistant", json=valid_request_data)
        assert response.status_code == 200

    def test_budget_levels(self, valid_request_data):
        """Test different budget levels."""
        for budget in ["low", "medium", "high"]:
            valid_request_data["budget"] = budget
            response = client.post("/api/travel-assistant", json=valid_request_data)
            assert response.status_code == 200

    def test_traveler_profiles(self, valid_request_data):
        """Test different traveler profiles."""
        for profile in ["solo", "couple", "family", "group"]:
            valid_request_data["traveler_profile"] = profile
            response = client.post("/api/travel-assistant", json=valid_request_data)
            assert response.status_code == 200

    def test_language_support(self, valid_request_data):
        """Test language parameter."""
        for lang in ["en", "es", "fr", "de"]:
            valid_request_data["language"] = lang
            response = client.post("/api/travel-assistant", json=valid_request_data)
            assert response.status_code == 200


class TestResponseSchemaValidation:
    """Test response schema structure and types."""

    @pytest.fixture
    def sample_response_data(self):
        """Get a sample response from the API."""
        request_data = {
            "destination": "Amsterdam, Netherlands",
            "start_date": "2025-08-01",
            "end_date": "2025-08-05",
            "budget": "medium",
            "preferences": ["culture", "cycling"],
        }
        response = client.post("/api/travel-assistant", json=request_data)
        return response.json()

    def test_request_echo(self, sample_response_data):
        """Test that original request is echoed in response."""
        assert "request" in sample_response_data
        assert "destination" in sample_response_data["request"]
        assert "start_date" in sample_response_data["request"]
        assert "end_date" in sample_response_data["request"]

    def test_flash_response_structure(self, sample_response_data):
        """Test Flash model response structure."""
        flash = sample_response_data["flash"]
        assert isinstance(flash["model"], str)
        assert isinstance(flash["latency_ms"], int)
        assert isinstance(flash["itinerary"], str)
        assert isinstance(flash["highlights"], str)
        assert isinstance(flash["raw_response"], str)
        assert len(flash["raw_response"]) > 0

    def test_pro_response_structure(self, sample_response_data):
        """Test Pro model response structure."""
        pro = sample_response_data["pro"]
        assert isinstance(pro["model"], str)
        assert isinstance(pro["latency_ms"], int)
        assert isinstance(pro["itinerary"], str)
        assert isinstance(pro["highlights"], str)
        assert isinstance(pro["raw_response"], str)
        assert len(pro["raw_response"]) > 0

    def test_comparison_structure(self, sample_response_data):
        """Test comparison data structure."""
        comparison = sample_response_data["comparison"]
        assert isinstance(comparison["summary"], str)
        assert isinstance(comparison["flash_strengths"], list)
        assert isinstance(comparison["pro_strengths"], list)
        assert isinstance(comparison["recommended_plan"], str)

        # Check that strengths lists contain strings
        for strength in comparison["flash_strengths"]:
            assert isinstance(strength, str)
            assert len(strength) > 0

        for strength in comparison["pro_strengths"]:
            assert isinstance(strength, str)
            assert len(strength) > 0

    def test_latency_values_reasonable(self, sample_response_data):
        """Test that latency values are within reasonable range."""
        flash_latency = sample_response_data["flash"]["latency_ms"]
        pro_latency = sample_response_data["pro"]["latency_ms"]

        # Latencies should be positive
        assert flash_latency > 0
        assert pro_latency > 0

        # Latencies should be less than 30 seconds (30000ms)
        assert flash_latency < 30000
        assert pro_latency < 30000


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_json(self):
        """Test endpoint with malformed JSON."""
        response = client.post(
            "/api/travel-assistant",
            data="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_extra_fields_ignored(self):
        """Test that extra fields in request are ignored."""
        data = {
            "destination": "Berlin, Germany",
            "start_date": "2025-09-01",
            "end_date": "2025-09-07",
            "extra_field": "should be ignored",
            "another_field": 12345,
        }
        response = client.post("/api/travel-assistant", json=data)
        # Should succeed and ignore extra fields
        assert response.status_code == 200


# Run tests with: pytest tests/test_travel_assistant.py -v
