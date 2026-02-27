from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.application.services.auth_service import SessionContext
from app.infrastructure.db.engine import create_all, init_engine


@pytest.fixture()
def engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    eng = init_engine(db_path)
    create_all(eng)
    return eng


@pytest.fixture()
def admin_session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


@pytest.fixture()
def operator_session() -> SessionContext:
    return SessionContext(user_id=2, login="operator", role="operator")

