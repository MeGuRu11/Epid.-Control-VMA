from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from app.application.dto.sanitary_dto import (
    SanitarySampleCreateRequest,
    SanitarySampleResponse,
    SanitarySampleResultUpdate,
    SanitarySampleUpdateRequest,
)
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.sanitary_repo import SanitaryRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope


def _format_sanitary_lab_no(seq_date: datetime, seq: int) -> str:
    return f"SAN-{seq_date.strftime('%Y%m%d')}-{seq:04d}"


def _clean_optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _sanitary_response(sample: Any, micro: Any | None = None) -> SanitarySampleResponse:
    return SanitarySampleResponse(
        id=cast(int, sample.id),
        lab_no=cast(str, sample.lab_no),
        barcode=cast(str | None, sample.barcode),
        department_id=cast(int, sample.department_id),
        sampling_point=cast(str | None, sample.sampling_point),
        room=cast(str | None, sample.room),
        medium=cast(str | None, sample.medium),
        ordered_at=cast(datetime | None, sample.ordered_at),
        taken_at=cast(datetime | None, sample.taken_at),
        delivered_at=cast(datetime | None, sample.delivered_at),
        growth_flag=cast(int | None, sample.growth_flag),
        microorganism_id=cast(int | None, micro.microorganism_id) if micro else None,
        microorganism_free=cast(str | None, micro.microorganism_free) if micro else None,
    )


class SanitaryService:
    def __init__(
        self,
        repo: SanitaryRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        user_repo: UserRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.repo = repo or SanitaryRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.user_repo = user_repo or UserRepository()
        self.session_factory = session_factory

    def _require_write_access(self, session, actor_id: int) -> None:
        if actor_id is None:  # raise on missing actor_id
            raise ValueError("actor_id обязателен для операций записи")
        actor = self.user_repo.get_by_id(session, actor_id)
        if actor is None or not bool(getattr(actor, "is_active", False)):
            raise ValueError("Пользователь не найден или неактивен")

    def create_sample(self, request: SanitarySampleCreateRequest, *, actor_id: int) -> SanitarySampleResponse:
        seq_date = request.taken_at or datetime.now(UTC)
        manual_lab_no = _clean_optional_text(request.lab_no)
        with self.session_factory() as session:
            self._require_write_access(session, actor_id)
            if manual_lab_no is not None:
                if self.repo.get_sample_by_lab_no(session, manual_lab_no) is not None:
                    raise ValueError(f"Лаб. номер уже существует: {manual_lab_no}")
                lab_no = manual_lab_no
            else:
                seq = self.repo.next_lab_number(session, seq_date)
                lab_no = _format_sanitary_lab_no(seq_date, seq)
            sample = self.repo.create_sample(
                session,
                lab_no=lab_no,
                barcode=_clean_optional_text(request.barcode),
                department_id=request.department_id,
                sampling_point=request.sampling_point,
                room=request.room,
                medium=request.medium,
                ordered_at=request.ordered_at,
                taken_at=request.taken_at,
                delivered_at=request.delivered_at,
                created_by=actor_id,
            )

            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="sanitary_sample",
                entity_id=str(cast(int, sample.id)),
                action="create_sanitary_sample",
                payload_json=json.dumps({"lab_no": lab_no}),
            )

            return _sanitary_response(sample)

    def update_result(
        self, sample_id: int, request: SanitarySampleResultUpdate, actor_id: int
    ) -> SanitarySampleResponse:
        with self.session_factory() as session:
            self._require_write_access(session, actor_id)
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
            return _sanitary_response(sample, micro)

    def update_sample(self, sample_id: int, request: SanitarySampleUpdateRequest, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_write_access(session, actor_id)
            sample = self.repo.get_sample(session, sample_id)
            if not sample:
                raise ValueError("Проба не найдена")

            current_lab_no = cast(str, sample.lab_no)
            manual_lab_no = _clean_optional_text(request.lab_no)
            if (
                manual_lab_no is not None
                and manual_lab_no != current_lab_no
                and self.repo.get_sample_by_lab_no(session, manual_lab_no) is not None
            ):
                raise ValueError(f"Лаб. номер уже существует: {manual_lab_no}")
            self.repo.update_sample(
                session,
                sample_id=sample_id,
                department_id=request.department_id,
                lab_no=manual_lab_no if manual_lab_no != current_lab_no else None,
                barcode=_clean_optional_text(request.barcode),
                sampling_point=request.sampling_point,
                room=request.room,
                medium=request.medium,
                ordered_at=request.ordered_at,
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
                responses.append(_sanitary_response(s, micro))
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

