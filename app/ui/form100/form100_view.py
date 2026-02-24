from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_dto import Form100Filters, Form100StageCreateRequest
from app.application.services.form100_service import Form100Service
from app.application.services.reporting_service import ReportingService
from app.ui.form100.form100_editor import Form100Editor
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error, show_info
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel
from app.ui.widgets.table_utils import connect_combo_autowidth


class Form100View(QWidget):
    def __init__(
        self,
        *,
        form100_service: Form100Service,
        reporting_service: ReportingService | None,
        session: SessionContext,
        on_data_changed=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.form100_service = form100_service
        self.reporting_service = reporting_service
        self.session = session
        self.on_data_changed = on_data_changed
        self._rows_by_index: list[str] = []
        self._cards_preferred_widths = [58, 102, 84, 182, 94, 208, 102, 164]
        self._cards_min_widths = [50, 88, 72, 144, 84, 168, 86, 144]
        self._cards_floor_widths = [44, 72, 62, 112, 74, 132, 74, 122]
        self._cards_resize_priority = [3, 5, 7, 1, 4, 6, 2, 0]
        self._cards_min_total = sum(self._cards_min_widths) + 8
        self._editor_min_width = 520
        self._vertical_breakpoint_px = 1380
        self._build_ui()
        self.refresh_cards()

    def set_session(self, session: SessionContext) -> None:
        self.session = session

    def clear_context(self) -> None:
        self.editor.clear_form()

    def refresh_references(self) -> None:
        return

    def refresh_patient(self, _patient_id: int) -> None:
        return

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Форма 100")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        filter_box = QGroupBox("Поиск карточек")
        filter_layout = QVBoxLayout(filter_box)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("ФИО, подразделение, жетон, диагноз")
        self.status_filter = QComboBox()
        self.status_filter.addItem("Все", None)
        self.status_filter.addItem("Черновик", "DRAFT")
        self.status_filter.addItem("Подписано", "SIGNED")
        connect_combo_autowidth(self.status_filter, min_width=108, padding=22)
        self.status_filter.setMaximumWidth(130)

        refresh_btn = QPushButton("Найти")
        compact_button(refresh_btn, min_width=92, max_width=140)
        refresh_btn.clicked.connect(self.refresh_cards)
        new_btn = QPushButton("Новая карточка")
        compact_button(new_btn, min_width=96, max_width=160)
        new_btn.clicked.connect(self._new_card)
        save_btn = QPushButton("Сохранить")
        compact_button(save_btn, min_width=96, max_width=160)
        save_btn.clicked.connect(self._save_card)
        sign_btn = QPushButton("Подписать")
        compact_button(sign_btn, min_width=96, max_width=160)
        sign_btn.clicked.connect(self._sign_card)
        stage_btn = QPushButton("Добавить этап")
        compact_button(stage_btn, min_width=96, max_width=160)
        stage_btn.clicked.connect(self._add_stage)

        export_zip_btn = QPushButton("Экспорт ZIP")
        compact_button(export_zip_btn, min_width=96, max_width=160)
        export_zip_btn.clicked.connect(self._export_zip)
        import_zip_btn = QPushButton("Импорт ZIP")
        compact_button(import_zip_btn, min_width=96, max_width=160)
        import_zip_btn.clicked.connect(self._import_zip)
        export_pdf_btn = QPushButton("Экспорт PDF")
        compact_button(export_pdf_btn, min_width=96, max_width=160)
        export_pdf_btn.clicked.connect(self._export_pdf)

        search_row = QHBoxLayout()
        search_row.addWidget(self.query_input, 1)
        search_row.addWidget(self.status_filter)
        search_row.addWidget(refresh_btn)
        filter_layout.addLayout(search_row)

        self._actions_panel = ResponsiveActionsPanel(min_button_width=102, max_columns=7)
        self._actions_panel.set_buttons(
            [new_btn, save_btn, sign_btn, stage_btn, export_zip_btn, import_zip_btn, export_pdf_btn]
        )
        filter_layout.addWidget(self._actions_panel)
        root.addWidget(filter_box)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self.cards_table = QTableWidget(0, 8)
        self.cards_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Статус",
                "Версия",
                "ФИО",
                "Рожд.",
                "Подразделение",
                "Жетон",
                "Обновлено",
            ]
        )
        self.cards_table.verticalHeader().setVisible(False)
        self.cards_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cards_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.cards_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header = self.cards_table.horizontalHeader()
        header.setSectionsMovable(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.cards_table.itemSelectionChanged.connect(self._load_selected_card)
        self._splitter.addWidget(self.cards_table)

        self.editor = Form100Editor()
        self._splitter.addWidget(self.editor)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(0)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        root.addWidget(self._splitter)
        self._apply_cards_layout()

    def refresh_cards(self) -> None:
        try:
            filters = Form100Filters(
                query=self.query_input.text().strip() or None,
                status=self.status_filter.currentData(),
            )
            rows = self.form100_service.list_cards(filters=filters, limit=500, offset=0)
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return

        self._rows_by_index = [item.id for item in rows]
        self.cards_table.setRowCount(len(rows))
        for row_idx, item in enumerate(rows):
            full_name = " ".join(part for part in [item.last_name, item.first_name, item.middle_name] if part)
            self.cards_table.setItem(row_idx, 0, QTableWidgetItem(item.id))
            self.cards_table.setItem(row_idx, 1, QTableWidgetItem(_status_label(item.status)))
            self.cards_table.setItem(row_idx, 2, QTableWidgetItem(str(item.version)))
            self.cards_table.setItem(row_idx, 3, QTableWidgetItem(full_name))
            self.cards_table.setItem(row_idx, 4, QTableWidgetItem(item.birth_date.strftime("%d.%m.%Y")))
            self.cards_table.setItem(row_idx, 5, QTableWidgetItem(item.unit))
            self.cards_table.setItem(row_idx, 6, QTableWidgetItem(item.dog_tag_number or ""))
            self.cards_table.setItem(row_idx, 7, QTableWidgetItem(item.updated_at.strftime("%d.%m.%Y %H:%M")))
        self._apply_cards_table_column_widths()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_cards_layout()

    def _apply_cards_layout(self) -> None:
        self._apply_responsive_splitter_orientation()
        self._enforce_splitter_sizes()
        self._apply_cards_table_column_widths()
        self._actions_panel.set_compact(self.width() < 1400)

    def _apply_responsive_splitter_orientation(self) -> None:
        if not hasattr(self, "_splitter"):
            return
        should_be_vertical = self.width() < self._vertical_breakpoint_px
        target = Qt.Orientation.Vertical if should_be_vertical else Qt.Orientation.Horizontal
        if self._splitter.orientation() != target:
            self._splitter.setOrientation(target)
            self._splitter.setSizes([1, 1])

    def _apply_cards_table_column_widths(self) -> None:
        if not hasattr(self, "cards_table"):
            return
        if self.cards_table.columnCount() != len(self._cards_preferred_widths):
            return

        available = max(1, self.cards_table.viewport().width())
        preferred = self._cards_preferred_widths
        min_widths = self._cards_min_widths
        floor_widths = self._cards_floor_widths
        widths = min_widths.copy()

        min_total = sum(min_widths)
        pref_total = sum(preferred)
        if available >= pref_total:
            widths = preferred.copy()
            delta = available - pref_total
            widths[3] += int(delta * 0.40)  # ФИО
            widths[5] += int(delta * 0.35)  # Подразделение
            widths[7] += delta - int(delta * 0.40) - int(delta * 0.35)  # Обновлено
        elif available > min_total:
            widths = min_widths.copy()
            extra = available - min_total
            caps = [p - m for p, m in zip(preferred, min_widths, strict=False)]
            for idx in self._cards_resize_priority:
                if extra <= 0:
                    break
                add = min(caps[idx], extra)
                if add > 0:
                    widths[idx] += add
                    extra -= add
            if extra > 0:
                widths[7] += extra
        else:
            widths = min_widths.copy()
            overflow = min_total - available
            for idx in self._cards_resize_priority:
                if overflow <= 0:
                    break
                cut = min(widths[idx] - floor_widths[idx], overflow)
                if cut > 0:
                    widths[idx] -= cut
                    overflow -= cut
            if overflow > 0:
                widths[-1] = max(20, widths[-1] - overflow)

        for idx, width in enumerate(widths):
            self.cards_table.setColumnWidth(idx, max(12, width))

    def _enforce_splitter_sizes(self) -> None:
        if not hasattr(self, "_splitter"):
            return
        if self._splitter.orientation() == Qt.Orientation.Vertical:
            total = self._splitter.height()
            if total <= 0:
                return
            top = max(220, int(total * 0.32))
            bottom = max(320, total - top)
            if top + bottom != total:
                bottom = max(1, total - top)
            self._splitter.setSizes([top, bottom])
            return

        total = self._splitter.width()
        if total <= 0:
            return
        preferred_left = int(total * 0.46)
        max_left = max(320, total - self._editor_min_width)
        if max_left < 260:
            left = max(220, int(total * 0.34))
        else:
            left = min(max(self._cards_min_total, preferred_left), max_left)
        right = max(320, total - left)
        if left + right != total:
            right = max(1, total - left)
        self._splitter.setSizes([left, right])

    def _new_card(self) -> None:
        self.editor.clear_form()

    def _load_selected_card(self) -> None:
        row = self.cards_table.currentRow()
        if row < 0 or row >= len(self._rows_by_index):
            return
        card_id = self._rows_by_index[row]
        try:
            card = self.form100_service.get_card(card_id)
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))
            return
        self.editor.load_card(card)
        self.editor.set_read_only(card.status == "SIGNED")

    def _save_card(self) -> None:
        try:
            self.editor.validation_banner.clear_error()
            if self.editor.current_card is None:
                create_request = self.editor.build_create_request()
                card = self.form100_service.create_card(create_request, actor_id=self.session.user_id)
                show_info(self, f"Карточка создана: {card.id}")
            else:
                update_request = self.editor.build_update_request()
                card = self.form100_service.update_card(
                    self.editor.current_card.id,
                    update_request,
                    actor_id=self.session.user_id,
                    expected_version=self.editor.current_card.version,
                )
                show_info(self, "Карточка обновлена")
            self.editor.load_card(card)
            self.editor.set_read_only(card.status == "SIGNED")
            self.refresh_cards()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            self.editor.validation_banner.show_error(str(exc))

    def _sign_card(self) -> None:
        if self.editor.current_card is None:
            show_error(self, "Сначала выберите карточку")
            return
        try:
            request = self.editor.build_sign_request(signed_by=self.session.login, seal_applied=True)
            card = self.form100_service.sign_card(
                self.editor.current_card.id,
                request,
                actor_id=self.session.user_id,
                expected_version=self.editor.current_card.version,
            )
            self.editor.load_card(card)
            self.editor.set_read_only(True)
            self.refresh_cards()
            show_info(self, "Карточка подписана")
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _add_stage(self) -> None:
        if self.editor.current_card is None:
            show_error(self, "Сначала выберите карточку")
            return
        stage_name, ok = QInputDialog.getText(self, "Новый этап", "Название этапа:")
        if not ok or not stage_name.strip():
            return
        try:
            request = Form100StageCreateRequest(stage_name=stage_name.strip())
            self.form100_service.add_stage(
                self.editor.current_card.id,
                request,
                actor_id=self.session.user_id,
            )
            card = self.form100_service.get_card(self.editor.current_card.id)
            self.editor.load_card(card)
            self.refresh_cards()
            show_info(self, "Этап добавлен")
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _export_zip(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт Form100 ZIP",
            "form100_export.zip",
            "ZIP (*.zip)",
        )
        if not path:
            return
        try:
            card_id = self.editor.current_card.id if self.editor.current_card else None
            result = self.form100_service.export_package_zip(
                file_path=path,
                actor_id=self.session.user_id,
                card_id=card_id,
                exported_by=self.session.login,
            )
            show_info(self, f"Экспорт завершён: {result.get('path')}")
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _import_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт Form100 ZIP",
            "",
            "ZIP (*.zip)",
        )
        if not path:
            return
        try:
            result = self.form100_service.import_package_zip(
                file_path=path,
                actor_id=self.session.user_id,
                mode="merge",
            )
            summary = result.get("summary", {})
            show_info(
                self,
                (
                    f"Импорт завершён: rows={summary.get('rows_total', 0)}, "
                    f"+{summary.get('added', 0)} ~{summary.get('updated', 0)} "
                    f"-{summary.get('skipped', 0)}"
                ),
            )
            self.refresh_cards()
            if self.on_data_changed:
                self.on_data_changed()
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _export_pdf(self) -> None:
        if self.editor.current_card is None:
            show_error(self, "Сначала выберите карточку")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт Form100 PDF",
            f"form100_{self.editor.current_card.id}.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return
        try:
            if self.reporting_service is not None:
                result = self.reporting_service.export_form100_pdf(
                    card_id=self.editor.current_card.id,
                    file_path=Path(path),
                    actor_id=self.session.user_id,
                )
            else:
                result = self.form100_service.export_pdf(
                    card_id=self.editor.current_card.id,
                    file_path=Path(path),
                    actor_id=self.session.user_id,
                )
            show_info(self, f"PDF сформирован: {result.get('path')}")
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))


def _status_label(status: str) -> str:
    labels = {
        "DRAFT": "Черновик",
        "SIGNED": "Подписано",
    }
    return labels.get(status, status)
