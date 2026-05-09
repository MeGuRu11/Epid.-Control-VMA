from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100UpdateV2Request,
)
from app.infrastructure.reporting import form100_pdf_report_v2 as report_module
from app.ui.form100_v2.form100_wizard import Form100Wizard
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_identification import StepIdentification


class _Form100ServiceStub:
    def __init__(self) -> None:
        self.created: list[Form100CreateV2Request] = []
        self.updated: list[tuple[str, Form100UpdateV2Request, int]] = []

    def create_card(self, request: Form100CreateV2Request, *, actor_id: int) -> Form100CardV2Dto:
        del actor_id
        self.created.append(request)
        return _card(birth_date=request.birth_date, data=request.data)

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
        return _card(
            card_id=card_id,
            birth_date=request.birth_date,
            data=request.data or Form100DataV2Dto(),
            version=expected_version + 1,
        )


def _session() -> SessionContext:
    return SessionContext(user_id=1, login="operator", role="operator")


def _card(
    *,
    card_id: str = "F100-1",
    birth_date: date | None = None,
    data: Form100DataV2Dto | None = None,
    version: int = 1,
) -> Form100CardV2Dto:
    now = datetime.now(tz=UTC)
    return Form100CardV2Dto(
        id=card_id,
        emr_case_id=11,
        created_at=now,
        created_by="operator",
        updated_at=now,
        updated_by="operator",
        status="DRAFT",
        version=version,
        is_archived=False,
        main_full_name="Иванов Иван",
        main_unit="1 рота",
        main_id_tag="Ж-100",
        main_diagnosis="Диагноз",
        birth_date=birth_date,
        data=data or Form100DataV2Dto(),
    )


def _wizard(service: _Form100ServiceStub, card: Form100CardV2Dto | None = None) -> Form100Wizard:
    return Form100Wizard(
        form100_service=cast(Any, service),
        session=_session(),
        card=card,
        emr_case_id=11,
    )


def _fill_required_identification(step: StepIdentification) -> None:
    step.main_full_name.setText("Иванов Иван")
    step.main_unit.setText("1 рота")
    step.main_id_tag.setText("Ж-100")


def _plain_texts(elements: list[Any]) -> list[str]:
    texts: list[str] = []

    def _walk(value: Any) -> None:
        if hasattr(value, "getPlainText"):
            texts.append(str(value.getPlainText()))
            return
        cellvalues = getattr(value, "_cellvalues", None)
        if isinstance(cellvalues, list):
            for row in cellvalues:
                if isinstance(row, list):
                    for cell in row:
                        _walk(cell)
                else:
                    _walk(row)

    for element in elements:
        _walk(element)
    return texts


def test_birth_date_widget_exists_and_empty_by_default(qapp) -> None:
    del qapp
    step = StepIdentification()
    try:
        assert isinstance(step.birth_date, QDateEdit)
        assert step.birth_date.specialValueText() == "Не указана"
        assert step.birth_date.minimumDate() == QDate(1900, 1, 1)
        assert step._get_birth_date() is None
    finally:
        step.close()


def test_birth_date_collects_iso_and_restores_existing_payload(qapp) -> None:
    del qapp
    step = StepIdentification()
    try:
        step.set_values({"birth_date_iso": "1985-06-15"}, [])
        assert step._get_birth_date() == date(1985, 6, 15)

        payload, _markers = step.collect()
        assert payload["birth_date_iso"] == "1985-06-15"
    finally:
        step.close()


def test_birth_date_saved_to_create_request(qapp) -> None:
    del qapp
    service = _Form100ServiceStub()
    wizard = _wizard(service)
    try:
        _fill_required_identification(wizard._step1)
        wizard._step1.birth_date.setDate(QDate(1985, 6, 15))

        payload, markers = wizard._collect_all()
        wizard._do_save(payload, markers)

        assert service.created[0].birth_date == date(1985, 6, 15)
    finally:
        wizard.close()


def test_birth_date_saved_to_update_request(qapp) -> None:
    del qapp
    service = _Form100ServiceStub()
    wizard = _wizard(service, card=_card(card_id="F100-2", version=4))
    try:
        _fill_required_identification(wizard._step1)
        wizard._step1.birth_date.setDate(QDate(1992, 2, 2))

        payload, markers = wizard._collect_all()
        wizard._do_save(payload, markers)

        _card_id, request, _expected_version = service.updated[0]
        assert request.birth_date == date(1992, 2, 2)
    finally:
        wizard.close()


def test_birth_date_loaded_from_existing_card(qapp) -> None:
    del qapp
    service = _Form100ServiceStub()
    wizard = _wizard(service, card=_card(birth_date=date(1985, 6, 15)))
    try:
        assert wizard._step1._get_birth_date() == date(1985, 6, 15)
    finally:
        wizard.close()


def test_pdf_birth_date_format_is_ddmmyyyy(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, list[Any]] = {}

    def _capture_elements(_doc: Any, elements: list[Any]) -> None:
        captured["elements"] = elements

    monkeypatch.setattr(report_module, "build_invariant_pdf", _capture_elements)

    report_module.export_form100_pdf_v2(
        card={
            "id": "F100-1",
            "version": 1,
            "status": "DRAFT",
            "birth_date": date(1985, 6, 15),
            "data": {
                "main": {"main_full_name": "Иванов Иван"},
                "bottom": {"main_diagnosis": "Диагноз"},
                "flags": {},
                "bodymap_annotations": [],
            },
        },
        file_path=tmp_path / "form100.pdf",
    )

    plain_text = "\n".join(_plain_texts(captured["elements"]))
    assert "15.06.1985" in plain_text
    assert "1985-06-15" not in plain_text
