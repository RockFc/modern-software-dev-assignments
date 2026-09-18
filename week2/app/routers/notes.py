from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import NoteCreate, NoteRead

# --- BEGIN AI-generated: notes router uses typed schemas (TODO 3 refactor) ---
router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteRead)
def create_note(payload: NoteCreate) -> NoteRead:
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    note_id = db.insert_note(content)
    note = db.get_note(note_id)
    if note is None:
        raise HTTPException(status_code=500, detail="failed to create note")

    return NoteRead(id=note["id"], content=note["content"], created_at=note["created_at"])


# --- BEGIN AI-generated: list all notes endpoint (TODO 4) ---
@router.get("", response_model=List[NoteRead])
def list_all_notes() -> List[NoteRead]:
    """Return all saved notes (newest first). Registered before /{note_id}."""
    rows = db.list_notes()
    return [
        NoteRead(id=row["id"], content=row["content"], created_at=row["created_at"])
        for row in rows
    ]


# --- END AI-generated: list all notes endpoint (TODO 4) ---


@router.get("/{note_id}", response_model=NoteRead)
def get_single_note(note_id: int) -> NoteRead:
    row = db.get_note(note_id)
    if row is None:
        raise HTTPException(status_code=404, detail="note not found")
    return NoteRead(id=row["id"], content=row["content"], created_at=row["created_at"])


# --- END AI-generated: notes router uses typed schemas (TODO 3 refactor) ---
