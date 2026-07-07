"""Unit tests for conversation analyzer (test-first development)."""
import pytest

from src.analyzer import ConversationAnalyzer, ConversationMetrics
from src.estimators import CharacterBasedEstimator
from src.patterns import PatternDetector


class TestConversationMetrics:
    """Tests for metrics data class."""

    def test_metrics_creation(self):
        metrics = ConversationMetrics(
            total_tokens=100,
            message_count=5,
            user_messages=2,
            assistant_messages=3,
        )
        assert metrics.total_tokens == 100
        assert metrics.message_count == 5
        assert metrics.user_messages == 2
        assert metrics.assistant_messages == 3

    def test_metrics_exchange_ratio(self):
        """Test calculation of exchange ratio."""
        metrics = ConversationMetrics(
            total_tokens=100,
            message_count=4,
            user_messages=2,
            assistant_messages=2,
        )
        assert metrics.exchange_ratio == 1.0  # 2:2 = 1:1


class TestConversationAnalyzer:
    """Tests for conversation analyzer."""

    @pytest.fixture
    def analyzer(self):
        estimator = CharacterBasedEstimator()
        detector = PatternDetector()
        return ConversationAnalyzer(estimator, detector)

    def test_analyze_single_conversation(self, analyzer, small_conversation_data):
        """Test analysis of single conversation."""
        from src.models import Conversation

        conv = Conversation.from_dict(small_conversation_data)
        metrics = analyzer.analyze_single(conv)

        assert metrics.total_tokens > 0
        assert metrics.message_count == 5
        assert metrics.user_messages == 3
        assert metrics.assistant_messages == 2

    def test_analyze_batch_aggregates_metrics(self, analyzer, small_conversation_data):
        """Test batch analysis aggregation."""
        from src.models import Conversation

        convs = [
            Conversation.from_dict(small_conversation_data),
            Conversation.from_dict(small_conversation_data),
        ]

        batch = analyzer.analyze_batch(convs)
        assert batch.total_conversations == 2
        assert batch.total_messages == 10
        assert batch.total_tokens > 0

    def test_analyze_empty_batch(self, analyzer):
        """Test handling of empty batch."""
        batch = analyzer.analyze_batch([])
        assert batch.total_conversations == 0
        assert batch.total_messages == 0

    def test_analyze_provides_pattern_insights(self, analyzer, long_conversation_data):
        """Test that analyzer detects patterns."""
        from src.models import Conversation

        conv = Conversation.from_dict(long_conversation_data)
        metrics = analyzer.analyze_single(conv)

        # Long conversation should be flagged
        assert metrics.has_long_conversation is True

    def test_message_type_counts(self, analyzer, code_heavy_conversation):
        """Test message type classification in analysis."""
        from src.models import Conversation

        conv = Conversation.from_dict(code_heavy_conversation)
        metrics = analyzer.analyze_single(conv)

        # Should have detected code messages
        assert metrics.code_message_count > 0
