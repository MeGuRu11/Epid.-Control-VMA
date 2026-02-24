from __future__ import annotations

from datetime import UTC, datetime

_DIAGNOSIS_KIND_TO_DTO = {
    "поступление": "admission",
    "перевод": "discharge",
    "выписка": "discharge",
    "осложнение": "complication",
    "admission": "admission",
    "discharge": "discharge",
    "complication": "complication",
}

_DIAGNOSIS_KIND_TO_UI = {
    "admission": "Поступление",
    "discharge": "Выписка",
    "complication": "Осложнение",
}


def parse_datetime_text(text: str | None) -> datetime | None:
    if not text:
        return None
    value = text.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def format_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    dt = value.astimezone(UTC) if value.tzinfo else value
    return dt.strftime("%d.%m.%Y %H:%M")


def sex_code_to_label(sex_code: str | None) -> str:
    return {"M": "М", "F": "Ж"}.get(sex_code or "", "М")


def diagnosis_kind_to_dto(raw_kind: str) -> str:
    return _DIAGNOSIS_KIND_TO_DTO.get(raw_kind.strip().lower(), raw_kind.strip().lower())


def diagnosis_kind_to_ui(kind: str) -> str:
    return _DIAGNOSIS_KIND_TO_UI.get(kind, "Поступление")
