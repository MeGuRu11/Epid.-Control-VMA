from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

from PySide6.QtCore import QDate, QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDateTimeEdit,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.form100_dto import (
    Form100CardDto,
    Form100CreateRequest,
    Form100SignRequest,
    Form100UpdateRequest,
)
from app.ui.form100.widgets.bodymap_editor import BodymapEditor
from app.ui.form100.widgets.flags_strip import FlagsStrip
from app.ui.form100.widgets.validation_banner import ValidationBanner


class Form100Editor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_card: Form100CardDto | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.validation_banner = ValidationBanner()
        root.addWidget(self.validation_banner)

        identity_box = QGroupBox("Идентификация")
        identity_layout = QFormLayout(identity_box)
        self.last_name = QLineEdit()
        self.first_name = QLineEdit()
        self.middle_name = QLineEdit()
        self.birth_date = QDateEdit()
        self.birth_date.setCalendarPopup(True)
        self.birth_date.setDisplayFormat("dd.MM.yyyy")
        self.birth_date.setDate(QDate.currentDate())
        self.rank = QLineEdit()
        self.unit = QLineEdit()
        self.dog_tag_number = QLineEdit()
        identity_layout.addRow("Фамилия", self.last_name)
        identity_layout.addRow("Имя", self.first_name)
        identity_layout.addRow("Отчество", self.middle_name)
        identity_layout.addRow("Дата рождения", self.birth_date)
        identity_layout.addRow("Звание", self.rank)
        identity_layout.addRow("Подразделение", self.unit)
        identity_layout.addRow("Жетон", self.dog_tag_number)
        root.addWidget(identity_box)

        event_box = QGroupBox("Событие")
        event_layout = QFormLayout(event_box)
        self.injury_dt = QDateTimeEdit()
        self.injury_dt.setCalendarPopup(True)
        self.injury_dt.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.injury_dt.setDateTime(QDateTime.currentDateTime())
        self.has_injury_dt = QCheckBox("Есть дата травмы")
        self.has_injury_dt.setChecked(False)

        injury_line = QWidget()
        injury_line_layout = QHBoxLayout(injury_line)
        injury_line_layout.setContentsMargins(0, 0, 0, 0)
        injury_line_layout.addWidget(self.has_injury_dt)
        injury_line_layout.addWidget(self.injury_dt)
        self.injury_dt.setEnabled(False)
        self.has_injury_dt.toggled.connect(self.injury_dt.setEnabled)

        self.arrival_dt = QDateTimeEdit()
        self.arrival_dt.setCalendarPopup(True)
        self.arrival_dt.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.arrival_dt.setDateTime(QDateTime.currentDateTime())
        self.first_aid_before = QCheckBox("Помощь до поступления")
        self.is_combat = QCheckBox("Боевое ранение")
        self.cause_category = QLineEdit()
        self.cause_category.setText("Прочее")
        event_layout.addRow("Дата травмы", injury_line)
        event_layout.addRow("Дата поступления", self.arrival_dt)
        event_layout.addRow("Причина", self.cause_category)
        event_layout.addRow(self.first_aid_before)
        event_layout.addRow(self.is_combat)
        root.addWidget(event_box)

        diag_box = QGroupBox("Диагноз")
        diag_layout = QFormLayout(diag_box)
        self.diagnosis_text = QTextEdit()
        self.diagnosis_text.setFixedHeight(64)
        self.diagnosis_code = QLineEdit()
        self.triage = QLineEdit()
        diag_layout.addRow("Текст диагноза", self.diagnosis_text)
        diag_layout.addRow("Код диагноза", self.diagnosis_code)
        diag_layout.addRow("Триаж", self.triage)
        root.addWidget(diag_box)

        flags_box = QGroupBox("Флаги")
        flags_layout = QVBoxLayout(flags_box)
        self.flags_strip = FlagsStrip()
        flags_layout.addWidget(self.flags_strip)
        root.addWidget(flags_box)

        bodymap_box = QGroupBox("Схема тела")
        bodymap_layout = QVBoxLayout(bodymap_box)
        self.bodymap_editor = BodymapEditor()
        bodymap_layout.addWidget(self.bodymap_editor)
        root.addWidget(bodymap_box)
        root.addStretch()

    def clear_form(self) -> None:
        self.current_card = None
        self.validation_banner.clear_error()
        self.last_name.clear()
        self.first_name.clear()
        self.middle_name.clear()
        self.birth_date.setDate(QDate.currentDate())
        self.rank.clear()
        self.unit.clear()
        self.dog_tag_number.clear()
        self.has_injury_dt.setChecked(False)
        self.injury_dt.setDateTime(QDateTime.currentDateTime())
        self.arrival_dt.setDateTime(QDateTime.currentDateTime())
        self.first_aid_before.setChecked(False)
        self.is_combat.setChecked(False)
        self.cause_category.setText("Прочее")
        self.diagnosis_text.clear()
        self.diagnosis_code.clear()
        self.triage.clear()
        self.flags_strip.set_values({})
        self.bodymap_editor.clear()

    def load_card(self, card: Form100CardDto) -> None:
        self.current_card = card
        self.validation_banner.clear_error()
        self.last_name.setText(card.last_name)
        self.first_name.setText(card.first_name)
        self.middle_name.setText(card.middle_name or "")
        self.birth_date.setDate(QDate(card.birth_date.year, card.birth_date.month, card.birth_date.day))
        self.rank.setText(card.rank)
        self.unit.setText(card.unit)
        self.dog_tag_number.setText(card.dog_tag_number or "")
        if card.injury_dt:
            self.has_injury_dt.setChecked(True)
            self.injury_dt.setDateTime(_to_qdatetime(card.injury_dt))
        else:
            self.has_injury_dt.setChecked(False)
        self.arrival_dt.setDateTime(_to_qdatetime(card.arrival_dt))
        self.first_aid_before.setChecked(card.first_aid_before)
        self.is_combat.setChecked(bool(card.is_combat))
        self.cause_category.setText(card.cause_category)
        self.diagnosis_text.setPlainText(card.diagnosis_text)
        self.diagnosis_code.setText(card.diagnosis_code or "")
        self.triage.setText(card.triage or "")
        self.flags_strip.set_values(
            {
                "flag_urgent": card.flag_urgent,
                "flag_sanitation": card.flag_sanitation,
                "flag_isolation": card.flag_isolation,
                "flag_radiation": card.flag_radiation,
            }
        )
        self.bodymap_editor.set_marks(card.marks)

    def build_create_request(self) -> Form100CreateRequest:
        marks = self.bodymap_editor.get_marks()
        payload = {
            "last_name": self.last_name.text().strip(),
            "first_name": self.first_name.text().strip(),
            "middle_name": _none_if_empty(self.middle_name.text()),
            "birth_date": _to_py_date(self.birth_date.date()),
            "rank": self.rank.text().strip(),
            "unit": self.unit.text().strip(),
            "dog_tag_number": _none_if_empty(self.dog_tag_number.text()),
            "injury_dt": _to_py_datetime(self.injury_dt.dateTime()) if self.has_injury_dt.isChecked() else None,
            "arrival_dt": _to_py_datetime(self.arrival_dt.dateTime()),
            "first_aid_before": self.first_aid_before.isChecked(),
            "cause_category": self.cause_category.text().strip() or "Прочее",
            "is_combat": self.is_combat.isChecked(),
            "diagnosis_text": self.diagnosis_text.toPlainText().strip(),
            "diagnosis_code": _none_if_empty(self.diagnosis_code.text()),
            "triage": _none_if_empty(self.triage.text()),
            "marks": marks,
            **self.flags_strip.get_values(),
        }
        return Form100CreateRequest.model_validate(payload)

    def build_update_request(self) -> Form100UpdateRequest:
        marks = self.bodymap_editor.get_marks()
        payload = {
            "last_name": self.last_name.text().strip(),
            "first_name": self.first_name.text().strip(),
            "middle_name": _none_if_empty(self.middle_name.text()),
            "birth_date": _to_py_date(self.birth_date.date()),
            "rank": self.rank.text().strip(),
            "unit": self.unit.text().strip(),
            "dog_tag_number": _none_if_empty(self.dog_tag_number.text()),
            "injury_dt": _to_py_datetime(self.injury_dt.dateTime()) if self.has_injury_dt.isChecked() else None,
            "arrival_dt": _to_py_datetime(self.arrival_dt.dateTime()),
            "first_aid_before": self.first_aid_before.isChecked(),
            "cause_category": self.cause_category.text().strip() or "Прочее",
            "is_combat": self.is_combat.isChecked(),
            "diagnosis_text": self.diagnosis_text.toPlainText().strip(),
            "diagnosis_code": _none_if_empty(self.diagnosis_code.text()),
            "triage": _none_if_empty(self.triage.text()),
            "marks": marks,
            **self.flags_strip.get_values(),
        }
        return Form100UpdateRequest.model_validate(payload)

    def build_sign_request(self, signed_by: str | None = None, *, seal_applied: bool = False) -> Form100SignRequest:
        return Form100SignRequest(signed_by=signed_by, seal_applied=seal_applied)

    def set_read_only(self, read_only: bool) -> None:
        widgets = [
            self.last_name,
            self.first_name,
            self.middle_name,
            self.birth_date,
            self.rank,
            self.unit,
            self.dog_tag_number,
            self.has_injury_dt,
            self.injury_dt,
            self.arrival_dt,
            self.first_aid_before,
            self.is_combat,
            self.cause_category,
            self.diagnosis_text,
            self.diagnosis_code,
            self.triage,
        ]
        for widget in widgets:
            widget.setEnabled(not read_only)
        self.flags_strip.setEnabled(not read_only)
        self.bodymap_editor.setEnabled(not read_only)


def _none_if_empty(value: str) -> str | None:
    text = value.strip()
    return text or None


def _to_py_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _to_py_datetime(value: QDateTime) -> datetime:
    dt = cast(datetime, value.toPython())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _to_qdatetime(value: datetime) -> QDateTime:
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return QDateTime(value.year, value.month, value.day, value.hour, value.minute, value.second)
