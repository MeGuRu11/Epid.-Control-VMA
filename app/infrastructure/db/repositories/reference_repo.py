from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from app.infrastructure.db import models_sqlalchemy as models


class ReferenceRepository:
    def list_all(self, session: Session, model: type) -> list:
        stmt: Any = select(model)
        return list(session.execute(stmt).scalars())

    def upsert_simple(self, session: Session, model: type, payloads: Iterable[dict], identity_field: str = "id") -> None:
        pk_cols: list[Any] = list(inspect(model).primary_key)
        pk_fields: set[str] = set()
        for col in pk_cols:
            pk_fields.add(col.key)
        for data in payloads:
            identity = data.get(identity_field)
            obj = None
            if identity is not None:
                for candidate in list(session.new) + list(session.identity_map.values()):
                    if isinstance(candidate, model) and getattr(candidate, identity_field, None) == identity:
                        obj = candidate
                        break
                if obj is None:
                    if identity_field in pk_fields:
                        obj = session.get(model, identity)
                    else:
                        stmt: Any = select(model).where(getattr(model, identity_field) == identity)
                        obj = session.execute(stmt).scalars().first()
            if obj:
                for k, v in data.items():
                    setattr(obj, k, v)
            else:
                session.add(model(**data))

    def search_microorganisms(
        self, session: Session, query: str, limit: int = 50
    ) -> list[models.RefMicroorganism]:
        clean = query.strip()
        if not clean:
            return []
        terms = [t for t in re.split(r"\s+", clean) if t]
        fts_query = " ".join(f"{t}*" for t in terms)
        if fts_query:
            try:
                ids = [
                    row[0]
                    for row in session.execute(
                        text(
                            """
                            SELECT microorganism_id
                            FROM ref_microorganisms_fts
                            WHERE ref_microorganisms_fts MATCH :q
                            ORDER BY bm25(ref_microorganisms_fts)
                            LIMIT :limit
                            """
                        ),
                        {"q": fts_query, "limit": limit},
                    )
                    if row[0] is not None
                ]
                if ids:
                    microbes = list(
                        session.execute(select(models.RefMicroorganism).where(models.RefMicroorganism.id.in_(ids))).scalars()
                    )
                    by_id = {m.id: m for m in microbes}
                    return [by_id[i] for i in ids if i in by_id]
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).debug("FTS search_microorganisms failed", exc_info=True)

        stmt = (
            select(models.RefMicroorganism)
            .where(
                or_(
                    models.RefMicroorganism.name.ilike(f"%{clean}%"),
                    models.RefMicroorganism.code.ilike(f"%{clean}%"),
                )
            )
            .order_by(models.RefMicroorganism.name)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def search_icd10(self, session: Session, query: str, limit: int = 50) -> list[models.RefICD10]:
        clean = query.strip()
        if not clean:
            return []
        terms = [t for t in re.split(r"\s+", clean) if t]
        fts_query = " ".join(f"{t}*" for t in terms)
        if fts_query:
            try:
                codes = [
                    row[0]
                    for row in session.execute(
                        text(
                            """
                            SELECT code
                            FROM ref_icd10_fts
                            WHERE ref_icd10_fts MATCH :q
                            ORDER BY bm25(ref_icd10_fts)
                            LIMIT :limit
                            """
                        ),
                        {"q": fts_query, "limit": limit},
                    )
                    if row[0]
                ]
                if codes:
                    items = list(
                        session.execute(select(models.RefICD10).where(models.RefICD10.code.in_(codes))).scalars()
                    )
                    by_code = {i.code: i for i in items}
                    return [by_code[c] for c in codes if c in by_code]
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).debug("FTS search_icd10 failed", exc_info=True)

        stmt = (
            select(models.RefICD10)
            .where(
                or_(
                    models.RefICD10.title.ilike(f"%{clean}%"),
                    models.RefICD10.code.ilike(f"%{clean}%"),
                )
            )
            .order_by(models.RefICD10.code)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def search_antibiotics(
        self, session: Session, query: str, limit: int = 50
    ) -> list[models.RefAntibiotic]:
        clean = query.strip()
        if not clean:
            return []
        stmt = (
            select(models.RefAntibiotic)
            .where(
                or_(
                    models.RefAntibiotic.name.ilike(f"%{clean}%"),
                    models.RefAntibiotic.code.ilike(f"%{clean}%"),
                )
            )
            .order_by(models.RefAntibiotic.name)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def search_material_types(
        self, session: Session, query: str, limit: int = 50
    ) -> list[models.RefMaterialType]:
        clean = query.strip()
        if not clean:
            return []
        stmt = (
            select(models.RefMaterialType)
            .where(
                or_(
                    models.RefMaterialType.name.ilike(f"%{clean}%"),
                    models.RefMaterialType.code.ilike(f"%{clean}%"),
                )
            )
            .order_by(models.RefMaterialType.name)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    # Convenience getters
    def get_material_type(self, session: Session, material_type_id: int) -> models.RefMaterialType | None:
        return session.get(models.RefMaterialType, material_type_id)

    def delete_by_id(self, session: Session, model: type, object_id: int) -> None:
        obj = session.get(model, object_id)
        if obj:
            session.delete(obj)
