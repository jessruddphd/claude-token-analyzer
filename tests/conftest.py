"""Pytest configuration and shared fixtures for token analyzer tests."""
import json
from pathlib import Path
from typing import Dict, Any

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def small_conversation_data() -> Dict[str, Any]:
    """Small conversation (5 messages) for basic testing."""
    return {
        "id": "test_small",
        "created_at": "2024-01-15T10:00:00Z",
        "messages": [
            {"role": "user", "content": "What is Python?", "timestamp": "2024-01-15T10:00:00Z"},
            {
                "role": "assistant",
                "content": "Python is a programming language.",
                "timestamp": "2024-01-15T10:01:00Z",
            },
            {"role": "user", "content": "Show me an example", "timestamp": "2024-01-15T10:02:00Z"},
            {
                "role": "assistant",
                "content": "```python\nprint('Hello')\n```",
                "timestamp": "2024-01-15T10:03:00Z",
            },
            {"role": "user", "content": "Thanks!", "timestamp": "2024-01-15T10:04:00Z"},
        ],
    }


@pytest.fixture
def long_conversation_data() -> Dict[str, Any]:
    """Conversation with 50+ messages for testing context management patterns."""
    messages = []
    for i in range(50):
        if i % 2 == 0:
            messages.append({
                "role": "user",
                "content": f"Question {i // 2}: What is the answer to question {i // 2}?",
                "timestamp": f"2024-01-15T10:{i:02d}:00Z",
            })
        else:
            messages.append({
                "role": "assistant",
                "content": f"The answer to question {i // 2} is: some detailed explanation...",
                "timestamp": f"2024-01-15T10:{i:02d}:00Z",
            })
    return {"id": "test_long", "created_at": "2024-01-15T10:00:00Z", "messages": messages}


@pytest.fixture
def claude_ai_export_format() -> Dict[str, Any]:
    """Claude.ai export format (list of messages with 'messages' key)."""
    return {
        "conversations": [
            {
                "id": "conv_test1",
                "created_at": "2024-01-15T10:00:00Z",
                "messages": [
                    {"role": "user", "content": "Hello", "timestamp": "2024-01-15T10:00:00Z"},
                    {
                        "role": "assistant",
                        "content": "Hi there!",
                        "timestamp": "2024-01-15T10:01:00Z",
                    },
                ],
            }
        ]
    }


@pytest.fixture
def cursor_export_format() -> Dict[str, Any]:
    """Claude Code / Cursor export format (flat list of events)."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": "What is Python?",
            },
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": "Python is a programming language.",
            },
        },
    ]


@pytest.fixture
def code_heavy_conversation() -> Dict[str, Any]:
    """Conversation mostly with code blocks."""
    return {
        "id": "test_code",
        "created_at": "2024-01-15T10:00:00Z",
        "messages": [
            {
                "role": "user",
                "content": "Write a function to sort a list",
                "timestamp": "2024-01-15T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "```python\ndef sort_list(items):\n    return sorted(items)\n```",
                "timestamp": "2024-01-15T10:01:00Z",
            },
            {"role": "user", "content": "Can you optimize it?", "timestamp": "2024-01-15T10:02:00Z"},
            {
                "role": "assistant",
                "content": "```python\ndef sort_list(items):\n    # Use quicksort for better performance\n    return sorted(items, key=lambda x: x)\n```",
                "timestamp": "2024-01-15T10:03:00Z",
            },
        ],
    }


@pytest.fixture
def clarification_pattern_conversation() -> Dict[str, Any]:
    """Conversation showing repeated clarification patterns."""
    return {
        "id": "test_clarification",
        "created_at": "2024-01-15T10:00:00Z",
        "messages": [
            {
                "role": "user",
                "content": "Optimize this?",
                "timestamp": "2024-01-15T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "Could you provide more context?",
                "timestamp": "2024-01-15T10:01:00Z",
            },
            {
                "role": "user",
                "content": "More details?",
                "timestamp": "2024-01-15T10:02:00Z",
            },
            {
                "role": "assistant",
                "content": "What specifically needs optimization?",
                "timestamp": "2024-01-15T10:03:00Z",
            },
            {
                "role": "user",
                "content": "The speed.",
                "timestamp": "2024-01-15T10:04:00Z",
            },
        ],
    }
