from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import Base


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
    )

    @contextmanager
    def _session_scope() -> Iterator[Session]:
        session: Session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session_scope


def _sqlite_tables(db_path: Path) -> set[str]:
    con = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]
            for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        con.close()


def _sqlite_triggers(db_path: Path) -> set[str]:
    con = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
    finally:
        con.close()


def test_fts_manager_ensure_all_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "fts_idempotent.db"
    session_factory = make_session_factory(db_path)
    manager = FtsManager(session_factory=session_factory)

    assert manager.ensure_all() is True
    assert manager.ensure_all() is True

    tables = _sqlite_tables(db_path)
    triggers = _sqlite_triggers(db_path)

    assert "patients_fts" in tables
    assert "ref_microorganisms_fts" in tables
    assert "ref_icd10_fts" in tables
    assert {"patients_ai", "patients_ad", "patients_au"}.issubset(triggers)
    assert {"ref_microorganisms_ai", "ref_microorganisms_ad", "ref_microorganisms_au"}.issubset(triggers)
    assert {"ref_icd10_ai", "ref_icd10_ad", "ref_icd10_au"}.issubset(triggers)


def test_fts_manager_restores_patients_fts_after_manual_drop(tmp_path: Path) -> None:
    db_path = tmp_path / "fts_restore.db"
    session_factory = make_session_factory(db_path)
    manager = FtsManager(session_factory=session_factory)
    assert manager.ensure_all() is True

    with session_factory() as session:
        session.execute(text("DROP TABLE IF EXISTS patients_fts"))

    assert manager.ensure_all() is True
    tables = _sqlite_tables(db_path)
    triggers = _sqlite_triggers(db_path)

    assert "patients_fts" in tables
    assert {"patients_ai", "patients_ad", "patients_au"}.issubset(triggers)
