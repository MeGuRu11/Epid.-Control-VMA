from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db import models_sqlalchemy as models

_DATA_JSON_FIELD_MAP = {
    "stub": "stub_json",
    "main": "main_json",
    "lesion": "lesion_json",
    "san_loss": "san_loss_json",
    "medical_help": "mp_json",
    "bottom": "bottom_json",
    "flags": "flags_json",
    "bodymap_annotations": "bodymap_annotations_json",
    "bodymap_tissue_types": "bodymap_tissue_types_json",
    "raw_payload": "raw_payload_json",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_json(value: object, *, default: str) -> str:
    if value is None:
        return default
    return json.dumps(value, ensure_ascii=False, default=str)


def _from_json(value: object, *, default: object) -> object:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except Exception:  # noqa: BLE001
        return default


def _normalize_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _normalize_datetime(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _normalize_datetime(parsed)


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class Form100RepositoryV2:
    def list_cards(
        self,
        session: Session,
        *,
        filters: dict[str, object] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[models.Form100V2]:
        filters = filters or {}
        stmt = select(models.Form100V2)

        patient_id = filters.get("patient_id")
        if isinstance(patient_id, int):
            stmt = stmt.join(
                models.EmrCase,
                models.EmrCase.id == models.Form100V2.emr_case_id,
            ).where(models.EmrCase.patient_id == patient_id)

        query_text = str(filters.get("query") or "").strip()
        if query_text:
            like = f"%{query_text}%"
            stmt = stmt.where(
                models.Form100V2.main_full_name.ilike(like)
                | models.Form100V2.main_unit.ilike(like)
                | models.Form100V2.main_id_tag.ilike(like)
                | models.Form100V2.main_diagnosis.ilike(like)
            )

        status = filters.get("status")
        if status:
            stmt = stmt.where(models.Form100V2.status == str(status))

        unit = str(filters.get("unit") or "").strip()
        if unit:
            stmt = stmt.where(models.Form100V2.main_unit.ilike(f"%{unit}%"))

        id_tag = str(filters.get("id_tag") or "").strip()
        if id_tag:
            stmt = stmt.where(models.Form100V2.main_id_tag.ilike(f"%{id_tag}%"))

        emr_case_id = filters.get("emr_case_id")
        if isinstance(emr_case_id, int):
            stmt = stmt.where(models.Form100V2.emr_case_id == emr_case_id)

        created_from = filters.get("created_from")
        if isinstance(created_from, date):
            stmt = stmt.where(models.Form100V2.created_at >= datetime.combine(created_from, datetime.min.time()))
        created_to = filters.get("created_to")
        if isinstance(created_to, date):
            stmt = stmt.where(models.Form100V2.created_at <= datetime.combine(created_to, datetime.max.time()))

        stmt = stmt.order_by(models.Form100V2.updated_at.desc()).offset(offset).limit(limit)
        return list(session.execute(stmt).scalars())

    def get_card(self, session: Session, card_id: str) -> models.Form100V2 | None:
        return session.get(models.Form100V2, card_id)

    def get_data(self, session: Session, card_id: str) -> models.Form100DataV2 | None:
        stmt = select(models.Form100DataV2).where(models.Form100DataV2.form100_id == card_id)
        return session.execute(stmt).scalars().first()

    def create_card(
        self,
        session: Session,
        *,
        payload: dict[str, object],
        data_payload: dict[str, object],
        actor_login: str,
        card_id: str | None = None,
    ) -> tuple[models.Form100V2, models.Form100DataV2]:
        now = _utc_now()
        row = models.Form100V2(
            id=card_id or str(uuid4()),
            created_at=now,
            created_by=actor_login,
            updated_at=now,
            updated_by=actor_login,
            status="DRAFT",
            version=1,
            is_archived=False,
        )
        self._apply_card_payload(row, payload)
        data_row = models.Form100DataV2(id=str(uuid4()), form100_id=row.id)
        self._apply_data_payload(data_row, data_payload)
        session.add(row)
        session.add(data_row)
        session.flush()
        return row, data_row

    def update_card(
        self,
        session: Session,
        *,
        card_id: str,
        payload: dict[str, object],
        data_payload: dict[str, object] | None,
        expected_version: int,
        actor_login: str,
    ) -> tuple[models.Form100V2, models.Form100DataV2]:
        row = self.get_card(session, card_id)
        if row is None:
            raise ValueError("Карточка Form100 V2 не найдена")
        if int(row.version) != expected_version:
            raise ValueError("Конфликт версий Form100 V2: запись была изменена другим пользователем")
        self._apply_card_payload(row, payload)
        row.updated_at = _utc_now()  # type: ignore[assignment]
        row.updated_by = actor_login  # type: ignore[assignment]
        row.version = int(row.version) + 1  # type: ignore[assignment]

        data_row = self.get_data(session, card_id)
        if data_row is None:
            data_row = models.Form100DataV2(id=str(uuid4()), form100_id=card_id)
            session.add(data_row)
        if data_payload is not None:
            self._apply_data_payload(data_row, data_payload)
        session.flush()
        return row, data_row

    def archive_card(
        self,
        session: Session,
        *,
        card_id: str,
        expected_version: int,
        actor_login: str,
    ) -> models.Form100V2:
        row = self.get_card(session, card_id)
        if row is None:
            raise ValueError("Карточка Form100 V2 не найдена")
        if int(row.version) != expected_version:
            raise ValueError("Конфликт версий Form100 V2: запись была изменена другим пользователем")
        row.is_archived = True  # type: ignore[assignment]
        row.updated_at = _utc_now()  # type: ignore[assignment]
        row.updated_by = actor_login  # type: ignore[assignment]
        row.version = int(row.version) + 1  # type: ignore[assignment]
        session.flush()
        return row

    def delete_card(self, session: Session, card_id: str) -> bool:
        row = self.get_card(session, card_id)
        if row is None:
            return False
        session.delete(row)
        return True

    def set_pdf_artifact(
        self,
        session: Session,
        *,
        card_id: str,
        artifact_path: str,
        artifact_sha256: str,
        actor_login: str,
    ) -> models.Form100V2:
        row = self.get_card(session, card_id)
        if row is None:
            raise ValueError("Карточка Form100 V2 не найдена")
        row.artifact_path = artifact_path  # type: ignore[assignment]
        row.artifact_sha256 = artifact_sha256  # type: ignore[assignment]
        row.updated_at = _utc_now()  # type: ignore[assignment]
        row.updated_by = actor_login  # type: ignore[assignment]
        row.version = int(row.version) + 1  # type: ignore[assignment]
        session.flush()
        return row

    def find_cards_for_export(
        self,
        session: Session,
        *,
        card_id: str | None = None,
        filters: dict[str, object] | None = None,
    ) -> list[models.Form100V2]:
        if card_id:
            card = self.get_card(session, card_id)
            return [card] if card else []
        return self.list_cards(session, filters=filters, limit=10_000, offset=0)

    def to_data_dict(self, row: models.Form100DataV2 | None) -> dict[str, Any]:
        if row is None:
            return {
                "stub": {},
                "main": {},
                "lesion": {},
                "san_loss": {},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
                "medical_help": {},
                "bottom": {},
                "flags": {},
                "raw_payload": {},
            }
        return {
            "stub": _from_json(row.stub_json, default={}),
            "main": _from_json(row.main_json, default={}),
            "lesion": _from_json(row.lesion_json, default={}),
            "san_loss": _from_json(row.san_loss_json, default={}),
            "bodymap_gender": str(row.bodymap_gender or "M"),
            "bodymap_annotations": _from_json(row.bodymap_annotations_json, default=[]),
            "bodymap_tissue_types": _from_json(row.bodymap_tissue_types_json, default=[]),
            "medical_help": _from_json(row.mp_json, default={}),
            "bottom": _from_json(row.bottom_json, default={}),
            "flags": _from_json(row.flags_json, default={}),
            "raw_payload": _from_json(row.raw_payload_json, default={}),
        }

    def to_card_dict(self, row: models.Form100V2, data_row: models.Form100DataV2 | None) -> dict[str, Any]:
        payload = {column.name: getattr(row, column.name) for column in row.__table__.columns}
        payload["data"] = self.to_data_dict(data_row)
        return payload

    def _apply_card_payload(self, row: models.Form100V2, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            if not hasattr(row, key):
                continue
            if key in {"created_at", "updated_at", "signed_at"}:
                value = _parse_datetime(value)
            elif key == "birth_date":
                value = _parse_date(value)
            setattr(row, key, value)

    def _apply_data_payload(self, row: models.Form100DataV2, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            if key == "bodymap_gender":
                row.bodymap_gender = str(value or "M")  # type: ignore[assignment]
                continue
            mapped = _DATA_JSON_FIELD_MAP.get(key)
            if not mapped:
                continue
            default = "[]" if mapped in {"bodymap_annotations_json", "bodymap_tissue_types_json"} else "{}"
            setattr(row, mapped, _to_json(value, default=default))
