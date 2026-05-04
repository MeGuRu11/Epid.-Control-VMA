from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

AUTO_DAY_MAX_DAYS = 31
AUTO_WEEK_MAX_DAYS = 180


class TimeGrouping(StrEnum):
    AUTO = "auto"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class TimeSeriesPoint:
    date: date
    value: int | float


@dataclass(frozen=True)
class GroupedTimeSeries:
    labels: list[str]
    values: list[int | float]
    effective_grouping: TimeGrouping


@dataclass(frozen=True)
class TrendSeriesPoint:
    date: date
    total: int
    positives: int


@dataclass(frozen=True)
class GroupedTrendSeries:
    labels: list[str]
    values: list[float]
    effective_grouping: TimeGrouping


def coerce_time_grouping(value: object) -> TimeGrouping:
    if isinstance(value, TimeGrouping):
        return value
    if isinstance(value, str):
        try:
            return TimeGrouping(value)
        except ValueError:
            return TimeGrouping.AUTO
    return TimeGrouping.AUTO


def resolve_time_grouping(
    requested: TimeGrouping,
    start_date: date,
    end_date: date,
) -> TimeGrouping:
    if requested is not TimeGrouping.AUTO:
        return requested

    start_date, end_date = _normalize_period(start_date, end_date)
    period_days = (end_date - start_date).days + 1
    if period_days <= AUTO_DAY_MAX_DAYS:
        return TimeGrouping.DAY
    if period_days <= AUTO_WEEK_MAX_DAYS:
        return TimeGrouping.WEEK
    return TimeGrouping.MONTH


def group_time_series(
    points: Sequence[TimeSeriesPoint],
    requested: TimeGrouping,
    start_date: date,
    end_date: date,
) -> GroupedTimeSeries:
    effective_grouping = resolve_time_grouping(requested, start_date, end_date)
    if not points:
        return GroupedTimeSeries(labels=[], values=[], effective_grouping=effective_grouping)

    if effective_grouping is TimeGrouping.DAY:
        grouped_by_day: dict[date, int | float] = {}
        for point in points:
            grouped_by_day[point.date] = grouped_by_day.get(point.date, 0) + point.value
        ordered_days = sorted(grouped_by_day)
        return GroupedTimeSeries(
            labels=[_format_day_label(day) for day in ordered_days],
            values=[grouped_by_day[day] for day in ordered_days],
            effective_grouping=effective_grouping,
        )

    grouped: dict[tuple[int, int], int | float] = {}
    labels: dict[tuple[int, int], str] = {}
    for point in sorted(points, key=lambda item: item.date):
        key, label = _group_key_and_label(point.date, effective_grouping)
        grouped[key] = grouped.get(key, 0) + point.value
        labels[key] = label

    ordered_keys = sorted(grouped)
    return GroupedTimeSeries(
        labels=[labels[key] for key in ordered_keys],
        values=[grouped[key] for key in ordered_keys],
        effective_grouping=effective_grouping,
    )


def group_trend_rows(
    rows: Iterable[Mapping[str, object]],
    requested: TimeGrouping,
    date_from: date | None = None,
    date_to: date | None = None,
) -> GroupedTrendSeries:
    daily_points, fallback_items = _build_daily_trend_points(rows, date_from, date_to)
    start_date, end_date = _trend_period(daily_points, date_from, date_to)
    if start_date is None or end_date is None:
        return GroupedTrendSeries(
            labels=[label for label, _value in fallback_items],
            values=[value for _label, value in fallback_items],
            effective_grouping=TimeGrouping.DAY,
        )

    effective_grouping = resolve_time_grouping(requested, start_date, end_date)
    if not daily_points:
        return GroupedTrendSeries(labels=[], values=[], effective_grouping=effective_grouping)

    if effective_grouping is TimeGrouping.DAY:
        grouped_by_day: dict[date, tuple[int, int]] = {}
        for point in daily_points:
            total, positives = grouped_by_day.get(point.date, (0, 0))
            grouped_by_day[point.date] = (total + point.total, positives + point.positives)
        ordered_days = sorted(grouped_by_day)
        return GroupedTrendSeries(
            labels=[_format_day_label(day) for day in ordered_days],
            values=[_positive_share(*grouped_by_day[day]) for day in ordered_days],
            effective_grouping=effective_grouping,
        )

    grouped: dict[tuple[int, int], tuple[int, int]] = {}
    labels: dict[tuple[int, int], str] = {}
    for point in sorted(daily_points, key=lambda item: item.date):
        key, label = _group_key_and_label(point.date, effective_grouping)
        total, positives = grouped.get(key, (0, 0))
        grouped[key] = (total + point.total, positives + point.positives)
        labels[key] = label

    ordered_keys = sorted(grouped)
    return GroupedTrendSeries(
        labels=[labels[key] for key in ordered_keys],
        values=[_positive_share(*grouped[key]) for key in ordered_keys],
        effective_grouping=effective_grouping,
    )


def _build_daily_trend_points(
    rows: Iterable[Mapping[str, object]],
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[TrendSeriesPoint], list[tuple[str, float]]]:
    day_map: dict[date, tuple[int, int]] = {}
    fallback_items: list[tuple[str, float]] = []

    for row in rows:
        raw_day = row.get("day")
        total = _coerce_chart_count(row.get("total"))
        positives = _coerce_chart_count(row.get("positives"))
        parsed_day = _coerce_chart_day(raw_day)
        if parsed_day is None:
            fallback_items.append((_format_any_day_label(raw_day), _positive_share(total, positives)))
            continue
        current_total, current_positives = day_map.get(parsed_day, (0, 0))
        day_map[parsed_day] = (current_total + total, current_positives + positives)

    if date_from is not None and date_to is not None:
        start_date, end_date = _normalize_period(date_from, date_to)
        points: list[TrendSeriesPoint] = []
        current_day = start_date
        while current_day <= end_date:
            total, positives = day_map.get(current_day, (0, 0))
            points.append(TrendSeriesPoint(date=current_day, total=total, positives=positives))
            current_day += timedelta(days=1)
        return points, fallback_items

    points = [
        TrendSeriesPoint(date=current_day, total=total, positives=positives)
        for current_day, (total, positives) in sorted(day_map.items())
    ]
    return points, fallback_items


def _trend_period(
    points: Sequence[TrendSeriesPoint],
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None]:
    if date_from is not None and date_to is not None:
        return _normalize_period(date_from, date_to)
    if not points:
        return None, None
    dates = [point.date for point in points]
    return min(dates), max(dates)


def _group_key_and_label(value: date, grouping: TimeGrouping) -> tuple[tuple[int, int], str]:
    if grouping is TimeGrouping.MONTH:
        return (value.year, value.month), f"{value.month:02d}.{value.year}"

    iso_year, iso_week, _weekday = value.isocalendar()
    return (iso_year, iso_week), f"{iso_year}-W{iso_week:02d}"


def _normalize_period(start_date: date, end_date: date) -> tuple[date, date]:
    if start_date > end_date:
        return end_date, start_date
    return start_date, end_date


def _format_day_label(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _format_any_day_label(value: object) -> str:
    parsed = _coerce_chart_day(value)
    if parsed is not None:
        return _format_day_label(parsed)
    return str(value)


def _positive_share(total: int, positives: int) -> float:
    return positives / total * 100.0 if total else 0.0


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
