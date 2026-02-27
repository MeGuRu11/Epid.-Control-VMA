from __future__ import annotations

from datetime import date

from ...application.dto.lab_dto import LabSampleCreateIn
from ...domain.rules import normalize_required_text
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.lab_repo import LabRepo
from ...infrastructure.db.repositories.reference_repo import ReferenceRepo


class LabService:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._repo = LabRepo(engine)
        self._refs = ReferenceRepo(engine)
        self._audit = AuditLogger(engine)
        self._refs.seed_min_references()

    def list(self, patient_id: int | None = None, emr_case_id: int | None = None):
        return self._repo.list_samples(patient_id=patient_id, emr_case_id=emr_case_id)

    def generate_lab_no(self, material_type_id: int | None = None, when: date | None = None) -> str:
        return self._repo.generate_lab_no(material_type_id=material_type_id, when=when)

    def create(
        self,
        patient_id: int,
        lab_no: str,
        material: str,
        organism: str,
        growth_flag: int | None,
        mic: str,
        cfu: str,
        emr_case_id: int | None = None,
    ) -> int:
        dto = LabSampleCreateIn(
            patient_id=patient_id,
            lab_no=lab_no.strip(),
            material=normalize_required_text(material, default="Кровь"),
            organism=organism or None,
            growth_flag=growth_flag,
            mic=mic or None,
            cfu=cfu or None,
            emr_case_id=emr_case_id,
        )
        sample_id = self._repo.create_sample(
            payload={
                "patient_id": dto.patient_id,
                "emr_case_id": dto.emr_case_id,
                "lab_no": dto.lab_no,
                "material": dto.material,
                "organism": dto.organism,
                "growth_flag": dto.growth_flag,
                "mic": dto.mic,
                "cfu": dto.cfu,
            },
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "lab_sample",
                str(sample_id),
                "create",
                {"patient_id": dto.patient_id, "lab_no": dto.lab_no},
            )
        )
        return sample_id

    def create_auto(
        self,
        patient_id: int,
        emr_case_id: int | None = None,
        material_type_id: int | None = None,
        material: str = "Кровь",
        organism: str | None = None,
    ) -> int:
        lab_no = self.generate_lab_no(material_type_id=material_type_id)
        return self.create(
            patient_id=patient_id,
            emr_case_id=emr_case_id,
            lab_no=lab_no,
            material=material,
            organism=organism or "",
            growth_flag=1 if organism else 0,
            mic="",
            cfu="",
        )

    def get_sample(self, sample_id: int):
        return self._repo.get_sample(sample_id)

    def get_panels(self, sample_id: int) -> dict:
        return self._repo.get_panels(sample_id)

    def update_result(self, sample_id: int, payload: dict) -> None:
        self._repo.update_sample_result(sample_id, payload)
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "lab_sample",
                str(sample_id),
                "update_result",
                payload,
            )
        )

    def save_panels(
        self,
        sample_id: int,
        isolates: list[dict] | None = None,
        abx: list[dict] | None = None,
        phages: list[dict] | None = None,
    ) -> None:
        self._repo.replace_panels(sample_id, isolates=isolates, abx=abx, phages=phages)
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "lab_sample",
                str(sample_id),
                "save_panels",
                {
                    "isolates": len(isolates or []),
                    "abx": len(abx or []),
                    "phages": len(phages or []),
                },
            )
        )
