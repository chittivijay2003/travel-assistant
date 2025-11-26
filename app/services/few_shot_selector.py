"""Dynamic Few-Shot Example Selector with Smart Selection Logic.

This module selects relevant few-shot examples from user history using:
- HIGH similarity (>70%): Use FULL recent trip details (~800 tokens)
- MEDIUM similarity (40-70%): Use condensed recent trips (~300 tokens)
- LOW similarity (<40%): Use summary only (~150 tokens)

This achieves 60-80% token savings while maintaining personalization.

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant - Task 3
"""

from typing import List, Dict, Tuple
from app.services.user_history import get_history_manager
from app.services.example_cache import example_cache


class FewShotSelector:
    """Selects relevant few-shot examples from user history with smart token optimization."""

    # Similarity thresholds for selection strategy
    HIGH_SIMILARITY_THRESHOLD = 0.70
    MEDIUM_SIMILARITY_THRESHOLD = 0.40

    def __init__(self):
        """Initialize the few-shot selector."""
        self.history_manager = get_history_manager()
        self.cache = example_cache

    def calculate_similarity_score(
        self, trip: Dict, destination: str, preferences: str
    ) -> float:
        """Calculate similarity score between a past trip and current request.

        Similarity factors:
        - Destination match: 40% weight
        - Preference overlap: 40% weight
        - Satisfaction rating: 20% weight

        Args:
            trip: Past trip dictionary
            destination: Current destination
            preferences: Current preferences

        Returns:
            Similarity score (0.0 to 1.0)
        """
        score = 0.0

        # 1. Destination similarity (40% weight)
        trip_dest = trip.get("destination", "").lower()
        current_dest = destination.lower()

        # Extract location parts (city, country)
        trip_parts = set(word.strip() for word in trip_dest.replace(",", " ").split())
        current_parts = set(
            word.strip() for word in current_dest.replace(",", " ").split()
        )

        # Calculate overlap
        if trip_parts & current_parts:  # Any overlap
            overlap_ratio = len(trip_parts & current_parts) / len(
                trip_parts | current_parts
            )
            score += 0.4 * overlap_ratio

        # 2. Preference similarity (40% weight)
        trip_prefs = set(trip.get("preferences", "").lower().replace(",", " ").split())
        current_prefs = set(preferences.lower().replace(",", " ").split())

        # Remove common stopwords
        stopwords = {
            "and",
            "the",
            "a",
            "an",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        trip_prefs = {p for p in trip_prefs if p and p not in stopwords}
        current_prefs = {p for p in current_prefs if p and p not in stopwords}

        if trip_prefs and current_prefs:
            preference_overlap = len(trip_prefs & current_prefs)
            preference_total = len(trip_prefs | current_prefs)
            if preference_total > 0:
                score += 0.4 * (preference_overlap / preference_total)

        # 3. Satisfaction rating bonus (20% weight)
        rating = trip.get("satisfaction_rating", 0)
        if rating > 0:
            score += 0.2 * (rating / 5.0)

        return min(score, 1.0)  # Cap at 1.0

    async def select_examples_smart(
        self,
        destination: str,
        preferences: str,
        user_id: str = "default_user",
        max_examples: int = 3,
    ) -> Dict:
        """Smart selection: Choose strategy based on similarity.

        Returns a dict with:
        - strategy: "full" | "condensed" | "summary"
        - examples: List of examples or summary text
        - estimated_tokens: Approximate token count
        - ranking_info: Re-ranking details if from cache

        Args:
            destination: Destination for current request
            preferences: User preferences for current request
            user_id: User identifier
            max_examples: Maximum number of examples to return

        Returns:
            Dict with strategy, examples, token estimate, and ranking info
        """
        # Check cache first for quick retrieval
        cached_examples = self.cache.get(destination, preferences)
        if cached_examples:
            # Use re-ranked cached examples
            ranked_examples, ranking_info = self.cache.get_ranked_examples(
                destination, preferences, top_k=max_examples
            )
            if ranked_examples:
                return {
                    "strategy": "condensed",
                    "examples": ranked_examples,
                    "estimated_tokens": len(ranked_examples) * 200,
                    "from_cache": True,
                    "ranking_info": ranking_info,
                }

        # Get user data
        recent_trips = await self.history_manager.get_recent_trips(user_id)
        summary = await self.history_manager.get_summary(user_id)

        if not recent_trips and not summary.get("totalTrips"):
            return {"strategy": "none", "examples": [], "estimated_tokens": 0}

        # Calculate similarity scores for recent trips
        scored_trips = []
        for trip in recent_trips:
            score = self.calculate_similarity_score(trip, destination, preferences)
            trip_with_score = trip.copy()
            trip_with_score["similarity_score"] = score
            scored_trips.append(trip_with_score)

        # Sort by score
        scored_trips.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Get best match score
        best_score = scored_trips[0]["similarity_score"] if scored_trips else 0

        # STRATEGY 1: HIGH similarity → Use FULL trip details
        if best_score >= self.HIGH_SIMILARITY_THRESHOLD:
            top_match = scored_trips[0]
            result = {
                "strategy": "full",
                "examples": [top_match],
                "estimated_tokens": 800,  # Full trip details
                "from_cache": False,
                "ranking_info": None,
            }
            # Cache the high-quality match
            self.cache.put(destination, preferences, [top_match])
            return result

        # STRATEGY 2: MEDIUM similarity → Use condensed recent trips
        elif best_score >= self.MEDIUM_SIMILARITY_THRESHOLD:
            top_matches = scored_trips[: min(max_examples, len(scored_trips))]
            result = {
                "strategy": "condensed",
                "examples": top_matches,
                "estimated_tokens": len(top_matches) * 200,  # Condensed format
                "from_cache": False,
                "ranking_info": None,
            }
            # Cache the condensed matches
            self.cache.put(destination, preferences, top_matches)
            return result

        # STRATEGY 3: LOW similarity → Use summary only
        else:
            return {
                "strategy": "summary",
                "examples": summary,
                "estimated_tokens": 150,  # Summary only
                "from_cache": False,
                "ranking_info": None,
            }

    def format_examples_for_prompt(
        self, selection_result: Dict, prompt_type: str = "general"
    ) -> str:
        """Format selected examples into a string for prompt injection.

        Args:
            selection_result: Result from select_examples_smart()
            prompt_type: Type of prompt ("flight", "hotel", "itinerary")

        Returns:
            Formatted examples string for prompt
        """
        strategy = selection_result["strategy"]
        examples = selection_result["examples"]

        if strategy == "none":
            return "No previous travel history available for this user.\n"

        # FULL trip details (high similarity)
        if strategy == "full":
            trip = examples[0]
            formatted = "RELEVANT PAST TRIP (High Similarity):\n\n"
            formatted += f"Destination: {trip['destination']}\n"
            formatted += f"Preferences: {trip['preferences']}\n"
            formatted += f"User Rating: {trip['satisfaction_rating']}/5\n\n"

            if prompt_type == "flight" and trip.get("flight_summary"):
                formatted += f"Flight Booked: {trip['flight_summary']}\n"
            elif prompt_type == "hotel" and trip.get("hotel_summary"):
                formatted += f"Hotel Booked: {trip['hotel_summary']}\n"
            elif prompt_type == "itinerary" and trip.get("itinerary_highlights"):
                formatted += (
                    f"Highlights Enjoyed: {', '.join(trip['itinerary_highlights'])}\n"
                )

            formatted += "\nBased on this successful past trip, provide similar recommendations:\n"
            return formatted

        # CONDENSED trips (medium similarity)
        elif strategy == "condensed":
            formatted = "PAST TRIPS (Similar Interests):\n\n"
            for i, trip in enumerate(examples, 1):
                formatted += f"{i}. {trip['destination']}\n"
                formatted += f"   Interests: {trip['preferences']}\n"
                formatted += f"   Rating: {trip['satisfaction_rating']}/5\n"

            formatted += "\nUse these preferences to guide your recommendations:\n"
            return formatted

        # SUMMARY only (low similarity)
        elif strategy == "summary":
            summary = examples
            formatted = "USER TRAVEL PROFILE:\n\n"
            formatted += f"Total Trips: {summary.get('totalTrips', 0)}\n"

            if summary.get("favoriteDestinations"):
                formatted += f"Favorite Destinations: {', '.join(summary['favoriteDestinations'][:5])}\n"

            if summary.get("preferencePatterns"):
                formatted += f"Common Interests: {', '.join(summary['preferencePatterns'][:10])}\n"

            formatted += (
                f"Average Satisfaction: {summary.get('avgSatisfactionRating', 0)}/5\n"
            )
            formatted += (
                "\nProvide recommendations aligned with these general preferences:\n"
            )
            return formatted

        return ""

    async def get_examples_for_flight(
        self, destination: str, preferences: str, user_id: str = "default_user"
    ) -> Tuple[str, List[float], Dict]:
        """Get formatted few-shot examples for flight search.

        Args:
            destination: Destination
            preferences: User preferences
            user_id: User identifier

        Returns:
            Tuple of (formatted_examples_string, similarity_scores_list, ranking_info_dict)
        """
        selection = await self.select_examples_smart(destination, preferences, user_id)
        formatted_text = self.format_examples_for_prompt(
            selection, prompt_type="flight"
        )

        # Extract similarity scores
        similarity_scores = []
        if selection["strategy"] == "full":
            similarity_scores = [selection["examples"][0].get("similarity_score", 0.0)]
        elif selection["strategy"] == "condensed":
            similarity_scores = [
                ex.get("similarity_score", 0.0) for ex in selection["examples"]
            ]
        elif selection["strategy"] == "summary":
            similarity_scores = [0.0]  # No specific match, generic summary
        elif selection["strategy"] == "none":
            similarity_scores = []  # No history available

        # Get ranking info
        ranking_info = selection.get("ranking_info")
        cache_hit = selection.get("from_cache", False)

        return (
            formatted_text,
            similarity_scores,
            {"ranking_info": ranking_info, "cache_hit": cache_hit},
        )

    async def get_examples_for_hotel(
        self, destination: str, preferences: str, user_id: str = "default_user"
    ) -> Tuple[str, List[float], Dict]:
        """Get formatted few-shot examples for hotel recommendations.

        Args:
            destination: Destination
            preferences: User preferences
            user_id: User identifier

        Returns:
            Tuple of (formatted_examples_string, similarity_scores_list, ranking_info_dict)
        """
        selection = await self.select_examples_smart(destination, preferences, user_id)
        formatted_text = self.format_examples_for_prompt(selection, prompt_type="hotel")

        # Extract similarity scores
        similarity_scores = []
        if selection["strategy"] == "full":
            similarity_scores = [selection["examples"][0].get("similarity_score", 0.0)]
        elif selection["strategy"] == "condensed":
            similarity_scores = [
                ex.get("similarity_score", 0.0) for ex in selection["examples"]
            ]
        elif selection["strategy"] == "summary":
            similarity_scores = [0.0]  # No specific match, generic summary
        elif selection["strategy"] == "none":
            similarity_scores = []  # No history available

        # Get ranking info
        ranking_info = selection.get("ranking_info")
        cache_hit = selection.get("from_cache", False)

        return (
            formatted_text,
            similarity_scores,
            {"ranking_info": ranking_info, "cache_hit": cache_hit},
        )

    async def get_examples_for_itinerary(
        self, destination: str, preferences: str, user_id: str = "default_user"
    ) -> Tuple[str, List[float], Dict]:
        """Get formatted few-shot examples for itinerary planning.

        Args:
            destination: Destination
            preferences: User preferences
            user_id: User identifier

        Returns:
            Tuple of (formatted_examples_string, similarity_scores_list, ranking_info_dict)
        """
        selection = await self.select_examples_smart(destination, preferences, user_id)
        formatted_text = self.format_examples_for_prompt(
            selection, prompt_type="itinerary"
        )

        # Extract similarity scores
        similarity_scores = []
        if selection["strategy"] == "full":
            similarity_scores = [selection["examples"][0].get("similarity_score", 0.0)]
        elif selection["strategy"] == "condensed":
            similarity_scores = [
                ex.get("similarity_score", 0.0) for ex in selection["examples"]
            ]
        elif selection["strategy"] == "summary":
            similarity_scores = [0.0]  # No specific match, generic summary
        elif selection["strategy"] == "none":
            similarity_scores = []  # No history available

        # Get ranking info
        ranking_info = selection.get("ranking_info")
        cache_hit = selection.get("from_cache", False)

        return (
            formatted_text,
            similarity_scores,
            {"ranking_info": ranking_info, "cache_hit": cache_hit},
        )


# Global instance for easy access
_few_shot_selector = None


def get_few_shot_selector() -> FewShotSelector:
    """Get or create the global few-shot selector instance.

    Returns:
        FewShotSelector instance
    """
    global _few_shot_selector
    if _few_shot_selector is None:
        _few_shot_selector = FewShotSelector()
    return _few_shot_selector
