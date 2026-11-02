import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "./data/app.db")

engine = create_engine(f"sqlite:///{DEFAULT_DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()
        raise
    finally:
        session.close()


def ensure_schema_upgrades() -> None:
    """Best-effort SQLite migrations for existing local DBs."""
    inspector = inspect(engine)
    if "notes" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("notes")}
    if "created_at" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE notes ADD COLUMN created_at DATETIME "
                    "DEFAULT CURRENT_TIMESTAMP NOT NULL"
                )
            )


def apply_seed_if_needed() -> None:
    db_path = Path(DEFAULT_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    newly_created = not db_path.exists()
    if newly_created:
        db_path.touch()

    seed_file = Path("./data/seed.sql")
    if newly_created and seed_file.exists():
        with engine.begin() as conn:
            sql = seed_file.read_text()
            if sql.strip():
                for statement in [s.strip() for s in sql.split(";") if s.strip()]:
                    conn.execute(text(statement))