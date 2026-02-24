from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services import reference_service as reference_service_module
from app.application.services.reference_service import ReferenceService
from app.infrastructure.db import models_sqlalchemy as models
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


def test_department_and_material_type_crud_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "reference_crud.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    service.add_department("ICU")
    service.add_material_type("BLOOD", "Blood")

    departments = service.list_departments()
    material_types = service.list_material_types()
    assert len(departments) == 1
    assert len(material_types) == 1

    dep_id = cast(int, departments[0].id)
    mt_id = cast(int, material_types[0].id)
    assert dep_id is not None
    assert mt_id is not None

    service.update_department(dep_id, "ICU-2")
    service.update_material_type(mt_id, "BLOOD-2", "Blood 2")

    departments = service.list_departments()
    material_types = service.list_material_types()
    assert departments[0].name == "ICU-2"
    assert material_types[0].code == "BLOOD-2"
    assert material_types[0].name == "Blood 2"

    service.delete_department(dep_id)
    service.delete_material_type(mt_id)
    assert service.list_departments() == []
    assert service.list_material_types() == []


def test_reference_service_validation_and_not_found_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_validation.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    with pytest.raises(ValueError):
        service.add_department("")
    with pytest.raises(ValueError):
        service.add_material_type("", "Name")
    with pytest.raises(ValueError):
        service.add_icd10("", "Title")

    with pytest.raises(ValueError):
        service.update_department(9999, "Missing")
    with pytest.raises(ValueError):
        service.update_material_type(9999, "C", "Missing")
    with pytest.raises(ValueError):
        service.update_icd10("A00", "Missing")

    with session_factory() as session:
        session.add(models.RefICD10(code="A00", title="Initial"))

    service.update_icd10("A00", "Updated")
    icd10 = service.list_icd10()
    assert len(icd10) == 1
    assert icd10[0].title == "Updated"
