from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import (
    LabAbxSusceptibility,
    LabMicrobeIsolation,
    LabNumberSequence,
    LabPhagePanelResult,
    LabSample,
    RefMaterialType,
)
from .base import RepoBase


class LabRepo(RepoBase):
    def list_samples(self, patient_id: int | None = None, emr_case_id: int | None = None) -> list[LabSample]:
        with self.tx() as s:
            q = select(LabSample)
            if patient_id is not None:
                q = q.where(LabSample.patient_id == patient_id)
            if emr_case_id is not None:
                q = q.where(LabSample.emr_case_id == emr_case_id)
            q = q.order_by(LabSample.created_at.desc())
            return list(s.execute(q).scalars().all())

    def create_sample(self, payload: dict, created_by: int | None) -> int:
        with self.tx() as s:
            row = LabSample(
                patient_id=payload["patient_id"],
                emr_case_id=payload.get("emr_case_id"),
                lab_no=payload["lab_no"],
                material=payload.get("material") or "Кровь",
                organism=payload.get("organism"),
                growth_flag=payload.get("growth_flag"),
                mic=payload.get("mic"),
                cfu=payload.get("cfu"),
                material_type_id=payload.get("material_type_id"),
                material_location=payload.get("material_location"),
                medium=payload.get("medium"),
                study_kind=payload.get("study_kind"),
                ordered_at=payload.get("ordered_at"),
                taken_at=payload.get("taken_at"),
                delivered_at=payload.get("delivered_at"),
                growth_result_at=payload.get("growth_result_at"),
                created_by=created_by,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def generate_lab_no(self, material_type_id: int | None, when: date | None = None) -> str:
        seq_date = when or date.today()
        material_type_id = material_type_id or 1
        with self.tx() as s:
            row = s.execute(
                select(LabNumberSequence).where(
                    LabNumberSequence.seq_date == seq_date,
                    LabNumberSequence.material_type_id == material_type_id,
                )
            ).scalar_one_or_none()
            if row is None:
                row = LabNumberSequence(seq_date=seq_date, material_type_id=material_type_id, last_number=0)
                s.add(row)
                s.flush()
            row.last_number = int(row.last_number) + 1

            mat = s.get(RefMaterialType, material_type_id)
            code = (mat.code if mat and mat.code else "LAB").upper()
            return f"{code}-{seq_date.strftime('%Y%m%d')}-{row.last_number:04d}"

    def get_sample(self, sample_id: int) -> LabSample | None:
        with self.tx() as s:
            return s.get(LabSample, sample_id)

    def update_sample_result(self, sample_id: int, payload: dict) -> None:
        with self.tx() as s:
            row = s.get(LabSample, sample_id)
            if row is None:
                return
            for field in ("growth_flag", "colony_desc", "microscopy", "cfu", "organism"):
                if field in payload:
                    setattr(row, field, payload[field])

    def get_panels(self, sample_id: int) -> dict:
        with self.tx() as s:
            isolates = list(
                s.execute(
                    select(LabMicrobeIsolation).where(LabMicrobeIsolation.lab_sample_id == sample_id)
                ).scalars().all()
            )
            abx = list(
                s.execute(
                    select(LabAbxSusceptibility).where(LabAbxSusceptibility.lab_sample_id == sample_id)
                ).scalars().all()
            )
            phages = list(
                s.execute(
                    select(LabPhagePanelResult).where(LabPhagePanelResult.lab_sample_id == sample_id)
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
            s.query(LabMicrobeIsolation).filter(LabMicrobeIsolation.lab_sample_id == sample_id).delete()
            s.query(LabAbxSusceptibility).filter(LabAbxSusceptibility.lab_sample_id == sample_id).delete()
            s.query(LabPhagePanelResult).filter(LabPhagePanelResult.lab_sample_id == sample_id).delete()

            for it in isolates:
                s.add(
                    LabMicrobeIsolation(
                        lab_sample_id=sample_id,
                        microorganism_id=it.get("microorganism_id"),
                        microorganism_free=it.get("microorganism_free"),
                        notes=it.get("notes"),
                    )
                )
            for it in abx:
                s.add(
                    LabAbxSusceptibility(
                        lab_sample_id=sample_id,
                        antibiotic_id=it.get("antibiotic_id"),
                        group_id=it.get("group_id"),
                        ris=it.get("ris"),
                        mic_mg_l=it.get("mic_mg_l"),
                        method=it.get("method"),
                    )
                )
            for it in phages:
                s.add(
                    LabPhagePanelResult(
                        lab_sample_id=sample_id,
                        phage_id=it.get("phage_id"),
                        phage_free=it.get("phage_free"),
                        lysis_diameter_mm=it.get("lysis_diameter_mm"),
                    )
                )

