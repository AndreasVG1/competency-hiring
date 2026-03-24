import os
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Ensure module-level app creation can import cleanly before pytest fixtures run.
os.environ["DEBUG"] = "false"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "test"
os.environ["JWT_SECRET"] = "test-secret"

from app import main as app_main
from app.core.settings import get_settings
from app.db.base import Base
from app.db.sqlite import (
    get_engine,
    get_session_factory,
    initialize_sqlite_database,
)


@pytest.fixture(autouse=True)
def test_environment(monkeypatch, tmp_path):
    """Configure a disposable settings environment for every test."""

    db_file = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    settings = get_settings()
    initialize_sqlite_database(settings)

    engine = get_engine()
    Base.metadata.create_all(engine)

    # Patch the names imported into app.main so startup never touches a real driver.
    monkeypatch.setattr(app_main, "get_neo4j_driver", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_main, "close_neo4j_driver", lambda *_args, **_kwargs: None)

    yield

    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()


@pytest.fixture
def app() -> FastAPI:
    return app_main.create_application()


@pytest.fixture
def client(app: FastAPI):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
