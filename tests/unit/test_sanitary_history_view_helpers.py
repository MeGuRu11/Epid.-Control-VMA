from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.ui.sanitary.history_view_helpers import (
    build_meta_line,
    filter_and_sort_samples,
    growth_visuals,
    matches_history_filters,
    paginate_samples,
    resolve_micro_text,
    summarize_history,
)


@dataclass
class _Sample:
    id: int
    lab_no: str | None
    growth_flag: int | None
    taken_at: datetime | None
    microorganism_id: int | None
    microorganism_free: str | None
    sampling_point: str | None
    room: str | None
    medium: str | None


def _make_sample(
    *,
    sample_id: int,
    lab_no: str = "SAN-1",
    growth_flag: int | None = None,
    taken_at: datetime | None = None,
    microorganism_id: int | None = None,
    microorganism_free: str | None = None,
    sampling_point: str | None = None,
    room: str | None = None,
    medium: str | None = None,
) -> _Sample:
    return _Sample(
        id=sample_id,
        lab_no=lab_no,
        growth_flag=growth_flag,
        taken_at=taken_at,
        microorganism_id=microorganism_id,
        microorganism_free=microorganism_free,
        sampling_point=sampling_point,
        room=room,
        medium=medium,
    )


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def test_matches_history_filters_by_search_growth_and_dates() -> None:
    sample = _make_sample(
        sample_id=1,
        lab_no="SAN-777",
        growth_flag=1,
        taken_at=_dt(2026, 2, 10, 8, 30),
    )

    assert (
        matches_history_filters(
            sample,
            search="777",
            growth=1,
            date_from=_dt(2026, 2, 10, 0, 0).date(),
            date_to=_dt(2026, 2, 10, 23, 59).date(),
        )
        is True
    )
    assert (
        matches_history_filters(
            sample,
            search="miss",
            growth=1,
            date_from=None,
            date_to=None,
        )
        is False
    )


def test_filter_and_sort_samples_uses_expected_order() -> None:
    a = _make_sample(sample_id=1, lab_no="A", taken_at=_dt(2026, 2, 1, 10, 0))
    b = _make_sample(sample_id=2, lab_no="B", taken_at=None)
    c = _make_sample(sample_id=3, lab_no="C", taken_at=_dt(2026, 2, 2, 10, 0))

    result = filter_and_sort_samples(
        [a, b, c],
        search="",
        growth=None,
        date_from=None,
        date_to=None,
    )

    assert [sample.id for sample in result] == [2, 3, 1]


def test_paginate_samples_normalizes_page_and_returns_slice() -> None:
    page = paginate_samples([1, 2, 3, 4, 5], page_index=4, page_size=2)
    assert page.page_index == 3
    assert page.total_pages == 3
    assert page.page_items == [5]


def test_summarize_history_counts_positives_and_last_date() -> None:
    summary = summarize_history(
        [
            _make_sample(sample_id=1, growth_flag=1, taken_at=_dt(2026, 2, 1, 10, 0)),
            _make_sample(sample_id=2, growth_flag=0, taken_at=_dt(2026, 2, 3, 11, 30)),
            _make_sample(sample_id=3, growth_flag=1, taken_at=None),
        ]
    )

    assert summary.total == 3
    assert summary.positives == 2
    assert summary.last_taken_text == "03.02.2026 11:30"


def test_growth_visuals_for_all_states() -> None:
    assert growth_visuals(1) == ("#E18A85", "Да")
    assert growth_visuals(0) == ("#9AD8A6", "Нет")
    assert growth_visuals(None) == ("#F4D58D", "-")


def test_resolve_micro_text_prefers_reference_then_free_text() -> None:
    sample_ref = _make_sample(sample_id=1, microorganism_id=10, microorganism_free="free")
    sample_free = _make_sample(sample_id=2, microorganism_id=11, microorganism_free="free")

    assert resolve_micro_text(sample_ref, microbe_map={10: "A01 - Staph"}) == "A01 - Staph"
    assert resolve_micro_text(sample_free, microbe_map={}) == "free"


def test_build_meta_line_includes_optional_parts() -> None:
    sample = _make_sample(
        sample_id=1,
        taken_at=_dt(2026, 2, 10, 8, 30),
        sampling_point="Раковина",
        room="Палата 1",
        medium="Агар",
    )
    line = build_meta_line(sample, growth_text="Да", micro_text="A01 - Staph")
    assert line == (
        "Взято: 10.02.2026 08:30 · Рост: Да · Микроорганизм: A01 - Staph"
        " · Точка: Раковина · Помещение: Палата 1 · Среда: Агар"
    )
