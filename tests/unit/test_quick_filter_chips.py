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


def test_chip_filter_resets_on_deactivation(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChips

    holder = {"request": AnalyticsSearchRequest()}
    chips = QuickFilterChips(base_request_getter=lambda: holder["request"])
    qtbot.addWidget(chips)

    emitted: list[AnalyticsSearchRequest] = []

    def _remember_request(request: AnalyticsSearchRequest) -> None:
        emitted.append(request)
        holder["request"] = request

    chips.filter_changed.connect(_remember_request)

    chips._chips[0].setChecked(True)
    assert emitted[-1].growth_flag == 1

    chips._chips[0].setChecked(False)
    assert emitted[-1].growth_flag is None


def test_material_chips_are_mutually_exclusive(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChips

    chips = QuickFilterChips(
        base_request_getter=AnalyticsSearchRequest,
        material_type_ids={"кровь": 7, "рана": 8},
    )
    qtbot.addWidget(chips)

    chips._chips[1].setChecked(True)
    chips._chips[2].setChecked(True)

    assert not chips._chips[1].isChecked()
    assert chips._chips[2].isChecked()


def test_base_request_not_contaminated_after_chip_toggle(qtbot: Any) -> None:
    from app.ui.analytics.widgets.quick_filter_chips import QuickFilterChips

    base = AnalyticsSearchRequest()
    chips = QuickFilterChips(base_request_getter=lambda: base)
    qtbot.addWidget(chips)

    chips._chips[0].setChecked(True)
    chips._chips[0].setChecked(False)

    assert base.growth_flag is None


class _ReferenceServiceStub:
    def list_material_types(self) -> list[object]:
        return []


class _MicrobiologyControllerStub:
    reference_service = _ReferenceServiceStub()

    def get_aggregates(self, request: AnalyticsSearchRequest) -> dict[str, object]:
        return {
            "total": 0,
            "positives": 0,
            "positive_share": 0.0,
            "top_microbes": [],
            "total_microbe_isolations": 0,
            "request": request,
        }

    def get_heatmap_data(
        self,
        _request: AnalyticsSearchRequest,
    ) -> tuple[dict[str, dict[str, int]], list[str]]:
        return {}, []

    def get_resistance_data(
        self,
        _request: AnalyticsSearchRequest,
    ) -> dict[str, dict[str, dict[str, int]]]:
        return {}


def test_microbiology_tab_base_request_separate_from_last(qtbot: Any) -> None:
    from app.ui.analytics.tabs.microbiology_tab import MicrobiologyTab

    tab = MicrobiologyTab(cast(Any, _MicrobiologyControllerStub()))
    qtbot.addWidget(tab)
    original = AnalyticsSearchRequest()

    tab.refresh(original)
    assert tab._base_request is original

    tab._chips._chips[0].setChecked(True)

    assert tab._base_request is original
    assert tab._last_request is not original
    assert tab._last_request is not None
    assert tab._last_request.growth_flag == 1
