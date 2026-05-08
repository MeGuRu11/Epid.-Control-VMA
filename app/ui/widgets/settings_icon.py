"""Кастомная иконка шестерёнки (gear) для кнопки настроек.

Рисуется программно через QSvgRenderer + QPixmap, чтобы:
- не требовать внешних файлов-ресурсов;
- автоматически принимать любой цвет темы;
- корректно рендериться в разных DPI (HiDPI-aware через devicePixelRatio).

Публичный API::

    make_settings_icon(color: QColor, size: int = 20) -> QIcon
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Шестерёнка в стиле Feather Icons (лицензия MIT).
# Цвет stroke заменяется при вызове через _colorize_svg.
_GEAR_SVG_TEMPLATE = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
     fill="none" stroke="{color}" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="3"/>
  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83
           l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21
           a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33
           l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15
           a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9
           a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06
           A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0
           v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06
           a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9
           a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09
           a1.65 1.65 0 0 0-1.51 1z"/>
</svg>
"""


def _colorize_svg(color: QColor) -> bytes:
    """Подставить цвет в SVG-шаблон и вернуть UTF-8 байты."""
    hex_color = color.name()  # '#rrggbb'
    return _GEAR_SVG_TEMPLATE.format(color=hex_color).encode("utf-8")


def make_settings_icon(color: QColor, size: int = 20) -> QIcon:
    """Создать QIcon с шестерёнкой заданного цвета и размера.

    Args:
        color: Цвет stroke (обычно берётся из темы, например ``QColor("#3A3A38")``).
        size:  Сторона квадрата в логических пикселях (масштабируется по DPI).

    Returns:
        QIcon, готовый к передаче в ``QAbstractButton.setIcon()``.
    """
    # HiDPI: рендерим в физических пикселях.
    app = QGuiApplication.instance()
    dpr = app.devicePixelRatio() if app is not None else 1.0  # type: ignore[attr-defined]  # noqa: PGH003
    phys = int(size * dpr)

    svg_bytes = _colorize_svg(color)
    renderer = QSvgRenderer(QByteArray(svg_bytes))

    pixmap = QPixmap(QSize(phys, phys))
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, phys, phys))
    painter.end()

    pixmap.setDevicePixelRatio(dpr)
    return QIcon(pixmap)
