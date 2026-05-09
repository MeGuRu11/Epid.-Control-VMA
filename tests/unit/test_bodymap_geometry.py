from __future__ import annotations

from app.domain.services.bodymap_geometry import (
    SLOT_EFFECTIVE_H,
    SLOT_EFFECTIVE_W,
    SLOT_PAD_LEFT,
    SLOT_PAD_TOP,
    denormalize_for_drawing,
    denormalize_for_pil,
)


def test_denormalize_center_front() -> None:
    x, y = denormalize_for_pil(
        0.5,
        0.5,
        panel_width_px=400,
        canvas_height_px=800,
        is_back=False,
    )

    assert abs(x - 200.0) < 0.5
    assert abs(y - 400.0) < 0.5


def test_denormalize_top_left_front() -> None:
    x, y = denormalize_for_pil(
        0.0,
        0.0,
        panel_width_px=400,
        canvas_height_px=800,
        is_back=False,
    )

    assert abs(x - 400 * 0.06) < 0.5
    assert abs(y - 800 * 0.03) < 0.5


def test_denormalize_bottom_right_back() -> None:
    x, y = denormalize_for_pil(
        1.0,
        1.0,
        panel_width_px=400,
        canvas_height_px=800,
        is_back=True,
    )

    assert abs(x - 776.0) < 0.5
    assert abs(y - 776.0) < 0.5


def test_drawing_y_is_inverted_vs_pil() -> None:
    _, y_pil = denormalize_for_pil(
        0.5,
        0.9,
        panel_width_px=400,
        canvas_height_px=800,
        is_back=False,
    )
    _, y_rl = denormalize_for_drawing(
        0.5,
        0.9,
        panel_width_pt=400,
        total_height_pt=800,
        is_back=False,
    )

    assert y_rl < 800 * 0.5
    assert abs(y_rl - (800 - y_pil)) < 0.5


def test_constants_match_bodymap_widget() -> None:
    from app.ui.form100_v2.wizard_widgets.bodymap_widget import (
        SLOT_EFFECTIVE_H as W_H,
        SLOT_EFFECTIVE_W as W_W,
        SLOT_PAD_LEFT as W_LEFT,
        SLOT_PAD_TOP as W_TOP,
    )

    assert SLOT_PAD_LEFT == W_LEFT
    assert SLOT_PAD_TOP == W_TOP
    assert SLOT_EFFECTIVE_W == W_W
    assert SLOT_EFFECTIVE_H == W_H
