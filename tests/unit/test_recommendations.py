"""Unit tests for recommendation generation."""
import pytest

from src.recommendations import Recommendation, RecommendationGenerator, RecommendationPriority
from src.analyzer import ConversationMetrics, BatchMetrics


class TestRecommendation:
    """Tests for recommendation model."""

    def test_recommendation_creation(self):
        rec = Recommendation(
            priority=RecommendationPriority.HIGH,
            category="Context Management",
            issue="Long conversations",
            impact="Token waste",
            recommendation="Start new conversations",
            action="Split at topic boundaries",
        )
        assert rec.priority == RecommendationPriority.HIGH
        assert rec.category == "Context Management"


class TestRecommendationGenerator:
    """Tests for recommendation generation."""

    @pytest.fixture
    def generator(self):
        return RecommendationGenerator()

    def test_no_recommendations_for_perfect_usage(self, generator):
        """Test that perfect usage generates no actionable recommendations."""
        metrics = BatchMetrics(
            total_conversations=2,
            total_messages=20,
            total_tokens=5000,
            avg_messages_per_conversation=10,
            conversations_with_clarifications=0,
            conversations_with_long_chains=0,
            conversations_with_short_prompts=0,
        )

        recs = generator.generate(metrics)
        actionable = [r for r in recs if r.priority != RecommendationPriority.INFO]
        assert len(actionable) == 0

    def test_recommends_context_management_for_long_convos(self, generator):
        """Test recommendation for long conversation pattern."""
        metrics = BatchMetrics(
            total_conversations=5,
            total_messages=250,  # 50 messages per conversation average
            total_tokens=50000,
            avg_messages_per_conversation=50,
            conversations_with_long_chains=3,
            conversations_with_clarifications=0,
            conversations_with_short_prompts=0,
        )

        recs = generator.generate(metrics)
        context_recs = [r for r in recs if r.category == "Context Management"]
        assert len(context_recs) > 0
        assert context_recs[0].priority == RecommendationPriority.HIGH

    def test_recommends_prompt_quality_for_short_prompts(self, generator):
        """Test recommendation for short prompt pattern."""
        metrics = BatchMetrics(
            total_conversations=5,
            total_messages=50,
            total_tokens=10000,
            avg_messages_per_conversation=10,
            conversations_with_clarifications=0,
            conversations_with_long_chains=0,
            conversations_with_short_prompts=4,
        )

        recs = generator.generate(metrics)
        quality_recs = [r for r in recs if r.category == "Prompt Quality"]
        assert len(quality_recs) > 0

    def test_recommends_clarification_pattern(self, generator):
        """Test recommendation for clarification patterns."""
        metrics = BatchMetrics(
            total_conversations=5,
            total_messages=100,
            total_tokens=20000,
            avg_messages_per_conversation=20,
            conversations_with_clarifications=3,
            conversations_with_long_chains=0,
            conversations_with_short_prompts=0,
        )

        recs = generator.generate(metrics)
        comm_recs = [r for r in recs if r.category == "Communication Efficiency"]
        assert len(comm_recs) > 0

    def test_includes_usage_summary(self, generator):
        """Test that usage summary is always included."""
        metrics = BatchMetrics(
            total_conversations=10,
            total_messages=100,
            total_tokens=25000,
            avg_messages_per_conversation=10,
        )

        recs = generator.generate(metrics)
        summary_recs = [r for r in recs if r.priority == RecommendationPriority.INFO]
        assert len(summary_recs) > 0

    def test_ranking_by_priority(self, generator):
        """Test that recommendations are ranked by priority."""
        metrics = BatchMetrics(
            total_conversations=10,
            total_messages=150,
            total_tokens=50000,
            avg_messages_per_conversation=15,
            conversations_with_long_chains=5,
            conversations_with_clarifications=3,
            conversations_with_short_prompts=4,
        )

        recs = generator.generate(metrics)
        ranked = generator.rank(recs)

        # High priority should come first
        if any(r.priority == RecommendationPriority.HIGH for r in ranked):
            high_idx = next(
                i for i, r in enumerate(ranked) if r.priority == RecommendationPriority.HIGH
            )
            medium_indices = [
                i for i, r in enumerate(ranked) if r.priority == RecommendationPriority.MEDIUM
            ]
            if medium_indices:
                assert high_idx < min(medium_indices)

    def test_recommendations_are_actionable(self, generator):
        """Test that recommendations include specific actions."""
        metrics = BatchMetrics(
            total_conversations=5,
            total_messages=100,
            total_tokens=25000,
            avg_messages_per_conversation=20,
            conversations_with_long_chains=3,
        )

        recs = generator.generate(metrics)
        high_priority_recs = [r for r in recs if r.priority == RecommendationPriority.HIGH]

        for rec in high_priority_recs:
            assert len(rec.action) > 10  # Should have meaningful action
            assert len(rec.recommendation) > 10
