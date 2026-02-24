from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

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


def test_seed_defaults_imports_groups_abx_micro_and_replaces_ismp(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_seed.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    seed_payload_v1 = {
        "antibiotic_groups": [{"code": "grp-a", "name": "Group A"}],
        "antibiotics": [{"code": "abx-a", "name": "Abx A", "group_code": "grp-a"}],
        "microorganisms": [{"code": "micro-a", "name": "Micro A", "taxon_group": "tg"}],
        "ismp_abbreviations": [{"code": "ismp-a", "name": "ISMP A", "description": "v1"}],
    }
    seed_payload_v2 = {
        "antibiotic_groups": [{"code": "grp-a", "name": "Group A"}],
        "antibiotics": [{"code": "abx-a", "name": "Abx A", "group_code": "grp-a"}],
        "microorganisms": [{"code": "micro-a", "name": "Micro A", "taxon_group": "tg"}],
        "ismp_abbreviations": [{"code": "ismp-b", "name": "ISMP B", "description": "v2"}],
    }

    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps(seed_payload_v1, ensure_ascii=False), encoding="utf-8")
    service.seed_defaults(seed_file)

    with session_factory() as session:
        groups = session.query(models.RefAntibioticGroup).all()
        antibiotics = session.query(models.RefAntibiotic).all()
        microbes = session.query(models.RefMicroorganism).all()
        ismp_rows = session.query(models.RefIsmpAbbreviation).all()

    assert len(groups) == 1
    assert len(antibiotics) == 1
    assert len(microbes) == 1
    assert len(ismp_rows) == 1
    assert antibiotics[0].group_id == groups[0].id
    assert ismp_rows[0].code == "ismp-a"

    seed_file.write_text(json.dumps(seed_payload_v2, ensure_ascii=False), encoding="utf-8")
    service.seed_defaults(seed_file)
    with session_factory() as session:
        ismp_rows = session.query(models.RefIsmpAbbreviation).order_by(models.RefIsmpAbbreviation.id).all()

    assert len(ismp_rows) == 1
    assert ismp_rows[0].code == "ismp-b"


def test_seed_defaults_if_empty_calls_seed_only_for_empty_target_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    session_factory = make_session_factory(tmp_path / "reference_seed_if_empty.db")
    monkeypatch.setattr(reference_service_module, "session_scope", session_factory)
    service = ReferenceService()

    called: list[str] = []
    monkeypatch.setattr(service, "seed_defaults", lambda seed_path=None: called.append("called"))
    service.seed_defaults_if_empty()
    assert called == ["called"]

    called.clear()
    with session_factory() as session:
        session.add(models.RefAntibioticGroup(code="grp-a", name="Group A"))
    service.seed_defaults_if_empty()
    assert called == []
