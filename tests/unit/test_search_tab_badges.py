from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from app.application.dto.analytics_dto import AnalyticsSampleRow
from app.application.dto.auth_dto import SessionContext


class _ControllerStub:
    def list_saved_filters(self) -> list[object]:
        return []


def _build_tab(qtbot: Any) -> Any:
    from app.ui.analytics.tabs.search_tab import SearchTab

    tab = SearchTab(
        controller=_ControllerStub(),  # type: ignore[arg-type]
        session=SessionContext(user_id=1, login="tester", role="admin"),
    )
    qtbot.addWidget(tab)
    return tab


def _row(growth_flag: int | None) -> AnalyticsSampleRow:
    return AnalyticsSampleRow(
        lab_sample_id=1,
        lab_no="L1",
        patient_name="Test",
        growth_flag=growth_flag,
    )


def test_positive_row_has_red_background(qtbot: Any) -> None:
    tab = _build_tab(qtbot)

    tab._apply_search_results([_row(1)], {"total": 1, "positives": 1, "positive_share": 1.0})

    item = tab.table.item(0, 0)
    assert item is not None
    assert item.background().color().name().lower() == "#fee2e2"


def test_negative_row_has_no_color(qtbot: Any) -> None:
    tab = _build_tab(qtbot)

    tab._apply_search_results([_row(0)], {"total": 1, "positives": 0, "positive_share": 0.0})

    item = tab.table.item(0, 0)
    assert item is not None
    assert item.background().style() == Qt.BrushStyle.NoBrush


def test_growth_column_shows_da_for_positive(qtbot: Any) -> None:
    tab = _build_tab(qtbot)

    tab._apply_search_results([_row(1)], {"total": 1, "positives": 1, "positive_share": 1.0})

    growth_col = 9
    item = tab.table.item(0, growth_col)
    assert item is not None
    assert item.text() == "Да"
