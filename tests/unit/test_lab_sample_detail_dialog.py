from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QDialogButtonBox, QMessageBox, QTabWidget, QWidget

from app.ui.lab.lab_sample_detail import LabSampleDetailDialog
from app.ui.widgets.susceptibility_panel import SusceptibilityPanel


class _LabServiceStub:
    def __init__(self) -> None:
        self.created: list[tuple[Any, int]] = []

    def create_sample(self, request: Any, *, actor_id: int) -> SimpleNamespace:
        self.created.append((request, actor_id))
        return SimpleNamespace(id=42, qc_due_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC))


class _ReferenceServiceStub:
    def list_material_types(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="BLD", name="Кровь")]

    def list_microorganisms(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=7, code="STA", name="Staphylococcus aureus")]

    def search_microorganisms(self, _query: str, *, limit: int) -> list[SimpleNamespace]:
        return self.list_microorganisms()[:limit]

    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="AMK", name="Amikacin")]

    def list_phages(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=1, code="PH", name="Бактериофаг")]


def _dialog(qtbot: Any) -> tuple[LabSampleDetailDialog, _LabServiceStub]:
    lab_service = _LabServiceStub()
    dialog = LabSampleDetailDialog(
        lab_service=cast(Any, lab_service),
        reference_service=cast(Any, _ReferenceServiceStub()),
        patient_id=11,
        emr_case_id=None,
        actor_id=7,
    )
    qtbot.addWidget(dialog)
    return dialog, lab_service


def test_lab_dialog_tab_structure(qtbot: Any) -> None:
    dialog, _ = _dialog(qtbot)

    tabs = dialog.findChild(QTabWidget, "sampleTabs")
    footer = dialog.findChild(QDialogButtonBox, "sampleFooter")

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Проба",
        "Идентификация",
        "Чувствительность",
        "Контроль качества",
    ]
    assert dialog.findChild(QWidget, "sampleHeader") is not None
    assert footer is not None
    assert dialog.layout() is not None
    assert dialog.layout().indexOf(footer) >= 0


def test_lab_dialog_save_validates_required_fields(qtbot: Any) -> None:
    dialog, lab_service = _dialog(qtbot)

    dialog.on_save()

    assert lab_service.created == []
    assert dialog.material_type.property("error") is True
    assert dialog.taken_at.property("error") is True
    assert "обязательные" in dialog.error_label.text().lower()


def test_lab_dialog_inline_validation_no_message_box(
    qtbot: Any,
    monkeypatch: Any,
) -> None:
    dialog, _ = _dialog(qtbot)

    def _fail_warning(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("QMessageBox.warning не должен вызываться для inline-валидации")

    monkeypatch.setattr(QMessageBox, "warning", _fail_warning)

    dialog.on_save()

    assert dialog.material_type.toolTip()
    assert dialog.taken_at.toolTip()


def test_lab_dialog_susceptibility_panel_extracted(qtbot: Any) -> None:
    dialog, _ = _dialog(qtbot)

    assert isinstance(dialog.susceptibility_panel, SusceptibilityPanel)
    assert dialog.susc_table is dialog.susceptibility_panel.susc_table
    assert dialog.phage_table is dialog.susceptibility_panel.phage_table
