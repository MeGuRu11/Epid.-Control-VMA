from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtTest import QTest

from app.ui.widgets.date_input_flow import DateInputAutoFlow
from app.ui.widgets.datetime_inputs import (
    DATE_DISPLAY_FORMAT,
    DATETIME_DISPLAY_FORMAT,
    DEFAULT_EMPTY_DATE,
    DEFAULT_EMPTY_DATETIME,
    IS_EMPTY_PROPERTY,
    create_optional_date_edit,
    create_optional_datetime_edit,
    optional_date_value,
    optional_datetime_value,
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
        assert widget.specialValueText() == ""
        assert widget.dateTime() == DEFAULT_EMPTY_DATETIME
        assert widget.text() == "01.01.1900 00:00"
        assert widget.property(IS_EMPTY_PROPERTY) is True
        assert widget.time() == QTime(0, 0)
    finally:
        widget.deleteLater()


def test_optional_date_edit_uses_visible_sentinel(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.displayFormat() == DATE_DISPLAY_FORMAT
        assert widget.specialValueText() == ""
        assert widget.date() == DEFAULT_EMPTY_DATE
        assert widget.text() == "01.01.1900"
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        widget.deleteLater()


def test_auto_flow_date_pastes_formatted_value(qapp) -> None:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    widget = create_optional_date_edit()
    try:
        qapp.clipboard().setText("26.05.2026")
        widget.show()
        widget.setFocus()
        qapp.processEvents()

        QTest.keySequence(widget, "Ctrl+V")
        qapp.processEvents()

        assert widget.text() == "26.05.2026"
        assert widget.date() == QDate(2026, 5, 26)
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_pastes_compact_value(qapp) -> None:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    widget = create_optional_datetime_edit()
    try:
        qapp.clipboard().setText("260520260830")
        widget.show()
        widget.setFocus()
        qapp.processEvents()

        QTest.keySequence(widget, "Ctrl+V")
        qapp.processEvents()

        assert widget.text() == "26.05.2026 08:30"
        assert widget.dateTime() == QDateTime(QDate(2026, 5, 26), QTime(8, 30))
    finally:
        qapp.removeEventFilter(flow)
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


def test_auto_flow_datetime_partial_time_digits_remain_visible(qapp) -> None:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    widget = create_optional_datetime_edit()
    try:
        widget.show()
        widget.lineEdit().setFocus()
        qapp.processEvents()

        QTest.keyClicks(widget.lineEdit(), "1010202412")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:__"
        assert widget.lineEdit().cursorPosition() == 14
        assert widget.date() == QDate(2024, 10, 10)
        assert widget.time() == QTime(12, 0)

        QTest.keyClicks(widget.lineEdit(), "4")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:4_"
        assert widget.time() == QTime(12, 40)

        QTest.keyClicks(widget.lineEdit(), "3")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:43"
        assert widget.dateTime() == QDateTime(QDate(2024, 10, 10), QTime(12, 43))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_shows_date_immediately_after_8_digits(qapp) -> None:
    flow = DateInputAutoFlow()
    widget = create_optional_datetime_edit()
    editor = widget.lineEdit()
    try:
        flow._apply_buffer(widget, editor, "10102024")

        assert widget.date() == QDate(2024, 10, 10)
        assert editor.text() == "10.10.2024 __:__"
        assert widget.time() == QTime(0, 0)
    finally:
        widget.deleteLater()


def test_auto_flow_datetime_progressively_shows_each_digit(qapp) -> None:
    flow = DateInputAutoFlow()
    widget = create_optional_datetime_edit()
    editor = widget.lineEdit()
    expected_text_by_length = {
        1: "1_.__.____ __:__",
        2: "10.__.____ __:__",
        3: "10.1_.____ __:__",
        4: "10.10.____ __:__",
        5: "10.10.2___ __:__",
        6: "10.10.20__ __:__",
        7: "10.10.202_ __:__",
        8: "10.10.2024 __:__",
        9: "10.10.2024 1_:__",
        10: "10.10.2024 12:__",
        11: "10.10.2024 12:4_",
        12: "10.10.2024 12:43",
    }
    try:
        for digit_count, expected_text in expected_text_by_length.items():
            buffer = "101020241243"[:digit_count]
            flow._apply_buffer(widget, editor, buffer)

            assert editor.text() == expected_text
            digits_in_text = "".join(character for character in editor.text() if character.isdigit())
            assert digits_in_text.startswith(buffer)

        assert widget.dateTime() == QDateTime(QDate(2024, 10, 10), QTime(12, 43))
    finally:
        widget.deleteLater()


def test_auto_flow_date_only_shows_date_immediately(qapp) -> None:
    flow = DateInputAutoFlow()
    widget = create_optional_date_edit()
    editor = widget.lineEdit()
    try:
        flow._apply_buffer(widget, editor, "10102024")

        assert widget.date() == QDate(2024, 10, 10)
        assert editor.text() == "10.10.2024"
    finally:
        widget.deleteLater()


def test_auto_flow_date_manual_input_matching_empty_sentinel_stays_visible(qapp) -> None:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    widget = create_optional_date_edit()
    try:
        widget.show()
        widget.lineEdit().setFocus()
        qapp.processEvents()

        QTest.keyClicks(widget.lineEdit(), "01011900")
        qapp.processEvents()

        assert widget.text() == "01.01.1900"
        assert optional_date_value(widget) is None
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_manual_input_matching_empty_sentinel_stays_visible(qapp) -> None:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    widget = create_optional_datetime_edit()
    try:
        widget.show()
        widget.lineEdit().setFocus()
        qapp.processEvents()

        QTest.keyClicks(widget.lineEdit(), "010119000000")
        qapp.processEvents()

        assert widget.text() == "01.01.1900 00:00"
        assert optional_datetime_value(widget) is None
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()
