from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.form100_dto import (
    Form100CreateRequest,
    Form100SignRequest,
    Form100UpdateRequest,
)
from app.application.services import reporting_service as reporting_service_module
from app.application.services.analytics_service import AnalyticsService
from app.application.services.form100_service import Form100Service
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


def make_create_request() -> Form100CreateRequest:
    return Form100CreateRequest(
        last_name="Иванов",
        first_name="Иван",
        middle_name="Иванович",
        birth_date=date(1992, 1, 2),
        rank="Рядовой",
        unit="1-я рота",
        dog_tag_number="A12345",
        injury_dt=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
        arrival_dt=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        first_aid_before=True,
        cause_category="Боевое",
        is_combat=True,
        diagnosis_text="Осколочное ранение правого плеча",
        diagnosis_code="S40.0",
        triage="Жёлтый",
    )


def test_form100_create_update_sign_and_audit(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100.db")
    admin_id, operator_id = seed_users(session_factory)
    _ = admin_id
    service = Form100Service(session_factory=session_factory)

    created = service.create_card(make_create_request(), actor_id=operator_id)
    assert created.id
    assert created.status == "DRAFT"
    assert created.version == 1

    updated = service.update_card(
        created.id,
        Form100UpdateRequest(diagnosis_text="Осколочное ранение правого плеча, состояние стабильное"),
        actor_id=operator_id,
        expected_version=1,
    )
    assert updated.version == 2
    assert "стабильное" in updated.diagnosis_text

    with pytest.raises(ValueError, match="Конфликт версий"):
        service.update_card(
            created.id,
            Form100UpdateRequest(diagnosis_text="stale"),
            actor_id=operator_id,
            expected_version=1,
        )

    signed = service.sign_card(
        created.id,
        Form100SignRequest(signed_by="operator", seal_applied=True),
        actor_id=operator_id,
        expected_version=2,
    )
    assert signed.status == "SIGNED"
    assert signed.version == 3

    with pytest.raises(ValueError, match="подписанной"):
        service.update_card(
            created.id,
            Form100UpdateRequest(diagnosis_text="after sign"),
            actor_id=operator_id,
            expected_version=3,
        )

    with session_factory() as session:
        audit_rows = (
            session.query(models.AuditLog)
            .filter(models.AuditLog.entity_type == "form100", models.AuditLog.entity_id == created.id)
            .all()
        )
    assert len(audit_rows) >= 3
    assert any(row.action == "create_form100" for row in audit_rows)
    assert any(row.action == "update_form100" for row in audit_rows)
    assert any(row.action == "sign_form100" for row in audit_rows)


def test_form100_operator_cannot_delete(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_acl.db")
    _admin_id, operator_id = seed_users(session_factory)
    service = Form100Service(session_factory=session_factory)
    card = service.create_card(make_create_request(), actor_id=operator_id)

    with pytest.raises(ValueError, match="администратору"):
        service.delete_card(card.id, actor_id=operator_id)


def test_form100_exchange_and_reporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    session_factory = make_session_factory(tmp_path / "form100_exchange.db")
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts")
    admin_id, _operator_id = seed_users(session_factory)
    form100_service = Form100Service(session_factory=session_factory)
    created = form100_service.create_card(make_create_request(), actor_id=admin_id)

    zip_path = tmp_path / "form100.zip"
    export_result = form100_service.export_package_zip(
        file_path=zip_path,
        actor_id=admin_id,
        card_id=created.id,
        exported_by="admin",
    )
    assert zip_path.exists()
    assert export_result["counts"]["form100_card"] == 1

    form100_service.delete_card(created.id, actor_id=admin_id)
    import_result = form100_service.import_package_zip(file_path=zip_path, actor_id=admin_id, mode="merge")
    assert import_result["summary"]["added"] == 1

    cards = form100_service.list_cards(limit=10, offset=0)
    assert len(cards) == 1
    restored_id = cards[0].id

    analytics_service = AnalyticsService(session_factory=session_factory)
    reporting_service = ReportingService(
        analytics_service=analytics_service,
        form100_service=form100_service,
        session_factory=session_factory,
    )
    pdf_path = tmp_path / "form100.pdf"
    report_result = reporting_service.export_form100_pdf(
        card_id=restored_id,
        file_path=pdf_path,
        actor_id=admin_id,
    )
    assert pdf_path.exists()
    assert Path(str(report_result["artifact_path"])).exists()

    with session_factory() as session:
        exchange_rows = session.query(models.DataExchangePackage).all()
        report_rows = session.query(models.ReportRun).filter(models.ReportRun.report_type == "form100").all()
    assert any(row.package_format == "form100+zip" for row in exchange_rows)
    assert len(report_rows) == 1
