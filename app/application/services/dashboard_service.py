from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.session import session_scope


class DashboardService:
    def __init__(self, session_factory: Callable = session_scope) -> None:
        self.session_factory = session_factory

    def get_counts(self) -> dict[str, int]:
        with self.session_factory() as session:
            return {
                "patients": session.execute(select(func.count(models.Patient.id))).scalar() or 0,
                "emr_cases": session.execute(select(func.count(models.EmrCase.id))).scalar() or 0,
                "lab_samples": session.execute(select(func.count(models.LabSample.id))).scalar() or 0,
                "sanitary_samples": session.execute(select(func.count(models.SanitarySample.id))).scalar() or 0,
                "users": session.execute(select(func.count(models.User.id))).scalar() or 0,
            }

    def list_recent_audit(self, limit: int = 10) -> list[dict]:
        with self.session_factory() as session:
            stmt = (
                select(
                    models.AuditLog.event_ts,
                    models.AuditLog.action,
                    models.AuditLog.entity_type,
                    models.AuditLog.entity_id,
                    models.User.login,
                )
                .select_from(models.AuditLog)
                .outerjoin(models.User, models.User.id == models.AuditLog.user_id)
                .order_by(models.AuditLog.event_ts.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            return [
                {
                    "event_ts": r.event_ts,
                    "action": r.action,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "login": r.login or "",
                }
                for r in rows
            ]

    def get_last_login(self, user_id: int) -> object | None:
        with self.session_factory() as session:
            stmt = (
                select(models.AuditLog.event_ts)
                .where(
                    models.AuditLog.user_id == user_id,
                    models.AuditLog.action == "login",
                )
                .order_by(models.AuditLog.event_ts.desc())
                .limit(1)
            )
            return session.execute(stmt).scalar_one_or_none()

    def get_new_patients_count(self, days: int) -> int:
        since = datetime.now(UTC) - timedelta(days=days - 1)
        with self.session_factory() as session:
            stmt = select(func.count(models.Patient.id)).where(models.Patient.created_at >= since)
            return session.execute(stmt).scalar() or 0

    def get_top_department_by_samples(self, days: int) -> tuple[str, int] | None:
        since = datetime.now(UTC) - timedelta(days=days - 1)
        with self.session_factory() as session:
            stmt = (
                select(models.Department.name, func.count(models.SanitarySample.id).label("cnt"))
                .select_from(models.SanitarySample)
                .join(models.Department, models.Department.id == models.SanitarySample.department_id)
                .where(
                    models.SanitarySample.taken_at.is_not(None),
                    models.SanitarySample.taken_at >= since,
                )
                .group_by(models.Department.name)
                .order_by(func.count(models.SanitarySample.id).desc())
                .limit(1)
            )
            row = session.execute(stmt).first()
            if not row:
                return None
            return row[0], int(row[1] or 0)
