from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.emz_dto import EmzCreateRequest, EmzVersionPayload
from app.application.services.emz_service import EmzService
from app.domain.constants import MilitaryCategory
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.user_repo import UserRepository


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


def seed_admin(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    user_repo = UserRepository()
    with session_factory() as session:
        admin = user_repo.create(session, login="admin", password_hash="$2b$12$abcdefghijklmnopqrstuv", role="admin")
        session.flush()
        return cast(int, admin.id)


def seed_admin_and_operator(session_factory: Callable[[], AbstractContextManager[Session]]) -> tuple[int, int]:
    user_repo = UserRepository()
    with session_factory() as session:
        admin = user_repo.create(
            session,
            login="admin",
            password_hash="$2b$12$abcdefghijklmnopqrstuv",
            role="admin",
        )
        operator = user_repo.create(
            session,
            login="operator",
            password_hash="$2b$12$abcdefghijklmnopqrstuv",
            role="operator",
        )
        session.flush()
        return cast(int, admin.id), cast(int, operator.id)


def test_create_emz_case(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "emr.db")
    actor_id = seed_admin(session_factory)
    service = EmzService(session_factory=session_factory)

    payload = EmzVersionPayload(
        admission_date=datetime(2025, 12, 15, 10, 0, tzinfo=UTC),
        injury_date=datetime(2025, 12, 10, 9, 0, tzinfo=UTC),
        outcome_date=None,
        severity="moderate",
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
    )

    req = EmzCreateRequest(
        patient_full_name="РРІР°РЅРѕРІ РРІР°РЅ",
        patient_dob=date(1990, 1, 1),
        patient_sex="M",
        patient_category="РЎРѕР»РґР°С‚",
        patient_military_unit=None,
        patient_military_district=None,
        hospital_case_no="CASE-001",
        department_id=None,
        payload=payload,
    )

    resp = service.create_emr(req, actor_id=actor_id)
    assert resp.id > 0
    assert resp.version_no == 1
    assert resp.days_to_admission == 5


def test_create_emz_invalid_outcome_before_injury(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "emr_invalid.db")
    actor_id = seed_admin(session_factory)
    service = EmzService(session_factory=session_factory)

    payload = EmzVersionPayload(
        admission_date=None,
        injury_date=datetime(2025, 12, 15, 10, 0, tzinfo=UTC),
        outcome_date=datetime(2025, 12, 10, 10, 0, tzinfo=UTC),
        severity="moderate",
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
    )

    req = EmzCreateRequest(
        patient_full_name="Ivan Ivanov",
        patient_dob=date(1990, 1, 1),
        patient_sex="M",
        patient_category=MilitaryCategory.OTHER.value,
        patient_military_unit=None,
        patient_military_district=None,
        hospital_case_no="CASE-INVALID",
        department_id=None,
        payload=payload,
    )

    with pytest.raises(ValueError, match="Дата исхода не может быть раньше даты травмы"):
        service.create_emr(req, actor_id=actor_id)


def test_delete_emz_requires_admin_and_writes_audit(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "emr_delete.db")
    admin_id, operator_id = seed_admin_and_operator(session_factory)
    service = EmzService(session_factory=session_factory)

    payload = EmzVersionPayload(
        admission_date=datetime(2025, 12, 15, 10, 0, tzinfo=UTC),
        injury_date=datetime(2025, 12, 10, 9, 0, tzinfo=UTC),
        outcome_date=None,
        severity="moderate",
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
    )
    req = EmzCreateRequest(
        patient_full_name="Петров Петр",
        patient_dob=date(1991, 1, 1),
        patient_sex="M",
        patient_category=MilitaryCategory.OTHER.value,
        patient_military_unit=None,
        patient_military_district=None,
        hospital_case_no="CASE-DELETE-001",
        department_id=None,
        payload=payload,
    )
    created = service.create_emr(req, actor_id=admin_id)

    with pytest.raises(ValueError, match="администратору"):
        service.delete_emr(created.id, actor_id=operator_id)

    with session_factory() as session:
        assert session.get(models.EmrCase, created.id) is not None

    service.delete_emr(created.id, actor_id=admin_id)

    with session_factory() as session:
        assert session.get(models.EmrCase, created.id) is None
        event = (
            session.query(models.AuditLog)
            .filter(
                models.AuditLog.entity_type == "emr_case",
                models.AuditLog.entity_id == str(created.id),
                models.AuditLog.action == "delete_emr",
            )
            .one_or_none()
        )
        assert event is not None
        assert event.user_id == admin_id

