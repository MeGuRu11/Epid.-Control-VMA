from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import (
    EmrAntibioticCourse,
    EmrCase,
    EmrCaseVersion,
    EmrDiagnosis,
    EmrIntervention,
    IsmpCase,
    LabSample,
)


class EmzRepository:
    def get_case(self, session: Session, emr_case_id: int) -> EmrCase | None:
        stmt = select(EmrCase).where(EmrCase.id == emr_case_id)
        return session.execute(stmt).scalar_one_or_none()

    def get_case_by_patient_and_no(
        self, session: Session, patient_id: int, hospital_case_no: str
    ) -> EmrCase | None:
        stmt = select(EmrCase).where(
            EmrCase.patient_id == patient_id,
            EmrCase.hospital_case_no == hospital_case_no,
        )
        return session.execute(stmt).scalar_one_or_none()

    def get_current_version(self, session: Session, emr_case_id: int) -> EmrCaseVersion | None:
        stmt = (
            select(EmrCaseVersion)
            .where(EmrCaseVersion.emr_case_id == emr_case_id, EmrCaseVersion.is_current == True)  # noqa: E712
        )
        return session.execute(stmt).scalar_one_or_none()

    def create_case(self, session: Session, patient_id: int, hospital_case_no: str, department_id: int | None, user_id: int | None) -> EmrCase:
        case = EmrCase(
            patient_id=patient_id,
            hospital_case_no=hospital_case_no,
            department_id=department_id,
            created_by=user_id,
        )
        session.add(case)
        session.flush()
        return case

    def add_version(
        self,
        session: Session,
        emr_case_id: int,
        version_no: int,
        payload: dict,
        entered_by: int | None,
        computed: dict,
    ) -> EmrCaseVersion:
        version = EmrCaseVersion(
            emr_case_id=emr_case_id,
            version_no=version_no,
            valid_from=datetime.now(UTC),
            valid_to=None,
            is_current=True,
            entered_by=entered_by,
            **payload,
            **computed,
        )
        session.add(version)
        session.flush()
        return version

    def close_version(self, session: Session, version_id: int) -> None:
        stmt = (
            update(EmrCaseVersion)
            .where(EmrCaseVersion.id == version_id)
            .values(is_current=False, valid_to=datetime.now(UTC))
        )
        session.execute(stmt)

    def replace_diagnoses(self, session: Session, version_id: int, items: Iterable[dict]) -> None:
        session.query(EmrDiagnosis).filter(EmrDiagnosis.emr_case_version_id == version_id).delete()
        objects = [EmrDiagnosis(emr_case_version_id=version_id, **item) for item in items]
        session.add_all(objects)

    def replace_interventions(self, session: Session, version_id: int, items: Iterable[dict]) -> None:
        session.query(EmrIntervention).filter(EmrIntervention.emr_case_version_id == version_id).delete()
        objects = [EmrIntervention(emr_case_version_id=version_id, **item) for item in items]
        session.add_all(objects)

    def replace_antibiotic_courses(self, session: Session, version_id: int, items: Iterable[dict]) -> None:
        session.query(EmrAntibioticCourse).filter(EmrAntibioticCourse.emr_case_version_id == version_id).delete()
        objects = [EmrAntibioticCourse(emr_case_version_id=version_id, **item) for item in items]
        session.add_all(objects)

    def replace_ismp(self, session: Session, emr_case_id: int, items: Iterable[dict]) -> None:
        session.query(IsmpCase).filter(IsmpCase.emr_case_id == emr_case_id).delete()
        objects = [IsmpCase(emr_case_id=emr_case_id, **item) for item in items]
        session.add_all(objects)

    def list_ismp(self, session: Session, emr_case_id: int) -> list[IsmpCase]:
        stmt = select(IsmpCase).where(IsmpCase.emr_case_id == emr_case_id).order_by(IsmpCase.start_date.asc())
        return list(session.execute(stmt).scalars())

    def fetch_case_detail(
        self, session: Session, emr_case_id: int
    ) -> tuple[
        EmrCase,
        EmrCaseVersion,
        list[EmrDiagnosis],
        list[EmrIntervention],
        list[EmrAntibioticCourse],
        list[IsmpCase],
    ] | None:
        case = self.get_case(session, emr_case_id)
        if not case:
            return None
        version = self.get_current_version(session, emr_case_id)
        if not version:
            return None
        diagnoses = session.query(EmrDiagnosis).filter(EmrDiagnosis.emr_case_version_id == version.id).all()
        interventions = session.query(EmrIntervention).filter(EmrIntervention.emr_case_version_id == version.id).all()
        abx = session.query(EmrAntibioticCourse).filter(EmrAntibioticCourse.emr_case_version_id == version.id).all()
        ismp = self.list_ismp(session, emr_case_id)
        return case, version, diagnoses, interventions, abx, ismp

    def list_cases_by_patient(self, session: Session, patient_id: int) -> list[EmrCase]:
        stmt = select(EmrCase).where(EmrCase.patient_id == patient_id).order_by(EmrCase.created_at.desc())
        return list(session.execute(stmt).scalars())

    def search_cases_by_case_no(self, session: Session, query: str, limit: int = 10) -> list[EmrCase]:
        stmt = (
            select(EmrCase)
            .where(EmrCase.hospital_case_no.ilike(f"%{query}%"))
            .order_by(EmrCase.created_at.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def delete_case(self, session: Session, emr_case_id: int) -> bool:
        case = self.get_case(session, emr_case_id)
        if not case:
            return False

        version_ids = [
            row[0]
            for row in session.execute(
                select(EmrCaseVersion.id).where(EmrCaseVersion.emr_case_id == emr_case_id)
            ).all()
        ]
        if version_ids:
            session.query(EmrDiagnosis).filter(
                EmrDiagnosis.emr_case_version_id.in_(version_ids)
            ).delete(synchronize_session=False)
            session.query(EmrIntervention).filter(
                EmrIntervention.emr_case_version_id.in_(version_ids)
            ).delete(synchronize_session=False)
            session.query(EmrAntibioticCourse).filter(
                EmrAntibioticCourse.emr_case_version_id.in_(version_ids)
            ).delete(synchronize_session=False)
            session.query(EmrCaseVersion).filter(
                EmrCaseVersion.id.in_(version_ids)
            ).delete(synchronize_session=False)

        session.query(IsmpCase).filter(IsmpCase.emr_case_id == emr_case_id).delete(
            synchronize_session=False
        )
        session.query(LabSample).filter(LabSample.emr_case_id == emr_case_id).update(
            {"emr_case_id": None},
            synchronize_session=False,
        )
        session.query(EmrCase).filter(EmrCase.id == emr_case_id).delete(synchronize_session=False)
        return True

    def update_case_meta(
        self,
        session: Session,
        emr_case_id: int,
        *,
        hospital_case_no: str,
        department_id: int | None,
    ) -> None:
        stmt = (
            update(EmrCase)
            .where(EmrCase.id == emr_case_id)
            .values(hospital_case_no=hospital_case_no, department_id=department_id)
        )
        session.execute(stmt)
