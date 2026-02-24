from __future__ import annotations

from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import AuditLog


class AuditLogRepository:
    def add_event(
        self,
        session: Session,
        *,
        user_id: int | None,
        entity_type: str,
        entity_id: str,
        action: str,
        payload_json: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            payload_json=payload_json,
        )
        session.add(entry)
        return entry
