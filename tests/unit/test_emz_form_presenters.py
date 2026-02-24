from __future__ import annotations

from datetime import UTC, date, datetime

from app.ui.emz.form_presenters import (
    format_admission_label,
    format_save_message,
    int_or_empty,
    split_date_or_datetime,
    text_or_empty,
)


def test_text_or_empty() -> None:
    assert text_or_empty(None) == ""
    assert text_or_empty("abc") == "abc"


def test_int_or_empty() -> None:
    assert int_or_empty(None) == ""
    assert int_or_empty(7) == "7"


def test_format_admission_label_for_datetime() -> None:
    value = datetime(2025, 1, 2, 13, 45, tzinfo=UTC)
    assert format_admission_label(value) == "02.01.2025 13:45"


def test_format_admission_label_for_date_and_none() -> None:
    assert format_admission_label(date(2025, 1, 2)) == "02.01.2025"
    assert format_admission_label(None) == "не указана"


def test_format_save_message() -> None:
    message = format_save_message(
        patient_name="Иван Иванов",
        hospital_case_no="A-1",
        admission_value=date(2025, 1, 2),
    )
    assert "Иван Иванов" in message
    assert "№A-1" in message
    assert "02.01.2025" in message


def test_split_date_or_datetime() -> None:
    dt = datetime(2025, 1, 2, 13, 45, tzinfo=UTC)
    dt_value, date_value = split_date_or_datetime(dt)
    assert dt_value == dt
    assert date_value is None

    dt_value, date_value = split_date_or_datetime(date(2025, 1, 2))
    assert dt_value is None
    assert date_value == date(2025, 1, 2)

    dt_value, date_value = split_date_or_datetime(None)
    assert dt_value is None
    assert date_value is None
