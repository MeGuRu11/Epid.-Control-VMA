from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.models.form100_v2 import (
    BODYMAP_ANNOTATION_TYPES,
    BODYMAP_SILHOUETTES,
    FORM100_V2_STATUS_DRAFT,
    FORM100_V2_STATUS_SIGNED,
)

_TISSUE_TYPES = {"мягкие ткани", "кости", "сосуды", "полостные раны", "ожоги"}


def validate_status_transition_v2(from_status: str, to_status: str) -> None:
    if from_status == to_status:
        return
    if from_status == FORM100_V2_STATUS_DRAFT and to_status == FORM100_V2_STATUS_SIGNED:
        return
    raise ValueError("Разрешен только переход статуса DRAFT -> SIGNED")


def validate_card_payload_v2(payload: dict[str, Any]) -> None:
    main = _as_dict(payload.get("main"))
    bottom = _as_dict(payload.get("bottom"))
    medical_help = _as_dict(payload.get("medical_help"))
    flags = _as_dict(payload.get("flags"))

    main_full_name = str(main.get("main_full_name") or payload.get("main_full_name") or "").strip()
    if not main_full_name:
        raise ValueError("Поле ФИО обязательно для формы 100")
    main_unit = str(main.get("main_unit") or payload.get("main_unit") or "").strip()
    if not main_unit:
        raise ValueError("Поле подразделения обязательно для формы 100")

    diagnosis = str(bottom.get("main_diagnosis") or payload.get("main_diagnosis") or "").strip()
    if not diagnosis:
        raise ValueError("Поле диагноза обязательно для формы 100")

    _validate_bool_with_details(
        medical_help,
        bool_key="mp_antibiotic",
        details_key="mp_antibiotic_dose",
        label="Антибиотик",
    )
    _validate_bool_with_details(
        medical_help,
        bool_key="mp_analgesic",
        details_key="mp_analgesic_dose",
        label="Обезболивающее",
    )

    for key in ("flag_emergency", "flag_radiation", "flag_sanitation"):
        if key in flags and not isinstance(flags.get(key), bool):
            raise ValueError(f"Флаг {key} должен быть логическим значением")

    bodymap_gender = str(payload.get("bodymap_gender") or "M").upper()
    if bodymap_gender not in {"M", "F"}:
        raise ValueError("bodymap_gender должен быть 'M' или 'F'")

    tissue_types = payload.get("bodymap_tissue_types") or []
    if not isinstance(tissue_types, list):
        raise ValueError("bodymap_tissue_types должен быть списком")
    for item in tissue_types:
        if str(item) not in _TISSUE_TYPES:
            raise ValueError(f"Недопустимый тип ткани: {item}")

    annotations = payload.get("bodymap_annotations") or []
    if not isinstance(annotations, list):
        raise ValueError("bodymap_annotations должен быть списком")
    for annotation in annotations:
        item = _as_dict(annotation)
        annotation_type = str(item.get("annotation_type") or "").upper()
        if annotation_type not in BODYMAP_ANNOTATION_TYPES:
            raise ValueError(f"Недопустимый тип аннотации: {annotation_type}")
        silhouette = str(item.get("silhouette") or "").lower()
        if silhouette not in BODYMAP_SILHOUETTES:
            raise ValueError(f"Недопустимый силуэт: {silhouette}")
        x = _as_float(item.get("x"))
        y = _as_float(item.get("y"))
        if x is None or y is None:
            raise ValueError("Координаты аннотаций должны быть числами")
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError("Координаты аннотаций должны быть в диапазоне 0..1")


def build_changed_paths_v2(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    before_changes: dict[str, Any] = {}
    after_changes: dict[str, Any] = {}
    _walk_diff(before, after, "", before_changes, after_changes)
    return {"before": before_changes, "after": after_changes}


def _walk_diff(
    before: Any,
    after: Any,
    path: str,
    before_changes: dict[str, Any],
    after_changes: dict[str, Any],
) -> None:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            child_path = f"{path}.{key}" if path else str(key)
            _walk_diff(before.get(key), after.get(key), child_path, before_changes, after_changes)
        return

    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            before_changes[path] = before
            after_changes[path] = after
        return

    if before != after:
        before_changes[path] = before
        after_changes[path] = after


def _validate_bool_with_details(payload: Mapping[str, Any], *, bool_key: str, details_key: str, label: str) -> None:
    enabled = payload.get(bool_key)
    details = str(payload.get(details_key) or "").strip()
    if bool(enabled) and not details:
        raise ValueError(f"{label}: укажите дозу/детали")


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:  # noqa: BLE001
        return None
