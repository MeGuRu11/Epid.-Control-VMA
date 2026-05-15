from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Qt

from app.application.dto.analytics_dto import AnalyticsSearchRequest


def test_chips_instantiate(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChips

    chips = QuickFilterChips(base_request_getter=AnalyticsSearchRequest)
    qtbot.addWidget(chips)

    assert chips is not None


def test_chip_toggle_emits_filter_changed(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChip, QuickFilterChips

    chips = QuickFilterChips(base_request_getter=AnalyticsSearchRequest)
    qtbot.addWidget(chips)
    first_chip = cast(list[QuickFilterChip], chips.findChildren(QuickFilterChip))[0]

    emitted: list[AnalyticsSearchRequest] = []
    chips.filter_changed.connect(emitted.append)
    qtbot.mouseClick(first_chip, Qt.MouseButton.LeftButton)

    assert emitted
    assert emitted[-1].growth_flag == 1


def test_material_chip_can_set_material_type_id(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChip, QuickFilterChips

    chips = QuickFilterChips(
        base_request_getter=AnalyticsSearchRequest,
        material_type_ids={"кровь": 7},
    )
    qtbot.addWidget(chips)
    material_chip = cast(list[QuickFilterChip], chips.findChildren(QuickFilterChip))[1]

    emitted: list[AnalyticsSearchRequest] = []
    chips.filter_changed.connect(emitted.append)
    qtbot.mouseClick(material_chip, Qt.MouseButton.LeftButton)

    assert emitted
    assert emitted[-1].material_type_id == 7
