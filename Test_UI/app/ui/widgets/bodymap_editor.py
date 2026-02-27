from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QInputDialog, QLineEdit, QTextEdit, QWidget

from ...infrastructure.form100 import (
    BODYMAP_ZONES,
    FORM100_FIELDS,
    FORM100_MARKER_LEGACY_ALIASES,
    FORM100_MARKER_TYPES,
    empty_form100_payload,
    normalize_form100_payload,
    resolve_template_path,
)


@dataclass
class BodyMarker:
    x: float
    y: float
    annotation_type: str
    view: str
    note: str = ""


COLORS = {
    "WOUND_X": QColor("#C0392B"),
    "BURN_HATCH": QColor("#E67E22"),
    "AMPUTATION": QColor("#943126"),
    "TOURNIQUET": QColor("#9C640C"),
    "NOTE_PIN": QColor("#1F77B4"),
}


@dataclass
class _FieldRef:
    key: str
    x: float
    y: float
    w: float
    h: float
    font: float
    multiline: bool
    widget: QWidget


class BodyMapEditor(QWidget):
    markersChanged = Signal()
    payloadChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markers: list[BodyMarker] = []
        self._payload_shadow: dict[str, str] = empty_form100_payload()
        self._kind = FORM100_MARKER_TYPES[0]
        self._template_path = resolve_template_path()
        self._pixmap = QPixmap(str(self._template_path)) if self._template_path else QPixmap()
        self._image_rect = QRectF()
        self._drag_index: int | None = None
        self._drag_zone: str | None = None
        self._markers_enabled = True
        self._field_refs: list[_FieldRef] = []
        self._hidden_keys: set[str] = set()
        self._hover_point: QPointF | None = None
        self._hover_zone: str | None = None
        self.setMinimumSize(700, 500)
        self._build_field_widgets()
        self._reflow_fields()

    def has_template(self) -> bool:
        return self._pixmap is not None and not self._pixmap.isNull()

    def template_path_text(self) -> str:
        return str(self._template_path) if self._template_path else ""

    def set_kind(self, kind: str) -> None:
        if kind in FORM100_MARKER_TYPES:
            self._kind = kind

    def set_markers_enabled(self, enabled: bool) -> None:
        self._markers_enabled = bool(enabled)
        if not self._markers_enabled:
            self._hover_point = None
            self._hover_zone = None
            self.update()

    def set_hidden_keys(self, keys: set[str]) -> None:
        self._hidden_keys = {str(x) for x in keys}
        self._reflow_fields()

    def set_payload_read_only(self, read_only: bool) -> None:
        for field in self._field_refs:
            if field.multiline:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QTextEdit)
                editor.setReadOnly(read_only)
            else:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QLineEdit)
                editor.setReadOnly(read_only)

    def clear_markers(self) -> None:
        self._markers.clear()
        self.update()
        self.markersChanged.emit()

    def pop_marker(self) -> None:
        if not self._markers:
            return
        self._markers.pop()
        self.update()
        self.markersChanged.emit()

    def set_markers(self, markers: list[dict]) -> None:
        out: list[BodyMarker] = []
        for marker in markers:
            try:
                x = max(0.0, min(1.0, float(marker.get("x"))))
                y = max(0.0, min(1.0, float(marker.get("y"))))
            except (TypeError, ValueError):
                continue
            raw_type = str(
                marker.get("annotation_type")
                or marker.get("kind")
                or FORM100_MARKER_TYPES[0]
            )
            annotation_type = FORM100_MARKER_LEGACY_ALIASES.get(raw_type, raw_type)
            if annotation_type not in FORM100_MARKER_TYPES:
                annotation_type = FORM100_MARKER_TYPES[0]
            raw_view = str(marker.get("view") or marker.get("zone") or "front")
            view = raw_view if raw_view in BODYMAP_ZONES else "front"
            note = str(marker.get("note") or "")
            out.append(BodyMarker(x=x, y=y, annotation_type=annotation_type, view=view, note=note))
        self._markers = out
        self.update()
        self.markersChanged.emit()

    def markers(self) -> list[dict]:
        return [
            {
                "x": m.x,
                "y": m.y,
                "annotation_type": m.annotation_type,
                "view": m.view,
                "note": m.note,
                # Legacy keys for backward compatibility in mixed versions.
                "kind": m.annotation_type,
                "zone": m.view,
            }
            for m in self._markers
        ]

    def clear_payload(self) -> None:
        self.set_payload(empty_form100_payload())

    def set_payload(self, payload: dict) -> None:
        normalized = normalize_form100_payload(payload)
        self._payload_shadow = dict(normalized)
        for field in self._field_refs:
            value = normalized.get(field.key, "")
            if field.multiline:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QTextEdit)
                with _blocked(editor):
                    editor.setPlainText(value)
            else:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QLineEdit)
                with _blocked(editor):
                    editor.setText(value)

    def payload(self) -> dict[str, str]:
        out = dict(self._payload_shadow)
        for field in self._field_refs:
            if field.multiline:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QTextEdit)
                out[field.key] = editor.toPlainText().strip()
            else:
                editor = field.widget  # type: ignore[assignment]
                assert isinstance(editor, QLineEdit)
                out[field.key] = editor.text().strip()
        return out

    def _build_field_widgets(self) -> None:
        for spec in FORM100_FIELDS:
            key = str(spec["key"])
            x = float(spec["x"])
            y = float(spec["y"])
            w = float(spec["w"])
            h = float(spec["h"])
            font = float(spec.get("font", 8.0))
            multiline = bool(spec.get("multiline", False))

            if multiline:
                widget = QTextEdit(self)
                widget.setObjectName("form100FieldMultiline")
                widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                widget.setAcceptRichText(False)
                widget.textChanged.connect(self.payloadChanged.emit)
            else:
                widget = QLineEdit(self)
                widget.setObjectName("form100Field")
                widget.textChanged.connect(self.payloadChanged.emit)

            self._field_refs.append(
                _FieldRef(
                    key=key,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    font=font,
                    multiline=multiline,
                    widget=widget,
                )
            )

    def _fit_rect(self) -> QRectF:
        if self._pixmap.isNull():
            return QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        pw = float(self._pixmap.width())
        ph = float(self._pixmap.height())
        w = float(self.width())
        h = float(self.height())
        scale = min(w / max(1.0, pw), h / max(1.0, ph))
        dw = pw * scale
        dh = ph * scale
        x = (w - dw) / 2.0
        y = (h - dh) / 2.0
        return QRectF(x, y, dw, dh)

    def _zone_rect(self, zone: str) -> QRectF:
        x0, y0, ww, hh = BODYMAP_ZONES[zone]
        return QRectF(
            self._image_rect.left() + self._image_rect.width() * x0,
            self._image_rect.top() + self._image_rect.height() * y0,
            self._image_rect.width() * ww,
            self._image_rect.height() * hh,
        )

    def _marker_canvas_pos(self, marker: BodyMarker) -> QPointF:
        zone_rect = self._zone_rect(marker.view)
        return QPointF(
            zone_rect.left() + marker.x * zone_rect.width(),
            zone_rect.top() + marker.y * zone_rect.height(),
        )

    def _marker_hit(self, pos: QPointF) -> tuple[int, str] | None:
        for idx, marker in enumerate(self._markers):
            mpos = self._marker_canvas_pos(marker)
            if (mpos.x() - pos.x()) ** 2 + (mpos.y() - pos.y()) ** 2 <= 110.0:
                return idx, marker.view
        return None

    def _point_to_zone_norm(self, pos: QPointF) -> tuple[str, float, float] | None:
        for zone in ("front", "back"):
            rect = self._zone_rect(zone)
            if rect.contains(pos):
                nx = (pos.x() - rect.left()) / max(1.0, rect.width())
                ny = (pos.y() - rect.top()) / max(1.0, rect.height())
                return zone, max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))
        return None

    def _reflow_fields(self) -> None:
        self._image_rect = self._fit_rect()
        if not self.has_template():
            for field in self._field_refs:
                field.widget.setVisible(False)
            return

        scale = self._image_rect.width() / max(1.0, float(self._pixmap.width()))
        for field in self._field_refs:
            if field.key in self._hidden_keys:
                field.widget.setVisible(False)
                continue
            px = self._image_rect.left() + self._image_rect.width() * field.x
            py = self._image_rect.top() + self._image_rect.height() * field.y
            pw = self._image_rect.width() * field.w
            ph = self._image_rect.height() * field.h
            rect = QRect(
                int(px),
                int(py),
                max(6, int(pw)),
                max(6, int(ph)),
            )
            field.widget.setGeometry(rect)
            qfont = field.widget.font()
            qfont.setPointSizeF(max(5.5, field.font * scale))
            field.widget.setFont(qfont)
            field.widget.setVisible(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_fields()

    def mousePressEvent(self, event):
        if not self._markers_enabled:
            super().mousePressEvent(event)
            return
        pos = event.position()
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._marker_hit(pos)
            if hit is not None:
                self._drag_index, self._drag_zone = hit
                return
            spot = self._point_to_zone_norm(pos)
            if spot is not None:
                zone, nx, ny = spot
                note = ""
                if self._kind == "NOTE_PIN":
                    note_text, ok = QInputDialog.getText(self, "Заметка", "Текст заметки:")
                    if not ok:
                        return
                    note = note_text.strip()
                self._markers.append(BodyMarker(x=nx, y=ny, annotation_type=self._kind, view=zone, note=note))
                self.update()
                self.markersChanged.emit()
                return
        if event.button() == Qt.MouseButton.RightButton:
            hit = self._marker_hit(pos)
            if hit is not None:
                self._markers.pop(hit[0])
                self.update()
                self.markersChanged.emit()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        hit = self._marker_hit(event.position())
        if hit is not None:
            marker = self._markers[hit[0]]
            if marker.annotation_type == "NOTE_PIN" and marker.note:
                self.setToolTip(marker.note)
            else:
                self.setToolTip(marker.annotation_type)
        else:
            self.setToolTip("")
        if (
            self._markers_enabled
            and self._drag_index is not None
            and self._drag_zone is not None
            and 0 <= self._drag_index < len(self._markers)
        ):
            pos = event.position()
            rect = self._zone_rect(self._drag_zone)
            nx = (pos.x() - rect.left()) / max(1.0, rect.width())
            ny = (pos.y() - rect.top()) / max(1.0, rect.height())
            nx = max(0.0, min(1.0, nx))
            ny = max(0.0, min(1.0, ny))
            marker = self._markers[self._drag_index]
            marker.x = nx
            marker.y = ny
            self.update()
            self.markersChanged.emit()
            return
        if self._markers_enabled:
            spot = self._point_to_zone_norm(event.position())
            if spot is not None:
                zone, nx, ny = spot
                rect = self._zone_rect(zone)
                self._hover_zone = zone
                self._hover_point = QPointF(
                    rect.left() + nx * rect.width(),
                    rect.top() + ny * rect.height(),
                )
            else:
                self._hover_zone = None
                self._hover_point = None
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_index = None
        self._drag_zone = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self._markers_enabled:
            super().mouseDoubleClickEvent(event)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        hit = self._marker_hit(event.position())
        if hit is None:
            super().mouseDoubleClickEvent(event)
            return
        marker = self._markers[hit[0]]
        if marker.annotation_type != "NOTE_PIN":
            super().mouseDoubleClickEvent(event)
            return
        note_text, ok = QInputDialog.getText(self, "Заметка", "Текст заметки:", text=marker.note)
        if not ok:
            return
        marker.note = note_text.strip()
        self.update()
        self.markersChanged.emit()

    def leaveEvent(self, event):
        self._hover_point = None
        self._hover_zone = None
        self.setToolTip("")
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        _ = event
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#FFFDF8"))

        self._image_rect = self._fit_rect()
        if self.has_template():
            p.drawPixmap(self._image_rect, self._pixmap, QRectF(self._pixmap.rect()))
        else:
            p.setPen(QPen(QColor("#7A7A78"), 1))
            p.drawRoundedRect(self.rect().adjusted(8, 8, -8, -8), 10, 10)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Шаблон form100 не найден")
            return

        guide_pen = QPen(QColor(111, 185, 173, 80), 1, Qt.PenStyle.DashLine)
        p.setPen(guide_pen)
        for zone in ("front", "back"):
            p.drawRect(self._zone_rect(zone))

        for marker in self._markers:
            mpos = self._marker_canvas_pos(marker)
            color = COLORS.get(marker.annotation_type, QColor("#1F77B4"))
            p.setPen(QPen(color, 2))
            p.setBrush(color)
            p.drawEllipse(mpos, 4, 4)
            if marker.annotation_type == "AMPUTATION":
                p.drawLine(int(mpos.x() - 6), int(mpos.y() - 6), int(mpos.x() + 6), int(mpos.y() + 6))
                p.drawLine(int(mpos.x() - 6), int(mpos.y() + 6), int(mpos.x() + 6), int(mpos.y() - 6))
            elif marker.annotation_type == "TOURNIQUET":
                p.drawLine(int(mpos.x() - 7), int(mpos.y()), int(mpos.x() + 7), int(mpos.y()))
            p.setPen(QPen(color, 1))
            p.drawText(int(mpos.x() + 6), int(mpos.y() - 6), marker.annotation_type)

        if self._markers_enabled and self._hover_point is not None and self._hover_zone is not None:
            preview_color = QColor("#5F6A6A")
            preview_color.setAlpha(150)
            p.setPen(QPen(preview_color, 1))
            p.setBrush(preview_color)
            p.drawEllipse(self._hover_point, 4, 4)
            p.setPen(QPen(preview_color, 1))
            p.drawText(int(self._hover_point.x() + 6), int(self._hover_point.y() - 6), self._kind)


class _blocked:
    def __init__(self, widget: QWidget):
        self._widget = widget
        self._previous = False

    def __enter__(self):
        self._previous = self._widget.blockSignals(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._widget.blockSignals(self._previous)
        return False
