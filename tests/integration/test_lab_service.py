from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.lab_dto import LabSampleCreateRequest, LabSampleResultUpdate
from app.application.services.lab_service import LabService
from app.infrastructure.db.models_sqlalchemy import Base, RefMaterialType


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


def test_lab_sample_autonumber(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab.db")
    material_type_id = seed_material(session_factory)
    service = LabService(session_factory=session_factory)

    req = LabSampleCreateRequest(
        patient_id=1,
        emr_case_id=None,
        material_type_id=material_type_id,
        taken_at=datetime(2025, 12, 15, 10, 0, 0, tzinfo=UTC),
        study_kind="primary",
    )
    resp1 = service.create_sample(req)
    resp2 = service.create_sample(req)

    assert resp1.lab_no.startswith("BLD-20251215-")
    assert resp1.lab_no.endswith("-0001")
    assert resp2.lab_no.startswith("BLD-20251215-")
    assert resp2.lab_no.endswith("-0002")

    # update result
    upd = LabSampleResultUpdate(
        growth_flag=1,
        growth_result_at=datetime(2025, 12, 16, 8, 0, 0, tzinfo=UTC),
    )
    resp_update = service.update_result(resp1.id, upd, actor_id=None)
    assert resp_update.growth_flag == 1
