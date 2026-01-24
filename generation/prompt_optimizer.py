# generation/prompt_optimizer.py
"""
Prompt Optimizer - Reduces token usage while maintaining prompt quality.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of prompt optimization."""

    original_length: int
    optimized_length: int
    reduction_percent: float
    optimized_text: str


class PromptOptimizer:
    """
    Optimizes prompts to reduce token usage and API costs.

    Techniques:
    - Whitespace normalization
    - Redundant phrase removal
    - Abbreviation substitution
    - Comment stripping in code samples
    """

    # Common abbreviations that LLMs understand
    ABBREVIATIONS: Dict[str, str] = {
        "implementation": "impl",
        "configuration": "config",
        "authentication": "auth",
        "authorization": "authz",
        "application": "app",
        "database": "db",
        "function": "func",
        "parameter": "param",
        "parameters": "params",
        "environment": "env",
        "development": "dev",
        "production": "prod",
        "repository": "repo",
        "initialize": "init",
        "information": "info",
        "documentation": "docs",
        "specification": "spec",
        "specifications": "specs",
        "requirements": "reqs",
    }

    # Phrases that can be shortened
    PHRASE_SHORTCUTS: Dict[str, str] = {
        "please make sure to": "ensure",
        "you should always": "always",
        "it is important to": "important:",
        "you need to make sure": "ensure",
        "please note that": "note:",
        "for example,": "e.g.,",
        "in order to": "to",
        "as well as": "and",
        "a lot of": "many",
        "make sure that": "ensure",
        "in addition to": "also",
        "with respect to": "regarding",
        "on the other hand": "however",
    }

    def __init__(self, aggressive: bool = False):
        """
        Initialize the optimizer.

        Args:
            aggressive: If True, apply more aggressive optimizations
        """
        self.aggressive = aggressive
        self.stats = {
            "prompts_optimized": 0,
            "total_chars_saved": 0,
            "total_original_chars": 0,
        }

    def optimize(self, text: str) -> OptimizationResult:
        """
        Optimize a prompt for reduced token usage.

        Args:
            text: Original prompt text

        Returns:
            OptimizationResult with optimized text and stats
        """
        original_length = len(text)
        optimized = text

        # Apply optimizations in order
        optimized = self._normalize_whitespace(optimized)
        optimized = self._apply_phrase_shortcuts(optimized)

        if self.aggressive:
            optimized = self._apply_abbreviations(optimized)
            optimized = self._strip_code_comments(optimized)

        # Final whitespace cleanup
        optimized = self._final_cleanup(optimized)

        optimized_length = len(optimized)
        reduction = (
            ((original_length - optimized_length) / original_length * 100)
            if original_length > 0
            else 0
        )

        # Update stats
        self.stats["prompts_optimized"] += 1
        self.stats["total_chars_saved"] += original_length - optimized_length
        self.stats["total_original_chars"] += original_length

        if reduction > 5:
            logger.debug(
                f"Prompt optimized: {reduction:.1f}% reduction ({original_length} → {optimized_length} chars)"
            )

        return OptimizationResult(
            original_length=original_length,
            optimized_length=optimized_length,
            reduction_percent=reduction,
            optimized_text=optimized,
        )

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize excessive whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing whitespace on lines
        text = re.sub(r" +\n", "\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def _apply_phrase_shortcuts(self, text: str) -> str:
        """Replace verbose phrases with shorter alternatives."""
        for phrase, shortcut in self.PHRASE_SHORTCUTS.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            text = pattern.sub(shortcut, text)
        return text

    def _apply_abbreviations(self, text: str) -> str:
        """Apply common abbreviations (aggressive mode only)."""
        for word, abbrev in self.ABBREVIATIONS.items():
            # Only replace standalone words, not parts of words
            pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
            text = pattern.sub(abbrev, text)
        return text

    def _strip_code_comments(self, text: str) -> str:
        """Remove comments from code blocks (aggressive mode only)."""
        # Remove single-line comments in code blocks
        # Be careful not to remove important ones

        # Pattern for code blocks
        code_block_pattern = r"```[\w]*\n(.*?)```"

        def strip_comments(match):
            code = match.group(1)
            # Remove obvious filler comments but keep important ones
            code = re.sub(
                r"^\s*//\s*(TODO|FIXME|NOTE|IMPORTANT).*$", "", code, flags=re.MULTILINE
            )
            code = re.sub(
                r"^\s*#\s*(TODO|FIXME|NOTE|IMPORTANT).*$", "", code, flags=re.MULTILINE
            )
            return f"```\n{code}```"

        return re.sub(code_block_pattern, strip_comments, text, flags=re.DOTALL)

    def _final_cleanup(self, text: str) -> str:
        """Final cleanup pass."""
        # Remove empty lines at start/end
        text = text.strip()

        # Normalize list markers
        text = re.sub(r"^- +", "- ", text, flags=re.MULTILINE)
        text = re.sub(r"^\* +", "- ", text, flags=re.MULTILINE)

        return text

    def optimize_system_prompt(self, text: str) -> str:
        """
        Optimize a system prompt (less aggressive).

        System prompts are reused, so optimization is important.
        """
        result = self.optimize(text)
        return result.optimized_text

    def optimize_user_prompt(self, text: str) -> str:
        """
        Optimize a user prompt.

        User prompts change frequently, optimization is less critical
        but still useful.
        """
        result = self.optimize(text)
        return result.optimized_text

    def get_stats(self) -> Dict:
        """Get optimization statistics."""
        total_original = self.stats["total_original_chars"]
        total_saved = self.stats["total_chars_saved"]

        return {
            "prompts_optimized": self.stats["prompts_optimized"],
            "total_chars_saved": total_saved,
            "average_reduction_percent": (
                (total_saved / total_original * 100) if total_original > 0 else 0
            ),
        }


# Global optimizer instance
_optimizer: PromptOptimizer | None = None


def get_optimizer(aggressive: bool = False) -> PromptOptimizer:
    """Get the global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PromptOptimizer(aggressive=aggressive)
    return _optimizer


def optimize_prompt(text: str, aggressive: bool = False) -> str:
    """Convenience function to optimize a prompt."""
    optimizer = get_optimizer(aggressive)
    return optimizer.optimize(text).optimized_text
