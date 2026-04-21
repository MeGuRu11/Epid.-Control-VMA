from __future__ import annotations

# mypy: disable-error-code=var-annotated
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QBoxLayout, QLabel, QScrollArea

from app.application.dto.sanitary_dto import SanitarySampleResponse
from app.ui.sanitary.sanitary_dashboard import SanitaryDashboard


class _SanitaryServiceStub:
    def __init__(self, samples_by_department: dict[int, list[SanitarySampleResponse]]) -> None:
        self._samples_by_department = samples_by_department
        self.calls: list[int] = []

    def list_samples_by_department(self, department_id: int) -> list[SanitarySampleResponse]:
        self.calls.append(department_id)
        return list(self._samples_by_department.get(department_id, []))


def _reference_service_stub(*, departments: list[SimpleNamespace] | None = None) -> Any:
    return SimpleNamespace(
        list_departments=lambda: departments
        if departments is not None
        else [
            SimpleNamespace(id=1, name="ОРИТ"),
            SimpleNamespace(id=2, name="Приемное отделение"),
        ],
        list_microorganisms=lambda: [
            SimpleNamespace(id=7, code="STA", name="Staphylococcus aureus"),
            SimpleNamespace(id=9, code="KLB", name="Klebsiella pneumoniae"),
        ],
    )


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _make_sample(
    sample_id: int,
    *,
    department_id: int,
    lab_no: str,
    growth_flag: int | None,
    taken_at: datetime | None,
    sampling_point: str | None = None,
    room: str | None = None,
    medium: str | None = None,
    microorganism_id: int | None = None,
    microorganism_free: str | None = None,
) -> SanitarySampleResponse:
    return SanitarySampleResponse(
        id=sample_id,
        lab_no=lab_no,
        department_id=department_id,
        sampling_point=sampling_point,
        room=room,
        medium=medium,
        taken_at=taken_at,
        growth_flag=growth_flag,
        microorganism_id=microorganism_id,
        microorganism_free=microorganism_free,
    )


def test_sanitary_dashboard_uses_responsive_hero_and_filter_layouts(qapp) -> None:
    dashboard = SanitaryDashboard(
        sanitary_service=cast(Any, _SanitaryServiceStub({})),
        reference_service=cast(Any, _reference_service_stub()),
    )
    dashboard.show()
    qapp.processEvents()

    dashboard.resize(1700, 900)
    qapp.processEvents()
    assert dashboard._hero_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert dashboard._filter_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert isinstance(dashboard._scroll_area, QScrollArea)
    assert dashboard._scroll_area.widgetResizable()
    assert dashboard._list_card.minimumHeight() >= 380
    assert dashboard.list_widget.minimumHeight() >= 240

    dashboard.resize(520, 900)
    qapp.processEvents()
    assert dashboard._hero_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert dashboard._filter_layout.direction() == QBoxLayout.Direction.TopToBottom


def test_sanitary_dashboard_updates_kpis_summary_and_department_card(qapp) -> None:
    sanitary = _SanitaryServiceStub(
        {
            1: [
                _make_sample(
                    1,
                    department_id=1,
                    lab_no="SAN-0001",
                    growth_flag=1,
                    taken_at=_dt(2026, 4, 20, 8, 30),
                    sampling_point="Раковина",
                    room="Палата 1",
                    microorganism_id=7,
                ),
                _make_sample(
                    2,
                    department_id=1,
                    lab_no="SAN-0002",
                    growth_flag=0,
                    taken_at=_dt(2026, 4, 21, 9, 0),
                    medium="Агар",
                ),
                _make_sample(
                    3,
                    department_id=1,
                    lab_no="SAN-0003",
                    growth_flag=None,
                    taken_at=_dt(2026, 4, 21, 11, 15),
                    sampling_point="Стол",
                    room="Процедурная",
                ),
            ],
            2: [
                _make_sample(
                    4,
                    department_id=2,
                    lab_no="SAN-0004",
                    growth_flag=1,
                    taken_at=_dt(2026, 4, 19, 7, 45),
                    microorganism_free="Klebsiella pneumoniae",
                )
            ],
        }
    )
    dashboard = SanitaryDashboard(
        sanitary_service=cast(Any, sanitary),
        reference_service=cast(Any, _reference_service_stub()),
    )
    dashboard.show()
    qapp.processEvents()

    assert dashboard._kpi_widgets["departments"].value_label.text() == "2"
    assert dashboard._kpi_widgets["samples"].value_label.text() == "4"
    assert dashboard._kpi_widgets["positive"].value_label.text() == "2"
    assert dashboard._kpi_widgets["pending"].value_label.text() == "1"
    assert dashboard.summary_label.text() == "Найдено 2 отделений • проб 4 • положительных 2"

    first_item = dashboard.list_widget.item(0)
    first_card = dashboard.list_widget.itemWidget(first_item)
    assert first_card is not None

    title_labels: list[QLabel] = list(first_card.findChildren(QLabel, "cardTitle"))
    badge_labels: list[QLabel] = list(first_card.findChildren(QLabel, "sanitaryStateBadge"))
    meta_labels: list[QLabel] = list(first_card.findChildren(QLabel, "sanitaryListMeta"))

    assert title_labels[0].text() == "ОРИТ"
    assert any("Есть положительные" in label.text() for label in badge_labels)
    assert any("Проб: 3" in label.text() for label in meta_labels)
    assert any("Последняя проба: 21.04.2026 11:15" in label.text() for label in meta_labels)


def test_sanitary_dashboard_updates_selection_context_and_opens_history(monkeypatch, qapp) -> None:
    captured: dict[str, Any] = {}

    class _DummyHistoryDialog:
        def __init__(self, sanitary_service, reference_service, **kwargs) -> None:
            captured["sanitary_service"] = sanitary_service
            captured["reference_service"] = reference_service
            captured["kwargs"] = kwargs

        def exec(self) -> int:
            captured["exec_called"] = True
            return 0

    monkeypatch.setattr("app.ui.sanitary.sanitary_dashboard.SanitaryHistoryDialog", _DummyHistoryDialog)

    dashboard = SanitaryDashboard(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            department_id=1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ]
                }
            ),
        ),
        reference_service=cast(
            Any,
            _reference_service_stub(departments=[SimpleNamespace(id=1, name="ОРИТ")]),
        ),
        session=cast(Any, SimpleNamespace(user_id=77)),
    )
    dashboard.show()
    qapp.processEvents()

    assert dashboard._department_context_value.text() == "Не выбрано"
    assert dashboard._context_badge.text() == "Выберите отделение"
    assert dashboard._quick_open_button.isEnabled() is False

    dashboard.list_widget.setCurrentRow(0)
    qapp.processEvents()

    assert dashboard._department_context_value.text() == "ОРИТ"
    assert dashboard._context_badge.text() == "Отделение выбрано"
    assert dashboard._quick_open_button.isEnabled() is True

    dashboard._handle_item_double_clicked(dashboard.list_widget.item(0))

    assert captured["exec_called"] is True
    assert captured["kwargs"]["department_id"] == 1
    assert captured["kwargs"]["department_name"] == "ОРИТ"
    assert captured["kwargs"]["actor_id"] == 77


def test_sanitary_dashboard_updates_filter_summary_and_reset(qapp) -> None:
    dashboard = SanitaryDashboard(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            department_id=1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ],
                    2: [
                        _make_sample(
                            2,
                            department_id=2,
                            lab_no="SAN-0002",
                            growth_flag=0,
                            taken_at=_dt(2026, 4, 23, 10, 0),
                        )
                    ],
                }
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
    )
    dashboard.show()
    qapp.processEvents()

    dashboard.filters_toggle.setChecked(True)
    dashboard.search_input.setText("ОРИТ")
    dashboard.filter_enabled.setChecked(True)
    dashboard.date_from.setDate(QDate(2026, 4, 20))
    dashboard.date_to.setDate(QDate(2026, 4, 21))
    dashboard.growth_filter.setCurrentIndex(1)
    qapp.processEvents()

    summary_text = dashboard._filter_summary_label.text()
    assert dashboard.filter_box.isVisible() is True
    assert dashboard.filters_toggle.text() == "Скрыть фильтры"
    assert "Отделение: ОРИТ" in summary_text
    assert "Даты:" in summary_text
    assert "20.04.2026" in summary_text
    assert "21.04.2026" in summary_text
    assert "Рост: положительные" in summary_text
    assert dashboard._kpi_widgets["departments"].value_label.text() == "1"

    dashboard._clear_filters()
    qapp.processEvents()

    assert dashboard._filter_summary_label.text() == "Без фильтров"
    assert dashboard.filter_enabled.isChecked() is False
    assert dashboard.search_input.text() == ""
    assert dashboard.growth_filter.currentIndex() == 0
    assert dashboard._date_value(dashboard.date_from) is None
    assert dashboard._date_value(dashboard.date_to) is None


def test_sanitary_dashboard_distinguishes_empty_states_and_clears_selection(qapp) -> None:
    no_data_dashboard = SanitaryDashboard(
        sanitary_service=cast(Any, _SanitaryServiceStub({})),
        reference_service=cast(Any, _reference_service_stub(departments=[])),
    )
    no_data_dashboard.show()
    qapp.processEvents()

    assert no_data_dashboard._last_empty_state == "no_data"
    no_data_card = no_data_dashboard.list_widget.itemWidget(no_data_dashboard.list_widget.item(0))
    assert no_data_card is not None
    assert any("Проб пока нет" in label.text() for label in no_data_card.findChildren(QLabel))

    filtered_dashboard = SanitaryDashboard(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            department_id=1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ]
                }
            ),
        ),
        reference_service=cast(
            Any,
            _reference_service_stub(departments=[SimpleNamespace(id=1, name="ОРИТ")]),
        ),
    )
    filtered_dashboard.show()
    qapp.processEvents()

    filtered_dashboard.list_widget.setCurrentRow(0)
    qapp.processEvents()
    assert filtered_dashboard._quick_open_button.isEnabled() is True

    filtered_dashboard.search_input.setText("zzz")
    qapp.processEvents()

    assert filtered_dashboard._last_empty_state == "filtered_out"
    assert filtered_dashboard._department_context_value.text() == "Не выбрано"
    assert filtered_dashboard._quick_open_button.isEnabled() is False
    filtered_card = filtered_dashboard.list_widget.itemWidget(filtered_dashboard.list_widget.item(0))
    assert filtered_card is not None
    assert any("Ничего не найдено" in label.text() for label in filtered_card.findChildren(QLabel))
