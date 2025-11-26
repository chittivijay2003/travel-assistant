"""Metrics Tracker for Travel Assistant.

This module tracks API call metrics including:
- Request count
- Token usage
- Latency
- User activity
- Error rates

Bonus Feature 2: Analytics Dashboard Backend
"""

import json
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class MetricsTracker:
    """Thread-safe metrics tracker for API analytics.

    Tracks:
    - API call counts and success rates
    - Token usage per endpoint and user
    - Latency distribution
    - User activity patterns
    - Error rates and types
    """

    def __init__(self, metrics_file: str = "app/data/metrics.json"):
        """Initialize the metrics tracker.

        Args:
            metrics_file: Path to persist metrics data
        """
        self.metrics_file = Path(metrics_file)
        self.lock = asyncio.Lock()

        # Real-time metrics (in-memory)
        self.requests: List[Dict] = []
        self.aggregates: Dict = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
            "errors": 0,
            "by_user": defaultdict(
                lambda: {"requests": 0, "tokens": 0, "latency_ms": 0}
            ),
            "by_endpoint": defaultdict(
                lambda: {"requests": 0, "tokens": 0, "latency_ms": 0, "errors": 0}
            ),
            "by_hour": defaultdict(
                lambda: {"requests": 0, "tokens": 0, "latency_ms": 0}
            ),
        }

        # Load existing metrics if available
        # Note: Initial load is sync, subsequent saves are async
        self._load_metrics_sync()

    def _load_metrics_sync(self):
        """Load metrics from disk if exists (sync version for init)."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    data = json.load(f)
                    self.requests = data.get("requests", [])[-1000:]  # Keep last 1000

                    # Restore aggregates
                    agg_data = data.get("aggregates", {})
                    self.aggregates["total_requests"] = agg_data.get(
                        "total_requests", 0
                    )
                    self.aggregates["total_tokens"] = agg_data.get("total_tokens", 0)
                    self.aggregates["total_latency_ms"] = agg_data.get(
                        "total_latency_ms", 0
                    )
                    self.aggregates["errors"] = agg_data.get("errors", 0)

                    # Restore nested aggregates
                    for key in ["by_user", "by_endpoint", "by_hour"]:
                        if key in agg_data:
                            for sub_key, values in agg_data[key].items():
                                self.aggregates[key][sub_key] = values

            except Exception as e:
                print(f"Error loading metrics: {e}")

    def _save_metrics_sync(self):
        """Persist metrics to disk (sync helper)."""
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert defaultdicts to regular dicts for JSON serialization
            data = {
                "requests": self.requests[-1000:],  # Keep last 1000
                "aggregates": {
                    "total_requests": self.aggregates["total_requests"],
                    "total_tokens": self.aggregates["total_tokens"],
                    "total_latency_ms": self.aggregates["total_latency_ms"],
                    "errors": self.aggregates["errors"],
                    "by_user": dict(self.aggregates["by_user"]),
                    "by_endpoint": dict(self.aggregates["by_endpoint"]),
                    "by_hour": dict(self.aggregates["by_hour"]),
                },
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving metrics: {e}")

    async def _save_metrics(self):
        """Persist metrics to disk (async, non-blocking)."""
        await asyncio.to_thread(self._save_metrics_sync)

    async def track_request(
        self,
        endpoint: str,
        user_id: str,
        token_usage: Dict[str, int],
        latency_ms: int,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """Track an API request.

        Args:
            endpoint: API endpoint called
            user_id: User ID making the request
            token_usage: Dictionary with prompt_tokens, completion_tokens, total_tokens
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            error: Error message if failed
        """
        async with self.lock:
            timestamp = datetime.now().isoformat()
            hour_key = datetime.now().strftime("%Y-%m-%d_%H")

            # Create request record
            request_record = {
                "timestamp": timestamp,
                "endpoint": endpoint,
                "user_id": user_id,
                "token_usage": token_usage,
                "latency_ms": latency_ms,
                "success": success,
                "error": error,
            }

            self.requests.append(request_record)

            # Update aggregates
            self.aggregates["total_requests"] += 1
            self.aggregates["total_tokens"] += token_usage.get("total_tokens", 0)
            self.aggregates["total_latency_ms"] += latency_ms

            if not success:
                self.aggregates["errors"] += 1

            # By user
            self.aggregates["by_user"][user_id]["requests"] += 1
            self.aggregates["by_user"][user_id]["tokens"] += token_usage.get(
                "total_tokens", 0
            )
            self.aggregates["by_user"][user_id]["latency_ms"] += latency_ms

            # By endpoint
            self.aggregates["by_endpoint"][endpoint]["requests"] += 1
            self.aggregates["by_endpoint"][endpoint]["tokens"] += token_usage.get(
                "total_tokens", 0
            )
            self.aggregates["by_endpoint"][endpoint]["latency_ms"] += latency_ms
            if not success:
                self.aggregates["by_endpoint"][endpoint]["errors"] += 1

            # By hour
            self.aggregates["by_hour"][hour_key]["requests"] += 1
            self.aggregates["by_hour"][hour_key]["tokens"] += token_usage.get(
                "total_tokens", 0
            )
            self.aggregates["by_hour"][hour_key]["latency_ms"] += latency_ms

            # Persist every 10 requests
            if self.aggregates["total_requests"] % 10 == 0:
                await self._save_metrics()

    async def get_summary(self, hours: int = 24) -> Dict:
        """Get metrics summary for the last N hours.

        Args:
            hours: Number of hours to include (default 24)

        Returns:
            Dictionary with summary statistics
        """
        async with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Filter recent requests
            recent_requests = [
                r
                for r in self.requests
                if datetime.fromisoformat(r["timestamp"]) > cutoff_time
            ]

            if not recent_requests:
                return {
                    "total_requests": 0,
                    "success_rate": 0.0,
                    "total_tokens": 0,
                    "avg_latency_ms": 0,
                    "error_count": 0,
                }

            # Calculate summary
            total_requests = len(recent_requests)
            successful_requests = sum(1 for r in recent_requests if r["success"])
            total_tokens = sum(
                r["token_usage"].get("total_tokens", 0) for r in recent_requests
            )
            total_latency = sum(r["latency_ms"] for r in recent_requests)
            error_count = total_requests - successful_requests

            return {
                "total_requests": total_requests,
                "success_rate": successful_requests / total_requests
                if total_requests > 0
                else 0.0,
                "total_tokens": total_tokens,
                "avg_tokens_per_request": total_tokens / total_requests
                if total_requests > 0
                else 0,
                "avg_latency_ms": total_latency / total_requests
                if total_requests > 0
                else 0,
                "error_count": error_count,
                "time_period_hours": hours,
            }

    async def get_user_stats(self, user_id: str) -> Dict:
        """Get statistics for a specific user.

        Args:
            user_id: User ID to get stats for

        Returns:
            Dictionary with user statistics
        """
        async with self.lock:
            user_data = self.aggregates["by_user"].get(
                user_id, {"requests": 0, "tokens": 0, "latency_ms": 0}
            )

            if user_data["requests"] == 0:
                return {
                    "user_id": user_id,
                    "total_requests": 0,
                    "total_tokens": 0,
                    "avg_latency_ms": 0,
                }

            return {
                "user_id": user_id,
                "total_requests": user_data["requests"],
                "total_tokens": user_data["tokens"],
                "avg_latency_ms": user_data["latency_ms"] / user_data["requests"],
            }

    async def get_hourly_breakdown(self, hours: int = 24) -> List[Dict]:
        """Get hourly breakdown of metrics.

        Args:
            hours: Number of hours to include (default 24)

        Returns:
            List of hourly metrics
        """
        async with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)

            hourly_data = []
            for hour_key, data in sorted(self.aggregates["by_hour"].items()):
                hour_time = datetime.strptime(hour_key, "%Y-%m-%d_%H")
                if hour_time > cutoff_time:
                    hourly_data.append(
                        {
                            "hour": hour_key,
                            "requests": data["requests"],
                            "tokens": data["tokens"],
                            "avg_latency_ms": data["latency_ms"] / data["requests"]
                            if data["requests"] > 0
                            else 0,
                        }
                    )

            return hourly_data

    async def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data.

        Returns:
            Dictionary with all dashboard data
        """
        async with self.lock:
            # Get 24h summary inline
            cutoff_24h = datetime.now() - timedelta(hours=24)
            recent_requests_24h = [
                r
                for r in self.requests
                if datetime.fromisoformat(r["timestamp"]) > cutoff_24h
            ]

            if recent_requests_24h:
                total_requests_24h = len(recent_requests_24h)
                successful_24h = sum(1 for r in recent_requests_24h if r["success"])
                total_tokens_24h = sum(
                    r["token_usage"].get("total_tokens", 0) for r in recent_requests_24h
                )
                total_latency_24h = sum(r["latency_ms"] for r in recent_requests_24h)
                summary_24h = {
                    "total_requests": total_requests_24h,
                    "success_rate": successful_24h / total_requests_24h
                    if total_requests_24h > 0
                    else 0.0,
                    "total_tokens": total_tokens_24h,
                    "avg_tokens_per_request": total_tokens_24h / total_requests_24h
                    if total_requests_24h > 0
                    else 0,
                    "avg_latency_ms": total_latency_24h / total_requests_24h
                    if total_requests_24h > 0
                    else 0,
                    "error_count": total_requests_24h - successful_24h,
                    "time_period_hours": 24,
                }
            else:
                summary_24h = {
                    "total_requests": 0,
                    "success_rate": 0.0,
                    "total_tokens": 0,
                    "avg_latency_ms": 0,
                    "error_count": 0,
                    "time_period_hours": 24,
                }

            # Get 1h summary inline
            cutoff_1h = datetime.now() - timedelta(hours=1)
            recent_requests_1h = [
                r
                for r in self.requests
                if datetime.fromisoformat(r["timestamp"]) > cutoff_1h
            ]

            if recent_requests_1h:
                total_requests_1h = len(recent_requests_1h)
                successful_1h = sum(1 for r in recent_requests_1h if r["success"])
                total_tokens_1h = sum(
                    r["token_usage"].get("total_tokens", 0) for r in recent_requests_1h
                )
                total_latency_1h = sum(r["latency_ms"] for r in recent_requests_1h)
                summary_1h = {
                    "total_requests": total_requests_1h,
                    "success_rate": successful_1h / total_requests_1h
                    if total_requests_1h > 0
                    else 0.0,
                    "total_tokens": total_tokens_1h,
                    "avg_tokens_per_request": total_tokens_1h / total_requests_1h
                    if total_requests_1h > 0
                    else 0,
                    "avg_latency_ms": total_latency_1h / total_requests_1h
                    if total_requests_1h > 0
                    else 0,
                    "error_count": total_requests_1h - successful_1h,
                    "time_period_hours": 1,
                }
            else:
                summary_1h = {
                    "total_requests": 0,
                    "success_rate": 0.0,
                    "total_tokens": 0,
                    "avg_latency_ms": 0,
                    "error_count": 0,
                    "time_period_hours": 1,
                }

            # Get hourly breakdown inline
            hourly_data = []
            for hour_key, data in sorted(self.aggregates["by_hour"].items()):
                hour_time = datetime.strptime(hour_key, "%Y-%m-%d_%H")
                if hour_time > cutoff_24h:
                    hourly_data.append(
                        {
                            "hour": hour_key,
                            "requests": data["requests"],
                            "tokens": data["tokens"],
                            "avg_latency_ms": data["latency_ms"] / data["requests"]
                            if data["requests"] > 0
                            else 0,
                        }
                    )

            # Get top users
            top_users = sorted(
                [
                    {
                        "user_id": user_id,
                        "requests": data["requests"],
                        "tokens": data["tokens"],
                    }
                    for user_id, data in self.aggregates["by_user"].items()
                ],
                key=lambda x: x["requests"],
                reverse=True,
            )[:10]

            # Get endpoint stats
            endpoint_stats = [
                {
                    "endpoint": endpoint,
                    "requests": data["requests"],
                    "tokens": data["tokens"],
                    "avg_latency_ms": data["latency_ms"] / data["requests"]
                    if data["requests"] > 0
                    else 0,
                    "error_rate": data["errors"] / data["requests"]
                    if data["requests"] > 0
                    else 0,
                }
                for endpoint, data in self.aggregates["by_endpoint"].items()
            ]

            return {
                "summary_24h": summary_24h,
                "summary_1h": summary_1h,
                "hourly_breakdown": hourly_data,
                "top_users": top_users,
                "endpoint_stats": endpoint_stats,
                "overall": {
                    "total_requests": self.aggregates["total_requests"],
                    "total_tokens": self.aggregates["total_tokens"],
                    "total_errors": self.aggregates["errors"],
                    "avg_latency_ms": self.aggregates["total_latency_ms"]
                    / self.aggregates["total_requests"]
                    if self.aggregates["total_requests"] > 0
                    else 0,
                },
            }

    async def reset(self):
        """Reset all metrics."""
        async with self.lock:
            self.requests.clear()
            self.aggregates = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_latency_ms": 0,
                "errors": 0,
                "by_user": defaultdict(
                    lambda: {"requests": 0, "tokens": 0, "latency_ms": 0}
                ),
                "by_endpoint": defaultdict(
                    lambda: {"requests": 0, "tokens": 0, "latency_ms": 0, "errors": 0}
                ),
                "by_hour": defaultdict(
                    lambda: {"requests": 0, "tokens": 0, "latency_ms": 0}
                ),
            }
            await self._save_metrics()

    async def get_latest_scenario_data(self) -> Dict:
        """Get scenario comparison data from the most recent travel-assistant request.

        Returns:
            Dictionary with scenario comparison metrics or empty dict if none found
        """
        async with self.lock:
            # Find most recent travel-assistant request with scenario data
            for request in reversed(self.requests):
                if request.get(
                    "endpoint"
                ) == "/travel-assistant" and "scenarios" in request.get(
                    "token_usage", {}
                ):
                    scenarios = request["token_usage"]["scenarios"]
                    return {
                        "has_data": True,
                        "timestamp": request.get("timestamp"),
                        "user_id": request.get("user_id"),
                        "scenario_1_no_history": scenarios.get("scenario_1_no_history"),
                        "scenario_2_all_history": scenarios.get(
                            "scenario_2_all_history"
                        ),
                        "scenario_3_smart_history": scenarios.get(
                            "scenario_3_smart_history"
                        ),
                        "tokens_saved": scenarios.get("tokens_saved"),
                        "savings_percentage": scenarios.get("savings_percentage"),
                    }

            return {"has_data": False, "message": "No scenario data available yet"}


# Global metrics tracker instance
metrics_tracker = MetricsTracker()
