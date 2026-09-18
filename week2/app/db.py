from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

# --- BEGIN AI-generated: DB layer cleanup (TODO 3 refactor) ---
from .config import DB_PATH


def ensure_data_directory_exists() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with Row factory; auto-commit/rollback on exit."""
    ensure_data_directory_exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                text TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (note_id) REFERENCES notes(id)
            );
            """
        )


def insert_note(content: str) -> int:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
        return int(cursor.lastrowid)


def list_notes() -> list[sqlite3.Row]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id, content, created_at FROM notes ORDER BY id DESC")
        return list(cursor.fetchall())


def get_note(note_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, content, created_at FROM notes WHERE id = ?",
            (note_id,),
        )
        return cursor.fetchone()


def insert_action_items(items: list[str], note_id: Optional[int] = None) -> list[int]:
    with get_connection() as connection:
        cursor = connection.cursor()
        ids: list[int] = []
        for item in items:
            cursor.execute(
                "INSERT INTO action_items (note_id, text) VALUES (?, ?)",
                (note_id, item),
            )
            ids.append(int(cursor.lastrowid))
        return ids


def list_action_items(note_id: Optional[int] = None) -> list[sqlite3.Row]:
    with get_connection() as connection:
        cursor = connection.cursor()
        if note_id is None:
            cursor.execute(
                "SELECT id, note_id, text, done, created_at FROM action_items ORDER BY id DESC"
            )
        else:
            cursor.execute(
                "SELECT id, note_id, text, done, created_at FROM action_items WHERE note_id = ? ORDER BY id DESC",
                (note_id,),
            )
        return list(cursor.fetchall())


def get_action_item(action_item_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT id, note_id, text, done, created_at FROM action_items WHERE id = ?",
            (action_item_id,),
        )
        return cursor.fetchone()


def mark_action_item_done(action_item_id: int, done: bool) -> bool:
    """Return True if a row was updated, False if the action item does not exist."""
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE action_items SET done = ? WHERE id = ?",
            (1 if done else 0, action_item_id),
        )
        return cursor.rowcount > 0


# --- END AI-generated: DB layer cleanup (TODO 3 refactor) ---
