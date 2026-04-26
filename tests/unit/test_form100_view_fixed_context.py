from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CreateV2Request,
    Form100UpdateV2Request,
    Form100V2Filters,
)
from app.ui.form100_v2 import form100_view as form100_view_module
from app.ui.form100_v2.form100_view import Form100ViewV2


class _Form100ServiceStub:
    def __init__(self) -> None:
        self.list_calls: list[tuple[Form100V2Filters, int, int]] = []
        self.created: list[Form100CreateV2Request] = []
        self.updated: list[tuple[str, Form100UpdateV2Request, int]] = []

    def list_cards(
        self,
        *,
        filters: Form100V2Filters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        self.list_calls.append((filters, limit, offset))
        return []

    def create_card(self, request: Form100CreateV2Request, *, actor_id: int) -> Form100CardV2Dto:
        self.created.append(request)
        return _card(card_id="F100-1", emr_case_id=request.emr_case_id, version=1)

    def update_card(
        self,
        card_id: str,
        request: Form100UpdateV2Request,
        *,
        actor_id: int,
        expected_version: int,
    ) -> Form100CardV2Dto:
        del actor_id
        self.updated.append((card_id, request, expected_version))
        return _card(card_id=card_id, emr_case_id=request.emr_case_id, version=expected_version + 1)


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def _card(card_id: str = "F100-1", emr_case_id: int | None = None, version: int = 1) -> Form100CardV2Dto:
    now = datetime.now(tz=UTC)
    return Form100CardV2Dto(
        id=card_id,
        emr_case_id=emr_case_id,
        created_at=now,
        created_by="admin",
        updated_at=now,
        updated_by="admin",
        status="DRAFT",
        version=version,
        is_archived=False,
        main_full_name="Иванов Иван",
        main_unit="1 рота",
        main_id_tag=None,
        main_diagnosis="Диагноз",
        birth_date=None,
    )


def _view(service: _Form100ServiceStub) -> Form100ViewV2:
    return Form100ViewV2(
        form100_service=cast(Any, service),
        reporting_service=None,
        session=_session(),
        fixed_patient_id=7,
        fixed_emr_case_id=9,
        embedded_mode=True,
    )


def test_form100_view_fixed_context_adds_patient_and_case_filters(qapp) -> None:
    del qapp
    service = _Form100ServiceStub()
    view = _view(service)
    try:
        filters, limit, offset = service.list_calls[0]
        assert filters.patient_id == 7
        assert filters.emr_case_id == 9
        assert limit == 500
        assert offset == 0
    finally:
        view.close()


def test_form100_view_create_in_embedded_mode_sets_current_case(qapp, monkeypatch) -> None:
    del qapp
    service = _Form100ServiceStub()
    monkeypatch.setattr(form100_view_module, "show_info", lambda *args, **kwargs: None)
    view = _view(service)
    try:
        monkeypatch.setattr(
            view.editor,
            "build_create_request",
            lambda: Form100CreateV2Request(
                emr_case_id=None,
                main_full_name="Иванов Иван",
                main_unit="1 рота",
                main_diagnosis="Диагноз",
            ),
        )
        monkeypatch.setattr(view.editor, "load_card", lambda card: None)
        monkeypatch.setattr(view.editor, "set_read_only", lambda read_only: None)

        view._save_card()

        assert service.created
        assert service.created[0].emr_case_id == 9
    finally:
        view.close()


def test_form100_view_update_in_embedded_mode_preserves_current_case(qapp, monkeypatch) -> None:
    del qapp
    service = _Form100ServiceStub()
    monkeypatch.setattr(form100_view_module, "show_info", lambda *args, **kwargs: None)
    view = _view(service)
    try:
        current_card = _card(card_id="F100-2", emr_case_id=3, version=4)
        view.editor.current_card = current_card
        monkeypatch.setattr(
            view.editor,
            "build_update_request",
            lambda: Form100UpdateV2Request(
                emr_case_id=None,
                main_full_name="Иванов Иван",
                main_unit="1 рота",
                main_diagnosis="Обновленный диагноз",
            ),
        )
        monkeypatch.setattr(view.editor, "load_card", lambda card: None)
        monkeypatch.setattr(view.editor, "set_read_only", lambda read_only: None)

        view._save_card()

        assert service.updated
        card_id, request, expected_version = service.updated[0]
        assert card_id == "F100-2"
        assert expected_version == 4
        assert request.emr_case_id == 9
    finally:
        view.close()
