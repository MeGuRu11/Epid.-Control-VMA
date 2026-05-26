from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox, QTabWidget, QWidget

from app.ui.sanitary.sanitary_history import SanitarySampleDetailDialog
from app.ui.widgets.susceptibility_panel import SusceptibilityPanel


class _SanitaryServiceStub:
    def __init__(self) -> None:
        self.created: list[tuple[Any, int]] = []

    def create_sample(self, request: Any, *, actor_id: int) -> SimpleNamespace:
        self.created.append((request, actor_id))
        return SimpleNamespace(id=100, lab_no=request.lab_no or "SAN-20260526-0001")


class _ReferenceServiceStub:
    def list_microorganisms(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=7, code="STA", name="Staphylococcus aureus")]

    def search_microorganisms(self, _query: str, *, limit: int) -> list[SimpleNamespace]:
        return self.list_microorganisms()[:limit]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="AMK", name="Amikacin")]

    def list_phages(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="PH", name="Бактериофаг")]


def _dialog(qtbot: Any) -> tuple[SanitarySampleDetailDialog, _SanitaryServiceStub]:
    sanitary_service = _SanitaryServiceStub()
    dialog = SanitarySampleDetailDialog(
        sanitary_service=cast(Any, sanitary_service),
        reference_service=cast(Any, _ReferenceServiceStub()),
        department_id=4,
        actor_id=77,
    )
    qtbot.addWidget(dialog)
    return dialog, sanitary_service


def test_sanitary_dialog_tab_structure(qtbot: Any) -> None:
    dialog, _ = _dialog(qtbot)

    tabs = dialog.findChild(QTabWidget, "sampleTabs")
    footer = dialog.findChild(QDialogButtonBox, "sampleFooter")

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Проба",
        "Идентификация",
        "Чувствительность",
    ]
    assert dialog.findChild(QWidget, "sampleHeader") is not None
    assert footer is not None
    layout = dialog.layout()
    assert layout is not None
    assert layout.indexOf(footer) >= 0


def test_sanitary_dialog_save_validates_required_fields(qtbot: Any) -> None:
    dialog, sanitary_service = _dialog(qtbot)

    dialog.on_save()

    assert sanitary_service.created == []
    assert dialog.sampling_point.property("error") is True
    assert dialog.taken_at.property("error") is True
    assert "обязательные" in dialog.error_label.text().lower()


def test_sanitary_dialog_inline_validation_no_message_box(
    qtbot: Any,
    monkeypatch: Any,
) -> None:
    dialog, _ = _dialog(qtbot)

    def _fail_warning(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("QMessageBox.warning не должен вызываться для inline-валидации")

    monkeypatch.setattr(QMessageBox, "warning", _fail_warning)

    dialog.on_save()

    assert dialog.sampling_point.toolTip()
    assert dialog.taken_at.toolTip()


def test_sanitary_dialog_susceptibility_panel_extracted(qtbot: Any) -> None:
    dialog, _ = _dialog(qtbot)

    assert isinstance(dialog.susceptibility_panel, SusceptibilityPanel)
    assert dialog.susc_table is dialog.susceptibility_panel.susc_table
    assert dialog.phage_table is dialog.susceptibility_panel.phage_table


def test_sanitary_dialog_exposes_identifier_fields_and_saves_them(qtbot: Any) -> None:
    dialog, sanitary_service = _dialog(qtbot)

    dialog.lab_no.setText("SAN-MANUAL-001")
    dialog.barcode.setText("460700000002")
    assert "4" in dialog.department_display.text()
    dialog.sampling_point.setText("Раковина")
    dialog.ordered_at.setDateTime(QDateTime(QDate(2026, 5, 26), QTime(7, 45)))
    dialog.taken_at.setDateTime(QDateTime(QDate(2026, 5, 26), QTime(8, 30)))

    dialog.on_save()

    assert sanitary_service.created
    request, actor_id = sanitary_service.created[0]
    assert actor_id == 77
    assert request.lab_no == "SAN-MANUAL-001"
    assert request.barcode == "460700000002"
    assert request.ordered_at == datetime.fromisoformat("2026-05-26T07:45:00")
