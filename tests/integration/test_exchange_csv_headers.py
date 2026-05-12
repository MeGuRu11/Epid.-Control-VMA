from __future__ import annotations

import csv
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services import exchange_service as exchange_module
from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base, User


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


def seed_actor(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    with session_factory() as session:
        actor = User(login="exchange_admin", password_hash="hash", role="admin", is_active=True)
        session.add(actor)
        session.flush()
        return int(actor.id)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def _seed_lab_sample(
    session_factory: Callable[[], AbstractContextManager[Session]],
    *,
    actor_id: int,
) -> None:
    with session_factory() as session:
        patient = models.Patient(
            full_name="Петров Пётр Петрович",
            dob=date(1990, 5, 12),
            sex="M",
            category="офицер",
            military_unit="1 батальон",
            military_district="ЗВО",
        )
        material = models.RefMaterialType(code="BLD", name="Кровь")
        session.add_all([patient, material])
        session.flush()
        session.add(
            models.LabSample(
                patient_id=patient.id,
                lab_no="LAB-0001",
                material_type_id=material.id,
                taken_at=datetime(2026, 5, 12, 8, 30, tzinfo=UTC),
                growth_flag=1,
                qc_due_at=datetime(2026, 5, 13, 8, 30, tzinfo=UTC),
                qc_status="valid",
                created_by=actor_id,
            )
        )


def _seed_sanitary_sample(
    session_factory: Callable[[], AbstractContextManager[Session]],
    *,
    actor_id: int,
) -> None:
    with session_factory() as session:
        department = models.Department(name="Хирургия")
        session.add(department)
        session.flush()
        session.add(
            models.SanitarySample(
                department_id=department.id,
                room="101",
                sampling_point="Раковина",
                lab_no="SAN-0001",
                taken_at=datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
                growth_flag=0,
                created_by=actor_id,
            )
        )


def test_lab_sample_csv_has_qc_due_at_localized(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_qc_due_at.db")
    actor_id = seed_actor(session_factory)
    _seed_lab_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "lab_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "lab_sample", actor_id=actor_id)

    headers, _rows = _read_csv(csv_path)
    assert "Срок QC" in headers
    assert "qc_due_at" not in headers


def test_lab_sample_csv_has_qc_status_localized(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_qc_status.db")
    actor_id = seed_actor(session_factory)
    _seed_lab_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "lab_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "lab_sample", actor_id=actor_id)

    headers, _rows = _read_csv(csv_path)
    assert "Статус QC" in headers
    assert "qc_status" not in headers


def test_lab_sample_csv_has_material_type_name_column(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_material_name.db")
    actor_id = seed_actor(session_factory)
    _seed_lab_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "lab_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "lab_sample", actor_id=actor_id)

    headers, rows = _read_csv(csv_path)
    assert headers[headers.index("ID типа материала") + 1] == "Тип материала"
    assert rows[0]["Тип материала"] == "BLD — Кровь"


def test_lab_sample_csv_growth_flag_header_is_rost(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_growth_flag.db")
    actor_id = seed_actor(session_factory)
    _seed_lab_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "lab_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "lab_sample", actor_id=actor_id)

    headers, _rows = _read_csv(csv_path)
    assert "Рост" in headers
    assert "Рост (0/1)" not in headers


def test_sanitary_sample_csv_has_department_name_column(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "san_department_name.db")
    actor_id = seed_actor(session_factory)
    _seed_sanitary_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "sanitary_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "sanitary_sample", actor_id=actor_id)

    headers, rows = _read_csv(csv_path)
    assert headers[headers.index("ID отделения") + 1] == "Отделение"
    assert rows[0]["Отделение"] == "Хирургия"


def test_csv_created_by_name_column_contains_username(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "lab_created_by_name.db")
    actor_id = seed_actor(session_factory)
    _seed_lab_sample(session_factory, actor_id=actor_id)
    csv_path = tmp_path / "lab_sample.csv"

    ExchangeService(session_factory=session_factory).export_csv(csv_path, "lab_sample", actor_id=actor_id)

    headers, rows = _read_csv(csv_path)
    assert headers[headers.index("Создал (ID)") + 1] == "Создал"
    assert rows[0]["Создал"] == "exchange_admin"


def test_lab_sample_pdf_headers_match_csv_headers(tmp_path: Path, monkeypatch: Any) -> None:
    session_factory = make_session_factory(tmp_path / "lab_pdf_headers.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    captured_headers: list[str] = []
    original_table = exchange_module.Table

    def capture_table(data: list[list[object]], *args: object, **kwargs: object) -> object:
        captured_headers[:] = [
            cast(str, cell.getPlainText()) if hasattr(cell, "getPlainText") else str(cell)
            for cell in data[0]
        ]
        return original_table(data, *args, **kwargs)

    monkeypatch.setattr(exchange_module, "Table", capture_table)
    csv_path = tmp_path / "lab_sample.csv"
    pdf_path = tmp_path / "lab_sample.pdf"

    service.export_csv(csv_path, "lab_sample", actor_id=actor_id)
    service.export_pdf(pdf_path, "lab_sample", actor_id=actor_id)

    csv_headers, _rows = _read_csv(csv_path)
    assert captured_headers == csv_headers
    assert "Срок QC" in captured_headers
    assert "Статус QC" in captured_headers
    assert "Тип материала" in captured_headers
