from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from app.domain.models.form100_v2 import (
    BODYMAP_ANNOTATION_TYPES,
    BODYMAP_SILHOUETTES,
    FORM100_V2_STATUS_DRAFT,
    FORM100_V2_STATUS_SIGNED,
)
from app.domain.types import JSONDict, JSONValue

_TISSUE_TYPES: set[str] = {"мягкие ткани", "кости", "сосуды", "полостные раны", "ожоги"}


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str
    hint: str | None = None


class Form100SigningError(ValueError):
    def __init__(self, errors: list[FieldError]) -> None:
        self.errors = errors
        error_lines = [f"- {error.field}: {error.message}" for error in errors]
        message = "Карточку Формы 100 нельзя подписать. Заполните обязательные поля:"
        if error_lines:
            message = f"{message}\n" + "\n".join(error_lines)
        super().__init__(message)


def validate_status_transition_v2(from_status: str, to_status: str) -> None:
    if from_status == to_status:
        return
    if from_status == FORM100_V2_STATUS_DRAFT and to_status == FORM100_V2_STATUS_SIGNED:
        return
    raise ValueError("Разрешен только переход статуса DRAFT -> SIGNED")


def validate_card_payload_v2(payload: Mapping[str, object]) -> None:
    validate_for_draft(payload)


def validate_for_draft(payload: Mapping[str, object]) -> None:
    main = _section(payload, "main")
    bottom = _section(payload, "bottom")
    medical_help = _section(payload, "medical_help")
    flags = _section(payload, "flags")

    main_full_name = _first_text(main.get("main_full_name"), payload.get("main_full_name"))
    if not main_full_name:
        raise ValueError("Поле ФИО обязательно для формы 100")
    main_unit = _first_text(main.get("main_unit"), payload.get("main_unit"))
    if not main_unit:
        raise ValueError("Поле подразделения обязательно для формы 100")

    diagnosis = _first_text(bottom.get("main_diagnosis"), payload.get("main_diagnosis"))
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

    bodymap_gender = str(payload.get("bodymap_gender") or _section_value(payload, "bodymap_gender") or "M").upper()
    if bodymap_gender not in {"M", "F"}:
        raise ValueError("bodymap_gender должен быть 'M' или 'F'")

    tissue_types_raw = payload.get("bodymap_tissue_types")
    if tissue_types_raw is None:
        tissue_types_raw = _section_value(payload, "bodymap_tissue_types")
    if tissue_types_raw is None:
        tissue_types: list[JSONValue] = []
    elif isinstance(tissue_types_raw, list):
        tissue_types = cast(list[JSONValue], tissue_types_raw)
    else:
        raise ValueError("bodymap_tissue_types должен быть списком")
    for item in tissue_types:
        if str(item) not in _TISSUE_TYPES:
            raise ValueError(f"Недопустимый тип ткани: {item}")

    annotations_raw = payload.get("bodymap_annotations")
    if annotations_raw is None:
        annotations_raw = _section_value(payload, "bodymap_annotations")
    if annotations_raw is None:
        annotations: list[JSONValue] = []
    elif isinstance(annotations_raw, list):
        annotations = cast(list[JSONValue], annotations_raw)
    else:
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


def validate_for_signing(payload: Mapping[str, object], *, signed_by: str | None) -> None:
    main = _section(payload, "main")
    stub = _section(payload, "stub")
    lesion = _section(payload, "lesion")
    san_loss = _section(payload, "san_loss")
    medical_help = _section(payload, "medical_help")
    bottom = _section(payload, "bottom")
    flags = _section(payload, "flags")

    errors: list[FieldError] = []
    _require_text(errors, "main.main_full_name", "Укажите ФИО.", main.get("main_full_name"), payload.get("main_full_name"))
    _require_text(errors, "main.main_rank", "Укажите воинское звание.", main.get("main_rank"), stub.get("stub_rank"))
    _require_text(errors, "main.main_unit", "Укажите воинскую часть.", main.get("main_unit"), payload.get("main_unit"), stub.get("stub_unit"))
    _require_text(errors, "main.birth_date", "Укажите дату рождения.", payload.get("birth_date"), main.get("birth_date"))
    _require_text(errors, "bottom.main_diagnosis", "Укажите основной диагноз.", bottom.get("main_diagnosis"), payload.get("main_diagnosis"), stub.get("stub_diagnosis"))
    _require_text(errors, "main.main_injury_date", "Укажите дату ранения или заболевания.", main.get("main_injury_date"), stub.get("stub_injury_date"))
    _require_text(errors, "main.main_injury_time", "Укажите время ранения или заболевания.", main.get("main_injury_time"), stub.get("stub_injury_time"))
    _require_text(errors, "signed_by", "Укажите подписанта.", signed_by)

    if not (_section_has_selected_value(lesion, exclude={"isolation_required"}) or _section_has_selected_value(san_loss)):
        errors.append(FieldError("lesion_or_san_loss", "Укажите вид поражения или вид санитарных потерь."))

    if _truthy(flags.get("flag_emergency")):
        _require_text(errors, "bottom.evacuation_priority", "Укажите очередность эвакуации.", bottom.get("evacuation_priority"))

    if _truthy(medical_help.get("mp_antibiotic")):
        _require_text(errors, "medical_help.mp_antibiotic_dose", "Укажите дозу/детали антибиотика.", medical_help.get("mp_antibiotic_dose"))
    if _truthy(medical_help.get("mp_analgesic")):
        _require_text(errors, "medical_help.mp_analgesic_dose", "Укажите дозу/детали обезболивающего.", medical_help.get("mp_analgesic_dose"))

    if errors:
        raise Form100SigningError(errors)


def build_changed_paths_v2(before: Mapping[str, object], after: Mapping[str, object]) -> dict[str, dict[str, object]]:
    before_changes: dict[str, object] = {}
    after_changes: dict[str, object] = {}
    _walk_diff(before, after, "", before_changes, after_changes)
    return {"before": before_changes, "after": after_changes}


def _walk_diff(
    before: object,
    after: object,
    path: str,
    before_changes: dict[str, object],
    after_changes: dict[str, object],
) -> None:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        before_map = cast(Mapping[object, object], before)
        after_map = cast(Mapping[object, object], after)
        keys: list[object] = sorted(set(before_map.keys()) | set(after_map.keys()), key=str)
        for key in keys:
            key_str = str(key)
            child_path = f"{path}.{key_str}" if path else key_str
            _walk_diff(before_map.get(key), after_map.get(key), child_path, before_changes, after_changes)
        return

    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            before_changes[path] = before
            after_changes[path] = after
        return

    if before != after:
        before_changes[path] = before
        after_changes[path] = after


def _validate_bool_with_details(
    payload: Mapping[str, JSONValue], *, bool_key: str, details_key: str, label: str
) -> None:
    enabled = payload.get(bool_key)
    details = str(payload.get(details_key) or "").strip()
    if bool(enabled) and not details:
        raise ValueError(f"{label}: укажите дозу/детали")


def _section(payload: Mapping[str, object], name: str) -> JSONDict:
    data = _as_dict(payload.get("data"))
    if name in data:
        return _as_dict(data.get(name))
    return _as_dict(payload.get(name))


def _section_value(payload: Mapping[str, object], name: str) -> object:
    data = _as_dict(payload.get("data"))
    if name in data:
        return data.get(name)
    return payload.get(name)


def _as_dict(value: object) -> JSONDict:
    if isinstance(value, Mapping):
        return {str(key): cast(JSONValue, item) for key, item in value.items()}
    return {}


def _first_text(*values: object) -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return ""


def _require_text(errors: list[FieldError], field: str, message: str, *values: object) -> None:
    if not _first_text(*values):
        errors.append(FieldError(field, message))


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "да"}


def _section_has_selected_value(section: Mapping[str, object], *, exclude: set[str] | None = None) -> bool:
    excluded = exclude or set()
    return any(key not in excluded and _truthy(value) for key, value in section.items())


def _as_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None
