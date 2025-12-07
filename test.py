"""
Visible Test Script for Travel Assistant API (Assignment D2)
============================================================
This script performs BASIC SANITY CHECKS on the /travel-assistant endpoint.
It validates the OpenAPI specification compliance and outputs a final score.

Students receive this file to verify their API works before submission.
"""

import requests
import json
import sys
from typing import Dict, Any, Tuple, List
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_URL = f"http://localhost:{os.getenv('API_PORT', '8000')}"
ENDPOINT = "/travel-assistant"
OUTPUT_FILE = "output.txt"

# =============================================================================
# HELPER CLASSES
# =============================================================================
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class Logger:
    """Dual logger: writes to both console and file"""
    def __init__(self, filename: str):
        self.filename = filename
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(f"{'='*70}\n")
            f.write(f"Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*70}\n\n")

    def log(self, message: str, color: str = "", file_only: bool = False):
        """Print to console with color and write plain text to file"""
        if not file_only:
            print(f"{color}{message}{Colors.RESET if color else ''}")
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(message + '\n')


# Initialize logger
logger = Logger(OUTPUT_FILE)

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================
def validate_response_structure(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates that the API response matches the OpenAPI specification.
    
    Required fields:
    - flight_recommendations (string)
    - hotel_recommendations (string)  
    - itinerary (string)
    - token_usage (integer, positive)
    - latency_ms (number, positive)
    - prompt_templates (object with flight_template, hotel_template, itinerary_template)
    - selected_few_shot_examples (array of strings - stringified few-shot examples)
    
    Note: Students can store few-shot examples internally in any format they prefer.
    The API must return them as an array of strings (e.g., JSON stringified).
    """
    # Check content fields exist and are non-empty strings
    content_fields = ['flight_recommendations', 'hotel_recommendations', 'itinerary']
    for field in content_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'"
        if not isinstance(data[field], str):
            return False, f"Field '{field}' must be a string"
        if len(data[field].strip()) < 10:
            return False, f"Field '{field}' is too short (min 10 chars)"

    # Check metric fields exist
    if 'token_usage' not in data:
        return False, "Missing required field: 'token_usage'"
    if 'latency_ms' not in data:
        return False, "Missing required field: 'latency_ms'"

    # Validate metric types and values
    if not isinstance(data['token_usage'], int):
        return False, "token_usage must be an integer"
    if data['token_usage'] <= 0:
        return False, "token_usage must be positive"

    if not isinstance(data['latency_ms'], (int, float)):
        return False, "latency_ms must be a number"
    if data['latency_ms'] <= 0:
        return False, "latency_ms must be positive"

    # Validate prompt_templates
    if 'prompt_templates' not in data:
        return False, "Missing required field: 'prompt_templates'"
    if not isinstance(data['prompt_templates'], dict):
        return False, "prompt_templates must be an object"
    template_fields = ['flight_template', 'hotel_template', 'itinerary_template']
    for field in template_fields:
        if field not in data['prompt_templates']:
            return False, f"Missing field in prompt_templates: '{field}'"
        if not isinstance(data['prompt_templates'][field], str):
            return False, f"prompt_templates.{field} must be a string"

    # Validate selected_few_shot_examples
    # Per OpenAPI spec: array of strings (stringified few-shot examples)
    # Students can store examples internally in any format, but API returns strings
    if 'selected_few_shot_examples' not in data:
        return False, "Missing required field: 'selected_few_shot_examples'"
    if not isinstance(data['selected_few_shot_examples'], list):
        return False, "selected_few_shot_examples must be an array"
    if len(data['selected_few_shot_examples']) == 0:
        return False, "selected_few_shot_examples must contain at least one example"
    
    # Each element must be a string (the stringified version of the example)
    for i, example in enumerate(data['selected_few_shot_examples']):
        if not isinstance(example, str):
            return False, f"selected_few_shot_examples[{i}] must be a string"
        # Verify the string is non-empty
        if len(example.strip()) == 0:
            return False, f"selected_few_shot_examples[{i}] cannot be empty"

    return True, "Valid response structure"


def validate_metrics_sanity(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Basic sanity check for metrics.
    - Token usage should be > 100 (real LLM calls use many tokens)
    - Latency should be > 100ms (LLM calls take time)
    """
    token_usage = data.get('token_usage', 0)
    latency_ms = data.get('latency_ms', 0)
    
    if token_usage < 100:
        return False, f"Token usage too low ({token_usage}). LLM may not be called."
    if latency_ms < 100:
        return False, f"Latency too fast ({latency_ms}ms). LLM may not be called."
    
    return True, f"Metrics look realistic (tokens={token_usage}, latency={latency_ms}ms)"


# =============================================================================
# TEST EXECUTION
# =============================================================================
def run_test(test_name: str, payload: Dict[str, Any], expect_success: bool = True) -> Dict[str, Any]:
    """
    Runs a single test against the API endpoint.
    
    Returns:
        Dict with 'passed' and 'message' keys
    """
    logger.log(f"\n{'='*70}", Colors.BLUE)
    logger.log(f"{test_name}", Colors.BLUE + Colors.BOLD)
    logger.log(f"{'='*70}", Colors.BLUE)
    logger.log(f"Payload: {json.dumps(payload, indent=2)}")

    result = {"passed": False, "message": ""}

    try:
        # Make API request
        response = requests.post(f"{BASE_URL}{ENDPOINT}", json=payload, timeout=300)
        logger.log(f"Status Code: {response.status_code}")

        if response.status_code == 200 and expect_success:
            # Parse response
            data = response.json()
            
            # Log metrics
            logger.log(f"\n--- Response Metrics ---")
            logger.log(f"Token Usage: {data.get('token_usage', 'N/A')}")
            logger.log(f"Latency: {data.get('latency_ms', 'N/A')} ms")
            
            # Log LLM-generated content (file only, not CLI)
            logger.log(f"\n--- LLM Generated Content ---", file_only=True)
            logger.log(f"\nFlight Recommendations:\n{data.get('flight_recommendations', 'N/A')}", file_only=True)
            logger.log(f"\nHotel Recommendations:\n{data.get('hotel_recommendations', 'N/A')}", file_only=True)
            logger.log(f"\nItinerary:\n{data.get('itinerary', 'N/A')}", file_only=True)
            logger.log(f"\n--- End LLM Generated Content ---", file_only=True)
            
            # Validate structure
            struct_valid, struct_msg = validate_response_structure(data)
            if not struct_valid:
                result["message"] = struct_msg
                logger.log(f"\n[FAILED] {struct_msg}", Colors.RED)
                return result
            
            # Check metrics sanity
            metrics_valid, metrics_msg = validate_metrics_sanity(data)
            logger.log(f"\n--- Metrics Check ---")
            logger.log(metrics_msg)
            if not metrics_valid:
                logger.log(f"[WARNING] {metrics_msg}", Colors.YELLOW)
            
            result["passed"] = True
            result["message"] = "Valid response with proper structure"
            logger.log(f"\n[PASSED]", Colors.GREEN)
            return result

        elif response.status_code == 422 and not expect_success:
            # Expected validation error
            try:
                error_data = response.json()
                logger.log(f"\n--- Validation Error Details ---")
                logger.log(f"{json.dumps(error_data, indent=2)}")
            except:
                logger.log(f"\n--- Raw Response ---")
                logger.log(f"{response.text}")
            
            result["passed"] = True
            result["message"] = "Correctly rejected invalid input"
            logger.log(f"\n[PASSED] Validation error as expected", Colors.GREEN)
            return result

        else:
            result["message"] = f"Unexpected status code: {response.status_code}"
            logger.log(f"\n[FAILED] {result['message']}", Colors.RED)
            return result

    except requests.exceptions.ConnectionError:
        result["message"] = "Connection refused. Is the server running on port 8000?"
        logger.log(f"\n[FAILED] {result['message']}", Colors.RED)
        return result
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        logger.log(f"\n[FAILED] {result['message']}", Colors.RED)
        return result


# =============================================================================
# MAIN EXECUTION
# =============================================================================
def main():
    """Run all visible tests and calculate final score"""
    
    logger.log("="*70, Colors.BOLD + Colors.BLUE)
    logger.log("Travel Assistant API (D2) - Visible Test Suite", Colors.BOLD + Colors.BLUE)
    logger.log("="*70, Colors.BOLD + Colors.BLUE)
    logger.log("\nThis test validates OpenAPI spec compliance and basic functionality.\n")

    # Define test cases
    test_cases = [
        {
            "name": "Test 1: Standard Trip Request (Paris)",
            "payload": {
                "destination": "Paris, France",
                "travel_dates": "June 1 - June 10, 2025",
                "preferences": "museums and local food"
            },
            "expect_success": True
        },
        {
            "name": "Test 2: Short Trip Request (New York)", 
            "payload": {
                "destination": "New York, USA",
                "travel_dates": "Dec 20 - Dec 22, 2025",
                "preferences": "Christmas lights and shopping"
            },
            "expect_success": True
        },
        {
            "name": "Test 3: Missing Field (Should Return 422)",
            "payload": {
                "destination": "London, UK",
                "travel_dates": "Aug 1 - Aug 5, 2025"
                # Missing 'preferences' field intentionally
            },
            "expect_success": False
        }
    ]

    # Run all tests and collect results
    results = []
    for tc in test_cases:
        result = run_test(tc["name"], tc["payload"], tc["expect_success"])
        results.append(result)

    # ==========================================================================
    # CALCULATE FINAL RESULTS
    # ==========================================================================
    tests_passed = sum(1 for r in results if r["passed"])
    total_tests = len(test_cases)
    
    logger.log(f"\n{'='*70}", Colors.BOLD)
    logger.log("FINAL RESULTS", Colors.BOLD + Colors.BLUE)
    logger.log(f"{'='*70}", Colors.BOLD)
    logger.log(f"Tests Passed: {tests_passed}/{total_tests}", Colors.BOLD)
    
    # Detailed breakdown
    logger.log(f"\n--- Test Breakdown ---")
    for i, (tc, res) in enumerate(zip(test_cases, results), 1):
        status = "✓" if res["passed"] else "✗"
        logger.log(f"  {status} Test {i}: {res['message']}")
    
    logger.log(f"\n{'='*70}")
    
    # Exit with appropriate code
    if tests_passed == total_tests:
        logger.log("ALL TESTS PASSED!", Colors.GREEN + Colors.BOLD)
        sys.exit(0)
    else:
        logger.log("SOME TESTS FAILED", Colors.RED + Colors.BOLD)
        sys.exit(1)


if __name__ == "__main__":
    main()