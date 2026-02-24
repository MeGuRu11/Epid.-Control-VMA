from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.patient_dto import PatientCreateRequest
from app.application.services.patient_service import PatientService
from app.domain.constants import MilitaryCategory
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.patient_repo import PatientRepository


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


def test_patient_service_repairs_fts_after_table_drop(tmp_path: Path) -> None:
    db_path = tmp_path / "patient_fts_repair.db"
    session_factory = make_session_factory(db_path)
    fts_manager = FtsManager(session_factory=session_factory)
    assert fts_manager.ensure_all() is True

    service = PatientService(
        patient_repo=PatientRepository(),
        session_factory=session_factory,
        fts_manager=fts_manager,
    )
    created = service.create_or_get(
        PatientCreateRequest(
            full_name="Иванов Иван Иванович",
            dob=date(2000, 1, 1),
            sex="M",
            category=MilitaryCategory.CIVILIAN_STAFF.value,
            military_unit="unit",
            military_district="district",
        )
    )

    with session_factory() as session:
        session.execute(text("DROP TABLE IF EXISTS patients_fts"))

    service.update_details(
        created.id,
        full_name="Петров Петр Петрович",
        dob=date(2000, 1, 1),
        sex="M",
        category=MilitaryCategory.CIVILIAN_STAFF.value,
        military_unit="unit",
        military_district="district",
    )
    updated = service.get_by_id(created.id)
    assert updated.full_name == "Петров Петр Петрович"

    con = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        triggers = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
    finally:
        con.close()

    assert "patients_fts" in tables
    assert {"patients_ai", "patients_ad", "patients_au"}.issubset(triggers)
