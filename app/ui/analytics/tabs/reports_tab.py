from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.analytics.report_history_helpers import (
    report_history_column_widths,
    to_report_history_view_row,
)
from app.ui.analytics.view_utils import make_section_frame
from app.ui.analytics.widgets.empty_state import EmptyState
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error
from app.ui.widgets.table_utils import (
    connect_combo_autowidth,
    resize_columns_to_content,
    set_table_read_only,
)

if TYPE_CHECKING:
    from app.ui.analytics.controller import AnalyticsController

VERIFY_OK_BG = QColor("#EAF3DE")
VERIFY_FAIL_BG = QColor("#FECACA")


class ReportsTab(QWidget):
    def __init__(self, controller: AnalyticsController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._build_ui()

    def refresh(self) -> None:
        self.load_report_history()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        history_box, history_layout = make_section_frame("История отчётов")

        filter_row = QHBoxLayout()
        self.report_type_filter = QComboBox()
        self.report_type_filter.addItem("Выбрать", None)
        self.report_type_filter.addItem("Аналитика", "analytics")
        connect_combo_autowidth(self.report_type_filter)
        self.report_type_filter.currentIndexChanged.connect(lambda _index: self.load_report_history())
        self.report_query_filter = QLineEdit()
        self.report_query_filter.setPlaceholderText("Поиск по пути артефакта, SHA256 или фильтрам")
        self.report_query_filter.textChanged.connect(lambda _text: self.load_report_history())
        clear_filters_btn = QPushButton("Сбросить фильтры")
        compact_button(clear_filters_btn)
        clear_filters_btn.clicked.connect(self._clear_report_history_filters)
        filter_row.addWidget(QLabel("Тип"))
        filter_row.addWidget(self.report_type_filter)
        filter_row.addWidget(self.report_query_filter)
        filter_row.addWidget(clear_filters_btn)
        history_layout.addLayout(filter_row)

        refresh_btn = QPushButton("Обновить историю")
        compact_button(refresh_btn)
        refresh_btn.clicked.connect(lambda _checked=False: self.load_report_history())
        verify_btn = QPushButton("Проверить хеши")
        compact_button(verify_btn)
        verify_btn.clicked.connect(lambda _checked=False: self.load_report_history(verify_hash=True))
        history_actions = QHBoxLayout()
        history_actions.addWidget(refresh_btn)
        history_actions.addWidget(verify_btn)
        history_actions.addStretch()
        history_layout.addLayout(history_actions)

        self.report_history_table = QTableWidget(0, 8)
        self.report_history_table.setHorizontalHeaderLabels(
            ["ID", "Тип", "Дата", "Пользователь", "Итого", "Верификация", "SHA256", "Артефакт"]
        )
        self.report_history_table.horizontalHeader().setStretchLastSection(True)
        self.report_history_table.verticalHeader().setVisible(False)
        self.report_history_table.setAlternatingRowColors(True)
        self.report_history_table.setMinimumHeight(260)
        set_table_read_only(self.report_history_table)
        self._empty_state = EmptyState("История отчётов пуста.", "Здесь появятся сформированные отчёты.")
        self._empty_state.setVisible(False)
        history_layout.addWidget(self._empty_state)
        history_layout.addWidget(self.report_history_table)
        self._apply_report_history_column_widths()

        layout.addWidget(history_box)
        layout.addStretch()

    def load_report_history(self, verify_hash: bool = False) -> None:
        try:
            rows = self.controller.load_report_history(
                report_type=self.report_type_filter.currentData(),
                query=self.report_query_filter.text().strip() or None,
                verify_hash=verify_hash,
            )
        except (LookupError, RuntimeError, ValueError, TypeError) as exc:
            show_error(self, str(exc))
            return

        self.report_history_table.clearContents()
        self.report_history_table.setRowCount(len(rows))
        self._empty_state.setVisible(len(rows) == 0)
        self.report_history_table.setVisible(len(rows) > 0)
        for i, item in enumerate(rows):
            row_data = to_report_history_view_row(item)
            row_bg = self._verification_background(row_data.verification_text)
            values = [
                row_data.report_run_id,
                row_data.report_type,
                row_data.created_text,
                row_data.created_by,
                row_data.total_text,
                row_data.verification_text,
                row_data.artifact_sha256,
                row_data.artifact_path,
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                if row_bg is not None:
                    table_item.setBackground(QBrush(row_bg))
                if column == 7:
                    table_item.setToolTip(str(value))
                self.report_history_table.setItem(i, column, table_item)
        resize_columns_to_content(self.report_history_table)
        self._apply_report_history_column_widths()

    @staticmethod
    def _verification_background(verification_text: str) -> QColor | None:
        text = verification_text.lower()
        if "ok" in text or ("совпадает" in text and "не совп" not in text):
            return VERIFY_OK_BG
        if "не совп" in text or "ошибка" in text or "не найден" in text:
            return VERIFY_FAIL_BG
        return None

    def _clear_report_history_filters(self) -> None:
        self.report_type_filter.setCurrentIndex(0)
        self.report_query_filter.clear()
        self.load_report_history()

    def _apply_report_history_column_widths(self) -> None:
        for column, width in report_history_column_widths().items():
            self.report_history_table.setColumnWidth(column, width)
