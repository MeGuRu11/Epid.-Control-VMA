from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_app_dirs
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.models_sqlalchemy import (
    EmrCase,
    EmrCaseVersion,
    Form100Card,
    LabSample,
    Patient,
    ReportRun,
    SanitarySample,
)
from ...infrastructure.db.repositories.exchange_repo import ExchangeRepo
from ...infrastructure.security.sha256 import file_sha256
from .analytics_service import AnalyticsService


class ExchangeService:
    def __init__(self, engine, session_ctx):
        self._engine = engine
        self._session = session_ctx
        self._repo = ExchangeRepo(engine)
        self._audit = AuditLogger(engine)
        self._analytics = AnalyticsService(engine, session_ctx)

    def _collect_export_data(self) -> dict:
        with Session(self._engine) as s:
            patients = [
                {
                    "id": row.id,
                    "full_name": row.full_name,
                    "dob": row.dob.isoformat() if row.dob else None,
                    "sex": row.sex,
                    "category": row.category,
                    "military_unit": row.military_unit,
                    "military_district": row.military_district,
                }
                for row in s.execute(select(Patient).order_by(Patient.id.asc())).scalars()
            ]
            emr_cases = [
                {
                    "id": row.id,
                    "patient_id": row.patient_id,
                    "hospital_case_no": row.hospital_case_no,
                    "department": row.department,
                    "department_id": row.department_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in s.execute(select(EmrCase).order_by(EmrCase.id.asc())).scalars()
            ]
            emr_versions = [
                {
                    "id": row.id,
                    "emr_case_id": row.emr_case_id,
                    "version_no": row.version_no,
                    "valid_from": row.valid_from.isoformat() if row.valid_from else None,
                    "valid_to": row.valid_to.isoformat() if row.valid_to else None,
                    "is_current": bool(row.is_current),
                    "admission_date": row.admission_date.isoformat() if row.admission_date else None,
                    "injury_date": row.injury_date.isoformat() if row.injury_date else None,
                    "outcome_date": row.outcome_date.isoformat() if row.outcome_date else None,
                    "severity": row.severity,
                    "sofa_score": row.sofa_score,
                    "notes": row.notes,
                }
                for row in s.execute(select(EmrCaseVersion).order_by(EmrCaseVersion.id.asc())).scalars()
            ]
            lab_samples = [
                {
                    "id": row.id,
                    "patient_id": row.patient_id,
                    "emr_case_id": row.emr_case_id,
                    "lab_no": row.lab_no,
                    "material": row.material,
                    "organism": row.organism,
                    "growth_flag": row.growth_flag,
                    "cfu": row.cfu,
                }
                for row in s.execute(select(LabSample).order_by(LabSample.id.asc())).scalars()
            ]
            sanitary_samples = [
                {
                    "id": row.id,
                    "department_id": row.department_id,
                    "sampling_point": row.sampling_point,
                    "lab_no": row.lab_no,
                    "room": row.room,
                    "growth_flag": row.growth_flag,
                    "cfu": row.cfu,
                }
                for row in s.execute(select(SanitarySample).order_by(SanitarySample.id.asc())).scalars()
            ]
            form100_cards = [
                {
                    "id": row.id,
                    "patient_id": row.patient_id,
                    "emr_case_id": row.emr_case_id,
                    "status": row.status,
                    "payload_json": row.payload_json,
                    "bodymap_json": row.bodymap_json,
                    "signed_by": row.signed_by,
                    "signed_at": row.signed_at.isoformat() if row.signed_at else None,
                }
                for row in s.execute(select(Form100Card).order_by(Form100Card.id.asc())).scalars()
            ]
            reports = [
                {
                    "id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "report_type": row.report_type,
                    "filters_json": row.filters_json,
                    "result_summary_json": row.result_summary_json,
                    "artifact_path": row.artifact_path,
                    "artifact_sha256": row.artifact_sha256,
                }
                for row in s.execute(select(ReportRun).order_by(ReportRun.id.asc())).scalars()
            ]
        return {
            "patients": patients,
            "emr_cases": emr_cases,
            "emr_case_versions": emr_versions,
            "lab_samples": lab_samples,
            "sanitary_samples": sanitary_samples,
            "form100_cards": form100_cards,
            "reports": reports,
        }

    def _safe_member(self, name: str) -> bool:
        p = PurePosixPath(name)
        if p.is_absolute():
            return False
        if ".." in p.parts:
            return False
        return True

    def export_package(self) -> Path:
        dirs = get_app_dirs()
        out_dir = dirs.data / "exchange"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = out_dir / f"export_{stamp}.json"
        zip_path = out_dir / f"export_{stamp}.zip"

        payload = {
            "schema_version": "1.1",
            "exported_at": datetime.now().isoformat(),
            "exported_by": self._session.login,
            "summary": self._analytics.summary(),
            "data": self._collect_export_data(),
        }
        json_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        json_path.write_bytes(json_bytes)

        manifest_files: dict[str, str] = {"data.json": hashlib.sha256(json_bytes).hexdigest()}
        artifact_entries: list[tuple[str, bytes]] = []
        for report in payload["data"]["reports"]:
            raw = report.get("artifact_path")
            if not raw:
                continue
            src = Path(raw)
            if not src.exists() or not src.is_file():
                continue
            arc = f"artifacts/report_{report['id']}_{src.name}"
            if not self._safe_member(arc):
                continue
            data = src.read_bytes()
            artifact_entries.append((arc, data))
            manifest_files[arc] = hashlib.sha256(data).hexdigest()

        form100_reports = get_app_dirs().data / "reports" / "form100"
        if form100_reports.exists():
            for src in sorted(form100_reports.glob("form100_*.pdf")):
                arc = f"artifacts/form100/{src.name}"
                if not self._safe_member(arc):
                    continue
                blob = src.read_bytes()
                artifact_entries.append((arc, blob))
                manifest_files[arc] = hashlib.sha256(blob).hexdigest()

        manifest = {
            "schema_version": payload["schema_version"],
            "created_at": payload["exported_at"],
            "files": manifest_files,
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        manifest_files["manifest.json"] = hashlib.sha256(manifest_bytes).hexdigest()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_bytes)
            zf.writestr("data.json", json_bytes)
            for name, blob in artifact_entries:
                zf.writestr(name, blob)

        digest = file_sha256(zip_path)
        package_id = self._repo.create(
            direction="export",
            package_format="zip+json",
            file_path=str(zip_path),
            sha256=digest,
            created_by=self._session.user_id,
            notes=f"Auto-generated export package schema={payload['schema_version']}",
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "data_exchange_package",
                str(package_id),
                "export",
                {"path": str(zip_path), "files": len(manifest_files)},
            )
        )
        return zip_path

    def _load_payload(self, path: Path) -> dict:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))

        if path.suffix.lower() != ".zip":
            raise ValueError("Поддерживаются только *.zip или *.json пакеты")

        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            for name in names:
                if not self._safe_member(name):
                    raise ValueError(f"Небезопасный путь в архиве: {name}")

            if "data.json" not in names or "manifest.json" not in names:
                raise ValueError("В архиве должны быть manifest.json и data.json")

            data_bytes = zf.read("data.json")
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            files = manifest.get("files")
            if not isinstance(files, dict):
                raise ValueError("manifest.json: поле files отсутствует или некорректно")

            for name, expected in files.items():
                if name not in names:
                    raise ValueError(f"manifest.json: отсутствует файл {name}")
                if not isinstance(expected, str) or not expected:
                    raise ValueError(f"manifest.json: неверный hash для {name}")
                got = hashlib.sha256(zf.read(name)).hexdigest()
                if got != expected:
                    raise ValueError(f"Неверный hash файла {name}")
            return json.loads(data_bytes.decode("utf-8"))

    def import_package(self, path: str | Path) -> int:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        payload = self._load_payload(p)
        schema_version = str(payload.get("schema_version", "")).strip()
        if not schema_version:
            raise ValueError("Пакет не содержит schema_version")

        digest = file_sha256(p)
        package_id = self._repo.create(
            direction="import",
            package_format=p.suffix.lstrip("."),
            file_path=str(p),
            sha256=digest,
            created_by=self._session.user_id,
            notes=f"Imported schema_version={schema_version}",
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "data_exchange_package",
                str(package_id),
                "import",
                {"path": str(p), "schema_version": schema_version},
            )
        )
        return package_id

    def history(self, limit: int = 100):
        return self._repo.latest(limit=limit)
