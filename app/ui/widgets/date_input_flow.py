from __future__ import annotations

from PySide6.QtCore import QDate, QDateTime, QEvent, QObject, Qt, QTime
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QDateEdit, QDateTimeEdit, QLineEdit


class DateInputAutoFlow(QObject):
    _BUFFER_PROP = "_flow_buffer"
    _ACTIVE_PROP = "_flow_active"

    def eventFilter(self, obj: object, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            if isinstance(obj, QComboBox):
                return True
            if self._is_combo_popup(obj):
                return True

        target: QDateEdit | QDateTimeEdit | None = None
        editor: QLineEdit | None = None
        if isinstance(obj, (QDateTimeEdit, QDateEdit)):
            target = obj
            editor = obj.lineEdit()
        elif isinstance(obj, QLineEdit):
            parent = obj.parent()
            if isinstance(parent, (QDateTimeEdit, QDateEdit)):
                target = parent
                editor = obj

        if target is None:
            return False

        if event.type() == QEvent.Type.Wheel:
            return True
        if event.type() == QEvent.Type.MouseButtonPress:
            target.setProperty(self._ACTIVE_PROP, False)
            target.setProperty(self._BUFFER_PROP, "")
            return False
        if event.type() == QEvent.Type.FocusIn:
            target.setProperty(self._ACTIVE_PROP, True)
            target.setProperty(self._BUFFER_PROP, "")
            if not self._is_date_only_edit(target):
                target.setCurrentSection(QDateTimeEdit.Section.DaySection)
            else:
                target.setCurrentSection(QDateEdit.Section.DaySection)
            if editor is not None:
                editor.selectAll()
                editor.setCursorPosition(0)
            return False
        if event.type() == QEvent.Type.KeyPress:
            key_event = event if isinstance(event, QKeyEvent) else None
            if key_event is None or editor is None:
                return False
            key_text = key_event.text()
            if not (key_text.isdigit() or key_event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)):
                return False
            buffer = str(target.property(self._BUFFER_PROP) or "")
            if editor.hasSelectedText():
                buffer = ""
            if key_event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
                buffer = buffer[:-1]
            else:
                max_len = 12 if not self._is_date_only_edit(target) else 8
                if len(buffer) < max_len:
                    buffer = buffer + key_text
            target.setProperty(self._BUFFER_PROP, buffer)
            self._apply_buffer(target, editor, buffer)
            return True
        return False

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

    def _apply_buffer(self, obj: QDateEdit | QDateTimeEdit, editor: QLineEdit, buffer: str) -> None:
        if not self._is_date_only_edit(obj):
            formatted = self._format_datetime_buffer(buffer)
            editor.setText(formatted)
            editor.setCursorPosition(len(formatted))
            if len(buffer) >= 8:
                date_val = self._parse_date(buffer[:8])
                if date_val is not None:
                    if len(buffer) >= 12:
                        time_val = self._parse_time(buffer[8:12])
                        if time_val is not None:
                            obj.setDateTime(QDateTime(date_val, time_val))
                        else:
                            obj.setDate(date_val)
                    else:
                        obj.setDate(date_val)
        else:
            formatted = self._format_date_buffer(buffer)
            editor.setText(formatted)
            editor.setCursorPosition(len(formatted))
            if len(buffer) >= 8:
                date_val = self._parse_date(buffer[:8])
                if date_val is not None:
                    obj.setDate(date_val)

    @staticmethod
    def _is_date_only_edit(obj: QDateEdit | QDateTimeEdit) -> bool:
        # QDateEdit inherits QDateTimeEdit in Qt. Determine date-only mode by format.
        display_format = obj.displayFormat()
        has_time_tokens = any(token in display_format for token in ("h", "H", "m", "s", "a", "A"))
        return not has_time_tokens

    @staticmethod
    def _format_date_buffer(buffer: str) -> str:
        digits = (buffer + "________")[:8]
        return f"{digits[0:2]}.{digits[2:4]}.{digits[4:8]}"

    @staticmethod
    def _format_datetime_buffer(buffer: str) -> str:
        digits = (buffer + "____________")[:12]
        return f"{digits[0:2]}.{digits[2:4]}.{digits[4:8]} {digits[8:10]}:{digits[10:12]}"

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
