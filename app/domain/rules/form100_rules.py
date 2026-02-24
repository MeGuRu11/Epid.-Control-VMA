from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.domain.models.form100 import FORM100_STATUS_DRAFT, FORM100_STATUS_SIGNED

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    FORM100_STATUS_DRAFT: {FORM100_STATUS_SIGNED},
    FORM100_STATUS_SIGNED: set(),
}

_DETAIL_RULES: tuple[tuple[str, str, str], ...] = (
    ("care_analgesia_given", "care_analgesia_details", "Анальгезия"),
    ("care_antibiotic_given", "care_antibiotic_details", "Антибиотик"),
    ("care_antidote_given", "care_antidote_details", "Антидот"),
    ("infusion_performed", "infusion_details", "Инфузия"),
    ("transfusion_performed", "transfusion_details", "Трансфузия"),
    ("sanitation_performed", "sanitation_details", "Санитарная обработка"),
)


def validate_status_transition(current_status: str, new_status: str) -> None:
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(f"Переход статуса {current_status} -> {new_status} запрещён")


def validate_card_payload(payload: Mapping[str, Any]) -> None:
    injury_dt = payload.get("injury_dt")
    arrival_dt = payload.get("arrival_dt")
    _validate_datetime_order(injury_dt=injury_dt, arrival_dt=arrival_dt)
    _validate_detail_flags(payload)
    _validate_volume_fields(payload)


def _validate_datetime_order(*, injury_dt: Any, arrival_dt: Any) -> None:
    if isinstance(injury_dt, datetime) and isinstance(arrival_dt, datetime) and arrival_dt < injury_dt:
        raise ValueError("Дата поступления не может быть раньше даты травмы")


def _validate_detail_flags(payload: Mapping[str, Any]) -> None:
    for flag_name, detail_name, title in _DETAIL_RULES:
        flag = bool(payload.get(flag_name))
        detail_value = payload.get(detail_name)
        detail = detail_value.strip() if isinstance(detail_value, str) else detail_value
        if flag and not detail:
            raise ValueError(f"Укажите детали для поля: {title}")
        if not flag and detail:
            raise ValueError(f"Поле '{title}' содержит детали при выключенном флаге")


def _validate_volume_fields(payload: Mapping[str, Any]) -> None:
    _validate_volume_pair(
        payload=payload,
        performed_key="infusion_performed",
        volume_key="infusion_volume_ml",
        title="Инфузия",
    )
    _validate_volume_pair(
        payload=payload,
        performed_key="transfusion_performed",
        volume_key="transfusion_volume_ml",
        title="Трансфузия",
    )


def _validate_volume_pair(
    *,
    payload: Mapping[str, Any],
    performed_key: str,
    volume_key: str,
    title: str,
) -> None:
    performed = bool(payload.get(performed_key))
    volume = payload.get(volume_key)
    if volume is not None and isinstance(volume, int) and volume < 0:
        raise ValueError(f"{title}: объём не может быть отрицательным")
    if performed and volume is not None and isinstance(volume, int) and volume <= 0:
        raise ValueError(f"{title}: укажите объём больше 0")
    if not performed and volume not in (None, 0):
        raise ValueError(f"{title}: объём заполнен при выключенном флаге")


def build_changed_paths(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    changed_before: dict[str, Any] = {}
    changed_after: dict[str, Any] = {}
    _collect_changes(before, after, "", changed_before, changed_after)
    return {"before": changed_before, "after": changed_after}


def _collect_changes(
    before: Any,
    after: Any,
    prefix: str,
    changed_before: dict[str, Any],
    changed_after: dict[str, Any],
) -> None:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        keys = set(before.keys()) | set(after.keys())
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            _collect_changes(before.get(key), after.get(key), path, changed_before, changed_after)
        return

    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            changed_before[prefix] = before
            changed_after[prefix] = after
        return

    if _normalize(before) != _normalize(after):
        changed_before[prefix] = before
        changed_after[prefix] = after


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value
