from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationState(Generic[T]):
    page_items: list[T]
    page_index: int
    total_pages: int


@dataclass(frozen=True)
class HistorySummary:
    total: int
    positives: int
    last_taken_text: str


def matches_history_filters(
    sample: Any,
    *,
    search: str,
    growth: int | None,
    date_from: date | None,
    date_to: date | None,
) -> bool:
    if search and search not in (sample.lab_no or "").lower():
        return False
    if growth is not None and sample.growth_flag != growth:
        return False
    taken = sample.taken_at.date() if sample.taken_at else None
    if date_from and (taken is None or taken < date_from):
        return False
    return not (date_to and (taken is None or taken > date_to))


def filter_and_sort_samples(
    samples: list[Any],
    *,
    search: str,
    growth: int | None,
    date_from: date | None,
    date_to: date | None,
) -> list[Any]:
    filtered = [
        sample
        for sample in samples
        if matches_history_filters(
            sample,
            search=search,
            growth=growth,
            date_from=date_from,
            date_to=date_to,
        )
    ]
    return sorted(
        filtered,
        key=lambda sample: (sample.taken_at is None, sample.taken_at),
        reverse=True,
    )


def paginate_samples(items: list[T], *, page_index: int, page_size: int) -> PaginationState[T]:
    if page_size <= 0:
        page_size = 50
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    normalized_page = min(max(1, page_index), total_pages)
    start_idx = (normalized_page - 1) * page_size
    end_idx = min(start_idx + page_size, len(items))
    return PaginationState(
        page_items=items[start_idx:end_idx],
        page_index=normalized_page,
        total_pages=total_pages,
    )


def summarize_history(samples: list[Any]) -> HistorySummary:
    positives = sum(1 for sample in samples if sample.growth_flag == 1)
    last_dt = max((sample.taken_at for sample in samples if sample.taken_at), default=None)
    last_text = last_dt.strftime("%d.%m.%Y %H:%M") if last_dt else "-"
    return HistorySummary(total=len(samples), positives=positives, last_taken_text=last_text)


def growth_visuals(growth_flag: int | None) -> tuple[str, str]:
    if growth_flag == 1:
        return "#E18A85", "Да"
    if growth_flag == 0:
        return "#9AD8A6", "Нет"
    return "#F4D58D", "-"


def resolve_micro_text(sample: Any, *, microbe_map: dict[int, str]) -> str:
    if sample.microorganism_id:
        label = microbe_map.get(sample.microorganism_id, "")
        if label:
            return label
    return sample.microorganism_free or ""


def build_meta_line(sample: Any, *, growth_text: str, micro_text: str) -> str:
    taken_text = sample.taken_at.strftime("%d.%m.%Y %H:%M") if sample.taken_at else "-"
    micro_part = f" · Микроорганизм: {micro_text}" if micro_text else ""
    point_part = f" · Точка: {sample.sampling_point}" if sample.sampling_point else ""
    room_part = f" · Помещение: {sample.room}" if sample.room else ""
    medium_part = f" · Среда: {sample.medium}" if sample.medium else ""
    return f"Взято: {taken_text} · Рост: {growth_text}{micro_part}{point_part}{room_part}{medium_part}"
