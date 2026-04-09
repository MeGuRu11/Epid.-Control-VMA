from __future__ import annotations

from collections.abc import Iterable, Mapping
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
    if isinstance(value, str):
        parsed = _coerce_chart_day(value)
        if parsed is not None:
            return parsed.strftime("%d.%m.%Y")
    return str(value)


def build_trend_chart_items(
    rows: Iterable[Mapping[str, object]],
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[tuple[str, float]]:
    day_map: dict[date, tuple[int, int]] = {}
    fallback_items: list[tuple[str, float]] = []

    for row in rows:
        raw_day = row.get("day")
        total = _coerce_chart_count(row.get("total"))
        positives = _coerce_chart_count(row.get("positives"))
        percentage = (positives / total * 100.0) if total else 0.0
        parsed_day = _coerce_chart_day(raw_day)
        if parsed_day is None:
            fallback_items.append((format_day_label(raw_day), percentage))
            continue
        day_map[parsed_day] = (total, positives)

    if date_from is not None and date_to is not None:
        start_date, end_date = normalize_date_range(date_from, date_to)
        if start_date is not None and end_date is not None:
            items: list[tuple[str, float]] = []
            current_day = start_date
            while current_day <= end_date:
                total, positives = day_map.get(current_day, (0, 0))
                percentage = (positives / total * 100.0) if total else 0.0
                items.append((format_day_label(current_day), percentage))
                current_day += timedelta(days=1)
            return items

    if day_map:
        items = []
        for current_day in sorted(day_map):
            total, positives = day_map[current_day]
            percentage = (positives / total * 100.0) if total else 0.0
            items.append((format_day_label(current_day), percentage))
        return items

    return fallback_items


def build_top_microbe_chart_items(
    items: Iterable[tuple[str, int]],
    *,
    total_microbe_isolations: int,
) -> list[tuple[str, float]]:
    denominator = max(total_microbe_isolations, 0)
    result: list[tuple[str, float]] = []
    for name, count in items:
        percentage = (count / denominator * 100.0) if denominator else 0.0
        result.append((name, percentage))
    return result


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
        date_to = today
    return date_from, date_to


def _coerce_chart_day(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
    return None


def _coerce_chart_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
