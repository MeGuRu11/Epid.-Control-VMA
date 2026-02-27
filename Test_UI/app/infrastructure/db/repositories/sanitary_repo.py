from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import (
    SanAbxSusceptibility,
    SanMicrobeIsolation,
    SanPhagePanelResult,
    SanitarySample,
)
from .base import RepoBase


class SanitaryRepo(RepoBase):
    def get_sample(self, sample_id: int) -> SanitarySample | None:
        with self.tx() as s:
            return s.get(SanitarySample, sample_id)

    def list_samples(self, department_id: int | None = None) -> list[SanitarySample]:
        with self.tx() as s:
            stmt = select(SanitarySample).order_by(SanitarySample.created_at.desc())
            if department_id is not None:
                stmt = stmt.where(SanitarySample.department_id == department_id)
            return list(s.execute(stmt).scalars())

    def create_sample(
        self,
        lab_no: str,
        sampling_point: str,
        department_id: int | None,
        room: str | None,
        growth_flag: int | None,
        cfu: str | None,
        created_by: int | None,
    ) -> int:
        with self.tx() as s:
            row = SanitarySample(
                lab_no=lab_no,
                sampling_point=sampling_point,
                department_id=department_id,
                room=room,
                growth_flag=growth_flag,
                cfu=cfu,
                created_by=created_by,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def update_sample_result(self, sample_id: int, payload: dict) -> None:
        with self.tx() as s:
            row = s.get(SanitarySample, sample_id)
            if row is None:
                return
            for field in ("growth_flag", "colony_desc", "microscopy", "cfu"):
                if field in payload:
                    setattr(row, field, payload[field])

    def get_panels(self, sample_id: int) -> dict:
        with self.tx() as s:
            isolates = list(
                s.execute(
                    select(SanMicrobeIsolation).where(SanMicrobeIsolation.sanitary_sample_id == sample_id)
                ).scalars().all()
            )
            abx = list(
                s.execute(
                    select(SanAbxSusceptibility).where(SanAbxSusceptibility.sanitary_sample_id == sample_id)
                ).scalars().all()
            )
            phages = list(
                s.execute(
                    select(SanPhagePanelResult).where(SanPhagePanelResult.sanitary_sample_id == sample_id)
                ).scalars().all()
            )
            return {"isolates": isolates, "abx": abx, "phages": phages}

    def replace_panels(
        self,
        sample_id: int,
        isolates: list[dict] | None = None,
        abx: list[dict] | None = None,
        phages: list[dict] | None = None,
    ) -> None:
        isolates = isolates or []
        abx = abx or []
        phages = phages or []
        with self.tx() as s:
            s.query(SanMicrobeIsolation).filter(SanMicrobeIsolation.sanitary_sample_id == sample_id).delete()
            s.query(SanAbxSusceptibility).filter(SanAbxSusceptibility.sanitary_sample_id == sample_id).delete()
            s.query(SanPhagePanelResult).filter(SanPhagePanelResult.sanitary_sample_id == sample_id).delete()
            for it in isolates:
                s.add(SanMicrobeIsolation(sanitary_sample_id=sample_id, microorganism_id=it.get("microorganism_id"), microorganism_free=it.get("microorganism_free"), notes=it.get("notes")))
            for it in abx:
                s.add(SanAbxSusceptibility(sanitary_sample_id=sample_id, antibiotic_id=it.get("antibiotic_id"), group_id=it.get("group_id"), ris=it.get("ris"), mic_mg_l=it.get("mic_mg_l"), method=it.get("method")))
            for it in phages:
                s.add(SanPhagePanelResult(sanitary_sample_id=sample_id, phage_id=it.get("phage_id"), phage_free=it.get("phage_free"), lysis_diameter_mm=it.get("lysis_diameter_mm")))
