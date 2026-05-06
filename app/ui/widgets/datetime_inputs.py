from __future__ import annotations

from datetime import date, datetime
from typing import cast

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QDateEdit, QDateTimeEdit, QWidget

DATE_DISPLAY_FORMAT = "dd.MM.yyyy"
DATETIME_DISPLAY_FORMAT = "dd.MM.yyyy HH:mm"
DEFAULT_EMPTY_DATE = QDate(2024, 1, 1)
DEFAULT_EMPTY_DATETIME = QDateTime(DEFAULT_EMPTY_DATE, QTime(0, 0))


def configure_optional_datetime_edit(
    widget: QDateTimeEdit,
    *,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
) -> QDateTimeEdit:
    """Настраивает date-time поле без скрытого текущего времени по умолчанию."""
    widget.setCalendarPopup(True)
    widget.setDisplayFormat(DATETIME_DISPLAY_FORMAT)
    widget.setKeyboardTracking(True)
    widget.setMinimumDateTime(empty_datetime)
    widget.setSpecialValueText("")
    widget.setDateTime(empty_datetime)
    widget.setCurrentSection(QDateTimeEdit.Section.DaySection)
    return widget


def create_optional_datetime_edit(
    *,
    parent: QWidget | None = None,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
) -> QDateTimeEdit:
    """Создает опциональный QDateTimeEdit с редактируемыми датой и временем."""
    return configure_optional_datetime_edit(QDateTimeEdit(parent), empty_datetime=empty_datetime)


def configure_optional_date_edit(
    widget: QDateEdit,
    *,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> QDateEdit:
    """Настраивает date-only поле без преобразования в скрытый datetime."""
    widget.setCalendarPopup(True)
    widget.setDisplayFormat(DATE_DISPLAY_FORMAT)
    widget.setMinimumDate(empty_date)
    widget.setSpecialValueText("")
    widget.setDate(empty_date)
    widget.setCurrentSection(QDateEdit.Section.DaySection)
    return widget


def create_optional_date_edit(
    *,
    parent: QWidget | None = None,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> QDateEdit:
    """Создает опциональный QDateEdit для date-only значений."""
    return configure_optional_date_edit(QDateEdit(parent), empty_date=empty_date)


def to_qdate(value: date) -> QDate:
    """Преобразует Python date в QDate без добавления времени."""
    return QDate(value.year, value.month, value.day)


def to_qdatetime(value: datetime) -> QDateTime:
    """Преобразует Python datetime в QDateTime с сохранением часов и минут."""
    return QDateTime(to_qdate(value.date()), QTime(value.hour, value.minute, value.second))


def optional_date_value(
    widget: QDateEdit,
    *,
    empty_date: QDate = DEFAULT_EMPTY_DATE,
) -> date | None:
    """Возвращает date или None, если поле осталось на empty sentinel."""
    qdate = widget.date()
    if not qdate.isValid() or qdate == empty_date:
        return None
    return cast(date, qdate.toPython())


def optional_datetime_value(
    widget: QDateTimeEdit,
    *,
    empty_datetime: QDateTime = DEFAULT_EMPTY_DATETIME,
) -> datetime | None:
    """Возвращает datetime или None, если поле осталось на empty sentinel."""
    qdt = widget.dateTime()
    if not qdt.isValid() or qdt == empty_datetime:
        return None
    return cast(datetime, qdt.toPython())
