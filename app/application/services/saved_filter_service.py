from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy import select

from app.application.exceptions import PermissionError as AppPermissionError
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.session import session_scope


class SavedFilterService:
    def __init__(
        self,
        session_factory: Callable = session_scope,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_repo = audit_repo or AuditLogRepository()

    def list_filters(self, filter_type: str) -> list[models.SavedFilter]:
        with self.session_factory() as session:
            stmt = (
                select(models.SavedFilter)
                .where(models.SavedFilter.filter_type == filter_type)
                .order_by(models.SavedFilter.created_at.desc())
            )
            return list(session.execute(stmt).scalars())

    def save_filter(
        self,
        filter_type: str,
        name: str,
        payload: dict[str, object],
        actor_id: int,
    ) -> models.SavedFilter:
        if actor_id is None:
            raise AppPermissionError("actor_id обязателен для операций записи")
        name = name.strip()
        if not name:
            raise ValueError("Название фильтра обязательно")
        if not payload:
            raise ValueError("Фильтр пустой")

        with self.session_factory() as session:
            exists_stmt = select(models.SavedFilter).where(
                models.SavedFilter.filter_type == filter_type,
                models.SavedFilter.name == name,
            )
            if session.execute(exists_stmt).scalar_one_or_none() is not None:
                raise ValueError("Фильтр с таким названием уже существует")

            item = models.SavedFilter(
                filter_type=filter_type,
                name=name,
                payload_json=json.dumps(payload, ensure_ascii=False),
                created_by=actor_id,
            )
            session.add(item)
            session.flush()
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="saved_filter",
                entity_id=str(item.id),
                action="saved_filter_create",
                payload_json=json.dumps(
                    {
                        "filter_type": filter_type,
                        "name": name,
                    },
                    ensure_ascii=False,
                ),
            )
            return item

    def delete_filter(self, filter_id: int, actor_id: int) -> None:
        if actor_id is None:
            raise AppPermissionError("actor_id обязателен для операций записи")

        with self.session_factory() as session:
            item = session.get(models.SavedFilter, filter_id)
            if item is None:
                raise ValueError("Фильтр не найден")
            filter_type = str(item.filter_type)
            name = str(item.name)
            session.delete(item)
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="saved_filter",
                entity_id=str(filter_id),
                action="saved_filter_delete",
                payload_json=json.dumps(
                    {
                        "filter_type": filter_type,
                        "name": name,
                    },
                    ensure_ascii=False,
                ),
            )
