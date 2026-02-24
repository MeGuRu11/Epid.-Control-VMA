from __future__ import annotations

from collections.abc import Iterable
from operator import attrgetter
from typing import Any


def parse_optional_int(text: str | None, field_label: str) -> int | None:
    if text is None:
        return None
    value = text.strip()
    if not value:
        return None
    if not value.isdigit():
        raise ValueError(f"Поле '{field_label}' должно быть числом")
    return int(value)


def normalize_sex_label(label: str) -> str:
    return "M" if label == "М" else "F"


def resolve_department_id(
    *,
    selected_id: int | None,
    selected_name: str,
    departments: Iterable[Any],
) -> int | None:
    if selected_id is not None:
        return selected_id
    name = selected_name.strip()
    if not name or name == "Выбрать":
        return None
    for department in departments:
        if str(attrgetter("name")(department)).strip() == name:
            return int(attrgetter("id")(department))
    return None
