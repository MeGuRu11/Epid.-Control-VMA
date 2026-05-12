"""
IdResolver — резолвинг числовых FK-ID в человекочитаемые строки.

Используется в human-readable экспорте (CSV, PDF).
Не используется в machine-exchange JSON (там ID нужны).

Работает через pre-fetch: один запрос к справочнику на экспорт,
не N запросов на строку.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class IdResolver:
    """Кэширует справочники на время жизни объекта (один экспорт)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._material_types: dict[int, str] = {}
        self._microorganisms: dict[int, str] = {}
        self._antibiotics: dict[int, str] = {}
        self._departments: dict[int, str] = {}
        self._users: dict[int, str] = {}

    def _load_material_types(self) -> None:
        if self._material_types:
            return
        from app.infrastructure.db.models_sqlalchemy import RefMaterialType

        rows = self._session.query(RefMaterialType).all()
        self._material_types = {int(r.id): f"{r.code} — {r.name}" for r in rows}

    def _load_microorganisms(self) -> None:
        if self._microorganisms:
            return
        from app.infrastructure.db.models_sqlalchemy import RefMicroorganism

        rows = self._session.query(RefMicroorganism).all()
        self._microorganisms = {int(r.id): f"{r.code} — {r.name}" for r in rows}

    def _load_antibiotics(self) -> None:
        if self._antibiotics:
            return
        from app.infrastructure.db.models_sqlalchemy import RefAntibiotic

        rows = self._session.query(RefAntibiotic).all()
        self._antibiotics = {int(r.id): f"{r.code} — {r.name}" for r in rows}

    def _load_departments(self) -> None:
        if self._departments:
            return
        from app.infrastructure.db.models_sqlalchemy import Department

        rows = self._session.query(Department).all()
        self._departments = {int(r.id): str(r.name) for r in rows}

    def _load_users(self) -> None:
        if self._users:
            return
        from app.infrastructure.db.models_sqlalchemy import User

        rows = self._session.query(User).all()
        self._users = {int(r.id): str(r.login) for r in rows}

    def resolve_material_type(self, id_: int | None) -> str:
        if id_ is None:
            return "—"
        self._load_material_types()
        return self._material_types.get(id_, str(id_))

    def resolve_microorganism(self, id_: int | None) -> str:
        if id_ is None:
            return "—"
        self._load_microorganisms()
        return self._microorganisms.get(id_, str(id_))

    def resolve_antibiotic(self, id_: int | None) -> str:
        if id_ is None:
            return "—"
        self._load_antibiotics()
        return self._antibiotics.get(id_, str(id_))

    def resolve_department(self, id_: int | None) -> str:
        if id_ is None:
            return "—"
        self._load_departments()
        return self._departments.get(id_, str(id_))

    def resolve_user(self, id_: int | None) -> str:
        if id_ is None:
            return "—"
        self._load_users()
        return self._users.get(id_, str(id_))
