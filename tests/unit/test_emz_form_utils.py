from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.ui.emz.form_utils import (
    diagnosis_kind_to_dto,
    diagnosis_kind_to_ui,
    format_datetime,
    outcome_label_to_type,
    outcome_type_to_label,
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


def test_outcome_type_to_label_maps_stable_codes() -> None:
    assert outcome_type_to_label("discharge") == "Выписка"
    assert outcome_type_to_label("transfer") == "Перевод"
    assert outcome_type_to_label("death") == "Летальный исход"
    assert outcome_type_to_label(None) == ""
    assert outcome_type_to_label("unknown") == ""


def test_outcome_label_to_type_maps_ui_labels_without_placeholder() -> None:
    assert outcome_label_to_type("Выписка") == "discharge"
    assert outcome_label_to_type("Перевод") == "transfer"
    assert outcome_label_to_type("Летальный исход") == "death"
    assert outcome_label_to_type("Не выбран") is None
    assert outcome_label_to_type("") is None
