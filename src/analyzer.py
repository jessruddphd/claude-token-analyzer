"""Core conversation analysis engine."""
from dataclasses import dataclass
from typing import List, Optional

from src.estimators import TokenEstimator
from src.models import Conversation
from src.patterns import PatternDetector, MessageType


@dataclass
class ConversationMetrics:
    """Metrics from analyzing a single conversation."""

    total_tokens: int
    message_count: int
    user_messages: int
    assistant_messages: int
    avg_message_length: float = 0.0
    has_clarifications: bool = False
    has_long_conversation: bool = False
    has_short_prompt_pattern: bool = False
    has_repetitive_questions: bool = False
    code_message_count: int = 0
    question_message_count: int = 0
    instruction_message_count: int = 0
    debugging_message_count: int = 0
    efficiency_score: float = 1.0

    @property
    def exchange_ratio(self) -> float:
        """Calculate user:assistant message ratio."""
        if self.assistant_messages == 0:
            return float(self.user_messages)
        return self.user_messages / self.assistant_messages


@dataclass
class BatchMetrics:
    """Aggregated metrics from analyzing multiple conversations."""

    total_conversations: int
    total_messages: int
    total_tokens: int
    avg_messages_per_conversation: float = 0.0
    avg_tokens_per_conversation: float = 0.0
    conversations_with_clarifications: int = 0
    conversations_with_long_chains: int = 0
    conversations_with_short_prompts: int = 0


class ConversationAnalyzer:
    """Analyzes conversations for patterns and metrics."""

    def __init__(self, token_estimator: TokenEstimator, pattern_detector: PatternDetector):
        """Initialize analyzer with dependencies.

        Args:
            token_estimator: Strategy for estimating token counts.
            pattern_detector: Strategy for detecting patterns.
        """
        self.estimator = token_estimator
        self.detector = pattern_detector

    def analyze_single(self, conversation: Conversation) -> ConversationMetrics:
        """Analyze a single conversation.

        Args:
            conversation: Conversation to analyze.

        Returns:
            ConversationMetrics with analysis results.
        """
        total_tokens = 0
        message_type_counts = {
            MessageType.CODE: 0,
            MessageType.QUESTION: 0,
            MessageType.INSTRUCTION: 0,
            MessageType.DEBUGGING: 0,
            MessageType.OTHER: 0,
        }

        # Calculate token counts and classify messages
        for msg in conversation.messages:
            tokens = self.estimator.estimate(msg.content)
            total_tokens += tokens

            msg_type = self.detector.classify_message_type(msg.content)
            message_type_counts[msg_type] += 1

        # Calculate average message length
        avg_msg_length = (
            conversation.total_content_length / conversation.message_count
            if conversation.message_count > 0
            else 0
        )

        # Detect patterns
        has_clarifications = self.detector.detect_clarification_loop(conversation)
        has_long_conv = self.detector.detect_long_conversation(conversation, threshold=40)
        has_short_prompts = self.detector.detect_short_prompt_pattern(conversation)
        has_repetitive = self.detector.detect_repetitive_questions(conversation)
        efficiency = self.detector.calculate_message_efficiency(conversation)

        return ConversationMetrics(
            total_tokens=total_tokens,
            message_count=conversation.message_count,
            user_messages=conversation.user_message_count,
            assistant_messages=conversation.assistant_message_count,
            avg_message_length=avg_msg_length,
            has_clarifications=has_clarifications,
            has_long_conversation=has_long_conv,
            has_short_prompt_pattern=has_short_prompts,
            has_repetitive_questions=has_repetitive,
            code_message_count=message_type_counts[MessageType.CODE],
            question_message_count=message_type_counts[MessageType.QUESTION],
            instruction_message_count=message_type_counts[MessageType.INSTRUCTION],
            debugging_message_count=message_type_counts[MessageType.DEBUGGING],
            efficiency_score=efficiency,
        )

    def analyze_batch(self, conversations: List[Conversation]) -> BatchMetrics:
        """Analyze multiple conversations.

        Args:
            conversations: List of conversations to analyze.

        Returns:
            BatchMetrics with aggregated results.
        """
        if not conversations:
            return BatchMetrics(
                total_conversations=0,
                total_messages=0,
                total_tokens=0,
            )

        # Analyze all conversations
        all_metrics = [self.analyze_single(conv) for conv in conversations]

        # Aggregate results
        total_messages = sum(m.message_count for m in all_metrics)
        total_tokens = sum(m.total_tokens for m in all_metrics)
        convs_with_clarifications = sum(1 for m in all_metrics if m.has_clarifications)
        convs_with_long = sum(1 for m in all_metrics if m.has_long_conversation)
        convs_with_short = sum(1 for m in all_metrics if m.has_short_prompt_pattern)

        avg_messages = total_messages / len(conversations) if conversations else 0
        avg_tokens = total_tokens / len(conversations) if conversations else 0

        return BatchMetrics(
            total_conversations=len(conversations),
            total_messages=total_messages,
            total_tokens=total_tokens,
            avg_messages_per_conversation=avg_messages,
            avg_tokens_per_conversation=avg_tokens,
            conversations_with_clarifications=convs_with_clarifications,
            conversations_with_long_chains=convs_with_long,
            conversations_with_short_prompts=convs_with_short,
        )
