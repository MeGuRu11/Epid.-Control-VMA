from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from typing import cast

from app.application.dto.emz_dto import (
    EmzAntibioticCourseDto,
    EmzCaseDetail,
    EmzCaseResponse,
    EmzCreateRequest,
    EmzDiagnosisDto,
    EmzInterventionDto,
    EmzIsmpDto,
    EmzUpdateRequest,
)
from app.application.services.patient_service import PatientService
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.emz_repo import EmzRepository
from app.infrastructure.db.repositories.patient_repo import PatientRepository
from app.infrastructure.db.session import session_scope


def _to_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _compute_days(
    admission: date | datetime | None,
    injury: date | datetime | None,
    outcome: date | datetime | None,
) -> tuple[int | None, int | None]:
    admission_date = _to_date(admission)
    injury_date = _to_date(injury)
    outcome_date = _to_date(outcome)
    days_to_adm = (admission_date - injury_date).days if admission_date and injury_date else None
    los = (outcome_date - admission_date).days if outcome_date and admission_date else None
    return days_to_adm, los


def _validate_date_order(
    admission: date | datetime | None,
    injury: date | datetime | None,
    outcome: date | datetime | None,
) -> None:
    admission_date = _to_date(admission)
    injury_date = _to_date(injury)
    outcome_date = _to_date(outcome)
    if admission_date and injury_date and admission_date < injury_date:
        raise ValueError("Дата поступления не может быть раньше даты травмы")
    if outcome_date and admission_date and outcome_date < admission_date:
        raise ValueError("Дата исхода не может быть раньше даты поступления")
    if outcome_date and injury_date and outcome_date < injury_date:
        raise ValueError("Дата исхода не может быть раньше даты травмы")


class EmzService:
    def __init__(
        self,
        emz_repo: EmzRepository | None = None,
        patient_repo: PatientRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.emr_repo = emz_repo or EmzRepository()
        self.patient_repo = patient_repo or PatientRepository()
        self.patient_service = PatientService(patient_repo=self.patient_repo, session_factory=session_factory)
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def create_emr(self, request: EmzCreateRequest, actor_id: int | None) -> EmzCaseResponse:
        patient_resp = self.patient_service.create_or_get(request.to_patient_request())
        with self.session_factory() as session:
            existing = self.emr_repo.get_case_by_patient_and_no(
                session, patient_resp.id, request.hospital_case_no
            )
            if existing:
                raise ValueError(
                    "Номер истории болезни уже используется у этого пациента. "
                    "Выберите другой номер для новой госпитализации."
                )

            case = self.emr_repo.create_case(
                session,
                patient_id=patient_resp.id,
                hospital_case_no=request.hospital_case_no,
                department_id=request.department_id,
                user_id=actor_id,
            )

            _validate_date_order(
                request.payload.admission_date,
                request.payload.injury_date,
                request.payload.outcome_date,
            )
            days_to_adm, los = _compute_days(
                request.payload.admission_date,
                request.payload.injury_date,
                request.payload.outcome_date,
            )

            case_id = cast(int, case.id)
            version = self.emr_repo.add_version(
                session,
                emr_case_id=case_id,
                version_no=1,
                payload=request.payload.model_dump(
                    exclude={"diagnoses", "interventions", "antibiotic_courses", "ismp_cases"}
                ),
                entered_by=actor_id,
                computed={"days_to_admission": days_to_adm, "length_of_stay_days": los},
            )

            version_id = cast(int, version.id)
            self.emr_repo.replace_diagnoses(
                session, version_id, [d.model_dump() for d in request.payload.diagnoses]
            )
            self.emr_repo.replace_interventions(
                session, version_id, [i.model_dump() for i in request.payload.interventions]
            )
            self.emr_repo.replace_antibiotic_courses(
                session, version_id, [c.model_dump() for c in request.payload.antibiotic_courses]
            )
            self.emr_repo.replace_ismp(
                session, case_id, [c.model_dump() for c in request.payload.ismp_cases]
            )

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="emr_case",
                entity_id=str(case_id),
                action="create_emr",
                payload_json=json.dumps({"emr_case_id": case_id, "version_id": version_id}),
            )

            version_no = cast(int, version.version_no)
            is_current = cast(bool, version.is_current)
            valid_from = cast(datetime, version.valid_from)
            valid_to = cast(datetime | None, version.valid_to)
            days_to_admission = cast(int | None, version.days_to_admission)
            length_of_stay_days = cast(int | None, version.length_of_stay_days)
            return EmzCaseResponse(
                id=case_id,
                version_id=version_id,
                version_no=version_no,
                is_current=is_current,
                valid_from=valid_from,
                valid_to=valid_to,
                days_to_admission=days_to_admission,
                length_of_stay_days=length_of_stay_days,
            )

    def update_emr(self, request: EmzUpdateRequest, actor_id: int | None) -> EmzCaseResponse:
        with self.session_factory() as session:
            current = self.emr_repo.get_current_version(session, request.emr_case_id)
            if not current:
                raise ValueError("Текущая версия ЭМЗ не найдена")

            current_id = cast(int, current.id)
            self.emr_repo.close_version(session, current_id)

            _validate_date_order(
                request.payload.admission_date,
                request.payload.injury_date,
                request.payload.outcome_date,
            )
            days_to_adm, los = _compute_days(
                request.payload.admission_date,
                request.payload.injury_date,
                request.payload.outcome_date,
            )

            current_version_no = cast(int, current.version_no)
            new_version_no = current_version_no + 1
            version = self.emr_repo.add_version(
                session,
                emr_case_id=request.emr_case_id,
                version_no=new_version_no,
                payload=request.payload.model_dump(
                    exclude={"diagnoses", "interventions", "antibiotic_courses", "ismp_cases"}
                ),
                entered_by=actor_id,
                computed={"days_to_admission": days_to_adm, "length_of_stay_days": los},
            )

            version_id = cast(int, version.id)
            self.emr_repo.replace_diagnoses(
                session, version_id, [d.model_dump() for d in request.payload.diagnoses]
            )
            self.emr_repo.replace_interventions(
                session, version_id, [i.model_dump() for i in request.payload.interventions]
            )
            self.emr_repo.replace_antibiotic_courses(
                session, version_id, [c.model_dump() for c in request.payload.antibiotic_courses]
            )
            self.emr_repo.replace_ismp(
                session,
                request.emr_case_id,
                [c.model_dump() for c in request.payload.ismp_cases],
            )

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="emr_case",
                entity_id=str(request.emr_case_id),
                action="update_emr",
                payload_json=json.dumps({"version_id": version_id}),
            )

            version_no = cast(int, version.version_no)
            is_current = cast(bool, version.is_current)
            valid_from = cast(datetime, version.valid_from)
            valid_to = cast(datetime | None, version.valid_to)
            days_to_admission = cast(int | None, version.days_to_admission)
            length_of_stay_days = cast(int | None, version.length_of_stay_days)
            return EmzCaseResponse(
                id=request.emr_case_id,
                version_id=version_id,
                version_no=version_no,
                is_current=is_current,
                valid_from=valid_from,
                valid_to=valid_to,
                days_to_admission=days_to_admission,
                length_of_stay_days=length_of_stay_days,
            )

    def get_current(self, emr_case_id: int) -> EmzCaseDetail:
        with self.session_factory() as session:
            data = self.emr_repo.fetch_case_detail(session, emr_case_id)
            if not data:
                raise ValueError("Госпитализация ЭМЗ не найдена")
            case, version, diagnoses, interventions, abx, ismp = data
            case_id = cast(int, case.id)
            patient_id = cast(int, case.patient_id)
            case_no = cast(str, case.hospital_case_no)
            department_id = cast(int | None, case.department_id)
            version_no = cast(int, version.version_no)
            admission_date = cast(datetime | None, version.admission_date)
            injury_date = cast(datetime | None, version.injury_date)
            outcome_date = cast(datetime | None, version.outcome_date)
            severity = cast(str | None, version.severity)
            sofa_score = cast(int | None, version.sofa_score)
            vph_p_or_score = cast(int | None, version.vph_p_or_score)
            patient_obj = self.patient_repo.get_by_id(session, patient_id)
            patient_name = cast(str, patient_obj.full_name) if patient_obj else ""
            patient_dob = cast(date | None, patient_obj.dob) if patient_obj else None
            patient_sex = cast(str, patient_obj.sex) if patient_obj else "U"
            patient_category = cast(str | None, patient_obj.category) if patient_obj else None
            patient_military_unit = cast(str | None, patient_obj.military_unit) if patient_obj else None
            patient_military_district = cast(str | None, patient_obj.military_district) if patient_obj else None
            return EmzCaseDetail(
                id=case_id,
                patient_id=patient_id,
                patient_full_name=patient_name,
                patient_dob=patient_dob,
                patient_sex=patient_sex,
                patient_category=patient_category,
                patient_military_unit=patient_military_unit,
                patient_military_district=patient_military_district,
                hospital_case_no=case_no,
                department_id=department_id,
                version_no=version_no,
                admission_date=admission_date,
                injury_date=injury_date,
                outcome_date=outcome_date,
                severity=severity,
                sofa_score=sofa_score,
                vph_p_or_score=vph_p_or_score,
                diagnoses=[
                    EmzDiagnosisDto(
                        kind=(cast(str | None, d.kind) or ""),
                        icd10_code=cast(str | None, d.icd10_code),
                        free_text=cast(str | None, d.free_text),
                    )
                    for d in diagnoses
                ],
                interventions=[
                    EmzInterventionDto(
                        type=(cast(str | None, i.type) or ""),
                        start_dt=cast(datetime | None, i.start_dt),
                        end_dt=cast(datetime | None, i.end_dt),
                        duration_minutes=cast(int | None, i.duration_minutes),
                        performed_by=cast(str | None, i.performed_by),
                        notes=cast(str | None, i.notes),
                    )
                    for i in interventions
                ],
                antibiotic_courses=[
                    EmzAntibioticCourseDto(
                        start_dt=cast(datetime | None, a.start_dt),
                        end_dt=cast(datetime | None, a.end_dt),
                        antibiotic_id=cast(int | None, a.antibiotic_id),
                        drug_name_free=cast(str | None, a.drug_name_free),
                        route=cast(str | None, a.route),
                        dose=cast(str | None, a.dose),
                    )
                    for a in abx
                ],
                ismp_cases=[
                    EmzIsmpDto(
                        ismp_type=cast(str, i.ismp_type),
                        start_date=cast(date, i.start_date),
                    )
                    for i in ismp
                ],
            )

    def update_case_meta(
        self,
        emr_case_id: int,
        *,
        hospital_case_no: str,
        department_id: int | None,
        actor_id: int | None,
    ) -> None:
        with self.session_factory() as session:
            case = self.emr_repo.get_case(session, emr_case_id)
            if not case:
                raise ValueError("Госпитализация ЭМЗ не найдена")
            patient_id = cast(int, case.patient_id)
            if hospital_case_no:
                existing = self.emr_repo.get_case_by_patient_and_no(
                    session, patient_id, hospital_case_no
                )
                if existing and cast(int, existing.id) != emr_case_id:
                    raise ValueError(
                        "Номер истории болезни уже используется у этого пациента. "
                        "Выберите другой номер для новой госпитализации."
                    )
            self.emr_repo.update_case_meta(
                session,
                emr_case_id,
                hospital_case_no=hospital_case_no,
                department_id=department_id,
            )
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="emr_case",
                entity_id=str(emr_case_id),
                action="update_emr_case_meta",
                payload_json=json.dumps(
                    {
                        "hospital_case_no": hospital_case_no,
                        "department_id": department_id,
                    }
                ),
            )

    def list_cases_by_patient(self, patient_id: int) -> list[EmzCaseResponse]:
        with self.session_factory() as session:
            cases = self.emr_repo.list_cases_by_patient(session, patient_id)
            results: list[EmzCaseResponse] = []
            for case in cases:
                case_id = cast(int, case.id)
                version = self.emr_repo.get_current_version(session, case_id)
                if not version:
                    continue
                version_id = cast(int, version.id)
                version_no = cast(int, version.version_no)
                is_current = cast(bool, version.is_current)
                valid_from = cast(datetime, version.valid_from)
                valid_to = cast(datetime | None, version.valid_to)
                days_to_admission = cast(int | None, version.days_to_admission)
                length_of_stay_days = cast(int | None, version.length_of_stay_days)
                results.append(
                    EmzCaseResponse(
                        id=case_id,
                        version_id=version_id,
                        version_no=version_no,
                        is_current=is_current,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        days_to_admission=days_to_admission,
                        length_of_stay_days=length_of_stay_days,
                    )
                )
            return results

    def search_cases_by_case_no(self, query: str, limit: int = 10) -> list[EmzCaseResponse]:
        with self.session_factory() as session:
            cases = self.emr_repo.search_cases_by_case_no(session, query, limit=limit)
            results: list[EmzCaseResponse] = []
            for case in cases:
                case_id = cast(int, case.id)
                version = self.emr_repo.get_current_version(session, case_id)
                if not version:
                    continue
                version_id = cast(int, version.id)
                version_no = cast(int, version.version_no)
                is_current = cast(bool, version.is_current)
                valid_from = cast(datetime, version.valid_from)
                valid_to = cast(datetime | None, version.valid_to)
                days_to_admission = cast(int | None, version.days_to_admission)
                length_of_stay_days = cast(int | None, version.length_of_stay_days)
                results.append(
                    EmzCaseResponse(
                        id=case_id,
                        version_id=version_id,
                        version_no=version_no,
                        is_current=is_current,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        days_to_admission=days_to_admission,
                        length_of_stay_days=length_of_stay_days,
                    )
                )
            return results

    def search_cases_meta(self, query: str, limit: int = 10) -> list[dict]:
        with self.session_factory() as session:
            cases = self.emr_repo.search_cases_by_case_no(session, query, limit=limit)
            return [{"id": c.id, "case_no": c.hospital_case_no} for c in cases]

    def delete_emr(self, emr_case_id: int, actor_id: int | None) -> None:
        with self.session_factory() as session:
            deleted = self.emr_repo.delete_case(session, emr_case_id)
            if not deleted:
                raise ValueError("Госпитализация ЭМЗ не найдена")
