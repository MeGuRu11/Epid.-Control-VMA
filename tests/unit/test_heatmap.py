from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt


def test_heatmap_set_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.heatmap import Heatmap

    heatmap = Heatmap()
    qtbot.addWidget(heatmap)

    heatmap.set_data({"ICU": {"ECO - E. coli": 3}}, ["ECO - E. coli"])

    assert heatmap is not None


def test_heatmap_empty_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.heatmap import Heatmap

    heatmap = Heatmap()
    qtbot.addWidget(heatmap)

    heatmap.set_data({}, [])

    assert heatmap is not None


def test_heatmap_cell_clicked_signal(qtbot: Any) -> None:
    from app.ui.analytics.widgets.heatmap import Heatmap, HeatmapCell

    heatmap = Heatmap()
    qtbot.addWidget(heatmap)
    heatmap.set_data({"ICU": {"ECO - E. coli": 3}}, ["ECO - E. coli"])
    cell = heatmap.findChild(HeatmapCell)
    assert cell is not None

    emitted: list[tuple[str, str]] = []
    heatmap.cell_clicked.connect(lambda dept, micro: emitted.append((dept, micro)))
    qtbot.mouseClick(cell, Qt.MouseButton.LeftButton)

    assert emitted == [("ICU", "ECO - E. coli")]
