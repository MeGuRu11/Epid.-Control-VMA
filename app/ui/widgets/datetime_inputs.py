"""Shared factories for optional QDateEdit/QDateTimeEdit widgets."""

from __future__ import annotations

from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QDateEdit, QDateTimeEdit, QWidget

DATE_DISPLAY_FORMAT = "dd.MM.yyyy"
DATETIME_DISPLAY_FORMAT = "dd.MM.yyyy HH:mm"

DEFAULT_EMPTY_DATE = QDate(1900, 1, 1)
DEFAULT_EMPTY_DATETIME = QDateTime(DEFAULT_EMPTY_DATE, QTime(0, 0))

DEFAULT_MAX_DATE = QDate(2100, 12, 31)
DEFAULT_MAX_DATETIME = QDateTime(DEFAULT_MAX_DATE, QTime(23, 59, 59))

IS_EMPTY_PROPERTY = "isEmpty"


def _refresh_style(widget: QWidget) -> None:
    style = widget.style()
    if style is None:
        return
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _set_empty_property(widget: QDateEdit | QDateTimeEdit, value: bool) -> None:
    widget.setProperty(IS_EMPTY_PROPERTY, value)
    _refresh_style(widget)


def _wire_empty_indicator_date(widget: QDateEdit, sentinel: QDate) -> None:
    def _on_changed(new_value: QDate, w: QDateEdit = widget, s: QDate = sentinel) -> None:
        _set_empty_property(w, new_value == s)

    widget.dateChanged.connect(_on_changed)
    _set_empty_property(widget, widget.date() == sentinel)


def _wire_empty_indicator_datetime(widget: QDateTimeEdit, sentinel: QDateTime) -> None:
    def _on_changed(new_value: QDateTime, w: QDateTimeEdit = widget, s: QDateTime = sentinel) -> None:
        _set_empty_property(w, new_value == s)

    widget.dateTimeChanged.connect(_on_changed)
    _set_empty_property(widget, widget.dateTime() == sentinel)


def configure_optional_date_edit(
    widget: QDateEdit,
    *,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
    minimum_date: QDate | None = None,
    maximum_date: QDate = DEFAULT_MAX_DATE,
) -> QDateEdit:
    """Configure a date-only optional field with 1900-01-01 as the empty sentinel."""
    min_date = minimum_date if minimum_date is not None else empty_date
    widget.setCalendarPopup(True)
    widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
    widget.setKeyboardTracking(False)
    widget.setMinimumDate(min_date)
    widget.setMaximumDate(maximum_date)
    widget.setDate(empty_date)
    widget.setCurrentSection(QDateEdit.Section.DaySection)
    _wire_empty_indicator_date(widget, empty_date)
    return widget


def create_optional_date_edit(
    *,
    parent: QWidget | None = None,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
    minimum_date: QDate | None = None,
    maximum_date: QDate = DEFAULT_MAX_DATE,
) -> QDateEdit:
    """Create an optional QDateEdit with default range 1900-01-01..2100-12-31."""
    return configure_optional_date_edit(
        QDateEdit(parent),
        empty_date=empty_date,
        minimum_date=minimum_date,
        maximum_date=maximum_date,
    )


def configure_birth_date_edit(
    widget: QDateEdit,
    *,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> QDateEdit:
    """Configure a birth-date field with range 1900-01-01..today."""
    return configure_optional_date_edit(
        widget,
        empty_date=empty_date,
        minimum_date=empty_date,
        maximum_date=QDate.currentDate(),
    )


def create_birth_date_edit(
    *,
    parent: QWidget | None = None,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> QDateEdit:
    """Create a birth-date QDateEdit with range 1900-01-01..today."""
    return configure_birth_date_edit(QDateEdit(parent), empty_date=empty_date)


def configure_optional_datetime_edit(
    widget: QDateTimeEdit,
    *,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
    minimum_datetime: QDateTime | None = None,
    maximum_datetime: QDateTime = DEFAULT_MAX_DATETIME,
) -> QDateTimeEdit:
    """Configure an optional date-time field with 1900-01-01 00:00 as sentinel."""
    min_dt = minimum_datetime if minimum_datetime is not None else empty_datetime
    widget.setCalendarPopup(True)
    widget.setDisplayFormat(DATETIME_DISPLAY_FORMAT)
    widget.setKeyboardTracking(False)
    widget.setMinimumDateTime(min_dt)
    widget.setMaximumDateTime(maximum_datetime)
    widget.setDateTime(empty_datetime)
    widget.setCurrentSection(QDateTimeEdit.Section.DaySection)
    _wire_empty_indicator_datetime(widget, empty_datetime)
    return widget


def create_optional_datetime_edit(
    *,
    parent: QWidget | None = None,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
    minimum_datetime: QDateTime | None = None,
    maximum_datetime: QDateTime = DEFAULT_MAX_DATETIME,
) -> QDateTimeEdit:
    """Create an optional QDateTimeEdit with default range 1900..2100."""
    return configure_optional_datetime_edit(
        QDateTimeEdit(parent),
        empty_datetime=empty_datetime,
        minimum_datetime=minimum_datetime,
        maximum_datetime=maximum_datetime,
    )


def to_qdate(value: date) -> QDate:
    """Convert Python date to QDate."""
    return QDate(value.year, value.month, value.day)


def to_qdatetime(value: datetime) -> QDateTime:
    """Convert Python datetime to QDateTime while preserving time."""
    return QDateTime(to_qdate(value.date()), QTime(value.hour, value.minute, value.second))


def optional_date_value(
    widget: QDateEdit,
    *,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> date | None:
    """Return None when the widget is still at the empty sentinel."""
    qdate = widget.date()
    if not qdate.isValid() or qdate == empty_date:
        return None
    return cast(date, qdate.toPython())


def optional_datetime_value(
    widget: QDateTimeEdit,
    *,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
) -> datetime | None:
    """Return None when the widget is still at the empty sentinel."""
    qdt = widget.dateTime()
    if not qdt.isValid() or qdt == empty_datetime:
        return None
    return cast(datetime, qdt.toPython())
