from __future__ import annotations

from datetime import date, datetime


def ensure_date_order(start: date | datetime | None, end: date | datetime | None, field: str) -> None:
    if start is None or end is None:
        return
    if start > end:
        raise ValueError(f"{field}: дата начала позже даты окончания")


def normalize_required_text(value: str | None, default: str = "н/д") -> str:
    text = (value or "").strip()
    return text or default

