from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from PySide6.QtWidgets import QDialog, QWidget

from app.application.dto.auth_dto import SessionContext
from app.container import Container
from app.ui.patient import patient_full_edit_dialog as dialog_module
from app.ui.patient.patient_full_edit_dialog import PatientFullEditDialog


class _PatientServiceStub:
    pass


class _FakeEmzForm(QWidget):
    instances: list[_FakeEmzForm] = []

    def __init__(self, **kwargs: object) -> None:
        parent = kwargs.get("parent")
        super().__init__(cast(QWidget | None, parent))
        self.kwargs = kwargs
        self.edit_mode: bool | None = None
        self.load_calls: list[tuple[int | None, int | None, bool]] = []
        _FakeEmzForm.instances.append(self)

    def set_edit_mode(self, enabled: bool) -> None:
        self.edit_mode = enabled

    def load_case(self, patient_id: int | None, emr_case_id: int | None, *, emit_context: bool = True) -> None:
        self.load_calls.append((patient_id, emr_case_id, emit_context))


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def _container(patient_service: _PatientServiceStub | None = None) -> Container:
    service = patient_service or _PatientServiceStub()
    return cast(
        Container,
        SimpleNamespace(
            patient_service=service,
        ),
    )


def test_full_edit_dialog_embeds_only_emz_editor(qapp, monkeypatch) -> None:
    del qapp
    _FakeEmzForm.instances.clear()
    monkeypatch.setattr(dialog_module, "EmzForm", _FakeEmzForm)

    dialog = PatientFullEditDialog(
        container=_container(),
        session=_session(),
        patient_id=7,
        emr_case_id=9,
    )
    try:
        assert not hasattr(dialog, "tabs")
        assert dialog.form is _FakeEmzForm.instances[0]
        assert _FakeEmzForm.instances[0].edit_mode is True
        assert _FakeEmzForm.instances[0].load_calls == [(7, 9, False)]
    finally:
        dialog.close()


def test_full_edit_dialog_accepts_after_emz_save(qapp, monkeypatch) -> None:
    del qapp
    _FakeEmzForm.instances.clear()
    monkeypatch.setattr(dialog_module, "EmzForm", _FakeEmzForm)

    dialog = PatientFullEditDialog(
        container=_container(),
        session=_session(),
        patient_id=7,
        emr_case_id=9,
    )
    try:
        dialog._on_saved()
        dialog.reject()

        assert dialog.result() == int(QDialog.DialogCode.Accepted)
    finally:
        dialog.close()
