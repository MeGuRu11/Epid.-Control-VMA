from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta

from app.ui.analytics.chart_data import TimeGrouping, coerce_time_grouping, group_trend_rows


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
    grouping: TimeGrouping | str = TimeGrouping.DAY,
) -> list[tuple[str, float]]:
    grouped = group_trend_rows(
        rows,
        requested=coerce_time_grouping(grouping),
        date_from=date_from,
        date_to=date_to,
    )
    return list(zip(grouped.labels, grouped.values, strict=False))


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
