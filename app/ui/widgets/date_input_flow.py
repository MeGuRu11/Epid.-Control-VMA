from __future__ import annotations

from PySide6.QtCore import QDate, QDateTime, QEvent, QObject, Qt, QTime
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QLineEdit,
)

from app.ui.widgets.datetime_inputs import DEFAULT_EMPTY_DATE, DEFAULT_EMPTY_DATETIME


class DateInputAutoFlow(QObject):
    def eventFilter(self, obj: object, event: QEvent) -> bool:  # noqa: N802
        try:
            if event.type() == QEvent.Type.Wheel:
                if isinstance(obj, QComboBox):
                    return True
                if self._is_combo_popup(obj):
                    return True

            target = self._resolve_date_widget(obj)

            if target is None:
                return False

            if event.type() == QEvent.Type.Wheel:
                return True
            if event.type() == QEvent.Type.KeyPress:
                key_event = event if isinstance(event, QKeyEvent) else None
                if key_event is None:
                    return False
                if key_event.matches(QKeySequence.StandardKey.Paste):
                    clipboard = QApplication.clipboard()
                    digits = self._normalize_paste_digits(clipboard.text())
                    return self._apply_paste_digits(target, digits)
                if self._whole_field_selected(target):
                    if key_event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                        self._clear_to_sentinel(target)
                        return True
                    key_text = key_event.text()
                    if key_text and key_text.isdigit():
                        target.setSelectedSection(target.sectionAt(0))
                        return False
            return False
        except KeyboardInterrupt:
            # Allow Ctrl+C from terminal without noisy Qt "Python override" tracebacks.
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return True

    @staticmethod
    def _resolve_date_widget(obj: object) -> QDateEdit | QDateTimeEdit | None:
        if isinstance(obj, QDateTimeEdit | QDateEdit):
            return obj
        if isinstance(obj, QLineEdit):
            parent = obj.parent()
            if isinstance(parent, QDateTimeEdit | QDateEdit):
                return parent
        return None

    @staticmethod
    def _is_combo_popup(obj: object) -> bool:
        current: QObject | None = obj if isinstance(obj, QObject) else None
        while current is not None:
            if isinstance(current, QComboBox):
                return True
            if isinstance(current, QAbstractItemView):
                parent = current.parent()
                if isinstance(parent, QComboBox):
                    return True
            current = current.parent()
        return False

    @staticmethod
    def _is_date_only_edit(obj: QDateEdit | QDateTimeEdit) -> bool:
        # QDateEdit inherits QDateTimeEdit in Qt. Determine date-only mode by format.
        display_format = obj.displayFormat()
        has_time_tokens = any(token in display_format for token in ("h", "H", "m", "s", "a", "A"))
        return not has_time_tokens

    @staticmethod
    def _normalize_paste_digits(text: str) -> str:
        return "".join(character for character in text if character.isdigit())

    @staticmethod
    def _whole_field_selected(obj: QDateEdit | QDateTimeEdit) -> bool:
        editor = obj.lineEdit()
        if editor is None:
            return False
        full_text = editor.text()
        return bool(full_text) and editor.selectedText() == full_text

    def _clear_to_sentinel(self, obj: QDateEdit | QDateTimeEdit) -> None:
        if self._is_date_only_edit(obj):
            obj.setDate(DEFAULT_EMPTY_DATE)
        else:
            obj.setDateTime(DEFAULT_EMPTY_DATETIME)

    def _apply_paste_digits(self, obj: QDateEdit | QDateTimeEdit, digits: str) -> bool:
        if len(digits) not in (8, 12):
            return False
        date_val = self._parse_date(digits[:8])
        if date_val is None:
            return False
        if self._is_date_only_edit(obj):
            obj.setDate(date_val)
            return True
        time_val = QTime(0, 0)
        if len(digits) == 12:
            parsed_time = self._parse_time(digits[8:12])
            if parsed_time is None:
                return False
            time_val = parsed_time
        obj.setDateTime(QDateTime(date_val, time_val))
        return True

    @staticmethod
    def _parse_date(digits: str) -> QDate | None:
        if len(digits) < 8:
            return None
        try:
            day = int(digits[0:2])
            month = int(digits[2:4])
            year = int(digits[4:8])
        except ValueError:
            return None
        date_val = QDate(year, month, day)
        if not date_val.isValid():
            return None
        return date_val

    @staticmethod
    def _parse_time(digits: str) -> QTime | None:
        if len(digits) < 4:
            return None
        try:
            hour = int(digits[0:2])
            minute = int(digits[2:4])
        except ValueError:
            return None
        time_val = QTime(hour, minute)
        if not time_val.isValid():
            return None
        return time_val
