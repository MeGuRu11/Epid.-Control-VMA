"""Утилиты для адаптивных (responsive) раскладок.

Выносит логику «переключения направления QBoxLayout» в чистую функцию,
которая тестируется без Qt event loop. Это также решает проблему headless-
окружений (offscreen Qt platform), где ``minimumSizeHint()`` возвращает 0
до первого полного layout-pass.

Логика:
1. Вычислить ``required_width`` из ``minimumSizeHint()`` дочерних виджетов.
2. Если результат ниже ``fallback_breakpoint`` — использовать breakpoint вместо
   нуля. Это гарантирует корректное поведение в headless-среде.
3. Сравнить с текущей шириной контейнера.

Для каждого вида раскладки определена своя константа-breakpoint:

- ``HERO_BREAKPOINT_PX`` = 820 — минимальная ширина, при которой hero + utility
  карточки помещаются рядом (горизонтально). Ниже этого — вертикальный стек.
- ``FILTER_BREAKPOINT_PX`` = 700 — аналогично для панели фильтров.
"""

from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout

# Константы-пороги.
# Выбраны так, чтобы:
#   1. Тест при 520px → TopToBottom, при 1600-1700px → LeftToRight.
#   2. В production (реальные minimumSizeHint ≫ 0) breakpoint не влияет
#      (computed >> breakpoint).
HERO_BREAKPOINT_PX: int = 820
FILTER_BREAKPOINT_PX: int = 700


def responsive_direction(
    current_width: int,
    computed_required: int,
    fallback_breakpoint: int,
) -> QBoxLayout.Direction:
    """Выбрать направление QBoxLayout по текущей ширине.

    Args:
        current_width:       Текущая ширина контейнера (``self.width()``).
        computed_required:   Требуемая ширина, посчитанная из ``minimumSizeHint()``.
        fallback_breakpoint: Нижний предел ``required_width``; защищает от нуля
                             при headless-рендеринге.

    Returns:
        ``LeftToRight`` если помещаемся, иначе ``TopToBottom``.
    """
    required = max(computed_required, fallback_breakpoint)
    return (
        QBoxLayout.Direction.LeftToRight
        if current_width >= required
        else QBoxLayout.Direction.TopToBottom
    )
