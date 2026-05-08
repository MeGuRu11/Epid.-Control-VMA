"""Тесты для утилиты responsive_direction.

Чистая функция — не требует Qt event loop.
Все edge-cases проверяются без show()/processEvents().
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QBoxLayout

from app.ui.widgets.responsive import (
    FILTER_BREAKPOINT_PX,
    HERO_BREAKPOINT_PX,
    responsive_direction,
)

LTR = QBoxLayout.Direction.LeftToRight
TTB = QBoxLayout.Direction.TopToBottom


# ------------------------------------------------------------------
# Базовые случаи
# ------------------------------------------------------------------


def test_wide_enough_returns_left_to_right() -> None:
    assert responsive_direction(1600, 900, 820) == LTR


def test_too_narrow_returns_top_to_bottom() -> None:
    assert responsive_direction(520, 900, 820) == TTB


def test_exactly_at_threshold_returns_left_to_right() -> None:
    # Граничное условие: >= threshold → LTR
    assert responsive_direction(820, 820, 820) == LTR


def test_one_pixel_below_threshold_returns_top_to_bottom() -> None:
    assert responsive_direction(819, 820, 820) == TTB


# ------------------------------------------------------------------
# Защита от нулевого minimumSizeHint (headless Qt)
# ------------------------------------------------------------------


def test_zero_computed_uses_fallback_breakpoint() -> None:
    # minimumSizeHint() вернул 0 → computed = 0,
    # но fallback = 820, поэтому required = 820.
    assert responsive_direction(800, 0, 820) == TTB
    assert responsive_direction(820, 0, 820) == LTR


def test_computed_below_fallback_uses_fallback() -> None:
    # computed = 50, fallback = 820 → required = 820
    assert responsive_direction(500, 50, 820) == TTB
    assert responsive_direction(900, 50, 820) == LTR


def test_computed_above_fallback_uses_computed() -> None:
    # В production minimumSizeHint() > fallback → используем computed.
    assert responsive_direction(950, 1000, 820) == TTB
    assert responsive_direction(1100, 1000, 820) == LTR


# ------------------------------------------------------------------
# Граничные значения: нулевые и отрицательные ширины
# ------------------------------------------------------------------


def test_zero_current_width_always_returns_top_to_bottom() -> None:
    assert responsive_direction(0, 0, 820) == TTB


def test_negative_current_width_returns_top_to_bottom() -> None:
    # На практике width() < 0 не бывает, но функция должна быть robust.
    assert responsive_direction(-1, 0, 820) == TTB


def test_zero_fallback_breakpoint_uses_computed() -> None:
    # Если breakpoint = 0, поведение определяется только computed.
    assert responsive_direction(100, 200, 0) == TTB
    assert responsive_direction(300, 200, 0) == LTR


# ------------------------------------------------------------------
# Константы-breakpoints: проверяем, что они разумны для тестовых сценариев
# (520px → TTB, 1600-1700px → LTR)
# ------------------------------------------------------------------


@pytest.mark.parametrize("narrow", [400, 480, 520, 600])
def test_hero_breakpoint_yields_ttb_for_narrow_widths(narrow: int) -> None:
    assert responsive_direction(narrow, 0, HERO_BREAKPOINT_PX) == TTB


@pytest.mark.parametrize("wide", [900, 1200, 1600, 1700])
def test_hero_breakpoint_yields_ltr_for_wide_widths(wide: int) -> None:
    assert responsive_direction(wide, 0, HERO_BREAKPOINT_PX) == LTR


@pytest.mark.parametrize("narrow", [400, 480, 520, 600])
def test_filter_breakpoint_yields_ttb_for_narrow_widths(narrow: int) -> None:
    assert responsive_direction(narrow, 0, FILTER_BREAKPOINT_PX) == TTB


@pytest.mark.parametrize("wide", [900, 1200, 1600, 1700])
def test_filter_breakpoint_yields_ltr_for_wide_widths(wide: int) -> None:
    assert responsive_direction(wide, 0, FILTER_BREAKPOINT_PX) == LTR
