from __future__ import annotations

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


def _make_service(db_path: Path) -> PatientService:
    session_factory = make_session_factory(db_path)
    fts_manager = FtsManager(session_factory=session_factory)
    assert fts_manager.ensure_all() is True
    return PatientService(
        patient_repo=PatientRepository(),
        session_factory=session_factory,
        fts_manager=fts_manager,
    )


def test_create_or_get_updates_existing_identity_fields(tmp_path: Path) -> None:
    service = _make_service(tmp_path / "patient_create_or_get.db")
    request = PatientCreateRequest(
        full_name="Ivan Ivanov",
        dob=date(2001, 1, 1),
        sex="M",
        category=MilitaryCategory.CIVILIAN_STAFF.value,
        military_unit="unit-1",
        military_district="district-1",
    )
    first = service.create_or_get(request)

    updated_request = PatientCreateRequest(
        full_name="Ivan Ivanov",
        dob=date(2001, 1, 1),
        sex="M",
        category=MilitaryCategory.PRIVATE.value,
        military_unit="unit-2",
        military_district="district-2",
    )
    second = service.create_or_get(updated_request)

    assert first.id == second.id
    reloaded = service.get_by_id(first.id)
    assert reloaded.category == MilitaryCategory.PRIVATE.value
    assert reloaded.military_unit == "unit-2"
    assert reloaded.military_district == "district-2"


def test_search_by_name_fallback_works_when_patients_fts_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "patient_search_fallback.db"
    service = _make_service(db_path)
    created = service.create_or_get(
        PatientCreateRequest(
            full_name="Petr Petrov",
            dob=date(2000, 2, 2),
            sex="M",
            category=MilitaryCategory.CIVILIAN_STAFF.value,
            military_unit="unit",
            military_district="district",
        )
    )

    session_factory = make_session_factory(db_path)
    with session_factory() as session:
        session.execute(text("DROP TABLE IF EXISTS patients_fts"))

    results = service.search_by_name("Petr")
    assert len(results) == 1
    assert results[0].id == created.id


def test_update_details_respects_none_policy_for_fields(tmp_path: Path) -> None:
    service = _make_service(tmp_path / "patient_update_details.db")
    created = service.create_or_get(
        PatientCreateRequest(
            full_name="Sergey Sergeev",
            dob=date(2001, 3, 3),
            sex="M",
            category=MilitaryCategory.CIVILIAN_STAFF.value,
            military_unit="unit-1",
            military_district="district-1",
        )
    )

    service.update_details(
        created.id,
        full_name="Sergey S.",
        dob=date(2001, 3, 3),
        sex="U",
        category=None,
        military_unit=None,
        military_district=None,
    )

    updated = service.get_by_id(created.id)
    assert updated.full_name == "Sergey S."
    assert updated.sex == "U"
    assert updated.category == MilitaryCategory.CIVILIAN_STAFF.value
    assert updated.military_unit is None
    assert updated.military_district is None
