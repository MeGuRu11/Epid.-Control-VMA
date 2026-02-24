from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy import select

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.session import session_scope


class SavedFilterService:
    def __init__(self, session_factory: Callable = session_scope) -> None:
        self.session_factory = session_factory

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
        payload: dict,
        created_by: int | None,
    ) -> models.SavedFilter:
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
                created_by=created_by,
            )
            session.add(item)
            session.flush()
            return item
