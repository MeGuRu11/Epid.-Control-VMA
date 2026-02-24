from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication, QWidget

from app.config import Settings


@dataclass(frozen=True)
class UiRuntimeConfig:
    premium_enabled: bool
    density: str
    animation_policy: str
    enable_animations: bool
    enable_background: bool

    @property
    def compact(self) -> bool:
        return self.density == "compact"


def resolve_ui_runtime(window: QWidget | None, app: QApplication, settings: Settings) -> UiRuntimeConfig:
    if not settings.ui_premium_enabled:
        return UiRuntimeConfig(
            premium_enabled=False,
            density=settings.ui_density,
            animation_policy=settings.ui_animation_policy,
            enable_animations=False,
            enable_background=False,
        )

    if settings.ui_animation_policy == "minimal":
        return UiRuntimeConfig(
            premium_enabled=True,
            density=settings.ui_density,
            animation_policy=settings.ui_animation_policy,
            enable_animations=False,
            enable_background=False,
        )

    if settings.ui_animation_policy == "full":
        return UiRuntimeConfig(
            premium_enabled=True,
            density=settings.ui_density,
            animation_policy=settings.ui_animation_policy,
            enable_animations=True,
            enable_background=True,
        )

    # adaptive
    screen = window.screen() if window is not None else app.primaryScreen()
    if screen is None:
        return UiRuntimeConfig(
            premium_enabled=True,
            density=settings.ui_density,
            animation_policy=settings.ui_animation_policy,
            enable_animations=True,
            enable_background=False,
        )

    geometry = screen.availableGeometry()
    dpi = max(screen.logicalDotsPerInchX(), screen.logicalDotsPerInchY())
    width = geometry.width()
    height = geometry.height()
    min_edge = min(width, height)

    high_dpi = dpi >= 144.0
    small_screen = width < 1366 or height < 768
    tiny_screen = min_edge <= 800

    enable_animations = not tiny_screen
    enable_background = not (small_screen or high_dpi)
    return UiRuntimeConfig(
        premium_enabled=True,
        density=settings.ui_density,
        animation_policy=settings.ui_animation_policy,
        enable_animations=enable_animations,
        enable_background=enable_background,
    )


def apply_density_property(widget: QWidget, settings: Settings) -> None:
    widget.setProperty("uiDensity", settings.ui_density)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
