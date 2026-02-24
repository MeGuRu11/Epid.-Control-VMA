from __future__ import annotations

import json
import zipfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.form100_v2_dto import Form100CreateV2Request, Form100DataV2Dto
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.user_repo import UserRepository


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
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
    repo = UserRepository()
    with session_factory() as session:
        admin = repo.create(session, login="admin", password_hash="x", role="admin")
        session.flush()
        return cast(int, admin.id)


def make_create_request() -> Form100CreateV2Request:
    return Form100CreateV2Request(
        main_full_name="Petrov Petr",
        main_unit="Unit 2",
        main_id_tag="B777",
        main_diagnosis="Burn",
        birth_date=date(1993, 3, 4),
        data=Form100DataV2Dto.model_validate(
            {
                "main": {"main_full_name": "Petrov Petr", "main_unit": "Unit 2"},
                "bottom": {"main_diagnosis": "Burn"},
                "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
                "flags": {"flag_emergency": True, "flag_radiation": False, "flag_sanitation": False},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
            }
        ),
    )


def _tamper_zip_payload(source_zip: Path, target_zip: Path) -> None:
    with zipfile.ZipFile(source_zip, "r") as src:
        payloads: dict[str, bytes] = {name: src.read(name) for name in src.namelist()}
    envelope = json.loads(payloads["form100.json"].decode("utf-8"))
    cards = envelope.get("cards", [])
    if cards:
        cards[0]["main_diagnosis"] = "Tampered diagnosis"
    envelope["cards"] = cards
    payloads["form100.json"] = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, content in payloads.items():
            dst.writestr(name, content)


def test_form100_v2_zip_roundtrip_append_and_hash_validation(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_v2_zip.db")
    admin_id = seed_admin(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(make_create_request(), actor_id=admin_id)
    zip_path = tmp_path / "form100_v2_export.zip"
    service.export_package_zip(file_path=zip_path, actor_id=admin_id, card_id=created.id, exported_by="admin")

    append_result = service.import_package_zip(file_path=zip_path, actor_id=admin_id, mode="append")
    assert append_result["summary"]["rows_total"] == 1
    assert append_result["summary"]["added"] == 0
    assert append_result["summary"]["skipped"] == 1

    tampered_zip = tmp_path / "form100_v2_export_tampered.zip"
    _tamper_zip_payload(zip_path, tampered_zip)
    with pytest.raises(ValueError):
        service.import_package_zip(file_path=tampered_zip, actor_id=admin_id, mode="merge")
