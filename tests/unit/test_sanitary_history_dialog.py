from __future__ import annotations

# mypy: disable-error-code=var-annotated
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QBoxLayout, QLabel

from app.application.dto.sanitary_dto import SanitarySampleResponse
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog


class _SanitaryServiceStub:
    def __init__(self, samples_by_department: dict[int, list[SanitarySampleResponse]]) -> None:
        self._samples_by_department = samples_by_department
        self.calls: list[int] = []

    def list_samples_by_department(self, department_id: int) -> list[SanitarySampleResponse]:
        self.calls.append(department_id)
        return list(self._samples_by_department.get(department_id, []))


def _reference_service_stub() -> Any:
    return SimpleNamespace(
        list_microorganisms=lambda: [
            SimpleNamespace(id=7, code="STA", name="Staphylococcus aureus"),
            SimpleNamespace(id=9, code="KLB", name="Klebsiella pneumoniae"),
        ]
    )


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _make_sample(
    sample_id: int,
    *,
    department_id: int = 1,
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


def test_sanitary_history_dialog_uses_responsive_filter_and_header_layouts(qapp) -> None:
    dialog = SanitaryHistoryDialog(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ]
                }
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    dialog.show()
    qapp.processEvents()

    action_buttons = [button for button in dialog._actions_panel.findChildren(type(dialog.prev_btn)) if button.text()]
    assert {button.text() for button in action_buttons} == {"Новая проба", "Обновить"}
    assert dialog.hint_label.text() == "Двойное нажатие по записи открывает карточку санитарной пробы."

    dialog.resize(1400, 800)
    qapp.processEvents()
    assert dialog._filter_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert dialog._list_header_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert dialog.list_widget.minimumHeight() >= 260
    assert hasattr(dialog, "_actions_panel")

    dialog.resize(520, 800)
    qapp.processEvents()
    assert dialog._filter_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert dialog._list_header_layout.direction() == QBoxLayout.Direction.TopToBottom


def test_sanitary_history_dialog_updates_summary_header_and_cards(qapp) -> None:
    dialog = SanitaryHistoryDialog(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                            sampling_point="Раковина",
                            room="Палата 1",
                            microorganism_id=7,
                        ),
                        _make_sample(
                            2,
                            lab_no="SAN-0002",
                            growth_flag=0,
                            taken_at=_dt(2026, 4, 21, 9, 45),
                            medium="Агар",
                        ),
                        _make_sample(
                            3,
                            lab_no="SAN-0003",
                            growth_flag=None,
                            taken_at=_dt(2026, 4, 21, 11, 15),
                            sampling_point="Стол",
                            room="Процедурная",
                        ),
                    ]
                }
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    dialog.show()
    qapp.processEvents()

    assert dialog._summary_total_value.text() == "3"
    assert dialog._summary_positive_value.text() == "1"
    assert dialog._summary_last_value.text() == "21.04.2026 11:15"
    assert dialog._summary_shown_value.text() == "3"
    assert dialog.list_summary_label.text() == "Найдено 3 проб • показано 3"

    first_item = dialog.list_widget.item(0)
    first_card = dialog.list_widget.itemWidget(first_item)
    assert first_card is not None

    title_labels: list[QLabel] = list(first_card.findChildren(QLabel, "cardTitle"))
    badge_labels: list[QLabel] = list(first_card.findChildren(QLabel, "sanitaryHistoryBadge"))
    meta_labels: list[QLabel] = list(first_card.findChildren(QLabel, "sanitaryHistoryMeta"))

    assert title_labels[0].text() == "SAN-0003"
    assert any("Без результата" in label.text() for label in badge_labels)
    assert any("Взято: 21.04.2026 11:15" in label.text() for label in meta_labels)
    assert any("Точка: Стол" in label.text() for label in meta_labels)


def test_sanitary_history_dialog_updates_filter_summary_and_resets_page(qapp) -> None:
    samples = [
        _make_sample(
            index,
            lab_no=f"SAN-{index:04d}",
            growth_flag=1 if index % 2 else 0,
            taken_at=_dt(2026, 4, 20 + (index % 3), 8, 30),
        )
        for index in range(1, 56)
    ]
    dialog = SanitaryHistoryDialog(
        sanitary_service=cast(Any, _SanitaryServiceStub({1: samples})),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    dialog.show()
    qapp.processEvents()

    dialog.page_size_combo.setCurrentText("20")
    dialog._on_page_size_changed()
    qapp.processEvents()
    assert dialog.page_label.text() == "Стр. 1 / 3"

    dialog._next_page()
    qapp.processEvents()
    assert dialog.page_index == 2
    assert dialog.page_label.text() == "Стр. 2 / 3"

    dialog.search_input.setText("san-0001")
    dialog.growth_filter.setCurrentIndex(1)
    dialog.date_from.setDate(QDate(2026, 4, 20))
    dialog.date_to.setDate(QDate(2026, 4, 22))
    qapp.processEvents()

    assert dialog.page_index == 1
    assert "Номер: san-0001" in dialog.filter_summary_label.text()
    assert "Рост: Положительные" in dialog.filter_summary_label.text()
    assert "20.04.2026" in dialog.filter_summary_label.text()
    assert "22.04.2026" in dialog.filter_summary_label.text()

    dialog._clear_filters()
    qapp.processEvents()

    assert dialog.page_index == 1
    assert dialog.filter_summary_label.text() == "Без фильтров"
    assert dialog.search_input.text() == ""
    assert dialog.growth_filter.currentIndex() == 0
    assert dialog._date_value(dialog.date_from) is None
    assert dialog._date_value(dialog.date_to) is None


def test_sanitary_history_dialog_distinguishes_no_data_and_filtered_empty_states(qapp) -> None:
    no_data_dialog = SanitaryHistoryDialog(
        sanitary_service=cast(Any, _SanitaryServiceStub({1: []})),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    no_data_dialog.show()
    qapp.processEvents()

    assert no_data_dialog._last_empty_state == "no_data"
    no_data_card = no_data_dialog.list_widget.itemWidget(no_data_dialog.list_widget.item(0))
    assert no_data_card is not None
    assert any("Проб пока нет" in label.text() for label in no_data_card.findChildren(QLabel))

    filtered_dialog = SanitaryHistoryDialog(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ]
                }
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    filtered_dialog.show()
    qapp.processEvents()

    filtered_dialog.search_input.setText("zzz")
    qapp.processEvents()

    assert filtered_dialog._last_empty_state == "filtered_out"
    filtered_card = filtered_dialog.list_widget.itemWidget(filtered_dialog.list_widget.item(0))
    assert filtered_card is not None
    assert any("По фильтрам ничего не найдено" in label.text() for label in filtered_card.findChildren(QLabel))


def test_sanitary_history_dialog_opens_detail_on_double_click(monkeypatch, qapp) -> None:
    captured: dict[str, Any] = {}

    class _DummyDetailDialog:
        def __init__(self, sanitary_service, reference_service, **kwargs) -> None:
            captured["sanitary_service"] = sanitary_service
            captured["reference_service"] = reference_service
            captured["kwargs"] = kwargs

        def refresh_references(self) -> None:
            return

        def exec(self) -> int:
            captured["exec_called"] = True
            return 0

    monkeypatch.setattr("app.ui.sanitary.sanitary_history.SanitarySampleDetailDialog", _DummyDetailDialog)

    dialog = SanitaryHistoryDialog(
        sanitary_service=cast(
            Any,
            _SanitaryServiceStub(
                {
                    1: [
                        _make_sample(
                            1,
                            lab_no="SAN-0001",
                            growth_flag=1,
                            taken_at=_dt(2026, 4, 20, 8, 30),
                        )
                    ]
                }
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
        department_id=1,
        department_name="ОРИТ",
        actor_id=77,
    )
    dialog.show()
    qapp.processEvents()

    dialog._handle_item_double_clicked(dialog.list_widget.item(0))

    assert captured["exec_called"] is True
    assert captured["kwargs"]["department_id"] == 1
    assert captured["kwargs"]["sample_id"] == 1
    assert captured["kwargs"]["actor_id"] == 77
