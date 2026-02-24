from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.form100_dto import Form100MarkDto

SIDE_FRONT = "FRONT"
SIDE_BACK = "BACK"
DEFAULT_MARK_TYPE = "NOTE_PIN"
TEMPLATE_BODY_IMAGE = "form_100_body.png"
TOOL_ITEMS: tuple[tuple[str, str], ...] = (
    ("Рана (X)", "WOUND_X"),
    ("Ожог (область)", "BURN_HATCH"),
    ("Жгут (линия)", "TOURNIQUET_LINE"),
    ("Ампутация (область)", "AMPUTATION_FILL"),
    ("Заметка (пин)", "NOTE_PIN"),
)
POINT_TOOLS = {"WOUND_X", "NOTE_PIN"}
LINE_TOOLS = {"TOURNIQUET_LINE"}
AREA_TOOLS = {"BURN_HATCH", "AMPUTATION_FILL"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_side(value: object, *, default: str = SIDE_FRONT) -> str:
    text = str(value or "").strip().upper()
    if text in {SIDE_FRONT, SIDE_BACK}:
        return text
    return default


def _normalize_mark_payload(payload: dict[str, Any], *, default_side: str) -> dict[str, Any]:
    return {
        "side": _normalize_side(payload.get("side"), default=default_side),
        "type": str(payload.get("type") or DEFAULT_MARK_TYPE),
        "shape_json": dict(payload.get("shape_json") or {}),
        "meta_json": dict(payload.get("meta_json") or {}),
    }


def _marks_stats(marks: list[dict[str, Any]]) -> str:
    if not marks:
        return "Нет меток"
    counts = Counter(str(item.get("type") or DEFAULT_MARK_TYPE) for item in marks)
    order = ["WOUND_X", "BURN_HATCH", "TOURNIQUET_LINE", "AMPUTATION_FILL", "NOTE_PIN"]
    labels = {
        "WOUND_X": "рана",
        "BURN_HATCH": "ожог",
        "TOURNIQUET_LINE": "жгут",
        "AMPUTATION_FILL": "ампутация",
        "NOTE_PIN": "пин",
    }
    parts: list[str] = []
    for key in order:
        if counts.get(key):
            parts.append(f"{labels[key]}: {counts[key]}")
    return ", ".join(parts)


def _resolve_template_pixmaps() -> tuple[QPixmap | None, QPixmap | None]:
    repo_root = Path(__file__).resolve().parents[4]
    image_root = repo_root / "app" / "image" / "main"
    front_path = image_root / "form_100_body_front.png"
    back_path = image_root / "form_100_body_back.png"
    if front_path.exists() and back_path.exists():
        front = QPixmap(str(front_path))
        back = QPixmap(str(back_path))
        if not front.isNull() and not back.isNull():
            return front, back

    combined_path = image_root / TEMPLATE_BODY_IMAGE
    if not combined_path.exists():
        return None, None
    combined = QPixmap(str(combined_path))
    if combined.isNull():
        return None, None
    return _split_combined_template(combined)


def _split_combined_template(combined: QPixmap) -> tuple[QPixmap, QPixmap]:
    def _copy_clamped(source: QPixmap, *, x: int, y: int, w: int, h: int) -> QPixmap:
        src_w = source.width()
        src_h = source.height()
        left = max(0, min(x, max(0, src_w - 1)))
        top = max(0, min(y, max(0, src_h - 1)))
        width_clamped = max(1, min(w, src_w - left))
        height_clamped = max(1, min(h, src_h - top))
        return source.copy(left, top, width_clamped, height_clamped)

    width = combined.width()
    height = combined.height()
    if width <= 0 or height <= 0:
        return combined, combined
    if width >= height * 1.3:
        # Для form_100_body.png ожидаем горизонтальную ленту фигур.
        # Выбираем перед/зад из первых двух сегментов.
        segments = 4 if width >= height * 1.45 else 2
        segment_width = max(1, width // segments)
        if segments >= 4:
            # Сдвиг crop-окон:
            # - front: чуть шире вправо, чтобы не терять правую кисть/пальцы;
            # - back: окно начинается правее границы сегмента, чтобы не захватывать
            #   руку соседней фигуры (вид спереди). Дополнительно немного подрезаем
            #   правый край, чтобы не попадал фрагмент следующей фигуры.
            front_extra_right = max(8, int(segment_width * 0.12))
            back_trim_left = max(8, int(segment_width * 0.06))
            back_trim_right = max(8, int(segment_width * 0.04))
            front = _copy_clamped(
                combined,
                x=0,
                y=0,
                w=segment_width + front_extra_right,
                h=height,
            )
            back = _copy_clamped(
                combined,
                x=segment_width + back_trim_left,
                y=0,
                w=segment_width - back_trim_left - back_trim_right,
                h=height,
            )
            return front, back
        front = _copy_clamped(combined, x=0, y=0, w=segment_width, h=height)
        back = _copy_clamped(combined, x=segment_width, y=0, w=segment_width, h=height) if segments > 1 else front
        return front, back
    if height >= width * 1.3:
        segments = 2
        segment_height = max(1, height // segments)
        front = _copy_clamped(combined, x=0, y=0, w=width, h=segment_height)
        back = _copy_clamped(combined, x=0, y=segment_height, w=width, h=segment_height)
        return front, back
    return combined, combined


class BodymapEditor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._marks: list[dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Метки схемы тела"))
        self._summary = QLabel("Нет меток")
        layout.addWidget(self._summary)

        buttons = QHBoxLayout()
        self._open_btn = QPushButton("Открыть окно рисования")
        self._open_btn.clicked.connect(self._open_draw_dialog)
        buttons.addWidget(self._open_btn)

        self._clear_btn = QPushButton("Очистить метки")
        self._clear_btn.clicked.connect(self.clear)
        buttons.addWidget(self._clear_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def set_marks(self, marks: list[Form100MarkDto]) -> None:
        payload = [item.model_dump(exclude={"created_at", "created_by"}) for item in marks]
        self._marks = [_normalize_mark_payload(item, default_side=SIDE_FRONT) for item in payload]
        self._refresh_summary()

    def get_marks(self) -> list[Form100MarkDto]:
        return [Form100MarkDto.model_validate(item) for item in self._marks]

    def clear(self) -> None:
        self._marks = []
        self._refresh_summary()

    def _open_draw_dialog(self) -> None:
        dialog = _BodymapDrawDialog(
            marks=self._marks,
            read_only=not self.isEnabled(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._marks = dialog.get_marks()
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        fronts = [item for item in self._marks if _normalize_side(item.get("side")) == SIDE_FRONT]
        backs = [item for item in self._marks if _normalize_side(item.get("side")) == SIDE_BACK]
        self._summary.setText(
            f"Спереди: {len(fronts)} ({_marks_stats(fronts)}). "
            f"Сзади: {len(backs)} ({_marks_stats(backs)})."
        )


class _BodymapDrawDialog(QDialog):
    def __init__(self, *, marks: list[dict[str, Any]], read_only: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактор схемы тела")
        self.resize(1100, 760)

        self._read_only = read_only

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(
            QLabel(
                "Клик: точечные метки (рана/пин). "
                "Зажмите и протяните: область ожога/ампутации или линия жгута. "
                "ПКМ: удалить ближайшую метку."
            )
        )

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Инструмент:"))
        self._tool_combo = QComboBox()
        for label, value in TOOL_ITEMS:
            self._tool_combo.addItem(label, value)
        self._tool_combo.currentIndexChanged.connect(self._on_tool_changed)
        toolbar.addWidget(self._tool_combo)
        toolbar.addStretch()
        root.addLayout(toolbar)

        marks_payload = [_normalize_mark_payload(item, default_side=SIDE_FRONT) for item in marks]
        front_marks = [item for item in marks_payload if item["side"] == SIDE_FRONT]
        back_marks = [item for item in marks_payload if item["side"] == SIDE_BACK]
        front_template, back_template = _resolve_template_pixmaps()

        canvases = QHBoxLayout()
        self._front_canvas = _BodymapCanvas(side=SIDE_FRONT, template_pixmap=front_template)
        self._back_canvas = _BodymapCanvas(side=SIDE_BACK, template_pixmap=back_template)
        self._front_canvas.set_marks(front_marks)
        self._back_canvas.set_marks(back_marks)
        self._front_canvas.marks_changed.connect(self._refresh_counts)
        self._back_canvas.marks_changed.connect(self._refresh_counts)
        self._front_canvas.set_read_only(read_only)
        self._back_canvas.set_read_only(read_only)

        canvases.addWidget(self._build_side_group("Вид спереди", self._front_canvas))
        canvases.addWidget(self._build_side_group("Вид сзади", self._back_canvas))
        root.addLayout(canvases)

        self._counts = QLabel()
        root.addWidget(self._counts)
        self._refresh_counts()
        self._on_tool_changed()

        if read_only:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
            if close_btn is not None:
                close_btn.setText("Закрыть")
            buttons.rejected.connect(self.reject)
        else:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
            cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if save_btn is not None:
                save_btn.setText("Применить")
            if cancel_btn is not None:
                cancel_btn.setText("Отмена")
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_marks(self) -> list[dict[str, Any]]:
        return self._front_canvas.get_marks() + self._back_canvas.get_marks()

    def _build_side_group(self, title: str, canvas: _BodymapCanvas) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.addWidget(canvas)

        controls = QHBoxLayout()
        undo_btn = QPushButton("Отменить последнюю")
        undo_btn.clicked.connect(canvas.pop_last_mark)
        clear_btn = QPushButton("Очистить сторону")
        clear_btn.clicked.connect(canvas.clear_marks)
        undo_btn.setEnabled(not self._read_only)
        clear_btn.setEnabled(not self._read_only)
        controls.addWidget(undo_btn)
        controls.addWidget(clear_btn)
        controls.addStretch()
        layout.addLayout(controls)
        return box

    def _on_tool_changed(self) -> None:
        tool = str(self._tool_combo.currentData() or DEFAULT_MARK_TYPE)
        self._front_canvas.set_active_tool(tool)
        self._back_canvas.set_active_tool(tool)

    def _refresh_counts(self) -> None:
        front = self._front_canvas.get_marks()
        back = self._back_canvas.get_marks()
        self._counts.setText(
            f"Итого меток: {len(front) + len(back)}. "
            f"Спереди: {len(front)} ({_marks_stats(front)}). "
            f"Сзади: {len(back)} ({_marks_stats(back)})."
        )


class _BodymapCanvas(QWidget):
    marks_changed = Signal()

    def __init__(
        self,
        *,
        side: str,
        template_pixmap: QPixmap | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._side = _normalize_side(side)
        self._marks: list[dict[str, Any]] = []
        self._active_tool = DEFAULT_MARK_TYPE
        self._read_only = False
        self._drag_start: QPointF | None = None
        self._drag_end: QPointF | None = None
        self._template_pixmap = template_pixmap if template_pixmap is not None and not template_pixmap.isNull() else None
        self.setMinimumSize(360, 520)
        self.setMouseTracking(True)

    def set_active_tool(self, tool: str) -> None:
        self._active_tool = tool

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only

    def set_marks(self, marks: list[dict[str, Any]]) -> None:
        self._marks = [_normalize_mark_payload(item, default_side=self._side) for item in marks]
        self.update()
        self.marks_changed.emit()

    def get_marks(self) -> list[dict[str, Any]]:
        return [_normalize_mark_payload(item, default_side=self._side) for item in self._marks]

    def pop_last_mark(self) -> None:
        if not self._marks or self._read_only:
            return
        self._marks.pop()
        self.update()
        self.marks_changed.emit()

    def clear_marks(self) -> None:
        if not self._marks or self._read_only:
            return
        self._marks = []
        self.update()
        self.marks_changed.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._read_only:
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._remove_nearest_mark(event.position())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._active_tool in POINT_TOOLS:
            self._add_point_mark(event.position())
            return
        if self._active_tool in LINE_TOOLS | AREA_TOOLS:
            self._drag_start = event.position()
            self._drag_end = event.position()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_start is None:
            return
        self._drag_end = event.position()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._read_only or event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag_start is None or self._drag_end is None:
            return
        if self._active_tool in LINE_TOOLS:
            shape = {
                **self._point_to_norm(self._drag_start, prefix="1"),
                **self._point_to_norm(self._drag_end, prefix="2"),
            }
            self._append_mark(self._active_tool, shape, {})
        elif self._active_tool in AREA_TOOLS:
            x1 = min(self._drag_start.x(), self._drag_end.x())
            y1 = min(self._drag_start.y(), self._drag_end.y())
            x2 = max(self._drag_start.x(), self._drag_end.x())
            y2 = max(self._drag_start.y(), self._drag_end.y())
            p1 = QPointF(x1, y1)
            p2 = QPointF(x2, y2)
            shape = {
                **self._point_to_norm(p1, prefix="1"),
                **self._point_to_norm(p2, prefix="2"),
            }
            self._append_mark(self._active_tool, shape, {})
        self._drag_start = None
        self._drag_end = None
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, on=True)
        painter.fillRect(self.rect(), QColor("#fcfcfc"))
        self._draw_body_template(painter)
        for mark in self._marks:
            self._draw_mark(painter, mark)
        self._draw_preview(painter)

    def _add_point_mark(self, point: QPointF) -> None:
        if self._active_tool == "NOTE_PIN":
            text, ok = QInputDialog.getText(self, "Заметка", "Комментарий:")
            if not ok:
                return
            meta = {"text": text.strip()} if text.strip() else {}
        else:
            meta = {}
        shape = self._point_to_norm(point)
        self._append_mark(self._active_tool, shape, meta)
        self.update()

    def _append_mark(self, mark_type: str, shape_json: dict[str, Any], meta_json: dict[str, Any]) -> None:
        self._marks.append(
            {
                "side": self._side,
                "type": mark_type,
                "shape_json": shape_json,
                "meta_json": meta_json,
            }
        )
        self.marks_changed.emit()

    def _remove_nearest_mark(self, point: QPointF) -> None:
        if not self._marks:
            return
        nearest_idx = -1
        nearest_distance = 10_000.0
        for idx, mark in enumerate(self._marks):
            anchor = self._mark_anchor(mark)
            distance = (anchor.x() - point.x()) ** 2 + (anchor.y() - point.y()) ** 2
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_idx = idx
        if nearest_idx < 0 or nearest_distance > 28 * 28:
            return
        self._marks.pop(nearest_idx)
        self.update()
        self.marks_changed.emit()

    def _mark_anchor(self, mark: dict[str, Any]) -> QPointF:
        mark_type = str(mark.get("type") or DEFAULT_MARK_TYPE)
        shape = dict(mark.get("shape_json") or {})
        if mark_type in POINT_TOOLS:
            return self._point_from_norm(shape.get("x"), shape.get("y"))
        if mark_type in LINE_TOOLS:
            p1 = self._point_from_norm(shape.get("x1"), shape.get("y1"))
            p2 = self._point_from_norm(shape.get("x2"), shape.get("y2"))
            return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
        p1 = self._point_from_norm(shape.get("x1"), shape.get("y1"))
        p2 = self._point_from_norm(shape.get("x2"), shape.get("y2"))
        return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)

    def _draw_body_template(self, painter: QPainter) -> None:
        if self._template_pixmap is not None:
            self._draw_image_template(painter)
            return
        body = self._body_rect()
        anchors = self._silhouette_anchors(body)

        painter.setPen(QPen(QColor("#ddd5ca"), 1))
        painter.setBrush(QColor("#faf8f4"))
        painter.drawRoundedRect(self.rect().adjusted(6, 30, -6, -6), 8, 8)

        silhouette = self._build_silhouette_path(body)
        painter.setPen(QPen(QColor("#8c8c8c"), 1.6))
        painter.setBrush(QColor("#f2eee7"))
        painter.drawPath(silhouette)

        painter.setPen(QPen(QColor("#b9b0a4"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(
            QPointF(anchors["cx"], anchors["y_shoulder"] + 5),
            QPointF(anchors["cx"], anchors["y_ankle"] - 8),
        )
        if self._side == SIDE_FRONT:
            painter.drawLine(
                QPointF(anchors["cx"] - anchors["shoulder_half"] * 0.45, anchors["y_shoulder"] + 18),
                QPointF(anchors["cx"] + anchors["shoulder_half"] * 0.45, anchors["y_shoulder"] + 18),
            )
            painter.drawLine(
                QPointF(anchors["cx"] - anchors["hip_half"] * 0.55, anchors["y_hip"] + 8),
                QPointF(anchors["cx"] + anchors["hip_half"] * 0.55, anchors["y_hip"] + 8),
            )
        else:
            painter.drawLine(
                QPointF(anchors["cx"] - anchors["shoulder_half"] * 0.55, anchors["y_shoulder"] + 24),
                QPointF(anchors["cx"] - anchors["shoulder_half"] * 0.08, anchors["y_waist"] - 10),
            )
            painter.drawLine(
                QPointF(anchors["cx"] + anchors["shoulder_half"] * 0.55, anchors["y_shoulder"] + 24),
                QPointF(anchors["cx"] + anchors["shoulder_half"] * 0.08, anchors["y_waist"] - 10),
            )

        painter.setPen(QColor("#6d6d6d"))
        label = "Вид спереди" if self._side == SIDE_FRONT else "Вид сзади"
        painter.drawText(QRectF(10, 8, self.width() - 20, 24), Qt.AlignmentFlag.AlignLeft, label)

    def _draw_image_template(self, painter: QPainter) -> None:
        if self._template_pixmap is None:
            return
        body = self._body_rect().adjusted(-12, -2, 12, 4)
        scaled = self._template_pixmap.scaled(
            body.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = body.x() + (body.width() - scaled.width()) / 2
        y = body.y() + (body.height() - scaled.height()) / 2
        painter.drawPixmap(int(x), int(y), scaled)
        painter.setPen(QPen(QColor("#c6beb2"), 1))
        painter.drawRoundedRect(QRectF(x, y, float(scaled.width()), float(scaled.height())), 4, 4)
        painter.setPen(QColor("#6d6d6d"))
        label = "Вид спереди" if self._side == SIDE_FRONT else "Вид сзади"
        painter.drawText(QRectF(10, 8, self.width() - 20, 24), Qt.AlignmentFlag.AlignLeft, label)

    def _draw_mark(self, painter: QPainter, mark: dict[str, Any]) -> None:
        mark_type = str(mark.get("type") or DEFAULT_MARK_TYPE)
        shape = dict(mark.get("shape_json") or {})
        meta = dict(mark.get("meta_json") or {})
        if mark_type == "WOUND_X":
            p = self._point_from_norm(shape.get("x"), shape.get("y"))
            pen = QPen(QColor("#c0392b"), 3)
            painter.setPen(pen)
            painter.drawLine(QPointF(p.x() - 7, p.y() - 7), QPointF(p.x() + 7, p.y() + 7))
            painter.drawLine(QPointF(p.x() - 7, p.y() + 7), QPointF(p.x() + 7, p.y() - 7))
            return
        if mark_type == "NOTE_PIN":
            p = self._point_from_norm(shape.get("x"), shape.get("y"))
            painter.setPen(QPen(QColor("#1f77b4"), 2))
            painter.setBrush(QColor("#6aaee6"))
            painter.drawEllipse(p, 5, 5)
            text = str(meta.get("text") or "").strip()
            if text:
                painter.setPen(QColor("#1f4f7a"))
                painter.drawText(QRectF(p.x() + 8, p.y() - 10, 140, 22), Qt.AlignmentFlag.AlignLeft, text)
            return
        if mark_type == "TOURNIQUET_LINE":
            p1 = self._point_from_norm(shape.get("x1"), shape.get("y1"))
            p2 = self._point_from_norm(shape.get("x2"), shape.get("y2"))
            painter.setPen(QPen(QColor("#9c640c"), 4))
            painter.drawLine(p1, p2)
            return
        if mark_type in {"BURN_HATCH", "AMPUTATION_FILL"}:
            rect = self._rect_from_norm(shape)
            if mark_type == "BURN_HATCH":
                painter.setPen(QPen(QColor("#e67e22"), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QColor(230, 126, 34, 60))
            else:
                painter.setPen(QPen(QColor("#943126"), 2))
                painter.setBrush(QColor(148, 49, 38, 90))
            painter.drawEllipse(rect)
            return
        p = self._point_from_norm(shape.get("x"), shape.get("y"))
        painter.setPen(QPen(QColor("#6c757d"), 2))
        painter.setBrush(QColor("#adb5bd"))
        painter.drawEllipse(p, 4, 4)

    def _draw_preview(self, painter: QPainter) -> None:
        if self._drag_start is None or self._drag_end is None:
            return
        painter.setPen(QPen(QColor("#5f6a6a"), 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._active_tool in LINE_TOOLS:
            painter.drawLine(self._drag_start, self._drag_end)
        elif self._active_tool in AREA_TOOLS:
            x1 = min(self._drag_start.x(), self._drag_end.x())
            y1 = min(self._drag_start.y(), self._drag_end.y())
            x2 = max(self._drag_start.x(), self._drag_end.x())
            y2 = max(self._drag_start.y(), self._drag_end.y())
            painter.drawEllipse(QRectF(QPointF(x1, y1), QPointF(x2, y2)))

    def _body_rect(self) -> QRectF:
        margin_x = max(24.0, self.width() * 0.16)
        top_margin = 44.0
        bottom_margin = 14.0
        return QRectF(
            margin_x,
            top_margin,
            max(20.0, self.width() - 2 * margin_x),
            max(20.0, self.height() - top_margin - bottom_margin),
        )

    def _silhouette_anchors(self, body: QRectF) -> dict[str, float]:
        cx = body.center().x()
        top = body.top()
        width = body.width()
        height = body.height()
        return {
            "cx": cx,
            "top": top,
            "width": width,
            "height": height,
            "y_shoulder": top + height * 0.20,
            "y_waist": top + height * 0.47,
            "y_hip": top + height * 0.60,
            "y_crotch": top + height * 0.67,
            "y_knee": top + height * 0.83,
            "y_ankle": top + height * 0.97,
            "shoulder_half": width * 0.24,
            "waist_half": width * 0.125,
            "hip_half": width * 0.17,
            "ankle_outer": width * 0.075,
            "ankle_inner": width * 0.028,
            "arm_width": width * 0.09,
            "head_width": width * 0.20,
            "head_height": height * 0.15,
        }

    def _build_silhouette_path(self, body: QRectF) -> QPainterPath:
        a = self._silhouette_anchors(body)
        cx = a["cx"]
        top = a["top"]
        y_shoulder = a["y_shoulder"]
        y_waist = a["y_waist"]
        y_hip = a["y_hip"]
        y_crotch = a["y_crotch"]
        y_knee = a["y_knee"]
        y_ankle = a["y_ankle"]
        shoulder_half = a["shoulder_half"]
        waist_half = a["waist_half"]
        hip_half = a["hip_half"]
        ankle_outer = a["ankle_outer"]
        ankle_inner = a["ankle_inner"]
        arm_width = a["arm_width"]
        head_width = a["head_width"]
        head_height = a["head_height"]

        path = QPainterPath()
        head_rect = QRectF(cx - head_width / 2, top + 2, head_width, head_height)
        path.addEllipse(head_rect)
        neck_rect = QRectF(cx - head_width * 0.20, top + head_height, head_width * 0.40, head_height * 0.22)
        path.addRoundedRect(neck_rect, 4, 4)

        left_arm = QRectF(
            cx - shoulder_half - arm_width * 1.22,
            y_shoulder + 5,
            arm_width,
            body.height() * 0.34,
        )
        right_arm = QRectF(
            cx + shoulder_half + arm_width * 0.22,
            y_shoulder + 5,
            arm_width,
            body.height() * 0.34,
        )
        path.addRoundedRect(left_arm, arm_width * 0.45, arm_width * 0.45)
        path.addRoundedRect(right_arm, arm_width * 0.45, arm_width * 0.45)
        path.addEllipse(QRectF(left_arm.center().x() - arm_width * 0.30, left_arm.bottom() - 10, arm_width * 0.6, 12))
        path.addEllipse(
            QRectF(right_arm.center().x() - arm_width * 0.30, right_arm.bottom() - 10, arm_width * 0.6, 12)
        )

        torso = QPainterPath()
        torso.moveTo(cx - shoulder_half, y_shoulder)
        torso.cubicTo(
            cx - shoulder_half * 1.1,
            y_shoulder + body.height() * 0.08,
            cx - waist_half * 1.35,
            y_waist - body.height() * 0.05,
            cx - waist_half,
            y_waist,
        )
        torso.cubicTo(
            cx - waist_half * 1.15,
            y_waist + body.height() * 0.05,
            cx - hip_half * 1.05,
            y_hip - body.height() * 0.03,
            cx - hip_half,
            y_hip,
        )
        torso.cubicTo(
            cx - hip_half * 1.05,
            y_hip + body.height() * 0.08,
            cx - ankle_outer * 1.55,
            y_knee,
            cx - ankle_outer,
            y_ankle,
        )
        torso.lineTo(cx - ankle_inner, y_ankle)
        torso.lineTo(cx - body.width() * 0.04, y_crotch)
        torso.lineTo(cx + body.width() * 0.04, y_crotch)
        torso.lineTo(cx + ankle_inner, y_ankle)
        torso.lineTo(cx + ankle_outer, y_ankle)
        torso.cubicTo(
            cx + ankle_outer * 1.55,
            y_knee,
            cx + hip_half * 1.05,
            y_hip + body.height() * 0.08,
            cx + hip_half,
            y_hip,
        )
        torso.cubicTo(
            cx + hip_half * 1.05,
            y_hip - body.height() * 0.03,
            cx + waist_half * 1.15,
            y_waist + body.height() * 0.05,
            cx + waist_half,
            y_waist,
        )
        torso.cubicTo(
            cx + waist_half * 1.35,
            y_waist - body.height() * 0.05,
            cx + shoulder_half * 1.1,
            y_shoulder + body.height() * 0.08,
            cx + shoulder_half,
            y_shoulder,
        )
        torso.closeSubpath()
        path.addPath(torso)
        return path

    def _point_to_norm(self, point: QPointF, *, prefix: str = "") -> dict[str, float]:
        width = max(1.0, float(self.width()))
        height = max(1.0, float(self.height()))
        x_key = "x" if not prefix else f"x{prefix}"
        y_key = "y" if not prefix else f"y{prefix}"
        return {x_key: _clamp01(point.x() / width), y_key: _clamp01(point.y() / height)}

    def _point_from_norm(self, x_value: object, y_value: object) -> QPointF:
        width = max(1.0, float(self.width()))
        height = max(1.0, float(self.height()))
        x = _clamp01(float(x_value if isinstance(x_value, (int, float)) else 0.5)) * width
        y = _clamp01(float(y_value if isinstance(y_value, (int, float)) else 0.5)) * height
        return QPointF(x, y)

    def _rect_from_norm(self, shape: dict[str, Any]) -> QRectF:
        p1 = self._point_from_norm(shape.get("x1"), shape.get("y1"))
        p2 = self._point_from_norm(shape.get("x2"), shape.get("y2"))
        x1 = min(p1.x(), p2.x())
        y1 = min(p1.y(), p2.y())
        x2 = max(p1.x(), p2.x())
        y2 = max(p1.y(), p2.y())
        return QRectF(QPointF(x1, y1), QPointF(x2, y2))
