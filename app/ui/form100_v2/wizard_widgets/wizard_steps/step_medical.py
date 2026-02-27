"""WizardStep3 — Медицинская помощь."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class StepMedical(QWidget):
    """Шаг 3 мастера: поля медицинской помощи."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        mp_box = QGroupBox("Медицинская помощь")
        mp_box.setObjectName("form100Help")
        mp_lay = QFormLayout(mp_box)
        mp_lay.setContentsMargins(20, 16, 20, 16)
        mp_lay.setVerticalSpacing(10)
        mp_lay.setHorizontalSpacing(16)

        self.mp_antibiotic = QCheckBox("Антибиотик")
        self.mp_antibiotic_dose = QLineEdit()
        self.mp_antibiotic_dose.setPlaceholderText("доза")

        self.mp_serum_pss = QCheckBox("Сыворотка ПСС")
        self.mp_serum_pgs = QCheckBox("Сыворотка ПГС")
        self.mp_serum_dose = QLineEdit()
        self.mp_serum_dose.setPlaceholderText("доза")

        self.mp_toxoid = QLineEdit()
        self.mp_toxoid.setPlaceholderText("анатоксин (какой)")

        self.mp_antidote = QLineEdit()
        self.mp_antidote.setPlaceholderText("антидот (какой)")

        self.mp_analgesic = QCheckBox("Обезболивающее")
        self.mp_analgesic_dose = QLineEdit()
        self.mp_analgesic_dose.setPlaceholderText("доза")

        self.mp_transfusion_blood = QCheckBox("Переливание крови")
        self.mp_transfusion_substitute = QCheckBox("Кровезаменители")
        self.mp_immobilization = QCheckBox("Иммобилизация")
        self.mp_bandage = QCheckBox("Перевязка")

        mp_lay.addRow(self.mp_antibiotic, self.mp_antibiotic_dose)
        mp_lay.addRow(self.mp_serum_pss)
        mp_lay.addRow(self.mp_serum_pgs, self.mp_serum_dose)
        mp_lay.addRow("Анатоксин:", self.mp_toxoid)
        mp_lay.addRow("Антидот:", self.mp_antidote)
        mp_lay.addRow(self.mp_analgesic, self.mp_analgesic_dose)
        mp_lay.addRow(self.mp_transfusion_blood)
        mp_lay.addRow(self.mp_transfusion_substitute)
        mp_lay.addRow(self.mp_immobilization)
        mp_lay.addRow(self.mp_bandage)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(mp_box)
        root.addWidget(scroll)

    def set_values(self, payload: dict[str, str], markers: list[dict]) -> None:  # type: ignore[type-arg]  # noqa: ARG002
        self.mp_antibiotic.setChecked(_truthy(payload.get("mp_antibiotic")))
        self.mp_antibiotic_dose.setText(str(payload.get("mp_antibiotic_dose") or ""))
        self.mp_serum_pss.setChecked(_truthy(payload.get("mp_serum_pss")))
        self.mp_serum_pgs.setChecked(_truthy(payload.get("mp_serum_pgs")))
        self.mp_serum_dose.setText(str(payload.get("mp_serum_dose") or ""))
        self.mp_toxoid.setText(str(payload.get("mp_toxoid") or ""))
        self.mp_antidote.setText(str(payload.get("mp_antidote") or ""))
        self.mp_analgesic.setChecked(_truthy(payload.get("mp_analgesic")))
        self.mp_analgesic_dose.setText(str(payload.get("mp_analgesic_dose") or ""))
        self.mp_transfusion_blood.setChecked(_truthy(payload.get("mp_transfusion_blood")))
        self.mp_transfusion_substitute.setChecked(_truthy(payload.get("mp_transfusion_substitute")))
        self.mp_immobilization.setChecked(_truthy(payload.get("mp_immobilization")))
        self.mp_bandage.setChecked(_truthy(payload.get("mp_bandage")))

    def collect(self) -> tuple[dict[str, str], list[dict]]:  # type: ignore[type-arg]
        return {
            "mp_antibiotic":             "1" if self.mp_antibiotic.isChecked() else "0",
            "mp_antibiotic_dose":        self.mp_antibiotic_dose.text().strip(),
            "mp_serum_pss":              "1" if self.mp_serum_pss.isChecked() else "0",
            "mp_serum_pgs":              "1" if self.mp_serum_pgs.isChecked() else "0",
            "mp_serum_dose":             self.mp_serum_dose.text().strip(),
            "mp_toxoid":                 self.mp_toxoid.text().strip(),
            "mp_antidote":               self.mp_antidote.text().strip(),
            "mp_analgesic":              "1" if self.mp_analgesic.isChecked() else "0",
            "mp_analgesic_dose":         self.mp_analgesic_dose.text().strip(),
            "mp_transfusion_blood":      "1" if self.mp_transfusion_blood.isChecked() else "0",
            "mp_transfusion_substitute": "1" if self.mp_transfusion_substitute.isChecked() else "0",
            "mp_immobilization":         "1" if self.mp_immobilization.isChecked() else "0",
            "mp_bandage":                "1" if self.mp_bandage.isChecked() else "0",
        }, []

    def set_locked(self, locked: bool) -> None:
        enabled = not locked
        for w in (
            self.mp_antibiotic,
            self.mp_antibiotic_dose,
            self.mp_serum_pss,
            self.mp_serum_pgs,
            self.mp_serum_dose,
            self.mp_toxoid,
            self.mp_antidote,
            self.mp_analgesic,
            self.mp_analgesic_dose,
            self.mp_transfusion_blood,
            self.mp_transfusion_substitute,
            self.mp_immobilization,
            self.mp_bandage,
        ):
            w.setEnabled(enabled)
