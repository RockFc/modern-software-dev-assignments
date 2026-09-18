# --- BEGIN AI-generated: app configuration (TODO 3 refactor) ---
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

# Allow overriding the SQLite path without code changes.
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "app.db")))

APP_TITLE = os.getenv("APP_TITLE", "Action Item Extractor")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
# --- END AI-generated: app configuration (TODO 3 refactor) ---
