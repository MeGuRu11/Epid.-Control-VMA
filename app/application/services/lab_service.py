from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import cast

from app.application.dto.lab_dto import (
    LabSampleCreateRequest,
    LabSampleResponse,
    LabSampleResultUpdate,
    LabSampleUpdateRequest,
)
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.lab_repo import LabRepository
from app.infrastructure.db.repositories.reference_repo import ReferenceRepository
from app.infrastructure.db.session import session_scope


def _format_lab_no(material_code: str, seq_date: date, seq: int) -> str:
    return f"{material_code}-{seq_date.strftime('%Y%m%d')}-{seq:04d}"


def _is_blood_material(material_code: str | None, material_name: str | None) -> bool:
    code = (material_code or "").casefold()
    name = (material_name or "").casefold()
    return "blood" in code or "кров" in name or "кров" in code


def _compute_qc_due_at(taken_at: datetime | None, material_code: str | None, material_name: str | None) -> datetime:
    base_dt = taken_at or datetime.now(UTC)
    hours = 2 if _is_blood_material(material_code, material_name) else 6
    return base_dt + timedelta(hours=hours)


class LabService:
    def __init__(
        self,
        lab_repo: LabRepository | None = None,
        ref_repo: ReferenceRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.lab_repo = lab_repo or LabRepository()
        self.ref_repo = ref_repo or ReferenceRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def create_sample(self, request: LabSampleCreateRequest) -> LabSampleResponse:
        taken_at = request.taken_at or datetime.now(UTC)
        seq_date = taken_at.date()
        with self.session_factory() as session:
            material = self.ref_repo.get_material_type(session, request.material_type_id)
            if not material:
                raise ValueError("Тип материала не найден")
            seq = self.lab_repo.next_lab_number(session, seq_date, request.material_type_id)
            material_code = cast(str, material.code)
            lab_no = _format_lab_no(material_code, seq_date, seq)
            qc_due_at = _compute_qc_due_at(
                request.taken_at,
                cast(str | None, material.code),
                cast(str | None, material.name),
            )

            sample = self.lab_repo.create_sample(
                session,
                patient_id=request.patient_id,
                emr_case_id=request.emr_case_id,
                lab_no=lab_no,
                material_type_id=request.material_type_id,
                material_location=request.material_location,
                medium=request.medium,
                study_kind=request.study_kind,
                ordered_at=request.ordered_at,
                taken_at=request.taken_at,
                delivered_at=request.delivered_at,
                qc_due_at=qc_due_at,
                qc_status="valid",
                created_by=request.created_by,
            )

            self.audit_repo.add_event(
                session,
                user_id=request.created_by,
                entity_type="lab_sample",
                entity_id=str(sample.id),
                action="create_lab_sample",
                payload_json=json.dumps({"lab_no": lab_no}),
            )

            sample_id = cast(int, sample.id)
            lab_no_value = cast(str, sample.lab_no)
            material_type_id = cast(int, sample.material_type_id)
            material_location = cast(str | None, sample.material_location)
            medium = cast(str | None, sample.medium)
            taken_at_value = cast(datetime | None, sample.taken_at)
            growth_flag = cast(int | None, sample.growth_flag)
            qc_due_at_value = cast(datetime | None, sample.qc_due_at)
            qc_status = cast(str | None, sample.qc_status)
            return LabSampleResponse(
                id=sample_id,
                lab_no=lab_no_value,
                material_type_id=material_type_id,
                material_location=material_location,
                medium=medium,
                taken_at=taken_at_value,
                growth_flag=growth_flag,
                qc_due_at=qc_due_at_value,
                qc_status=qc_status,
            )

    def update_result(self, sample_id: int, request: LabSampleResultUpdate, actor_id: int | None) -> LabSampleResponse:
        with self.session_factory() as session:
            sample = self.lab_repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")

            self.lab_repo.update_result(
                session,
                sample_id=sample_id,
                growth_result_at=request.growth_result_at,
                growth_flag=request.growth_flag,
                colony_desc=request.colony_desc,
                microscopy=request.microscopy,
                cfu=request.cfu,
                qc_status=request.qc_status,
            )

            iso_payload = []
            if request.microorganism_id or request.microorganism_free:
                iso_payload.append(
                    {
                        "microorganism_id": request.microorganism_id,
                        "microorganism_free": request.microorganism_free,
                        "notes": None,
                    }
                )
            self.lab_repo.replace_isolation(session, sample_id, iso_payload)
            self.lab_repo.replace_susceptibility(session, sample_id, request.susceptibility)
            self.lab_repo.replace_phages(session, sample_id, request.phages)

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="lab_sample",
                entity_id=str(sample_id),
                action="update_lab_result",
                payload_json=json.dumps({"growth_flag": request.growth_flag}),
            )

            # Refresh sample data
            session.refresh(sample)
            isolation = self.lab_repo.get_isolation(session, sample_id)
            micro = isolation[0] if isolation else None
            sample_id_value = cast(int, sample.id)
            lab_no_value = cast(str, sample.lab_no)
            material_type_id = cast(int, sample.material_type_id)
            material_location = cast(str | None, sample.material_location)
            medium = cast(str | None, sample.medium)
            taken_at = cast(datetime | None, sample.taken_at)
            growth_flag = cast(int | None, sample.growth_flag)
            qc_due_at_value = cast(datetime | None, sample.qc_due_at)
            qc_status = cast(str | None, sample.qc_status)
            microorganism_id = cast(int | None, micro.microorganism_id) if micro else None
            microorganism_free = cast(str | None, micro.microorganism_free) if micro else None
            return LabSampleResponse(
                id=sample_id_value,
                lab_no=lab_no_value,
                material_type_id=material_type_id,
                material_location=material_location,
                medium=medium,
                taken_at=taken_at,
                growth_flag=growth_flag,
                qc_due_at=qc_due_at_value,
                qc_status=qc_status,
                microorganism_id=microorganism_id,
                microorganism_free=microorganism_free,
            )

    def update_sample(self, sample_id: int, request: LabSampleUpdateRequest, actor_id: int | None) -> None:
        with self.session_factory() as session:
            sample = self.lab_repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")

            material_id = request.material_type_id or cast(int, sample.material_type_id)
            material = self.ref_repo.get_material_type(session, material_id)
            base_taken_at = request.taken_at if request.taken_at is not None else cast(datetime | None, sample.taken_at)
            qc_due_at = _compute_qc_due_at(
                base_taken_at,
                cast(str | None, material.code) if material else None,
                cast(str | None, material.name) if material else None,
            )

            self.lab_repo.update_sample(
                session,
                sample_id=sample_id,
                material_type_id=request.material_type_id,
                material_location=request.material_location,
                medium=request.medium,
                study_kind=request.study_kind,
                ordered_at=request.ordered_at,
                taken_at=request.taken_at,
                delivered_at=request.delivered_at,
                qc_due_at=qc_due_at,
            )

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="lab_sample",
                entity_id=str(sample_id),
                action="update_lab_sample",
                payload_json=json.dumps({"material_type_id": request.material_type_id}),
            )

    def list_samples(self, patient_id: int, emr_case_id: int | None = None) -> list[LabSampleResponse]:
        with self.session_factory() as session:
            samples = self.lab_repo.list_by_patient(session, patient_id, emr_case_id=emr_case_id)
            responses = []
            for s in samples:
                sample_id = cast(int, s.id)
                isolation = self.lab_repo.get_isolation(session, sample_id)
                micro = isolation[0] if isolation else None
                lab_no_value = cast(str, s.lab_no)
                material_type_id = cast(int, s.material_type_id)
                material_location = cast(str | None, s.material_location)
                medium = cast(str | None, s.medium)
                taken_at = cast(datetime | None, s.taken_at)
                growth_flag = cast(int | None, s.growth_flag)
                qc_due_at_value = cast(datetime | None, s.qc_due_at)
                qc_status = cast(str | None, s.qc_status)
                microorganism_id = cast(int | None, micro.microorganism_id) if micro else None
                microorganism_free = cast(str | None, micro.microorganism_free) if micro else None
                responses.append(
                    LabSampleResponse(
                        id=sample_id,
                        lab_no=lab_no_value,
                        material_type_id=material_type_id,
                        material_location=material_location,
                        medium=medium,
                        taken_at=taken_at,
                        growth_flag=growth_flag,
                        qc_due_at=qc_due_at_value,
                        qc_status=qc_status,
                        microorganism_id=microorganism_id,
                        microorganism_free=microorganism_free,
                    )
                )
            return responses

    def get_detail(self, sample_id: int) -> dict:
        with self.session_factory() as session:
            sample = self.lab_repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")
            isolation = self.lab_repo.get_isolation(session, sample_id)
            susceptibility = self.lab_repo.get_susceptibility(session, sample_id)
            phages = self.lab_repo.get_phages(session, sample_id)
            return {
                "sample": sample,
                "isolation": isolation,
                "susceptibility": susceptibility,
                "phages": phages,
            }
