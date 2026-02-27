"""WizardStep1 — Идентификация + Корешок."""
from __future__ import annotations

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTimeEdit,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.form100_stub_widget import Form100StubWidget


class StepIdentification(QWidget):
    """Шаг 1 мастера: Корешок + Идентификация основного бланка."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._stub = Form100StubWidget()
        stub_scroll = QScrollArea()
        stub_scroll.setWidgetResizable(True)
        stub_scroll.setFrameShape(QFrame.Shape.NoFrame)
        stub_scroll.setWidget(self._stub)
        layout.addWidget(stub_scroll, 1)

        ident_box = QGroupBox("Идентификация — основной бланк")
        ident_lay = QFormLayout(ident_box)
        ident_lay.setContentsMargins(14, 12, 14, 12)
        ident_lay.setVerticalSpacing(10)
        ident_lay.setHorizontalSpacing(14)

        self.main_issued_place = QLineEdit()
        self.main_issued_place.setPlaceholderText("Мед. пункт / учреждение")

        issued_row = QHBoxLayout()
        issued_row.setContentsMargins(0, 0, 0, 0)
        issued_row.setSpacing(6)
        self.main_issued_time = QTimeEdit()
        self.main_issued_time.setDisplayFormat("HH:mm")
        self.main_issued_date = QDateEdit()
        self.main_issued_date.setDisplayFormat("dd.MM.yyyy")
        self.main_issued_date.setCalendarPopup(True)
        issued_row.addWidget(self.main_issued_time)
        issued_row.addWidget(QLabel("от"))
        issued_row.addWidget(self.main_issued_date)
        issued_row.addStretch(1)

        self.main_rank = QLineEdit()
        self.main_rank.setPlaceholderText("в/звание")
        self.main_unit = QLineEdit()
        self.main_unit.setPlaceholderText("в/часть")
        self.main_full_name = QLineEdit()
        self.main_full_name.setPlaceholderText("фамилия, имя, отчество")
        self.main_id_tag = QLineEdit()
        self.main_id_tag.setPlaceholderText("удостоверение / жетон №")

        injury_row = QHBoxLayout()
        injury_row.setContentsMargins(0, 0, 0, 0)
        injury_row.setSpacing(6)
        self.main_injury_time = QTimeEdit()
        self.main_injury_time.setDisplayFormat("HH:mm")
        self.main_injury_date = QDateEdit()
        self.main_injury_date.setDisplayFormat("dd.MM.yyyy")
        self.main_injury_date.setCalendarPopup(True)
        injury_row.addWidget(self.main_injury_time)
        injury_row.addWidget(QLabel("от"))
        injury_row.addWidget(self.main_injury_date)
        injury_row.addStretch(1)

        ident_lay.addRow("Выдана:", self.main_issued_place)
        ident_lay.addRow("Время / дата выдачи:", issued_row)
        ident_lay.addRow("В/звание:", self.main_rank)
        ident_lay.addRow("В/часть:", self.main_unit)
        ident_lay.addRow("ФИО:", self.main_full_name)
        ident_lay.addRow("Жетон №:", self.main_id_tag)
        ident_lay.addRow("Ранен / заболел:", injury_row)

        ident_scroll = QScrollArea()
        ident_scroll.setWidgetResizable(True)
        ident_scroll.setFrameShape(QFrame.Shape.NoFrame)
        ident_scroll.setWidget(ident_box)
        layout.addWidget(ident_scroll, 1)

    def set_values(self, payload: dict[str, str], markers: list[dict]) -> None:  # type: ignore[type-arg]  # noqa: ARG002
        self._stub.set_values(payload)
        self.main_issued_place.setText(str(payload.get("main_issued_place") or ""))
        self.main_rank.setText(str(payload.get("main_rank") or ""))
        self.main_unit.setText(str(payload.get("main_unit") or ""))
        self.main_full_name.setText(str(payload.get("main_full_name") or ""))
        self.main_id_tag.setText(str(payload.get("main_id_tag") or ""))

        for time_edit, key in (
            (self.main_issued_time, "main_issued_time"),
            (self.main_injury_time, "main_injury_time"),
        ):
            val = str(payload.get(key) or "")
            t = QTime.fromString(val, "HH:mm")
            time_edit.setTime(t if t.isValid() else QTime(0, 0))

        for date_edit, key in (
            (self.main_issued_date, "main_issued_date"),
            (self.main_injury_date, "main_injury_date"),
        ):
            val = str(payload.get(key) or "")
            d = QDate.fromString(val, "dd.MM.yyyy")
            date_edit.setDate(d if d.isValid() else QDate.currentDate())

    def collect(self) -> tuple[dict[str, str], list[dict]]:  # type: ignore[type-arg]
        out = self._stub.collect()
        out["main_issued_place"] = self.main_issued_place.text().strip()
        out["main_rank"] = self.main_rank.text().strip()
        out["main_unit"] = self.main_unit.text().strip()
        out["main_full_name"] = self.main_full_name.text().strip()
        out["main_id_tag"] = self.main_id_tag.text().strip()
        out["main_issued_time"] = self.main_issued_time.time().toString("HH:mm")
        out["main_issued_date"] = self.main_issued_date.date().toString("dd.MM.yyyy")
        out["main_injury_time"] = self.main_injury_time.time().toString("HH:mm")
        out["main_injury_date"] = self.main_injury_date.date().toString("dd.MM.yyyy")
        return out, []

    def set_locked(self, locked: bool) -> None:
        self._stub.set_enabled(not locked)
        for w in (
            self.main_issued_place,
            self.main_issued_time,
            self.main_issued_date,
            self.main_rank,
            self.main_unit,
            self.main_full_name,
            self.main_id_tag,
            self.main_injury_time,
            self.main_injury_date,
        ):
            w.setEnabled(not locked)
