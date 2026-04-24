from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from PySide6.QtWidgets import QMessageBox

from app.application.dto.auth_dto import SessionContext
from app.application.services.reference_service import ReferenceService
from app.ui.references import reference_view as reference_view_module
from app.ui.references.reference_view import ReferenceView


class _ReferenceServiceStub:
    def __init__(self) -> None:
        self.delete_calls: list[int] = []
        self.list_calls = 0

    def list_departments(self) -> list[object]:
        self.list_calls += 1
        return [SimpleNamespace(id=10, name="Терапия")]

    def delete_department(self, item_id: int, *, actor_id: int) -> None:
        self.delete_calls.append(item_id)
        assert actor_id == 1


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def _selected_department_view(service: _ReferenceServiceStub) -> ReferenceView:
    view = ReferenceView(reference_service=cast(ReferenceService, service), session=_session())
    item = view.list_box.item(0)
    assert item is not None
    view._on_item_selected(item)
    return view


def test_reference_delete_cancel_does_not_call_service(monkeypatch: pytest.MonkeyPatch, qapp) -> None:
    del qapp
    service = _ReferenceServiceStub()
    view = _selected_department_view(service)
    initial_list_calls = service.list_calls

    monkeypatch.setattr(
        reference_view_module,
        "exec_message_box",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )

    view._delete_item()

    assert service.delete_calls == []
    assert service.list_calls == initial_list_calls
    assert view._current_id == 10


def test_reference_delete_confirm_calls_service_and_refreshes(monkeypatch: pytest.MonkeyPatch, qapp) -> None:
    del qapp
    service = _ReferenceServiceStub()
    view = _selected_department_view(service)
    initial_list_calls = service.list_calls

    monkeypatch.setattr(
        reference_view_module,
        "exec_message_box",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    view._delete_item()

    assert service.delete_calls == [10]
    assert service.list_calls == initial_list_calls + 1
    assert view._current_id is None
