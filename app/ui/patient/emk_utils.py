from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from app.application.dto.emz_dto import EmzCaseDetail


def format_patient_sex(value: str | None) -> str:
    if not value:
        return "вЂ”"
    value_clean = value.strip()
    if not value_clean:
        return "вЂ”"
    lower = value_clean.lower()
    if lower in {"m", "male", "Рј", "РјСѓР¶", "РјСѓР¶СЃРєРѕР№"}:
        return "РњСѓР¶СЃРєРѕР№"
    if lower in {"f", "female", "Р¶", "Р¶РµРЅ", "Р¶РµРЅСЃРєРёР№"}:
        return "Р–РµРЅСЃРєРёР№"
    return value_clean


def format_emk_datetime(value: datetime | date | None) -> str:
    if value is None:
        return "вЂ”"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    return value.strftime("%d.%m.%Y")


def normalize_filter_date(raw_date: date | None, empty_date: date) -> date | None:
    if raw_date == empty_date:
        return None
    return raw_date


def _extract_case_date(value: datetime | date | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def matches_case_filters(
    detail: EmzCaseDetail,
    department_id: int | None,
    from_date: date | None,
    to_date: date | None,
) -> bool:
    if department_id is not None and detail.department_id != department_id:
        return False
    admission_date = _extract_case_date(detail.admission_date)
    if from_date and admission_date and admission_date < from_date:
        return False
    return not (to_date and admission_date and admission_date > to_date)


def choose_latest_case_id(cases_cache: Sequence[tuple[EmzCaseDetail, object]]) -> int | None:
    latest_id: int | None = None
    latest_date: date | None = None
    for detail, _ in cases_cache:
        candidate_date = _extract_case_date(detail.admission_date or detail.outcome_date)
        if candidate_date and (latest_date is None or candidate_date > latest_date):
            latest_date = candidate_date
            latest_id = detail.id
        elif candidate_date is None and latest_date is None:
            if latest_id is None or detail.id > latest_id:
                latest_id = detail.id
    return latest_id

