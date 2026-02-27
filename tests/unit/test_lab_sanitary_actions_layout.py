from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QBoxLayout, QWidget

from app.ui.lab.lab_samples_view import LabSamplesView
from app.ui.sanitary.sanitary_dashboard import SanitaryDashboard
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog


class _DummyPatientSelector(QWidget):
    def __init__(self, _on_select, parent: QWidget | None = None) -> None:  # noqa: D401
        super().__init__(parent)

    def set_patient_id(self, _patient_id: int) -> None:
        return

    def clear(self) -> None:
        return


def test_lab_samples_view_uses_responsive_actions(monkeypatch, qapp) -> None:
    monkeypatch.setattr("app.ui.lab.lab_samples_view.PatientSelector", _DummyPatientSelector)
    ref = SimpleNamespace(
        list_material_types=list,
        list_microorganisms=list,
    )
    lab = SimpleNamespace(list_samples=lambda _pid, _case: [])
    view = LabSamplesView(lab_service=lab, reference_service=ref)  # type: ignore[arg-type]
    view.show()
    qapp.processEvents()

    assert hasattr(view, "_quick_actions_layout")
    view.resize(440, 700)
    qapp.processEvents()
    assert view._quick_actions_layout.direction() == QBoxLayout.Direction.TopToBottom
    view.resize(1800, 900)
    qapp.processEvents()
    assert view._quick_actions_layout.direction() == QBoxLayout.Direction.LeftToRight


def test_sanitary_views_use_responsive_actions(qapp) -> None:
    ref = SimpleNamespace(
        list_departments=list,
        list_microorganisms=list,
    )
    sanitary = SimpleNamespace(
        list_samples_by_department=lambda _dep_id: [],
    )

    dashboard = SanitaryDashboard(sanitary_service=sanitary, reference_service=ref)  # type: ignore[arg-type]
    dashboard.show()
    qapp.processEvents()
    assert hasattr(dashboard, "_quick_actions_layout")
    assert hasattr(dashboard, "_filter_layout")
    dashboard.resize(440, 700)
    qapp.processEvents()
    assert dashboard._filter_layout.direction() == QBoxLayout.Direction.TopToBottom
    dashboard.resize(1700, 900)
    qapp.processEvents()
    assert dashboard._filter_layout.direction() == QBoxLayout.Direction.LeftToRight

    history = SanitaryHistoryDialog(
        sanitary_service=cast(Any, sanitary),
        reference_service=cast(Any, ref),
        department_id=1,
        department_name="Тест",
    )
    history.show()
    qapp.processEvents()
    panel = history._actions_panel
    assert isinstance(panel.is_compact(), bool)
    panel.set_compact(True)
    qapp.processEvents()
    assert panel.is_compact() is True
    panel.set_compact(False)
    qapp.processEvents()
    assert panel.is_compact() is False
