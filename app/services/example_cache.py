"""Example Cache for Travel Assistant.

This module implements an LRU (Least Recently Used) cache for few-shot examples
with intelligent re-ranking based on:
- User satisfaction scores
- Popularity (how often examples are used)
- Recency (when examples were added)

Bonus Feature 1: Advanced Example Selection
"""

import json
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ExampleCache:
    """LRU cache for few-shot examples with smart re-ranking.

    Features:
    - LRU eviction when cache is full
    - Re-ranking by weighted score: satisfaction + popularity + recency
    - Tracks usage statistics for each example
    - Persists cache to disk for durability
    """

    def __init__(
        self, max_size: int = 50, cache_file: str = "app/data/example_cache.json"
    ):
        """Initialize the example cache.

        Args:
            max_size: Maximum number of examples to cache
            cache_file: Path to persist cache data
        """
        self.max_size = max_size
        self.cache_file = Path(cache_file)
        self.cache: OrderedDict = OrderedDict()
        self.stats: Dict[str, Dict] = {}  # Usage statistics per example

        # Load existing cache if available
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk if exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    # Restore cache with OrderedDict
                    for key in data.get("cache_order", []):
                        if key in data.get("cache", {}):
                            self.cache[key] = data["cache"][key]
                    self.stats = data.get("stats", {})
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.cache = OrderedDict()
                self.stats = {}

    def _save_cache(self):
        """Persist cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "cache": dict(self.cache),
                "cache_order": list(self.cache.keys()),
                "stats": self.stats,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _generate_key(self, destination: str, preferences: str) -> str:
        """Generate cache key from destination and preferences.

        Args:
            destination: Travel destination
            preferences: User preferences

        Returns:
            Unique cache key
        """
        # Simple key: destination + first few words of preferences
        pref_words = preferences.lower().split()[:5]
        key = f"{destination.lower()}_{'_'.join(pref_words)}"
        return key

    def get(self, destination: str, preferences: str) -> Optional[List[Dict]]:
        """Retrieve examples from cache.

        Args:
            destination: Travel destination
            preferences: User preferences

        Returns:
            List of cached examples if found, None otherwise
        """
        key = self._generate_key(destination, preferences)

        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)

            # Update usage stats
            if key not in self.stats:
                self.stats[key] = {
                    "usage_count": 0,
                    "last_used": None,
                    "created_at": datetime.now().isoformat(),
                }

            self.stats[key]["usage_count"] += 1
            self.stats[key]["last_used"] = datetime.now().isoformat()

            self._save_cache()
            return self.cache[key]

        return None

    def put(
        self,
        destination: str,
        preferences: str,
        examples: List[Dict],
        satisfaction_score: float = 0.5,
    ):
        """Store examples in cache.

        Args:
            destination: Travel destination
            preferences: User preferences
            examples: Few-shot examples to cache
            satisfaction_score: User satisfaction (0.0-1.0), default 0.5
        """
        key = self._generate_key(destination, preferences)

        # Remove if already exists (will be re-added at end)
        if key in self.cache:
            del self.cache[key]

        # Add to cache
        self.cache[key] = examples

        # Initialize/update stats
        if key not in self.stats:
            self.stats[key] = {
                "usage_count": 0,
                "satisfaction_score": satisfaction_score,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
            }
        else:
            # Update satisfaction as running average
            current_score = self.stats[key].get("satisfaction_score", 0.5)
            count = self.stats[key]["usage_count"]
            new_score = (current_score * count + satisfaction_score) / (count + 1)
            self.stats[key]["satisfaction_score"] = new_score

        # Evict least recently used if over capacity
        if len(self.cache) > self.max_size:
            # Get least recently used key
            lru_key = next(iter(self.cache))
            del self.cache[lru_key]
            if lru_key in self.stats:
                del self.stats[lru_key]

        self._save_cache()

    def get_ranked_examples(
        self, destination: str, preferences: str, top_k: int = 5
    ) -> Tuple[List[Dict], Dict]:
        """Get examples ranked by composite score with ranking details.

        Re-ranks cached examples based on:
        - Satisfaction score (40% weight)
        - Popularity/usage count (30% weight)
        - Recency (30% weight)

        Args:
            destination: Travel destination
            preferences: User preferences
            top_k: Number of top examples to return

        Returns:
            Tuple of (List of top-ranked examples, ranking_info dict)
        """
        # Get examples from cache
        examples = self.get(destination, preferences)
        if not examples:
            return [], {}

        # Calculate composite scores for each example
        scored_examples = []
        current_time = time.time()

        for example in examples:
            # Get stats for this example's original cache key
            # For simplicity, use current key's stats
            key = self._generate_key(destination, preferences)
            stats = self.stats.get(key, {})

            # Satisfaction score (0.0-1.0)
            satisfaction = stats.get("satisfaction_score", 0.5)

            # Popularity score (normalize by max usage in cache)
            max_usage = max(
                [s.get("usage_count", 1) for s in self.stats.values()] or [1]
            )
            popularity = stats.get("usage_count", 0) / max_usage

            # Recency score (decay over 30 days)
            created_at = stats.get("created_at", datetime.now().isoformat())
            created_timestamp = datetime.fromisoformat(created_at).timestamp()
            age_days = (current_time - created_timestamp) / (60 * 60 * 24)
            recency = max(0.0, 1.0 - (age_days / 30.0))  # Linear decay over 30 days

            # Composite score (weighted)
            composite_score = 0.4 * satisfaction + 0.3 * popularity + 0.3 * recency

            scored_examples.append(
                {
                    "example": example,
                    "score": composite_score,
                    "breakdown": {
                        "satisfaction": round(satisfaction, 3),
                        "popularity": round(popularity, 3),
                        "recency": round(recency, 3),
                        "composite": round(composite_score, 3),
                    },
                }
            )

        # Sort by composite score (descending)
        scored_examples.sort(key=lambda x: x["score"], reverse=True)

        # Build ranking info
        ranking_info = {
            "total_examples_evaluated": len(scored_examples),
            "top_examples_selected": min(top_k, len(scored_examples)),
            "ranking_weights": {"satisfaction": 0.4, "popularity": 0.3, "recency": 0.3},
            "scores": [item["breakdown"] for item in scored_examples[:top_k]],
        }

        # Return top k examples and ranking info
        return [item["example"] for item in scored_examples[:top_k]], ranking_info

    def update_satisfaction(
        self, destination: str, preferences: str, satisfaction_score: float
    ):
        """Update satisfaction score for cached examples.

        Args:
            destination: Travel destination
            preferences: User preferences
            satisfaction_score: User satisfaction (0.0-1.0)
        """
        key = self._generate_key(destination, preferences)

        if key in self.stats:
            # Update as running average
            current_score = self.stats[key].get("satisfaction_score", 0.5)
            count = self.stats[key]["usage_count"]
            new_score = (current_score * count + satisfaction_score) / (count + 1)
            self.stats[key]["satisfaction_score"] = new_score
            self._save_cache()

    def clear(self):
        """Clear all cached examples."""
        self.cache.clear()
        self.stats.clear()
        self._save_cache()

    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "total_usage": sum(s.get("usage_count", 0) for s in self.stats.values()),
            "avg_satisfaction": sum(
                s.get("satisfaction_score", 0.5) for s in self.stats.values()
            )
            / len(self.stats)
            if self.stats
            else 0.0,
            "entries": [
                {
                    "key": key,
                    "usage_count": stats.get("usage_count", 0),
                    "satisfaction_score": stats.get("satisfaction_score", 0.5),
                    "created_at": stats.get("created_at"),
                    "last_used": stats.get("last_used"),
                }
                for key, stats in self.stats.items()
            ],
        }


# Global cache instance
example_cache = ExampleCache()
