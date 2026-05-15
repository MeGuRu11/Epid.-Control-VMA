from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap


def test_sparkline_instantiates(qtbot: Any) -> None:
    from app.ui.analytics.widgets.sparkline import Sparkline

    sparkline = Sparkline()
    qtbot.addWidget(sparkline)

    assert sparkline is not None


def test_sparkline_set_data_does_not_raise(qtbot: Any) -> None:
    from app.ui.analytics.widgets.sparkline import Sparkline

    sparkline = Sparkline()
    qtbot.addWidget(sparkline)

    sparkline.set_data([1, 4, 2, 7])

    assert sparkline._values == [1.0, 4.0, 2.0, 7.0]


def test_sparkline_empty_data_does_not_crash_paint(qtbot: Any) -> None:
    from app.ui.analytics.widgets.sparkline import Sparkline

    sparkline = Sparkline()
    qtbot.addWidget(sparkline)
    sparkline.set_data([])

    sparkline.render(QPixmap(sparkline.size()))


def test_sparkline_single_value_does_not_crash_paint(qtbot: Any) -> None:
    from app.ui.analytics.widgets.sparkline import Sparkline

    sparkline = Sparkline()
    qtbot.addWidget(sparkline)
    sparkline.set_data([5])

    sparkline.render(QPixmap(sparkline.size()))


def test_sparkline_fixed_size(qtbot: Any) -> None:
    from app.ui.analytics.widgets.sparkline import Sparkline

    sparkline = Sparkline()
    qtbot.addWidget(sparkline)

    assert sparkline.sizeHint() == QSize(70, 28)
    assert sparkline.minimumSize() == QSize(70, 28)
    assert sparkline.maximumSize() == QSize(70, 28)
