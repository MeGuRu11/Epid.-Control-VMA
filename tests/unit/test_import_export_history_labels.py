from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from app.application.dto.auth_dto import SessionContext
from app.application.services.exchange_service import ExchangeService
from app.ui.import_export.import_export_view import ImportExportView


class _HistoryServiceStub:
    def list_packages(
        self,
        limit: int = 50,
        direction: str | None = None,
        query: str | None = None,
    ) -> list[object]:
        del limit, direction, query
        return [
            SimpleNamespace(
                direction="legacy",
                package_format="",
                created_at=None,
                created_by=None,
                sha256="hash",
                file_path="C:/tmp/legacy.dat",
            )
        ]

    def get_actor_label(self, actor_id: int | None) -> str:
        return "admin" if actor_id else "—"


def test_history_fallback_labels_do_not_contain_question_mojibake(qapp) -> None:
    del qapp
    session = SessionContext(user_id=1, login="admin", role="admin")

    view = ImportExportView(exchange_service=cast(ExchangeService, _HistoryServiceStub()), session=session)

    format_item = view.history_table.item(0, 1)
    created_item = view.history_table.item(0, 2)
    assert format_item is not None
    assert created_item is not None
    assert format_item.text() == "Неизвестно"
    assert created_item.text() == "Неизвестно"
    assert "?" not in format_item.text()
    assert "?" not in created_item.text()
