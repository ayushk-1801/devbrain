"""SQLite database engine and session factory for the platform service."""
from __future__ import annotations
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine
import os

PLATFORM_DB_PATH = os.getenv("PLATFORM_DB_PATH", "./.devbrain/platform.db")

# Ensure parent directory exists
Path(PLATFORM_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{PLATFORM_DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
