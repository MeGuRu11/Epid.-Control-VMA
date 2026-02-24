from __future__ import annotations

import csv
import json
import zipfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.security.sha256 import sha256_file


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


def test_import_csv_returns_error_report_and_log(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_csv_report.db")
    service = ExchangeService(session_factory=session_factory)
    csv_path = tmp_path / "patients.csv"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
        writer.writerow([1, "Иванов Иван", "2024-01-01", "M", "cat", "", ""])
        writer.writerow([2, "Петров Петр", "bad-date", "M", "cat", "", ""])

    result = service.import_csv(csv_path, "patients", mode="merge")

    assert result["count"] == 1
    assert result["error_count"] == 1
    assert result["summary"]["rows_total"] == 2
    assert result["summary"]["added"] == 1
    assert result["summary"]["errors"] == 1

    error_log_path = Path(str(result["error_log_path"]))
    assert error_log_path.exists()
    payload = json.loads(error_log_path.read_text(encoding="utf-8"))
    assert payload["errors_count"] == 1
    assert payload["errors"][0]["scope"] == "patients"

    with session_factory() as session:
        patients = session.query(models.Patient).all()
    assert len(patients) == 1
    assert patients[0].full_name == "Иванов Иван"


def test_import_excel_returns_error_report_and_log(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_excel_report.db")
    service = ExchangeService(session_factory=session_factory)
    xlsx_path = tmp_path / "import.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "patients"
    ws.append(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
    ws.append([1, "Сидоров Сидор", "2024-01-01", "M", "cat", "", ""])
    ws.append([2, "Смирнов Семен", "bad-date", "M", "cat", "", ""])
    wb.save(xlsx_path)

    result = service.import_excel(xlsx_path, mode="merge")

    assert result["counts"]["patients"] == 2
    assert result["details"]["patients"]["added"] == 1
    assert result["details"]["patients"]["errors"] == 1
    assert result["summary"]["errors"] == 1

    error_log_path = Path(str(result["error_log_path"]))
    assert error_log_path.exists()
    payload = json.loads(error_log_path.read_text(encoding="utf-8"))
    assert payload["errors_count"] == 1
    assert payload["errors"][0]["scope"] == "patients"

    with session_factory() as session:
        patients = session.query(models.Patient).all()
    assert len(patients) == 1
    assert patients[0].full_name == "Сидоров Сидор"


def test_import_zip_returns_nested_import_error_report(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_zip_report.db")
    service = ExchangeService(session_factory=session_factory)
    xlsx_path = tmp_path / "export.xlsx"
    zip_path = tmp_path / "import.zip"

    wb = Workbook()
    ws = wb.active
    ws.title = "patients"
    ws.append(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
    ws.append([1, "Кузнецов Кирилл", "2024-01-01", "M", "cat", "", ""])
    ws.append([2, "Федоров Федор", "bad-date", "M", "cat", "", ""])
    wb.save(xlsx_path)

    manifest = {
        "schema_version": "1.0",
        "files": [{"name": "export.xlsx", "sha256": sha256_file(xlsx_path)}],
    }
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(xlsx_path, arcname="export.xlsx")
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))

    result = service.import_zip(zip_path, actor_id=None, mode="merge")

    assert result["error_count"] == 1
    assert result["summary"]["errors"] == 1
    error_log_path = Path(str(result["error_log_path"]))
    assert error_log_path.exists()
    payload = json.loads(error_log_path.read_text(encoding="utf-8"))
    assert payload["source_file"] == str(zip_path)
    assert payload["errors_count"] == 1
