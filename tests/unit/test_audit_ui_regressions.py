from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout, QDialog, QLabel, QMessageBox, QTabWidget, QWidget

from app.application.dto.auth_dto import SessionContext
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.setup_service import SetupService
from app.application.services.user_admin_service import UserAdminService
from app.ui.admin import user_admin_view as user_admin_view_module
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
        self.queries: list[str | None] = []
        self.reset_calls: list[tuple[int, str, bool, int]] = []
        self.active_calls: list[tuple[int, bool, int]] = []

    def list_users(self, query: str | None = None) -> list[SimpleNamespace]:
        self.queries.append(query)
        if query:
            return [user for user in self.users if query in user.login]
        return self.users

    def create_user(self, request: Any, *, actor_id: int) -> int:
        user_id = len(self.users) + 1
        self.created.append((request.login, request.password, request.role, actor_id))
        self.users.append(SimpleNamespace(id=user_id, login=request.login, role=request.role, is_active=True))
        return user_id

    def reset_password(self, request: Any, *, actor_id: int) -> None:
        self.reset_calls.append((request.user_id, request.new_password, request.deactivate, actor_id))

    def set_active(self, user_id: int, is_active: bool, *, actor_id: int) -> None:
        self.active_calls.append((user_id, is_active, actor_id))
        for user in self.users:
            if user.id == user_id:
                user.is_active = is_active


class _DashboardServiceStub:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []

    def list_recent_audit(self, limit: int = 20) -> list[dict[str, object]]:
        del limit
        return self.rows


class _BackupServiceStub:
    def get_last_backup(self) -> object | None:
        return None


def _admin_session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def _operator_session() -> SessionContext:
    return SessionContext(user_id=2, login="operator", role="operator")


def _make_admin_view(
    *,
    user_service: _UserAdminServiceStub | None = None,
    dashboard_service: _DashboardServiceStub | None = None,
    backup_service: _BackupServiceStub | None = None,
    session: SessionContext | None = None,
) -> UserAdminView:
    return UserAdminView(
        user_admin_service=cast(UserAdminService, user_service or _UserAdminServiceStub()),
        dashboard_service=cast(DashboardService, dashboard_service or _DashboardServiceStub()),
        backup_service=cast(BackupService, backup_service or _BackupServiceStub()),
        session=session or _admin_session(),
    )


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
    view = _make_admin_view(user_service=user_service)
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


def test_user_admin_view_creates_expected_tabs(qapp) -> None:
    del qapp
    view = _make_admin_view()
    try:
        tabs = view.findChild(QTabWidget, "adminTabs")

        assert tabs is not None
        assert [tabs.tabText(index) for index in range(tabs.count())] == [
            "Пользователи",
            "Аудит",
            "Резервные копии",
        ]
    finally:
        view.close()


def test_user_admin_view_uses_two_columns_on_initial_wide_show(qapp) -> None:
    view = _make_admin_view()
    try:
        view.resize(1900, 900)
        view.show()
        qapp.processEvents()
        qapp.processEvents()

        assert view._content_layout.direction() == QBoxLayout.Direction.LeftToRight
    finally:
        view.close()


def test_user_admin_view_recalculates_layout_after_resize(qapp) -> None:
    view = _make_admin_view()
    try:
        view.resize(900, 900)
        view.show()
        qapp.processEvents()
        qapp.processEvents()

        assert view._content_layout.direction() == QBoxLayout.Direction.TopToBottom

        view.resize(1900, 900)
        qapp.processEvents()
        qapp.processEvents()

        assert view._content_layout.direction() == QBoxLayout.Direction.LeftToRight
    finally:
        view.close()


def test_user_admin_view_hero_text_block_has_transparent_qss_hook(qapp) -> None:
    del qapp
    view = _make_admin_view()
    try:
        assert view.findChild(QWidget, "adminHeroTextBlock") is not None
    finally:
        view.close()


def test_user_admin_view_search_passes_query(qapp) -> None:
    del qapp
    user_service = _UserAdminServiceStub()
    user_service.users = [
        SimpleNamespace(id=1, login="operator", role="operator", is_active=True),
        SimpleNamespace(id=2, login="admin", role="admin", is_active=True),
    ]
    view = _make_admin_view(user_service=user_service)
    try:
        view.search_input.setText("oper")

        assert user_service.queries[-1] == "oper"
        assert view.user_table.rowCount() == 1
    finally:
        view.close()


def test_user_admin_view_selection_updates_detail_and_actions(qapp) -> None:
    del qapp
    user_service = _UserAdminServiceStub()
    user_service.users = [SimpleNamespace(id=5, login="operator", role="operator", is_active=True)]
    view = _make_admin_view(user_service=user_service)
    try:
        view.user_table.selectRow(0)
        item = view.user_table.item(0, 0)
        assert item is not None
        payload = item.data(Qt.ItemDataRole.UserRole)

        assert payload == {"id": 5, "login": "operator", "role": "operator", "is_active": True}
        assert view.selected_user_login.text() == "operator"
        assert view.selected_user_role.text() == "Оператор"
        assert view.selected_user_status.text() == "Активен"
        assert view.reset_btn.isEnabled()
        assert view.deactivate_btn.isEnabled()
        assert not view.activate_btn.isEnabled()
    finally:
        view.close()


def test_user_admin_view_no_selection_does_not_call_user_actions(qapp) -> None:
    del qapp
    user_service = _UserAdminServiceStub()
    user_service.users = [SimpleNamespace(id=5, login="operator", role="operator", is_active=True)]
    view = _make_admin_view(user_service=user_service)
    try:
        view.user_table.clearSelection()
        view._reset_password()
        view._set_active(False)

        assert user_service.reset_calls == []
        assert user_service.active_calls == []
        assert "пользователь" in view.status.text().lower()
    finally:
        view.close()


def test_user_admin_view_deactivate_cancel_does_not_call_service(
    qapp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del qapp
    user_service = _UserAdminServiceStub()
    user_service.users = [SimpleNamespace(id=5, login="operator", role="operator", is_active=True)]
    view = _make_admin_view(user_service=user_service)
    try:
        monkeypatch.setattr(
            user_admin_view_module,
            "exec_message_box",
            lambda *args, **kwargs: QMessageBox.StandardButton.No,
        )
        view.user_table.selectRow(0)

        view._set_active(False)

        assert user_service.active_calls == []
        assert "отмен" in view.status.text().lower()
    finally:
        view.close()


def test_user_admin_view_audit_empty_state_visible(qapp) -> None:
    del qapp
    view = _make_admin_view(dashboard_service=_DashboardServiceStub(rows=[]))
    try:
        assert view.audit_table.rowCount() == 0
        assert view.audit_empty_label.text() == "Событий аудита пока нет"
        assert not view.audit_empty_label.isHidden()
    finally:
        view.close()


def test_user_admin_view_backup_buttons_follow_role_and_busy(qapp) -> None:
    del qapp
    operator_view = _make_admin_view(session=_operator_session())
    admin_view = _make_admin_view()
    try:
        assert not operator_view.backup_create_btn.isEnabled()
        assert not operator_view.backup_restore_btn.isEnabled()

        admin_view._set_backup_busy(True)
        assert not admin_view.backup_create_btn.isEnabled()
        assert not admin_view.backup_restore_btn.isEnabled()

        admin_view._set_backup_busy(False)
        assert admin_view.backup_create_btn.isEnabled()
        assert admin_view.backup_restore_btn.isEnabled()
    finally:
        operator_view.close()
        admin_view.close()


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


def test_patient_emk_edit_passes_selected_case() -> None:
    calls: list[tuple[int, int | None]] = []
    view = SimpleNamespace(
        _current_patient=SimpleNamespace(id=7),
        _current_case_id=9,
        on_edit_patient=lambda patient_id, emr_case_id: calls.append((patient_id, emr_case_id)),
        _set_status=lambda message, level="info": None,
    )

    PatientEmkView._open_edit_patient(cast(PatientEmkView, view))

    assert calls == [(7, 9)]


def test_patient_emk_edit_falls_back_to_latest_case() -> None:
    calls: list[tuple[int, int | None]] = []
    view = SimpleNamespace(
        _current_patient=SimpleNamespace(id=7),
        _current_case_id=None,
        _choose_latest_case_id=lambda: 12,
        on_edit_patient=lambda patient_id, emr_case_id: calls.append((patient_id, emr_case_id)),
        _set_status=lambda message, level="info": None,
    )

    PatientEmkView._open_edit_patient(cast(PatientEmkView, view))

    assert calls == [(7, 12)]


def test_patient_emk_edit_passes_none_without_cases() -> None:
    calls: list[tuple[int, int | None]] = []
    statuses: list[tuple[str, str]] = []
    view = SimpleNamespace(
        _current_patient=SimpleNamespace(id=7),
        _current_case_id=None,
        _choose_latest_case_id=lambda: None,
        on_edit_patient=lambda patient_id, emr_case_id: calls.append((patient_id, emr_case_id)),
        _set_status=lambda message, level="info": statuses.append((message, level)),
    )

    PatientEmkView._open_edit_patient(cast(PatientEmkView, view))

    assert calls == []
    assert statuses == [("Нет госпитализаций для редактирования ЭМЗ.", "warning")]


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
