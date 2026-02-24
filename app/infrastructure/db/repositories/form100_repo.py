from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db import models_sqlalchemy as models

_JSON_LIST_MAP = {
    "trauma_types": "trauma_types_json",
    "wound_types": "wound_types_json",
    "features": "features_json",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _to_json(value: object, *, default: str) -> str:
    if value is None:
        return default
    return json.dumps(value, ensure_ascii=False)


def _from_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _from_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


class Form100Repository:
    def list_cards(
        self,
        session: Session,
        *,
        filters: dict[str, object] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[models.Form100Card]:
        filters = filters or {}
        stmt = select(models.Form100Card)

        query_text = str(filters.get("query") or "").strip()
        if query_text:
            like = f"%{query_text}%"
            stmt = stmt.where(
                models.Form100Card.last_name.ilike(like)
                | models.Form100Card.first_name.ilike(like)
                | models.Form100Card.middle_name.ilike(like)
                | models.Form100Card.unit.ilike(like)
                | models.Form100Card.dog_tag_number.ilike(like)
                | models.Form100Card.diagnosis_text.ilike(like)
            )

        status = filters.get("status")
        if status:
            stmt = stmt.where(models.Form100Card.status == str(status))

        unit = str(filters.get("unit") or "").strip()
        if unit:
            stmt = stmt.where(models.Form100Card.unit.ilike(f"%{unit}%"))

        dog_tag_number = str(filters.get("dog_tag_number") or "").strip()
        if dog_tag_number:
            stmt = stmt.where(models.Form100Card.dog_tag_number.ilike(f"%{dog_tag_number}%"))

        arrival_from = filters.get("arrival_date_from")
        if isinstance(arrival_from, date):
            stmt = stmt.where(models.Form100Card.arrival_dt >= datetime.combine(arrival_from, datetime.min.time()))
        arrival_to = filters.get("arrival_date_to")
        if isinstance(arrival_to, date):
            stmt = stmt.where(models.Form100Card.arrival_dt <= datetime.combine(arrival_to, datetime.max.time()))

        injury_from = filters.get("injury_date_from")
        if isinstance(injury_from, date):
            stmt = stmt.where(models.Form100Card.injury_dt >= datetime.combine(injury_from, datetime.min.time()))
        injury_to = filters.get("injury_date_to")
        if isinstance(injury_to, date):
            stmt = stmt.where(models.Form100Card.injury_dt <= datetime.combine(injury_to, datetime.max.time()))

        stmt = stmt.order_by(models.Form100Card.updated_at.desc()).offset(offset).limit(limit)
        return list(session.execute(stmt).scalars())

    def get_card(self, session: Session, card_id: str) -> models.Form100Card | None:
        return session.get(models.Form100Card, card_id)

    def create_card(
        self,
        session: Session,
        *,
        card_id: str | None,
        payload: dict[str, object],
        actor_login: str,
    ) -> models.Form100Card:
        now = _utc_now()
        row = models.Form100Card(
            id=card_id or str(uuid4()),
            created_at=now,
            updated_at=now,
            created_by=actor_login,
            updated_by=actor_login,
            status=str(payload.get("status") or "DRAFT"),
            version=1,
        )
        self._apply_card_payload(row, payload)
        session.add(row)
        session.flush()
        return row

    def touch_card(
        self,
        session: Session,
        *,
        card_id: str,
        expected_version: int,
        actor_login: str,
    ) -> models.Form100Card:
        row = self.get_card(session, card_id)
        if row is None:
            raise ValueError("Карточка Form100 не найдена")
        if int(row.version) != expected_version:
            raise ValueError("Конфликт версий Form100: запись была изменена другим пользователем")
        row.version = int(row.version) + 1  # type: ignore[assignment]
        row.updated_at = _utc_now()  # type: ignore[assignment]
        row.updated_by = actor_login  # type: ignore[assignment]
        session.flush()
        return row

    def update_card(
        self,
        session: Session,
        *,
        card_id: str,
        payload: dict[str, object],
        expected_version: int,
        actor_login: str,
    ) -> models.Form100Card:
        row = self.get_card(session, card_id)
        if row is None:
            raise ValueError("Карточка Form100 не найдена")
        if int(row.version) != expected_version:
            raise ValueError("Конфликт версий Form100: запись была изменена другим пользователем")
        self._apply_card_payload(row, payload)
        row.version = int(row.version) + 1  # type: ignore[assignment]
        row.updated_at = _utc_now()  # type: ignore[assignment]
        row.updated_by = actor_login  # type: ignore[assignment]
        session.flush()
        return row

    def delete_card(self, session: Session, card_id: str) -> bool:
        row = self.get_card(session, card_id)
        if row is None:
            return False
        session.delete(row)
        return True

    def list_marks(self, session: Session, card_id: str) -> list[models.Form100Mark]:
        stmt = select(models.Form100Mark).where(models.Form100Mark.card_id == card_id).order_by(models.Form100Mark.created_at.asc())
        return list(session.execute(stmt).scalars())

    def replace_marks(
        self,
        session: Session,
        *,
        card_id: str,
        marks: list[dict[str, object]],
        actor_login: str,
    ) -> list[models.Form100Mark]:
        session.query(models.Form100Mark).where(models.Form100Mark.card_id == card_id).delete()
        now = _utc_now()
        rows: list[models.Form100Mark] = []
        for item in marks:
            row = models.Form100Mark(
                id=str(uuid4()),
                card_id=card_id,
                side=str(item.get("side") or "FRONT"),
                type=str(item.get("type") or "NOTE_PIN"),
                shape_json=_to_json(item.get("shape_json") or {}, default="{}"),
                meta_json=_to_json(item.get("meta_json") or {}, default="{}"),
                created_at=cast_datetime(item.get("created_at")) or now,
                created_by=str(item.get("created_by") or actor_login),
            )
            session.add(row)
            rows.append(row)
        session.flush()
        return rows

    def list_stages(self, session: Session, card_id: str) -> list[models.Form100Stage]:
        stmt = (
            select(models.Form100Stage)
            .where(models.Form100Stage.card_id == card_id)
            .order_by(models.Form100Stage.received_at.asc())
        )
        return list(session.execute(stmt).scalars())

    def add_stage(
        self,
        session: Session,
        *,
        card_id: str,
        payload: dict[str, object],
    ) -> models.Form100Stage:
        row = models.Form100Stage(
            id=str(uuid4()),
            card_id=card_id,
            stage_name=str(payload.get("stage_name") or ""),
            received_at=cast_datetime(payload.get("received_at")),
            updated_diagnosis_text=cast_str(payload.get("updated_diagnosis_text")),
            updated_diagnosis_code=cast_str(payload.get("updated_diagnosis_code")),
            procedures_text=cast_str(payload.get("procedures_text")),
            evac_next_destination=cast_str(payload.get("evac_next_destination")),
            evac_next_dt=cast_datetime(payload.get("evac_next_dt")),
            condition_at_transfer=cast_str(payload.get("condition_at_transfer")),
            outcome=cast_str(payload.get("outcome")),
            outcome_date=cast_date(payload.get("outcome_date")),
            burial_place=cast_str(payload.get("burial_place")),
            signed_by=cast_str(payload.get("signed_by")),
            signed_at=cast_datetime(payload.get("signed_at")),
        )
        session.add(row)
        session.flush()
        return row

    def replace_stages(
        self,
        session: Session,
        *,
        card_id: str,
        stages: list[dict[str, object]],
    ) -> list[models.Form100Stage]:
        session.query(models.Form100Stage).where(models.Form100Stage.card_id == card_id).delete()
        rows: list[models.Form100Stage] = []
        for item in stages:
            row = self.add_stage(session, card_id=card_id, payload=item)
            rows.append(row)
        return rows

    def _apply_card_payload(self, row: models.Form100Card, payload: dict[str, object]) -> None:
        mapped_payload: dict[str, object] = {}
        for key, value in payload.items():
            if key in _JSON_LIST_MAP:
                mapped_payload[_JSON_LIST_MAP[key]] = _to_json(value or [], default="[]")
            else:
                mapped_payload[key] = value

        for key, value in mapped_payload.items():
            if hasattr(row, key):
                setattr(row, key, value)

    @staticmethod
    def to_card_dict(row: models.Form100Card) -> dict[str, object]:
        data: dict[str, object] = {}
        for col in row.__table__.columns:
            data[col.name] = getattr(row, col.name)
        data["trauma_types"] = _from_json_list(str(data.pop("trauma_types_json", "") or ""))
        data["wound_types"] = _from_json_list(str(data.pop("wound_types_json", "") or ""))
        data["features"] = _from_json_list(str(data.pop("features_json", "") or ""))
        return data

    @staticmethod
    def to_mark_dict(row: models.Form100Mark) -> dict[str, object]:
        return {
            "id": row.id,
            "card_id": row.card_id,
            "side": row.side,
            "type": row.type,
            "shape_json": _from_json_dict(cast(str | None, row.shape_json)),
            "meta_json": _from_json_dict(cast(str | None, row.meta_json)),
            "created_at": row.created_at,
            "created_by": row.created_by,
        }

    @staticmethod
    def to_stage_dict(row: models.Form100Stage) -> dict[str, object]:
        return {
            "id": row.id,
            "card_id": row.card_id,
            "stage_name": row.stage_name,
            "received_at": row.received_at,
            "updated_diagnosis_text": row.updated_diagnosis_text,
            "updated_diagnosis_code": row.updated_diagnosis_code,
            "procedures_text": row.procedures_text,
            "evac_next_destination": row.evac_next_destination,
            "evac_next_dt": row.evac_next_dt,
            "condition_at_transfer": row.condition_at_transfer,
            "outcome": row.outcome,
            "outcome_date": row.outcome_date,
            "burial_place": row.burial_place,
            "signed_by": row.signed_by,
            "signed_at": row.signed_at,
        }

    def find_cards_for_export(
        self,
        session: Session,
        *,
        card_id: str | None = None,
        filters: dict[str, object] | None = None,
    ) -> list[models.Form100Card]:
        if card_id:
            row = self.get_card(session, card_id)
            return [row] if row else []
        return self.list_cards(session, filters=filters, limit=10_000, offset=0)


def cast_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            pass
        date_and_time = text.split(" ")
        if len(date_and_time) == 2 and "." in date_and_time[0]:
            date_parts = date_and_time[0].split(".")
            time_parts = date_and_time[1].split(":")
            if len(date_parts) == 3 and len(time_parts) >= 2:
                try:
                    day, month, year = (int(part) for part in date_parts)
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2]) if len(time_parts) > 2 else 0
                    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
                except ValueError:
                    return None
        return None
    return None


def cast_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
        parts = value.split(".")
        if len(parts) == 3:
            try:
                day, month, year = (int(part) for part in parts)
                return date(year, month, day)
            except ValueError:
                return None
        return None
    return None


def cast_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
