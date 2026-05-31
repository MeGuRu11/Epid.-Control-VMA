"""Единая геометрия bodymap.

Нормализованные координаты (x_norm, y_norm in [0, 1]) задаются относительно
рабочей области внутри слота силуэта с фиксированными отступами.
"""
from __future__ import annotations

SLOT_PAD_LEFT = 0.06
SLOT_PAD_TOP = 0.03
SLOT_EFFECTIVE_W = 0.88
SLOT_EFFECTIVE_H = 0.94


def bodymap_slot_rect(
    *,
    panel_width: float,
    canvas_height: float,
    is_back: bool,
) -> tuple[float, float, float, float]:
    panel_offset = panel_width if is_back else 0.0
    return (
        panel_offset + panel_width * SLOT_PAD_LEFT,
        canvas_height * SLOT_PAD_TOP,
        panel_width * SLOT_EFFECTIVE_W,
        canvas_height * SLOT_EFFECTIVE_H,
    )


def fit_rect_keep_aspect(
    *,
    container_x: float,
    container_y: float,
    container_w: float,
    container_h: float,
    source_w: float,
    source_h: float,
) -> tuple[float, float, float, float]:
    if source_w <= 0 or source_h <= 0 or container_w <= 0 or container_h <= 0:
        return container_x, container_y, max(1.0, container_w), max(1.0, container_h)
    scale = min(container_w / source_w, container_h / source_h)
    width = max(1.0, source_w * scale)
    height = max(1.0, source_h * scale)
    x = container_x + (container_w - width) / 2.0
    y = container_y + (container_h - height) / 2.0
    return x, y, width, height


def denormalize_for_pil(
    x_norm: float,
    y_norm: float,
    *,
    panel_width_px: float,
    canvas_height_px: float,
    is_back: bool,
    source_width_px: float | None = None,
    source_height_px: float | None = None,
) -> tuple[float, float]:
    """Конвертирует нормализованные координаты UI в пиксели PIL canvas."""
    left_px, top_px, width_px, height_px = bodymap_slot_rect(
        panel_width=panel_width_px,
        canvas_height=canvas_height_px,
        is_back=is_back,
    )
    if source_width_px is not None and source_height_px is not None:
        left_px, top_px, width_px, height_px = fit_rect_keep_aspect(
            container_x=left_px,
            container_y=top_px,
            container_w=width_px,
            container_h=height_px,
            source_w=source_width_px,
            source_h=source_height_px,
        )

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
    left_pt, top_pt, width_pt, height_pt = bodymap_slot_rect(
        panel_width=panel_width_pt,
        canvas_height=total_height_pt,
        is_back=is_back,
    )

    x = left_pt + x_norm * width_pt
    y = total_height_pt - (top_pt + y_norm * height_pt)
    return x, y
