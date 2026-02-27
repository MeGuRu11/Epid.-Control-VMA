from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGraphicsEllipseItem, QGraphicsScene, QGraphicsView


@dataclass
class Particle:
    item: QGraphicsEllipseItem
    radius: float
    vx: float
    vy: float
    phase: float


class MedicalBackground(QGraphicsView):
    """Lightweight medical background with subtle motion."""

    def __init__(self, parent=None, intensity: str = "subtle"):
        super().__init__(parent)
        self.intensity = intensity
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheNone)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._particles: list[Particle] = []
        self._t = 0.0
        self._mx = 0.0
        self._my = 0.0

        fps = 32 if intensity == "subtle" else 48
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / fps))
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._build()

    def _build(self):
        self._scene.clear()
        self._particles.clear()

        is_showcase = self.intensity == "showcase"
        count = 24 if not is_showcase else 44
        min_r = 8 if not is_showcase else 9
        max_r = 30 if not is_showcase else 40
        for _ in range(count):
            radius = random.uniform(min_r, max_r)
            item = QGraphicsEllipseItem(0, 0, radius, radius)
            item.setPos(random.uniform(0, 1200), random.uniform(0, 800))

            alpha = random.randint(28, 62) if not is_showcase else random.randint(40, 90)
            fill = QColor("#A1E3D8")
            fill.setAlpha(alpha)
            item.setBrush(QBrush(fill))

            pen = QPen(QColor("#6FB9AD"))
            pen_alpha = 60 if not is_showcase else 92
            pen_color = QColor("#6FB9AD")
            pen_color.setAlpha(pen_alpha)
            pen.setColor(pen_color)
            pen.setWidth(1)
            item.setPen(pen)

            self._scene.addItem(item)
            self._particles.append(
                Particle(
                    item=item,
                    radius=radius,
                    vx=random.uniform(-0.42, 0.42) if not is_showcase else random.uniform(-1.05, 1.05),
                    vy=random.uniform(-0.32, 0.32) if not is_showcase else random.uniform(-0.82, 0.82),
                    phase=random.uniform(0, math.tau),
                )
            )

        pulse_size = 220 if not is_showcase else 300
        self._pulse = QGraphicsEllipseItem(0, 0, pulse_size, pulse_size)
        self._pulse.setBrush(QBrush(QColor(0, 0, 0, 0)))
        pulse_pen = QPen(QColor("#61C9B6"))
        pulse_pen.setWidth(1 if not is_showcase else 2)
        self._pulse.setPen(pulse_pen)
        self._pulse.setZValue(-1)
        self._scene.addItem(self._pulse)
        # Secondary ring makes motion more visible without adding visual noise.
        self._pulse2 = QGraphicsEllipseItem(0, 0, pulse_size * 0.78, pulse_size * 0.78)
        self._pulse2.setBrush(QBrush(QColor(0, 0, 0, 0)))
        pulse2_pen = QPen(QColor("#8FDCCF"))
        pulse2_pen.setWidth(1)
        self._pulse2.setPen(pulse2_pen)
        self._pulse2.setZValue(-1)
        self._scene.addItem(self._pulse2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())

    def mouseMoveEvent(self, event):
        point = event.position()
        self._mx = float(point.x())
        self._my = float(point.y())
        super().mouseMoveEvent(event)

    def _tick(self):
        dt = self._timer.interval() / 1000.0
        self._t += dt
        width = max(1.0, float(self.viewport().width()))
        height = max(1.0, float(self.viewport().height()))

        is_showcase = self.intensity == "showcase"
        amp = 14 if not is_showcase else 32
        base_radius = 110 if not is_showcase else 150
        pulse_radius = base_radius + amp * math.sin(self._t * 1.1)
        self._pulse.setRect(0, 0, pulse_radius * 2, pulse_radius * 2)
        self._pulse.setPos(width * 0.5 - pulse_radius, height * 0.38 - pulse_radius)
        pulse2_radius = pulse_radius * (0.62 + 0.13 * math.sin(self._t * 2.0 + 0.8))
        self._pulse2.setRect(0, 0, pulse2_radius * 2, pulse2_radius * 2)
        self._pulse2.setPos(width * 0.5 - pulse2_radius, height * 0.38 - pulse2_radius)

        pen = self._pulse.pen()
        alpha = int((28 if not is_showcase else 42) + (34 if not is_showcase else 84) * (0.5 + 0.5 * math.sin(self._t * 1.2)))
        pulse_color = QColor("#61C9B6")
        pulse_color.setAlpha(alpha)
        pen.setColor(pulse_color)
        self._pulse.setPen(pen)
        pen2 = self._pulse2.pen()
        pulse2_color = QColor("#8FDCCF")
        pulse2_color.setAlpha(int(alpha * 0.72))
        pen2.setColor(pulse2_color)
        self._pulse2.setPen(pen2)

        ax = (self._mx - width * 0.5) / width
        ay = (self._my - height * 0.5) / height
        parallax = 0.14 if not is_showcase else 0.34

        for particle in self._particles:
            item = particle.item
            pos = item.pos()
            drift = math.sin(self._t * 1.35 + particle.phase) * (0.22 if not is_showcase else 0.78)
            x = pos.x() + particle.vx + ax * parallax + drift * 0.45
            y = pos.y() + particle.vy + ay * parallax + drift * 0.32

            wrap = 50
            if x < -wrap:
                x = width + wrap
            if x > width + wrap:
                x = -wrap
            if y < -wrap:
                y = height + wrap
            if y > height + wrap:
                y = -wrap

            scale_amp = 0.08 if not is_showcase else 0.18
            item.setScale(1.0 + scale_amp * math.sin(self._t * 1.6 + particle.phase))
            item.setPos(QPointF(x, y))
