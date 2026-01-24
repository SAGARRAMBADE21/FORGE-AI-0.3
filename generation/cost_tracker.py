# generation/cost_tracker.py
"""
Cost Tracker - Track and estimate LLM API costs.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Pricing per 1M tokens (input/output) - Updated January 2025
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic Claude
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # OpenRouter pricing (varies, using estimates)
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.40, "output": 0.40},
    "meta-llama/llama-3.1-8b-instruct": {"input": 0.05, "output": 0.05},
    "google/gemini-pro": {"input": 0.50, "output": 1.50},
    "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
    # Groq (free tier limits apply)
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    # Google Gemini Direct
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free experimental
    # Default for unknown models
    "default": {"input": 1.00, "output": 3.00},
}


@dataclass
class UsageRecord:
    """Single API usage record."""

    timestamp: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool = False
    operation: str = "generate"


@dataclass
class CostTracker:
    """
    Tracks LLM API usage and costs.

    Features:
    - Per-request cost tracking
    - Session and lifetime totals
    - Cost limits and alerts
    - Usage reports
    """

    storage_path: Path = field(
        default_factory=lambda: Path.home() / ".code_indexer" / "cost_tracking.json"
    )
    session_limit_usd: float = 10.0  # Default $10 per session limit
    lifetime_limit_usd: float = 100.0  # Default $100 lifetime limit

    # Runtime tracking
    records: List[UsageRecord] = field(default_factory=list)
    session_start: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize and load existing data."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        """Load existing usage data."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.records = [UsageRecord(**r) for r in data.get("records", [])]
                logger.debug(f"Loaded {len(self.records)} usage records")
            except Exception as e:
                logger.warning(f"Failed to load cost data: {e}")
                self.records = []

    def _save(self):
        """Save usage data to disk."""
        try:
            data = {
                "records": [asdict(r) for r in self.records],
                "last_updated": time.time(),
            }
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save cost data: {e}")

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model."""
        # Try exact match
        if model in MODEL_PRICING:
            return MODEL_PRICING[model]

        # Try partial match
        model_lower = model.lower()
        for known_model, pricing in MODEL_PRICING.items():
            if known_model.lower() in model_lower or model_lower in known_model.lower():
                return pricing

        # Default pricing
        return MODEL_PRICING["default"]

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a request.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self.get_model_pricing(model)

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached: bool = False,
        operation: str = "generate",
    ) -> UsageRecord:
        """
        Record API usage.

        Args:
            provider: API provider name
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            cached: Whether response was from cache
            operation: Type of operation

        Returns:
            The created usage record
        """
        cost = 0.0 if cached else self.estimate_cost(model, input_tokens, output_tokens)

        record = UsageRecord(
            timestamp=time.time(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            cached=cached,
            operation=operation,
        )

        self.records.append(record)
        self._save()

        # Check limits
        self._check_limits()

        return record

    def _check_limits(self):
        """Check if spending limits are exceeded."""
        session_total = self.get_session_total()
        lifetime_total = self.get_lifetime_total()

        if session_total >= self.session_limit_usd:
            logger.warning(
                f"⚠️ Session spending limit reached: ${session_total:.2f} / ${self.session_limit_usd:.2f}"
            )
        elif session_total >= self.session_limit_usd * 0.8:
            logger.info(
                f"Session spending at 80%: ${session_total:.2f} / ${self.session_limit_usd:.2f}"
            )

        if lifetime_total >= self.lifetime_limit_usd:
            logger.warning(
                f"⚠️ Lifetime spending limit reached: ${lifetime_total:.2f} / ${self.lifetime_limit_usd:.2f}"
            )

    def get_session_total(self) -> float:
        """Get total cost for current session."""
        return sum(
            r.cost_usd for r in self.records if r.timestamp >= self.session_start
        )

    def get_lifetime_total(self) -> float:
        """Get total lifetime cost."""
        return sum(r.cost_usd for r in self.records)

    def get_today_total(self) -> float:
        """Get total cost for today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        return sum(r.cost_usd for r in self.records if r.timestamp >= today_start)

    def get_usage_by_model(self) -> Dict[str, Dict[str, Any]]:
        """Get usage breakdown by model."""
        usage: Dict[str, Dict[str, Any]] = {}

        for record in self.records:
            if record.model not in usage:
                usage[record.model] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "cached_requests": 0,
                }

            usage[record.model]["requests"] += 1
            usage[record.model]["input_tokens"] += record.input_tokens
            usage[record.model]["output_tokens"] += record.output_tokens
            usage[record.model]["cost_usd"] += record.cost_usd
            if record.cached:
                usage[record.model]["cached_requests"] += 1

        return usage

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        total_requests = len(self.records)
        cached_requests = sum(1 for r in self.records if r.cached)

        return {
            "session_cost_usd": f"${self.get_session_total():.4f}",
            "today_cost_usd": f"${self.get_today_total():.4f}",
            "lifetime_cost_usd": f"${self.get_lifetime_total():.4f}",
            "total_requests": total_requests,
            "cached_requests": cached_requests,
            "cache_hit_rate": f"{(cached_requests / total_requests * 100) if total_requests > 0 else 0:.1f}%",
            "total_input_tokens": sum(r.input_tokens for r in self.records),
            "total_output_tokens": sum(r.output_tokens for r in self.records),
            "session_limit_usd": f"${self.session_limit_usd:.2f}",
            "lifetime_limit_usd": f"${self.lifetime_limit_usd:.2f}",
        }

    def reset_session(self):
        """Reset session tracking."""
        self.session_start = time.time()
        logger.info("Session cost tracking reset")

    def clear_history(self):
        """Clear all usage history."""
        self.records = []
        self._save()
        logger.info("Usage history cleared")


# Global tracker instance
_tracker: Optional[CostTracker] = None


def get_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
