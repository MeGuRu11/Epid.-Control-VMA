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


def test_antibiotic_group_and_antibiotic_crud_with_search(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_catalog_abx.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    service.add_antibiotic_group("grp-1", "Group 1")
    group = service.list_antibiotic_groups()[0]
    group_id = cast(int, group.id)

    service.add_antibiotic("abx-1", "Antibiotic 1", group_id)
    antibiotics = service.search_antibiotics("Antibiotic")
    assert len(antibiotics) == 1
    abx = antibiotics[0]
    abx_id = cast(int, abx.id)
    assert abx.group_id == group_id

    service.update_antibiotic(abx_id, "abx-2", "Antibiotic 2", None)
    updated_abx = service.search_antibiotics("abx-2")
    assert len(updated_abx) == 1
    assert updated_abx[0].name == "Antibiotic 2"
    assert updated_abx[0].group_id is None

    service.update_antibiotic_group(group_id, "grp-2", "Group 2")
    groups = service.list_antibiotic_groups()
    assert len(groups) == 1
    assert groups[0].code == "grp-2"
    assert groups[0].name == "Group 2"

    service.delete_antibiotic(abx_id)
    assert service.list_antibiotics() == []
    service.delete_antibiotic_group(group_id)
    assert service.list_antibiotic_groups() == []


def test_microorganism_phage_ismp_and_icd10_crud(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_catalog_other.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    service.add_microorganism("micro-1", "Microbe 1", "tg1")
    microorganism = service.search_microorganisms("Microbe")[0]
    micro_id = cast(int, microorganism.id)
    service.update_microorganism(micro_id, "micro-2", "Microbe 2", "tg2")
    search_micro = service.search_microorganisms("micro-2")
    assert len(search_micro) == 1
    assert search_micro[0].name == "Microbe 2"
    service.delete_microorganism(micro_id)
    assert service.list_microorganisms() == []

    service.add_phage("phage-1", "Phage 1", True)
    phage = service.list_phages()[0]
    phage_id = cast(int, phage.id)
    service.update_phage(phage_id, "phage-2", "Phage 2", False)
    updated_phage = service.list_phages()[0]
    assert updated_phage.code == "phage-2"
    assert updated_phage.name == "Phage 2"
    assert updated_phage.is_active is False
    service.delete_phage(phage_id)
    assert service.list_phages() == []

    service.add_ismp_abbreviation("ismp-1", "ISMP 1", "desc")
    ismp = service.list_ismp_abbreviations()[0]
    ismp_id = cast(int, ismp.id)
    service.update_ismp_abbreviation(ismp_id, "ismp-2", "ISMP 2", "desc-2")
    updated_ismp = service.list_ismp_abbreviations()[0]
    assert updated_ismp.code == "ismp-2"
    assert updated_ismp.name == "ISMP 2"
    service.delete_ismp_abbreviation(ismp_id)
    assert service.list_ismp_abbreviations() == []

    service.add_icd10("A00", "Cholera")
    icd_rows = service.search_icd10("A00")
    assert len(icd_rows) == 1
    assert icd_rows[0].title == "Cholera"
    service.delete_icd10("A00")
    assert service.list_icd10() == []


def test_reference_service_catalog_update_not_found_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_catalog_not_found.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    with pytest.raises(ValueError):
        service.update_antibiotic(999, "abx", "ABX", None)
    with pytest.raises(ValueError):
        service.update_antibiotic_group(999, "grp", "Group")
    with pytest.raises(ValueError):
        service.update_microorganism(999, "micro", "Micro", None)
    with pytest.raises(ValueError):
        service.update_phage(999, "phage", "Phage", True)
    with pytest.raises(ValueError):
        service.update_ismp_abbreviation(999, "ismp", "ISMP", None)
