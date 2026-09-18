from __future__ import annotations

import os
import re
from typing import List
import json
from typing import Any
from ollama import chat
from dotenv import load_dotenv

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)


def _is_action_line(line: str) -> bool:
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def extract_action_items(text: str) -> List[str]:
    lines = text.splitlines()
    extracted: List[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)
            cleaned = cleaned.strip()
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()
            cleaned = cleaned.removeprefix("[todo]").strip()
            extracted.append(cleaned)
    # Fallback: if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if _looks_imperative(s):
                extracted.append(s)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for item in extracted:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def _looks_imperative(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z']+", sentence)
    if not words:
        return False
    first = words[0]
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters


# --- BEGIN AI-generated: LLM action-item extraction (TODO 1) ---
# JSON schema for Ollama structured outputs: object wrapping a string array.
_ACTION_ITEMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action_items": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["action_items"],
}


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    """Strip, drop empties, and deduplicate (case-insensitive) while keeping order."""
    seen: set[str] = set()
    unique: List[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def extract_action_items_llm(text: str, *, raise_on_error: bool = False) -> List[str]:
    """Extract concrete action items from free-form notes via a local Ollama model.

    Uses Ollama structured outputs (`format=`) so the model returns JSON. Falls back
    to `json.loads` on the message content. Override the model with OLLAMA_MODEL
    (default: llama3.1:8b).

    By default soft-fails to [] on Ollama errors (keeps unit tests / callers safe).
    Pass raise_on_error=True from the API so the UI can show a clear failure message.
    """
    if not text or not text.strip():
        return []

    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    prompt = (
        "Extract concrete, actionable to-do items from the notes below. "
        "Return only real action items as short imperative phrases. "
        "Do not invent unrelated tasks. Respond as JSON matching the schema "
        '(an object with key "action_items" whose value is an array of strings).\n\n'
        f"Notes:\n{text.strip()}"
    )

    try:
        response = chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=_ACTION_ITEMS_SCHEMA,
            options={"temperature": 0},
        )
        content = (response.message.content or "").strip()
        if not content:
            return []

        # Structured output should already be JSON; parse safely either way.
        data = json.loads(content)
        if isinstance(data, dict):
            raw_items = data.get("action_items", [])
        elif isinstance(data, list):
            # Fallback if the model returns a bare JSON array of strings.
            raw_items = data
        else:
            return []

        if not isinstance(raw_items, list):
            return []

        string_items = [item for item in raw_items if isinstance(item, str)]
        return _dedupe_preserve_order(string_items)
    except Exception as exc:
        # Soft-fail by default: return [] so casual callers / tests do not crash.
        # API endpoints can set raise_on_error=True for a clear HTTP error instead.
        if raise_on_error:
            raise RuntimeError(f"Ollama extraction failed: {exc}") from exc
        return []


# --- END AI-generated: LLM action-item extraction (TODO 1) ---
