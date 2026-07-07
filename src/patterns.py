"""Pattern detection in conversations for analysis and recommendations."""
import re
from collections import Counter
from enum import Enum
from typing import Dict
from difflib import SequenceMatcher

from src.models import Conversation, Role


class MessageType(Enum):
    """Classification of message content type."""

    CODE = "code"
    QUESTION = "question"
    INSTRUCTION = "instruction"
    DEBUGGING = "debugging"
    OTHER = "other"


class PatternDetector:
    """Detect inefficiency patterns in conversations."""

    def classify_message_type(self, content: str) -> MessageType:
        """Classify message type based on content.

        Args:
            content: Message content text.

        Returns:
            MessageType classification.
        """
        content_lower = content.lower()

        # Instruction detection (before code - higher priority)
        if re.search(
            r'\b(create|build|make|generate|write|implement|develop|design|refactor)\b',
            content_lower,
        ):
            # But check it's not asking about code syntax
            if not re.search(r'^(how|what|where|why|when).*(code|syntax|function)', content_lower):
                return MessageType.INSTRUCTION

        # Code detection
        if re.search(r'```|def |class |function|import |const |let |var |return ', content):
            return MessageType.CODE

        # Debugging detection
        if re.search(r'\b(error|issue|bug|fix|debug|broken|failed|exception)\b', content_lower):
            return MessageType.DEBUGGING

        # Question detection
        if content.rstrip().endswith("?") or re.search(r'\b(what|how|why|when|where|can you|could you|would you)\b', content_lower):
            return MessageType.QUESTION

        return MessageType.OTHER

    def is_short_prompt(self, content: str, threshold: int = 20) -> bool:
        """Check if message is very short (likely to need clarification).

        Args:
            content: Message content.
            threshold: Character threshold for "short" (default 20 characters).

        Returns:
            True if message is shorter than threshold.
        """
        return len(content) < threshold

    def detect_clarification_loop(self, conversation: Conversation) -> bool:
        """Detect pattern: user question → vague response → follow-up question.

        Args:
            conversation: Conversation to analyze.

        Returns:
            True if clarification loop pattern detected.
        """
        user_questions = 0
        assistant_clarification = 0

        for msg in conversation.messages:
            if msg.role == Role.USER:
                msg_type = self.classify_message_type(msg.content)
                if msg_type == MessageType.QUESTION:
                    user_questions += 1
            elif msg.role == Role.ASSISTANT:
                # Check if assistant is asking for clarification
                if re.search(
                    r'\b(clarify|more detail|more info|context|could you|can you provide)\b',
                    msg.content.lower(),
                ):
                    assistant_clarification += 1

        # Pattern: at least 2 user questions AND assistant requested clarification
        return user_questions >= 2 and assistant_clarification >= 1

    def detect_long_conversation(self, conversation: Conversation, threshold: int = 40) -> bool:
        """Detect conversations exceeding message threshold.

        Args:
            conversation: Conversation to analyze.
            threshold: Message count threshold (default 40).

        Returns:
            True if conversation exceeds threshold.
        """
        return conversation.message_count > threshold

    def detect_short_prompt_pattern(
        self, conversation: Conversation, short_threshold: int = 30
    ) -> bool:
        """Detect pattern: multiple short prompts requiring clarification.

        Args:
            conversation: Conversation to analyze.
            short_threshold: Character threshold for short message (default 30 chars).

        Returns:
            True if pattern detected.
        """
        short_prompts = 0
        assistant_requests_info = 0

        for msg in conversation.messages:
            if msg.role == Role.USER:
                # Check if this is a short user message
                if len(msg.content) < short_threshold:
                    short_prompts += 1
            elif msg.role == Role.ASSISTANT:
                # Check if assistant is asking for more info/clarification
                content_lower = msg.content.lower()
                if re.search(
                    r'(clarify|clarification|more (detail|info|context|explanation)|could you|can you|need|specify|specifically)',
                    content_lower,
                ):
                    assistant_requests_info += 1

        # Pattern: at least 1 short prompt AND at least 1 clarification request
        return short_prompts >= 1 and assistant_requests_info >= 1

    def detect_repetitive_questions(
        self, conversation: Conversation, similarity_threshold: float = 0.8
    ) -> bool:
        """Detect similar questions asked multiple times.

        Args:
            conversation: Conversation to analyze.
            similarity_threshold: Threshold for similarity matching (0-1).

        Returns:
            True if repetitive questions detected.
        """
        user_messages = [msg.content for msg in conversation.messages if msg.role == Role.USER]

        if len(user_messages) < 2:
            return False

        # Check all pairs for high similarity
        for i, msg1 in enumerate(user_messages):
            for msg2 in user_messages[i + 1 :]:
                similarity = SequenceMatcher(None, msg1, msg2).ratio()
                if similarity >= similarity_threshold:
                    return True

        return False

    def get_message_type_distribution(self, conversation: Conversation) -> Dict[MessageType, int]:
        """Get count of each message type in conversation.

        Args:
            conversation: Conversation to analyze.

        Returns:
            Dictionary with MessageType -> count mapping.
        """
        distribution = Counter()

        for msg in conversation.messages:
            msg_type = self.classify_message_type(msg.content)
            distribution[msg_type] += 1

        return dict(distribution)

    def calculate_message_efficiency(self, conversation: Conversation) -> float:
        """Calculate conversation efficiency score (0-1).

        Higher score = more efficient (fewer clarifications needed).

        Args:
            conversation: Conversation to analyze.

        Returns:
            Efficiency score between 0 and 1.
        """
        if conversation.message_count == 0:
            return 1.0

        # Factors that reduce efficiency
        efficiency_penalties = 0.0

        # Clarification loops reduce efficiency
        if self.detect_clarification_loop(conversation):
            efficiency_penalties += 0.3

        # Short prompts reduce efficiency
        if self.detect_short_prompt_pattern(conversation):
            efficiency_penalties += 0.2

        # Repetitive questions reduce efficiency
        if self.detect_repetitive_questions(conversation):
            efficiency_penalties += 0.2

        # Long conversations reduce efficiency (context overhead)
        if self.detect_long_conversation(conversation, threshold=40):
            efficiency_penalties += 0.15

        # Return score clamped to 0-1
        efficiency_score = max(0.0, 1.0 - efficiency_penalties)
        return min(1.0, efficiency_score)
