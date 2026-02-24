from __future__ import annotations

from datetime import date

from app.application.dto.emz_dto import EmzCaseDetail, EmzVersionPayload
from app.ui.emz.form_orchestrators import (
    LoadCaseContext,
    SaveCaseContext,
    collect_save_case_context,
    run_load_case,
    run_save_case,
)
from app.ui.emz.form_patient_identity import PatientIdentityData


def _payload() -> EmzVersionPayload:
    return EmzVersionPayload(diagnoses=[], interventions=[], antibiotic_courses=[], ismp_cases=[])


def _detail() -> EmzCaseDetail:
    return EmzCaseDetail(
        id=11,
        patient_id=22,
        patient_full_name="Ivanov Ivan",
        patient_dob=date(1990, 1, 1),
        patient_sex="M",
        hospital_case_no="HC-1",
        department_id=3,
        version_no=1,
        admission_date=None,
        injury_date=None,
        outcome_date=None,
        severity=None,
        sofa_score=None,
        vph_p_or_score=None,
        diagnoses=[],
        interventions=[],
        antibiotic_courses=[],
        ismp_cases=[],
    )


def _identity() -> PatientIdentityData:
    return PatientIdentityData(
        full_name="Ivanov Ivan",
        dob=date(1990, 1, 1),
        sex_code="M",
        category="OFFICER",
        military_unit="123",
        military_district="SPB",
    )


def test_collect_save_case_context_returns_none_when_required_invalid() -> None:
    calls = {"tables": 0, "payload": 0}

    def _validate_tables_dt() -> bool:
        calls["tables"] += 1
        return True

    def _build_payload() -> EmzVersionPayload:
        calls["payload"] += 1
        return _payload()

    context = collect_save_case_context(
        validate_required=lambda: False,
        validate_tables_dt=_validate_tables_dt,
        build_payload=_build_payload,
        get_category_value=lambda: "OFFICER",
        get_department_value=lambda: 1,
        emr_case_id=None,
    )
    assert context is None
    assert calls == {"tables": 0, "payload": 0}


def test_collect_save_case_context_returns_none_when_table_validation_fails() -> None:
    calls = {"payload": 0}

    def _build_payload() -> EmzVersionPayload:
        calls["payload"] += 1
        return _payload()

    context = collect_save_case_context(
        validate_required=lambda: True,
        validate_tables_dt=lambda: False,
        build_payload=_build_payload,
        get_category_value=lambda: "OFFICER",
        get_department_value=lambda: 1,
        emr_case_id=None,
    )
    assert context is None
    assert calls["payload"] == 0


def test_collect_save_case_context_collects_values_for_new_case() -> None:
    context = collect_save_case_context(
        validate_required=lambda: True,
        validate_tables_dt=lambda: True,
        build_payload=_payload,
        get_category_value=lambda: "OFFICER",
        get_department_value=lambda: 7,
        emr_case_id=None,
    )
    assert context == SaveCaseContext(
        payload=_payload(),
        category_value="OFFICER",
        department_value=7,
        is_new_case=True,
    )


def test_collect_save_case_context_marks_existing_case() -> None:
    context = collect_save_case_context(
        validate_required=lambda: True,
        validate_tables_dt=lambda: True,
        build_payload=_payload,
        get_category_value=lambda: "OFFICER",
        get_department_value=lambda: None,
        emr_case_id=55,
    )
    assert context is not None
    assert context.is_new_case is False


def test_run_save_case_calls_new_handler() -> None:
    calls: list[str] = []
    context = SaveCaseContext(
        payload=_payload(),
        category_value="OFFICER",
        department_value=1,
        is_new_case=True,
    )

    def _save_new(payload: EmzVersionPayload, category: str, department: int | None) -> None:
        assert payload == context.payload
        assert category == "OFFICER"
        assert department == 1
        calls.append("new")

    def _save_existing(payload: EmzVersionPayload, category: str, department: int | None) -> None:
        calls.append("existing")

    run_save_case(context=context, save_new=_save_new, save_existing=_save_existing)
    assert calls == ["new"]


def test_run_save_case_calls_existing_handler() -> None:
    calls: list[str] = []
    context = SaveCaseContext(
        payload=_payload(),
        category_value="OFFICER",
        department_value=None,
        is_new_case=False,
    )

    def _save_new(payload: EmzVersionPayload, category: str, department: int | None) -> None:
        calls.append("new")

    def _save_existing(payload: EmzVersionPayload, category: str, department: int | None) -> None:
        assert payload == context.payload
        assert category == "OFFICER"
        assert department is None
        calls.append("existing")

    run_save_case(context=context, save_new=_save_new, save_existing=_save_existing)
    assert calls == ["existing"]


def test_run_load_case_opens_by_case_id() -> None:
    detail = _detail()
    applied: list[int] = []

    opened_case = run_load_case(
        context=LoadCaseContext(patient_id=22, emr_case_id=11),
        get_case_detail=lambda case_id: detail if case_id == 11 else _detail(),
        apply_case_detail=lambda payload: applied.append(payload.id),
        get_patient_identity=lambda patient_id: (patient_id, _identity()),
        apply_patient_selection=lambda patient_id, identity: applied.append(patient_id + 1000),
    )
    assert opened_case is True
    assert applied == [11]


def test_run_load_case_selects_patient_when_case_missing() -> None:
    selected: list[int] = []

    opened_case = run_load_case(
        context=LoadCaseContext(patient_id=22, emr_case_id=None),
        get_case_detail=lambda case_id: _detail(),
        apply_case_detail=lambda payload: selected.append(payload.id),
        get_patient_identity=lambda patient_id: (patient_id, _identity()),
        apply_patient_selection=lambda patient_id, identity: selected.append(patient_id),
    )
    assert opened_case is False
    assert selected == [22]


def test_run_load_case_noop_when_no_ids() -> None:
    called = {"detail": 0, "patient": 0}

    def _apply_detail(detail: EmzCaseDetail) -> None:
        called["detail"] += 1

    def _apply_patient(patient_id: int, identity: PatientIdentityData) -> None:
        called["patient"] += 1

    opened_case = run_load_case(
        context=LoadCaseContext(patient_id=None, emr_case_id=None),
        get_case_detail=lambda case_id: _detail(),
        apply_case_detail=_apply_detail,
        get_patient_identity=lambda patient_id: (patient_id, _identity()),
        apply_patient_selection=_apply_patient,
    )
    assert opened_case is False
    assert called == {"detail": 0, "patient": 0}
