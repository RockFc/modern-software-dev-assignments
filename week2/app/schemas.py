# --- BEGIN AI-generated: API request/response contracts (TODO 3 refactor) ---
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class NoteRead(BaseModel):
    id: int
    content: str
    created_at: str


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1)
    save_note: bool = False


class ExtractedItem(BaseModel):
    id: int
    text: str


class ExtractResponse(BaseModel):
    note_id: Optional[int] = None
    items: List[ExtractedItem]


class ActionItemRead(BaseModel):
    id: int
    note_id: Optional[int] = None
    text: str
    done: bool
    created_at: str


class MarkDoneRequest(BaseModel):
    done: bool = True


class MarkDoneResponse(BaseModel):
    id: int
    done: bool


class ErrorResponse(BaseModel):
    detail: str


# --- END AI-generated: API request/response contracts (TODO 3 refactor) ---
