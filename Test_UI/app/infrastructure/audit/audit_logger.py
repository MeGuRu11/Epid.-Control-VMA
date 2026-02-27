
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db.models_sqlalchemy import AuditLog

def utcnow():
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class AuditEvent:
    user_id: int | None
    username: str | None
    entity_type: str
    entity_id: str
    action: str
    payload: dict

class AuditLogger:
    def __init__(self, engine):
        self._engine = engine

    def log(self, e: AuditEvent) -> None:
        with Session(self._engine) as s:
            s.add(AuditLog(
                event_ts=utcnow(),
                user_id=e.user_id,
                username=e.username,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                action=e.action,
                payload_json=json.dumps(e.payload, ensure_ascii=False),
            ))
            s.commit()

    def latest(self, limit: int = 200) -> list[dict]:
        with Session(self._engine) as s:
            rows = s.execute(select(AuditLog).order_by(AuditLog.event_ts.desc()).limit(limit)).scalars().all()
            return [r.to_dict() for r in rows]
