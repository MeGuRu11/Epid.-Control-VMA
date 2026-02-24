from __future__ import annotations

from datetime import UTC, date, datetime

from app.ui.analytics.view_utils import (
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
    assert format_day_label("x") == "x"

    date_from, date_to = quick_period_bounds("7d", date(2026, 2, 12))
    assert date_from == date(2026, 2, 6)
    assert date_to == date(2026, 2, 12)

    month_from, month_to = quick_period_bounds("month", date(2026, 2, 12))
    assert month_from == date(2026, 2, 1)
    assert month_to == date(2026, 2, 28)
