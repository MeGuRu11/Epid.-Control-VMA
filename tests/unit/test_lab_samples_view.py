from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QBoxLayout, QLabel, QScrollArea, QWidget

from app.application.dto.lab_dto import LabSampleResponse
from app.ui.lab.lab_samples_view import LabSamplesView


class _DummyPatientSelector(QWidget):
    def __init__(self, _on_select, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def set_patient_id(self, _patient_id: int) -> None:
        return

    def clear(self) -> None:
        return


class _LabServiceStub:
    def __init__(self, samples: list[LabSampleResponse]) -> None:
        self._samples = samples
        self.calls: list[tuple[int, int | None]] = []

    def list_samples(self, patient_id: int, emr_case_id: int | None) -> list[LabSampleResponse]:
        self.calls.append((patient_id, emr_case_id))
        return list(self._samples)


def _reference_service_stub() -> Any:
    return SimpleNamespace(
        list_material_types=lambda: [
            SimpleNamespace(id=1, code="BLD", name="Кровь"),
            SimpleNamespace(id=2, code="URN", name="Моча"),
        ],
        list_microorganisms=lambda: [
            SimpleNamespace(id=7, code="STA", name="Staphylococcus aureus"),
        ],
    )


def _make_sample(
    sample_id: int,
    *,
    lab_no: str,
    material_type_id: int = 1,
    taken_at: datetime | None,
    growth_flag: int | None,
    qc_status: str | None = "valid",
    microorganism_id: int | None = None,
    microorganism_free: str | None = None,
    material_location: str | None = None,
    medium: str | None = None,
) -> LabSampleResponse:
    return LabSampleResponse(
        id=sample_id,
        lab_no=lab_no,
        material_type_id=material_type_id,
        material_location=material_location,
        medium=medium,
        taken_at=taken_at,
        growth_flag=growth_flag,
        qc_due_at=taken_at,
        qc_status=qc_status,
        microorganism_id=microorganism_id,
        microorganism_free=microorganism_free,
    )


def test_lab_samples_view_uses_responsive_hero_and_filter_layouts(monkeypatch, qapp) -> None:
    monkeypatch.setattr("app.ui.lab.lab_samples_view.PatientSelector", _DummyPatientSelector)
    lab = _LabServiceStub([])
    view = LabSamplesView(
        lab_service=cast(Any, lab),
        reference_service=cast(Any, _reference_service_stub()),
    )
    view.show()
    qapp.processEvents()

    view.resize(1600, 900)
    qapp.processEvents()
    assert view._hero_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert view._filter_content_layout.direction() == QBoxLayout.Direction.LeftToRight
    assert abs(view._hero_card.height() - view._utility_card.height()) <= 2
    assert isinstance(view._scroll_area, QScrollArea)
    assert view._scroll_area.widgetResizable()
    assert view._list_card.minimumHeight() >= 380
    assert view.list_widget.minimumHeight() >= 240

    view.resize(520, 900)
    qapp.processEvents()
    assert view._hero_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert view._filter_content_layout.direction() == QBoxLayout.Direction.TopToBottom


def test_lab_samples_view_updates_context_kpis_and_item_card(monkeypatch, qapp) -> None:
    monkeypatch.setattr("app.ui.lab.lab_samples_view.PatientSelector", _DummyPatientSelector)
    samples = [
        _make_sample(
            1,
            lab_no="BLD-0001",
            taken_at=datetime(2026, 4, 20, 8, 30, tzinfo=UTC),
            growth_flag=1,
            qc_status="valid",
            microorganism_id=7,
            material_location="Рана",
            medium="Агар",
        ),
        _make_sample(
            2,
            lab_no="URN-0002",
            material_type_id=2,
            taken_at=datetime(2026, 4, 21, 9, 30, tzinfo=UTC),
            growth_flag=0,
            qc_status="conditional",
            microorganism_free="Klebsiella pneumoniae",
        ),
        _make_sample(
            3,
            lab_no="BLD-0003",
            taken_at=datetime(2026, 4, 21, 10, 15, tzinfo=UTC),
            growth_flag=None,
            qc_status=None,
        ),
    ]
    lab = _LabServiceStub(samples)
    view = LabSamplesView(
        lab_service=cast(Any, lab),
        reference_service=cast(Any, _reference_service_stub()),
    )
    view.set_context(10, 55)
    view.show()
    qapp.processEvents()

    assert view._patient_context_value.text() == "Пациент #10"
    assert view._case_context_value.text() == "ЭМЗ #55"
    assert view._context_badge.text() == "Контекст выбран"
    assert view._kpi_widgets["total"].value_label.text() == "3"
    assert view._kpi_widgets["positive"].value_label.text() == "1"
    assert view._kpi_widgets["negative"].value_label.text() == "1"
    assert view._kpi_widgets["pending"].value_label.text() == "1"
    assert view.count_label.text().startswith("Всего 3")

    first_item = view.list_widget.item(0)
    first_card = view.list_widget.itemWidget(first_item)
    assert first_card is not None

    title_labels = first_card.findChildren(QLabel, "cardTitle")
    badge_labels = first_card.findChildren(QLabel, "labStateBadge")
    meta_labels = first_card.findChildren(QLabel, "labListMeta")

    assert title_labels[0].text() == "BLD-0003"
    assert any("QC" in label.text() for label in badge_labels)
    assert any("Рост" in label.text() or "Без результата" in label.text() for label in badge_labels)
    assert any("Материал:" in label.text() for label in meta_labels)


def test_lab_samples_view_clear_context_returns_to_no_context_state(monkeypatch, qapp) -> None:
    monkeypatch.setattr("app.ui.lab.lab_samples_view.PatientSelector", _DummyPatientSelector)
    lab = _LabServiceStub(
        [
            _make_sample(
                1,
                lab_no="BLD-0001",
                taken_at=datetime(2026, 4, 20, 8, 30, tzinfo=UTC),
                growth_flag=1,
            )
        ]
    )
    view = LabSamplesView(
        lab_service=cast(Any, lab),
        reference_service=cast(Any, _reference_service_stub()),
    )
    view.set_context(10, 55)
    view.clear_context()
    view.show()
    qapp.processEvents()

    assert view._last_empty_state == "no_context"
    assert view._patient_context_value.text() == "Не выбран"
    assert view._case_context_value.text() == "Не выбрана"
    assert view._kpi_widgets["total"].value_label.text() == "0"
    assert view._kpi_widgets["total"].detail_label.text() == "Выберите пациента"

    empty_item = view.list_widget.item(0)
    empty_card = view.list_widget.itemWidget(empty_item)
    assert empty_card is not None
    assert empty_item.sizeHint().height() >= 112
    assert any("Выберите пациента" in label.text() for label in empty_card.findChildren(QLabel))


def test_lab_samples_view_distinguishes_no_data_and_filtered_empty_states(monkeypatch, qapp) -> None:
    monkeypatch.setattr("app.ui.lab.lab_samples_view.PatientSelector", _DummyPatientSelector)

    empty_view = LabSamplesView(
        lab_service=cast(Any, _LabServiceStub([])),
        reference_service=cast(Any, _reference_service_stub()),
    )
    empty_view.set_context(10, None)
    empty_view.show()
    qapp.processEvents()

    assert empty_view._last_empty_state == "no_data"
    assert "0 проб" in empty_view.count_label.text()

    filtered_view = LabSamplesView(
        lab_service=cast(
            Any,
            _LabServiceStub(
                [
                    _make_sample(
                        1,
                        lab_no="BLD-0001",
                        taken_at=datetime(2026, 4, 20, 8, 30, tzinfo=UTC),
                        growth_flag=1,
                    )
                ]
            ),
        ),
        reference_service=cast(Any, _reference_service_stub()),
    )
    filtered_view.set_context(10, None)
    filtered_view.show()
    qapp.processEvents()
    filtered_view.search_input.setText("zzz")
    qapp.processEvents()

    assert filtered_view._last_empty_state == "filtered_out"
    assert filtered_view._filter_summary_label.text().startswith("№: zzz")
    assert filtered_view.count_label.text() == "Найдено 0 из 1"
