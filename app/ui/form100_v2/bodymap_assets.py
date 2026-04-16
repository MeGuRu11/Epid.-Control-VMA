from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

SILHOUETTE_ORDER = ("male_front", "male_back")
_TEMPLATE_IMAGES: tuple[str, ...] = ("form_100_bd.png", "form_100_body.png")
_TWO_FIGURE_SPLIT_MIN_RATIO = 0.6
_LEGACY_STRIP_RATIO = 2.2
_CENTER_SCAN_LEFT = 0.3
_CENTER_SCAN_RIGHT = 0.7
_SPLIT_PADDING = 12
_CONTENT_LUMINANCE_THRESHOLD = 235
_CONTENT_COLUMN_MIN_PIXELS = 18


def get_bodymap_image_root() -> Path:
    meipass = cast(object, getattr(sys, "_MEIPASS", None))
    if getattr(sys, "frozen", False) and isinstance(meipass, str):
        return Path(meipass) / "app" / "image" / "main"
    return Path(__file__).resolve().parents[2] / "image" / "main"


def load_bodymap_template_pixmap() -> QPixmap | None:
    image_root = get_bodymap_image_root()
    for file_name in _TEMPLATE_IMAGES:
        image_path = image_root / file_name
        if not image_path.exists():
            continue
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            return pixmap
    return None


def split_bodymap_template(
    template: QPixmap,
    normalize: Callable[[QPixmap], QPixmap],
) -> dict[str, QPixmap]:
    width = template.width()
    height = template.height()
    if width <= 0 or height <= 0:
        return {}

    if width >= int(height * _LEGACY_STRIP_RATIO):
        return _build_legacy_strip(template, normalize)

    if width >= int(height * _TWO_FIGURE_SPLIT_MIN_RATIO):
        return _build_dual_silhouettes(template, normalize)

    normalized = normalize(template.copy(0, 0, width, height))
    return dict.fromkeys(SILHOUETTE_ORDER, normalized)


def _build_legacy_strip(
    template: QPixmap,
    normalize: Callable[[QPixmap], QPixmap],
) -> dict[str, QPixmap]:
    segment = max(1, template.width() // 4)
    front = template.copy(0, 0, segment, template.height())
    back = template.copy(segment, 0, segment, template.height())
    if front.isNull() or back.isNull():
        return {}
    return {
        "male_front": normalize(front),
        "male_back": normalize(back),
    }


def _build_dual_silhouettes(
    template: QPixmap,
    normalize: Callable[[QPixmap], QPixmap],
) -> dict[str, QPixmap]:
    image = template.toImage()
    split = detect_bodymap_split_column(image)
    if split is None:
        split = max(1, template.width() // 2)
    front_rect = _content_crop_rect(image, 0, split)
    back_rect = _content_crop_rect(image, split, template.width())
    if front_rect is None or back_rect is None:
        front_end = max(1, split - _SPLIT_PADDING)
        back_start = min(template.width() - 1, split + _SPLIT_PADDING)
        front = template.copy(0, 0, front_end, template.height())
        back = template.copy(back_start, 0, max(1, template.width() - back_start), template.height())
    else:
        front = template.copy(*front_rect)
        back = template.copy(*back_rect)
    front = _add_transparent_padding(front, _SPLIT_PADDING)
    back = _add_transparent_padding(back, _SPLIT_PADDING)
    if front.isNull() or back.isNull():
        return {}
    return {
        "male_front": normalize(front),
        "male_back": normalize(back),
    }


def detect_bodymap_split_column(image: QImage) -> int | None:
    width = image.width()
    height = image.height()
    if width <= 0 or height <= 0:
        return None

    scan_start = max(1, int(width * _CENTER_SCAN_LEFT))
    scan_end = min(width - 1, int(width * _CENTER_SCAN_RIGHT))
    if scan_start >= scan_end:
        return None

    column_scores = []
    for x in range(scan_start, scan_end + 1):
        column_scores.append((x, _column_content_score(image, x)))
    if not column_scores:
        return None

    return min(column_scores, key=lambda item: (item[1], abs(item[0] - (width // 2))))[0]


def _column_content_score(image: QImage, x: int) -> int:
    score = 0
    for y in range(image.height()):
        color = QColor(image.pixelColor(x, y))
        if color.alpha() == 0:
            continue
        luminance = (color.red() + color.green() + color.blue()) // 3
        if luminance < _CONTENT_LUMINANCE_THRESHOLD:
            score += 1
    return score if score >= _CONTENT_COLUMN_MIN_PIXELS else 0


def _content_crop_rect(image: QImage, start_x: int, end_x: int) -> tuple[int, int, int, int] | None:
    width = image.width()
    height = image.height()
    start = max(0, min(start_x, width - 1))
    end = max(start + 1, min(end_x, width))
    x_columns = [x for x in range(start, end) if _column_content_score(image, x) > 0]
    y_rows = [y for y in range(height) if _row_content_score(image, y, start, end) > 0]
    if not x_columns or not y_rows:
        return None
    crop_left = max(0, min(x_columns) - _SPLIT_PADDING)
    crop_top = max(0, min(y_rows) - _SPLIT_PADDING)
    crop_right = min(width - 1, max(x_columns) + _SPLIT_PADDING)
    crop_bottom = min(height - 1, max(y_rows) + _SPLIT_PADDING)
    return crop_left, crop_top, max(1, crop_right - crop_left + 1), max(1, crop_bottom - crop_top + 1)


def _row_content_score(image: QImage, y: int, start_x: int, end_x: int) -> int:
    score = 0
    for x in range(start_x, end_x):
        color = QColor(image.pixelColor(x, y))
        if color.alpha() == 0:
            continue
        luminance = (color.red() + color.green() + color.blue()) // 3
        if luminance < _CONTENT_LUMINANCE_THRESHOLD:
            score += 1
    return score if score >= _CONTENT_COLUMN_MIN_PIXELS else 0


def _add_transparent_padding(pixmap: QPixmap, padding: int) -> QPixmap:
    if pixmap.isNull() or padding <= 0:
        return pixmap
    canvas = QPixmap(pixmap.width() + padding * 2, pixmap.height() + padding * 2)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawPixmap(padding, padding, pixmap)
    painter.end()
    return canvas
