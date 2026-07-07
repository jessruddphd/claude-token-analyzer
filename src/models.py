"""Data models for conversation analysis."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class Role(Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"


class ConversationFormat(Enum):
    """Detected conversation export format."""

    CLAUDE_AI = "claude_ai"
    CLAUDE_CODE = "claude_code"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Message:
    """A single message in a conversation.

    Attributes:
        role: Message author (user or assistant).
        content: Message text content.
        timestamp: Optional ISO timestamp when message was sent.
    """

    role: Role
    content: str
    timestamp: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize message data."""
        # Content validation
        if not isinstance(self.content, str):
            raise TypeError(f"content must be str, got {type(self.content)}")

        content_stripped = self.content.strip()
        if not content_stripped:
            raise ValueError("content cannot be empty or whitespace-only")

        # Update content to be stripped
        object.__setattr__(self, "content", content_stripped)


@dataclass
class Conversation:
    """A conversation between user and Claude.

    Attributes:
        messages: Tuple of messages in conversation.
        id: Unique conversation identifier.
        created_at: Timestamp when conversation was created.
        metadata: Additional metadata from the export.
        detected_format: Format in which the conversation was exported.
    """

    messages: tuple  # Stored as tuple for hashability
    id: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_format: ConversationFormat = ConversationFormat.UNKNOWN

    def __post_init__(self):
        """Validate conversation data."""
        if not self.messages:
            raise ValueError("Conversation must have at least one message")

    @property
    def user_message_count(self) -> int:
        """Count of user messages."""
        return sum(1 for msg in self.messages if msg.role == Role.USER)

    @property
    def assistant_message_count(self) -> int:
        """Count of assistant messages."""
        return sum(1 for msg in self.messages if msg.role == Role.ASSISTANT)

    @property
    def message_count(self) -> int:
        """Total message count."""
        return len(self.messages)

    @property
    def total_content_length(self) -> int:
        """Total character count across all messages."""
        return sum(len(msg.content) for msg in self.messages)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Load conversation from dictionary (supports multiple formats).

        Handles both claude.ai export format and Claude Code event format.

        Args:
            data: Dictionary with conversation data.

        Returns:
            Conversation instance.

        Raises:
            ValueError: If data format is invalid or has no messages.
        """
        # Extract messages from various possible locations
        messages_raw = None

        if isinstance(data, dict):
            # Try different message locations
            if "messages" in data:
                messages_raw = data["messages"]
            elif "chat_messages" in data:
                messages_raw = data["chat_messages"]
            else:
                # Might be a single message or wrapped message
                if "role" in data or "sender" in data:
                    messages_raw = [data]

        if not messages_raw:
            raise ValueError("Could not find messages in conversation data")

        # Parse messages
        messages = cls._parse_messages(messages_raw)

        # Detect format
        detected_format = ConversationFormat.CLAUDE_AI
        if any("message" in msg for msg in messages_raw if isinstance(msg, dict)):
            detected_format = ConversationFormat.CLAUDE_CODE

        # Extract metadata
        metadata = {k: v for k, v in data.items() if k not in ["messages", "chat_messages"]}

        conv_id = data.get("id")
        created_at = data.get("created_at")

        return cls(
            messages=tuple(messages),
            id=conv_id,
            created_at=created_at,
            metadata=metadata,
            detected_format=detected_format,
        )

    @staticmethod
    def _parse_messages(messages_raw: List[Any]) -> List[Message]:
        """Parse raw message data into Message objects.

        Args:
            messages_raw: Raw message data (can be various formats).

        Returns:
            List of Message objects.

        Raises:
            ValueError: If messages cannot be parsed.
        """
        messages = []

        for msg_data in messages_raw:
            if not isinstance(msg_data, dict):
                continue

            # Extract role (with aliases)
            role_str = msg_data.get("role") or msg_data.get("sender") or msg_data.get("type")
            if not role_str:
                continue

            # Map aliases to canonical roles
            role_str = role_str.lower()
            if role_str in ("user", "human"):
                role = Role.USER
            elif role_str in ("assistant", "ai", "claude"):
                role = Role.ASSISTANT
            else:
                continue

            # Extract content (can be string or list of blocks)
            content_raw = (
                msg_data.get("content")
                or msg_data.get("text")
                or msg_data.get("message", {}).get("content")
            )

            if isinstance(content_raw, list):
                # Handle list of content blocks (Claude Code format)
                content_parts = []
                for block in content_raw:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                content_parts.append(text)
                content = " ".join(content_parts)
            elif isinstance(content_raw, str):
                content = content_raw
            else:
                continue

            # Skip empty messages
            if not content or not content.strip():
                continue

            # Extract timestamp
            timestamp = msg_data.get("timestamp")

            # Create message (will validate in __post_init__)
            try:
                msg = Message(role=role, content=content, timestamp=timestamp)
                messages.append(msg)
            except (ValueError, TypeError):
                # Skip invalid messages
                continue

        return messages

    @classmethod
    def from_cursor_export(cls, data: List[Dict[str, Any]]) -> List["Conversation"]:
        """Load conversations from Claude Code / Cursor export format.

        Args:
            data: List of event objects from Claude Code export.

        Returns:
            List of Conversation instances.
        """
        # Filter to only message events
        message_events = [item for item in data if isinstance(item, dict) and item.get("type") in ("user", "assistant")]

        if not message_events:
            return []

        # Parse into a single conversation
        messages = cls._parse_messages(message_events)

        if not messages:
            return []

        conversation = cls(
            messages=tuple(messages),
            detected_format=ConversationFormat.CLAUDE_CODE,
        )

        return [conversation]
