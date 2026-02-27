from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import AuditLog
from .base import RepoBase


class AuditRepo(RepoBase):
    def latest(self, limit: int = 200) -> list[AuditLog]:
        with self.tx() as s:
            return list(s.execute(select(AuditLog).order_by(AuditLog.event_ts.desc()).limit(limit)).scalars())
