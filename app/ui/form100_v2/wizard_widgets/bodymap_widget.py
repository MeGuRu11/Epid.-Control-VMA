"""BodyMapWidget — интерактивная схема тела (4 силуэта).

Мужчина спереди/сзади + Женщина спереди/сзади.
Клик внутри активного силуэта размещает аннотацию.
ПКМ — удаляет ближайшую аннотацию в радиусе 15 px.
Неактивные силуэты (другой пол) приглушены полупрозрачным оверлеем.
Фоновое изображение загружается из app/image/main/form_100_body.png.
NOTE_PIN: при наведении показывается всплывающая карточка заметки.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ── Константы ────────────────────────────────────────────────────────────────

SILHOUETTE_ORDER = ("male_front", "male_back", "female_front", "female_back")
SILHOUETTE_LABELS = {
    "male_front":   "М (перед)",
    "male_back":    "М (зад)",
    "female_front": "Ж (перед)",
    "female_back":  "Ж (зад)",
}
GENDER_ACTIVE: dict[str, set[str]] = {
    "M": {"male_front", "male_back"},
    "F": {"female_front", "female_back"},
}

ANNOTATION_TYPES = ("WOUND_X", "BURN_HATCH", "AMPUTATION", "TOURNIQUET", "NOTE_PIN")
ANNOTATION_LABELS = {
    "WOUND_X":    "Рана ✕",
    "BURN_HATCH":  "Ожог ○",
    "AMPUTATION":  "Ампутация ▲",
    "TOURNIQUET":  "Жгут ─",
    "NOTE_PIN":    "Заметка ◎",
}
ANNOTATION_COLORS: dict[str, QColor] = {
    "WOUND_X":    QColor("#E74C3C"),
    "BURN_HATCH":  QColor("#F39C12"),
    "AMPUTATION":  QColor("#C0392B"),
    "TOURNIQUET":  QColor("#E67E22"),
    "NOTE_PIN":    QColor("#3498DB"),
}

# Путь к изображению схемы тела (app/image/main/form_100_body.png)
_IMG_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "image" / "main" / "form_100_body.png"
)


# ── Domain dataclass ──────────────────────────────────────────────────────────

@dataclass
class AnnotationData:
    annotation_type: str
    x: float          # 0.0–1.0 внутри силуэтного прямоугольника
    y: float
    silhouette: str   # one of SILHOUETTE_ORDER
    note: str = ""


# ── Холст: рисование силуэтов и аннотаций ───────────────────────────────────

class _BodyCanvas(QWidget):
    markersChanged = Signal()  # noqa: N815

    _shared_pixmap: QPixmap | None = None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gender = "M"
        self._kind = ANNOTATION_TYPES[0]
        self._annotations: list[AnnotationData] = []
        self._markers_enabled = True
        self._hover_sil: str | None = None
        self._hover_pt: QPointF | None = None
        self._hover_ann_idx: int | None = None
        self.setMinimumSize(500, 320)
        self.setMouseTracking(True)

        if _BodyCanvas._shared_pixmap is None:
            px = QPixmap(str(_IMG_PATH))
            _BodyCanvas._shared_pixmap = px if not px.isNull() else None

    # ── Геометрия ─────────────────────────────────────────────────────────

    def _canvas_h(self) -> float:
        return float(self.height()) - 22

    def _sil_rect(self, silhouette: str) -> QRectF:
        idx = SILHOUETTE_ORDER.index(silhouette)
        slot_w = self.width() / 4.0
        return QRectF(idx * slot_w, 0.0, slot_w, self._canvas_h())

    def _body_hit_rect(self, sil: str) -> QRectF:
        r = self._sil_rect(sil)
        return QRectF(
            r.x() + r.width() * 0.18,
            r.y() + r.height() * 0.03,
            r.width() * 0.64,
            r.height() * 0.94,
        )

    def _ann_canvas_pos(self, ann: AnnotationData) -> QPointF:
        r = self._sil_rect(ann.silhouette)
        return QPointF(r.left() + ann.x * r.width(), r.top() + ann.y * r.height())

    def _hit_annotation(self, pos: QPointF) -> int | None:
        for idx, ann in enumerate(self._annotations):
            ap = self._ann_canvas_pos(ann)
            if (ap.x() - pos.x()) ** 2 + (ap.y() - pos.y()) ** 2 <= 225.0:
                return idx
        return None

    def _hit_body(self, pos: QPointF) -> tuple[str, float, float] | None:
        active = GENDER_ACTIVE[self._gender]
        for sil in SILHOUETTE_ORDER:
            if sil not in active:
                continue
            if self._body_hit_rect(sil).contains(pos):
                r = self._sil_rect(sil)
                nx = max(0.0, min(1.0, (pos.x() - r.left()) / max(1.0, r.width())))
                ny = max(0.0, min(1.0, (pos.y() - r.top()) / max(1.0, r.height())))
                return sil, nx, ny
        return None

    # ── Отрисовка ────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ARG002, N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        ch = int(self._canvas_h())

        p.fillRect(self.rect(), QColor("#1A1E24"))

        px = _BodyCanvas._shared_pixmap
        if px is not None:
            scaled = px.scaled(
                self.width(), ch,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(0, 0, scaled)

        active = GENDER_ACTIVE[self._gender]
        for sil in SILHOUETTE_ORDER:
            if sil not in active:
                r = self._sil_rect(sil)
                p.fillRect(r, QColor(0, 0, 0, 150))

        for ann in self._annotations:
            ap = self._ann_canvas_pos(ann)
            is_active_sil = ann.silhouette in active
            p.setOpacity(0.35 if not is_active_sil else 1.0)
            self._draw_symbol(
                p, ann.annotation_type, ap,
                ANNOTATION_COLORS.get(ann.annotation_type, QColor("#3498DB")),
            )
        p.setOpacity(1.0)

        if self._markers_enabled and self._hover_pt is not None:
            prev_color = QColor("#FFFFFF")
            prev_color.setAlpha(170)
            self._draw_symbol(p, self._kind, self._hover_pt, prev_color, preview=True)

        p.setOpacity(1.0)
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        p.setPen(QPen(QColor("#AAAAAA"), 1))
        for sil in SILHOUETTE_ORDER:
            r = self._sil_rect(sil)
            lr = QRectF(r.x(), float(self.height()) - 20, r.width(), 18)
            p.drawText(lr, Qt.AlignmentFlag.AlignHCenter, SILHOUETTE_LABELS[sil])

        if (
            self._hover_ann_idx is not None
            and 0 <= self._hover_ann_idx < len(self._annotations)
        ):
            ann = self._annotations[self._hover_ann_idx]
            if ann.annotation_type == "NOTE_PIN" and ann.note:
                ap = self._ann_canvas_pos(ann)
                self._draw_note_bubble(p, ap, ann.note)

    @staticmethod
    def _draw_symbol(
        p: QPainter,
        ann_type: str,
        pos: QPointF,
        color: QColor,
        *,
        preview: bool = False,
    ) -> None:
        p.save()
        p.setPen(QPen(color, 2))
        p.setBrush(QBrush(color))
        px, py = int(pos.x()), int(pos.y())
        size = 5 if preview else 7

        if ann_type == "WOUND_X":
            p.drawLine(px - size, py - size, px + size, py + size)
            p.drawLine(px - size, py + size, px + size, py - size)
        elif ann_type == "BURN_HATCH":
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pos, float(size + 1), float(size + 1))
            p.drawLine(px - size, py - size, px + size, py + size)
        elif ann_type == "AMPUTATION":
            tri = QPolygonF([
                QPointF(px, py - size - 2),
                QPointF(px - size, py + size),
                QPointF(px + size, py + size),
            ])
            p.drawPolygon(tri)
        elif ann_type == "TOURNIQUET":
            cap_h = 3
            p.drawLine(px - size - 3, py, px + size + 3, py)
            p.drawLine(px - size - 3, py - cap_h, px - size - 3, py + cap_h)
            p.drawLine(px + size + 3, py - cap_h, px + size + 3, py + cap_h)
        elif ann_type == "NOTE_PIN":
            p.drawEllipse(pos, float(size), float(size))
            p.drawLine(px, py + size, px, py + size + 7)
        else:
            p.drawEllipse(pos, float(size), float(size))
        p.restore()

    def _draw_note_bubble(self, p: QPainter, pos: QPointF, text: str) -> None:
        p.save()
        font = p.font()
        font.setPointSize(9)
        p.setFont(font)
        fm = p.fontMetrics()
        max_w = 220
        display = text if len(text) <= 35 else text[:33] + "…"
        tw = min(fm.horizontalAdvance(display), max_w)
        th = fm.height()
        pad = 7
        bw = tw + pad * 2
        bh = th + pad * 2
        bx = pos.x() + 16
        by = pos.y() - bh - 6
        if bx + bw > self.width() - 4:
            bx = pos.x() - bw - 16
        if by < 4:
            by = pos.y() + 18
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(QRectF(bx + 2, by + 2, bw, bh), 5, 5)
        p.setBrush(QColor("#1E3352"))
        p.setPen(QPen(QColor("#4A90D9"), 1.5))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 5, 5)
        p.setPen(QPen(QColor("#E8F4FD")))
        p.drawText(
            QRectF(bx + pad, by + pad, tw, th),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            display,
        )
        p.restore()

    # ── Мышь ─────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self._markers_enabled:
            super().mousePressEvent(event)
            return
        pos = event.position()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._hit_annotation(pos) is not None:
                return
            spot = self._hit_body(pos)
            if spot is not None:
                sil, nx, ny = spot
                note = ""
                if self._kind == "NOTE_PIN":
                    text, ok = QInputDialog.getText(self, "Заметка", "Текст заметки:")
                    if not ok:
                        return
                    note = text.strip()
                self._annotations.append(
                    AnnotationData(
                        annotation_type=self._kind,
                        x=nx, y=ny,
                        silhouette=sil,
                        note=note,
                    )
                )
                self.update()
                self.markersChanged.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            idx = self._hit_annotation(pos)
            if idx is not None:
                self._annotations.pop(idx)
                self.update()
                self.markersChanged.emit()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        if self._markers_enabled:
            spot = self._hit_body(pos)
            if spot is not None:
                sil, nx, ny = spot
                r = self._sil_rect(sil)
                self._hover_sil = sil
                self._hover_pt = QPointF(
                    r.left() + nx * r.width(),
                    r.top() + ny * r.height(),
                )
            else:
                self._hover_sil = None
                self._hover_pt = None

        hit = self._hit_annotation(pos)
        if hit != self._hover_ann_idx:
            self._hover_ann_idx = hit
            if hit is not None:
                ann = self._annotations[hit]
                self.setToolTip("" if ann.annotation_type == "NOTE_PIN" else ann.annotation_type)
            else:
                self.setToolTip("")

        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_sil = None
        self._hover_pt = None
        self._hover_ann_idx = None
        self.update()
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if not self._markers_enabled:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._hit_annotation(event.position())
        if idx is None:
            return
        ann = self._annotations[idx]
        if ann.annotation_type != "NOTE_PIN":
            return
        text, ok = QInputDialog.getText(
            self, "Заметка", "Текст заметки:", text=ann.note
        )
        if ok:
            ann.note = text.strip()
            self.update()
            self.markersChanged.emit()


# ── Публичный виджет ─────────────────────────────────────────────────────────

class BodyMapWidget(QWidget):
    """4-силуэтная интерактивная схема тела Формы 100."""

    markersChanged = Signal()  # noqa: N815
    annotations_changed = Signal(list)
    gender_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        toolbar.addWidget(QLabel("Пол:"))
        self._gender_combo = QComboBox()
        self._gender_combo.addItem("Мужчина", "M")
        self._gender_combo.addItem("Женщина", "F")
        self._gender_combo.setFixedWidth(100)
        self._gender_combo.currentIndexChanged.connect(self._on_gender_changed)
        toolbar.addWidget(self._gender_combo)

        toolbar.addWidget(QLabel("Метка:"))
        self._kind_group = QButtonGroup(self)
        self._kind_group.setExclusive(True)
        for idx, ann_type in enumerate(ANNOTATION_TYPES):
            btn = QPushButton(ANNOTATION_LABELS[ann_type])
            btn.setCheckable(True)
            btn.setObjectName("lesionToggle")
            self._kind_group.addButton(btn, idx)
            toolbar.addWidget(btn)
        first_btn = self._kind_group.buttons()[0]
        if first_btn is not None:
            first_btn.setChecked(True)
        self._kind_group.idClicked.connect(self._on_kind_changed)

        btn_pop = QPushButton("Удалить посл.")
        btn_pop.setObjectName("secondary")
        btn_pop.clicked.connect(self.pop_marker)
        toolbar.addWidget(btn_pop)

        btn_clear = QPushButton("Очистить")
        btn_clear.setObjectName("ghost")
        btn_clear.clicked.connect(self.clear_markers)
        toolbar.addWidget(btn_clear)
        toolbar.addStretch(1)

        root.addLayout(toolbar)

        self._canvas = _BodyCanvas(self)
        self._canvas.markersChanged.connect(self._on_canvas_changed)
        root.addWidget(self._canvas, 1)

    def _on_gender_changed(self) -> None:
        gender = self._gender_combo.currentData() or "M"
        self._canvas._gender = gender
        self._canvas.update()
        self.gender_changed.emit(gender)

    def _on_kind_changed(self, idx: int) -> None:
        if 0 <= idx < len(ANNOTATION_TYPES):
            self._canvas._kind = ANNOTATION_TYPES[idx]

    def _on_canvas_changed(self) -> None:
        self.markersChanged.emit()
        self.annotations_changed.emit(self.annotations())

    def set_gender(self, gender: str) -> None:
        idx = 0 if gender != "F" else 1
        self._gender_combo.setCurrentIndex(idx)
        self._canvas._gender = gender
        self._canvas.update()

    def gender(self) -> str:
        return self._gender_combo.currentData() or "M"

    def set_kind(self, kind: str) -> None:
        if kind in ANNOTATION_TYPES:
            idx = ANNOTATION_TYPES.index(kind)
            btn = self._kind_group.button(idx)
            if btn is not None:
                btn.setChecked(True)
            self._canvas._kind = kind

    def annotations(self) -> list[AnnotationData]:
        return list(self._canvas._annotations)

    def set_markers(self, markers: list[dict]) -> None:  # type: ignore[type-arg]
        out: list[AnnotationData] = []
        for m in markers:
            try:
                x = max(0.0, min(1.0, float(m.get("x") or 0)))
                y = max(0.0, min(1.0, float(m.get("y") or 0)))
            except (TypeError, ValueError):
                continue
            ann_type = str(m.get("annotation_type") or m.get("kind") or "WOUND_X")
            if ann_type not in ANNOTATION_TYPES:
                ann_type = "WOUND_X"
            silhouette = str(m.get("silhouette") or "")
            if silhouette not in SILHOUETTE_ORDER:
                view = str(m.get("view") or m.get("zone") or "front")
                silhouette = f"male_{view}" if view in ("front", "back") else "male_front"
            note = str(m.get("note") or "")
            out.append(
                AnnotationData(
                    annotation_type=ann_type, x=x, y=y,
                    silhouette=silhouette, note=note,
                )
            )
        self._canvas._annotations = out
        self._canvas.update()

    def markers(self) -> list[dict]:  # type: ignore[type-arg]
        return [
            {
                "annotation_type": a.annotation_type,
                "x": a.x,
                "y": a.y,
                "silhouette": a.silhouette,
                "note": a.note,
                "kind": a.annotation_type,
                "view": "front" if "front" in a.silhouette else "back",
                "zone": "front" if "front" in a.silhouette else "back",
            }
            for a in self._canvas._annotations
        ]

    def pop_marker(self) -> None:
        if self._canvas._annotations:
            self._canvas._annotations.pop()
            self._canvas.update()
            self.markersChanged.emit()

    def clear_markers(self) -> None:
        self._canvas._annotations.clear()
        self._canvas.update()
        self.markersChanged.emit()

    def set_markers_enabled(self, enabled: bool) -> None:
        self._canvas._markers_enabled = enabled
        if not enabled:
            self._canvas._hover_pt = None
            self._canvas._hover_sil = None
            self._canvas._hover_ann_idx = None
            self._canvas.update()

    def set_hidden_keys(self, keys: set[str]) -> None:
        pass

    def set_payload(self, payload: dict) -> None:  # type: ignore[type-arg]
        gender = str(payload.get("bodymap_gender") or "M")
        if gender in ("M", "F"):
            self.set_gender(gender)

    def payload(self) -> dict:  # type: ignore[type-arg]
        return {"bodymap_gender": self.gender()}

    def has_template(self) -> bool:
        return _BodyCanvas._shared_pixmap is not None

    def set_payload_read_only(self, read_only: bool) -> None:  # noqa: ARG002
        pass
