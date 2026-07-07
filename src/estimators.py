"""Token estimation strategies."""
from abc import ABC, abstractmethod


class TokenEstimator(ABC):
    """Abstract base class for token estimation strategies."""

    @abstractmethod
    def estimate(self, text: str) -> int:
        """Estimate token count for given text.

        Args:
            text: Text to estimate.

        Returns:
            Estimated token count.
        """
        pass


class CharacterBasedEstimator(TokenEstimator):
    """Estimate tokens based on character count.

    Uses heuristic: 1 token ≈ 4 characters (English baseline).
    Fast but less accurate than ML-based estimation.
    """

    def __init__(self, chars_per_token: int = 4):
        """Initialize estimator.

        Args:
            chars_per_token: Characters per token (default 4 for English).
        """
        self.chars_per_token = chars_per_token

    def estimate(self, text: str) -> int:
        """Estimate tokens from character count.

        Args:
            text: Text to estimate.

        Returns:
            Estimated token count (integer).
        """
        if not text or not text.strip():
            return 0
        # Round up to nearest token
        char_count = len(text)
        return max(1, (char_count + self.chars_per_token - 1) // self.chars_per_token)
