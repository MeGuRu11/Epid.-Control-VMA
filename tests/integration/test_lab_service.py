from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.lab_dto import LabSampleCreateRequest, LabSampleResultUpdate
from app.application.services.lab_service import LabService
from app.infrastructure.db.models_sqlalchemy import Base, LabSample, RefMaterialType, User


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


def seed_material(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    with session_factory() as session:
        mt = RefMaterialType(code="BLD", name="Кровь")
        session.add(mt)
        session.flush()
        return cast(int, mt.id)


def seed_actor(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    with session_factory() as session:
        actor = User(login="lab_admin", password_hash="hash", role="admin", is_active=True)
        session.add(actor)
        session.flush()
        return cast(int, actor.id)


def test_lab_sample_autonumber(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab.db")
    material_type_id = seed_material(session_factory)
    actor_id = seed_actor(session_factory)
    service = LabService(session_factory=session_factory)

    req = LabSampleCreateRequest(
        patient_id=1,
        emr_case_id=None,
        material_type_id=material_type_id,
        taken_at=datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC),
        study_kind="primary",
    )
    resp1 = service.create_sample(req, actor_id=actor_id)
    resp2 = service.create_sample(req, actor_id=actor_id)

    assert resp1.lab_no.startswith("BLD-20251215-")
    assert resp1.lab_no.endswith("-0001")
    assert resp2.lab_no.startswith("BLD-20251215-")
    assert resp2.lab_no.endswith("-0002")

    upd = LabSampleResultUpdate(
        growth_flag=1,
        growth_result_at=datetime(2025, 12, 16, 8, 0, 0, tzinfo=UTC),
    )
    resp_update = service.update_result(resp1.id, upd, actor_id=actor_id)
    assert resp_update.growth_flag == 1


def test_lab_sample_accepts_manual_identifier_fields(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_manual.db")
    material_type_id = seed_material(session_factory)
    actor_id = seed_actor(session_factory)
    service = LabService(session_factory=session_factory)

    req = LabSampleCreateRequest(
        patient_id=1,
        emr_case_id=None,
        lab_no="LAB-MANUAL-001",
        barcode="460700000001",
        material_type_id=material_type_id,
        material_location="Рана бедра",
        ordered_at=datetime(2025, 12, 15, 8, 0, 0, tzinfo=UTC),
        taken_at=datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC),
        study_kind="primary",
    )

    resp = service.create_sample(req, actor_id=actor_id)

    assert resp.lab_no == "LAB-MANUAL-001"
    assert resp.barcode == "460700000001"
    assert resp.material_location == "Рана бедра"

    with pytest.raises(ValueError, match="Лаб. номер"):
        service.create_sample(req, actor_id=actor_id)


def test_lab_sample_empty_optional_ordered_at_persists_as_null(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_null_dates.db")
    material_type_id = seed_material(session_factory)
    actor_id = seed_actor(session_factory)
    service = LabService(session_factory=session_factory)

    req = LabSampleCreateRequest(
        patient_id=1,
        emr_case_id=None,
        material_type_id=material_type_id,
        ordered_at=None,
        taken_at=datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC),
        study_kind="primary",
    )

    resp = service.create_sample(req, actor_id=actor_id)
    loaded = service.list_samples(patient_id=1)

    assert next(item for item in loaded if item.id == resp.id).ordered_at is None
    with session_factory() as session:
        stored = session.execute(select(LabSample.ordered_at).where(LabSample.id == resp.id)).scalar_one()
    assert stored is None
