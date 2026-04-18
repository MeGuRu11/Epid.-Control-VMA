from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.exceptions import AppError
from app.application.security import can_manage_exchange
from app.application.services.exchange_service import ExchangeService
from app.config import DATA_DIR
from app.ui.import_export.import_export_wizard import ImportExportWizard
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import error_text, show_error
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    make_readonly_item,
    resize_columns_to_content,
    set_table_read_only,
)

_HANDLED_IMPORT_EXPORT_ERRORS = (ValueError, RuntimeError, LookupError, TypeError, AppError, OSError)
_ALLOWED_ARTIFACT_DIRS = [DATA_DIR / "artifacts", DATA_DIR / "backups", DATA_DIR / "reports"]
_PACKAGE_FORMAT_LABELS = {
    "excel": "Excel",
    "csv": "CSV",
    "pdf": "PDF",
    "zip+excel": "ZIP + Excel",
    "form100+zip": "Form100 ZIP",
}


def _is_safe_path(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    return any(resolved.is_relative_to(base_dir.resolve(strict=False)) for base_dir in _ALLOWED_ARTIFACT_DIRS)


class ImportExportView(QWidget):
    def __init__(
        self,
        exchange_service: ExchangeService,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.exchange_service = exchange_service
        self.session = session
        self._build_ui()

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._sync_permissions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Импорт/экспорт данных")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self._table_labels = {
            "lab_sample": "Лаборатория",
            "sanitary_sample": "Санитария",
            "patients": "ЭМЗ (пациенты)",
            "emr_case": "ЭМЗ (госпитализации)",
        }

        actions_box = QGroupBox("Быстрые действия")
        actions_layout = QVBoxLayout(actions_box)
        wizard_btn = QPushButton("Открыть мастер импорта/экспорта")
        wizard_btn.setObjectName("primaryButton")
        wizard_btn.clicked.connect(self._open_wizard)
        compact_button(wizard_btn, min_width=132, max_width=300)
        self._wizard_btn = wizard_btn
        refresh_history_btn = QPushButton("Обновить историю пакетов")
        refresh_history_btn.setObjectName("secondaryButton")
        compact_button(refresh_history_btn)
        refresh_history_btn.clicked.connect(self._load_history)
        open_history_btn = QPushButton("Открыть файл")
        open_history_btn.setObjectName("secondaryButton")
        compact_button(open_history_btn)
        open_history_btn.clicked.connect(self._open_history_file)
        self._quick_actions_bar = QWidget()
        self._quick_actions_bar.setObjectName("sectionActionBar")
        self._quick_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._quick_actions_bar)
        self._quick_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._quick_actions_layout.setSpacing(10)

        self._quick_history_group = QWidget()
        self._quick_history_group.setObjectName("sectionActionGroup")
        history_group_layout = QHBoxLayout(self._quick_history_group)
        history_group_layout.setContentsMargins(0, 0, 0, 0)
        history_group_layout.setSpacing(8)
        history_group_layout.addWidget(refresh_history_btn)
        history_group_layout.addWidget(open_history_btn)

        self._quick_wizard_group = QWidget()
        self._quick_wizard_group.setObjectName("sectionActionGroup")
        wizard_layout = QHBoxLayout(self._quick_wizard_group)
        wizard_layout.setContentsMargins(0, 0, 0, 0)
        wizard_layout.addWidget(wizard_btn)

        self._quick_actions_layout.addWidget(self._quick_history_group)
        self._quick_actions_layout.addStretch()
        self._quick_actions_layout.addWidget(self._quick_wizard_group)
        actions_layout.addWidget(self._quick_actions_bar)
        self._update_quick_actions_layout()
        layout.addWidget(actions_box)

        history_box = QGroupBox("История пакетов обмена")
        history_layout = QVBoxLayout(history_box)
        self._history_filter_bar = QWidget()
        self._history_filter_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._history_filter_bar)
        self._history_filter_layout.setContentsMargins(0, 0, 0, 0)
        self._history_filter_layout.setSpacing(10)
        self.direction_filter = QComboBox()
        self.direction_filter.addItem("Выбрать", None)
        self.direction_filter.addItem("Экспорт", "export")
        self.direction_filter.addItem("Импорт", "import")
        connect_combo_autowidth(self.direction_filter)
        self.direction_filter.currentIndexChanged.connect(self._load_history)
        self.query_filter = QLineEdit()
        self.query_filter.setPlaceholderText("Поиск по пути или SHA256")
        self.query_filter.textChanged.connect(self._load_history)
        clear_filters_btn = QPushButton("Сбросить фильтры")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_filters)
        self._history_direction_group = QWidget()
        direction_layout = QHBoxLayout(self._history_direction_group)
        direction_layout.setContentsMargins(0, 0, 0, 0)
        direction_layout.setSpacing(8)
        direction_layout.addWidget(QLabel("Направление"))
        direction_layout.addWidget(self.direction_filter)

        self._history_query_group = QWidget()
        query_layout = QHBoxLayout(self._history_query_group)
        query_layout.setContentsMargins(0, 0, 0, 0)
        query_layout.setSpacing(8)
        query_layout.addWidget(self.query_filter)
        query_layout.addWidget(clear_filters_btn)

        self._history_filter_layout.addWidget(self._history_direction_group)
        self._history_filter_layout.addWidget(self._history_query_group, 1)
        history_layout.addWidget(self._history_filter_bar)
        self._update_history_filter_layout()

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(
            ["Направление", "Формат", "Дата", "Пользователь", "SHA256", "Файл"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setMinimumHeight(260)
        set_table_read_only(self.history_table)
        self.history_table.itemDoubleClicked.connect(self._open_history_file)
        history_layout.addWidget(self.history_table)
        self.history_table.setColumnWidth(0, 170)
        layout.addWidget(history_box)

        layout.addStretch()
        self._sync_permissions()
        self._load_history()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_quick_actions_layout"):
            self._update_quick_actions_layout()
        if hasattr(self, "_history_filter_layout"):
            self._update_history_filter_layout()

    def _update_quick_actions_layout(self) -> None:
        update_action_bar_direction(
            self._quick_actions_layout,
            self._quick_actions_bar,
            [self._quick_history_group, self._quick_wizard_group],
        )

    def _update_history_filter_layout(self) -> None:
        update_action_bar_direction(
            self._history_filter_layout,
            self._history_filter_bar,
            [self._history_direction_group, self._history_query_group],
        )

    def _open_wizard(self) -> None:
        if not can_manage_exchange(self.session.role):
            show_error(self, "Недостаточно прав для операций импорта/экспорта")
            return
        wizard = ImportExportWizard(
            exchange_service=self.exchange_service,
            session=self.session,
            table_labels=self._table_labels,
            parent=self,
        )
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self._load_history()

    def _sync_permissions(self) -> None:
        can_manage = can_manage_exchange(self.session.role)
        self._wizard_btn.setEnabled(can_manage)
        self._wizard_btn.setVisible(can_manage)

    def _load_history(self) -> None:
        try:
            rows = self.exchange_service.list_packages(
                limit=100,
                direction=self.direction_filter.currentData(),
                query=self.query_filter.text().strip() or None,
            )
        except _HANDLED_IMPORT_EXPORT_ERRORS as exc:
            show_error(self, error_text(exc, "?? ??????? ????????? ??????? ???????"))
            return
        self.history_table.clearContents()
        self.history_table.setRowCount(len(rows))
        for i, package in enumerate(rows):
            direction_key = str(package.direction or "")
            direction = {"export": "Экспорт", "import": "Импорт"}.get(direction_key, "Неизвестно")
            format_key = str(package.package_format or "")
            format_label = _PACKAGE_FORMAT_LABELS.get(format_key, format_key or "??????????")
            created_raw = package.created_at
            created_text = (
                created_raw.strftime("%d.%m.%Y %H:%M") if isinstance(created_raw, datetime) else "??????????"
            )
            actor_label = self.exchange_service.get_actor_label(cast(int | None, package.created_by))
            self.history_table.setItem(i, 0, make_readonly_item(direction))
            self.history_table.setItem(i, 1, make_readonly_item(format_label))
            self.history_table.setItem(i, 2, make_readonly_item(created_text))
            self.history_table.setItem(i, 3, make_readonly_item(actor_label))
            self.history_table.setItem(i, 4, make_readonly_item(str(package.sha256 or "—")))
            self.history_table.setItem(i, 5, make_readonly_item(str(package.file_path or "—")))
        resize_columns_to_content(self.history_table)
        self.history_table.setColumnWidth(0, 170)

    def _clear_filters(self) -> None:
        self.direction_filter.setCurrentIndex(0)
        self.query_filter.clear()
        self._load_history()

    def _open_history_file(self) -> None:
        row = self.history_table.currentRow()
        if row < 0:
            show_error(self, "Выберите строку в истории пакетов.")
            return
        path_item = self.history_table.item(row, 5)
        if not path_item or not path_item.text().strip():
            show_error(self, "Файл не указан.")
            return
        file_path = Path(path_item.text().strip())
        if not file_path.exists():
            show_error(self, "Файл не найден на диске.")
            return
        if not _is_safe_path(file_path):
            show_error(self, "Открытие файла запрещено: путь вне разрешённых директорий артефактов.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path.resolve(strict=False))))


