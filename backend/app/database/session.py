"""Database engine and session configuration."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_PROJECT_DB_FILE = Path(__file__).resolve().parents[3] / "aqua_mind.db"
_DEFAULT_URL = (
    f"sqlite:///{_PROJECT_DB_FILE.as_posix()}"
    if _PROJECT_DB_FILE.is_file()
    else "sqlite:///./aqua_mind.db"
)
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
