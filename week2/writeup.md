# Week 2 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: **TODO** \
SUNet ID: **TODO** \
Citations: **TODO**

This assignment took me about **TODO** hours to do. 


## YOUR RESPONSES
For each exercise, please include what prompts you used to generate the answer, in addition to the location of the generated response. Make sure to clearly add comments in your code documenting which parts are generated.

### Exercise 1: Scaffold a New Feature
Prompt: 
```
@app/services/extract.py In app/services/extract.py, keep the existing extract_action_items() heuristic function unchanged.

Add a new function:

    def extract_action_items_llm(text: str) -> List[str]:

Requirements:
1. Use the Ollama Python client (already imported: `from ollama import chat`) to extract action items from free-form notes.
2. Return a Python list of strings. Each string is one concrete action item.
3. Prefer Ollama structured outputs so the model returns a JSON array of strings (see https://ollama.com/blog/structured-outputs). If structured outputs are awkward in this client version, fall back to asking for JSON and parsing with json.loads safely.
4. Choose a small local model by default (e.g. llama3.1:8b), and allow overriding via an environment variable like OLLAMA_MODEL.
5. Handle empty / whitespace-only input by returning [].
6. Clean results: strip whitespace, drop empty strings, deduplicate while preserving order.
7. Do not crash the app if Ollama fails: catch exceptions and either re-raise a clear error or return [] — pick one approach and document it with a short comment.
8. Add clear comments marking which parts were AI-generated for the course writeup.
9. Do not modify unrelated files in this step.

After implementing, show me the full new function and a minimal example of how to call it.
``` 

Generated Code Snippets:
```
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


def extract_action_items_llm(text: str) -> List[str]:
    """Extract concrete action items from free-form notes via a local Ollama model.

    Uses Ollama structured outputs (`format=`) so the model returns JSON. Falls back
    to `json.loads` on the message content. Override the model with OLLAMA_MODEL
    (default: llama3.1:8b).
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
    except Exception:
        # Soft-fail: if Ollama is unreachable or returns bad JSON, return [] so the
        # FastAPI app does not crash. Callers can treat empty as "no items / unavailable".
        return []
```

### Exercise 2: Add Unit Tests
Prompt: 
```
Write unit tests for `extract_action_items_llm()` covering multiple inputs (e.g., bullet lists, keyword-prefixed lines, empty input) in `week2/tests/test_extract.py`.
``` 

Generated Code Snippets:
```
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
```

### Exercise 3: Refactor Existing Code for Clarity
Prompt: 
```
Perform a refactor of the code in the backend, focusing in particular on well-defined API contracts/schemas, database layer cleanup, app lifecycle/configuration, error handling.

Constraints:
- Keep existing API behavior working (rule-based extract still works from the UI).
- Do not remove extract_action_items_llm() or the unit tests.
- Prefer small, clear changes over a full rewrite.
- Add brief comments marking AI-generated refactor changes.
- After refactor, tell me which files changed and how to re-run the server and tests.
``` 

Generated/Modified Code Snippets:
```
  ┌───────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────┬────────────┐
  │ File                              │ Change                                                                                      │ + / −      │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/config.py               │ New — DATABASE_PATH, APP_TITLE, paths, OLLAMA_MODEL                                         │ +20 / −0   │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/schemas.py              │ New — Pydantic request/response contracts                                                   │ +55 / −0   │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/db.py                   │ Context-managed connections, commit/rollback, get_action_item, mark_action_item_done → bool │ +31 / −17  │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/main.py                 │ Lifespan startup, config-driven title/static, JSON catch-all errors                         │ +33 / −9   │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/routers/notes.py        │ Typed schemas + clearer 400/404/500                                                         │ +14 / −14  │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ week2/app/routers/action_items.py │ Typed schemas; 404 when marking a missing item                                              │ +34 / −21  │
  ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────┼────────────┤
  │ Total                             │                                                                                             │ +187 / −61 │
  └───────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────┴────────────┘
```


### Exercise 4: Use Agentic Mode to Automate a Small Task
Prompt: 
```
Work in the week2 Action Item Extractor app.

Implement TODO 4 with two features:

1) LLM extraction endpoint + UI button
- Add a new backend endpoint that runs extract_action_items_llm() on the submitted notes text.
- Keep the existing rule-based Extract endpoint/button unchanged.
- Update week2/frontend/index.html to add an "Extract LLM" button.
- Clicking "Extract LLM" should call the new endpoint and render the returned action items as a checklist (same UX style as the current Extract result).
- Respect the existing "Save as note" checkbox behavior if applicable.

2) List all notes endpoint + UI button
- Add a backend endpoint that returns all saved notes from the database.
- Update the frontend to add a "List Notes" button.
- Clicking it should fetch and display the notes in a simple readable list on the page.

Constraints:
- Prefer small, clear changes; reuse existing schemas/routers/db helpers where possible.
- Do not remove extract_action_items(), extract_action_items_llm(), or existing tests.
- Handle errors cleanly (e.g., Ollama failure should show a clear message, not crash the server).
- Add brief comments marking AI-generated changes for the course writeup.
- When done, list changed files and how to manually verify both buttons in the browser.
``` 

Generated Code Snippets:
```
  ┌───────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ File                              │ Change                                                                                                   │
  ├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ week2/app/routers/action_items.py │ POST /action-items/extract-llm → extract_action_items_llm(..., raise_on_error=True); Ollama errors → 503 │
  ├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ week2/app/routers/notes.py        │ GET /notes lists all notes (before /{note_id})                                                           │
  ├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ week2/app/services/extract.py     │ Optional raise_on_error (default False so tests stay soft-fail)                                          │
  ├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ week2/frontend/index.html         │ Extract LLM + List Notes buttons and UI                                                                  │
  └───────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```


### Exercise 5: Generate a README from the Codebase
Prompt: 
```
  analyze the current codebase and generate a well-structured `README.md` file. The README should include, at a minimum:                                                                     
  - A brief overview of the project                                                                                                                                                          
  - How to set up and run the project                                                                                                                                                        
  - API endpoints and functionality                                                                                                                                                          
  - Instructions for running the test suite   
``` 

Generated Code Snippets:
```
 week2/README.md  │ 1–164 (new) 
```


## SUBMISSION INSTRUCTIONS
1. Hit a `Command (⌘) + F` (or `Ctrl + F`) to find any remaining `TODO`s in this file. If no results are found, congratulations – you've completed all required fields. 
2. Make sure you have all changes pushed to your remote repository for grading.
3. Submit via Gradescope. 