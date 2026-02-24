from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.application.dto.emz_dto import EmzCaseDetail, EmzVersionPayload
from app.ui.emz.form_patient_identity import PatientIdentityData


@dataclass(frozen=True)
class SaveCaseContext:
    payload: EmzVersionPayload
    category_value: str
    department_value: int | None
    is_new_case: bool


@dataclass(frozen=True)
class LoadCaseContext:
    patient_id: int | None
    emr_case_id: int | None


def collect_save_case_context(
    *,
    validate_required: Callable[[], bool],
    validate_tables_dt: Callable[[], bool],
    build_payload: Callable[[], EmzVersionPayload],
    get_category_value: Callable[[], str],
    get_department_value: Callable[[], int | None],
    emr_case_id: int | None,
) -> SaveCaseContext | None:
    if not validate_required() or not validate_tables_dt():
        return None
    return SaveCaseContext(
        payload=build_payload(),
        category_value=get_category_value(),
        department_value=get_department_value(),
        is_new_case=emr_case_id is None,
    )


def run_save_case(
    *,
    context: SaveCaseContext,
    save_new: Callable[[EmzVersionPayload, str, int | None], None],
    save_existing: Callable[[EmzVersionPayload, str, int | None], None],
) -> None:
    if context.is_new_case:
        save_new(context.payload, context.category_value, context.department_value)
        return
    save_existing(context.payload, context.category_value, context.department_value)


def run_load_case(
    *,
    context: LoadCaseContext,
    get_case_detail: Callable[[int], EmzCaseDetail],
    apply_case_detail: Callable[[EmzCaseDetail], None],
    get_patient_identity: Callable[[int], tuple[int, PatientIdentityData]],
    apply_patient_selection: Callable[[int, PatientIdentityData], None],
) -> bool:
    if context.emr_case_id is not None:
        detail = get_case_detail(context.emr_case_id)
        apply_case_detail(detail)
        return True
    if context.patient_id is not None:
        patient_id, identity = get_patient_identity(context.patient_id)
        apply_patient_selection(patient_id, identity)
    return False
