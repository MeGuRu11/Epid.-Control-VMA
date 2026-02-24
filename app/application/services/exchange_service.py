from __future__ import annotations

import csv
import json
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from sqlalchemy import Date, DateTime

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.session import session_scope
from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name
from app.infrastructure.security.sha256 import sha256_file

TABLE_MODELS: dict[str, type[Any]] = {
    "departments": models.Department,
    "ref_icd10": models.RefICD10,
    "ref_microorganisms": models.RefMicroorganism,
    "ref_antibiotic_groups": models.RefAntibioticGroup,
    "ref_antibiotics": models.RefAntibiotic,
    "ref_phages": models.RefPhage,
    "ref_material_types": models.RefMaterialType,
    "patients": models.Patient,
    "emr_case": models.EmrCase,
    "emr_case_version": models.EmrCaseVersion,
    "emr_diagnosis": models.EmrDiagnosis,
    "emr_intervention": models.EmrIntervention,
    "emr_antibiotic_course": models.EmrAntibioticCourse,
    "lab_sample": models.LabSample,
    "lab_microbe_isolation": models.LabMicrobeIsolation,
    "lab_abx_susceptibility": models.LabAbxSusceptibility,
    "lab_phage_panel_result": models.LabPhagePanelResult,
    "sanitary_sample": models.SanitarySample,
    "san_microbe_isolation": models.SanMicrobeIsolation,
    "san_abx_susceptibility": models.SanAbxSusceptibility,
    "san_phage_panel_result": models.SanPhagePanelResult,
    "form100_card": models.Form100Card,
    "form100_mark": models.Form100Mark,
    "form100_stage": models.Form100Stage,
}

CSV_TABLES: dict[str, type[Any]] = {
    "lab_sample": models.LabSample,
    "sanitary_sample": models.SanitarySample,
    "patients": models.Patient,
    "emr_case": models.EmrCase,
}

CSV_HEADERS: dict[str, dict[str, str]] = {
    "patients": {
        "id": "ID пациента",
        "full_name": "ФИО",
        "dob": "Дата рождения",
        "sex": "Пол",
        "category": "Категория",
        "military_unit": "Воинская часть",
        "military_district": "Военный округ",
        "created_at": "Создано",
    },
    "emr_case": {
        "id": "ID госпитализации",
        "patient_id": "ID пациента",
        "hospital_case_no": "№ госпитализации",
        "department_id": "ID отделения",
        "created_at": "Создано",
        "created_by": "Создал",
    },
    "lab_sample": {
        "id": "ID пробы",
        "patient_id": "ID пациента",
        "emr_case_id": "ID госпитализации",
        "lab_no": "Лаб. номер",
        "barcode": "Штрихкод",
        "material_type_id": "ID типа материала",
        "material_location": "Локализация материала",
        "medium": "Среда",
        "study_kind": "Тип исследования",
        "ordered_at": "Назначено",
        "taken_at": "Взято",
        "delivered_at": "Доставлено",
        "growth_result_at": "Результат роста",
        "growth_flag": "Рост (0/1)",
        "colony_desc": "Колонии/морфология",
        "microscopy": "Микроскопия",
        "cfu": "КОЕ",
        "created_at": "Создано",
        "created_by": "Создал",
    },
    "sanitary_sample": {
        "id": "ID пробы",
        "department_id": "ID отделения",
        "room": "Помещение",
        "sampling_point": "Точка отбора",
        "lab_no": "Лаб. номер",
        "barcode": "Штрихкод",
        "medium": "Среда",
        "ordered_at": "Назначено",
        "taken_at": "Взято",
        "delivered_at": "Доставлено",
        "growth_result_at": "Результат роста",
        "growth_flag": "Рост (0/1)",
        "colony_desc": "Колонии/морфология",
        "microscopy": "Микроскопия",
        "cfu": "КОЕ",
        "created_at": "Создано",
        "created_by": "Создал",
    },
}


def _format_date_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return value


def _serialize_value(value: Any) -> Any:
    return _format_date_value(value)


def _model_to_dict(obj: Any) -> dict:
    data = {}
    for column in obj.__table__.columns:
        data[column.name] = _serialize_value(getattr(obj, column.name))
    return data


def _get_csv_headers(table_name: str, columns: list[str]) -> list[str]:
    header_map = CSV_HEADERS.get(table_name, {})
    return [header_map.get(col, col) for col in columns]


def _map_csv_row(table_name: str, row: dict[str, Any]) -> dict[str, Any]:
    header_map = CSV_HEADERS.get(table_name, {})
    reverse_map = {label: key for key, label in header_map.items()}
    return {reverse_map.get(key, key): value for key, value in row.items()}


def _parse_value(value: Any, column) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (date, datetime)):
        return value
    if isinstance(column.type, Date):
        try:
            return date.fromisoformat(value)
        except Exception:
            parts = value.split(".")
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    if isinstance(column.type, DateTime):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                return datetime.strptime(value, "%d.%m.%Y %H:%M").replace(tzinfo=UTC)
            except Exception:
                return datetime.strptime(value, "%d.%m.%Y %H:%M:%S").replace(tzinfo=UTC)
    return value


def _dict_to_model(model_cls: type[Any], data: dict) -> Any:
    obj = model_cls()
    for column in model_cls.__table__.columns:
        name = column.name
        if name in data:
            setattr(obj, name, _parse_value(data[name], column))
    return obj


def _safe_extract_zip(zip_file: zipfile.ZipFile, destination: Path) -> list[Path]:
    """
    Safely extract ZIP archive contents into destination.

    Protects against path traversal (Zip Slip) by rejecting entries that try to
    escape destination via absolute paths, drive prefixes, or '..' components.
    """
    destination = destination.resolve()
    extracted: list[Path] = []
    for member in zip_file.infolist():
        if member.is_dir():
            continue

        raw_name = member.filename.replace("\\", "/")
        pure_path = PurePosixPath(raw_name)
        if not raw_name:
            raise ValueError(f"Недопустимый путь в архиве (пустое имя): {member.filename}")
        if pure_path.is_absolute():
            raise ValueError(f"Недопустимый путь в архиве (абсолютный путь): {member.filename}")
        if ".." in pure_path.parts:
            raise ValueError(f"Недопустимый путь в архиве (path traversal): {member.filename}")
        if pure_path.parts and ":" in pure_path.parts[0]:
            raise ValueError(f"Недопустимый путь в архиве (префикс диска): {member.filename}")

        target_path = (destination / Path(*pure_path.parts)).resolve()
        try:
            target_path.relative_to(destination)
        except ValueError as exc:
            raise ValueError(f"Недопустимый путь в архиве (выход за каталог): {member.filename}") from exc

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(member, "r") as src, target_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        extracted.append(target_path)
    return extracted


def _get_pk_identity(model_cls: type[Any], data: dict) -> Any | None:
    pk_cols = list(model_cls.__table__.primary_key.columns)
    if len(pk_cols) != 1:
        return None
    pk_name = pk_cols[0].name
    if pk_name not in data or data[pk_name] in (None, ""):
        return None
    return _parse_value(data[pk_name], pk_cols[0])


def _format_import_error(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _write_import_error_log(
    source_file: Path,
    errors: list[dict[str, Any]],
) -> str | None:
    if not errors:
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    log_path = source_file.with_name(f"{source_file.stem}_import_errors_{timestamp}.json")
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "source_file": str(source_file),
        "errors_count": len(errors),
        "errors": errors,
    }
    try:
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return None
    return str(log_path)


def _build_import_summary(
    details: dict[str, dict[str, int]],
    *,
    errors_count: int,
) -> dict[str, int]:
    rows_total = 0
    added = 0
    updated = 0
    skipped = 0
    for item in details.values():
        rows_total += int(item.get("rows", 0))
        added += int(item.get("added", 0))
        updated += int(item.get("updated", 0))
        skipped += int(item.get("skipped", 0))
    return {
        "rows_total": rows_total,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "errors": errors_count,
    }


@contextmanager
def _working_temp_dir() -> Iterator[Path]:
    """
    Create a writable temporary directory with fallback strategy.

    In some restricted environments, directories created by tempfile may be
    inaccessible for writing. We verify writability and fall back to a
    workspace-local directory when needed.
    """
    roots = [Path(tempfile.gettempdir()), Path.cwd() / "tmp_run"]
    last_error: OSError | None = None

    for root in roots:
        temp_dir = root / f"epid-temp-{uuid4().hex}"
        try:
            root.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=False)
            probe_file = temp_dir / ".write_probe"
            probe_file.write_text("ok", encoding="utf-8")
            probe_file.unlink(missing_ok=True)
            try:
                yield temp_dir
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return
        except OSError as exc:
            last_error = exc
            shutil.rmtree(temp_dir, ignore_errors=True)

    raise OSError("Не удалось создать временный каталог для операции импорта/экспорта") from last_error


class ExchangeService:
    def __init__(
        self,
        session_factory: Callable = session_scope,
        form100_service: Any | None = None,
        form100_v2_service: Any | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.form100_service = form100_service
        self.form100_v2_service = form100_v2_service

    def _log_package(
        self, direction: str, package_format: str, file_path: Path, sha256: str, created_by: int | None
    ) -> None:
        with self.session_factory() as session:
            session.add(
                models.DataExchangePackage(
                    direction=direction,
                    package_format=package_format,
                    file_path=str(file_path),
                    sha256=sha256,
                    created_by=created_by,
                )
            )

    def export_excel(self, file_path: str | Path, exported_by: str | None = None) -> dict:
        file_path = Path(file_path)
        wb = Workbook()
        meta = wb.active
        meta.title = "meta"
        meta.append(["schema_version", "1.0"])
        meta.append(["exported_at", datetime.now(UTC).isoformat()])
        meta.append(["exported_by", exported_by or ""])

        counts: dict[str, int] = {}
        with self.session_factory() as session:
            for name, model_cls in TABLE_MODELS.items():
                ws = wb.create_sheet(title=name)
                columns = [c.name for c in model_cls.__table__.columns]
                ws.append(columns)
                rows = session.query(model_cls).all()
                for row in rows:
                    data = _model_to_dict(row)
                    ws.append([data.get(col) for col in columns])
                counts[name] = len(rows)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(file_path)
        return {"path": str(file_path), "counts": counts}

    def export_zip(self, file_path: str | Path, exported_by: str | None = None, actor_id: int | None = None) -> dict:
        file_path = Path(file_path)
        with _working_temp_dir() as tmp_dir_path:
            excel_path = tmp_dir_path / "export.xlsx"
            result = self.export_excel(excel_path, exported_by=exported_by)
            files: list[Path] = [excel_path]
            manifest_files: list[dict[str, Any]] = []
            manifest: dict[str, Any] = {
                "schema_version": "1.0",
                "exported_at": datetime.now(UTC).isoformat(),
                "exported_by": exported_by,
                "files": manifest_files,
            }
            for f in files:
                manifest_files.append(
                    {
                        "name": f.name,
                        "sha256": sha256_file(f),
                        "size": f.stat().st_size,
                    }
                )
            manifest_path = tmp_dir_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(excel_path, arcname=excel_path.name)
                zf.write(manifest_path, arcname=manifest_path.name)

        package_hash = sha256_file(file_path)
        self._log_package("export", "zip+excel", file_path, package_hash, actor_id)
        return {"path": str(file_path), "counts": result["counts"], "sha256": package_hash}

    def import_excel(self, file_path: str | Path, mode: str = "merge", *, write_error_log: bool = True) -> dict:
        file_path = Path(file_path)
        wb = load_workbook(file_path, read_only=True, data_only=True)
        counts: dict[str, int] = {}
        details: dict[str, dict[str, int]] = {}
        errors: list[dict[str, Any]] = []
        with self.session_factory() as session:
            for sheet_name in wb.sheetnames:
                if sheet_name == "meta":
                    continue
                if sheet_name not in TABLE_MODELS:
                    continue
                model_cls = TABLE_MODELS[sheet_name]
                ws = wb[sheet_name]
                row_iter = ws.iter_rows(values_only=True)
                header_row = next(row_iter, None)
                if header_row is None:
                    counts[sheet_name] = 0
                    details[sheet_name] = {"rows": 0, "added": 0, "updated": 0, "skipped": 0, "errors": 0}
                    continue
                header_positions = [(idx, str(val)) for idx, val in enumerate(header_row) if val is not None]
                if not header_positions:
                    counts[sheet_name] = 0
                    details[sheet_name] = {"rows": 0, "added": 0, "updated": 0, "skipped": 0, "errors": 0}
                    continue
                rows_total = 0
                added = 0
                updated = 0
                skipped = 0
                sheet_errors = 0
                for row_idx, row in enumerate(row_iter, start=2):
                    rows_total += 1
                    try:
                        data = {
                            header: row[idx] if row is not None and idx < len(row) else None
                            for idx, header in header_positions
                        }
                        identity = _get_pk_identity(model_cls, data)
                        existing = session.get(model_cls, identity) if identity is not None else None
                        if mode == "append" and existing is not None:
                            skipped += 1
                            continue
                        obj = _dict_to_model(model_cls, data)
                        if existing is not None:
                            updated += 1
                        else:
                            added += 1
                        session.merge(obj)
                    except Exception as exc:  # noqa: BLE001
                        sheet_errors += 1
                        errors.append(
                            {
                                "scope": sheet_name,
                                "row": row_idx,
                                "message": _format_import_error(exc),
                            }
                        )
                counts[sheet_name] = rows_total
                details[sheet_name] = {
                    "rows": rows_total,
                    "added": added,
                    "updated": updated,
                    "skipped": skipped,
                    "errors": sheet_errors,
                }
        summary = _build_import_summary(details, errors_count=len(errors))
        result: dict[str, Any] = {
            "path": str(file_path),
            "counts": counts,
            "details": details,
            "errors": errors,
            "error_count": len(errors),
            "summary": summary,
        }
        if write_error_log:
            result["error_log_path"] = _write_import_error_log(file_path, errors)
        return result

    def import_zip(self, file_path: str | Path, actor_id: int | None = None, mode: str = "merge") -> dict:
        file_path = Path(file_path)
        with _working_temp_dir() as tmp_dir_path:
            with zipfile.ZipFile(file_path, "r") as zf:
                try:
                    _safe_extract_zip(zf, tmp_dir_path)
                except ValueError as exc:
                    raise ValueError(f"Небезопасный ZIP-архив: {exc}") from exc

            manifest_path = tmp_dir_path / "manifest.json"
            if not manifest_path.exists():
                raise ValueError("В архиве отсутствует manifest.json")
            manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_files = cast(list[dict[str, Any]], manifest.get("files", []))
            for entry in manifest_files:
                f = tmp_dir_path / entry["name"]
                if not f.exists():
                    raise ValueError(f"Файл отсутствует: {entry['name']}")
                if sha256_file(f) != entry.get("sha256"):
                    raise ValueError(f"Хэш не совпадает: {entry['name']}")

            excel_path = tmp_dir_path / "export.xlsx"
            if not excel_path.exists():
                raise ValueError("В архиве отсутствует export.xlsx")
            result = self.import_excel(excel_path, mode=mode, write_error_log=False)

        package_hash = sha256_file(file_path)
        self._log_package("import", "zip+excel", file_path, package_hash, actor_id)
        errors = cast(list[dict[str, Any]], result.get("errors", []))
        return {
            "path": str(file_path),
            "counts": result.get("counts", {}),
            "details": result.get("details", {}),
            "errors": errors,
            "error_count": len(errors),
            "error_log_path": _write_import_error_log(file_path, errors),
            "summary": result.get("summary", {}),
            "sha256": package_hash,
        }

    def export_form100_package_zip(
        self,
        file_path: str | Path,
        *,
        actor_id: int | None = None,
        exported_by: str | None = None,
        card_id: str | None = None,
    ) -> dict:
        if self.form100_service is None:
            raise ValueError("Сервис Form100 не подключён")
        return self.form100_service.export_package_zip(
            file_path=file_path,
            actor_id=actor_id,
            card_id=card_id,
            exported_by=exported_by,
        )

    def import_form100_package_zip(
        self,
        file_path: str | Path,
        *,
        actor_id: int | None = None,
        mode: str = "merge",
    ) -> dict:
        if self.form100_service is None:
            raise ValueError("Сервис Form100 не подключён")
        return self.form100_service.import_package_zip(
            file_path=file_path,
            actor_id=actor_id,
            mode=mode,
        )

    def export_form100_v2_package_zip(
        self,
        file_path: str | Path,
        *,
        actor_id: int | None = None,
        exported_by: str | None = None,
        card_id: str | None = None,
    ) -> dict:
        if self.form100_v2_service is None:
            raise ValueError("Сервис Form100 V2 не подключён")
        return self.form100_v2_service.export_package_zip(
            file_path=file_path,
            actor_id=actor_id,
            card_id=card_id,
            exported_by=exported_by,
        )

    def import_form100_v2_package_zip(
        self,
        file_path: str | Path,
        *,
        actor_id: int | None = None,
        mode: str = "merge",
    ) -> dict:
        if self.form100_v2_service is None:
            raise ValueError("Сервис Form100 V2 не подключён")
        return self.form100_v2_service.import_package_zip(
            file_path=file_path,
            actor_id=actor_id,
            mode=mode,
        )

    def list_packages(
        self, limit: int = 50, direction: str | None = None, query: str | None = None
    ) -> list[models.DataExchangePackage]:
        with self.session_factory() as session:
            q = session.query(models.DataExchangePackage)
            if direction:
                q = q.filter(models.DataExchangePackage.direction == direction)
            if query:
                q = q.filter(
                    models.DataExchangePackage.file_path.ilike(f"%{query}%")
                    | models.DataExchangePackage.sha256.ilike(f"%{query}%")
                )
            return q.order_by(models.DataExchangePackage.created_at.desc()).limit(limit).all()

    def export_csv(self, file_path: str | Path, table_name: str) -> dict:
        file_path = Path(file_path)
        if table_name not in CSV_TABLES:
            raise ValueError("Неизвестная таблица CSV")
        model_cls = CSV_TABLES[table_name]
        with self.session_factory() as session:
            rows = session.query(model_cls).all()
            columns = [c.name for c in model_cls.__table__.columns]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_get_csv_headers(table_name, columns))
                for row in rows:
                    data = _model_to_dict(row)
                    writer.writerow([data.get(col) for col in columns])
        return {"path": str(file_path), "count": len(rows)}

    def import_csv(self, file_path: str | Path, table_name: str, mode: str = "merge") -> dict:
        file_path = Path(file_path)
        if table_name not in CSV_TABLES:
            raise ValueError("Неизвестная таблица CSV")
        model_cls = CSV_TABLES[table_name]
        count = 0
        rows_total = 0
        added = updated = skipped = 0
        errors: list[dict[str, Any]] = []
        with self.session_factory() as session, file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                rows_total += 1
                try:
                    mapped_row = _map_csv_row(table_name, row)
                    identity = _get_pk_identity(model_cls, mapped_row)
                    existing = session.get(model_cls, identity) if identity is not None else None
                    if mode == "append" and existing is not None:
                        skipped += 1
                        continue
                    obj = _dict_to_model(model_cls, mapped_row)
                    if existing is not None:
                        updated += 1
                    else:
                        added += 1
                    session.merge(obj)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(
                        {
                            "scope": table_name,
                            "row": row_idx,
                            "message": _format_import_error(exc),
                        }
                    )
        details = {
            table_name: {
                "rows": rows_total,
                "added": added,
                "updated": updated,
                "skipped": skipped,
                "errors": len(errors),
            }
        }
        summary = _build_import_summary(details, errors_count=len(errors))
        return {
            "path": str(file_path),
            "count": count,
            "counts": {table_name: rows_total},
            "details": details,
            "errors": errors,
            "error_count": len(errors),
            "error_log_path": _write_import_error_log(file_path, errors),
            "summary": summary,
        }

    def export_pdf(self, file_path: str | Path, table_name: str) -> dict:
        file_path = Path(file_path)
        if table_name not in CSV_TABLES:
            raise ValueError("Неизвестная таблица PDF")
        model_cls = CSV_TABLES[table_name]
        with self.session_factory() as session:
            rows = session.query(model_cls).all()
            columns = [c.name for c in model_cls.__table__.columns]
            data = [_get_csv_headers(table_name, columns)]
            for row in rows:
                record = _model_to_dict(row)
                data.append(["" if record.get(col) is None else str(record.get(col)) for col in columns])

        file_path.parent.mkdir(parents=True, exist_ok=True)
        unicode_font = get_pdf_unicode_font_name()
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            )
        )
        doc.build([table])
        return {"path": str(file_path), "count": len(data) - 1}

    # Legacy JSON support (not used in UI)
    def export_json(self, file_path: str | Path, exported_by: str | None = None) -> dict:
        file_path = Path(file_path)
        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "exported_by": exported_by,
            "data": {},
        }

        with self.session_factory() as session:
            for name, model_cls in TABLE_MODELS.items():
                payload["data"][name] = [_model_to_dict(x) for x in session.query(model_cls).all()]

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"path": str(file_path), "counts": {k: len(v) for k, v in payload["data"].items()}}

    def import_json(self, file_path: str | Path, mode: str = "merge") -> dict:
        file_path = Path(file_path)
        payload: dict[str, Any] = json.loads(file_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0":
            raise ValueError("Неподдерживаемая версия схемы")
        data: dict[str, Any] = payload.get("data") or {}

        counts: dict[str, int] = {}
        details: dict[str, dict[str, int]] = {}
        errors: list[dict[str, Any]] = []
        with self.session_factory() as session:
            for name, model_cls in TABLE_MODELS.items():
                items = data.get(name) or []
                rows_total = 0
                added = updated = skipped = 0
                table_errors = 0
                for idx, item in enumerate(items, start=1):
                    rows_total += 1
                    try:
                        identity = _get_pk_identity(model_cls, item)
                        existing = session.get(model_cls, identity) if identity is not None else None
                        if mode == "append" and existing is not None:
                            skipped += 1
                            continue
                        obj = _dict_to_model(model_cls, item)
                        if existing is not None:
                            updated += 1
                        else:
                            added += 1
                        session.merge(obj)
                    except Exception as exc:  # noqa: BLE001
                        table_errors += 1
                        errors.append(
                            {
                                "scope": name,
                                "row": idx,
                                "message": _format_import_error(exc),
                            }
                        )
                counts[name] = rows_total
                details[name] = {
                    "rows": rows_total,
                    "added": added,
                    "updated": updated,
                    "skipped": skipped,
                    "errors": table_errors,
                }
        summary = _build_import_summary(details, errors_count=len(errors))
        return {
            "path": str(file_path),
            "counts": counts,
            "details": details,
            "errors": errors,
            "error_count": len(errors),
            "error_log_path": _write_import_error_log(file_path, errors),
            "summary": summary,
        }
