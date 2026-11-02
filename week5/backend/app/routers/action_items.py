from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ActionItem
from ..schemas import ActionItemCreate, ActionItemRead, Paginated

router = APIRouter(prefix="/action-items", tags=["action_items"])

MAX_PAGE_SIZE = 100


def _clamp_page_size(page_size: int) -> int:
    if page_size < 1:
        return 1
    return min(page_size, MAX_PAGE_SIZE)


@router.get("/", response_model=Paginated[ActionItemRead])
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1),
    db: Session = Depends(get_db),
) -> Paginated[ActionItemRead]:
    page = max(page, 1)
    page_size = _clamp_page_size(page_size)
    total = db.execute(select(func.count()).select_from(ActionItem)).scalar_one()
    offset = (page - 1) * page_size
    rows = (
        db.execute(select(ActionItem).order_by(ActionItem.id.asc()).offset(offset).limit(page_size))
        .scalars()
        .all()
    )
    return Paginated[ActionItemRead](
        items=[ActionItemRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=ActionItemRead, status_code=201)
def create_item(payload: ActionItemCreate, db: Session = Depends(get_db)) -> ActionItemRead:
    item = ActionItem(description=payload.description, completed=False)
    db.add(item)
    db.flush()
    db.refresh(item)
    return ActionItemRead.model_validate(item)


@router.put("/{item_id}/complete", response_model=ActionItemRead)
def complete_item(item_id: int, db: Session = Depends(get_db)) -> ActionItemRead:
    item = db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")
    item.completed = True
    db.add(item)
    db.flush()
    db.refresh(item)
    return ActionItemRead.model_validate(item)