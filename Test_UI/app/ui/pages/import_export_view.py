from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.services.exchange_service import ExchangeService
from ..widgets.toast import show_toast


class ImportExportView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self._svc = ExchangeService(engine, session_ctx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Импорт / Экспорт")
        title.setObjectName("title")
        layout.addWidget(title)

        actions = QHBoxLayout()
        self.btn_export = QPushButton("Сформировать пакет")
        self.btn_export.clicked.connect(self.export_package)
        self.btn_import = QPushButton("Импортировать пакет")
        self.btn_import.setObjectName("secondary")
        self.btn_import.clicked.connect(self.import_package)
        self.btn_refresh = QPushButton("Обновить историю")
        self.btn_refresh.setObjectName("ghost")
        self.btn_refresh.clicked.connect(self.refresh)
        actions.addWidget(self.btn_export)
        actions.addWidget(self.btn_import)
        actions.addWidget(self.btn_refresh)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Direction", "Format", "File", "SHA256", "Created", "Notes"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        rows = self._svc.history()
        self.table.setRowCount(len(rows))
        for idx, row in enumerate(rows):
            self.table.setItem(idx, 0, QTableWidgetItem(str(row.id)))
            self.table.setItem(idx, 1, QTableWidgetItem(row.direction))
            self.table.setItem(idx, 2, QTableWidgetItem(row.package_format))
            self.table.setItem(idx, 3, QTableWidgetItem(row.file_path))
            self.table.setItem(idx, 4, QTableWidgetItem(row.sha256[:12] + "..."))
            self.table.setItem(idx, 5, QTableWidgetItem(row.created_at.isoformat(timespec="seconds")))
            self.table.setItem(idx, 6, QTableWidgetItem(row.notes or ""))

    def export_package(self):
        path = self._svc.export_package()
        show_toast(self.window(), f"Пакет экспорта создан: {path.name}", "success")
        self.refresh()

    def import_package(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать пакет", "", "ZIP/JSON (*.zip *.json);;All files (*)")
        if not path:
            return
        try:
            self._svc.import_package(path)
        except Exception as exc:
            show_toast(self.window(), f"Ошибка импорта: {exc}", "error")
            return
        show_toast(self.window(), "Пакет импортирован в журнал.", "success")
        self.refresh()
