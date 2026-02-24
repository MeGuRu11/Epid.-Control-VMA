from __future__ import annotations

from datetime import date, datetime, timedelta


def normalize_date_range(date_from: date | None, date_to: date | None) -> tuple[date | None, date | None]:
    if date_from and date_to and date_from > date_to:
        return date_to, date_from
    return date_from, date_to


def calculate_compare_window(end_date: date, days: int) -> tuple[date, date, date, date]:
    current_to = end_date
    current_from = current_to - timedelta(days=days - 1)
    prev_to = current_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=days - 1)
    return current_from, current_to, prev_from, prev_to


def format_analytics_datetime(value: date | datetime | None) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    return value.strftime("%d.%m.%Y")


def format_day_label(value: object) -> str:
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value)


def quick_period_bounds(mode: str | None, today: date) -> tuple[date, date]:
    date_from = today
    date_to = today
    if mode == "7d":
        date_from = today - timedelta(days=6)
    elif mode == "30d":
        date_from = today - timedelta(days=29)
    elif mode == "90d":
        date_from = today - timedelta(days=89)
    elif mode == "month":
        first_day = date(today.year, today.month, 1)
        date_from = first_day
        next_month = date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
        date_to = next_month - timedelta(days=1)
    return date_from, date_to
