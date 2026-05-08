from __future__ import annotations

import csv
import json
from pathlib import Path

from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db import models_sqlalchemy as models
from tests.integration.test_exchange_service_import_reports import make_session_factory, seed_actor

PATIENT_COLUMNS = ["id", "full_name", "dob", "sex", "category", "military_unit", "military_district"]


def test_csv_export_then_import_accepts_ru_headers_and_bom(tmp_path: Path) -> None:
    source_factory = make_session_factory(tmp_path / "csv_roundtrip_source.db")
    source_actor = seed_actor(source_factory)
    source_service = ExchangeService(session_factory=source_factory)
    csv_path = tmp_path / "patients_export.csv"
    with source_factory() as session:
        session.add(
            models.Patient(
                full_name="Round Trip Patient",
                sex="M",
                category="control",
                military_unit="unit",
                military_district="district",
            )
        )

    source_service.export_csv(csv_path, "patients", actor_id=source_actor)
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")

    target_factory = make_session_factory(tmp_path / "csv_roundtrip_target.db")
    target_actor = seed_actor(target_factory)
    target_service = ExchangeService(session_factory=target_factory)

    result = target_service.import_csv(csv_path, "patients", actor_id=target_actor, mode="merge")

    assert result["error_count"] == 0
    assert result["summary"]["total"] == 1
    assert result["summary"]["imported"] == 1
    assert result["summary"]["skipped"] == 0
    assert result["summary"]["errors"] == 0
    with target_factory() as session:
        patients = session.query(models.Patient).all()
    assert len(patients) == 1
    assert str(patients[0].full_name) == "Round Trip Patient"


def test_csv_import_accumulates_structured_row_errors_for_en_headers(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "csv_structured_errors.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    csv_path = tmp_path / "invalid_patients.csv"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(PATIENT_COLUMNS)
        writer.writerow([1, "Valid Patient", "1990-01-01", "M", "cat", "unit", "district"])
        writer.writerow(["", "Missing Id", "1991-01-01", "F", "cat", "unit", "district"])
        writer.writerow([2, "Bad Date", "bad-date", "M", "cat", "unit", "district"])
        writer.writerow([3, "Bad Sex", "1992-02-02", "Q", "cat", "unit", "district"])
        writer.writerow([1, "Duplicate Id", "1993-03-03", "M", "cat", "unit", "district"])
        writer.writerow([4, "Short Row"])

    result = service.import_csv(csv_path, "patients", actor_id=actor_id, mode="merge")

    assert result["count"] == 1
    assert result["summary"]["total"] == 6
    assert result["summary"]["imported"] == 1
    assert result["summary"]["skipped"] == 5
    assert result["summary"]["errors"] == 5
    assert [error["error_code"] for error in result["errors"]] == [
        "missing_required",
        "invalid_date_format",
        "invalid_enum_value",
        "duplicate_row",
        "row_length_mismatch",
    ]
    assert result["errors"][1]["field"] == "dob"
    assert result["errors"][1]["value"] == "bad-date"
    assert "list index out of range" not in json.dumps(result["errors"], ensure_ascii=False)

    error_log_path = Path(str(result["error_log_path"]))
    payload = json.loads(error_log_path.read_text(encoding="utf-8"))
    assert payload["summary"]["total"] == 6
    assert payload["summary"]["imported"] == 1
    assert payload["summary"]["skipped"] == 5
    assert payload["summary"]["errors"] == 5
    assert payload["errors"][0]["error_code"] == "missing_required"


def test_csv_import_reports_malformed_csv_without_traceback(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "csv_malformed.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    csv_path = tmp_path / "malformed_patients.csv"
    csv_path.write_text(
        "id,full_name,dob,sex,category,military_unit,military_district\n"
        '1,"Broken row,1990-01-01,M,cat,unit,district' + "\n",
        encoding="utf-8-sig",
    )

    result = service.import_csv(csv_path, "patients", actor_id=actor_id, mode="merge")

    assert result["count"] == 0
    assert result["error_count"] == 1
    assert result["summary"]["total"] == 0
    assert result["summary"]["imported"] == 0
    assert result["summary"]["skipped"] == 0
    assert result["summary"]["errors"] == 1
    assert result["errors"][0]["error_code"] == "csv_parse_error"
    assert "Traceback" not in result["errors"][0]["message"]
