"""Token budgeting for context."""

from dataclasses import dataclass

from core.utils import count_tokens


@dataclass
class TokenBudget:
    """Token budget allocation."""
    total: int = 8000
    search_results: int = 4000
    current_file: int = 2000
    related_files: int = 1500
    system: int = 500


class TokenBudgeter:
    """Manage token budget for context building."""

    def __init__(self, budget: TokenBudget | None = None):
        self.budget = budget or TokenBudget()
        self._used = 0

    def reset(self):
        """Reset used tokens."""
        self._used = 0

    @property
    def remaining(self) -> int:
        """Get remaining tokens."""
        return self.budget.total - self._used

    def can_fit(self, text: str) -> bool:
        """Check if text fits in remaining budget."""
        return count_tokens(text) <= self.remaining

    def allocate(self, text: str) -> bool:
        """Try to allocate tokens for text."""
        tokens = count_tokens(text)
        if tokens <= self.remaining:
            self._used += tokens
            return True
        return False

    def truncate_to_fit(self, text: str, max_tokens: int | None = None) -> str:
        """Truncate text to fit in budget."""
        from core.utils import truncate_tokens
        
        limit = min(max_tokens or self.remaining, self.remaining)
        return truncate_tokens(text, limit)

    def get_allocation(self, category: str) -> int:
        """Get token allocation for category."""
        allocations = {
            "search": self.budget.search_results,
            "current": self.budget.current_file,
            "related": self.budget.related_files,
            "system": self.budget.system,
        }
        return allocations.get(category, 0)