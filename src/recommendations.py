"""Recommendation generation engine based on usage patterns."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import statistics

from src.analyzer import BatchMetrics


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class ExamplePrompt:
    """Example of a problematic prompt and its improvement."""

    current: str
    improved: str


@dataclass
class Recommendation:
    """A single recommendation."""

    priority: RecommendationPriority
    category: str
    issue: str
    impact: str
    recommendation: str
    action: str
    example: Optional[ExamplePrompt] = None


class RecommendationGenerator:
    """Generates personalized recommendations from metrics."""

    def generate(self, metrics: BatchMetrics) -> List[Recommendation]:
        """Generate recommendations from batch metrics.

        Args:
            metrics: Aggregated metrics from multiple conversations.

        Returns:
            List of recommendations.
        """
        recommendations = []

        # 1. Long conversation pattern
        if metrics.conversations_with_long_chains > 0:
            pct_long = (
                metrics.conversations_with_long_chains / metrics.total_conversations * 100
            )
            context_waste = metrics.total_tokens * 0.25  # Rough estimate

            recommendations.append(
                Recommendation(
                    priority=RecommendationPriority.HIGH,
                    category="Context Management",
                    issue=f"{metrics.conversations_with_long_chains} conversations exceed 40 messages",
                    impact=f"Estimated token waste: ~{int(context_waste):,} tokens ({pct_long:.0f}% of conversations)",
                    recommendation="Start new conversations when switching topics or reaching 30+ messages",
                    action="Split long conversations at natural topic boundaries. Each message includes full context history.",
                )
            )

        # 2. Short prompt pattern
        if metrics.conversations_with_short_prompts > 0:
            pct_short = (
                metrics.conversations_with_short_prompts / metrics.total_conversations * 100
            )

            recommendations.append(
                Recommendation(
                    priority=RecommendationPriority.MEDIUM,
                    category="Prompt Quality",
                    issue=f"{metrics.conversations_with_short_prompts} conversations with vague/short prompts ({pct_short:.0f}%)",
                    impact="Vague prompts lead to back-and-forth clarifications, wasting tokens",
                    recommendation="Provide context upfront: expected format, constraints, and examples",
                    action="Before prompting: Ask 'What details would help Claude understand this better?' Include: task, constraints, example output.",
                )
            )

        # 3. Clarification patterns
        if metrics.conversations_with_clarifications > 0:
            pct_clarif = (
                metrics.conversations_with_clarifications / metrics.total_conversations * 100
            )
            clarif_waste = metrics.total_tokens * 0.15  # Rough estimate

            recommendations.append(
                Recommendation(
                    priority=RecommendationPriority.MEDIUM,
                    category="Communication Efficiency",
                    issue=f"{metrics.conversations_with_clarifications} conversations show clarification loops ({pct_clarif:.0f}%)",
                    impact=f"Each clarification round doubles token usage. Estimated waste: ~{int(clarif_waste):,} tokens",
                    recommendation="Structure prompts: Context → Task → Constraints → Expected Output format",
                    action='Example: Instead of "optimize this", try "Optimize this Python function for speed (target <100ms) while maintaining readability. Return documented code."',
                )
            )

        # 4. Usage summary (always included)
        if metrics.total_conversations > 0:
            efficiency_multiplier = (
                metrics.total_tokens / (metrics.total_conversations * 5000)
                if metrics.total_conversations > 0
                else 1.0
            )

            if efficiency_multiplier > 2:
                benchmark = "higher than efficient usage patterns"
            else:
                benchmark = "within typical range"

            recommendations.append(
                Recommendation(
                    priority=RecommendationPriority.INFO,
                    category="Usage Summary",
                    issue=f"Average {metrics.avg_messages_per_conversation:.0f} messages, {metrics.avg_tokens_per_conversation:,.0f} tokens per conversation",
                    impact=f"Total: {metrics.total_tokens:,} tokens across {metrics.total_conversations} conversations",
                    recommendation=f"Your usage is {benchmark}. Benchmark: Efficient users average 5,000-10,000 tokens/conversation.",
                    action="Monitor the patterns above to reduce token usage while maintaining quality.",
                )
            )

        return recommendations

    def enhance_with_examples(self, recommendations: List[Recommendation], conversations: List) -> List[Recommendation]:
        """Enhance recommendations with real examples from conversations.

        Args:
            recommendations: List of recommendations to enhance.
            conversations: List of Conversation objects.

        Returns:
            Recommendations with examples added where applicable.
        """
        from src.patterns import PatternDetector
        from src.models import Role

        detector = PatternDetector()

        for rec in recommendations:
            if rec.category == "Prompt Quality":
                # Find a short prompt example
                for conv in conversations:
                    for msg in conv.messages:
                        if msg.role == Role.USER and detector.is_short_prompt(msg.content):
                            # Create an improved version
                            improved = self._improve_prompt(msg.content)
                            rec.example = ExamplePrompt(current=msg.content, improved=improved)
                            break
                    if rec.example:
                        break

            elif rec.category == "Communication Efficiency":
                # Find a clarification loop example
                for conv in conversations:
                    if detector.detect_clarification_loop(conv):
                        # Get the initial vague prompt
                        for i, msg in enumerate(conv.messages):
                            if msg.role == Role.USER and i > 0:
                                # Check if next message is assistant asking for clarification
                                if (
                                    i + 1 < len(conv.messages)
                                    and conv.messages[i + 1].role == Role.ASSISTANT
                                ):
                                    assistant_msg = conv.messages[i + 1].content.lower()
                                    if any(
                                        word in assistant_msg
                                        for word in ["clarify", "more", "details", "context", "understand"]
                                    ):
                                        improved = self._improve_prompt(msg.content)
                                        rec.example = ExamplePrompt(current=msg.content, improved=improved)
                                        break
                        if rec.example:
                            break

        return recommendations

    @staticmethod
    def _improve_prompt(vague_prompt: str) -> str:
        """Generate an improved version of a vague prompt.

        Args:
            vague_prompt: Original vague prompt.

        Returns:
            Improved prompt with more context and structure.
        """
        # Simple heuristics to improve prompts
        improved = vague_prompt.strip()

        # Add structure if missing
        if len(improved) < 30:
            # Very short prompt - needs more detail
            improved = f"{improved}. Please include: what you want, any constraints, and the expected format."

        # If it's a question without context, add context request
        if improved.endswith("?") and "?" not in improved[:-1]:
            improved = improved[:-1] + " in detail? Please provide examples if possible."

        return improved

    @staticmethod
    def rank(recommendations: List[Recommendation]) -> List[Recommendation]:
        """Rank recommendations by priority and impact.

        Args:
            recommendations: List of recommendations to rank.

        Returns:
            Ranked recommendations (high priority first).
        """
        priority_order = {
            RecommendationPriority.HIGH: 0,
            RecommendationPriority.MEDIUM: 1,
            RecommendationPriority.LOW: 2,
            RecommendationPriority.INFO: 3,
        }

        return sorted(recommendations, key=lambda r: priority_order[r.priority])
