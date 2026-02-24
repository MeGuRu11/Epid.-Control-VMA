from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsView, QWidget


@dataclass
class _Particle:
    item: QGraphicsEllipseItem
    vx: float
    vy: float
    phase: float


class MedicalBackground(QGraphicsView):
    def __init__(self, parent: QWidget | None = None, *, intensity: str = "subtle") -> None:
        super().__init__(parent)
        self.intensity = intensity
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheNone)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._particles: list[_Particle] = []
        self._t = 0.0
        self._mx = 0.0
        self._my = 0.0

        fps = 28 if intensity == "subtle" else 42
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / fps))
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._build()

    def _build(self) -> None:
        self._scene.clear()
        self._particles.clear()
        showcase = self.intensity == "showcase"
        count = 18 if not showcase else 34
        min_r = 8 if not showcase else 10
        max_r = 28 if not showcase else 38
        for _ in range(count):
            radius = random.uniform(min_r, max_r)
            item = QGraphicsEllipseItem(0, 0, radius, radius)
            item.setPos(random.uniform(0, 1200), random.uniform(0, 800))
            fill = QColor("#A1E3D8")
            fill.setAlpha(random.randint(26, 58) if not showcase else random.randint(35, 82))
            item.setBrush(QBrush(fill))
            pen_color = QColor("#6FB9AD")
            pen_color.setAlpha(54 if not showcase else 86)
            item.setPen(QPen(pen_color, 1))
            self._scene.addItem(item)
            self._particles.append(
                _Particle(
                    item=item,
                    vx=random.uniform(-0.36, 0.36) if not showcase else random.uniform(-0.92, 0.92),
                    vy=random.uniform(-0.28, 0.28) if not showcase else random.uniform(-0.72, 0.72),
                    phase=random.uniform(0, math.tau),
                )
            )

        pulse = 220 if not showcase else 300
        self._pulse = QGraphicsEllipseItem(0, 0, pulse, pulse)
        self._pulse.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self._pulse.setPen(QPen(QColor("#61C9B6"), 1 if not showcase else 2))
        self._pulse.setZValue(-1)
        self._scene.addItem(self._pulse)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        point = event.position()
        self._mx = float(point.x())
        self._my = float(point.y())
        super().mouseMoveEvent(event)

    def _tick(self) -> None:
        dt = self._timer.interval() / 1000.0
        self._t += dt
        width = max(1.0, float(self.viewport().width()))
        height = max(1.0, float(self.viewport().height()))
        showcase = self.intensity == "showcase"

        amp = 12 if not showcase else 28
        base = 108 if not showcase else 146
        radius = base + amp * math.sin(self._t * 1.1)
        self._pulse.setRect(0, 0, radius * 2, radius * 2)
        self._pulse.setPos(width * 0.52 - radius, height * 0.36 - radius)
        pulse_pen = self._pulse.pen()
        color = QColor("#61C9B6")
        color.setAlpha(int((26 if not showcase else 38) + (32 if not showcase else 72) * (0.5 + 0.5 * math.sin(self._t))))
        pulse_pen.setColor(color)
        self._pulse.setPen(pulse_pen)

        ax = (self._mx - width * 0.5) / width
        ay = (self._my - height * 0.5) / height
        parallax = 0.12 if not showcase else 0.30
        for particle in self._particles:
            item = particle.item
            pos = item.pos()
            drift = math.sin(self._t * 1.3 + particle.phase) * (0.22 if not showcase else 0.70)
            x = pos.x() + particle.vx + ax * parallax + drift * 0.42
            y = pos.y() + particle.vy + ay * parallax + drift * 0.28
            wrap = 50
            if x < -wrap:
                x = width + wrap
            if x > width + wrap:
                x = -wrap
            if y < -wrap:
                y = height + wrap
            if y > height + wrap:
                y = -wrap
            scale_amp = 0.06 if not showcase else 0.14
            item.setScale(1.0 + scale_amp * math.sin(self._t * 1.5 + particle.phase))
            item.setPos(QPointF(x, y))
