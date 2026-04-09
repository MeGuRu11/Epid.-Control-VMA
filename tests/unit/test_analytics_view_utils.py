from __future__ import annotations

from datetime import UTC, date, datetime

from app.ui.analytics.view_utils import (
    build_top_microbe_chart_items,
    build_trend_chart_items,
    calculate_compare_window,
    format_analytics_datetime,
    format_day_label,
    normalize_date_range,
    quick_period_bounds,
)


def test_normalize_date_range_swaps_when_from_greater_than_to() -> None:
    left, right = normalize_date_range(date(2026, 2, 12), date(2026, 2, 1))
    assert left == date(2026, 2, 1)
    assert right == date(2026, 2, 12)


def test_calculate_compare_window_returns_current_and_previous_windows() -> None:
    current_from, current_to, prev_from, prev_to = calculate_compare_window(date(2026, 2, 12), 7)
    assert current_to == date(2026, 2, 12)
    assert current_from == date(2026, 2, 6)
    assert prev_to == date(2026, 2, 5)
    assert prev_from == date(2026, 1, 30)


def test_formatters_and_quick_period_bounds() -> None:
    assert format_analytics_datetime(datetime(2026, 2, 12, 14, 30, tzinfo=UTC)) == "12.02.2026 14:30"
    assert format_analytics_datetime(date(2026, 2, 12)) == "12.02.2026"
    assert format_analytics_datetime(None) == ""
    assert format_day_label(date(2026, 2, 12)) == "12.02.2026"
    assert format_day_label("2026-02-12") == "12.02.2026"
    assert format_day_label("x") == "x"

    date_from, date_to = quick_period_bounds("7d", date(2026, 2, 12))
    assert date_from == date(2026, 2, 6)
    assert date_to == date(2026, 2, 12)

    month_from, month_to = quick_period_bounds("month", date(2026, 2, 12))
    assert month_from == date(2026, 2, 1)
    assert month_to == date(2026, 2, 12)


def test_build_trend_chart_items_formats_real_dates_and_calculates_percentages() -> None:
    rows = [
        {"day": "2026-04-01", "total": 10, "positives": 5},
        {"day": "2026-04-03", "total": 4, "positives": 1},
    ]

    result = build_trend_chart_items(rows, date(2026, 4, 1), date(2026, 4, 3))

    assert result == [
        ("01.04.2026", 50.0),
        ("02.04.2026", 0.0),
        ("03.04.2026", 25.0),
    ]


def test_build_top_microbe_chart_items_calculates_percentage_share() -> None:
    items = [("ECO - E. coli", 3), ("SAU - S. aureus", 1)]

    result = build_top_microbe_chart_items(items, total_microbe_isolations=4)

    assert result == [("ECO - E. coli", 75.0), ("SAU - S. aureus", 25.0)]
