"""WizardStep2 — Поражения + Схема тела."""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.bodymap_widget import BodyMapWidget
from app.ui.form100_v2.wizard_widgets.lesion_type_widget import LesionTypeWidget

LESION_ITEMS: tuple[tuple[str, str], ...] = (
    ("lesion_gunshot",    "О  Огнестрельное"),
    ("lesion_nuclear",    "Я  Ядерное"),
    ("lesion_chemical",   "Х  Химическое"),
    ("lesion_biological", "Бак. Бактериол."),
    ("lesion_other",      "Другие"),
    ("lesion_frostbite",  "Отм. Отморожение"),
    ("lesion_burn",       "Б  Ожог"),
    ("lesion_misc",       "И  Иное"),
)

SAN_LOSS_ITEMS: tuple[tuple[str, str], ...] = (
    ("san_loss_gunshot",    "О  Огнестрельное"),
    ("san_loss_nuclear",    "Я  Ядерное"),
    ("san_loss_chemical",   "Х  Химическое"),
    ("san_loss_biological", "Бак. Бактериол."),
    ("san_loss_other",      "Другие"),
    ("san_loss_frostbite",  "Отм. Отморожение"),
    ("san_loss_burn",       "Б  Ожог"),
    ("san_loss_misc",       "И  Иное"),
)

TISSUE_TYPES: tuple[str, ...] = (
    "мягкие ткани",
    "кости",
    "сосуды",
    "полостные раны",
    "ожоги",
)


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class StepBodymap(QWidget):
    """Шаг 2 мастера: виды поражений + схема тела + типы тканей."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ── Top row: controls ───────────────────────────────────────────────
        self._controls = QWidget()
        self._controls_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._controls)
        self._controls_layout.setContentsMargins(0, 0, 0, 0)
        self._controls_layout.setSpacing(8)
        root.addWidget(self._controls, 0)

        # Left: lesion grids + isolation
        self._left_controls = QWidget()
        left_col = QVBoxLayout(self._left_controls)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(6)

        lesion_box = QGroupBox("Вид поражения")
        lesion_box.setObjectName("form100Lesion")
        lesion_lay = QVBoxLayout(lesion_box)
        lesion_lay.setContentsMargins(8, 6, 8, 6)
        self.lesion_widget = LesionTypeWidget(LESION_ITEMS)
        lesion_lay.addWidget(self.lesion_widget)
        left_col.addWidget(lesion_box)

        san_box = QGroupBox("Вид сан. потерь")
        san_box.setObjectName("form100Lesion")
        san_lay = QVBoxLayout(san_box)
        san_lay.setContentsMargins(8, 6, 8, 6)
        self.san_loss_widget = LesionTypeWidget(SAN_LOSS_ITEMS)
        san_lay.addWidget(self.san_loss_widget)
        left_col.addWidget(san_box)

        left_col.addStretch(1)
        self._controls_layout.addWidget(self._left_controls, 3)

        # Middle: isolation
        self._isolation_controls = QWidget()
        isolation_col = QVBoxLayout(self._isolation_controls)
        isolation_col.setContentsMargins(0, 0, 0, 0)
        isolation_col.setSpacing(4)

        self.chk_isolation = QCheckBox("ИЗО-\nЛЯЦИЯ")
        self.chk_isolation.setObjectName("isolationCheck")
        self.chk_isolation.toggled.connect(self._sync_isolation_bar)
        isolation_col.addWidget(self.chk_isolation, 0, Qt.AlignmentFlag.AlignHCenter)

        self.isolation_bar = QFrame()
        self.isolation_bar.setObjectName("form100Isolation")
        self.isolation_bar.setMinimumWidth(18)
        self.isolation_bar.setMaximumWidth(24)
        self.isolation_bar.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.isolation_bar.setToolTip("ИЗОЛЯЦИЯ")
        isolation_col.addWidget(self.isolation_bar, 1, Qt.AlignmentFlag.AlignHCenter)

        self._controls_layout.addWidget(self._isolation_controls, 0)

        # Right: tissue types + notes
        self._right_controls = QWidget()
        right_col = QVBoxLayout(self._right_controls)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(8)

        tissue_box = QGroupBox("Типы тканей")
        tissue_box.setObjectName("form100Tissue")
        tissue_box.setMinimumWidth(140)
        tissue_box.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        tissue_lay = QVBoxLayout(tissue_box)
        tissue_lay.setContentsMargins(10, 6, 10, 8)
        tissue_lay.setSpacing(2)

        self.chk_tissues: list[QCheckBox] = []
        for title in TISSUE_TYPES:
            cb = QCheckBox(title)
            cb.setObjectName("form100TissueCheck")
            self.chk_tissues.append(cb)
            tissue_lay.addWidget(cb)

        right_col.addWidget(tissue_box)

        notes_box = QGroupBox("Заметки на схеме")
        notes_box.setObjectName("form100Notes")
        notes_box.setMinimumWidth(140)
        notes_box.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        notes_lay = QVBoxLayout(notes_box)
        notes_lay.setContentsMargins(10, 6, 10, 8)
        notes_lay.setSpacing(0)

        self._notes_hint = QLabel(
            "Нет заметок.\nДобавьте метку\n«Заметка ◎» на схему."
        )
        self._notes_hint.setWordWrap(True)
        self._notes_hint.setObjectName("form100NotesHint")
        self._notes_hint.setAlignment(Qt.AlignmentFlag.AlignTop)
        notes_lay.addWidget(self._notes_hint)

        self._notes_container = QWidget()
        self._notes_container.setObjectName("form100NotesContainer")
        self._notes_vlay = QVBoxLayout(self._notes_container)
        self._notes_vlay.setContentsMargins(0, 0, 0, 0)
        self._notes_vlay.setSpacing(3)
        notes_lay.addWidget(self._notes_container)

        right_col.addWidget(notes_box)
        right_col.addStretch(1)

        self._controls_layout.addWidget(self._right_controls, 2)

        # ── Bottom: body map editor (full width) ────────────────────────────
        self.editor = BodyMapWidget()
        self.editor.markersChanged.connect(self._refresh_notes)
        self.editor.setMinimumHeight(300)
        root.addWidget(self.editor, 1)

        self._apply_responsive_layout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        if width < 1260:
            self._controls_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._controls_layout.setSpacing(6)
            self.editor.setMinimumHeight(270)
            self._left_controls.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            self._right_controls.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
        else:
            self._controls_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._controls_layout.setSpacing(8)
            self.editor.setMinimumHeight(320)
            self._left_controls.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
            self._right_controls.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )

    def _sync_isolation_bar(self, checked: bool) -> None:
        self.isolation_bar.setProperty("active", bool(checked))
        self.isolation_bar.style().unpolish(self.isolation_bar)
        self.isolation_bar.style().polish(self.isolation_bar)
        self.isolation_bar.update()

    def _refresh_notes(self) -> None:
        while self._notes_vlay.count():
            item = self._notes_vlay.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.deleteLater()

        notes = [
            m for m in self.editor.markers()
            if m.get("annotation_type") == "NOTE_PIN" and m.get("note")
        ]

        if not notes:
            self._notes_hint.setVisible(True)
            self._notes_container.setVisible(False)
        else:
            self._notes_hint.setVisible(False)
            self._notes_container.setVisible(True)
            for i, m in enumerate(notes, start=1):
                row = QFrame()
                row.setObjectName("form100NoteRow")
                row_lay = QHBoxLayout(row)
                row_lay.setContentsMargins(6, 4, 6, 4)
                row_lay.setSpacing(6)

                idx_lbl = QLabel(f"{i}.")
                idx_lbl.setObjectName("form100NoteIndex")
                idx_lbl.setMinimumWidth(16)
                idx_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
                row_lay.addWidget(idx_lbl)

                text_lbl = QLabel(str(m.get("note", "")))
                text_lbl.setWordWrap(True)
                text_lbl.setObjectName("form100NoteText")
                row_lay.addWidget(text_lbl, 1)

                self._notes_vlay.addWidget(row)

    def set_values(self, payload: dict[str, str], markers: list[dict[str, Any]]) -> None:
        def _parse_json_list(raw: object) -> set[str]:
            try:
                parsed = json.loads(str(raw or "[]"))
                if isinstance(parsed, list):
                    return {str(x) for x in parsed}
            except (TypeError, ValueError, json.JSONDecodeError):
                return set()
            return set()

        lesion_vals = _parse_json_list(payload.get("lesion_json"))
        san_vals = _parse_json_list(payload.get("san_loss_json"))
        tissue_vals = _parse_json_list(payload.get("bodymap_tissue_types_json"))

        for key, btn in self.lesion_widget.checks.items():
            active = key in lesion_vals or _truthy(payload.get(key))
            btn.setChecked(active)
            self.lesion_widget._sync_button_state(btn, active)

        for key, btn in self.san_loss_widget.checks.items():
            active = key in san_vals or _truthy(payload.get(key))
            btn.setChecked(active)
            self.san_loss_widget._sync_button_state(btn, active)

        for cb in self.chk_tissues:
            cb.setChecked(cb.text() in tissue_vals)

        isolation = _truthy(payload.get("isolation_required"))
        self.chk_isolation.setChecked(isolation)
        self._sync_isolation_bar(isolation)

        gender = str(payload.get("bodymap_gender") or "M")
        if gender in ("M", "F"):
            self.editor.set_gender(gender)
        self.editor.set_markers(markers)

        self._refresh_notes()

    def collect(self) -> tuple[dict[str, str], list[dict[str, Any]]]:
        payload: dict[str, str] = {}

        lesion_sel = [k for k, b in self.lesion_widget.checks.items() if b.isChecked()]
        san_sel = [k for k, b in self.san_loss_widget.checks.items() if b.isChecked()]
        tissue_sel = [cb.text() for cb in self.chk_tissues if cb.isChecked()]

        payload["lesion_json"] = json.dumps(lesion_sel, ensure_ascii=False)
        payload["san_loss_json"] = json.dumps(san_sel, ensure_ascii=False)
        payload["bodymap_tissue_types_json"] = json.dumps(tissue_sel, ensure_ascii=False)

        for key, btn in self.lesion_widget.checks.items():
            payload[key] = "1" if btn.isChecked() else "0"
        for key, btn in self.san_loss_widget.checks.items():
            payload[key] = "1" if btn.isChecked() else "0"

        payload["isolation_required"] = "1" if self.chk_isolation.isChecked() else "0"
        payload["bodymap_gender"] = self.editor.gender()

        markers = self.editor.markers()
        payload["bodymap_annotations_json"] = json.dumps(markers, ensure_ascii=False)

        return payload, markers

    def set_locked(self, locked: bool) -> None:
        self.editor.set_markers_enabled(not locked)
        enabled = not locked
        self.lesion_widget.set_enabled(enabled)
        self.san_loss_widget.set_enabled(enabled)
        for cb in self.chk_tissues:
            cb.setEnabled(enabled)
        self.chk_isolation.setEnabled(enabled)

