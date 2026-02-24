from __future__ import annotations

from datetime import UTC, date, datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.patient_service import PatientService
from app.domain.constants import MilitaryCategory
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import clear_status, set_status


class PatientEditDialog(QDialog):
    def __init__(
        self,
        patient_service: PatientService,
        patient_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.patient_service = patient_service
        self.patient_id = patient_id
        self.setWindowTitle("Редактирование пациента")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_patient()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("Редактирование пациента")
        header.setObjectName("pageTitle")
        layout.addWidget(header)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("muted")
        layout.addWidget(self.subtitle)

        box = QGroupBox("Данные пациента")
        form = QFormLayout()
        self.full_name = QLineEdit()
        self.dob = QDateEdit()
        self.dob.setCalendarPopup(True)
        self.dob.setDisplayFormat("dd.MM.yyyy")
        self.dob.setMinimumDate(QDate(1900, 1, 1))
        self.dob.setMaximumDate(QDate.currentDate())
        self.sex = QComboBox()
        self.sex.addItems(["М", "Ж"])
        self.category_combo = QComboBox()
        self.category_combo.addItem("Выбрать", None)
        for value in MilitaryCategory.values():
            self.category_combo.addItem(value, value)
        self.military_unit = QLineEdit()
        self.military_district = QLineEdit()

        form.addRow("ФИО *", self.full_name)
        form.addRow("Дата рождения", self.dob)
        form.addRow("Пол", self.sex)
        form.addRow("Категория *", self.category_combo)
        form.addRow("Воинская часть", self.military_unit)
        form.addRow("Военный округ", self.military_district)
        box.setLayout(form)
        layout.addWidget(box)

        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        layout.addWidget(self.status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("primaryButton")
        compact_button(self.save_btn)
        self.save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Отмена")
        compact_button(cancel_btn)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _load_patient(self) -> None:
        patient = self.patient_service.get_by_id(self.patient_id)
        self.subtitle.setText(f"ID: {patient.id}")
        self.full_name.setText(patient.full_name)
        if patient.dob:
            self.dob.setDate(QDate(patient.dob.year, patient.dob.month, patient.dob.day))
        sex_map = {"M": "М", "F": "Ж"}
        self.sex.setCurrentText(sex_map.get(patient.sex or "", "М"))
        idx_cat = self.category_combo.findData(patient.category)
        if idx_cat >= 0:
            self.category_combo.setCurrentIndex(idx_cat)
        self.military_unit.setText(patient.military_unit or "")
        self.military_district.setText(patient.military_district or "")

    def _validate(self) -> bool:
        clear_status(self.status)
        if not self.full_name.text().strip():
            set_status(self.status, "Укажите ФИО пациента.", "error")
            return False
        dob = self._date_value()
        if dob and dob > datetime.now(tz=UTC).date():
            set_status(self.status, "Дата рождения не может быть в будущем.", "error")
            return False
        if self.category_combo.currentData() is None:
            set_status(self.status, "Выберите категорию военнослужащего.", "error")
            return False
        return True

    def _date_value(self) -> date | None:
        qd = self.dob.date()
        if not qd.isValid():
            return None
        return date(qd.year(), qd.month(), qd.day())

    def _on_save(self) -> None:
        if not self._validate():
            return
        sex_code = "M" if self.sex.currentText() == "М" else "F"
        category = self.category_combo.currentData()
        try:
            self.patient_service.update_details(
                self.patient_id,
                full_name=self.full_name.text().strip(),
                dob=self._date_value(),
                sex=sex_code,
                category=category,
                military_unit=self.military_unit.text().strip() or None,
                military_district=self.military_district.text().strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        QMessageBox.information(self, "Готово", "Данные пациента обновлены.")
        self.accept()
