from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import (
    LabAbxSusceptibility,
    LabMicrobeIsolation,
    LabNumberSequence,
    LabPhagePanelResult,
    LabSample,
)


class LabRepository:
    def get_sample(self, session: Session, sample_id: int) -> LabSample | None:
        stmt = select(LabSample).where(LabSample.id == sample_id)
        return session.execute(stmt).scalar_one_or_none()

    def list_by_patient(self, session: Session, patient_id: int, emr_case_id: int | None = None) -> list[LabSample]:
        stmt = select(LabSample).where(LabSample.patient_id == patient_id)
        if emr_case_id is not None:
            stmt = stmt.where(LabSample.emr_case_id == emr_case_id)
        stmt = stmt.order_by(LabSample.created_at.desc())
        return list(session.execute(stmt).scalars())

    def next_lab_number(self, session: Session, seq_date: date, material_type_id: int) -> int:
        stmt = select(LabNumberSequence).where(
            LabNumberSequence.seq_date == seq_date,
            LabNumberSequence.material_type_id == material_type_id,
        )
        seq = session.execute(stmt).scalar_one_or_none()
        if seq is None:
            seq = LabNumberSequence(seq_date=seq_date, material_type_id=material_type_id, last_number=1)
            session.add(seq)
            session.flush()
            return cast(int, cast(Any, seq).last_number)
        seq_obj = cast(Any, seq)
        seq_obj.last_number = cast(int, seq_obj.last_number) + 1
        session.flush()
        return cast(int, seq_obj.last_number)

    def create_sample(
        self,
        session: Session,
        *,
        patient_id: int,
        emr_case_id: int | None,
        lab_no: str,
        material_type_id: int,
        material_location: str | None,
        medium: str | None,
        study_kind: str | None,
        ordered_at: datetime | None,
        taken_at: datetime | None,
        delivered_at: datetime | None,
        qc_due_at: datetime | None,
        qc_status: str | None,
        created_by: int | None,
    ) -> LabSample:
        sample = LabSample(
            patient_id=patient_id,
            emr_case_id=emr_case_id,
            lab_no=lab_no,
            material_type_id=material_type_id,
            material_location=material_location,
            medium=medium,
            study_kind=study_kind,
            ordered_at=ordered_at,
            taken_at=taken_at,
            delivered_at=delivered_at,
            qc_due_at=qc_due_at,
            qc_status=qc_status,
            created_by=created_by,
        )
        session.add(sample)
        session.flush()
        return sample

    def update_result(
        self,
        session: Session,
        sample_id: int,
        *,
        growth_result_at: datetime | None,
        growth_flag: int | None,
        colony_desc: str | None,
        microscopy: str | None,
        cfu: str | None,
        qc_status: str | None,
    ) -> None:
        values = {
            "growth_result_at": growth_result_at,
            "growth_flag": growth_flag,
            "colony_desc": colony_desc,
            "microscopy": microscopy,
            "cfu": cfu,
        }
        if qc_status is not None:
            values["qc_status"] = qc_status
        stmt = (
            update(LabSample)
            .where(LabSample.id == sample_id)
            .values(**values)
        )
        session.execute(stmt)

    def update_sample(
        self,
        session: Session,
        sample_id: int,
        *,
        material_type_id: int | None,
        material_location: str | None,
        medium: str | None,
        study_kind: str | None,
        ordered_at: datetime | None,
        taken_at: datetime | None,
        delivered_at: datetime | None,
        qc_due_at: datetime | None = None,
    ) -> None:
        values = {
            "material_type_id": material_type_id,
            "material_location": material_location,
            "medium": medium,
            "study_kind": study_kind,
            "ordered_at": ordered_at,
            "taken_at": taken_at,
            "delivered_at": delivered_at,
        }
        if qc_due_at is not None:
            values["qc_due_at"] = qc_due_at
        stmt = (
            update(LabSample)
            .where(LabSample.id == sample_id)
            .values(**values)
        )
        session.execute(stmt)

    def replace_isolation(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(LabMicrobeIsolation).filter(LabMicrobeIsolation.lab_sample_id == sample_id).delete()
        session.add_all([LabMicrobeIsolation(lab_sample_id=sample_id, **item) for item in items])

    def replace_susceptibility(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(LabAbxSusceptibility).filter(LabAbxSusceptibility.lab_sample_id == sample_id).delete()
        session.add_all([LabAbxSusceptibility(lab_sample_id=sample_id, **item) for item in items])

    def replace_phages(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(LabPhagePanelResult).filter(LabPhagePanelResult.lab_sample_id == sample_id).delete()
        session.add_all([LabPhagePanelResult(lab_sample_id=sample_id, **item) for item in items])

    def get_isolation(self, session: Session, sample_id: int) -> list[LabMicrobeIsolation]:
        return list(
            session.query(LabMicrobeIsolation)
            .filter(LabMicrobeIsolation.lab_sample_id == sample_id)
            .all()
        )

    def get_susceptibility(self, session: Session, sample_id: int) -> list[LabAbxSusceptibility]:
        return list(
            session.query(LabAbxSusceptibility)
            .filter(LabAbxSusceptibility.lab_sample_id == sample_id)
            .all()
        )

    def get_phages(self, session: Session, sample_id: int) -> list[LabPhagePanelResult]:
        return list(
            session.query(LabPhagePanelResult)
            .filter(LabPhagePanelResult.lab_sample_id == sample_id)
            .all()
        )
