from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas import (
    ActionItemRead,
    ExtractRequest,
    ExtractResponse,
    ExtractedItem,
    MarkDoneRequest,
    MarkDoneResponse,
)
from ..services.extract import extract_action_items, extract_action_items_llm

# --- BEGIN AI-generated: action-items router uses typed schemas (TODO 3 refactor) ---
router = APIRouter(prefix="/action-items", tags=["action-items"])


@router.post("/extract", response_model=ExtractResponse)
def extract(payload: ExtractRequest) -> ExtractResponse:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    note_id: Optional[int] = None
    if payload.save_note:
        note_id = db.insert_note(text)

    items = extract_action_items(text)
    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedItem(id=i, text=t) for i, t in zip(ids, items)],
    )


# --- BEGIN AI-generated: LLM extract endpoint (TODO 4) ---
@router.post("/extract-llm", response_model=ExtractResponse)
def extract_llm(payload: ExtractRequest) -> ExtractResponse:
    """Same contract as /extract, but uses the Ollama-backed extractor."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    try:
        items = extract_action_items_llm(text, raise_on_error=True)
    except RuntimeError as exc:
        # Keep the server up; surface a clear message for the frontend.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    note_id: Optional[int] = None
    if payload.save_note:
        note_id = db.insert_note(text)

    ids = db.insert_action_items(items, note_id=note_id)
    return ExtractResponse(
        note_id=note_id,
        items=[ExtractedItem(id=i, text=t) for i, t in zip(ids, items)],
    )


# --- END AI-generated: LLM extract endpoint (TODO 4) ---


@router.get("", response_model=List[ActionItemRead])
def list_all(note_id: Optional[int] = None) -> List[ActionItemRead]:
    rows = db.list_action_items(note_id=note_id)
    return [
        ActionItemRead(
            id=r["id"],
            note_id=r["note_id"],
            text=r["text"],
            done=bool(r["done"]),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{action_item_id}/done", response_model=MarkDoneResponse)
def mark_done(action_item_id: int, payload: MarkDoneRequest) -> MarkDoneResponse:
    updated = db.mark_action_item_done(action_item_id, payload.done)
    if not updated:
        raise HTTPException(status_code=404, detail="action item not found")
    return MarkDoneResponse(id=action_item_id, done=payload.done)


# --- END AI-generated: action-items router uses typed schemas (TODO 3 refactor) ---
