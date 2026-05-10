from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.reporting.formatters import (
    DASH,
    format_annotation_type,
    format_bool,
    format_date,
    format_datetime,
    format_growth_flag,
    format_outcome,
    format_percent,
    format_ris,
    format_sex,
    format_silhouette_short,
    localize_header,
    localize_headers,
    to_iso_utc,
)


def test_format_date_iso_string_to_ddmmyyyy() -> None:
    assert format_date("2026-05-10") == "10.05.2026"


def test_format_date_date_object_to_ddmmyyyy() -> None:
    assert format_date(date(2026, 5, 10)) == "10.05.2026"


def test_format_date_none_returns_dash() -> None:
    assert format_date(None) == DASH


def test_format_datetime_strips_microseconds() -> None:
    value = datetime(2026, 5, 10, 7, 14, 46, 206189, tzinfo=UTC)
    assert format_datetime(value) == "10.05.2026 07:14"


def test_format_datetime_none_returns_dash() -> None:
    assert format_datetime(None) == DASH


def test_format_bool_true_returns_da() -> None:
    assert format_bool(True) == "Да"
    assert format_bool(1) == "Да"


def test_format_bool_false_returns_net() -> None:
    assert format_bool(False) == "Нет"
    assert format_bool(0) == "Нет"


def test_format_bool_none_returns_dash() -> None:
    assert format_bool(None) == DASH


def test_format_percent_fraction_to_percent_string() -> None:
    assert format_percent(0.123) == "12.3%"


def test_format_percent_one_returns_100_0_percent() -> None:
    assert format_percent(1.0) == "100.0%"


def test_format_percent_none_returns_dash() -> None:
    assert format_percent(None) == DASH


def test_format_sex_m_returns_male() -> None:
    assert format_sex("M") == "Мужской"


def test_format_sex_f_returns_female() -> None:
    assert format_sex("F") == "Женский"


def test_format_sex_none_returns_dash() -> None:
    assert format_sex(None) == DASH


def test_format_outcome_discharge() -> None:
    assert format_outcome("discharge") == "Выписан"


def test_format_outcome_transfer() -> None:
    assert format_outcome("transfer") == "Перевод"


def test_format_outcome_death() -> None:
    assert format_outcome("death") == "Скончался"


def test_format_outcome_unknown_returns_dash() -> None:
    assert format_outcome("unknown") == DASH


def test_format_annotation_type_wound_x() -> None:
    assert format_annotation_type("WOUND_X") == "Рана"


def test_format_annotation_type_unknown_returns_dash() -> None:
    assert format_annotation_type("UNKNOWN") == DASH


def test_format_ris_s_r_i() -> None:
    assert format_ris("S") == "Чувствительный"
    assert format_ris("R") == "Резистентный"
    assert format_ris("I") == "Промежуточный"


def test_format_growth_flag_int_and_bool() -> None:
    assert format_growth_flag(1) == "Да"
    assert format_growth_flag(True) == "Да"
    assert format_growth_flag(0) == "Нет"
    assert format_growth_flag(False) == "Нет"
    assert format_growth_flag(None) == DASH


def test_localize_header_known_field() -> None:
    assert localize_header("full_name") == "ФИО"


def test_localize_header_unknown_field_returns_as_is() -> None:
    assert localize_header("custom_field") == "custom_field"


def test_localize_headers_list() -> None:
    assert localize_headers(["id", "full_name", "custom_field"]) == [
        "ID пациента",
        "ФИО",
        "custom_field",
    ]


def test_to_iso_utc_adds_utc_timezone_to_naive_datetime() -> None:
    value = datetime.fromisoformat("2026-05-10T07:14:46.206189")
    assert to_iso_utc(value) == "2026-05-10T07:14:46.206189+00:00"


def test_to_iso_utc_none_returns_none() -> None:
    assert to_iso_utc(None) is None


def test_format_silhouette_short_front() -> None:
    assert format_silhouette_short("male_front") == "Спереди"
    assert format_silhouette_short("female_front") == "Спереди"


def test_format_silhouette_short_back() -> None:
    assert format_silhouette_short("male_back") == "Сзади"
    assert format_silhouette_short("female_back") == "Сзади"


def test_format_silhouette_short_none() -> None:
    assert format_silhouette_short(None) == DASH
