"""Form100View — главная страница раздела «Форма 100».

Компоновка:
  QSplitter (горизонтальный)
  ├── LEFT (~300 px) — Панель пациента
  │   ├── QGroupBox «Пациент» (ID, ID госпитализации + инфо из последней карточки)
  │   ├── QGroupBox «Быстрые действия» (создать / открыть / PDF / архивировать)
  │   └── QGroupBox «Последняя карточка» (статус-бейдж, ФИО, диагноз, мини-схема тела)
  └── RIGHT — История карточек
      ├── QTableWidget (Дата | Статус | Подписант | ID)
      └── Нижние кнопки (Новая редакция | Экспорт ZIP | Импорт ZIP | Очистить | Обновить)
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...application.services.form100_service import Form100Service
from ...infrastructure.form100 import empty_form100_payload
from ..widgets.toast import show_toast
from .form100_wizard import Form100Wizard


# ── Вспомогательный виджет: мини-схема тела ──────────────────────────────────

class _BodyMapPreview(QWidget):
    _colors = {
        "WOUND_X":    QColor("#C0392B"),
        "BURN_HATCH": QColor("#E67E22"),
        "AMPUTATION": QColor("#943126"),
        "TOURNIQUET": QColor("#9C640C"),
        "NOTE_PIN":   QColor("#1F77B4"),
    }

    def __init__(self, markers: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._markers = markers
        self.setMinimumHeight(140)

    def set_markers(self, markers: list[dict]) -> None:
        self._markers = markers
        self.update()

    def paintEvent(self, event) -> None:
        _ = event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#FFFDF8"))
        p.setPen(QPen(QColor("#D7CEC4"), 1))
        p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

        w = float(self.width())
        h = float(self.height())
        front = QRectF(w * 0.10, h * 0.20, w * 0.34, h * 0.70)
        back  = QRectF(w * 0.56, h * 0.20, w * 0.34, h * 0.70)

        guide_pen = QPen(QColor(111, 185, 173, 120), 1, Qt.PenStyle.DashLine)
        p.setPen(guide_pen)
        p.drawRoundedRect(front, 10, 10)
        p.drawRoundedRect(back, 10, 10)
        p.setPen(QPen(QColor("#6A6A68"), 1))
        p.drawText(int(front.left()), int(h * 0.14), "ПЕРЕД")
        p.drawText(int(back.left()), int(h * 0.14), "ЗАД")

        for marker in self._markers:
            view = str(marker.get("view") or marker.get("zone") or "front")
            rect = back if view == "back" else front
            try:
                x = max(0.0, min(1.0, float(marker.get("x") or 0)))
                y = max(0.0, min(1.0, float(marker.get("y") or 0)))
            except (TypeError, ValueError):
                continue
            annotation_type = str(
                marker.get("annotation_type") or marker.get("kind") or "WOUND_X"
            )
            color = self._colors.get(annotation_type, QColor("#1F77B4"))
            px = rect.left() + x * rect.width()
            py = rect.top() + y * rect.height()
            p.setPen(QPen(color, 2))
            p.setBrush(color)
            p.drawEllipse(int(px - 3), int(py - 3), 6, 6)


# ── Диалог импорта ZIP ────────────────────────────────────────────────────────

class _ImportZipDialog(QDialog):
    def __init__(
        self,
        preview: dict,
        selected_card_id: int | None,
        selected_status: str | None,
        context_patient_id: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Импорт Формы 100 (ZIP)")
        self.setMinimumWidth(560)
        self._selected_card_id = selected_card_id
        self._selected_status = selected_status or ""

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        summary = QLabel(
            f"Файл: {preview.get('file_path', '')}\n"
            f"SHA256: {preview.get('sha256', '')[:16]}...\n"
            f"Источник: card={preview.get('source_card_id', '-')}, "
            f"patient={preview.get('source_patient_id', '-')}, "
            f"case={preview.get('source_case_id', '-')}, "
            f"status={preview.get('source_status', '-')}\n"
            f"Заполненных полей: {preview.get('filled_fields', 0)} | "
            f"Меток: {preview.get('markers', 0)}"
        )
        summary.setWordWrap(True)
        summary.setObjectName("muted")
        root.addWidget(summary)

        root.addWidget(QLabel("Режим импорта"))
        self.mode_combo = QComboBox()
        if selected_card_id is not None and self._selected_status == "DRAFT":
            self.mode_combo.addItem("Слить в выбранную DRAFT-карточку", "merge")
        if selected_card_id is not None:
            self.mode_combo.addItem("Новая редакция выбранной карточки", "revision")
        self.mode_combo.addItem("Новая карточка", "new")
        root.addWidget(self.mode_combo)

        root.addWidget(QLabel("patient_id для новой карточки"))
        self.patient_id_edit = QLineEdit()
        default_patient = context_patient_id
        if default_patient is None:
            src_patient = preview.get("source_patient_id")
            if isinstance(src_patient, int):
                default_patient = src_patient
            elif isinstance(src_patient, str) and src_patient.strip().isdigit():
                default_patient = int(src_patient.strip())
        if default_patient is not None:
            self.patient_id_edit.setText(str(default_patient))
        self.patient_id_edit.setPlaceholderText("Введите patient_id")
        root.addWidget(self.patient_id_edit)

        root.addWidget(QLabel("Предпросмотр полей"))
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        lines = preview.get("preview_lines")
        if isinstance(lines, list):
            self.preview_text.setPlainText("\n".join(str(x) for x in lines))
        root.addWidget(self.preview_text, 1)

        root.addWidget(QLabel("Предпросмотр bodymap"))
        marker_rows = preview.get("markers_data")
        marker_list = marker_rows if isinstance(marker_rows, list) else []
        self._bmp = _BodyMapPreview(marker_list, self)
        root.addWidget(self._bmp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.mode_combo.currentIndexChanged.connect(self._sync_mode_state)
        self._sync_mode_state()

    def _sync_mode_state(self) -> None:
        self.patient_id_edit.setEnabled(self.mode() == "new")

    def mode(self) -> str:
        value = self.mode_combo.currentData()
        if isinstance(value, str) and value in {"new", "revision", "merge"}:
            return value
        return "new"

    def patient_id(self) -> int | None:
        raw = self.patient_id_edit.text().strip()
        if not raw or not raw.isdigit():
            return None
        return int(raw)


# ── Главное представление ─────────────────────────────────────────────────────

class Form100View(QWidget):
    """Главная страница Формы 100: панель пациента + история карточек."""

    def __init__(self, engine, session_ctx) -> None:
        super().__init__()
        self._svc = Form100Service(engine, session_ctx)
        self._context_patient_id: int | None = None
        self._context_case_id: int | None = None
        self._current_card_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Заголовок ─────────────────────────────────────────────────────
        title = QLabel("Форма 100")
        title.setObjectName("title")
        root.addWidget(title)


        # ── Сплиттер ──────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        # ═══════════════════════════════════════════════════════════════
        # LEFT: панель пациента
        # ═══════════════════════════════════════════════════════════════
        left_panel = QFrame()
        left_panel.setObjectName("card")
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(360)
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(12, 12, 12, 12)
        left_lay.setSpacing(10)

        # — Пациент ——————————————————————————————————————————————————
        patient_box = QGroupBox("Пациент")
        patient_box_lay = QVBoxLayout(patient_box)
        patient_box_lay.setContentsMargins(10, 8, 10, 8)
        patient_box_lay.setSpacing(3)

        self.lbl_patient_name = QLabel("—")
        font = self.lbl_patient_name.font()
        font.setBold(True)
        self.lbl_patient_name.setFont(font)
        self.lbl_patient_name.setWordWrap(True)

        self.lbl_patient_rank = QLabel()
        self.lbl_patient_rank.setObjectName("muted")
        self.lbl_patient_id = QLabel("ID пациента: —")
        self.lbl_patient_id.setObjectName("muted")
        self.lbl_case_id = QLabel("Госпитализация: —")
        self.lbl_case_id.setObjectName("muted")

        patient_box_lay.addWidget(self.lbl_patient_name)
        patient_box_lay.addWidget(self.lbl_patient_rank)
        patient_box_lay.addWidget(self.lbl_patient_id)
        patient_box_lay.addWidget(self.lbl_case_id)
        left_lay.addWidget(patient_box)

        # — Быстрые действия ——————————————————————————————————————————
        actions_box = QGroupBox("Быстрые действия")
        actions_lay = QVBoxLayout(actions_box)
        actions_lay.setContentsMargins(10, 8, 10, 8)
        actions_lay.setSpacing(6)

        self.btn_new = QPushButton("Создать новую Ф100")
        self.btn_new.clicked.connect(self._create_card)

        self.btn_open = QPushButton("Открыть в мастере")
        self.btn_open.setObjectName("secondary")
        self.btn_open.clicked.connect(self._open_wizard)

        self.btn_export_pdf = QPushButton("Экспорт PDF")
        self.btn_export_pdf.setObjectName("secondary")
        self.btn_export_pdf.clicked.connect(self._export_pdf)

        self.btn_archive = QPushButton("Архивировать")
        self.btn_archive.setObjectName("secondary")
        self.btn_archive.clicked.connect(self._archive_card)

        actions_lay.addWidget(self.btn_new)
        actions_lay.addWidget(self.btn_open)
        actions_lay.addWidget(self.btn_export_pdf)
        actions_lay.addWidget(self.btn_archive)
        left_lay.addWidget(actions_box)

        # — Выбранная карточка (мини-превью) ——————————————————————————
        preview_box = QGroupBox("Выбранная карточка")
        preview_lay = QVBoxLayout(preview_box)
        preview_lay.setContentsMargins(10, 8, 10, 8)
        preview_lay.setSpacing(4)

        self.lbl_preview_status = QLabel("—")
        self.lbl_preview_name = QLabel()
        self.lbl_preview_name.setObjectName("muted")
        self.lbl_preview_name.setWordWrap(True)
        self.lbl_preview_diag = QLabel()
        self.lbl_preview_diag.setObjectName("muted")
        self.lbl_preview_diag.setWordWrap(True)

        self._body_preview = _BodyMapPreview([], self)
        self.lbl_preview_date = QLabel()
        self.lbl_preview_date.setObjectName("muted")

        preview_lay.addWidget(self.lbl_preview_status)
        preview_lay.addWidget(self.lbl_preview_name)
        preview_lay.addWidget(self.lbl_preview_diag)
        preview_lay.addWidget(self._body_preview)
        preview_lay.addWidget(self.lbl_preview_date)
        left_lay.addWidget(preview_box, 1)

        splitter.addWidget(left_panel)

        # ═══════════════════════════════════════════════════════════════
        # RIGHT: история карточек
        # ═══════════════════════════════════════════════════════════════
        right_panel = QFrame()
        right_panel.setObjectName("card")
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(10)

        history_lbl = QLabel("История карточек")
        history_lbl.setObjectName("sectionTitle")
        right_lay.addWidget(history_lbl)

        hint = QLabel(
            "Двойной клик по строке — открыть в мастере.  "
            "Выберите пациента и госпитализацию, чтобы активировать «Создать»."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        right_lay.addWidget(hint)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Дата создания", "Статус", "Подписант", "ФИО (корешок)", "ID"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(lambda _r, _c: self._open_wizard())
        right_lay.addWidget(self.table, 1)

        # — Нижние кнопки ——————————————————————————————————————————————
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.btn_revision = QPushButton("Новая редакция")
        self.btn_revision.setObjectName("secondary")
        self.btn_revision.clicked.connect(self._create_revision)

        self.btn_export_zip = QPushButton("Экспорт ZIP")
        self.btn_export_zip.setObjectName("secondary")
        self.btn_export_zip.clicked.connect(self._export_zip)

        self.btn_import_zip = QPushButton("Импорт ZIP")
        self.btn_import_zip.setObjectName("secondary")
        self.btn_import_zip.clicked.connect(self._import_zip)

        self.btn_clear = QPushButton("Очистить карточку")
        self.btn_clear.setObjectName("danger")
        self.btn_clear.clicked.connect(self._clear_card)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setObjectName("ghost")
        self.btn_refresh.clicked.connect(self.refresh)

        bottom_row.addWidget(self.btn_revision)
        bottom_row.addWidget(self.btn_export_zip)
        bottom_row.addWidget(self.btn_import_zip)
        bottom_row.addWidget(self.btn_clear)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.btn_refresh)
        right_lay.addLayout(bottom_row)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 900])

        self._update_button_states()
        self.refresh()

    # ── Контекст ─────────────────────────────────────────────────────────────

    def set_context(self, patient_id: int | None, case_id: int | None) -> None:
        self._context_patient_id = patient_id
        self._context_case_id = case_id
        self._current_card_id = None
        pat = str(patient_id) if patient_id is not None else "-"
        cas = str(case_id) if case_id is not None else "-"
        self.lbl_patient_id.setText(f"ID пациента: {pat}")
        self.lbl_case_id.setText(f"Госпитализация: {cas}")
        self.refresh()

    def clear_context(self) -> None:
        self.set_context(None, None)

    # ── Обновление таблицы ───────────────────────────────────────────────────

    def refresh(self) -> None:
        selected_id = self._current_card_id
        rows = self._svc.list(
            patient_id=self._context_patient_id,
            emr_case_id=self._context_case_id,
        )

        self.table.setRowCount(len(rows))
        selected_row: int | None = None

        for idx, row in enumerate(rows):
            items = [
                QTableWidgetItem(row.created_at.isoformat(timespec="seconds")),
                QTableWidgetItem(row.status),
                QTableWidgetItem(row.signed_by or ""),
                QTableWidgetItem(""),  # ФИО — заполняется при выборе строки
                QTableWidgetItem(str(row.id)),
            ]
            for col, item in enumerate(items):
                self.table.setItem(idx, col, item)
            self._apply_status_style(items, row.status)
            if selected_id is not None and row.id == selected_id:
                selected_row = idx

        if rows:
            if selected_row is not None:
                target_row = selected_row
            else:
                target_row = 0
                for idx, row in enumerate(rows):
                    if row.status != "ARCHIVED":
                        target_row = idx
                        break
            self.table.selectRow(target_row)
        else:
            self.table.clearSelection()
            self._current_card_id = None
            self._clear_preview()
            self._clear_patient_info()

        self._update_button_states()

    def _selected_card_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 4)  # column 4 = ID
        if item is None:
            return None
        return int(item.text())

    @staticmethod
    def _apply_status_style(items: list[QTableWidgetItem], status: str) -> None:
        if status == "SIGNED":
            bg = QColor(230, 246, 234)
        elif status == "ARCHIVED":
            bg = QColor(241, 241, 238)
        else:
            bg = QColor(242, 255, 252)
        for item in items:
            item.setBackground(bg)

    # ── Обновление левой панели ───────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        card_id = self._selected_card_id()
        self._current_card_id = card_id
        if card_id is None:
            self._clear_preview()
            self._clear_patient_info()
            self._update_button_states()
            return

        row = self._svc.get(card_id)
        payload = self._svc.get_payload(card_id)
        markers = self._svc.get_bodymap(card_id)

        # Обновить панель «Пациент»
        # Корешок имеет приоритет, иначе берём из основного бланка
        full_name = str(payload.get("stub_full_name") or payload.get("main_full_name") or "—")
        rank      = str(payload.get("stub_rank")      or payload.get("main_rank")      or "")
        id_tag    = str(payload.get("stub_id_tag")    or payload.get("main_id_tag")    or "")
        self.lbl_patient_name.setText(full_name)
        info_parts = [p for p in (rank, id_tag) if p]
        self.lbl_patient_rank.setText(" | ".join(info_parts) if info_parts else "")

        # Обновить мини-превью
        status = row.status if row else "—"
        self.lbl_preview_status.setText(f"Статус: {status}")
        diagnosis = str(
            payload.get("main_diagnosis") or payload.get("stub_diagnosis") or ""
        )
        self.lbl_preview_diag.setText(
            (diagnosis[:80] + "…") if len(diagnosis) > 80 else diagnosis
        )
        self.lbl_preview_name.setText(full_name if full_name != "—" else "")
        self._body_preview.set_markers(markers)
        date_str = row.created_at.isoformat(timespec="seconds") if row else ""
        signed_by = (row.signed_by or "") if row else ""
        self.lbl_preview_date.setText(
            f"{date_str}{'  (' + signed_by + ')' if signed_by else ''}"
        )

        # Заполнить ФИО в строке таблицы (ленивая загрузка)
        cur_row = self.table.currentRow()
        if cur_row >= 0:
            name_item = self.table.item(cur_row, 3)
            if name_item is not None and not name_item.text():
                name_item.setText(full_name if full_name != "—" else "")

        # Передаём row чтобы не делать повторный DB-запрос
        self._update_button_states(row)

    def _clear_preview(self) -> None:
        self.lbl_preview_status.setText("—")
        self.lbl_preview_name.setText("")
        self.lbl_preview_diag.setText("")
        self._body_preview.set_markers([])
        self.lbl_preview_date.setText("")

    def _clear_patient_info(self) -> None:
        self.lbl_patient_name.setText("—")
        self.lbl_patient_rank.setText("")

    def _update_button_states(self, row=None) -> None:
        """Обновить доступность кнопок.

        Параметр row — уже загруженный объект Form100CardRow (из _on_selection_changed).
        Если не передан — загружается из сервиса при необходимости.
        """
        has_context = (
            self._context_patient_id is not None
            and self._context_case_id is not None
        )
        card_id = self._selected_card_id()
        has_card = card_id is not None

        if row is None and card_id is not None:
            row = self._svc.get(card_id)
        is_archived = bool(row and row.status == "ARCHIVED")
        is_draft = bool(row and row.status == "DRAFT")

        self.btn_new.setEnabled(has_context)
        self.btn_open.setEnabled(has_card)
        self.btn_export_pdf.setEnabled(has_card)
        self.btn_archive.setEnabled(has_card and not is_archived)
        self.btn_revision.setEnabled(has_card)
        self.btn_export_zip.setEnabled(has_card)
        self.btn_clear.setEnabled(has_card and is_draft)

    # ── Действия с карточкой ─────────────────────────────────────────────────

    def _create_card(self) -> None:
        if self._context_patient_id is None or self._context_case_id is None:
            show_toast(
                self.window(),
                "Для создания формы выберите пациента и госпитализацию.",
                "warning",
            )
            return
        new_id = self._svc.create(
            patient_id=self._context_patient_id,
            emr_case_id=self._context_case_id,
            payload=empty_form100_payload(),
        )
        self._current_card_id = new_id
        payload = self._svc.get_payload(new_id)
        markers = self._svc.get_bodymap(new_id)
        wizard = Form100Wizard(
            self._svc, new_id, payload, markers,
            is_locked=False, card_status="DRAFT",
            parent=self,
        )
        wizard.exec()
        self.refresh()

    def _open_wizard(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        row = self._svc.get(card_id)
        if row is None:
            show_toast(self.window(), "Карточка не найдена.", "error")
            return
        payload = self._svc.get_payload(card_id)
        markers = self._svc.get_bodymap(card_id)
        is_locked = row.status in {"SIGNED", "ARCHIVED"}
        wizard = Form100Wizard(
            self._svc, card_id, payload, markers,
            is_locked=is_locked, card_status=row.status,
            parent=self,
        )
        wizard.exec()
        self.refresh()

    def _archive_card(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        if self._svc.archive(card_id):
            self.refresh()
            show_toast(self.window(), "Карточка архивирована.", "success")
        else:
            show_toast(self.window(), "Карточка не найдена.", "error")

    def _create_revision(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        new_id = self._svc.create_revision(card_id)
        if new_id is None:
            show_toast(self.window(), "Карточка не найдена.", "error")
            return
        self._current_card_id = new_id
        self.refresh()
        show_toast(self.window(), f"Создана новая редакция: {new_id}", "success")

    def _export_pdf(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        try:
            path = self._svc.export_pdf(card_id)
        except Exception as exc:
            show_toast(self.window(), f"Ошибка экспорта PDF: {exc}", "error")
            return
        show_toast(self.window(), f"PDF сохранён: {path.name}", "success")

    def _export_zip(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        try:
            path = self._svc.export_zip(card_id)
        except Exception as exc:
            show_toast(self.window(), f"Ошибка экспорта ZIP: {exc}", "error")
            return
        show_toast(self.window(), f"ZIP сохранён: {path.name}", "success")

    def _clear_card(self) -> None:
        card_id = self._selected_card_id()
        if card_id is None:
            show_toast(self.window(), "Выберите карточку в таблице.", "warning")
            return
        row = self._svc.get(card_id)
        if row is None:
            show_toast(self.window(), "Карточка не найдена.", "error")
            return
        if row.status in {"SIGNED", "ARCHIVED"}:
            show_toast(
                self.window(),
                "Нельзя очищать подписанную/архивированную карточку.",
                "error",
            )
            return
        answer = QMessageBox.question(
            self,
            "Очистка карточки",
            "Очистить все поля и метки текущей карточки?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not self._svc.update_payload(card_id, empty_form100_payload()):
            show_toast(self.window(), "Не удалось очистить поля карточки.", "error")
            return
        if not self._svc.update_bodymap(card_id, []):
            show_toast(self.window(), "Не удалось очистить метки карточки.", "error")
            return
        self.refresh()
        show_toast(self.window(), "Карточка очищена.", "success")

    def _import_zip(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт карточки Form100", "", "ZIP (*.zip)"
        )
        if not file_path:
            return
        selected_id = self._selected_card_id()
        selected_status: str | None = None
        if selected_id is not None:
            row = self._svc.get(selected_id)
            selected_status = row.status if row is not None else None
        try:
            preview = self._svc.preview_zip(file_path)
        except Exception as exc:
            show_toast(self.window(), f"Ошибка чтения ZIP: {exc}", "error")
            return

        dlg = _ImportZipDialog(
            preview, selected_id, selected_status, self._context_patient_id, self
        )
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        try:
            mode = dlg.mode()
            if mode == "merge" and selected_id is not None:
                new_id = self._svc.merge_zip_into_card(selected_id, file_path)
            elif mode == "revision" and selected_id is not None:
                new_id = self._svc.import_zip_revision(selected_id, file_path)
            else:
                patient_id = dlg.patient_id()
                if patient_id is None:
                    show_toast(
                        self.window(),
                        "Укажите корректный patient_id для новой карточки.",
                        "error",
                    )
                    return
                new_id = self._svc.import_zip(
                    file_path,
                    patient_id=patient_id,
                    emr_case_id=self._context_case_id,
                )
        except Exception as exc:
            show_toast(self.window(), f"Ошибка импорта ZIP: {exc}", "error")
            return

        self._current_card_id = new_id
        self.refresh()
        show_toast(self.window(), f"Импорт завершён: {new_id}", "success")
