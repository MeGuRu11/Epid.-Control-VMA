from __future__ import annotations

from typing import Any, cast

import pytest
from PySide6.QtWidgets import QDialog

from app.application.dto.auth_dto import SessionContext
from app.application.services.exchange_service import ExchangeService
from app.ui.import_export import import_export_view as import_export_view_module
from app.ui.import_export.import_export_view import ImportExportView
from app.ui.import_export.import_export_wizard import ImportExportWizard


class _ExchangeServiceStub:
    def list_packages(
        self,
        limit: int = 50,
        direction: str | None = None,
        query: str | None = None,
    ) -> list[object]:
        return []


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="admin", role="admin")


def test_direction_page_contextually_hides_irrelevant_controls(qapp) -> None:
    wizard = ImportExportWizard(
        exchange_service=cast(ExchangeService, _ExchangeServiceStub()),
        session=_session(),
        table_labels={"patients": "Пациенты"},
    )
    page = wizard._direction_page

    assert page.table_select.isHidden()
    assert page.import_mode.isHidden()
    assert "полный набор листов" in page._context_hint.text().lower()

    page.format.setCurrentText("CSV")
    qapp.processEvents()
    assert not page.table_select.isHidden()
    assert page.import_mode.isHidden()
    assert "по одной таблице" in page._context_hint.text().lower()

    page.direction.setCurrentText("Импорт")
    qapp.processEvents()
    assert not page.table_select.isHidden()
    assert not page.import_mode.isHidden()

    page.format.setCurrentText("Excel")
    qapp.processEvents()
    assert page.table_select.isHidden()
    assert not page.import_mode.isHidden()
    assert "обновлять ли существующие записи" in page._context_hint.text().lower()


def test_import_export_view_reloads_history_after_successful_wizard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _AcceptedWizard:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs

        def exec(self) -> int:
            return int(QDialog.DialogCode.Accepted)

    monkeypatch.setattr(import_export_view_module, "ImportExportWizard", _AcceptedWizard)

    view = ImportExportView(exchange_service=cast(ExchangeService, _ExchangeServiceStub()), session=_session())
    calls: list[str] = []

    def _fake_load_history() -> None:
        calls.append("loaded")

    monkeypatch.setattr(view, "_load_history", _fake_load_history)
    view._open_wizard()

    assert calls == ["loaded"]
