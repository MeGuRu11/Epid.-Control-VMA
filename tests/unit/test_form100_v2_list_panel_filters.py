from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import Form100CardV2ListItemDto, Form100V2Filters
from app.ui.form100_v2 import form100_list_panel as list_panel_module
from app.ui.form100_v2.form100_list_panel import Form100ListPanel


class _ServiceStub:
    def __init__(self) -> None:
        self.calls: list[Form100V2Filters] = []
        self.rows: list[Form100CardV2ListItemDto] = []
        self.export_pdf_calls: list[tuple[str, str, int]] = []

    def list_cards(self, filters: Form100V2Filters, limit: int = 100) -> list[Form100CardV2ListItemDto]:
        del limit
        self.calls.append(filters)
        return self.rows

    def export_pdf(self, card_id: str, file_path: str, actor_id: int) -> dict[str, object]:
        self.export_pdf_calls.append((card_id, file_path, actor_id))
        return {"path": file_path, "card_id": card_id, "sha256": "abc"}


def test_list_panel_uses_patient_scope_first(qapp) -> None:
    service = _ServiceStub()
    panel = Form100ListPanel(
        form100_service=cast(Any, service),
        session=SessionContext(user_id=1, login="admin", role="admin"),
        patient_id=42,
        emr_case_id=777,
    )
    qapp.processEvents()

    assert service.calls
    filters = service.calls[0]
    assert filters.patient_id == 42
    assert filters.emr_case_id is None
    panel.close()


def test_list_panel_exports_selected_card_pdf(qapp, monkeypatch) -> None:
    service = _ServiceStub()
    service.rows = [
        Form100CardV2ListItemDto(
            id="F100-1",
            status="DRAFT",
            version=1,
            main_full_name="Иванов Иван",
            birth_date=None,
            main_unit="1 рота",
            main_id_tag=None,
            main_diagnosis="Диагноз",
            updated_at=datetime.now(tz=UTC),
            is_archived=False,
        )
    ]
    monkeypatch.setattr(
        list_panel_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("C:/tmp/form100.pdf", "PDF (*.pdf)"),
    )
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(
        list_panel_module,
        "exec_message_box",
        lambda parent, title, message, **kwargs: messages.append((title, message)),
    )
    panel = Form100ListPanel(
        form100_service=cast(Any, service),
        session=SessionContext(user_id=1, login="admin", role="admin"),
        patient_id=42,
        emr_case_id=777,
    )
    try:
        panel._table.selectRow(0)
        qapp.processEvents()

        panel._export_selected_pdf()

        assert service.export_pdf_calls == [("F100-1", "C:/tmp/form100.pdf", 1)]
        assert messages
        assert messages[-1][0] == "Форма 100"
    finally:
        panel.close()
