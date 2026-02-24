from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.services.exchange_service import ExchangeService
from app.ui.import_export.import_export_wizard import ImportExportWizard
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import connect_combo_autowidth, resize_columns_by_first_row


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
        actions_layout = QHBoxLayout(actions_box)
        wizard_btn = QPushButton("Открыть мастер импорта/экспорта")
        wizard_btn.clicked.connect(self._open_wizard)
        wizard_btn.setMinimumWidth(260)
        wizard_btn.setMaximumWidth(360)
        refresh_history_btn = QPushButton("Обновить историю пакетов")
        compact_button(refresh_history_btn)
        refresh_history_btn.clicked.connect(self._load_history)
        open_history_btn = QPushButton("Открыть файл")
        compact_button(open_history_btn)
        open_history_btn.clicked.connect(self._open_history_file)
        self._actions_panel = ResponsiveActionsPanel(min_button_width=190, max_columns=3)
        self._actions_panel.set_buttons([wizard_btn, refresh_history_btn, open_history_btn])
        self._actions_panel.set_compact(self.width() < 1420)
        actions_layout.addWidget(self._actions_panel)
        layout.addWidget(actions_box)

        history_box = QGroupBox("История пакетов обмена")
        history_layout = QVBoxLayout(history_box)
        filter_row = QHBoxLayout()
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
        filter_row.addWidget(QLabel("Направление"))
        filter_row.addWidget(self.direction_filter)
        filter_row.addWidget(self.query_filter)
        filter_row.addWidget(clear_filters_btn)
        history_layout.addLayout(filter_row)

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(
            ["Направление", "Формат", "Дата", "Пользователь", "SHA256", "Файл"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True)
        self.history_table.setMinimumHeight(260)
        self.history_table.itemDoubleClicked.connect(self._open_history_file)
        history_layout.addWidget(self.history_table)
        self.history_table.setColumnWidth(0, 170)
        layout.addWidget(history_box)

        layout.addStretch()
        self._load_history()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_actions_panel"):
            self._actions_panel.set_compact(self.width() < 1420)

    def _open_wizard(self) -> None:
        wizard = ImportExportWizard(
            exchange_service=self.exchange_service,
            session=self.session,
            table_labels=self._table_labels,
            parent=self,
        )
        wizard.exec()

    def _load_history(self) -> None:
        try:
            rows = self.exchange_service.list_packages(
                limit=100,
                direction=self.direction_filter.currentData(),
                query=self.query_filter.text().strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return
        self.history_table.clearContents()
        self.history_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            direction_key = str(r.direction or "")
            direction = {"export": "Экспорт", "import": "Импорт"}.get(direction_key, "")
            self.history_table.setItem(i, 0, QTableWidgetItem(direction))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(r.package_format or "")))
            created_text = r.created_at.strftime("%d.%m.%Y %H:%M") if r.created_at else ""
            self.history_table.setItem(i, 2, QTableWidgetItem(created_text))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(r.created_by or "")))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(r.sha256 or "")))
            self.history_table.setItem(i, 5, QTableWidgetItem(str(r.file_path or "")))
        resize_columns_by_first_row(self.history_table)
        resize_columns_by_first_row(self.history_table)
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
        file_path = path_item.text().strip()
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
