from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Note
from ..schemas import NoteCreate, NoteRead, Paginated

router = APIRouter(prefix="/notes", tags=["notes"])

MAX_PAGE_SIZE = 100
SortOption = Literal["created_desc", "title_asc"]


def _clamp_page_size(page_size: int) -> int:
    if page_size < 1:
        return 1
    return min(page_size, MAX_PAGE_SIZE)


def _paginate_notes(
    db: Session,
    *,
    page: int,
    page_size: int,
    q: Optional[str] = None,
    sort: SortOption = "created_desc",
) -> Paginated[NoteRead]:
    page = max(page, 1)
    page_size = _clamp_page_size(page_size)

    filters = []
    if q:
        pattern = f"%{q.lower()}%"
        filters.append(
            or_(
                func.lower(Note.title).like(pattern),
                func.lower(Note.content).like(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(Note)
    list_stmt = select(Note)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    if sort == "title_asc":
        list_stmt = list_stmt.order_by(func.lower(Note.title).asc(), Note.id.asc())
    else:
        list_stmt = list_stmt.order_by(Note.created_at.desc(), Note.id.desc())

    total = db.execute(count_stmt).scalar_one()
    offset = (page - 1) * page_size
    rows = db.execute(list_stmt.offset(offset).limit(page_size)).scalars().all()
    return Paginated[NoteRead](
        items=[NoteRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/", response_model=Paginated[NoteRead])
def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
) -> Paginated[NoteRead]:
    return _paginate_notes(db, page=page, page_size=page_size)


@router.post("/", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)) -> NoteRead:
    note = Note(title=payload.title, content=payload.content)
    db.add(note)
    db.flush()
    db.refresh(note)
    return NoteRead.model_validate(note)


@router.get("/search", response_model=Paginated[NoteRead])
@router.get("/search/", response_model=Paginated[NoteRead])
def search_notes(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    sort: SortOption = Query("created_desc"),
    db: Session = Depends(get_db),
) -> Paginated[NoteRead]:
    return _paginate_notes(db, page=page, page_size=page_size, q=q, sort=sort)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: int, db: Session = Depends(get_db)) -> NoteRead:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteRead.model_validate(note)