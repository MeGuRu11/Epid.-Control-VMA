"""BodyMapWidget — интерактивная схема тела (2 силуэта).

Единый набор силуэтов: вид спереди и вид сзади.
Клик внутри силуэта размещает аннотацию.
ПКМ — удаляет ближайшую аннотацию в радиусе 15 px.
Фоновое изображение загружается из app/image/main/form_100_bd.png (fallback: form_100_body.png).
NOTE_PIN: при наведении показывается всплывающая карточка заметки.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ── Константы ────────────────────────────────────────────────────────────────

SILHOUETTE_ORDER = ("male_front", "male_back")
SILHOUETTE_LABELS = {
    "male_front": "Вид спереди",
    "male_back": "Вид сзади",
}
GENDER_ACTIVE: dict[str, set[str]] = {
    "M": {"male_front", "male_back"},
    "F": {"male_front", "male_back"},
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

_IMG_FILES: tuple[str, ...] = ("form_100_bd.png", "form_100_body.png")

def _get_image_root() -> Path:
    meipass = cast(object, getattr(sys, "_MEIPASS", None))
    if getattr(sys, "frozen", False) and isinstance(meipass, str):
        return Path(meipass) / "app" / "image" / "main"
    return Path(__file__).parent.parent.parent.parent / "image" / "main"


def _load_bodymap_template() -> QPixmap | None:
    img_root = _get_image_root()
    for file_name in _IMG_FILES:
        img_path = img_root / file_name
        if not img_path.exists():
            continue
        pixmap = QPixmap(str(img_path))
        if not pixmap.isNull():
            return pixmap
    return None


def _normalize_silhouette_pixmap(pixmap: QPixmap) -> QPixmap:
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 0:
                continue
            luminance = (color.red() + color.green() + color.blue()) // 3
            if luminance > 220:
                image.setPixelColor(x, y, QColor(0, 0, 0, 0))
            else:
                # Map luminance to alpha: darker pixels → more opaque
                alpha = max(20, min(255, 255 - luminance))
                image.setPixelColor(x, y, QColor(60, 60, 60, alpha))
    return QPixmap.fromImage(image)


def _split_bodymap_template(template: QPixmap) -> dict[str, QPixmap]:
    width = template.width()
    height = template.height()
    if width <= 0 or height <= 0:
        return {}

    if width >= int(height * 2.2):
        segment = max(1, width // 4)
        front = template.copy(0, 0, segment, height)
        back = template.copy(segment, 0, segment, height)
        if not front.isNull() and not back.isNull():
            return {
                "male_front": _normalize_silhouette_pixmap(front),
                "male_back": _normalize_silhouette_pixmap(back),
            }

    if width >= int(height * 0.6):
        split = max(1, width // 2)
        front = template.copy(0, 0, split, height)
        back = template.copy(split, 0, max(1, width - split), height)
        if not front.isNull() and not back.isNull():
            return {
                "male_front": _normalize_silhouette_pixmap(front),
                "male_back": _normalize_silhouette_pixmap(back),
            }

    normalized = _normalize_silhouette_pixmap(template.copy(0, 0, width, height))
    return dict.fromkeys(SILHOUETTE_ORDER, normalized)


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

    _shared_pixmaps: dict[str, QPixmap] | None = None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gender = "M"
        self._kind = ANNOTATION_TYPES[0]
        self._annotations: list[AnnotationData] = []
        self._markers_enabled = True
        self._hover_sil: str | None = None
        self._hover_pt: QPointF | None = None
        self._hover_ann_idx: int | None = None
        self.setMinimumSize(440, 280)
        self.setMouseTracking(True)

        if _BodyCanvas._shared_pixmaps is None:
            template = _load_bodymap_template()
            _BodyCanvas._shared_pixmaps = _split_bodymap_template(template) if template is not None else {}

    # ── Геометрия ─────────────────────────────────────────────────────────

    def _canvas_h(self) -> float:
        return float(self.height()) - 22

    def _sil_rect(self, silhouette: str) -> QRectF:
        idx = SILHOUETTE_ORDER.index(silhouette)
        slot_w = self.width() / float(len(SILHOUETTE_ORDER))
        return QRectF(idx * slot_w, 0.0, slot_w, self._canvas_h())

    def _body_hit_rect(self, sil: str) -> QRectF:
        r = self._sil_rect(sil)
        return QRectF(
            r.x() + r.width() * 0.06,
            r.y() + r.height() * 0.03,
            r.width() * 0.88,
            r.height() * 0.94,
        )

    def _template_rect(self, sil: str) -> QRectF:
        rect = self._body_hit_rect(sil)
        pixmaps = _BodyCanvas._shared_pixmaps or {}
        pixmap = pixmaps.get(sil)
        if pixmap is None or pixmap.isNull():
            return rect
        target = pixmap.size().scaled(
            rect.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        w = float(max(1, target.width()))
        h = float(max(1, target.height()))
        x = rect.x() + (rect.width() - w) / 2.0
        y = rect.y() + (rect.height() - h) / 2.0
        return QRectF(x, y, w, h)

    def _ann_canvas_pos(self, ann: AnnotationData) -> QPointF:
        r = self._template_rect(ann.silhouette)
        return QPointF(r.left() + ann.x * r.width(), r.top() + ann.y * r.height())

    def _hit_annotation(self, pos: QPointF) -> int | None:
        for idx, ann in enumerate(self._annotations):
            ap = self._ann_canvas_pos(ann)
            if (ap.x() - pos.x()) ** 2 + (ap.y() - pos.y()) ** 2 <= 225.0:
                return idx
        return None

    def _hit_body(self, pos: QPointF) -> tuple[str, float, float] | None:
        active = GENDER_ACTIVE["M"]
        for sil in SILHOUETTE_ORDER:
            if sil not in active:
                continue
            r = self._template_rect(sil)
            if r.contains(pos):
                nx = max(0.0, min(1.0, (pos.x() - r.left()) / max(1.0, r.width())))
                ny = max(0.0, min(1.0, (pos.y() - r.top()) / max(1.0, r.height())))
                return sil, nx, ny
        return None

    # ── Отрисовка ────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ARG002, N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        p.fillRect(self.rect(), QColor("#FFFFFF"))

        p.setPen(QPen(QColor("#D7D7D7"), 1))
        p.setBrush(QColor("#FFFFFF"))
        for sil in SILHOUETTE_ORDER:
            slot = self._sil_rect(sil)
            p.drawRoundedRect(slot, 6, 6)

        pixmaps = _BodyCanvas._shared_pixmaps or {}
        for sil in SILHOUETTE_ORDER:
            px = pixmaps.get(sil)
            if px is None or px.isNull():
                continue
            target_rect = self._template_rect(sil)
            scaled = px.scaled(
                target_rect.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
            y = target_rect.y() + (target_rect.height() - scaled.height()) / 2
            p.drawPixmap(int(x), int(y), scaled)

        for ann in self._annotations:
            ap = self._ann_canvas_pos(ann)
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
        p.setPen(QPen(QColor("#2E2E2E"), 1))
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
                r = self._template_rect(sil)
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
    """2-силуэтная интерактивная схема тела Формы 100."""

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

        toolbar.addWidget(QLabel("Метка:"))
        self._kind_group = QButtonGroup(self)
        self._kind_group.setExclusive(True)
        for idx, ann_type in enumerate(ANNOTATION_TYPES):
            btn = QPushButton(ANNOTATION_LABELS[ann_type])
            btn.setCheckable(True)
            btn.setObjectName("lesionToggle")
            btn.toggled.connect(lambda checked, b=btn: self._sync_toggle_button_state(b, checked))  # noqa: ARG005
            self._kind_group.addButton(btn, idx)
            toolbar.addWidget(btn)
        first_btn = self._kind_group.buttons()[0]
        if isinstance(first_btn, QPushButton):
            first_btn.setChecked(True)
            self._sync_toggle_button_state(first_btn, True)
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

    def _on_kind_changed(self, idx: int) -> None:
        if 0 <= idx < len(ANNOTATION_TYPES):
            self._canvas._kind = ANNOTATION_TYPES[idx]

    @staticmethod
    def _sync_toggle_button_state(btn: QPushButton, checked: bool) -> None:
        btn.setProperty("active", bool(checked))
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    def _on_canvas_changed(self) -> None:
        self.markersChanged.emit()
        self.annotations_changed.emit(self.annotations())

    def set_gender(self, gender: str) -> None:
        self._canvas._gender = "M"
        self._canvas.update()
        self.gender_changed.emit("M")

    def gender(self) -> str:
        return "M"

    def set_kind(self, kind: str) -> None:
        if kind in ANNOTATION_TYPES:
            idx = ANNOTATION_TYPES.index(kind)
            btn = self._kind_group.button(idx)
            if btn is not None:
                btn.setChecked(True)
            self._canvas._kind = kind

    def annotations(self) -> list[AnnotationData]:
        return list(self._canvas._annotations)

    def set_markers(self, markers: list[dict[str, Any]]) -> None:
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
            if silhouette in {"female_front", "front"}:
                silhouette = "male_front"
            elif silhouette in {"female_back", "back"}:
                silhouette = "male_back"
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

    def markers(self) -> list[dict[str, Any]]:
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

    def set_payload(self, payload: dict[str, Any]) -> None:
        self.set_gender("M")

    def payload(self) -> dict[str, Any]:
        return {"bodymap_gender": self.gender()}

    def has_template(self) -> bool:
        pixmaps = _BodyCanvas._shared_pixmaps or {}
        return any(not px.isNull() for px in pixmaps.values())

    def set_payload_read_only(self, read_only: bool) -> None:  # noqa: ARG002
        pass
