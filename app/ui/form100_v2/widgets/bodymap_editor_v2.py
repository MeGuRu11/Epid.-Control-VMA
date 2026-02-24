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
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.form100_v2_dto import Form100AnnotationDto

_TEMPLATE_IMAGE = "form_100_body.png"
_SILHOUETTE_ORDER = ("male_front", "male_back", "female_front", "female_back")
_TOOL_ITEMS: tuple[tuple[str, str], ...] = (
    ("Рана (X)", "WOUND_X"),
    ("Ожог (область)", "BURN_HATCH"),
    ("Ампутация (область)", "AMPUTATION"),
    ("Жгут (линия)", "TOURNIQUET"),
    ("Заметка (пин)", "NOTE_PIN"),
)
_POINT_TOOLS = {"WOUND_X", "NOTE_PIN"}
_DRAG_TOOLS = {"BURN_HATCH", "AMPUTATION", "TOURNIQUET"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _to_float(value: object, default: float = 0.5) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:  # noqa: BLE001
        return default


def _active_silhouettes(gender: str) -> set[str]:
    return {"male_front", "male_back"} if gender == "M" else {"female_front", "female_back"}


def _load_silhouette_pixmaps() -> dict[str, QPixmap]:
    repo_root = Path(__file__).resolve().parents[4]
    image_path = repo_root / "app" / "image" / "main" / _TEMPLATE_IMAGE
    if not image_path.exists():
        return {}
    src = QPixmap(str(image_path))
    if src.isNull():
        return {}
    width = src.width()
    height = src.height()
    if width <= 0 or height <= 0:
        return {}
    segment = max(1, width // 4)
    result: dict[str, QPixmap] = {}
    for idx, name in enumerate(_SILHOUETTE_ORDER):
        x = idx * segment
        w = segment if idx < 3 else max(1, width - x)
        result[name] = src.copy(x, 0, w, height)
    return result


def _marks_stats(marks: list[dict[str, Any]]) -> str:
    if not marks:
        return "Нет меток"
    labels = {
        "WOUND_X": "рана",
        "BURN_HATCH": "ожог",
        "AMPUTATION": "ампутация",
        "TOURNIQUET": "жгут",
        "NOTE_PIN": "пин",
    }
    counts = Counter(str(item.get("annotation_type") or "NOTE_PIN") for item in marks)
    parts = [f"{labels.get(key, key.lower())}: {value}" for key, value in counts.items() if value > 0]
    return ", ".join(parts) if parts else "Нет меток"


class BodymapEditorV2(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._gender = "M"
        self._marks: list[dict[str, Any]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addWidget(QLabel("Метки схемы тела"))
        self._summary = QLabel("Нет меток")
        root.addWidget(self._summary)

        row = QHBoxLayout()
        self._open_btn = QPushButton("Открыть окно рисования")
        self._open_btn.clicked.connect(self._open_dialog)
        row.addWidget(self._open_btn)
        self._clear_btn = QPushButton("Очистить метки")
        self._clear_btn.clicked.connect(self.clear)
        row.addWidget(self._clear_btn)
        row.addStretch()
        root.addLayout(row)

    def set_value(self, *, gender: str, annotations: list[Form100AnnotationDto]) -> None:
        self._gender = "M" if str(gender).upper() != "F" else "F"
        self._marks = [item.model_dump() for item in annotations]
        self._refresh_summary()

    def get_value(self) -> tuple[str, list[Form100AnnotationDto]]:
        return self._gender, [Form100AnnotationDto.model_validate(item) for item in self._marks]

    def clear(self) -> None:
        self._marks = []
        self._refresh_summary()

    def _open_dialog(self) -> None:
        dialog = _BodymapDialogV2(
            gender=self._gender,
            marks=self._marks,
            read_only=not self.isEnabled(),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._gender = dialog.get_gender()
            self._marks = dialog.get_marks()
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        male = [item for item in self._marks if str(item.get("silhouette", "")).startswith("male_")]
        female = [item for item in self._marks if str(item.get("silhouette", "")).startswith("female_")]
        self._summary.setText(
            f"Пол: {'М' if self._gender == 'M' else 'Ж'}. "
            f"Метки: {len(self._marks)} (муж: {len(male)}, жен: {len(female)}). {_marks_stats(self._marks)}."
        )


class _BodymapDialogV2(QDialog):
    def __init__(
        self,
        *,
        gender: str,
        marks: list[dict[str, Any]],
        read_only: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактор схемы тела")
        self.resize(1220, 820)
        self._read_only = read_only

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(
            QLabel(
                "Клик: точечные метки (рана/пин). "
                "Зажмите и протяните: область ожога/ампутации или линия жгута. "
                "ПКМ: удалить ближайшую метку."
            )
        )

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Пол:"))
        self._gender_combo = QComboBox()
        self._gender_combo.addItem("Мужчина", "M")
        self._gender_combo.addItem("Женщина", "F")
        self._gender_combo.setCurrentIndex(0 if str(gender).upper() != "F" else 1)
        self._gender_combo.currentIndexChanged.connect(self._on_gender_changed)
        toolbar.addWidget(self._gender_combo)
        toolbar.addSpacing(10)
        toolbar.addWidget(QLabel("Инструмент:"))
        self._tool_combo = QComboBox()
        for label, value in _TOOL_ITEMS:
            self._tool_combo.addItem(label, value)
        self._tool_combo.currentIndexChanged.connect(self._on_tool_changed)
        toolbar.addWidget(self._tool_combo)
        toolbar.addStretch()
        root.addLayout(toolbar)

        self._canvas = _BodymapCanvasV2()
        self._canvas.set_gender(self.get_gender())
        self._canvas.set_marks(marks)
        self._canvas.set_read_only(read_only)
        self._canvas.marks_changed.connect(self._refresh_stats)
        root.addWidget(self._canvas, 1)

        self._stats = QLabel()
        root.addWidget(self._stats)
        self._refresh_stats()

        if read_only:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
            if close_btn:
                close_btn.setText("Закрыть")
            buttons.rejected.connect(self.reject)
        else:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
            cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
            if save_btn:
                save_btn.setText("Применить")
            if cancel_btn:
                cancel_btn.setText("Отмена")
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._on_tool_changed()

    def get_gender(self) -> str:
        return "M" if self._gender_combo.currentData() != "F" else "F"

    def get_marks(self) -> list[dict[str, Any]]:
        return self._canvas.get_marks()

    def _on_gender_changed(self) -> None:
        self._canvas.set_gender(self.get_gender())
        self._refresh_stats()

    def _on_tool_changed(self) -> None:
        self._canvas.set_active_tool(str(self._tool_combo.currentData() or "WOUND_X"))

    def _refresh_stats(self) -> None:
        marks = self._canvas.get_marks()
        active = _active_silhouettes(self.get_gender())
        active_marks = [item for item in marks if item.get("silhouette") in active]
        self._stats.setText(
            f"Итого: {len(marks)}. Активные ({'М' if self.get_gender() == 'M' else 'Ж'}): "
            f"{len(active_marks)} ({_marks_stats(active_marks)})."
        )


class _BodymapCanvasV2(QWidget):
    marks_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(920, 600)
        self.setMouseTracking(True)
        self._gender = "M"
        self._active_tool = "WOUND_X"
        self._read_only = False
        self._marks: list[dict[str, Any]] = []
        self._drag_start: QPointF | None = None
        self._drag_current: QPointF | None = None
        self._drag_silhouette: str | None = None
        self._hover_point: QPointF | None = None
        self._hover_silhouette: str | None = None
        self._silhouette_pixmaps = _load_silhouette_pixmaps()
        self._silhouette_rects: dict[str, QRectF] = {}
        self._body_rects: dict[str, QRectF] = {}
        self._body_paths: dict[str, QPainterPath] = {}

    def set_gender(self, gender: str) -> None:
        self._gender = "M" if str(gender).upper() != "F" else "F"
        self.update()

    def set_active_tool(self, tool: str) -> None:
        self._active_tool = tool if tool in {item[1] for item in _TOOL_ITEMS} else "WOUND_X"

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only

    def set_marks(self, marks: list[dict[str, Any]]) -> None:
        self._marks = [self._normalize_mark(item) for item in marks]
        self.update()
        self.marks_changed.emit()

    def get_marks(self) -> list[dict[str, Any]]:
        return [self._normalize_mark(item) for item in self._marks]

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._read_only:
            return
        if event.button() == Qt.MouseButton.RightButton:
            self._remove_nearest(event.position())
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        hit = self._resolve_hit(event.position())
        if hit is None:
            return
        silhouette, norm = hit
        if silhouette not in _active_silhouettes(self._gender):
            return
        if self._active_tool in _POINT_TOOLS:
            self._add_point_mark(silhouette=silhouette, norm=norm)
            return
        if self._active_tool in _DRAG_TOOLS:
            self._drag_start = event.position()
            self._drag_current = event.position()
            self._drag_silhouette = silhouette
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._hover_point = event.position()
        hit = self._resolve_hit(event.position())
        self._hover_silhouette = hit[0] if hit is not None else None
        if self._drag_start is not None:
            self._drag_current = event.position()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._read_only or event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag_start is None or self._drag_current is None or self._drag_silhouette is None:
            return
        start_hit = self._resolve_hit(self._drag_start)
        end_hit = self._resolve_hit(self._drag_current)
        if start_hit is None or end_hit is None:
            self._clear_drag()
            return
        if start_hit[0] != self._drag_silhouette or end_hit[0] != self._drag_silhouette:
            self._clear_drag()
            return
        if self._drag_silhouette not in _active_silhouettes(self._gender):
            self._clear_drag()
            return

        start_norm = start_hit[1]
        end_norm = end_hit[1]
        center_x = (start_norm.x() + end_norm.x()) / 2
        center_y = (start_norm.y() + end_norm.y()) / 2
        shape_json = {"x2": _clamp01(end_norm.x()), "y2": _clamp01(end_norm.y())}
        self._marks.append(
            {
                "annotation_type": self._active_tool,
                "x": _clamp01(center_x),
                "y": _clamp01(center_y),
                "silhouette": self._drag_silhouette,
                "note": "",
                "shape_json": shape_json,
            }
        )
        self._clear_drag()
        self.marks_changed.emit()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, on=True)
        painter.fillRect(self.rect(), QColor("#fcfcfc"))

        self._layout_silhouettes()
        active = _active_silhouettes(self._gender)
        for name in _SILHOUETTE_ORDER:
            slot = self._silhouette_rects[name]
            body_rect = self._body_rects[name]
            path = self._body_paths[name]
            pixmap = self._silhouette_pixmaps.get(name)
            painter.setPen(QPen(QColor("#d8d0c6"), 1))
            painter.setBrush(QColor("#f7f5f1"))
            painter.drawRoundedRect(slot, 6, 6)

            if pixmap and not pixmap.isNull():
                scaled = pixmap.scaled(
                    body_rect.size().toSize(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                x = body_rect.x() + (body_rect.width() - scaled.width()) / 2
                y = body_rect.y() + (body_rect.height() - scaled.height()) / 2
                painter.drawPixmap(int(x), int(y), scaled)
            else:
                painter.setPen(QPen(QColor("#8c8c8c"), 1.4))
                painter.setBrush(QColor("#f2eee7"))
                painter.drawPath(path)

            if name not in active:
                painter.save()
                painter.setBrush(QColor(55, 58, 61, 90))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(slot, 6, 6)
                painter.restore()

            painter.setPen(QColor("#6d6d6d"))
            label_map = {
                "male_front": "Мужчина спереди",
                "male_back": "Мужчина сзади",
                "female_front": "Женщина спереди",
                "female_back": "Женщина сзади",
            }
            painter.drawText(QRectF(slot.x() + 6, slot.y() + 4, slot.width() - 12, 18), label_map[name])

        for mark in self._marks:
            self._draw_mark(painter, mark)
        self._draw_preview(painter)

    def _layout_silhouettes(self) -> None:
        margin = 12.0
        gap = 10.0
        available_w = self.width() - 2 * margin - gap * 3
        slot_w = max(120.0, available_w / 4.0)
        slot_h = self.height() - 2 * margin
        for idx, name in enumerate(_SILHOUETTE_ORDER):
            x = margin + idx * (slot_w + gap)
            y = margin
            slot = QRectF(x, y, slot_w, slot_h)
            body_rect = QRectF(
                slot.x() + slot.width() * 0.20,
                slot.y() + slot.height() * 0.08,
                slot.width() * 0.60,
                slot.height() * 0.84,
            )
            is_back = name.endswith("back")
            path = self._build_silhouette_path(body_rect, is_back=is_back)
            self._silhouette_rects[name] = slot
            self._body_rects[name] = body_rect
            self._body_paths[name] = path

    def _resolve_hit(self, point: QPointF) -> tuple[str, QPointF] | None:
        self._layout_silhouettes()
        for name in _SILHOUETTE_ORDER:
            if not self._silhouette_rects[name].contains(point):
                continue
            path = self._body_paths[name]
            if not path.contains(point):
                continue
            body = self._body_rects[name]
            norm = QPointF(
                _clamp01((point.x() - body.x()) / max(1.0, body.width())),
                _clamp01((point.y() - body.y()) / max(1.0, body.height())),
            )
            return name, norm
        return None

    def _add_point_mark(self, *, silhouette: str, norm: QPointF) -> None:
        note = ""
        if self._active_tool == "NOTE_PIN":
            text, ok = QInputDialog.getText(self, "Заметка", "Комментарий:")
            if not ok:
                return
            note = text.strip()
        self._marks.append(
            {
                "annotation_type": self._active_tool,
                "x": _clamp01(norm.x()),
                "y": _clamp01(norm.y()),
                "silhouette": silhouette,
                "note": note,
                "shape_json": {},
            }
        )
        self.marks_changed.emit()
        self.update()

    def _remove_nearest(self, point: QPointF) -> None:
        hit = self._resolve_hit(point)
        if hit is None:
            return
        silhouette = hit[0]
        if silhouette not in _active_silhouettes(self._gender):
            return

        nearest_idx = -1
        nearest_distance = 1e9
        for idx, mark in enumerate(self._marks):
            if mark.get("silhouette") != silhouette:
                continue
            mark_point = self._mark_anchor(mark)
            distance = (mark_point.x() - point.x()) ** 2 + (mark_point.y() - point.y()) ** 2
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_idx = idx
        if nearest_idx < 0 or nearest_distance > 15 * 15:
            return
        self._marks.pop(nearest_idx)
        self.marks_changed.emit()
        self.update()

    def _draw_mark(self, painter: QPainter, mark: dict[str, Any]) -> None:
        silhouette = str(mark.get("silhouette") or "")
        if silhouette not in self._body_rects:
            return
        body = self._body_rects[silhouette]
        x = _clamp01(float(mark.get("x") or 0.5))
        y = _clamp01(float(mark.get("y") or 0.5))
        p = QPointF(body.x() + x * body.width(), body.y() + y * body.height())
        mark_type = str(mark.get("annotation_type") or "NOTE_PIN")
        shape = mark.get("shape_json") or {}
        if not isinstance(shape, dict):
            shape = {}

        if mark_type == "WOUND_X":
            painter.setPen(QPen(QColor("#c0392b"), 2.4))
            painter.drawLine(QPointF(p.x() - 6, p.y() - 6), QPointF(p.x() + 6, p.y() + 6))
            painter.drawLine(QPointF(p.x() - 6, p.y() + 6), QPointF(p.x() + 6, p.y() - 6))
            return
        if mark_type == "NOTE_PIN":
            painter.setPen(QPen(QColor("#1f77b4"), 1.5))
            painter.setBrush(QColor("#6aaee6"))
            painter.drawEllipse(p, 4, 4)
            text = str(mark.get("note") or "").strip()
            if text:
                painter.setPen(QColor("#1f4f7a"))
                painter.drawText(QRectF(p.x() + 6, p.y() - 8, 120, 20), text)
            return
        if mark_type == "TOURNIQUET":
            x2 = _clamp01(float(shape.get("x2", x)))
            y2 = _clamp01(float(shape.get("y2", y)))
            p2 = QPointF(body.x() + x2 * body.width(), body.y() + y2 * body.height())
            painter.setPen(QPen(QColor("#9c640c"), 3))
            painter.drawLine(p, p2)
            return
        if mark_type in {"BURN_HATCH", "AMPUTATION"}:
            x2 = _clamp01(float(shape.get("x2", x)))
            y2 = _clamp01(float(shape.get("y2", y)))
            p2 = QPointF(body.x() + x2 * body.width(), body.y() + y2 * body.height())
            rect = QRectF(QPointF(min(p.x(), p2.x()), min(p.y(), p2.y())), QPointF(max(p.x(), p2.x()), max(p.y(), p2.y())))
            if mark_type == "BURN_HATCH":
                painter.setPen(QPen(QColor("#e67e22"), 2, Qt.PenStyle.DashLine))
                painter.setBrush(QColor(230, 126, 34, 55))
            else:
                painter.setPen(QPen(QColor("#943126"), 2))
                painter.setBrush(QColor(148, 49, 38, 75))
            painter.drawEllipse(rect)

    def _draw_preview(self, painter: QPainter) -> None:
        if self._hover_point is None or self._hover_silhouette is None:
            return
        if self._hover_silhouette not in _active_silhouettes(self._gender):
            return
        painter.setPen(QPen(QColor("#5f6a6a"), 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(95, 106, 106, 90))
        if self._drag_start is not None and self._drag_current is not None:
            if self._active_tool == "TOURNIQUET":
                painter.drawLine(self._drag_start, self._drag_current)
                return
            if self._active_tool in {"BURN_HATCH", "AMPUTATION"}:
                rect = QRectF(self._drag_start, self._drag_current).normalized()
                painter.drawEllipse(rect)
                return
        if self._active_tool in _POINT_TOOLS:
            painter.drawEllipse(self._hover_point, 4, 4)

    def _mark_anchor(self, mark: dict[str, Any]) -> QPointF:
        silhouette = str(mark.get("silhouette") or "")
        body = self._body_rects.get(silhouette)
        if body is None:
            return QPointF(0, 0)
        x = _clamp01(_to_float(mark.get("x"), 0.5))
        y = _clamp01(_to_float(mark.get("y"), 0.5))
        return QPointF(body.x() + x * body.width(), body.y() + y * body.height())

    def _clear_drag(self) -> None:
        self._drag_start = None
        self._drag_current = None
        self._drag_silhouette = None

    def _normalize_mark(self, mark: dict[str, Any]) -> dict[str, Any]:
        annotation_type = str(mark.get("annotation_type") or "NOTE_PIN").upper()
        if annotation_type not in {"WOUND_X", "BURN_HATCH", "AMPUTATION", "TOURNIQUET", "NOTE_PIN"}:
            annotation_type = "NOTE_PIN"
        silhouette = str(mark.get("silhouette") or "male_front").lower()
        if silhouette not in set(_SILHOUETTE_ORDER):
            silhouette = "male_front"
        shape = mark.get("shape_json") or {}
        if not isinstance(shape, dict):
            shape = {}
        return {
            "annotation_type": annotation_type,
            "x": _clamp01(_to_float(mark.get("x"), 0.5)),
            "y": _clamp01(_to_float(mark.get("y"), 0.5)),
            "silhouette": silhouette,
            "note": str(mark.get("note") or ""),
            "shape_json": {k: float(v) for k, v in shape.items() if isinstance(v, (int, float))},
        }

    def _build_silhouette_path(self, body: QRectF, *, is_back: bool) -> QPainterPath:
        cx = body.center().x()
        top = body.top()
        width = body.width()
        height = body.height()
        y_shoulder = top + height * 0.20
        y_waist = top + height * 0.47
        y_hip = top + height * 0.60
        y_crotch = top + height * 0.67
        y_knee = top + height * 0.83
        y_ankle = top + height * 0.97
        shoulder_half = width * 0.24
        waist_half = width * 0.125
        hip_half = width * 0.17
        ankle_outer = width * 0.075
        ankle_inner = width * 0.028
        arm_width = width * 0.09
        head_width = width * 0.20
        head_height = height * 0.15

        path = QPainterPath()
        head_rect = QRectF(cx - head_width / 2, top + 2, head_width, head_height)
        path.addEllipse(head_rect)
        neck_rect = QRectF(cx - head_width * 0.20, top + head_height, head_width * 0.40, head_height * 0.22)
        path.addRoundedRect(neck_rect, 4, 4)

        left_arm = QRectF(cx - shoulder_half - arm_width * 1.22, y_shoulder + 5, arm_width, body.height() * 0.34)
        right_arm = QRectF(cx + shoulder_half + arm_width * 0.22, y_shoulder + 5, arm_width, body.height() * 0.34)
        path.addRoundedRect(left_arm, arm_width * 0.45, arm_width * 0.45)
        path.addRoundedRect(right_arm, arm_width * 0.45, arm_width * 0.45)
        path.addEllipse(QRectF(left_arm.center().x() - arm_width * 0.30, left_arm.bottom() - 10, arm_width * 0.6, 12))
        path.addEllipse(QRectF(right_arm.center().x() - arm_width * 0.30, right_arm.bottom() - 10, arm_width * 0.6, 12))

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

        if is_back:
            # Slightly widen shoulder area for back view.
            back = QPainterPath()
            back.addRect(
                QRectF(
                    cx - shoulder_half * 0.8,
                    y_shoulder + 10,
                    shoulder_half * 1.6,
                    height * 0.08,
                )
            )
            path = path.united(back)
        return path
