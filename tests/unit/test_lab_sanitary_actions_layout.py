from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QWidget

from app.ui.lab.lab_samples_view import LabSamplesView
from app.ui.sanitary.sanitary_dashboard import SanitaryDashboard
from app.ui.sanitary.sanitary_history import SanitaryHistoryDialog
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel


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
    view = LabSamplesView(lab_service=lab, reference_service=ref)
    view.show()
    qapp.processEvents()

    assert isinstance(view._quick_actions_panel, ResponsiveActionsPanel)
    view.resize(900, 700)
    qapp.processEvents()
    assert view._quick_actions_panel._compact is True
    view.resize(1800, 900)
    qapp.processEvents()
    assert view._quick_actions_panel._compact is False


def test_sanitary_views_use_responsive_actions(qapp) -> None:
    ref = SimpleNamespace(
        list_departments=list,
        list_microorganisms=list,
    )
    sanitary = SimpleNamespace(
        list_samples_by_department=lambda _dep_id: [],
    )

    dashboard = SanitaryDashboard(sanitary_service=sanitary, reference_service=ref)
    dashboard.show()
    qapp.processEvents()
    assert isinstance(dashboard._quick_actions_panel, ResponsiveActionsPanel)

    history = SanitaryHistoryDialog(
        sanitary_service=sanitary,
        reference_service=ref,
        department_id=1,
        department_name="Тест",
    )
    history.show()
    qapp.processEvents()
    assert isinstance(history._actions_panel, ResponsiveActionsPanel)
    history.resize(980, 700)
    qapp.processEvents()
    assert history._actions_panel._compact is True
    history.resize(1600, 900)
    qapp.processEvents()
    assert history._actions_panel._compact is False
