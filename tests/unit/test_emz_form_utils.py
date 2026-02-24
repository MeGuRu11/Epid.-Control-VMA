from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.ui.emz.form_utils import (
    diagnosis_kind_to_dto,
    diagnosis_kind_to_ui,
    format_datetime,
    parse_datetime_text,
    sex_code_to_label,
)


def test_parse_datetime_text_supports_iso() -> None:
    parsed = parse_datetime_text("2025-12-31 10:15")
    expected = datetime(2025, 12, 31, 10, 15, tzinfo=UTC).replace(tzinfo=None)
    assert parsed == expected


def test_parse_datetime_text_supports_ru_format() -> None:
    parsed = parse_datetime_text("31.12.2025 10:15")
    assert parsed == datetime(2025, 12, 31, 10, 15, tzinfo=UTC)


def test_parse_datetime_text_invalid_returns_none() -> None:
    assert parse_datetime_text("31/12/2025") is None


def test_format_datetime_converts_to_utc_for_aware_values() -> None:
    dt_local = datetime(2025, 12, 31, 10, 15, tzinfo=timezone(timedelta(hours=3)))
    assert format_datetime(dt_local) == "31.12.2025 07:15"


def test_sex_code_to_label_defaults_to_male() -> None:
    assert sex_code_to_label(None) == "М"
    assert sex_code_to_label("X") == "М"


def test_sex_code_to_label_maps_known_values() -> None:
    assert sex_code_to_label("M") == "М"
    assert sex_code_to_label("F") == "Ж"


def test_diagnosis_kind_to_dto_maps_ru_values() -> None:
    assert diagnosis_kind_to_dto("Поступление") == "admission"
    assert diagnosis_kind_to_dto("Осложнение") == "complication"


def test_diagnosis_kind_to_ui_maps_dto_values() -> None:
    assert diagnosis_kind_to_ui("discharge") == "Выписка"
    assert diagnosis_kind_to_ui("unknown") == "Поступление"
