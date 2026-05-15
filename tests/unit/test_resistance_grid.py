from __future__ import annotations

from typing import Any


def test_resistance_grid_set_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.resistance_grid import ResistanceGrid

    grid = ResistanceGrid()
    qtbot.addWidget(grid)

    grid.set_data({"ECO - E. coli": {"AMX - Amoxicillin": {"S": 1, "I": 1, "R": 3, "total": 5}}})

    assert grid.rowCount() == 1
    assert grid.columnCount() == 1


def test_resistance_grid_empty_data_no_crash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.resistance_grid import ResistanceGrid

    grid = ResistanceGrid()
    qtbot.addWidget(grid)

    grid.set_data({})

    assert grid.rowCount() == 0
    assert grid.columnCount() == 0


def test_resistance_grid_low_count_shows_dash(qtbot: Any) -> None:
    from app.ui.analytics.widgets.resistance_grid import ResistanceGrid

    grid = ResistanceGrid()
    qtbot.addWidget(grid)

    grid.set_data({"ECO - E. coli": {"AMX - Amoxicillin": {"S": 1, "I": 0, "R": 3, "total": 4}}})

    assert grid.item(0, 0).text() == "\u2014"


def test_resistance_grid_high_resistance_red_background(qtbot: Any) -> None:
    from app.ui.analytics.widgets.resistance_grid import ResistanceGrid

    grid = ResistanceGrid()
    qtbot.addWidget(grid)

    grid.set_data({"ECO - E. coli": {"AMX - Amoxicillin": {"S": 1, "I": 0, "R": 4, "total": 5}}})

    item = grid.item(0, 0)
    assert item.text() == "80%"
    assert item.background().color().name().lower() == "#fecaca"
