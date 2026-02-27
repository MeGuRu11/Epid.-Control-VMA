from __future__ import annotations

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import Form100V2Filters
from app.ui.form100_v2.form100_list_panel import Form100ListPanel


class _ServiceStub:
    def __init__(self) -> None:
        self.calls: list[Form100V2Filters] = []

    def list_cards(self, filters: Form100V2Filters, limit: int = 100) -> list:  # noqa: ANN401
        self.calls.append(filters)
        return []


def test_list_panel_uses_patient_scope_first(qapp) -> None:
    service = _ServiceStub()
    panel = Form100ListPanel(
        form100_service=service,  # type: ignore[arg-type]
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
