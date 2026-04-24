from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtWidgets import QDialog, QLabel, QMessageBox

from app.application.dto.auth_dto import SessionContext
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.setup_service import SetupService
from app.application.services.user_admin_service import UserAdminService
from app.ui.admin.user_admin_view import UserAdminView
from app.ui.first_run_dialog import FirstRunDialog
from app.ui.form100_v2.form100_wizard import _build_structured_data, _build_wizard_payload
from app.ui.lab.lab_sample_detail import LabSampleDetailDialog
from app.ui.patient import patient_emk_view as patient_emk_view_module
from app.ui.patient.patient_emk_view import PatientEmkView


class _SetupServiceStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def create_initial_user(self, *, login: str, password: str) -> None:
        self.calls.append((login, password))


class _UserAdminServiceStub:
    def __init__(self) -> None:
        self.users: list[SimpleNamespace] = []
        self.created: list[tuple[str, str, str, int]] = []

    def list_users(self, query: str | None = None) -> list[SimpleNamespace]:
        if query:
            return [user for user in self.users if query in user.login]
        return self.users

    def create_user(self, request: Any, *, actor_id: int) -> int:
        user_id = len(self.users) + 1
        self.created.append((request.login, request.password, request.role, actor_id))
        self.users.append(SimpleNamespace(id=user_id, login=request.login, role=request.role, is_active=True))
        return user_id


class _DashboardServiceStub:
    def list_recent_audit(self, limit: int = 20) -> list[dict[str, object]]:
        del limit
        return []


class _BackupServiceStub:
    def get_last_backup(self) -> object | None:
        return None


def _admin_session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def test_first_run_dialog_validates_empty_login(qapp) -> None:
    del qapp
    setup = _SetupServiceStub()
    dialog = FirstRunDialog(setup_service=cast(SetupService, setup))
    try:
        dialog.password_edit.setText("password123")
        dialog.password_confirm.setText("password123")

        dialog._on_create()

        assert setup.calls == []
        assert "логин" in dialog.error_label.text().lower()
    finally:
        dialog.close()


def test_first_run_dialog_accepts_valid_admin(qapp) -> None:
    del qapp
    setup = _SetupServiceStub()
    dialog = FirstRunDialog(setup_service=cast(SetupService, setup))
    try:
        dialog.login_edit.setText("admin")
        dialog.password_edit.setText("password123")
        dialog.password_confirm.setText("password123")

        dialog._on_create()

        assert setup.calls == [("admin", "password123")]
        assert dialog.result() == int(QDialog.DialogCode.Accepted)
    finally:
        dialog.close()


def test_user_admin_view_create_user_refreshes_table(qapp) -> None:
    del qapp
    user_service = _UserAdminServiceStub()
    view = UserAdminView(
        user_admin_service=cast(UserAdminService, user_service),
        dashboard_service=cast(DashboardService, _DashboardServiceStub()),
        backup_service=cast(BackupService, _BackupServiceStub()),
        session=_admin_session(),
    )
    try:
        view.create_login.setText("operator")
        view.create_password.setText("password123")
        view.create_role.setCurrentIndex(0)

        view._create_user()

        assert user_service.created == [("operator", "password123", "operator", 1)]
        assert view.user_table.rowCount() == 1
        assert view.create_login.text() == ""
        assert view.create_password.text() == ""
    finally:
        view.close()


def test_patient_delete_cancel_does_not_call_service(monkeypatch: pytest.MonkeyPatch) -> None:
    delete_calls: list[tuple[int, int]] = []
    statuses: list[tuple[str, str]] = []
    data_changed = {"count": 0}

    monkeypatch.setattr(
        patient_emk_view_module,
        "exec_message_box",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    view = SimpleNamespace(
        _current_patient=SimpleNamespace(id=7, full_name="Иванов Иван"),
        _session=_admin_session(),
        patient_service=SimpleNamespace(
            delete_patient=lambda patient_id, *, actor_id: delete_calls.append((patient_id, actor_id))
        ),
        _reset_search=lambda: None,
        _set_status=lambda message, level="info": statuses.append((message, level)),
        on_data_changed=lambda: data_changed.__setitem__("count", data_changed["count"] + 1),
    )

    PatientEmkView._delete_patient(cast(PatientEmkView, view))

    assert delete_calls == []
    assert statuses == []
    assert data_changed["count"] == 0


def test_lab_sample_detail_reports_missing_actor(qapp) -> None:
    del qapp
    label = QLabel()
    dialog = SimpleNamespace(error_label=label, actor_id=None)

    LabSampleDetailDialog.on_save(cast(LabSampleDetailDialog, dialog))

    assert "пользователя сессии" in label.text().lower()


def test_form100_wizard_minimal_mapping_smoke() -> None:
    data = _build_structured_data(
        {
            "main_full_name": "Иванов Иван",
            "main_unit": "1 рота",
            "bodymap_tissue_types_json": json.dumps([], ensure_ascii=False),
        },
        [],
    )

    payload, markers = _build_wizard_payload(data)

    assert payload["main_full_name"] == "Иванов Иван"
    assert payload["main_unit"] == "1 рота"
    assert markers == []
