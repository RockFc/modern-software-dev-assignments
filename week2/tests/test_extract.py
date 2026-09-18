import json
from types import SimpleNamespace
from unittest.mock import patch

from ..app.services.extract import extract_action_items, extract_action_items_llm


def test_extract_bullets_and_checkboxes():
    text = """
    Notes from meeting:
    - [ ] Set up database
    * implement API extract endpoint
    1. Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items(text)
    assert "Set up database" in items
    assert "implement API extract endpoint" in items
    assert "Write tests" in items


# --- BEGIN AI-generated: unit tests for extract_action_items_llm (TODO 2) ---


def _fake_chat_response(payload) -> SimpleNamespace:
    """Build a minimal ollama-like chat response with JSON content."""
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(message=SimpleNamespace(content=content))


def test_extract_action_items_llm_empty_and_whitespace():
    assert extract_action_items_llm("") == []
    assert extract_action_items_llm("   \n\t  ") == []


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_bullet_list(mock_chat):
    mock_chat.return_value = _fake_chat_response(
        {"action_items": ["Set up database", "Write tests"]}
    )
    text = """
    Notes from meeting:
    - Set up database
    * Write tests
    Some narrative sentence.
    """.strip()

    items = extract_action_items_llm(text)

    assert items == ["Set up database", "Write tests"]
    mock_chat.assert_called_once()
    assert "Set up database" in mock_chat.call_args.kwargs["messages"][0]["content"]


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_keyword_prefixed(mock_chat):
    mock_chat.return_value = _fake_chat_response(
        {
            "action_items": [
                "email the team about the demo",
                "fix the login bug",
            ]
        }
    )
    text = """
    TODO: email the team about the demo
    Action: fix the login bug
    Next: schedule retrospective
    """.strip()

    items = extract_action_items_llm(text)

    assert "email the team about the demo" in items
    assert "fix the login bug" in items
    mock_chat.assert_called_once()


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_cleans_and_dedupes(mock_chat):
    mock_chat.return_value = _fake_chat_response(
        {
            "action_items": [
                "  Buy milk  ",
                "",
                "Buy milk",
                "Call dentist",
                "call dentist",
            ]
        }
    )

    items = extract_action_items_llm("notes with duplicates")

    assert items == ["Buy milk", "Call dentist"]


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_bare_json_array_fallback(mock_chat):
    mock_chat.return_value = _fake_chat_response(["Ship feature", "Update docs"])

    items = extract_action_items_llm("Ship feature and update docs")

    assert items == ["Ship feature", "Update docs"]


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_ollama_failure_returns_empty(mock_chat):
    mock_chat.side_effect = ConnectionError("ollama unavailable")

    assert extract_action_items_llm("TODO: do something") == []


@patch("week2.app.services.extract.chat")
def test_extract_action_items_llm_uses_ollama_model_env(mock_chat, monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "tinyllama:latest")
    mock_chat.return_value = _fake_chat_response({"action_items": ["Do the thing"]})

    items = extract_action_items_llm("TODO: Do the thing")

    assert items == ["Do the thing"]
    assert mock_chat.call_args.kwargs["model"] == "tinyllama:latest"


# --- END AI-generated: unit tests for extract_action_items_llm (TODO 2) ---
