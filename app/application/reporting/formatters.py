from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, cast

from app.domain.constants import IsmpType, MilitaryCategory

DASH = "—"

LOCALIZED_HEADERS: dict[str, str] = {
    "id": "ID пациента",
    "full_name": "ФИО",
    "dob": "Дата рождения",
    "sex": "Пол",
    "category": "Категория",
    "military_unit": "Воинская часть",
    "military_district": "Военный округ",
    "created_at": "Создано",
    "created_by": "Создал",
    "created_by_name": "Создал",
    "hospital_case_no": "Номер истории болезни",
    "department_id": "Отделение",
    "department_name": "Отделение",
    "patient_id": "ID пациента",
    "emr_case_id": "ID госпитализации",
    "version_no": "Версия",
    "admission_date": "Дата поступления",
    "injury_date": "Дата травмы",
    "outcome_date": "Дата исхода",
    "outcome_type": "Исход",
    "severity": "Тяжесть",
    "vph_sp_score": "ВПХ-СП",
    "vph_p_or_score": "ВПХ-П/ОР",
    "sofa_score": "SOFA",
    "days_to_admission": "Дни до поступления",
    "length_of_stay_days": "Койко-дней",
    "is_current": "Актуальна",
    "lab_no": "Лаб. номер",
    "barcode": "Штрихкод",
    "material_type_id": "Тип материала",
    "material_type_name": "Тип материала",
    "material_location": "Локализация материала",
    "medium": "Среда",
    "study_kind": "Тип исследования",
    "ordered_at": "Назначено",
    "taken_at": "Взято",
    "delivered_at": "Доставлено",
    "growth_result_at": "Результат роста",
    "growth_flag": "Рост",
    "colony_desc": "Колонии/морфология",
    "microscopy": "Микроскопия",
    "cfu": "КОЕ",
    "qc_due_at": "Срок QC",
    "qc_status": "Статус QC",
    "room": "Помещение",
    "sampling_point": "Точка отбора",
    "ris": "Чувствительность",
    "mic_mg_l": "МИК мг/л",
    "method": "Метод",
    "antibiotic_id": "Антибиотик",
    "group_id": "Группа",
    "microorganism_id": "Микроорганизм",
    "microorganism_free": "Микроорганизм (свободный)",
    "sanitary_sample_id": "ID пробы (санит.)",
    "lab_sample_id": "ID пробы",
}

_SEX_LABELS = {
    "M": "Мужской",
    "F": "Женский",
}

_EXPORT_SEX_LABELS = {
    "M": "М",
    "F": "Ж",
    "U": DASH,
}

_OUTCOME_LABELS = {
    "discharge": "Выписан",
    "transfer": "Перевод",
    "death": "Скончался",
}

_SEVERITY_LABELS = {
    "mild": "Лёгкая",
    "light": "Лёгкая",
    "moderate": "Средняя",
    "medium": "Средняя",
    "severe": "Тяжёлая",
    "critical": "Критическая",
}

_STUDY_KIND_LABELS = {
    "primary": "Первичное",
    "repeat": "Повторное",
}

_ROUTE_LABELS = {
    "iv": "В/в",
    "po": "Внутрь",
    "im": "В/м",
    "sc": "П/к",
    "subcutaneous": "П/к",
    "topical": "Местно",
    "inhalation": "Ингаляционно",
}

_QC_STATUS_LABELS = {
    "valid": "Действителен",
    "expired": "Просрочен",
    "pending": "Ожидает",
    "conditional": "Условно действителен",
    "rejected": "Отклонён",
}

_RIS_LABELS = {
    "S": "Чувствительный",
    "I": "Промежуточный",
    "R": "Резистентный",
}

_METHOD_LABELS = {
    "disk": "Диско-диффузионный",
    "etest": "Е-тест",
    "broth": "Бульонный",
}

_DIAGNOSIS_KIND_LABELS = {
    "admission": "При поступлении",
    "discharge": "При выписке",
    "complication": "Осложнение",
}

_GROWTH_FLAG_LABELS = {
    0: "Рост не выявлен",
    1: "Рост выявлен",
    "0": "Рост не выявлен",
    "1": "Рост выявлен",
}

_FORM100_STATUS_LABELS = {
    "DRAFT": "Черновик",
    "SIGNED": "Подписан",
}

EXPORT_ENUM_LABELS: dict[str, dict[object, str]] = {
    "sex": cast(dict[object, str], _EXPORT_SEX_LABELS),
    "outcome_type": cast(dict[object, str], _OUTCOME_LABELS),
    "severity": cast(dict[object, str], _SEVERITY_LABELS),
    "study_kind": cast(dict[object, str], _STUDY_KIND_LABELS),
    "route": cast(dict[object, str], _ROUTE_LABELS),
    "qc_status": cast(dict[object, str], _QC_STATUS_LABELS),
    "method": cast(dict[object, str], _METHOD_LABELS),
    "ris": cast(dict[object, str], _RIS_LABELS),
    "kind": cast(dict[object, str], _DIAGNOSIS_KIND_LABELS),
    "growth_flag": _GROWTH_FLAG_LABELS,
    "status": cast(dict[object, str], _FORM100_STATUS_LABELS),
}

_ANNOTATION_TYPE_LABELS = {
    "WOUND_X": "Рана",
    "BURN_HATCH": "Ожог",
    "AMPUTATION": "Ампутация",
    "TOURNIQUET": "Жгут",
    "NOTE_PIN": "Заметка",
}

_SILHOUETTE_LABELS = {
    "male_front": "Мужской, спереди",
    "male_back": "Мужской, сзади",
    "female_front": "Женский, спереди",
    "female_back": "Женский, сзади",
}

_ISMP_TYPES = {
    "ВАП",
    "КА-ИК",
    "КА-ИМП",
    "ИОХВ",
    "ПАП",
    "БАК",
    "СЕПСИС",
    *IsmpType.values(),
}

_MILITARY_CATEGORIES = set(MilitaryCategory.values())


def _parse_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_code(code: str | None, labels: dict[str, str]) -> str:
    if code is None:
        return DASH
    normalized = code.strip()
    if not normalized:
        return DASH
    return labels.get(normalized, DASH)


def format_date(value: date | str | None) -> str:
    parsed = _parse_date(value)
    if parsed is None:
        return DASH
    return parsed.strftime("%d.%m.%Y")


def format_datetime(value: datetime | str | None, *, with_seconds: bool = False) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return DASH
    fmt = "%d.%m.%Y %H:%M:%S" if with_seconds else "%d.%m.%Y %H:%M"
    return parsed.replace(microsecond=0).strftime(fmt)


def format_bool(value: bool | int | None) -> str:
    if value is None:
        return DASH
    if value is True or value == 1:
        return "Да"
    if value is False or value == 0:
        return "Нет"
    return DASH


def format_percent(value: float | None, *, digits: int = 1) -> str:
    if value is None:
        return DASH
    return f"{value * 100:.{digits}f}%"


def format_missing(value: Any) -> str:
    if value is None or value == "":
        return DASH
    return str(value)


def format_sex(code: str | None) -> str:
    if code is None:
        return DASH
    return _SEX_LABELS.get(code.strip().upper(), DASH)


def format_outcome(code: str | None) -> str:
    if code is None:
        return DASH
    return _OUTCOME_LABELS.get(code.strip().lower(), DASH)


def format_severity(code: str | None) -> str:
    if code is None:
        return DASH
    return _SEVERITY_LABELS.get(code.strip().lower(), DASH)


def format_study_kind(code: str | None) -> str:
    if code is None:
        return DASH
    return _STUDY_KIND_LABELS.get(code.strip().lower(), DASH)


def format_route(code: str | None) -> str:
    if code is None:
        return DASH
    return _ROUTE_LABELS.get(code.strip().lower(), DASH)


def format_qc_status(code: str | None) -> str:
    if code is None:
        return DASH
    return _QC_STATUS_LABELS.get(code.strip().lower(), DASH)


def format_growth_flag(value: int | bool | None) -> str:
    return format_bool(value)


def format_ris(code: str | None) -> str:
    if code is None:
        return DASH
    return _RIS_LABELS.get(code.strip().upper(), DASH)


def _normalize_enum_text(value: object) -> str:
    return str(value).strip().casefold()


def _machine_enum_value(field: str, value: object) -> object:
    mapping = EXPORT_ENUM_LABELS.get(field)
    if mapping is None:
        return value
    if value in mapping:
        return value
    normalized_value = _normalize_enum_text(value)
    for machine_value in mapping:
        if _normalize_enum_text(machine_value) == normalized_value:
            return machine_value
    return value


def format_export_enum(field: str, value: object) -> object:
    mapping = EXPORT_ENUM_LABELS.get(field)
    if mapping is None or value is None:
        return value
    machine_value = _machine_enum_value(field, value)
    return mapping.get(machine_value, value)


def export_enum_reverse_labels() -> dict[str, dict[str, object]]:
    reverse: dict[str, dict[str, object]] = {}
    for field, mapping in EXPORT_ENUM_LABELS.items():
        field_reverse: dict[str, object] = {}
        for machine_value, label in mapping.items():
            field_reverse.setdefault(_normalize_enum_text(label), machine_value)
        reverse[field] = field_reverse
    return reverse


def normalize_export_enum(field: str, value: object) -> object:
    if value is None or value == "":
        return value
    machine_value = _machine_enum_value(field, value)
    if machine_value != value:
        return machine_value
    return export_enum_reverse_labels().get(field, {}).get(_normalize_enum_text(value), value)


def format_method(code: str | None) -> str:
    if code is None:
        return DASH
    return _METHOD_LABELS.get(code.strip().lower(), DASH)


def format_diagnosis_kind(code: str | None) -> str:
    if code is None:
        return DASH
    return _DIAGNOSIS_KIND_LABELS.get(code.strip().lower(), DASH)


def format_form100_status(code: str | None) -> str:
    if code is None:
        return DASH
    normalized = code.strip().upper()
    if not normalized:
        return DASH
    return _FORM100_STATUS_LABELS.get(normalized, normalized)


def format_annotation_type(code: str | None) -> str:
    return _format_code(code, _ANNOTATION_TYPE_LABELS)


def format_silhouette(code: str | None) -> str:
    return _format_code(code, _SILHOUETTE_LABELS)


def format_silhouette_short(code: str | None) -> str:
    """'male_front'/'female_front' -> 'Спереди'; '*_back' -> 'Сзади'; None -> '—'."""
    if code is None:
        return DASH
    normalized = code.strip().lower()
    if not normalized:
        return DASH
    if normalized.endswith("_front") or normalized == "front":
        return "Спереди"
    if normalized.endswith("_back") or normalized == "back":
        return "Сзади"
    return DASH


def format_ismp_type(code: str | None) -> str:
    if code is None:
        return DASH
    normalized = code.strip()
    if not normalized:
        return DASH
    return normalized if normalized in _ISMP_TYPES else DASH


def format_military_category(code: str | None) -> str:
    if code is None:
        return DASH
    normalized = code.strip()
    if not normalized:
        return DASH
    return normalized if normalized in _MILITARY_CATEGORIES else DASH


def localize_header(field: str) -> str:
    return LOCALIZED_HEADERS.get(field, field)


def localize_headers(fields: list[str]) -> list[str]:
    return [localize_header(field) for field in fields]


def to_iso_utc(dt: datetime | None) -> str | None:
    """datetime -> ISO 8601 с TZ (+00:00). None -> None. Используется для JSON-экспорта."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()
