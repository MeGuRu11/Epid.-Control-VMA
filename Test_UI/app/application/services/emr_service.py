from __future__ import annotations

from datetime import date

from ...application.dto.emr_dto import EmrCaseCreateIn, EmrVersionIn
from ...domain.rules import ensure_date_order, normalize_required_text
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.emr_repo import EmrRepo


def _days(a: date | None, b: date | None) -> int | None:
    if a is None or b is None:
        return None
    return (a - b).days


class EmrService:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._repo = EmrRepo(engine)
        self._audit = AuditLogger(engine)

    def ensure_case(self, patient_id: int, hospital_case_no: str, department: str = "") -> int:
        case_in = EmrCaseCreateIn(
            patient_id=patient_id,
            hospital_case_no=hospital_case_no.strip(),
            department=normalize_required_text(department, default="н/д"),
        )
        case_id = self._repo.ensure_case(
            patient_id=case_in.patient_id,
            hospital_case_no=case_in.hospital_case_no,
            department=case_in.department,
            department_id=case_in.department_id,
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "emr_case",
                str(case_id),
                "ensure_case",
                {"patient_id": patient_id},
            )
        )
        return case_id

    def versions(self, emr_case_id: int):
        return self._repo.list_versions(emr_case_id)

    def cases_for_patient(self, patient_id: int):
        return self._repo.list_cases_for_patient(patient_id)

    def current_version(self, emr_case_id: int):
        return self._repo.get_current_version(emr_case_id)

    def create_new_version(self, emr_case_id: int, payload: dict) -> int:
        dto = EmrVersionIn(
            admission_date=payload.get("admission_date"),
            injury_date=payload.get("injury_date"),
            outcome_date=payload.get("outcome_date"),
            outcome_type=payload.get("outcome_type"),
            severity=payload.get("severity"),
            vph_sp_score=payload.get("vph_sp_score"),
            vph_p_or_score=payload.get("vph_p_or_score"),
            sofa_score=payload.get("sofa_score"),
            notes=payload.get("notes"),
        )
        ensure_date_order(dto.injury_date, dto.admission_date, "injury/admission")
        ensure_date_order(dto.admission_date, dto.outcome_date, "admission/outcome")
        data = {
            "admission_date": dto.admission_date,
            "injury_date": dto.injury_date,
            "outcome_date": dto.outcome_date,
            "outcome_type": normalize_required_text(dto.outcome_type, default="н/д") if dto.outcome_type else None,
            "severity": normalize_required_text(dto.severity, default="н/д") if dto.severity else None,
            "vph_sp_score": dto.vph_sp_score,
            "vph_p_or_score": dto.vph_p_or_score,
            "sofa_score": dto.sofa_score,
            "notes": dto.notes,
            "days_to_admission": _days(dto.admission_date, dto.injury_date),
            "length_of_stay_days": _days(dto.outcome_date, dto.admission_date),
        }
        version_id = self._repo.create_version(
            emr_case_id=emr_case_id,
            entered_by=self._session.user_id,
            payload=data,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "emr_case_version",
                str(version_id),
                "create_version",
                {"emr_case_id": emr_case_id},
            )
        )
        return version_id

    def get_children(self, version_id: int) -> dict:
        return {
            "diagnoses": self._repo.get_diagnoses(version_id),
            "interventions": self._repo.get_interventions(version_id),
            "abx_courses": self._repo.get_abx_courses(version_id),
        }

    def save_children(
        self,
        emr_case_version_id: int,
        diagnoses: list[dict] | None = None,
        interventions: list[dict] | None = None,
        abx_courses: list[dict] | None = None,
    ) -> None:
        self._repo.replace_diagnoses(emr_case_version_id, diagnoses or [])
        self._repo.replace_interventions(emr_case_version_id, interventions or [])
        self._repo.replace_abx_courses(emr_case_version_id, abx_courses or [])
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "emr_case_version",
                str(emr_case_version_id),
                "save_children",
                {
                    "diagnoses": len(diagnoses or []),
                    "interventions": len(interventions or []),
                    "abx_courses": len(abx_courses or []),
                },
            )
        )

    def restore_version_as_new(self, version_id: int) -> int | None:
        old = self._repo.get_version(version_id)
        if old is None:
            return None
        payload = {
            "admission_date": old.admission_date,
            "injury_date": old.injury_date,
            "outcome_date": old.outcome_date,
            "outcome_type": old.outcome_type,
            "severity": old.severity,
            "vph_sp_score": old.vph_sp_score,
            "vph_p_or_score": old.vph_p_or_score,
            "sofa_score": old.sofa_score,
            "notes": old.notes,
        }
        return self.create_new_version(int(old.emr_case_id), payload)
