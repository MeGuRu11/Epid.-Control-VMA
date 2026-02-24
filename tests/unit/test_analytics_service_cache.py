from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from typing import Any, cast

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services.analytics_service import AnalyticsService


def make_session_factory() -> Callable[[], AbstractContextManager[object]]:
    @contextmanager
    def _session_scope() -> Iterator[object]:
        yield object()

    return _session_scope


class FakeRepo:
    def __init__(self) -> None:
        self.aggregate_calls = 0
        self.aggregate_count_calls = 0
        self.ismp_calls = 0

    def get_aggregates(self, _session: object, **_kwargs) -> dict:
        self.aggregate_calls += 1
        return {
            "total": 5,
            "positives": 2,
            "positive_share": 0.4,
            "top_microbes": [("ECO - E. coli", 2)],
        }

    def get_aggregate_counts(
        self,
        _session: object,
        _date_from: date,
        _date_to: date,
        *,
        patient_category: str | None,
    ) -> dict:
        self.aggregate_count_calls += 1
        if patient_category:
            return {"total": 4, "positives": 1, "positive_share": 0.25}
        return {"total": 6, "positives": 3, "positive_share": 0.5}

    def get_ismp_metrics(
        self,
        _session: object,
        _date_from: date | None,
        _date_to: date | None,
        _department_id: int | None,
    ) -> dict:
        self.ismp_calls += 1
        return {
            "total_cases": 10,
            "total_patient_days": 200,
            "ismp_total": 4,
            "ismp_cases": 3,
            "by_type": [{"type": "ВАП", "count": 3}],
        }


def test_get_aggregates_uses_cache_and_returns_copy() -> None:
    repo = FakeRepo()
    now = [100.0]

    def _clock() -> float:
        return now[0]

    service = AnalyticsService(
        repo=cast(Any, repo),
        session_factory=make_session_factory(),
        cache_ttl_seconds=60.0,
        clock=_clock,
    )
    req = AnalyticsSearchRequest(growth_flag=1)

    first = service.get_aggregates(req)
    first["total"] = 999
    second = service.get_aggregates(req)

    assert repo.aggregate_calls == 1
    assert second["total"] == 5


def test_get_aggregates_cache_expires_by_ttl() -> None:
    repo = FakeRepo()
    now = [0.0]

    def _clock() -> float:
        return now[0]

    service = AnalyticsService(
        repo=cast(Any, repo),
        session_factory=make_session_factory(),
        cache_ttl_seconds=10.0,
        clock=_clock,
    )
    req = AnalyticsSearchRequest(patient_category="service")

    service.get_aggregates(req)
    now[0] = 9.0
    service.get_aggregates(req)
    now[0] = 11.0
    service.get_aggregates(req)

    assert repo.aggregate_calls == 2


def test_compare_periods_uses_cache() -> None:
    repo = FakeRepo()
    now = [10.0]

    def _clock() -> float:
        return now[0]

    service = AnalyticsService(
        repo=cast(Any, repo),
        session_factory=make_session_factory(),
        cache_ttl_seconds=60.0,
        clock=_clock,
    )
    first = service.compare_periods(
        current_from=date(2026, 1, 1),
        current_to=date(2026, 1, 31),
        prev_from=date(2025, 12, 1),
        prev_to=date(2025, 12, 31),
        patient_category="service",
    )
    second = service.compare_periods(
        current_from=date(2026, 1, 1),
        current_to=date(2026, 1, 31),
        prev_from=date(2025, 12, 1),
        prev_to=date(2025, 12, 31),
        patient_category="service",
    )

    assert first == second
    assert repo.aggregate_count_calls == 2


def test_ismp_metrics_uses_cache() -> None:
    repo = FakeRepo()
    now = [50.0]

    def _clock() -> float:
        return now[0]

    service = AnalyticsService(
        repo=cast(Any, repo),
        session_factory=make_session_factory(),
        cache_ttl_seconds=60.0,
        clock=_clock,
    )

    first = service.get_ismp_metrics(date(2026, 1, 1), date(2026, 1, 31), department_id=1)
    second = service.get_ismp_metrics(date(2026, 1, 1), date(2026, 1, 31), department_id=1)

    assert first["ismp_cases"] == 3
    assert second["ismp_cases"] == 3
    assert repo.ismp_calls == 1
