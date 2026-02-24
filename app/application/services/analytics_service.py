from __future__ import annotations

import copy
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.application.dto.analytics_dto import AnalyticsSampleRow, AnalyticsSearchRequest
from app.infrastructure.db.repositories.analytics_repo import AnalyticsRepository
from app.infrastructure.db.session import session_scope


@dataclass
class _CacheEntry:
    created_at: float
    value: Any


class AnalyticsService:
    def __init__(
        self,
        repo: AnalyticsRepository | None = None,
        session_factory: Callable = session_scope,
        cache_ttl_seconds: float = 60.0,
        cache_max_entries: int = 256,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.repo = repo or AnalyticsRepository()
        self.session_factory = session_factory
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_max_entries = cache_max_entries
        self._clock = clock
        self._cache: dict[str, _CacheEntry] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def _normalize_cache_value(self, value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(k): self._normalize_cache_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._normalize_cache_value(v) for v in value]
        return value

    def _make_cache_key(self, scope: str, payload: dict[str, Any]) -> str:
        normalized = self._normalize_cache_value(payload)
        return (
            f"{scope}:"
            f"{json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        )

    def _cache_get(self, key: str) -> Any | None:
        if self.cache_ttl_seconds <= 0:
            return None
        entry = self._cache.get(key)
        if entry is None:
            return None
        if self._clock() - entry.created_at > self.cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return copy.deepcopy(entry.value)

    def _cache_set(self, key: str, value: Any) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        self._cache[key] = _CacheEntry(created_at=self._clock(), value=copy.deepcopy(value))
        self._prune_cache()

    def _prune_cache(self) -> None:
        if self.cache_ttl_seconds > 0:
            now = self._clock()
            expired = [
                key
                for key, entry in self._cache.items()
                if now - entry.created_at > self.cache_ttl_seconds
            ]
            for key in expired:
                self._cache.pop(key, None)

        if len(self._cache) <= self.cache_max_entries:
            return
        oldest_keys = sorted(self._cache.keys(), key=lambda key: self._cache[key].created_at)
        overflow = len(self._cache) - self.cache_max_entries
        for key in oldest_keys[:overflow]:
            self._cache.pop(key, None)

    def _cached_call(self, scope: str, payload: dict[str, Any], loader: Callable[[], Any]) -> Any:
        key = self._make_cache_key(scope, payload)
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        value = loader()
        self._cache_set(key, value)
        return copy.deepcopy(value)

    def search_samples(self, request: AnalyticsSearchRequest) -> list[AnalyticsSampleRow]:
        with self.session_factory() as session:
            rows = self.repo.search_samples(
                session,
                date_from=request.date_from,
                date_to=request.date_to,
                department_id=request.department_id,
                icd10_code=request.icd10_code,
                microorganism_id=request.microorganism_id,
                antibiotic_id=request.antibiotic_id,
                material_type_id=request.material_type_id,
                growth_flag=request.growth_flag,
                patient_category=request.patient_category,
                patient_name=request.patient_name,
                lab_no=request.lab_no,
                search_text=request.search_text,
            )

            result_map: dict[int, AnalyticsSampleRow] = {}
            for sample, patient, _case, dept, material, micro, abx in rows:
                if sample.id not in result_map:
                    result_map[sample.id] = AnalyticsSampleRow(
                        lab_sample_id=sample.id,
                        lab_no=sample.lab_no,
                        patient_name=patient.full_name,
                        patient_category=patient.category,
                        taken_at=sample.taken_at.isoformat() if sample.taken_at else None,
                        department_name=dept.name if dept else None,
                        material_type=f"{material.code} - {material.name}" if material else None,
                        microorganism=None,
                        antibiotic=None,
                        growth_flag=sample.growth_flag,
                    )
                row = result_map[sample.id]
                if micro and not row.microorganism:
                    if isinstance(micro, str):
                        row.microorganism = micro
                    else:
                        row.microorganism = f"{micro.code or '-'} - {micro.name}"
                if abx and not row.antibiotic:
                    if isinstance(abx, str):
                        row.antibiotic = abx
                    else:
                        row.antibiotic = f"{abx.code} - {abx.name}"

            return list(result_map.values())

    def get_aggregates_from_rows(self, rows: list[tuple]) -> dict:
        sample_flags: dict[int, int | None] = {}
        micro_counts: dict[str, int] = {}
        for sample, _patient, _case, _dept, _material, micro, _abx in rows:
            if sample.id not in sample_flags:
                sample_flags[sample.id] = sample.growth_flag
            if micro:
                label = f"{micro.code or '-'} - {micro.name}"
                micro_counts[label] = micro_counts.get(label, 0) + 1

        total = len(sample_flags)
        positives = sum(1 for v in sample_flags.values() if v == 1)
        share = (positives / total) if total else 0.0
        top_microbes = sorted(micro_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

        return {
            "total": total,
            "positives": positives,
            "positive_share": share,
            "top_microbes": top_microbes,
        }

    def get_aggregates(self, request: AnalyticsSearchRequest) -> dict:
        payload = request.model_dump(mode="json", exclude_none=True)

        def _load() -> dict:
            with self.session_factory() as session:
                return self.repo.get_aggregates(
                    session,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    department_id=request.department_id,
                    icd10_code=request.icd10_code,
                    microorganism_id=request.microorganism_id,
                    antibiotic_id=request.antibiotic_id,
                    material_type_id=request.material_type_id,
                    growth_flag=request.growth_flag,
                    patient_category=request.patient_category,
                    patient_name=request.patient_name,
                    lab_no=request.lab_no,
                    search_text=request.search_text,
                )

        return self._cached_call("get_aggregates", payload, _load)

    def get_department_summary(
        self, date_from: date | None, date_to: date | None, patient_category: str | None = None
    ) -> list[dict]:
        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "patient_category": patient_category,
        }

        def _load() -> list[dict]:
            with self.session_factory() as session:
                return self.repo.get_department_summary(
                    session, date_from, date_to, patient_category=patient_category
                )

        return self._cached_call("get_department_summary", payload, _load)

    def get_trend_by_day(
        self, date_from: date | None, date_to: date | None, patient_category: str | None = None
    ) -> list[dict]:
        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "patient_category": patient_category,
        }

        def _load() -> list[dict]:
            with self.session_factory() as session:
                return self.repo.get_trend_by_day(
                    session,
                    date_from,
                    date_to,
                    patient_category=patient_category,
                )

        return self._cached_call("get_trend_by_day", payload, _load)

    def compare_periods(
        self,
        current_from: date,
        current_to: date,
        prev_from: date,
        prev_to: date,
        patient_category: str | None = None,
    ) -> dict:
        payload = {
            "current_from": current_from,
            "current_to": current_to,
            "prev_from": prev_from,
            "prev_to": prev_to,
            "patient_category": patient_category,
        }

        def _load() -> dict:
            with self.session_factory() as session:
                current = self.repo.get_aggregate_counts(
                    session, current_from, current_to, patient_category=patient_category
                )
                previous = self.repo.get_aggregate_counts(
                    session, prev_from, prev_to, patient_category=patient_category
                )
                return {"current": current, "previous": previous}

        return self._cached_call("compare_periods", payload, _load)

    def get_ismp_metrics(
        self, date_from: date | None, date_to: date | None, department_id: int | None
    ) -> dict:
        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "department_id": department_id,
        }

        def _load() -> dict:
            with self.session_factory() as session:
                raw = self.repo.get_ismp_metrics(session, date_from, date_to, department_id)
                total_cases = raw["total_cases"]
                total_patient_days = raw["total_patient_days"]
                ismp_total = raw["ismp_total"]
                ismp_cases = raw["ismp_cases"]
                incidence = (ismp_cases / total_cases * 1000) if total_cases else 0.0
                incidence_density = (
                    (ismp_total / total_patient_days * 1000) if total_patient_days else 0.0
                )
                prevalence = (ismp_cases / total_cases * 100) if total_cases else 0.0
                return {
                    "total_cases": total_cases,
                    "total_patient_days": total_patient_days,
                    "ismp_total": ismp_total,
                    "ismp_cases": ismp_cases,
                    "incidence": incidence,
                    "incidence_density": incidence_density,
                    "prevalence": prevalence,
                    "by_type": raw["by_type"],
                }

        return self._cached_call("get_ismp_metrics", payload, _load)
