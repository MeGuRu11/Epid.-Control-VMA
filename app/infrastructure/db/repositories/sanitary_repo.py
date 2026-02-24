from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import (
    SanAbxSusceptibility,
    SanitaryNumberSequence,
    SanitarySample,
    SanMicrobeIsolation,
    SanPhagePanelResult,
)


class SanitaryRepository:
    def get_sample(self, session: Session, sample_id: int) -> SanitarySample | None:
        stmt = select(SanitarySample).where(SanitarySample.id == sample_id)
        return session.execute(stmt).scalar_one_or_none()

    def next_lab_number(self, session: Session, seq_date: datetime) -> int:
        seq_day = seq_date.date()
        stmt = select(SanitaryNumberSequence).where(SanitaryNumberSequence.seq_date == seq_day)
        seq = session.execute(stmt).scalar_one_or_none()
        if seq is None:
            seq = SanitaryNumberSequence(seq_date=seq_day, last_number=1)
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
        lab_no: str,
        department_id: int,
        sampling_point: str,
        room: str | None,
        medium: str | None,
        taken_at: datetime | None,
        delivered_at: datetime | None,
        created_by: int | None,
    ) -> SanitarySample:
        sample = SanitarySample(
            lab_no=lab_no,
            department_id=department_id,
            sampling_point=sampling_point,
            room=room,
            medium=medium,
            taken_at=taken_at,
            delivered_at=delivered_at,
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
    ) -> None:
        stmt = (
            update(SanitarySample)
            .where(SanitarySample.id == sample_id)
            .values(
                growth_result_at=growth_result_at,
                growth_flag=growth_flag,
                colony_desc=colony_desc,
                microscopy=microscopy,
                cfu=cfu,
            )
        )
        session.execute(stmt)

    def update_sample(
        self,
        session: Session,
        sample_id: int,
        *,
        sampling_point: str | None,
        room: str | None,
        medium: str | None,
        taken_at: datetime | None,
        delivered_at: datetime | None,
    ) -> None:
        stmt = (
            update(SanitarySample)
            .where(SanitarySample.id == sample_id)
            .values(
                sampling_point=sampling_point,
                room=room,
                medium=medium,
                taken_at=taken_at,
                delivered_at=delivered_at,
            )
        )
        session.execute(stmt)

    def replace_isolation(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(SanMicrobeIsolation).filter(SanMicrobeIsolation.sanitary_sample_id == sample_id).delete()
        session.add_all([SanMicrobeIsolation(sanitary_sample_id=sample_id, **item) for item in items])

    def replace_susceptibility(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(SanAbxSusceptibility).filter(SanAbxSusceptibility.sanitary_sample_id == sample_id).delete()
        session.add_all([SanAbxSusceptibility(sanitary_sample_id=sample_id, **item) for item in items])

    def replace_phages(self, session: Session, sample_id: int, items: Iterable[dict]) -> None:
        session.query(SanPhagePanelResult).filter(SanPhagePanelResult.sanitary_sample_id == sample_id).delete()
        session.add_all([SanPhagePanelResult(sanitary_sample_id=sample_id, **item) for item in items])

    def list_by_department(self, session: Session, department_id: int) -> list[SanitarySample]:
        stmt = select(SanitarySample).where(SanitarySample.department_id == department_id)
        stmt = stmt.order_by(SanitarySample.created_at.desc())
        return list(session.execute(stmt).scalars())

    def get_isolation(self, session: Session, sample_id: int) -> list[SanMicrobeIsolation]:
        return list(
            session.query(SanMicrobeIsolation)
            .filter(SanMicrobeIsolation.sanitary_sample_id == sample_id)
            .all()
        )

    def get_susceptibility(self, session: Session, sample_id: int) -> list[SanAbxSusceptibility]:
        return list(
            session.query(SanAbxSusceptibility)
            .filter(SanAbxSusceptibility.sanitary_sample_id == sample_id)
            .all()
        )

    def get_phages(self, session: Session, sample_id: int) -> list[SanPhagePanelResult]:
        return list(
            session.query(SanPhagePanelResult)
            .filter(SanPhagePanelResult.sanitary_sample_id == sample_id)
            .all()
        )
