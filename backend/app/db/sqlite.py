from functools import lru_cache
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import Settings, get_settings


def _resolve_sqlite_path(sqlite_url: str) -> Path:
    if not sqlite_url.startswith("sqlite:///"):
        raise ValueError("sqlite_url must use a file-based sqlite:/// URL.")
    return Path(sqlite_url.removeprefix("sqlite:///")).expanduser().resolve()


def initialize_sqlite_database(active_settings: Settings) -> Path:
    sqlite_path = _resolve_sqlite_path(active_settings.sqlite_url)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    with create_engine(
        active_settings.sqlite_url,
        connect_args={"check_same_thread": False},
    ).connect():
        pass

    return sqlite_path


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.sqlite_url,
        connect_args={"check_same_thread": False},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
