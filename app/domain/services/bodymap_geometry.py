"""Единая геометрия bodymap.

Нормализованные координаты (x_norm, y_norm in [0, 1]) задаются относительно
рабочей области внутри слота силуэта с фиксированными отступами.
"""
from __future__ import annotations

SLOT_PAD_LEFT = 0.06
SLOT_PAD_TOP = 0.03
SLOT_EFFECTIVE_W = 0.88
SLOT_EFFECTIVE_H = 0.94


def denormalize_for_pil(
    x_norm: float,
    y_norm: float,
    *,
    panel_width_px: float,
    canvas_height_px: float,
    is_back: bool,
) -> tuple[float, float]:
    """Конвертирует нормализованные координаты UI в пиксели PIL canvas."""
    panel_offset = panel_width_px if is_back else 0.0

    left_px = panel_offset + panel_width_px * SLOT_PAD_LEFT
    top_px = canvas_height_px * SLOT_PAD_TOP
    width_px = panel_width_px * SLOT_EFFECTIVE_W
    height_px = canvas_height_px * SLOT_EFFECTIVE_H

    x = left_px + x_norm * width_px
    y = top_px + y_norm * height_px
    return x, y


def denormalize_for_drawing(
    x_norm: float,
    y_norm: float,
    *,
    panel_width_pt: float,
    total_height_pt: float,
    is_back: bool,
) -> tuple[float, float]:
    """Конвертирует координаты UI в ReportLab Drawing, где Y растёт вверх."""
    panel_offset = panel_width_pt if is_back else 0.0

    left_pt = panel_offset + panel_width_pt * SLOT_PAD_LEFT
    top_pt = total_height_pt * SLOT_PAD_TOP
    width_pt = panel_width_pt * SLOT_EFFECTIVE_W
    height_pt = total_height_pt * SLOT_EFFECTIVE_H

    x = left_pt + x_norm * width_pt
    y = total_height_pt - (top_pt + y_norm * height_pt)
    return x, y
