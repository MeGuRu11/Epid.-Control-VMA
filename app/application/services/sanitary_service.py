from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from app.application.dto.sanitary_dto import (
    SanitarySampleCreateRequest,
    SanitarySampleResponse,
    SanitarySampleResultUpdate,
    SanitarySampleUpdateRequest,
)
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.sanitary_repo import SanitaryRepository
from app.infrastructure.db.session import session_scope


def _format_sanitary_lab_no(seq_date: datetime, seq: int) -> str:
    return f"SAN-{seq_date.strftime('%Y%m%d')}-{seq:04d}"


class SanitaryService:
    def __init__(
        self,
        repo: SanitaryRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.repo = repo or SanitaryRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def create_sample(self, request: SanitarySampleCreateRequest) -> SanitarySampleResponse:
        seq_date = request.taken_at or datetime.now(UTC)
        with self.session_factory() as session:
            seq = self.repo.next_lab_number(session, seq_date)
            lab_no = _format_sanitary_lab_no(seq_date, seq)
            sample = self.repo.create_sample(
                session,
                lab_no=lab_no,
                department_id=request.department_id,
                sampling_point=request.sampling_point,
                room=request.room,
                medium=request.medium,
                taken_at=request.taken_at,
                delivered_at=request.delivered_at,
                created_by=request.created_by,
            )

            self.audit_repo.add_event(
                session,
                user_id=request.created_by,
                entity_type="sanitary_sample",
                entity_id=str(cast(int, sample.id)),
                action="create_sanitary_sample",
                payload_json=json.dumps({"lab_no": lab_no}),
            )

            sample_id = cast(int, sample.id)
            lab_no_value = cast(str, sample.lab_no)
            department_id = cast(int, sample.department_id)
            sampling_point = cast(str | None, sample.sampling_point)
            room = cast(str | None, sample.room)
            medium = cast(str | None, sample.medium)
            taken_at = cast(datetime | None, sample.taken_at)
            growth_flag = cast(int | None, sample.growth_flag)
            return SanitarySampleResponse(
                id=sample_id,
                lab_no=lab_no_value,
                department_id=department_id,
                sampling_point=sampling_point,
                room=room,
                medium=medium,
                taken_at=taken_at,
                growth_flag=growth_flag,
            )

    def update_result(
        self, sample_id: int, request: SanitarySampleResultUpdate, actor_id: int | None
    ) -> SanitarySampleResponse:
        with self.session_factory() as session:
            sample = self.repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")

            self.repo.update_result(
                session,
                sample_id=sample_id,
                growth_result_at=request.growth_result_at,
                growth_flag=request.growth_flag,
                colony_desc=request.colony_desc,
                microscopy=request.microscopy,
                cfu=request.cfu,
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
            self.repo.replace_isolation(session, sample_id, iso_payload)
            self.repo.replace_susceptibility(session, sample_id, request.susceptibility)
            self.repo.replace_phages(session, sample_id, request.phages)

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="sanitary_sample",
                entity_id=str(sample_id),
                action="update_sanitary_result",
                payload_json=json.dumps({"growth_flag": request.growth_flag}),
            )

            session.refresh(sample)
            isolation = self.repo.get_isolation(session, sample_id)
            micro = isolation[0] if isolation else None
            sample_id_value = cast(int, sample.id)
            lab_no_value = cast(str, sample.lab_no)
            department_id = cast(int, sample.department_id)
            sampling_point = cast(str | None, sample.sampling_point)
            room = cast(str | None, sample.room)
            medium = cast(str | None, sample.medium)
            taken_at = cast(datetime | None, sample.taken_at)
            growth_flag = cast(int | None, sample.growth_flag)
            microorganism_id = cast(int | None, micro.microorganism_id) if micro else None
            microorganism_free = cast(str | None, micro.microorganism_free) if micro else None
            return SanitarySampleResponse(
                id=sample_id_value,
                lab_no=lab_no_value,
                department_id=department_id,
                sampling_point=sampling_point,
                room=room,
                medium=medium,
                taken_at=taken_at,
                growth_flag=growth_flag,
                microorganism_id=microorganism_id,
                microorganism_free=microorganism_free,
            )

    def update_sample(self, sample_id: int, request: SanitarySampleUpdateRequest, actor_id: int | None) -> None:
        with self.session_factory() as session:
            sample = self.repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")

            self.repo.update_sample(
                session,
                sample_id=sample_id,
                sampling_point=request.sampling_point,
                room=request.room,
                medium=request.medium,
                taken_at=request.taken_at,
                delivered_at=request.delivered_at,
            )

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="sanitary_sample",
                entity_id=str(sample_id),
                action="update_sanitary_sample",
                payload_json=json.dumps(
                    {
                        "sampling_point": request.sampling_point,
                        "room": request.room,
                        "medium": request.medium,
                    }
                ),
            )

    def list_samples_by_department(self, department_id: int) -> list[SanitarySampleResponse]:
        with self.session_factory() as session:
            samples = self.repo.list_by_department(session, department_id)
            responses = []
            for s in samples:
                sample_id = cast(int, s.id)
                isolation = self.repo.get_isolation(session, sample_id)
                micro = isolation[0] if isolation else None
                lab_no_value = cast(str, s.lab_no)
                department_id = cast(int, s.department_id)
                sampling_point = cast(str | None, s.sampling_point)
                room = cast(str | None, s.room)
                medium = cast(str | None, s.medium)
                taken_at = cast(datetime | None, s.taken_at)
                growth_flag = cast(int | None, s.growth_flag)
                microorganism_id = cast(int | None, micro.microorganism_id) if micro else None
                microorganism_free = cast(str | None, micro.microorganism_free) if micro else None
                responses.append(
                    SanitarySampleResponse(
                        id=sample_id,
                        lab_no=lab_no_value,
                        department_id=department_id,
                        sampling_point=sampling_point,
                        room=room,
                        medium=medium,
                        taken_at=taken_at,
                        growth_flag=growth_flag,
                        microorganism_id=microorganism_id,
                        microorganism_free=microorganism_free,
                    )
                )
            return responses

    def get_detail(self, sample_id: int) -> dict:
        with self.session_factory() as session:
            sample = self.repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")
            isolation = self.repo.get_isolation(session, sample_id)
            susceptibility = self.repo.get_susceptibility(session, sample_id)
            phages = self.repo.get_phages(session, sample_id)
            return {
                "sample": sample,
                "isolation": isolation,
                "susceptibility": susceptibility,
                "phages": phages,
            }
