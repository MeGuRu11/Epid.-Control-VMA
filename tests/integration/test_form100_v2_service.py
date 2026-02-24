from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.form100_v2_dto import (
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100SignV2Request,
    Form100UpdateV2Request,
)
from app.application.services import reporting_service as reporting_service_module
from app.application.services.analytics_service import AnalyticsService
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.application.services.reporting_service import ReportingService
from app.infrastructure.db import models_sqlalchemy as models
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


def seed_users(session_factory: Callable[[], AbstractContextManager[Session]]) -> tuple[int, int]:
    repo = UserRepository()
    with session_factory() as session:
        admin = repo.create(session, login="admin", password_hash="x", role="admin")
        operator = repo.create(session, login="operator", password_hash="x", role="operator")
        session.flush()
        return cast(int, admin.id), cast(int, operator.id)


def make_create_request() -> Form100CreateV2Request:
    return Form100CreateV2Request(
        main_full_name="Иванов Иван Иванович",
        main_unit="1-я рота",
        main_id_tag="A12345",
        main_diagnosis="Осколочное ранение правого плеча",
        birth_date=date(1992, 1, 2),
        data=Form100DataV2Dto.model_validate(
            {
            "main": {
                "main_full_name": "Иванов Иван Иванович",
                "main_unit": "1-я рота",
                "main_id_tag": "A12345",
            },
            "bottom": {"main_diagnosis": "Осколочное ранение правого плеча"},
            "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
            "flags": {"flag_emergency": True, "flag_radiation": False, "flag_sanitation": False},
            "bodymap_gender": "M",
            "bodymap_annotations": [
                {
                    "annotation_type": "WOUND_X",
                    "x": 0.42,
                    "y": 0.36,
                    "silhouette": "male_front",
                    "note": "",
                    "shape_json": {},
                }
            ],
            "bodymap_tissue_types": ["мягкие ткани"],
        },
        ),
    )


def test_form100_v2_create_update_sign_audit(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_v2.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(make_create_request(), actor_id=operator_id)
    assert created.id
    assert created.status == "DRAFT"
    assert created.version == 1

    updated = service.update_card(
        created.id,
        Form100UpdateV2Request(main_diagnosis="Осколочное ранение правого плеча, состояние стабильное"),
        actor_id=operator_id,
        expected_version=1,
    )
    assert updated.version == 2
    assert "стабильное" in (updated.main_diagnosis or "")

    with pytest.raises(ValueError, match="Конфликт версий"):
        service.update_card(
            created.id,
            Form100UpdateV2Request(main_diagnosis="stale"),
            actor_id=operator_id,
            expected_version=1,
        )

    signed = service.sign_card(
        created.id,
        Form100SignV2Request(signed_by="operator"),
        actor_id=operator_id,
        expected_version=2,
    )
    assert signed.status == "SIGNED"
    assert signed.version == 3

    with pytest.raises(ValueError, match="подписанной"):
        service.update_card(
            created.id,
            Form100UpdateV2Request(main_diagnosis="after sign"),
            actor_id=operator_id,
            expected_version=3,
        )

    with session_factory() as session:
        audit_rows = (
            session.query(models.AuditLog)
            .filter(models.AuditLog.entity_type == "form100", models.AuditLog.entity_id == created.id)
            .all()
        )
    actions = {row.action for row in audit_rows}
    assert "form100_create" in actions
    assert "form100_update" in actions
    assert "form100_sign" in actions


def test_form100_v2_exchange_and_reporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "form100_v2_exchange.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)
    created = service.create_card(make_create_request(), actor_id=operator_id)

    zip_path = tmp_path / "form100_v2.zip"
    export_result = service.export_package_zip(
        file_path=zip_path,
        actor_id=admin_id,
        card_id=created.id,
        exported_by="admin",
    )
    assert zip_path.exists()
    assert export_result["counts"]["form100"] == 1

    service.delete_card(created.id, actor_id=admin_id)
    import_result = service.import_package_zip(file_path=zip_path, actor_id=admin_id, mode="merge")
    assert import_result["summary"]["added"] == 1

    cards = service.list_cards(limit=10, offset=0)
    assert len(cards) == 1
    restored_id = cards[0].id

    analytics_service = AnalyticsService(session_factory=session_factory)
    reporting_service = ReportingService(
        analytics_service=analytics_service,
        form100_v2_service=service,
        session_factory=session_factory,
    )
    pdf_path = tmp_path / "form100_v2.pdf"
    report_result = reporting_service.export_form100_v2_pdf(
        card_id=restored_id,
        file_path=pdf_path,
        actor_id=admin_id,
    )
    assert pdf_path.exists()
    assert Path(str(report_result["artifact_path"])).exists()

    with session_factory() as session:
        exchange_rows = session.query(models.DataExchangePackage).all()
        report_rows = session.query(models.ReportRun).filter(models.ReportRun.report_type == "form100_v2").all()
    assert any(row.package_format == "form100_v2+zip" for row in exchange_rows)
    assert len(report_rows) == 1
