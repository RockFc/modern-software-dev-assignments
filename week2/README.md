<!-- AI-generated README for Week 2 (TODO 5) -->
# Week 2 – Action Item Extractor

A small FastAPI + SQLite app that turns free-form notes into actionable checklists. The UI supports **rule-based** extraction and **LLM-powered** extraction (via Ollama), plus listing saved notes.

Full assignment details: [assignment.md](./assignment.md)

## Overview

| Layer | Role |
|-------|------|
| `app/` | FastAPI backend: notes, action items, extractors |
| `frontend/` | Single-page HTML UI served at `/` |
| `data/` | SQLite database (`app.db` by default) |
| `tests/` | Pytest coverage for extractors |

Extraction modes:

- **Heuristic** (`extract_action_items`) — bullets, checkboxes, `TODO:` / `Action:` / `Next:` prefixes, simple imperatives
- **LLM** (`extract_action_items_llm`) — local/remote Ollama model with structured JSON output

## Setup

From the **repository root** (parent of `week2/`):

1. Create and activate the course conda env (Python 3.10+):

```bash
conda create -n cs146s python=3.12 -y
conda activate cs146s
```

2. Install dependencies with Poetry:

```bash
poetry install --no-interaction
```

3. **(Optional, for LLM extract)** Point the Ollama client at your server (e.g. Docker) and ensure a model is available:

```bash
export OLLAMA_HOST=http://localhost:11434   # or your Docker host/IP
export OLLAMA_MODEL=llama3.1:8b             # optional override
ollama pull llama3.1:8b                     # if using a local Ollama CLI
```

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_PATH` | `week2/data/app.db` | SQLite file location |
| `APP_TITLE` | `Action Item Extractor` | FastAPI app title |
| `OLLAMA_HOST` | Ollama client default | Ollama HTTP base URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model used by LLM extract |

## Run the app

From the repository root:

```bash
conda activate cs146s
poetry run uvicorn week2.app.main:app --reload
```

Then open:

- App UI: http://127.0.0.1:8000/
- Interactive API docs: http://127.0.0.1:8000/docs

### UI buttons

| Button | Behavior |
|--------|----------|
| **Extract** | Rule-based extract via `POST /action-items/extract` |
| **Extract LLM** | Ollama extract via `POST /action-items/extract-llm` |
| **List Notes** | Loads all notes via `GET /notes` |
| **Save as note** | When checked, successful extracts also persist the note text |

## Project structure

```
week2/
├── app/
│   ├── main.py              # FastAPI app, lifespan, error handling
│   ├── config.py            # Env-based settings
│   ├── db.py                # SQLite helpers
│   ├── schemas.py           # Pydantic request/response models
│   ├── routers/
│   │   ├── notes.py
│   │   └── action_items.py
│   └── services/
│       └── extract.py       # Heuristic + LLM extractors
├── frontend/
│   └── index.html
├── tests/
│   └── test_extract.py
├── assignment.md
└── writeup.md
```

## API endpoints

### Notes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/notes` | Create a note. Body: `{ "content": "..." }` |
| `GET` | `/notes` | List all notes (newest first) |
| `GET` | `/notes/{note_id}` | Fetch one note |

**Note response shape:** `{ "id", "content", "created_at" }`

### Action items

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/action-items/extract` | Rule-based extraction |
| `POST` | `/action-items/extract-llm` | LLM extraction (Ollama) |
| `GET` | `/action-items` | List action items; optional `?note_id=` |
| `POST` | `/action-items/{id}/done` | Mark done/undone. Body: `{ "done": true }` |

**Extract request:**

```json
{ "text": "meeting notes...", "save_note": true }
```

**Extract response:**

```json
{
  "note_id": 1,
  "items": [{ "id": 1, "text": "Set up database" }]
}
```

If Ollama is unreachable or fails, `POST /action-items/extract-llm` returns **503** with `{ "detail": "Ollama extraction failed: ..." }` instead of crashing the server.

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the HTML frontend |
| `GET` | `/static/...` | Static files from `frontend/` |

## Tests

From the repository root:

```bash
conda activate cs146s
poetry run pytest week2/tests/test_extract.py -v
```

The suite covers:

- Heuristic extraction (bullets / checkboxes)
- LLM extraction with a **mocked** Ollama client (empty input, bullets, keyword lines, dedupe, failure soft-fail, `OLLAMA_MODEL` override)

No live Ollama instance is required for unit tests.

## License / course context

Part of [CS146S: The Modern Software Developer](https://themodernsoftware.dev) assignments.
