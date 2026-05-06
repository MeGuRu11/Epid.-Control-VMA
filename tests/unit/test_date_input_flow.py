from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, QTime

from app.ui.widgets.date_input_flow import DateInputAutoFlow
from app.ui.widgets.datetime_inputs import (
    DATETIME_DISPLAY_FORMAT,
    DEFAULT_EMPTY_DATETIME,
    create_optional_datetime_edit,
)


class _FakeEditor:
    def __init__(self) -> None:
        self.text = ""
        self.cursor = -1

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = value

    def setCursorPosition(self, value: int) -> None:  # noqa: N802
        self.cursor = value


class _FakeDateTimeEdit:
    def __init__(self, display_format: str) -> None:
        self._display_format = display_format
        self.date_calls = 0
        self.datetime_calls = 0

    def displayFormat(self) -> str:  # noqa: N802
        return self._display_format

    def setDate(self, _value) -> None:  # noqa: N802
        self.date_calls += 1

    def setDateTime(self, _value) -> None:  # noqa: N802
        self.datetime_calls += 1


class _FakeDateEdit(_FakeDateTimeEdit):
    pass


def test_is_date_only_edit_handles_qdateedit_inheritance() -> None:
    flow = DateInputAutoFlow()
    date_only = _FakeDateEdit("dd.MM.yyyy")
    date_time = _FakeDateTimeEdit("dd.MM.yyyy HH:mm")

    assert flow._is_date_only_edit(cast(Any, date_only)) is True
    assert flow._is_date_only_edit(cast(Any, date_time)) is False


def test_apply_buffer_keeps_date_only_field_without_time_part() -> None:
    flow = DateInputAutoFlow()
    editor = _FakeEditor()
    date_only = _FakeDateEdit("dd.MM.yyyy")

    flow._apply_buffer(cast(Any, date_only), cast(Any, editor), "120120001530")

    assert editor.text == "12.01.2000"
    assert date_only.date_calls == 1
    assert date_only.datetime_calls == 0


def test_apply_buffer_keeps_datetime_field_with_time_part() -> None:
    flow = DateInputAutoFlow()
    editor = _FakeEditor()
    date_time = _FakeDateTimeEdit("dd.MM.yyyy HH:mm")

    flow._apply_buffer(cast(Any, date_time), cast(Any, editor), "120120001530")

    assert editor.text == "12.01.2000 15:30"
    assert date_time.datetime_calls == 1


def test_optional_datetime_edit_starts_empty_without_current_time(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert widget.displayFormat() == DATETIME_DISPLAY_FORMAT
        assert widget.dateTime() == DEFAULT_EMPTY_DATETIME
        assert widget.time() == QTime(0, 0)
    finally:
        widget.deleteLater()


def test_optional_datetime_edit_keeps_user_time_when_date_changes(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 1, 1), QTime(8, 30)))
        widget.setDate(QDate(2024, 1, 2))

        assert widget.date() == QDate(2024, 1, 2)
        assert widget.time() == QTime(8, 30)
    finally:
        widget.deleteLater()


def test_auto_flow_datetime_date_only_input_uses_empty_time_not_current(qapp) -> None:
    flow = DateInputAutoFlow()
    widget = create_optional_datetime_edit()
    editor = widget.lineEdit()
    try:
        flow._apply_buffer(widget, editor, "01012024")

        assert widget.date() == QDate(2024, 1, 1)
        assert widget.time() == QTime(0, 0)
    finally:
        widget.deleteLater()


def test_auto_flow_datetime_full_input_preserves_explicit_user_time(qapp) -> None:
    flow = DateInputAutoFlow()
    widget = create_optional_datetime_edit()
    editor = widget.lineEdit()
    try:
        flow._apply_buffer(widget, editor, "010120240830")

        assert widget.date() == QDate(2024, 1, 1)
        assert widget.time() == QTime(8, 30)
    finally:
        widget.deleteLater()
