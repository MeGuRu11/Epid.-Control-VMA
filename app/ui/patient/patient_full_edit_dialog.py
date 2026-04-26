from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from app.application.dto.auth_dto import SessionContext
from app.container import Container
from app.ui.emz.emz_form import EmzForm
from app.ui.widgets.dialog_utils import localize_button_box


class PatientFullEditDialog(QDialog):
    """Диалог редактирования ЭМЗ из карточки пациента."""

    def __init__(
        self,
        *,
        container: Container,
        session: SessionContext,
        patient_id: int,
        emr_case_id: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.container = container
        self.session = session
        self.patient_id = patient_id
        self.emr_case_id = emr_case_id
        self.was_saved = False

        self.setWindowTitle("Редактирование ЭМЗ")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(1200, 900)
        self.setMinimumSize(1000, 760)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Редактирование ЭМЗ")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"Пациент ID: {self.patient_id} · ЭМЗ ID: {self.emr_case_id}")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        self.form = EmzForm(
            container=self.container,
            session=self.session,
            on_case_selected=None,
            on_edit_patient=None,
            on_data_changed=self._on_saved,
            parent=self,
        )
        self.form.set_edit_mode(True)
        self.form.load_case(self.patient_id, self.emr_case_id, emit_context=False)
        layout.addWidget(self.form, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        localize_button_box(buttons)
        buttons.rejected.connect(self._finish)
        layout.addWidget(buttons)

    def _on_saved(self) -> None:
        self.was_saved = True

    def reject(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if self.was_saved:
            self.accept()
            return
        super().reject()
