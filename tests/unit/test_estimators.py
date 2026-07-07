"""Unit tests for token estimation (test-first development)."""
import pytest

from src.estimators import CharacterBasedEstimator


class TestCharacterBasedEstimator:
    """Tests for character-based token estimation."""

    @pytest.fixture
    def estimator(self):
        return CharacterBasedEstimator()

    def test_estimates_english_text(self, estimator):
        """Test estimation on normal English text."""
        # "This is a test" ≈ 14 chars = 3-4 tokens
        result = estimator.estimate("This is a test")
        assert result >= 3 and result <= 4

    def test_handles_empty_string(self, estimator):
        assert estimator.estimate("") == 0

    def test_handles_whitespace_only(self, estimator):
        assert estimator.estimate("   ") == 0

    def test_estimates_code(self, estimator):
        code = "def foo():\n    return 42"
        result = estimator.estimate(code)
        assert result > 0
        # ~24 chars = 6 tokens
        assert result >= 5 and result <= 7

    def test_estimates_long_text(self, estimator):
        text = "a" * 1000
        result = estimator.estimate(text)
        assert result >= 200 and result <= 300

    def test_consistency(self, estimator):
        """Same text should give same estimate."""
        text = "Hello world, this is a test"
        result1 = estimator.estimate(text)
        result2 = estimator.estimate(text)
        assert result1 == result2

    def test_proportional_to_text_length(self, estimator):
        """Longer text should estimate to more tokens."""
        short = "Hello"
        long = "Hello world this is a much longer text with more content"
        assert estimator.estimate(short) < estimator.estimate(long)

    def test_handles_special_characters(self, estimator):
        text = "!@#$%^&*()_+-=[]{}|;:',.<>?"
        result = estimator.estimate(text)
        assert result > 0

    def test_handles_unicode(self, estimator):
        text = "Hello 世界 🌍"
        result = estimator.estimate(text)
        assert result > 0

    def test_estimate_conversation_messages(self, estimator):
        """Test estimation of typical conversation messages."""
        short_msg = "What is Python?"
        result = estimator.estimate(short_msg)
        assert result >= 2 and result <= 5

        long_msg = "Write a Python function that takes a list of numbers and returns the sum of squares of all even numbers, with error handling for invalid input types"
        result = estimator.estimate(long_msg)
        assert result > estimator.estimate(short_msg)
