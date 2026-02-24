from __future__ import annotations

from datetime import date, datetime


def text_or_empty(value: str | None) -> str:
    return value or ""


def int_or_empty(value: int | None) -> str:
    return str(value) if value is not None else ""


def format_admission_label(value: date | datetime | None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return "не указана"


def format_save_message(
    *,
    patient_name: str,
    hospital_case_no: str,
    admission_value: date | datetime | None,
) -> str:
    name = patient_name.strip() or "Пациент"
    case_no = hospital_case_no.strip() or "—"
    admission_text = format_admission_label(admission_value)
    return f"ЭМЗ сохранена: {name}, госпитализация №{case_no}, дата поступления {admission_text}."


def split_date_or_datetime(value: date | datetime | None) -> tuple[datetime | None, date | None]:
    if isinstance(value, datetime):
        return value, None
    if isinstance(value, date):
        return None, value
    return None, None
