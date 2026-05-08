from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path
from typing import cast

from openpyxl import Workbook

from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.security.sha256 import sha256_file
from tests.integration.test_exchange_service_import_reports import make_session_factory, seed_actor


def _audit_payloads(session_factory) -> list[dict[str, object]]:
    with session_factory() as session:
        rows = (
            session.query(models.AuditLog)
            .filter(models.AuditLog.entity_type == "exchange")
            .order_by(models.AuditLog.id.asc())
            .all()
        )
    return [json.loads(str(row.payload_json)) for row in rows]


def _write_patient_xlsx(path: Path, patient_id: int, full_name: str) -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "patients"
    ws.append(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
    ws.append([patient_id, full_name, "1990-01-01", "M", "cat", "unit", "district"])
    wb.save(path)


def test_exchange_exports_create_audit_events(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_export_audit.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    with session_factory() as session:
        session.add(models.Patient(full_name="Audit Export", sex="M", category="cat"))

    excel_path = tmp_path / "full.xlsx"
    zip_path = tmp_path / "full.zip"
    csv_path = tmp_path / "patients.csv"
    pdf_path = tmp_path / "patients.pdf"
    json_path = tmp_path / "full.json"

    service.export_excel(excel_path, exported_by="exchange_admin", actor_id=actor_id)
    service.export_zip(zip_path, exported_by="exchange_admin", actor_id=actor_id)
    service.export_csv(csv_path, "patients", actor_id=actor_id)
    service.export_pdf(pdf_path, "patients", actor_id=actor_id)
    service.export_json(json_path, exported_by="exchange_admin", actor_id=actor_id)

    payloads = _audit_payloads(session_factory)
    assert [payload["action"] for payload in payloads] == ["data_export"] * 5
    assert [payload["format"] for payload in payloads] == ["excel", "zip", "csv", "pdf", "json"]
    assert payloads[0]["scope_tables"]
    assert "patients" in cast(list[str], payloads[0]["scope_tables"])
    assert cast(list[str], payloads[2]["scope_tables"]) == ["patients"]
    assert payloads[2]["rows_affected"] == 1
    assert payloads[2]["file_sha256"] == sha256_file(csv_path)
    assert all(payload["error_summary"] is None for payload in payloads)


def test_exchange_imports_create_success_and_failed_audit_events(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_import_audit.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)

    csv_path = tmp_path / "patients.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
        writer.writerow([1, "CSV Import", "1990-01-01", "M", "cat", "unit", "district"])
    service.import_csv(csv_path, "patients", actor_id=actor_id, mode="merge")

    invalid_csv_path = tmp_path / "patients_invalid.csv"
    with invalid_csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"])
        writer.writerow([2, "Bad Date", "bad-date", "M", "cat", "unit", "district"])
    service.import_csv(invalid_csv_path, "patients", actor_id=actor_id, mode="merge")

    xlsx_path = tmp_path / "patients.xlsx"
    _write_patient_xlsx(xlsx_path, 3, "Excel Import")
    service.import_excel(xlsx_path, actor_id=actor_id, mode="merge")

    zip_payload_path = tmp_path / "zip_payload.xlsx"
    zip_path = tmp_path / "patients.zip"
    _write_patient_xlsx(zip_payload_path, 4, "Zip Import")
    manifest = {"schema_version": "1.0", "files": [{"name": "export.xlsx", "sha256": sha256_file(zip_payload_path)}]}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(zip_payload_path, arcname="export.xlsx")
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
    service.import_zip(zip_path, actor_id=actor_id, mode="merge")

    json_path = tmp_path / "patients.json"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "data": {
                    "patients": [
                        {
                            "id": 5,
                            "full_name": "JSON Import",
                            "dob": "1990-01-01",
                            "sex": "M",
                            "category": "cat",
                            "military_unit": "unit",
                            "military_district": "district",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    service.import_json(json_path, actor_id=actor_id, mode="merge")

    payloads = _audit_payloads(session_factory)
    assert [payload["action"] for payload in payloads] == [
        "data_import",
        "data_import_failed",
        "data_import",
        "data_import",
        "data_import",
    ]
    assert [payload["format"] for payload in payloads] == ["csv", "csv", "excel", "zip", "json"]
    assert cast(list[str], payloads[0]["scope_tables"]) == ["patients"]
    assert payloads[0]["rows_affected"] == 1
    assert payloads[1]["rows_affected"] == 0
    assert payloads[1]["error_summary"] == {"errors_count": 1, "first_error_code": "invalid_date_format"}
    assert cast(list[str], payloads[-1]["scope_tables"]) == ["patients"]
