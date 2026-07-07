"""Unit tests for pattern detection (test-first development)."""
import pytest

from src.models import Conversation, Message, Role
from src.patterns import PatternDetector, MessageType


class TestMessageType:
    """Tests for message type classification."""

    def test_message_type_enum_values(self):
        assert MessageType.CODE.value == "code"
        assert MessageType.QUESTION.value == "question"
        assert MessageType.INSTRUCTION.value == "instruction"
        assert MessageType.DEBUGGING.value == "debugging"
        assert MessageType.OTHER.value == "other"


class TestPatternDetector:
    """Tests for pattern detection in conversations."""

    @pytest.fixture
    def detector(self):
        return PatternDetector()

    def test_classifies_code_message(self, detector):
        """Test code message classification."""
        assert detector.classify_message_type("def foo(): pass") == MessageType.CODE
        assert detector.classify_message_type("```python\nprint('hi')\n```") == MessageType.CODE
        assert detector.classify_message_type("import numpy") == MessageType.CODE
        assert detector.classify_message_type("class Foo: pass") == MessageType.CODE

    def test_classifies_question_message(self, detector):
        """Test question message classification."""
        assert detector.classify_message_type("What is Python?") == MessageType.QUESTION
        assert detector.classify_message_type("How do I optimize this?") == MessageType.QUESTION
        assert detector.classify_message_type("Why is this slow?") == MessageType.QUESTION
        assert detector.classify_message_type("Can you help?") == MessageType.QUESTION

    def test_classifies_instruction_message(self, detector):
        """Test instruction/request message classification."""
        assert detector.classify_message_type("Write a function that...") == MessageType.INSTRUCTION
        assert detector.classify_message_type("Create a new API endpoint") == MessageType.INSTRUCTION
        assert detector.classify_message_type("Generate a test for this") == MessageType.INSTRUCTION
        assert detector.classify_message_type("Build a dashboard with...") == MessageType.INSTRUCTION

    def test_classifies_debugging_message(self, detector):
        """Test debugging/problem message classification."""
        assert detector.classify_message_type("I'm getting an error: ...") == MessageType.DEBUGGING
        assert detector.classify_message_type("This code is broken") == MessageType.DEBUGGING
        assert detector.classify_message_type("Fix this bug") == MessageType.DEBUGGING
        assert detector.classify_message_type("Debug this issue") == MessageType.DEBUGGING

    def test_classifies_other_message(self, detector):
        """Test fallback classification."""
        assert detector.classify_message_type("This is fine") == MessageType.OTHER
        assert detector.classify_message_type("Looks good") == MessageType.OTHER

    def test_classifies_short_prompts(self, detector):
        """Test short prompts are detected."""
        short = "Optimize?"
        assert detector.is_short_prompt(short)

        long = "Can you help me optimize this function for better performance?"
        assert not detector.is_short_prompt(long)

    def test_detects_clarification_loop(self, detector, clarification_pattern_conversation):
        """Test detection of clarification patterns."""
        conv = Conversation.from_dict(clarification_pattern_conversation)
        result = detector.detect_clarification_loop(conv)
        assert result is True

    def test_no_clarification_in_linear_conversation(self, detector, small_conversation_data):
        """Test that linear conversations don't trigger clarification detection."""
        conv = Conversation.from_dict(small_conversation_data)
        result = detector.detect_clarification_loop(conv)
        assert result is False

    def test_detects_long_conversation(self, detector, long_conversation_data):
        """Test detection of long conversations."""
        conv = Conversation.from_dict(long_conversation_data)
        result = detector.detect_long_conversation(conv, threshold=40)
        assert result is True

    def test_no_detection_for_short_conversation(self, detector, small_conversation_data):
        """Test that short conversations pass the threshold."""
        conv = Conversation.from_dict(small_conversation_data)
        result = detector.detect_long_conversation(conv, threshold=40)
        assert result is False

    def test_message_type_distribution(self, detector, code_heavy_conversation):
        """Test calculation of message type distribution."""
        conv = Conversation.from_dict(code_heavy_conversation)
        distribution = detector.get_message_type_distribution(conv)

        assert distribution[MessageType.CODE] > 0
        assert sum(distribution.values()) == conv.message_count

    def test_repetitive_question_detection(self, detector):
        """Test detection of repetitive questions."""
        messages = [
            Message(Role.USER, "How do I use this?"),
            Message(Role.ASSISTANT, "You can..."),
            Message(Role.USER, "How do I use this?"),  # Same question
            Message(Role.ASSISTANT, "As I said..."),
        ]
        conv = Conversation(messages=tuple(messages))

        has_repetition = detector.detect_repetitive_questions(conv, similarity_threshold=0.8)
        assert has_repetition is True

    def test_no_repetition_for_different_questions(self, detector):
        """Test that different questions don't trigger repetition detection."""
        messages = [
            Message(Role.USER, "What is Python?"),
            Message(Role.ASSISTANT, "Python is..."),
            Message(Role.USER, "What is JavaScript?"),
            Message(Role.ASSISTANT, "JavaScript is..."),
        ]
        conv = Conversation(messages=tuple(messages))

        has_repetition = detector.detect_repetitive_questions(conv, similarity_threshold=0.8)
        assert has_repetition is False

    def test_message_efficiency_score(self, detector, small_conversation_data):
        """Test calculation of conversation efficiency."""
        conv = Conversation.from_dict(small_conversation_data)
        score = detector.calculate_message_efficiency(conv)
        # Should be a float between 0 and 1
        assert isinstance(score, float)
        assert 0 <= score <= 1

    def test_detects_short_prompt_pattern(self, detector):
        """Test detection of short prompt followed by clarification."""
        messages = [
            Message(Role.USER, "Optimize?"),  # Very short
            Message(Role.ASSISTANT, "Need more context"),
            Message(Role.USER, "Make it faster"),  # Still short
            Message(Role.ASSISTANT, "What specifically?"),
        ]
        conv = Conversation(messages=tuple(messages))

        has_pattern = detector.detect_short_prompt_pattern(conv, short_threshold=20)
        assert has_pattern is True
