from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.icon_select_widget import IconSelectWidget


def _parse_time(raw: str) -> QTime:
    text = raw.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)  # noqa: DTZ007
            return QTime(dt.hour, dt.minute, dt.second)
        except ValueError:
            continue
    return QTime.currentTime()


def _row(label_text: str, field: QWidget, label_w: int = 120) -> QHBoxLayout:
    """Горизонтальная строка: QLabel(fixed) + поле."""
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(label_w)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet("color: #5D6D7E; font-size: 12px;")
    lay.addWidget(lbl)
    lay.addWidget(field, 1)
    return lay


def _sep() -> QFrame:
    """Тонкий горизонтальный разделитель."""
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet("background: #E0E6EA; border: none;")
    return f


class Form100BottomWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        block = QGroupBox("Эвакуация и заключение")
        block.setObjectName("form100Bottom")
        vlay = QVBoxLayout(block)
        vlay.setContentsMargins(14, 12, 14, 14)
        vlay.setSpacing(8)

        # ── Жгут (время) ──────────────────────────────────────────────────
        self.tourniquet_time = QTimeEdit()
        self.tourniquet_time.setDisplayFormat("HH:mm")
        self.tourniquet_time.setFixedWidth(110)
        tq_lay = QHBoxLayout()
        tq_lay.setContentsMargins(0, 0, 0, 0)
        tq_lay.setSpacing(10)
        lbl_tq = QLabel("Жгут (время)")
        lbl_tq.setFixedWidth(120)
        lbl_tq.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl_tq.setStyleSheet("color: #5D6D7E; font-size: 12px;")
        tq_lay.addWidget(lbl_tq)
        tq_lay.addWidget(self.tourniquet_time)
        tq_lay.addStretch(1)
        vlay.addLayout(tq_lay)

        # ── Санобработка ──────────────────────────────────────────────────
        san_widget = QWidget()
        san_widget.setStyleSheet("background: transparent;")
        san_inner = QHBoxLayout(san_widget)
        san_inner.setContentsMargins(0, 0, 0, 0)
        san_inner.setSpacing(16)
        self.sanitation_group = QButtonGroup(self)
        self.rb_san_full = QRadioButton("Полная")
        self.rb_san_partial = QRadioButton("Частичная")
        self.rb_san_none = QRadioButton("Не проводилась")
        for rb in (self.rb_san_full, self.rb_san_partial, self.rb_san_none):
            self.sanitation_group.addButton(rb)
            san_inner.addWidget(rb)
        san_inner.addStretch(1)
        vlay.addLayout(_row("Санобработка", san_widget))

        vlay.addWidget(_sep())

        # ── Позиция при эвакуации ─────────────────────────────────────────
        sec_lbl = QLabel("ЭВАКУАЦИЯ")
        sec_lbl.setStyleSheet(
            "color: #2E86C1; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;"
        )
        vlay.addWidget(sec_lbl)

        self.evacuation_dest = IconSelectWidget(
            (
                ("lying",     "Лёжа"),
                ("sitting",   "Сидя"),
                ("stretcher", "Носилки"),
            )
        )
        vlay.addLayout(_row("Позиция", self.evacuation_dest))

        # ── Очерёдность ───────────────────────────────────────────────────
        prio_widget = QWidget()
        prio_widget.setStyleSheet("background: transparent;")
        prio_inner = QHBoxLayout(prio_widget)
        prio_inner.setContentsMargins(0, 0, 0, 0)
        prio_inner.setSpacing(16)
        self.priority_group = QButtonGroup(self)
        self.rb_priority_i   = QRadioButton("I")
        self.rb_priority_ii  = QRadioButton("II")
        self.rb_priority_iii = QRadioButton("III")
        for rb in (self.rb_priority_i, self.rb_priority_ii, self.rb_priority_iii):
            self.priority_group.addButton(rb)
            prio_inner.addWidget(rb)
        prio_inner.addStretch(1)
        vlay.addLayout(_row("Очерёдность", prio_widget))

        # ── Транспорт ─────────────────────────────────────────────────────
        self.transport_type = IconSelectWidget(
            (
                ("car",   "Авто"),
                ("ambu",  "Сан."),
                ("ship",  "Корабль"),
                ("heli",  "Вертолёт"),
                ("plane", "Самолёт"),
            )
        )
        vlay.addLayout(_row("Транспорт", self.transport_type))

        vlay.addWidget(_sep())

        # ── Подпись врача + Диагноз ───────────────────────────────────────
        sec_lbl2 = QLabel("ЗАКЛЮЧЕНИЕ")
        sec_lbl2.setStyleSheet(
            "color: #2E86C1; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;"
        )
        vlay.addWidget(sec_lbl2)

        self.doctor_signature = QLineEdit()
        vlay.addLayout(_row("Подпись врача", self.doctor_signature))

        diag_lbl = QLabel("Диагноз")
        diag_lbl.setStyleSheet("color: #5D6D7E; font-size: 12px;")
        vlay.addWidget(diag_lbl)
        self.main_diagnosis = QTextEdit()
        self.main_diagnosis.setFixedHeight(70)
        self.main_diagnosis.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        vlay.addWidget(self.main_diagnosis)

        root.addWidget(block)

    # ── Вспомогательные ──────────────────────────────────────────────────────

    def _set_sanitation_type(self, value: str) -> None:
        if value == "full":
            self.rb_san_full.setChecked(True)
        elif value == "partial":
            self.rb_san_partial.setChecked(True)
        elif value == "none":
            self.rb_san_none.setChecked(True)
        else:
            self.sanitation_group.setExclusive(False)
            for rb in (self.rb_san_full, self.rb_san_partial, self.rb_san_none):
                rb.setChecked(False)
            self.sanitation_group.setExclusive(True)

    def _sanitation_type(self) -> str:
        if self.rb_san_full.isChecked():
            return "full"
        if self.rb_san_partial.isChecked():
            return "partial"
        if self.rb_san_none.isChecked():
            return "none"
        return ""

    def _set_priority(self, value: str) -> None:
        if value == "I":
            self.rb_priority_i.setChecked(True)
        elif value == "II":
            self.rb_priority_ii.setChecked(True)
        elif value == "III":
            self.rb_priority_iii.setChecked(True)
        else:
            self.priority_group.setExclusive(False)
            for rb in (self.rb_priority_i, self.rb_priority_ii, self.rb_priority_iii):
                rb.setChecked(False)
            self.priority_group.setExclusive(True)

    def _priority(self) -> str:
        if self.rb_priority_i.isChecked():
            return "I"
        if self.rb_priority_ii.isChecked():
            return "II"
        if self.rb_priority_iii.isChecked():
            return "III"
        return ""

    # ── Публичный API ────────────────────────────────────────────────────────

    def set_values(self, payload: dict[str, str]) -> None:
        self.tourniquet_time.setTime(
            _parse_time(str(payload.get("tourniquet_time") or ""))
        )
        self._set_sanitation_type(str(payload.get("sanitation_type") or ""))
        self.evacuation_dest.set_value(str(payload.get("evacuation_dest") or ""))
        self._set_priority(str(payload.get("evacuation_priority") or ""))
        self.transport_type.set_value(str(payload.get("transport_type") or ""))
        self.doctor_signature.setText(str(payload.get("doctor_signature") or ""))
        self.main_diagnosis.setPlainText(str(payload.get("main_diagnosis") or ""))

    def collect(self) -> dict[str, str]:
        return {
            "tourniquet_time":   self.tourniquet_time.time().toString("HH:mm"),
            "sanitation_type":   self._sanitation_type(),
            "evacuation_dest":   self.evacuation_dest.value(),
            "evacuation_priority": self._priority(),
            "transport_type":    self.transport_type.value(),
            "doctor_signature":  self.doctor_signature.text().strip(),
            "main_diagnosis":    self.main_diagnosis.toPlainText().strip(),
        }

    def set_locked(self, locked: bool) -> None:
        self.tourniquet_time.setEnabled(not locked)
        self.rb_san_full.setEnabled(not locked)
        self.rb_san_partial.setEnabled(not locked)
        self.rb_san_none.setEnabled(not locked)
        self.evacuation_dest.setEnabled(not locked)
        self.rb_priority_i.setEnabled(not locked)
        self.rb_priority_ii.setEnabled(not locked)
        self.rb_priority_iii.setEnabled(not locked)
        self.transport_type.setEnabled(not locked)
        self.doctor_signature.setEnabled(not locked)
        self.main_diagnosis.setReadOnly(locked)
