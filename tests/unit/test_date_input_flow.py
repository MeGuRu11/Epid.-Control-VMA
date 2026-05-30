from __future__ import annotations

from PySide6.QtCore import QDate, QDateTime, Qt, QTime
from PySide6.QtTest import QTest

from app.ui.widgets.date_input_flow import DateInputAutoFlow
from app.ui.widgets.datetime_inputs import (
    DATE_DISPLAY_FORMAT,
    DATETIME_DISPLAY_FORMAT,
    DEFAULT_EMPTY_DATE,
    DEFAULT_EMPTY_DATETIME,
    IS_EMPTY_PROPERTY,
    create_birth_date_edit,
    create_optional_date_edit,
    create_optional_datetime_edit,
    optional_date_value,
    optional_datetime_value,
)


def _install_flow(qapp) -> DateInputAutoFlow:
    flow = DateInputAutoFlow(qapp)
    qapp.installEventFilter(flow)
    return flow


def _commit_widget_text(widget) -> None:
    widget.interpretText()


def test_is_date_only_edit_handles_qdateedit_inheritance(qapp) -> None:
    flow = DateInputAutoFlow()
    date_only = create_optional_date_edit()
    date_time = create_optional_datetime_edit()

    try:
        assert flow._is_date_only_edit(date_only) is True
        assert flow._is_date_only_edit(date_time) is False
    finally:
        date_only.deleteLater()
        date_time.deleteLater()


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


def test_optional_datetime_edit_disables_keyboard_tracking(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        assert widget.keyboardTracking() is False
    finally:
        widget.deleteLater()


def test_optional_date_edit_disables_keyboard_tracking(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.keyboardTracking() is False
    finally:
        widget.deleteLater()


def test_year_section_accepts_full_four_digit_year_after_commit(qapp) -> None:
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.YearSection)

        QTest.keyClicks(widget, "1985")
        qapp.processEvents()

        assert widget.text() == "10.10.1985 12:43"
        _commit_widget_text(widget)
        assert widget.dateTime() == QDateTime(QDate(1985, 10, 10), QTime(12, 43))
    finally:
        widget.deleteLater()


def test_birth_date_year_below_2000_sequential_typing(qapp) -> None:
    widget = create_birth_date_edit()
    try:
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.DaySection)

        QTest.keyClicks(widget, "15061985")
        qapp.processEvents()

        assert widget.text() == "15.06.1985"
        _commit_widget_text(widget)
        assert widget.date() == QDate(1985, 6, 15)
    finally:
        widget.deleteLater()


def test_minimum_does_not_change_empty_sentinel(qapp) -> None:
    widget = create_optional_date_edit()
    try:
        assert widget.date() == DEFAULT_EMPTY_DATE
        assert optional_date_value(widget) is None

        widget.setDate(QDate(1985, 6, 15))

        assert optional_date_value(widget) == QDate(1985, 6, 15).toPython()
    finally:
        widget.deleteLater()


def test_auto_flow_date_pastes_formatted_value(qapp) -> None:
    flow = _install_flow(qapp)
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
    flow = _install_flow(qapp)
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


def test_auto_flow_datetime_pastes_formatted_value(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        qapp.clipboard().setText("26.05.2026 08:30")
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


def test_auto_flow_datetime_paste_replaces_full_field_from_middle_section(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        qapp.clipboard().setText("26.05.2026 08:30")
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.MonthSection)

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


def test_auto_flow_datetime_native_typing_shows_partial_time_digits(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.DaySection)

        QTest.keyClicks(widget, "1010202412")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:00"

        QTest.keyClicks(widget, "4")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:4"

        QTest.keyClicks(widget, "3")
        qapp.processEvents()

        assert widget.lineEdit().text() == "10.10.2024 12:43"
        _commit_widget_text(widget)
        assert widget.dateTime() == QDateTime(QDate(2024, 10, 10), QTime(12, 43))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_sequential_typing_builds_full_datetime(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.DaySection)

        QTest.keyClicks(widget, "101020241243")
        qapp.processEvents()

        assert widget.text() == "10.10.2024 12:43"
        _commit_widget_text(widget)
        assert widget.text() == "10.10.2024 12:43"
        assert widget.dateTime() == QDateTime(QDate(2024, 10, 10), QTime(12, 43))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_section_edit_does_not_restart_full_input(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.MonthSection)

        QTest.keyClicks(widget, "05")
        qapp.processEvents()

        assert widget.text() == "10.05.2024 12:43"
        _commit_widget_text(widget)
        assert widget.dateTime() == QDateTime(QDate(2024, 5, 10), QTime(12, 43))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_select_all_then_type_restarts_from_first_section(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        line = widget.lineEdit()
        line.selectAll()
        qapp.processEvents()

        QTest.keyClicks(widget, "26052026")
        qapp.processEvents()

        assert widget.text().startswith("26.05.2026")
        _commit_widget_text(widget)
        assert widget.date() == QDate(2026, 5, 26)
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_year_section_edit_preserves_other_sections(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(8, 30)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.YearSection)

        QTest.keyClicks(widget, "1985")
        qapp.processEvents()

        assert widget.text() == "10.10.1985 08:30"
        _commit_widget_text(widget)
        assert widget.dateTime() == QDateTime(QDate(1985, 10, 10), QTime(8, 30))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_arrow_changes_only_selected_section(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.MonthSection)

        QTest.keyClick(widget, Qt.Key.Key_Up)
        qapp.processEvents()

        assert widget.text() == "10.11.2024 12:43"
        assert widget.dateTime() == QDateTime(QDate(2024, 11, 10), QTime(12, 43))
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_select_all_then_delete_clears_datetime_to_sentinel(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.setDateTime(QDateTime(QDate(2024, 10, 10), QTime(12, 43)))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        line = widget.lineEdit()
        line.selectAll()
        qapp.processEvents()

        QTest.keyClick(widget, Qt.Key.Key_Delete)
        qapp.processEvents()

        assert widget.dateTime() == DEFAULT_EMPTY_DATETIME
        assert optional_datetime_value(widget) is None
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_select_all_then_backspace_clears_date_to_sentinel(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_date_edit()
    try:
        widget.setDate(QDate(2024, 10, 10))
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        line = widget.lineEdit()
        line.selectAll()
        qapp.processEvents()

        QTest.keyClick(widget, Qt.Key.Key_Backspace)
        qapp.processEvents()

        assert widget.date() == DEFAULT_EMPTY_DATE
        assert optional_date_value(widget) is None
        assert widget.property(IS_EMPTY_PROPERTY) is True
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_single_section_delete_stays_native(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        original = QDateTime(QDate(2024, 10, 10), QTime(12, 43))
        widget.setDateTime(original)
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.MonthSection)

        QTest.keyClick(widget, Qt.Key.Key_Delete)
        qapp.processEvents()

        assert widget.dateTime() == original
        assert optional_datetime_value(widget) is not None
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_date_manual_input_matching_empty_sentinel_stays_visible(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_date_edit()
    try:
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.DaySection)

        QTest.keyClicks(widget, "01011900")
        qapp.processEvents()

        _commit_widget_text(widget)
        assert widget.text() == "01.01.1900"
        assert optional_date_value(widget) is None
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()


def test_auto_flow_datetime_manual_input_matching_empty_sentinel_stays_visible(qapp) -> None:
    flow = _install_flow(qapp)
    widget = create_optional_datetime_edit()
    try:
        widget.show()
        widget.setFocus()
        qapp.processEvents()
        widget.setSelectedSection(widget.Section.DaySection)

        QTest.keyClicks(widget, "010119000000")
        qapp.processEvents()

        _commit_widget_text(widget)
        assert widget.text() == "01.01.1900 00:00"
        assert optional_datetime_value(widget) is None
    finally:
        qapp.removeEventFilter(flow)
        widget.deleteLater()
