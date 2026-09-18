from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# --- BEGIN AI-generated: app lifecycle, config, error handling (TODO 3 refactor) ---
from .config import APP_TITLE, FRONTEND_DIR
from .db import init_db
from .routers import action_items, notes


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize database schema on startup; teardown hook reserved for later."""
    init_db()
    yield


# CREATE IF NOT EXISTS is idempotent; import-time init keeps simple TestClients working
# even when lifespan is not entered.
init_db()
app = FastAPI(title=APP_TITLE, lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Soft-fail unexpected errors as JSON so the API does not return an HTML traceback.
    FastAPI still handles HTTPException and validation errors via their own handlers.
    """
    # Do not swallow framework HTTP errors if they bubble here.
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_path = Path(FRONTEND_DIR) / "index.html"
    if not html_path.is_file():
        raise HTTPException(status_code=500, detail="frontend index.html missing")
    return html_path.read_text(encoding="utf-8")


app.include_router(notes.router)
app.include_router(action_items.router)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
# --- END AI-generated: app lifecycle, config, error handling (TODO 3 refactor) ---
