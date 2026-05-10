from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

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
    "hospital_case_no": "Номер истории болезни",
    "department_id": "Отделение",
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


def format_annotation_type(code: str | None) -> str:
    return _format_code(code, _ANNOTATION_TYPE_LABELS)


def format_silhouette(code: str | None) -> str:
    return _format_code(code, _SILHOUETTE_LABELS)


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
