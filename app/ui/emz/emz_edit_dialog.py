from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from app.container import Container
from app.ui.emz.emz_form import EmzForm


class EmzEditDialog(QDialog):
    def __init__(
        self,
        container: Container,
        patient_id: int,
        emr_case_id: int,
        on_saved: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.container = container
        self.patient_id = patient_id
        self.emr_case_id = emr_case_id
        self.on_saved = on_saved
        self.setWindowTitle("Редактирование ЭМЗ")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(1200, 980)
        self.setMinimumSize(1000, 800)

        layout = QVBoxLayout(self)
        title = QLabel("Редактирование ЭМЗ")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.form = EmzForm(
            container=self.container,
            on_case_selected=None,
            on_edit_patient=None,
            on_data_changed=self._on_saved,
            parent=self,
        )
        self.form.set_edit_mode(True)
        self.form.load_case(self.patient_id, self.emr_case_id)
        layout.addWidget(self.form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_saved(self) -> None:
        if self.on_saved:
            self.on_saved()
