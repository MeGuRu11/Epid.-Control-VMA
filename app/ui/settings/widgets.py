"""Общие виджеты-помощники для построения вкладок настроек."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class FolderPickerRow(QWidget):
    """Строка выбора папки: подпись + поле + кнопки «Обзор» и «Открыть»."""

    def __init__(
        self,
        label: str,
        initial_path: str,
        on_open_in_explorer: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_open_in_explorer = on_open_in_explorer

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        title = QLabel(label)
        title.setObjectName("settingsFieldLabel")
        outer.addWidget(title)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self._edit = QLineEdit(initial_path)
        self._edit.setObjectName("settingsPathEdit")
        self._edit.setPlaceholderText("Каталог не задан — будет использован путь по умолчанию")
        self._edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(self._edit, 1)

        self._browse_btn = QToolButton()
        self._browse_btn.setObjectName("settingsBrowseButton")
        self._browse_btn.setText("Обзор…")
        self._browse_btn.setToolTip("Выбрать каталог")
        self._browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self._browse_btn, 0, Qt.AlignmentFlag.AlignRight)

        self._open_btn = QToolButton()
        self._open_btn.setObjectName("settingsOpenFolderButton")
        self._open_btn.setText("Открыть")
        self._open_btn.setToolTip("Открыть в проводнике")
        self._open_btn.clicked.connect(self._on_open)
        row.addWidget(self._open_btn, 0, Qt.AlignmentFlag.AlignRight)

        outer.addLayout(row)

    @property
    def value(self) -> str:
        return self._edit.text().strip()

    def set_value(self, value: str) -> None:
        self._edit.setText(value)

    def _on_browse(self) -> None:
        start_dir = self._edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Выберите каталог", start_dir)
        if chosen:
            self._edit.setText(chosen)

    def _on_open(self) -> None:
        path = self._edit.text().strip()
        if path:
            self._on_open_in_explorer(path)


def labeled_row(label: str, control: QWidget) -> QWidget:
    """Универсальная строка «название слева — контрол справа» (для совместимости)."""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    title = QLabel(label)
    title.setObjectName("settingsFieldLabel")
    title.setMinimumWidth(220)
    layout.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(control, 1)
    return container


def make_section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("settingsSectionTitle")
    return label


def make_section_hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("settingsSectionHint")
    label.setWordWrap(True)
    return label


def make_dialog_button(text: str, *, primary: bool = False) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("primaryButton" if primary else "secondaryButton")
    return button
