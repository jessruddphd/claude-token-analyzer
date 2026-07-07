"""Unit tests for data models (test-first development)."""
import pytest
from typing import Dict, Any

from src.models import Role, Message, Conversation, ConversationFormat


class TestRole:
    """Tests for Role enum."""

    def test_role_user_value(self):
        assert Role.USER.value == "user"

    def test_role_assistant_value(self):
        assert Role.ASSISTANT.value == "assistant"

    def test_role_has_two_variants(self):
        assert len(Role) == 2


class TestMessage:
    """Tests for Message model."""

    def test_message_creation(self):
        msg = Message(role=Role.USER, content="Hello")
        assert msg.role == Role.USER
        assert msg.content == "Hello"

    def test_message_with_timestamp(self):
        msg = Message(role=Role.USER, content="Hello", timestamp="2024-01-15T10:00:00Z")
        assert msg.timestamp == "2024-01-15T10:00:00Z"

    def test_message_rejects_empty_content(self):
        with pytest.raises(ValueError, match="content cannot be empty"):
            Message(role=Role.USER, content="")

    def test_message_rejects_none_content(self):
        with pytest.raises((ValueError, TypeError)):
            Message(role=Role.USER, content=None)

    def test_message_strips_whitespace(self):
        msg = Message(role=Role.USER, content="  Hello  ")
        assert msg.content == "Hello"

    def test_message_with_all_fields(self):
        msg = Message(
            role=Role.ASSISTANT,
            content="Response",
            timestamp="2024-01-15T10:00:00Z",
        )
        assert msg.role == Role.ASSISTANT
        assert msg.content == "Response"
        assert msg.timestamp == "2024-01-15T10:00:00Z"


class TestConversation:
    """Tests for Conversation model."""

    def test_conversation_creation(self, small_conversation_data: Dict[str, Any]):
        conv = Conversation.from_dict(small_conversation_data)
        assert len(conv.messages) == 5
        assert conv.messages[0].role == Role.USER
        assert conv.messages[1].role == Role.ASSISTANT

    def test_conversation_rejects_empty_messages(self):
        with pytest.raises(ValueError, match="at least one message"):
            Conversation(messages=[])

    def test_conversation_preserves_message_order(self, small_conversation_data):
        conv = Conversation.from_dict(small_conversation_data)
        contents = [msg.content for msg in conv.messages]
        assert contents[0] == "What is Python?"
        assert contents[-1] == "Thanks!"

    def test_conversation_from_claude_ai_format(self, claude_ai_export_format):
        """Test loading from claude.ai export format."""
        data = claude_ai_export_format["conversations"][0]
        conv = Conversation.from_dict(data)
        assert len(conv.messages) == 2
        assert conv.messages[0].content == "Hello"
        assert conv.messages[1].content == "Hi there!"

    def test_conversation_from_cursor_format(self, cursor_export_format):
        """Test loading from Claude Code/Cursor format."""
        conversations = Conversation.from_cursor_export(cursor_export_format)
        assert len(conversations) == 1
        assert len(conversations[0].messages) == 2
        assert conversations[0].messages[0].role == Role.USER
        assert conversations[0].messages[1].role == Role.ASSISTANT

    def test_conversation_detects_format_automatically(self, small_conversation_data):
        """Test automatic format detection."""
        conv = Conversation.from_dict(small_conversation_data)
        assert conv.detected_format == ConversationFormat.CLAUDE_AI

    def test_conversation_with_various_role_aliases(self):
        """Test that common role aliases are handled."""
        data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "human", "content": "Test"},  # Alias
                {"role": "ai", "content": "Response"},  # Alias
            ]
        }
        conv = Conversation.from_dict(data)
        assert len(conv.messages) == 4
        # All user-like roles should map to USER
        assert conv.messages[0].role == Role.USER
        assert conv.messages[2].role == Role.USER
        # All assistant-like roles should map to ASSISTANT
        assert conv.messages[1].role == Role.ASSISTANT
        assert conv.messages[3].role == Role.ASSISTANT

    def test_conversation_user_and_assistant_counts(self, small_conversation_data):
        conv = Conversation.from_dict(small_conversation_data)
        assert conv.user_message_count == 3
        assert conv.assistant_message_count == 2

    def test_conversation_total_content_length(self, small_conversation_data):
        conv = Conversation.from_dict(small_conversation_data)
        # Total characters across all messages
        total = sum(len(msg.content) for msg in conv.messages)
        assert total > 0
        assert conv.total_content_length == total

    def test_conversation_handles_nested_content_structures(self):
        """Test handling of content as list of blocks (Claude Code format)."""
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Part 1"},
                        {"type": "text", "text": "Part 2"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": "Response",
                },
            ]
        }
        conv = Conversation.from_dict(data)
        # Content from list blocks joined with space
        assert "Part 1" in conv.messages[0].content
        assert "Part 2" in conv.messages[0].content

    def test_conversation_with_missing_timestamp(self):
        """Test that conversations work without timestamps."""
        data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        }
        conv = Conversation.from_dict(data)
        assert len(conv.messages) == 2
        assert conv.messages[0].timestamp is None

    def test_conversation_metadata_preserved(self, small_conversation_data):
        """Test that conversation metadata is preserved."""
        conv = Conversation.from_dict(small_conversation_data)
        assert conv.id == "test_small"
        assert conv.created_at == "2024-01-15T10:00:00Z"

    def test_conversation_from_dict_handles_chat_messages_key(self):
        """Test alternative data format with 'chat_messages' key."""
        data = {
            "chat_messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        }
        conv = Conversation.from_dict(data)
        assert len(conv.messages) == 2

    def test_conversation_equality(self, small_conversation_data):
        """Test that two conversations with same data are equal."""
        conv1 = Conversation.from_dict(small_conversation_data)
        conv2 = Conversation.from_dict(small_conversation_data)
        # Same data should create equal conversations
        assert conv1.message_count == conv2.message_count
        assert all(m1.content == m2.content for m1, m2 in zip(conv1.messages, conv2.messages))
