"""Form100ListPanel — диалог со списком карточек Формы 100."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import (
    Form100CardV2ListItemDto,
    Form100V2Filters,
)
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.ui.form100_v2.form100_wizard import Form100Wizard
from app.ui.widgets.notifications import error_text

_STATUS_LABELS: dict[str, str] = {
    "DRAFT":  "Черновик",
    "SIGNED": "Подписан",
}
_HANDLED_FORM100_ERRORS = (ValueError, RuntimeError, LookupError, TypeError, SQLAlchemyError)


class _PreviewPanel(QFrame):
    """Правая панель: превью выбранной карточки + кнопки действий."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("form100ListPreview")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(10)

        self._badge = QLabel()
        self._badge.setObjectName("form100ListBadge")
        self._badge.setProperty("tone", "empty")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setMinimumHeight(28)
        self._badge.setMaximumHeight(36)
        root.addWidget(self._badge)

        self._name_lbl = QLabel()
        self._name_lbl.setObjectName("form100ListName")
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._name_lbl)

        self._unit_lbl = QLabel()
        self._unit_lbl.setObjectName("form100ListUnit")
        self._unit_lbl.setWordWrap(True)
        self._unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._unit_lbl)

        sep = QFrame()
        sep.setObjectName("form100ListSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setMaximumHeight(1)
        root.addWidget(sep)

        self._diag_lbl = QLabel()
        self._diag_lbl.setObjectName("form100ListDiagnosis")
        self._diag_lbl.setWordWrap(True)
        root.addWidget(self._diag_lbl)

        self._date_lbl = QLabel()
        self._date_lbl.setObjectName("form100ListDate")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._date_lbl)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.open_btn = QPushButton("Открыть / Редактировать")
        self.open_btn.setEnabled(False)
        btn_row.addWidget(self.open_btn, 1)
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.setObjectName("ghost")
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

        self.clear()

    def _refresh_badge_style(self) -> None:
        style = self._badge.style()
        style.unpolish(self._badge)
        style.polish(self._badge)
        self._badge.update()

    def clear(self) -> None:
        self._badge.setText("")
        self._badge.setProperty("tone", "empty")
        self._refresh_badge_style()
        self._name_lbl.setText("Выберите карточку из списка")
        self._unit_lbl.setText("")
        self._diag_lbl.setText("")
        self._date_lbl.setText("")
        self.open_btn.setEnabled(False)

    def show_card(self, card: Form100CardV2ListItemDto) -> None:
        if card.is_archived:
            label = "Архив"
            tone = "archived"
        else:
            label = _STATUS_LABELS.get(card.status, card.status)
            tone = "signed" if card.status == "SIGNED" else "draft"

        self._badge.setText(label)
        self._badge.setProperty("tone", tone)
        self._refresh_badge_style()
        self._name_lbl.setText(card.main_full_name or "—")
        self._unit_lbl.setText(card.main_unit or "")
        diag = card.main_diagnosis or ""
        self._diag_lbl.setText(diag if diag else "(диагноз не указан)")
        self._date_lbl.setText(f"Обновлено: {card.updated_at.strftime('%d.%m.%Y %H:%M')}")
        self.open_btn.setEnabled(True)


class Form100ListPanel(QDialog):
    """Диалог со списком карточек Формы 100 для ЭМЗ."""

    def __init__(
        self,
        form100_service: Form100ServiceV2,
        session: SessionContext,
        patient_id: int | None = None,
        emr_case_id: int | None = None,
        on_data_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = form100_service
        self._session = session
        self._patient_id = patient_id
        self._emr_case_id = emr_case_id
        self._on_data_changed = on_data_changed
        self._cards: list[Form100CardV2ListItemDto] = []

        self.setWindowTitle("Форма 100")
        self.setMinimumSize(780, 560)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Заголовок ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        title = QLabel("Карточки Формы 100")
        title.setObjectName("pageTitle")
        hdr.addWidget(title)
        hdr.addStretch(1)
        self._btn_create = QPushButton("Создать форму")
        self._btn_create.clicked.connect(lambda: self._open_wizard(None))
        hdr.addWidget(self._btn_create)
        root.addLayout(hdr)

        # ── Сплиттер ─────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self._splitter = splitter

        # Левая: таблица
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(4)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Дата", "Статус", "ФИО", "Диагноз"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        self._table.setColumnWidth(2, 180)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemDoubleClicked.connect(lambda _: self._open_selected())
        left_lay.addWidget(self._table)
        splitter.addWidget(left)

        # Правая: превью
        self._preview = _PreviewPanel()
        splitter.addWidget(self._preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        # Кнопки из превью
        self._preview.open_btn.clicked.connect(self._open_selected)
        self._preview.close_btn.clicked.connect(self.reject)

        self._apply_initial_size()
        self._apply_responsive_layout()
        self._load_cards()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        if width < 1200:
            left, right = 62, 38
        elif width < 1600:
            left, right = 58, 42
        else:
            left, right = 55, 45
        total = max(1, self._splitter.width())
        self._splitter.setSizes(
            [
                max(260, total * left // 100),
                max(240, total * right // 100),
            ]
        )

    def _apply_initial_size(self) -> None:
        app = QApplication.instance()
        if app is None:
            self.resize(1120, 760)
            return
        assert isinstance(app, QApplication)
        screen = self.screen() or app.primaryScreen()
        if screen is None:
            self.resize(1120, 760)
            return

        geometry = screen.availableGeometry()
        min_width = min(900, max(780, geometry.width() - 80))
        min_height = min(620, max(540, geometry.height() - 80))
        max_width = max(min_width, geometry.width() - 24)
        max_height = max(min_height, geometry.height() - 24)
        target_width = max(min_width, min(1320, int(geometry.width() * 0.84), max_width))
        target_height = max(min_height, min(860, int(geometry.height() * 0.86), max_height))

        self.setMinimumSize(min_width, min_height)
        self.resize(target_width, target_height)

    # ── Данные ───────────────────────────────────────────────────────────────

    def _load_cards(self) -> None:
        if self._patient_id is not None:
            filters = Form100V2Filters(patient_id=self._patient_id)
        else:
            filters = Form100V2Filters(emr_case_id=self._emr_case_id)
        try:
            self._cards = self._service.list_cards(filters, limit=200)
        except _HANDLED_FORM100_ERRORS as exc:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось загрузить карточки:\n"
                f"{error_text(exc, 'Операция не выполнена')}",
            )
            self._cards = []
        self._rebuild_table()

    def _rebuild_table(self) -> None:
        self._table.setRowCount(0)
        self._preview.clear()
        for card in self._cards:
            row = self._table.rowCount()
            self._table.insertRow(row)

            date_str = card.updated_at.strftime("%d.%m.%Y %H:%M")
            if card.is_archived:
                status_text = "Архив"
            else:
                status_text = _STATUS_LABELS.get(card.status, card.status)

            items = [
                QTableWidgetItem(date_str),
                QTableWidgetItem(status_text),
                QTableWidgetItem(card.main_full_name or "—"),
                QTableWidgetItem(card.main_diagnosis or "—"),
            ]
            items[0].setData(Qt.ItemDataRole.UserRole, card.id)
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(row, col, item)

    # ── Выбор ────────────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        card = self._selected_list_item()
        if card is None:
            self._preview.clear()
        else:
            self._preview.show_card(card)

    def _selected_list_item(self) -> Form100CardV2ListItemDto | None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self._table.item(row, 0)
        if item is None:
            return None
        card_id: str = item.data(Qt.ItemDataRole.UserRole)
        return next((c for c in self._cards if c.id == card_id), None)

    def _open_selected(self) -> None:
        card_item = self._selected_list_item()
        if card_item is None:
            return
        self._open_wizard(card_item.id)

    # ── Мастер ───────────────────────────────────────────────────────────────

    def _open_wizard(self, card_id: str | None) -> None:
        from app.application.dto.form100_v2_dto import Form100CardV2Dto

        if card_id is None and self._emr_case_id is None:
            QMessageBox.warning(
                self,
                "Форма 100",
                "Для создания карточки выберите госпитализацию.",
            )
            return

        card: Form100CardV2Dto | None = None
        if card_id is not None:
            try:
                card = self._service.get_card(card_id)
            except _HANDLED_FORM100_ERRORS as exc:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось загрузить карточку:\n"
                    f"{error_text(exc, 'Операция не выполнена')}",
                )
                return

        wizard = Form100Wizard(
            form100_service=self._service,
            session=self._session,
            card=card,
            emr_case_id=self._emr_case_id,
            parent=self,
        )
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self._load_cards()
            if self._on_data_changed:
                self._on_data_changed()


