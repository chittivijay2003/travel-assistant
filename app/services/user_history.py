"""User History Management System with Dual-Strategy.

This module handles reading and writing user travel history using:
- recentTrips: Last 10 trips with FULL details (for high-similarity few-shot)
- historySummary: Compressed stats for ALL trips (for context)

Features:
- Auto-pruning when >10 recent trips
- Automatic summary updates
- Smart trip archiving

Author: Chitti Vijay
Date: November 25, 2025
Assignment: Generative AI Travel Assistant - Task 3
"""

import json
import os
import asyncio
from typing import Dict, List
from datetime import datetime
from collections import Counter


class UserHistoryManager:
    """Manages user travel history with dual-strategy approach."""

    MAX_RECENT_TRIPS = 10
    SUMMARY_UPDATE_FREQUENCY = 5

    def __init__(self, history_file: str = None):
        """Initialize the user history manager.

        Args:
            history_file: Path to the JSON file containing user history.
                         If None, uses default location.
        """
        if history_file is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.history_file = os.path.join(
                current_dir, "..", "data", "user_history.json"
            )
        else:
            self.history_file = history_file

        # Async lock for thread-safe file operations across parallel requests
        self._lock = asyncio.Lock()

        self._ensure_history_file_exists()

    def _ensure_history_file_exists(self):
        """Create history file with default structure if it doesn't exist."""
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

            default_history = {
                "users": {
                    "default_user": {
                        "name": "Guest User",
                        "recentTrips": [],
                        "historySummary": {
                            "totalTrips": 0,
                            "favoriteDestinations": [],
                            "preferencePatterns": [],
                            "avgSatisfactionRating": 0,
                            "avgTokenUsage": 0,
                            "avgLatencyMs": 0,
                            "tripsByContinent": {},
                            "lastUpdated": datetime.now().isoformat(),
                        },
                    }
                }
            }

            with open(self.history_file, "w") as f:
                json.dump(default_history, f, indent=2)

    def _load_history_sync(self) -> Dict:
        """Synchronous helper to load history."""
        try:
            with open(self.history_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading history: {e}")
            return {"users": {}}

    async def load_history(self) -> Dict:
        """Load all user history from JSON file (async, non-blocking).

        Returns:
            Dict containing all user history data
        """
        async with self._lock:
            return await asyncio.to_thread(self._load_history_sync)

    def _save_history_sync(self, history: Dict):
        """Synchronous helper to save history."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    async def save_history(self, history: Dict):
        """Save user history to JSON file (async, non-blocking).

        Args:
            history: Complete history dictionary to save
        """
        async with self._lock:
            await asyncio.to_thread(self._save_history_sync, history)

    async def get_user_data(self, user_id: str = "default_user") -> Dict:
        """Get complete user data including recentTrips and historySummary.

        Args:
            user_id: User identifier

        Returns:
            Dict with recentTrips and historySummary
        """
        history = await self.load_history()
        users = history.get("users", {})

        if user_id not in users:
            return users.get(
                "default_user",
                {
                    "name": "Guest User",
                    "recentTrips": [],
                    "historySummary": {
                        "totalTrips": 0,
                        "favoriteDestinations": [],
                        "preferencePatterns": [],
                        "avgSatisfactionRating": 0,
                        "avgTokenUsage": 0,
                        "avgLatencyMs": 0,
                        "tripsByContinent": {},
                        "lastUpdated": datetime.now().isoformat(),
                    },
                },
            )

        return users[user_id]

    async def get_recent_trips(
        self, user_id: str = "default_user", limit: int = None
    ) -> List[Dict]:
        """Get recent trips with FULL details for a specific user.

        Args:
            user_id: User identifier
            limit: Maximum number of trips to return (None = all recent trips)

        Returns:
            List of recent trip dictionaries (max limit or 10)
        """
        user_data = await self.get_user_data(user_id)
        trips = user_data.get("recentTrips", [])
        if limit is not None:
            return trips[:limit]
        return trips

    async def get_summary(self, user_id: str = "default_user") -> Dict:
        """Get compressed summary of ALL trips for a user.

        Args:
            user_id: User identifier

        Returns:
            Summary dictionary
        """
        user_data = await self.get_user_data(user_id)
        return user_data.get("historySummary", {})

    async def add_trip(
        self,
        user_id: str,
        destination: str,
        travel_dates: str,
        preferences: str,
        flight_summary: str = "",
        hotel_summary: str = "",
        itinerary_highlights: List[str] = None,
        satisfaction_rating: int = 0,
        token_usage: int = 0,
        latency_ms: int = 0,
    ):
        """Add a new trip to user's history with dual-strategy storage.

        This method:
        1. Adds trip to recentTrips
        2. Auto-prunes if >10 recent trips
        3. Updates historySummary

        Args:
            user_id: User identifier
            destination: Trip destination
            travel_dates: Travel dates
            preferences: User preferences
            flight_summary: Summary of flight recommendations
            hotel_summary: Summary of hotel recommendations
            itinerary_highlights: List of key activities
            satisfaction_rating: Rating from 1-5 (0 if not rated)
            token_usage: Tokens used for this request
            latency_ms: Response time in milliseconds
        """
        history = await self.load_history()

        # Ensure user exists
        if user_id not in history["users"]:
            history["users"][user_id] = {
                "name": f"User {user_id}",
                "recentTrips": [],
                "historySummary": {
                    "totalTrips": 0,
                    "favoriteDestinations": [],
                    "preferencePatterns": [],
                    "avgSatisfactionRating": 0,
                    "avgTokenUsage": 0,
                    "avgLatencyMs": 0,
                    "tripsByContinent": {},
                    "lastUpdated": datetime.now().isoformat(),
                },
            }

        user = history["users"][user_id]

        # Create new trip entry
        trip_count = user["historySummary"]["totalTrips"] + 1
        new_trip = {
            "id": f"trip_{user_id}_{trip_count}",
            "destination": destination,
            "travel_dates": travel_dates,
            "preferences": preferences,
            "flight_summary": flight_summary,
            "hotel_summary": hotel_summary,
            "itinerary_highlights": itinerary_highlights or [],
            "satisfaction_rating": satisfaction_rating,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat(),
        }

        # Add to recentTrips
        user["recentTrips"].append(new_trip)

        # Auto-prune if exceeds MAX_RECENT_TRIPS
        if len(user["recentTrips"]) > self.MAX_RECENT_TRIPS:
            # Archive oldest trip data to summary before deleting
            oldest_trip = user["recentTrips"].pop(0)
            self._archive_trip_to_summary(user["historySummary"], oldest_trip)

        # Update summary
        self._update_summary(user["historySummary"], user["recentTrips"])

        # Save updated history
        await self.save_history(history)

    def _archive_trip_to_summary(self, summary: Dict, trip: Dict):
        """Archive an old trip's data into the summary.

        Args:
            summary: historySummary dictionary
            trip: Trip to archive
        """
        # Add destination to favorites if not already there
        dest = trip["destination"]
        if dest not in summary.get("favoriteDestinations", []):
            if len(summary.get("favoriteDestinations", [])) < 10:
                summary.setdefault("favoriteDestinations", []).append(dest)

        # Extract and add preferences
        prefs = trip.get("preferences", "").split(",")
        for pref in prefs:
            pref = pref.strip().lower()
            if pref and pref not in summary.get("preferencePatterns", []):
                if len(summary.get("preferencePatterns", [])) < 20:
                    summary.setdefault("preferencePatterns", []).append(pref)

    def _update_summary(self, summary: Dict, recent_trips: List[Dict]):
        """Update summary statistics from recent trips.

        Args:
            summary: historySummary dictionary to update
            recent_trips: List of recent trip dictionaries
        """
        if not recent_trips:
            return

        # Update total trips count
        summary["totalTrips"] = summary.get("totalTrips", 0)

        # Calculate averages from recent trips
        ratings = [
            t.get("satisfaction_rating", 0)
            for t in recent_trips
            if t.get("satisfaction_rating", 0) > 0
        ]
        tokens = [
            t.get("token_usage", 0) for t in recent_trips if t.get("token_usage", 0) > 0
        ]
        latencies = [
            t.get("latency_ms", 0) for t in recent_trips if t.get("latency_ms", 0) > 0
        ]

        if ratings:
            summary["avgSatisfactionRating"] = round(sum(ratings) / len(ratings), 2)
        if tokens:
            summary["avgTokenUsage"] = int(sum(tokens) / len(tokens))
        if latencies:
            summary["avgLatencyMs"] = int(sum(latencies) / len(latencies))

        # Update favorite destinations from recent trips
        destinations = [t["destination"] for t in recent_trips]
        dest_counts = Counter(destinations)
        summary["favoriteDestinations"] = [
            dest for dest, _ in dest_counts.most_common(10)
        ]

        # Extract preference patterns
        all_prefs = []
        for trip in recent_trips:
            prefs = trip.get("preferences", "").lower().replace(",", " ").split()
            all_prefs.extend([p.strip() for p in prefs if p.strip()])

        pref_counts = Counter(all_prefs)
        summary["preferencePatterns"] = [
            pref for pref, _ in pref_counts.most_common(20)
        ]

        # Update timestamp
        summary["lastUpdated"] = datetime.now().isoformat()


# Global instance for easy access
_history_manager = None


def get_history_manager() -> UserHistoryManager:
    """Get or create the global user history manager instance.

    Returns:
        UserHistoryManager instance
    """
    global _history_manager
    if _history_manager is None:
        _history_manager = UserHistoryManager()
    return _history_manager
