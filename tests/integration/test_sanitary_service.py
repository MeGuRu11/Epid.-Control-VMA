from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.sanitary_dto import SanitarySampleCreateRequest, SanitarySampleResultUpdate
from app.application.services.sanitary_service import SanitaryService
from app.infrastructure.db.models_sqlalchemy import Base, Department


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


def seed_department(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    with session_factory() as session:
        dep = Department(name="Хирургия")
        session.add(dep)
        session.flush()
        return cast(int, dep.id)


def test_sanitary_sample(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "san.db")
    dep_id = seed_department(session_factory)
    service = SanitaryService(session_factory=session_factory)

    req = SanitarySampleCreateRequest(
        department_id=dep_id,
        sampling_point="Раковина",
        room="101",
        taken_at=datetime(2025, 12, 15, 9, 0, 0, tzinfo=UTC),
    )
    resp = service.create_sample(req)
    assert resp.lab_no.startswith("SAN-")

    upd = SanitarySampleResultUpdate(
        growth_flag=0,
        growth_result_at=datetime(2025, 12, 16, 8, 0, 0, tzinfo=UTC),
    )
    resp2 = service.update_result(resp.id, upd, actor_id=None)
    assert resp2.growth_flag == 0
