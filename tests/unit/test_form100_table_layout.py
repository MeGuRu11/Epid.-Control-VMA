from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from PySide6.QtWidgets import QHeaderView

from app.application.dto.auth_dto import SessionContext
from app.ui.form100.form100_view import Form100View


class _FakeForm100Service:
    def list_cards(self, *, filters, limit: int, offset: int):  # noqa: ANN001
        _ = filters, limit, offset
        return [
            SimpleNamespace(
                id="CARD-1",
                status="DRAFT",
                version=1,
                last_name="Иванов",
                first_name="Иван",
                middle_name="Иванович",
                birth_date=date(1990, 1, 1),
                unit="Отделение №1",
                dog_tag_number="TAG-11",
                updated_at=datetime(2026, 2, 1, 9, 30, tzinfo=UTC),
            )
        ]

    def get_card(self, _card_id: str):  # noqa: ANN001
        raise RuntimeError("not needed")


def test_form100_table_has_fixed_header_sections_and_non_movable_columns(qapp) -> None:
    view = Form100View(
        form100_service=_FakeForm100Service(),
        reporting_service=None,
        session=SessionContext(user_id=1, login="admin", role="admin"),
    )
    view.resize(1500, 900)
    qapp.processEvents()

    header = view.cards_table.horizontalHeader()
    assert header.sectionsMovable() is False
    # Fixed mode blocks manual drag-resizing by users.
    assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Fixed
    assert header.sectionResizeMode(7) == QHeaderView.ResizeMode.Fixed
