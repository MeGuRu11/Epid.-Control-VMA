from __future__ import annotations

import json
import hashlib
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath

from ...config import get_app_dirs
from ...domain.rules import normalize_required_text
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.patient_repo import PatientRepo
from ...infrastructure.db.repositories.form100_repo import Form100Repo
from ...infrastructure.security.sha256 import file_sha256
from ...infrastructure.form100 import (
    FORM100_MARKER_LEGACY_ALIASES,
    BODYMAP_ZONES,
    FORM100_FIELDS,
    FORM100_MARKER_TYPES,
    empty_form100_payload,
    normalize_form100_payload,
    resolve_template_path,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Form100Service:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._repo = Form100Repo(engine)
        self._patients = PatientRepo(engine)
        self._audit = AuditLogger(engine)

    @staticmethod
    def _is_locked_status(status: str | None) -> bool:
        return str(status or "").upper() in {"SIGNED", "ARCHIVED"}

    @staticmethod
    def _is_truthy(value: object) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def list(self, patient_id: int | None = None, emr_case_id: int | None = None):
        return self._repo.list_cards(patient_id=patient_id, emr_case_id=emr_case_id)

    def get(self, card_id: int):
        return self._repo.get(card_id)

    def get_payload(self, card_id: int) -> dict:
        row = self._repo.get(card_id)
        if row is None:
            return empty_form100_payload()
        try:
            raw = json.loads(row.payload_json or "{}")
            if isinstance(raw, dict):
                return normalize_form100_payload(raw)
        except Exception:
            pass
        return empty_form100_payload()

    def get_bodymap(self, card_id: int) -> list[dict]:
        row = self._repo.get(card_id)
        if row is None:
            return []
        try:
            data = json.loads(row.bodymap_json or "[]")
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except Exception:
            pass
        return []

    def create(self, patient_id: int, emr_case_id: int | None = None, payload: dict | None = None) -> int:
        payload = normalize_form100_payload(payload)
        patient = self._patients.get(patient_id)
        if patient is not None:
            if not payload.get("main_full_name"):
                payload["main_full_name"] = str(patient.full_name or "").strip()
            if not payload.get("main_id_tag"):
                payload["main_id_tag"] = f"ID {patient.id}"
            if not payload.get("stub_full_name"):
                payload["stub_full_name"] = str(patient.full_name or "").strip()
            if not payload.get("stub_id_tag"):
                payload["stub_id_tag"] = f"ID {patient.id}"
        card_id = self._repo.create(
            patient_id=patient_id,
            emr_case_id=emr_case_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
            bodymap_json="[]",
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(card_id),
                "create",
                {"patient_id": patient_id, "emr_case_id": emr_case_id},
            )
        )
        return card_id

    def update_payload(self, card_id: int, payload: dict) -> bool:
        row = self._repo.get(card_id)
        if row is None:
            return False
        if self._is_locked_status(row.status):
            raise PermissionError("Карточка недоступна для редактирования")
        normalized = normalize_form100_payload(payload)
        ok = self._repo.set_payload(card_id, json.dumps(normalized, ensure_ascii=False))
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "form100_card",
                    str(card_id),
                    "update_payload",
                    {"keys": sorted(normalized.keys())},
                )
            )
        return ok

    def update_note(self, card_id: int, note: str) -> bool:
        payload = self.get_payload(card_id)
        payload["main_diagnosis"] = normalize_required_text(note, default="")
        return self.update_payload(card_id, payload)

    def update_bodymap(self, card_id: int, markers: list[dict]) -> bool:
        row = self._repo.get(card_id)
        if row is None:
            return False
        if self._is_locked_status(row.status):
            raise PermissionError("Карточка недоступна для редактирования")
        normalized: list[dict] = []
        for marker in markers:
            try:
                nx = float(marker.get("x"))
                ny = float(marker.get("y"))
            except (TypeError, ValueError):
                continue
            nx = max(0.0, min(1.0, nx))
            ny = max(0.0, min(1.0, ny))
            raw_type = str(marker.get("annotation_type") or marker.get("kind") or FORM100_MARKER_TYPES[0])
            annotation_type = FORM100_MARKER_LEGACY_ALIASES.get(raw_type, raw_type)
            if annotation_type not in FORM100_MARKER_TYPES:
                annotation_type = FORM100_MARKER_TYPES[0]
            raw_view = str(marker.get("view") or marker.get("zone") or "front")
            view = raw_view if raw_view in BODYMAP_ZONES else "front"
            note = str(marker.get("note") or "")
            normalized.append(
                {
                    "x": nx,
                    "y": ny,
                    "annotation_type": annotation_type,
                    "view": view,
                    "note": note,
                    # Legacy keys to keep compatibility with old reader code.
                    "kind": annotation_type,
                    "zone": view,
                }
            )

        ok = self._repo.set_bodymap(card_id, json.dumps(normalized, ensure_ascii=False))
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "form100_card",
                    str(card_id),
                    "update_bodymap",
                    {"markers": len(normalized)},
                )
            )
        return ok

    def sign(self, card_id: int, signer: str) -> bool:
        row = self._repo.get(card_id)
        if row is None:
            return False
        if row.status == "SIGNED":
            return True
        if row.status == "ARCHIVED":
            raise PermissionError("Архивированная карточка недоступна для подписи")
        ok = self._repo.sign(card_id, signer=normalize_required_text(signer), signed_at=utcnow())
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "form100_card",
                    str(card_id),
                    "sign",
                    {"signer": signer},
                )
            )
        return ok

    def archive(self, card_id: int) -> bool:
        row = self._repo.get(card_id)
        if row is None:
            return False
        if row.status == "ARCHIVED":
            return True
        ok = self._repo.set_status(card_id, "ARCHIVED")
        if ok:
            self._audit.log(
                AuditEvent(
                    self._session.user_id,
                    self._session.login,
                    "form100_card",
                    str(card_id),
                    "archive",
                    {"from_status": row.status},
                )
            )
        return ok

    def create_revision(self, card_id: int) -> int | None:
        row = self._repo.get(card_id)
        if row is None:
            return None
        payload = self.get_payload(card_id)
        bodymap = self.get_bodymap(card_id)
        new_id = self._repo.create(
            patient_id=row.patient_id,
            emr_case_id=row.emr_case_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
            bodymap_json=json.dumps(bodymap, ensure_ascii=False),
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(new_id),
                "create_revision",
                {"source_card_id": card_id},
            )
        )
        return new_id

    def export_pdf(self, card_id: int) -> Path:
        row = self._repo.get(card_id)
        if row is None:
            raise ValueError("Карточка не найдена")
        payload = self.get_payload(card_id)
        markers = self.get_bodymap(card_id)

        template = resolve_template_path()
        if template is None:
            raise ValueError("Не найден файл шаблона Form100")

        try:
            from reportlab.lib.colors import Color
            from reportlab.lib.pagesizes import A5, landscape
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("reportlab не установлен") from exc

        out_dir = get_app_dirs().data / "reports" / "form100"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"form100_{card_id}_{stamp}.pdf"

        page_w, page_h = landscape(A5)
        margin = 12.0
        max_w = page_w - margin * 2
        max_h = page_h - margin * 2

        image = ImageReader(str(template))
        iw, ih = image.getSize()
        scale = min(max_w / max(1.0, float(iw)), max_h / max(1.0, float(ih)))
        draw_w = float(iw) * scale
        draw_h = float(ih) * scale
        ox = (page_w - draw_w) / 2.0
        oy = (page_h - draw_h) / 2.0

        c = canvas.Canvas(str(path), pagesize=(page_w, page_h))
        c.drawImage(image, ox, oy, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")

        # Form100 side flags from payload (active=strong, inactive=light).
        flag_emergency = str(payload.get("flag_emergency") or "").strip().lower() in {"1", "true", "yes", "on"}
        flag_radiation = str(payload.get("flag_radiation") or "").strip().lower() in {"1", "true", "yes", "on"}
        flag_sanitation = str(payload.get("flag_sanitation") or "").strip().lower() in {"1", "true", "yes", "on"}
        c.saveState()
        c.setStrokeColor(Color(0, 0, 0, alpha=0))
        c.setFillColor(Color(0.75, 0.22, 0.17, alpha=1.0 if flag_emergency else 0.25))
        c.rect(ox + draw_w * 0.31, oy + draw_h * 0.955, draw_w * 0.63, draw_h * 0.04, fill=1, stroke=0)
        c.setFillColor(Color(0.12, 0.47, 0.71, alpha=1.0 if flag_radiation else 0.25))
        c.rect(ox + draw_w * 0.31, oy + draw_h * 0.000, draw_w * 0.63, draw_h * 0.04, fill=1, stroke=0)
        c.setFillColor(Color(0.96, 0.84, 0.55, alpha=1.0 if flag_sanitation else 0.25))
        c.rect(ox + draw_w * 0.94, oy + draw_h * 0.00, draw_w * 0.05, draw_h * 1.00, fill=1, stroke=0)
        c.restoreState()

        # Overlay markers onto the exact body zones over template.
        c.setFont("Helvetica-Bold", 8)
        for marker in markers:
            raw_view = str(marker.get("view") or marker.get("zone") or "front")
            view = raw_view if raw_view in BODYMAP_ZONES else "front"
            zx, zy, zw, zh = BODYMAP_ZONES[view]
            try:
                nx = max(0.0, min(1.0, float(marker.get("x"))))
                ny = max(0.0, min(1.0, float(marker.get("y"))))
            except (TypeError, ValueError):
                continue
            raw_type = str(marker.get("annotation_type") or marker.get("kind") or FORM100_MARKER_TYPES[0])
            annotation_type = FORM100_MARKER_LEGACY_ALIASES.get(raw_type, raw_type)
            if annotation_type not in FORM100_MARKER_TYPES:
                annotation_type = FORM100_MARKER_TYPES[0]

            px = ox + draw_w * (zx + nx * zw)
            py = oy + draw_h * (1.0 - (zy + ny * zh))
            if annotation_type == "WOUND_X":
                c.setFillColor(Color(0.75, 0.22, 0.17))
            elif annotation_type == "BURN_HATCH":
                c.setFillColor(Color(0.90, 0.45, 0.13))
            elif annotation_type == "AMPUTATION":
                c.setFillColor(Color(0.58, 0.19, 0.15))
            elif annotation_type == "TOURNIQUET":
                c.setFillColor(Color(0.61, 0.39, 0.05))
            else:
                c.setFillColor(Color(0.12, 0.47, 0.71))
            c.circle(px, py, 2.8, stroke=0, fill=1)
            c.setFillColor(Color(0.12, 0.12, 0.12))
            note_text = ""
            if annotation_type == "NOTE_PIN":
                note_text = str(marker.get("note") or "").strip()
            label = note_text or annotation_type
            c.drawString(px + 4.0, py + 2.0, self._fit_single_line(c, label, 52.0, 8))

        c.setFillColor(Color(0.1, 0.1, 0.1))
        checkbox_like_fields = {"mp_antibiotic", "mp_transfusion_blood", "mp_immobilization"}
        for spec in FORM100_FIELDS:
            key = str(spec["key"])
            text = str(payload.get(key) or "").strip()
            if key in checkbox_like_fields:
                if self._is_truthy(text):
                    text = "X"
                else:
                    text = ""
            if not text:
                continue
            self._draw_field_text(
                c,
                text,
                x=float(spec["x"]),
                y=float(spec["y"]),
                w=float(spec["w"]),
                h=float(spec["h"]),
                font_size=float(spec.get("font", 8.0)),
                multiline=bool(spec.get("multiline", False)),
                ox=ox,
                oy=oy,
                draw_w=draw_w,
                draw_h=draw_h,
            )

        if row.signed_by:
            c.setFont("Helvetica", 8)
            sign_text = str(row.signed_by)
            sx = ox + draw_w * 0.654
            sy = oy + draw_h * (1.0 - 0.874 - 0.028) + 10
            c.drawString(sx, sy, self._fit_single_line(c, sign_text, draw_w * 0.188, 8))

        c.save()
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(card_id),
                "export_pdf",
                {"path": str(path), "markers": len(markers)},
            )
        )
        return path

    def export_zip(self, card_id: int) -> Path:
        row = self._repo.get(card_id)
        if row is None:
            raise ValueError("Карточка не найдена")

        payload = self.get_payload(card_id)
        markers = self.get_bodymap(card_id)
        pdf_path = self.export_pdf(card_id)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = get_app_dirs().data / "exchange" / "form100"
        out_dir.mkdir(parents=True, exist_ok=True)
        zip_path = out_dir / f"form100_card_{card_id}_{stamp}.zip"

        card_data = {
            "schema_version": "1.0",
            "entity": "form100_card",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "exported_by": self._session.login,
            "card": {
                "id": row.id,
                "patient_id": row.patient_id,
                "emr_case_id": row.emr_case_id,
                "status": row.status,
                "signed_by": row.signed_by,
                "signed_at": row.signed_at.isoformat() if row.signed_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            },
            "payload": payload,
            "bodymap": markers,
        }
        card_bytes = json.dumps(card_data, ensure_ascii=False, indent=2).encode("utf-8")
        pdf_bytes = pdf_path.read_bytes()

        manifest_files = {
            "form100_card.json": hashlib.sha256(card_bytes).hexdigest(),
            f"artifacts/{pdf_path.name}": hashlib.sha256(pdf_bytes).hexdigest(),
        }
        manifest = {
            "schema_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest_files,
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_bytes)
            zf.writestr("form100_card.json", card_bytes)
            zf.writestr(f"artifacts/{pdf_path.name}", pdf_bytes)

        digest = file_sha256(zip_path)
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(card_id),
                "export_zip",
                {"path": str(zip_path), "sha256": digest, "files": 3},
            )
        )
        return zip_path

    @staticmethod
    def _safe_member(name: str) -> bool:
        p = PurePosixPath(name)
        if p.is_absolute():
            return False
        if ".." in p.parts:
            return False
        return True

    def _normalize_markers(self, markers: object) -> list[dict]:
        if not isinstance(markers, list):
            return []
        normalized: list[dict] = []
        for marker in markers:
            if not isinstance(marker, dict):
                continue
            try:
                nx = float(marker.get("x"))
                ny = float(marker.get("y"))
            except (TypeError, ValueError):
                continue
            nx = max(0.0, min(1.0, nx))
            ny = max(0.0, min(1.0, ny))
            raw_type = str(marker.get("annotation_type") or marker.get("kind") or FORM100_MARKER_TYPES[0])
            annotation_type = FORM100_MARKER_LEGACY_ALIASES.get(raw_type, raw_type)
            if annotation_type not in FORM100_MARKER_TYPES:
                annotation_type = FORM100_MARKER_TYPES[0]
            raw_view = str(marker.get("view") or marker.get("zone") or "front")
            view = raw_view if raw_view in BODYMAP_ZONES else "front"
            note = str(marker.get("note") or "")
            normalized.append(
                {
                    "x": nx,
                    "y": ny,
                    "annotation_type": annotation_type,
                    "view": view,
                    "note": note,
                    "kind": annotation_type,
                    "zone": view,
                }
            )
        return normalized

    def _read_zip_card(self, path: Path) -> tuple[dict, dict, list[dict], str]:
        p = path
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(str(p))
        if p.suffix.lower() != ".zip":
            raise ValueError("Поддерживается только ZIP архив")

        with zipfile.ZipFile(p, "r") as zf:
            names = set(zf.namelist())
            for name in names:
                if not self._safe_member(name):
                    raise ValueError(f"Небезопасный путь в архиве: {name}")
            if "manifest.json" not in names or "form100_card.json" not in names:
                raise ValueError("Архив должен содержать manifest.json и form100_card.json")

            try:
                manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            except Exception as exc:
                raise ValueError("Поврежден manifest.json") from exc
            files = manifest.get("files")
            if not isinstance(files, dict):
                raise ValueError("manifest.json: отсутствует поле files")
            for name, expected in files.items():
                if name not in names:
                    raise ValueError(f"manifest.json: отсутствует файл {name}")
                if not isinstance(expected, str) or not expected:
                    raise ValueError(f"manifest.json: некорректный hash для {name}")
                digest = hashlib.sha256(zf.read(name)).hexdigest()
                if digest != expected:
                    raise ValueError(f"Неверный hash файла {name}")

            try:
                data = json.loads(zf.read("form100_card.json").decode("utf-8"))
            except Exception as exc:
                raise ValueError("Поврежден form100_card.json") from exc

        if not isinstance(data, dict):
            raise ValueError("Некорректный payload form100_card.json")
        if str(data.get("entity") or "").strip() not in ("", "form100_card"):
            raise ValueError("Архив не содержит карточку Form100")

        card_info = data.get("card")
        if not isinstance(card_info, dict):
            card_info = {}
        payload = normalize_form100_payload(data.get("payload") if isinstance(data.get("payload"), dict) else {})
        markers = self._normalize_markers(data.get("bodymap"))
        archive_sha = file_sha256(p)
        return card_info, payload, markers, archive_sha

    def import_zip(self, path: str | Path, *, patient_id: int | None = None, emr_case_id: int | None = None) -> int:
        p = Path(path)
        card_info, payload, markers, archive_sha = self._read_zip_card(p)

        source_patient = card_info.get("patient_id")
        source_case = card_info.get("emr_case_id")
        target_patient_id: int | None = patient_id
        if target_patient_id is None:
            try:
                target_patient_id = int(source_patient)
            except (TypeError, ValueError):
                target_patient_id = None
        if target_patient_id is None:
            raise ValueError("Не удалось определить patient_id для импорта")
        if self._patients.get(target_patient_id) is None:
            raise ValueError(f"Пациент {target_patient_id} не найден в текущей БД")

        target_case_id: int | None = emr_case_id
        if target_case_id is None:
            try:
                target_case_id = int(source_case) if source_case is not None else None
            except (TypeError, ValueError):
                target_case_id = None

        new_id = self._repo.create(
            patient_id=target_patient_id,
            emr_case_id=target_case_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
            bodymap_json=json.dumps(markers, ensure_ascii=False),
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(new_id),
                "import_zip",
                {
                    "source_path": str(p),
                    "source_sha256": archive_sha,
                    "source_status": str(card_info.get("status") or ""),
                    "markers": len(markers),
                },
            )
        )
        return new_id

    def import_zip_revision(self, base_card_id: int, path: str | Path) -> int:
        base_row = self._repo.get(base_card_id)
        if base_row is None:
            raise ValueError("Базовая карточка не найдена")
        p = Path(path)
        card_info, payload, markers, archive_sha = self._read_zip_card(p)
        new_id = self._repo.create(
            patient_id=base_row.patient_id,
            emr_case_id=base_row.emr_case_id,
            payload_json=json.dumps(payload, ensure_ascii=False),
            bodymap_json=json.dumps(markers, ensure_ascii=False),
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(new_id),
                "import_zip_revision",
                {
                    "base_card_id": base_card_id,
                    "source_path": str(p),
                    "source_sha256": archive_sha,
                    "source_status": str(card_info.get("status") or ""),
                    "markers": len(markers),
                },
            )
        )
        return new_id

    def merge_zip_into_card(self, card_id: int, path: str | Path) -> int:
        row = self._repo.get(card_id)
        if row is None:
            raise ValueError("Карточка не найдена")
        if self._is_locked_status(row.status):
            raise PermissionError("Карточка недоступна для редактирования")

        p = Path(path)
        card_info, payload, markers, archive_sha = self._read_zip_card(p)
        ok_payload = self._repo.set_payload(card_id, json.dumps(payload, ensure_ascii=False))
        ok_bodymap = self._repo.set_bodymap(card_id, json.dumps(markers, ensure_ascii=False))
        if not ok_payload or not ok_bodymap:
            raise ValueError("Не удалось обновить карточку данными из ZIP")

        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "form100_card",
                str(card_id),
                "import_zip_merge",
                {
                    "source_path": str(p),
                    "source_sha256": archive_sha,
                    "source_status": str(card_info.get("status") or ""),
                    "markers": len(markers),
                },
            )
        )
        return card_id

    def preview_zip(self, path: str | Path) -> dict:
        p = Path(path)
        card_info, payload, markers, archive_sha = self._read_zip_card(p)
        filled_payload = {k: v for k, v in payload.items() if str(v).strip()}
        preview_lines: list[str] = []
        preview_order = (
            "main_full_name",
            "main_diagnosis",
            "main_issued_place",
            "main_id_tag",
            "main_injury_time",
            "evacuation_dest",
        )
        for key in preview_order:
            value = filled_payload.get(key)
            if value:
                preview_lines.append(f"{key}: {value}")
        if not preview_lines and filled_payload:
            first_items = list(filled_payload.items())[:6]
            preview_lines = [f"{k}: {v}" for k, v in first_items]

        return {
            "file_path": str(p),
            "sha256": archive_sha,
            "source_card_id": card_info.get("id"),
            "source_patient_id": card_info.get("patient_id"),
            "source_case_id": card_info.get("emr_case_id"),
            "source_status": str(card_info.get("status") or ""),
            "source_signed_by": str(card_info.get("signed_by") or ""),
            "filled_fields": len(filled_payload),
            "markers": len(markers),
            "markers_data": markers,
            "preview_lines": preview_lines,
        }

    @staticmethod
    def _fit_single_line(c, text: str, max_width: float, font_size: float) -> str:
        if not text:
            return ""
        out = text
        while out and c.stringWidth(out, "Helvetica", font_size) > max_width:
            out = out[:-1]
        return out

    @staticmethod
    def _wrap_lines(c, text: str, max_width: float, font_size: float, max_lines: int) -> list[str]:
        lines: list[str] = []
        for paragraph in text.splitlines() or [""]:
            words = paragraph.split(" ")
            if not words:
                words = [""]
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}".strip()
                if c.stringWidth(candidate, "Helvetica", font_size) <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
                    if len(lines) >= max_lines:
                        return lines[:max_lines]
            lines.append(current)
            if len(lines) >= max_lines:
                return lines[:max_lines]
        return lines[:max_lines]

    def _draw_field_text(
        self,
        c,
        text: str,
        *,
        x: float,
        y: float,
        w: float,
        h: float,
        font_size: float,
        multiline: bool,
        ox: float,
        oy: float,
        draw_w: float,
        draw_h: float,
    ) -> None:
        box_x = ox + draw_w * x
        box_y = oy + draw_h * (1.0 - y - h)
        box_w = draw_w * w
        box_h = draw_h * h
        base_font = max(5.5, font_size)
        c.setFont("Helvetica", base_font)
        if multiline:
            line_h = base_font * 1.15
            max_lines = max(1, int(box_h / max(1.0, line_h)))
            lines = self._wrap_lines(c, text, box_w, base_font, max_lines)
            baseline = box_y + box_h - base_font
            for line in lines:
                c.drawString(box_x + 1.0, baseline, line)
                baseline -= line_h
                if baseline < box_y:
                    break
            return

        line = self._fit_single_line(c, text.replace("\n", " "), box_w, base_font)
        baseline = box_y + box_h - base_font + 0.5
        c.drawString(box_x + 1.0, baseline, line)
