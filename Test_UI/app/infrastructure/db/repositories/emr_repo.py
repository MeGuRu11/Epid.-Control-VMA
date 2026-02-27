from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.infrastructure.db.models_sqlalchemy import (
    EmrAntibioticCourse,
    EmrCase,
    EmrCaseVersion,
    EmrDiagnosis,
    EmrIntervention,
)
from .base import RepoBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmrRepo(RepoBase):
    def ensure_case(
        self,
        patient_id: int,
        hospital_case_no: str,
        department: str | None = None,
        department_id: int | None = None,
        created_by: int | None = None,
    ) -> int:
        with self.tx() as s:
            existing = s.execute(
                select(EmrCase).where(
                    EmrCase.patient_id == patient_id,
                    EmrCase.hospital_case_no == hospital_case_no,
                )
            ).scalar_one_or_none()
            if existing:
                return int(existing.id)
            row = EmrCase(
                patient_id=patient_id,
                hospital_case_no=hospital_case_no,
                department=department,
                department_id=department_id,
                created_by=created_by,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def list_versions(self, emr_case_id: int) -> list[EmrCaseVersion]:
        with self.tx() as s:
            return list(
                s.execute(
                    select(EmrCaseVersion)
                    .where(EmrCaseVersion.emr_case_id == emr_case_id)
                    .order_by(EmrCaseVersion.version_no.desc())
                ).scalars()
            )

    def list_cases_for_patient(self, patient_id: int) -> list[EmrCase]:
        with self.tx() as s:
            return list(
                s.execute(
                    select(EmrCase)
                    .where(EmrCase.patient_id == patient_id)
                    .order_by(EmrCase.created_at.desc(), EmrCase.id.desc())
                ).scalars()
            )

    def get_current_version(self, emr_case_id: int) -> EmrCaseVersion | None:
        with self.tx() as s:
            return s.execute(
                select(EmrCaseVersion)
                .where(
                    EmrCaseVersion.emr_case_id == emr_case_id,
                    EmrCaseVersion.is_current == True,  # noqa: E712
                )
                .limit(1)
            ).scalar_one_or_none()

    def get_version(self, version_id: int) -> EmrCaseVersion | None:
        with self.tx() as s:
            return s.get(EmrCaseVersion, version_id)

    def create_version(self, emr_case_id: int, entered_by: int | None, payload: dict) -> int:
        with self.tx() as s:
            current = s.execute(
                select(EmrCaseVersion).where(
                    EmrCaseVersion.emr_case_id == emr_case_id,
                    EmrCaseVersion.is_current == True,  # noqa: E712
                )
            ).scalar_one_or_none()
            if current:
                current.is_current = False
                current.valid_to = utcnow()

            next_no = int(
                s.execute(
                    select(func.coalesce(func.max(EmrCaseVersion.version_no), 0)).where(
                        EmrCaseVersion.emr_case_id == emr_case_id
                    )
                ).scalar_one()
            ) + 1

            row = EmrCaseVersion(
                emr_case_id=emr_case_id,
                version_no=next_no,
                is_current=True,
                valid_from=utcnow(),
                entered_by=entered_by,
                admission_date=payload.get("admission_date"),
                injury_date=payload.get("injury_date"),
                outcome_date=payload.get("outcome_date"),
                outcome_type=payload.get("outcome_type"),
                severity=payload.get("severity"),
                vph_sp_score=payload.get("vph_sp_score"),
                vph_p_or_score=payload.get("vph_p_or_score"),
                sofa_score=payload.get("sofa_score"),
                notes=payload.get("notes"),
                days_to_admission=payload.get("days_to_admission"),
                length_of_stay_days=payload.get("length_of_stay_days"),
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def get_diagnoses(self, version_id: int) -> list[EmrDiagnosis]:
        with self.tx() as s:
            return list(
                s.execute(select(EmrDiagnosis).where(EmrDiagnosis.emr_case_version_id == version_id)).scalars().all()
            )

    def get_interventions(self, version_id: int) -> list[EmrIntervention]:
        with self.tx() as s:
            return list(
                s.execute(
                    select(EmrIntervention).where(EmrIntervention.emr_case_version_id == version_id)
                ).scalars().all()
            )

    def get_abx_courses(self, version_id: int) -> list[EmrAntibioticCourse]:
        with self.tx() as s:
            return list(
                s.execute(
                    select(EmrAntibioticCourse).where(EmrAntibioticCourse.emr_case_version_id == version_id)
                ).scalars().all()
            )

    def replace_diagnoses(self, emr_case_version_id: int, rows: list[dict]) -> None:
        with self.tx() as s:
            s.query(EmrDiagnosis).filter(EmrDiagnosis.emr_case_version_id == emr_case_version_id).delete()
            for item in rows:
                s.add(
                    EmrDiagnosis(
                        emr_case_version_id=emr_case_version_id,
                        kind=item.get("kind", "admission"),
                        icd10_code=item.get("icd10_code"),
                        free_text=item.get("free_text"),
                    )
                )

    def replace_interventions(self, emr_case_version_id: int, rows: list[dict]) -> None:
        with self.tx() as s:
            s.query(EmrIntervention).filter(EmrIntervention.emr_case_version_id == emr_case_version_id).delete()
            for item in rows:
                s.add(
                    EmrIntervention(
                        emr_case_version_id=emr_case_version_id,
                        type=item.get("type", "other"),
                        start_dt=item.get("start_dt"),
                        end_dt=item.get("end_dt"),
                        duration_minutes=item.get("duration_minutes"),
                        performed_by=item.get("performed_by"),
                        notes=item.get("notes"),
                    )
                )

    def replace_abx_courses(self, emr_case_version_id: int, rows: list[dict]) -> None:
        with self.tx() as s:
            s.query(EmrAntibioticCourse).filter(
                EmrAntibioticCourse.emr_case_version_id == emr_case_version_id
            ).delete()
            for item in rows:
                s.add(
                    EmrAntibioticCourse(
                        emr_case_version_id=emr_case_version_id,
                        start_dt=item.get("start_dt"),
                        end_dt=item.get("end_dt"),
                        antibiotic_id=item.get("antibiotic_id"),
                        drug_name_free=item.get("drug_name_free"),
                        route=item.get("route"),
                        dose=item.get("dose"),
                    )
                )
