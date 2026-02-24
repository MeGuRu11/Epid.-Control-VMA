from __future__ import annotations

from datetime import UTC, datetime

from app.ui.emz.form_case_selectors import pick_latest_case_id


def test_pick_latest_case_id_prefers_latest_admission_or_outcome() -> None:
    case_dates = [
        (1, datetime(2026, 1, 10, 10, 0, tzinfo=UTC), None),
        (2, datetime(2026, 1, 12, 8, 0, tzinfo=UTC), None),
        (3, None, datetime(2026, 1, 11, 9, 0, tzinfo=UTC)),
    ]
    assert pick_latest_case_id(case_dates) == 2


def test_pick_latest_case_id_falls_back_to_highest_id_when_no_dates() -> None:
    case_dates = [
        (1, None, None),
        (4, None, None),
        (2, None, None),
    ]
    assert pick_latest_case_id(case_dates) == 4


def test_pick_latest_case_id_returns_none_for_empty_input() -> None:
    assert pick_latest_case_id([]) is None
