from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class SampleHeader(QFrame):
    """Sticky-header с кратким контекстом пробы."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sampleHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        text_block = QWidget(self)
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel("Проба", self)
        self.title_label.setObjectName("sampleHeaderTitle")
        self.context_label = QLabel("", self)
        self.context_label.setObjectName("sampleHeaderMeta")
        self.context_label.setWordWrap(True)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.context_label)

        layout.addWidget(text_block, 1)

    def set_lab_context(self, sample_id: int | None, lab_no: str, patient: str) -> None:
        """Обновить контекст лабораторной пробы."""
        title = lab_no.strip() if lab_no else ""
        if title:
            self.title_label.setText(f"Лабораторная проба {title}")
        elif sample_id is not None:
            self.title_label.setText(f"Лабораторная проба #{sample_id}")
        else:
            self.title_label.setText("Новая лабораторная проба")

        patient_text = patient.strip() if patient else "не указан"
        self.context_label.setText(f"Пациент: {patient_text}")

    def set_sanitary_context(self, sample_id: int | None, sampling_point: str) -> None:
        """Обновить контекст санитарной пробы."""
        if sample_id is not None:
            self.title_label.setText(f"Санитарная проба #{sample_id}")
        else:
            self.title_label.setText("Новая санитарная проба")

        point = sampling_point.strip() if sampling_point else "не указана"
        self.context_label.setText(f"Точка отбора: {point}")
