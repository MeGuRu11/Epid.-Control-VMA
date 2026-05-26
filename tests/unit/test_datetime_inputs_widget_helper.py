"""Regressions for optional date/date-time widget factories."""

from __future__ import annotations

from datetime import date as py_date, datetime as py_datetime

from PySide6.QtCore import QDate, QDateTime, QTime

from app.ui.widgets.datetime_inputs import (
    DEFAULT_EMPTY_DATE,
    DEFAULT_EMPTY_DATETIME,
    DEFAULT_MAX_DATE,
    DEFAULT_MAX_DATETIME,
    IS_EMPTY_PROPERTY,
    create_birth_date_edit,
    create_optional_date_edit,
    create_optional_datetime_edit,
    optional_date_value,
    optional_datetime_value,
)


def test_default_empty_date_is_1900_not_2024() -> None:
    assert QDate(1900, 1, 1) == DEFAULT_EMPTY_DATE
    assert QDateTime(QDate(1900, 1, 1), QTime(0, 0)) == DEFAULT_EMPTY_DATETIME


def test_default_max_date_is_2100() -> None:
    assert QDate(2100, 12, 31) == DEFAULT_MAX_DATE
    assert QDateTime(QDate(2100, 12, 31), QTime(23, 59, 59)) == DEFAULT_MAX_DATETIME


def test_optional_date_edit_minimum_is_1900(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.minimumDate() == QDate(1900, 1, 1)
    finally:
        widget.deleteLater()


def test_optional_date_edit_maximum_is_2100(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.maximumDate() == QDate(2100, 12, 31)
    finally:
        widget.deleteLater()


def test_optional_date_edit_does_not_set_special_value_text(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.specialValueText() == ""
        assert widget.text() == "01.01.1900"
    finally:
        widget.deleteLater()


def test_optional_date_edit_starts_empty_with_is_empty_property(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.date() == DEFAULT_EMPTY_DATE
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        widget.deleteLater()


def test_optional_date_edit_is_empty_property_clears_on_user_value(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        widget.setDate(QDate(2020, 5, 26))
        assert widget.property(IS_EMPTY_PROPERTY) is False
    finally:
        widget.deleteLater()


def test_optional_date_edit_is_empty_property_restores_on_sentinel(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        widget.setDate(QDate(2020, 5, 26))
        assert widget.property(IS_EMPTY_PROPERTY) is False
        widget.setDate(DEFAULT_EMPTY_DATE)
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        widget.deleteLater()


def test_optional_date_edit_accepts_year_below_2000(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        widget.setDate(QDate(1985, 3, 15))
        assert widget.date() == QDate(1985, 3, 15)
    finally:
        widget.deleteLater()


def test_birth_date_edit_minimum_is_1900(qapp) -> None:
    widget = create_birth_date_edit()
    try:
        assert widget.minimumDate() == QDate(1900, 1, 1)
    finally:
        widget.deleteLater()


def test_birth_date_edit_maximum_is_today(qapp) -> None:
    widget = create_birth_date_edit()
    try:
        assert widget.maximumDate() == QDate.currentDate()
    finally:
        widget.deleteLater()


def test_birth_date_edit_accepts_old_birth_year(qapp) -> None:
    widget = create_birth_date_edit()
    try:
        widget.setDate(QDate(1950, 6, 12))
        assert widget.date() == QDate(1950, 6, 12)
    finally:
        widget.deleteLater()


def test_optional_datetime_edit_minimum_is_1900(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert widget.minimumDateTime() == DEFAULT_EMPTY_DATETIME
    finally:
        widget.deleteLater()


def test_optional_datetime_edit_maximum_is_2100(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert widget.maximumDateTime() == DEFAULT_MAX_DATETIME
    finally:
        widget.deleteLater()


def test_optional_datetime_edit_starts_empty(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert widget.dateTime() == DEFAULT_EMPTY_DATETIME
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        widget.deleteLater()


def test_optional_date_value_returns_none_when_sentinel(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert optional_date_value(widget) is None
    finally:
        widget.deleteLater()


def test_optional_date_value_returns_date_when_set(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        widget.setDate(QDate(2025, 8, 15))
        assert optional_date_value(widget) == py_date(2025, 8, 15)
    finally:
        widget.deleteLater()


def test_optional_datetime_value_returns_none_when_sentinel(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert optional_datetime_value(widget) is None
    finally:
        widget.deleteLater()


def test_optional_datetime_value_returns_datetime_when_set(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2025, 8, 15), QTime(14, 30)))
        assert optional_datetime_value(widget) == py_datetime.fromisoformat("2025-08-15T14:30:00")
    finally:
        widget.deleteLater()
