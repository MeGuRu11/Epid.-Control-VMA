from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.reference_repo import ReferenceRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope


class ReferenceService:
    def __init__(
        self,
        repo: ReferenceRepository | None = None,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.repo = repo or ReferenceRepository()
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self._logger = logging.getLogger(__name__)

    def _require_admin_write(self, session, actor_id: int | None, *, action: str) -> None:
        if actor_id is None:
            return
        actor = self.user_repo.get_by_id(session, actor_id)
        if actor and actor.role == "admin":
            return
        with session_scope() as audit_session:
            self.audit_repo.add_event(
                audit_session,
                user_id=actor_id,
                entity_type="reference",
                entity_id="*",
                action="access_denied",
                payload_json=json.dumps(
                    {
                        "reason": "admin_required",
                        "permission": "manage_references",
                        "action": action,
                    },
                    ensure_ascii=False,
                ),
            )
        raise ValueError("Недостаточно прав для редактирования справочников")

    def seed_defaults(self, seed_path: Path | None = None) -> None:
        seed_file = seed_path or Path(__file__).resolve().parents[3] / "resources" / "reference_seed.json"
        if not seed_file.exists():
            self._logger.warning("Reference seed file not found: %s", seed_file)
            return
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        self._logger.info(
            "Reference seed loaded: groups=%s, antibiotics=%s, microorganisms=%s, ismp_abbrev=%s",
            len(payload.get("antibiotic_groups", [])),
            len(payload.get("antibiotics", [])),
            len(payload.get("microorganisms", [])),
            len(payload.get("ismp_abbreviations", [])),
        )

        with session_scope() as session:
            self.repo.upsert_simple(
                session,
                models.RefAntibioticGroup,
                payload.get("antibiotic_groups", []),
                identity_field="code",
            )
            session.flush()
            group_id_by_code = {
                grp.code: grp.id
                for grp in self.repo.list_all(session, models.RefAntibioticGroup)
                if grp.code
            }
            abx_payload = []
            for item in payload.get("antibiotics", []):
                code = item.get("code")
                name = item.get("name")
                if not code or not name:
                    continue
                group_id = group_id_by_code.get(item.get("group_code"))
                abx_payload.append({"code": code, "name": name, "group_id": group_id})
            self.repo.upsert_simple(
                session,
                models.RefAntibiotic,
                abx_payload,
                identity_field="code",
            )
            self.repo.upsert_simple(
                session,
                models.RefMicroorganism,
                payload.get("microorganisms", []),
                identity_field="code",
            )
            ismp_payload = payload.get("ismp_abbreviations", [])
            if ismp_payload:
                session.query(models.RefIsmpAbbreviation).delete()
                self.repo.upsert_simple(
                    session,
                    models.RefIsmpAbbreviation,
                    ismp_payload,
                    identity_field="code",
                )
        self._logger.info("Reference seed applied")

    def seed_defaults_if_empty(self) -> None:
        with session_scope() as session:
            has_groups = session.query(models.RefAntibioticGroup).first() is not None
            has_abx = session.query(models.RefAntibiotic).first() is not None
            has_micro = session.query(models.RefMicroorganism).first() is not None
        if not (has_groups or has_abx or has_micro):
            self.seed_defaults()

    def list_material_types(self) -> list[models.RefMaterialType]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefMaterialType)

    def list_departments(self) -> list[models.Department]:
        with session_scope() as session:
            return self.repo.list_all(session, models.Department)

    def upsert_bulk(self, model: type, items: Iterable[dict]) -> None:
        with session_scope() as session:
            self.repo.upsert_simple(session, model, items)

    def list_microorganisms(self) -> list[models.RefMicroorganism]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefMicroorganism)

    def list_icd10(self) -> list[models.RefICD10]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefICD10)

    def search_microorganisms(self, query: str, limit: int = 50) -> list[models.RefMicroorganism]:
        with session_scope() as session:
            return self.repo.search_microorganisms(session, query, limit=limit)

    def search_icd10(self, query: str, limit: int = 50) -> list[models.RefICD10]:
        with session_scope() as session:
            return self.repo.search_icd10(session, query, limit=limit)

    def search_antibiotics(self, query: str, limit: int = 50) -> list[models.RefAntibiotic]:
        with session_scope() as session:
            return self.repo.search_antibiotics(session, query, limit=limit)

    def search_material_types(self, query: str, limit: int = 50) -> list[models.RefMaterialType]:
        with session_scope() as session:
            return self.repo.search_material_types(session, query, limit=limit)

    def list_antibiotics(self) -> list[models.RefAntibiotic]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefAntibiotic)

    def list_antibiotic_groups(self) -> list[models.RefAntibioticGroup]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefAntibioticGroup)

    def list_phages(self) -> list[models.RefPhage]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefPhage)

    def list_ismp_abbreviations(self) -> list[models.RefIsmpAbbreviation]:
        with session_scope() as session:
            return self.repo.list_all(session, models.RefIsmpAbbreviation)

    def add_department(self, name: str, *, actor_id: int | None = None) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_department")
            self.repo.upsert_simple(session, models.Department, [{"name": name}], identity_field="name")

    def add_material_type(self, code: str, name: str, *, actor_id: int | None = None) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_material_type")
            self.repo.upsert_simple(
                session,
                models.RefMaterialType,
                [{"code": code, "name": name}],
                identity_field="code",
            )

    def delete_department(self, dep_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_department")
            self.repo.delete_by_id(session, models.Department, dep_id)

    def delete_material_type(self, mt_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_material_type")
            self.repo.delete_by_id(session, models.RefMaterialType, mt_id)

    def add_icd10(self, code: str, title: str, *, actor_id: int | None = None) -> None:
        if not code or not title:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_icd10")
            self.repo.upsert_simple(
                session,
                models.RefICD10,
                [{"code": code, "title": title, "is_active": True}],
                identity_field="code",
            )

    def delete_icd10(self, code: str, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_icd10")
            obj = session.get(models.RefICD10, code)
            if obj:
                session.delete(obj)

    def add_antibiotic(
        self,
        code: str,
        name: str,
        group_id: int | None = None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_antibiotic")
            self.repo.upsert_simple(
                session,
                models.RefAntibiotic,
                [{"code": code, "name": name, "group_id": group_id}],
                identity_field="code",
            )

    def delete_antibiotic(self, abx_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_antibiotic")
            self.repo.delete_by_id(session, models.RefAntibiotic, abx_id)

    def add_microorganism(
        self,
        code: str | None,
        name: str,
        taxon_group: str | None = None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_microorganism")
            payload = {"code": code, "name": name, "taxon_group": taxon_group}
            self.repo.upsert_simple(session, models.RefMicroorganism, [payload], identity_field="code")

    def delete_microorganism(self, micro_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_microorganism")
            self.repo.delete_by_id(session, models.RefMicroorganism, micro_id)

    def add_antibiotic_group(
        self,
        code: str | None,
        name: str,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_antibiotic_group")
            self.repo.upsert_simple(
                session,
                models.RefAntibioticGroup,
                [{"code": code, "name": name}],
                identity_field="code",
            )

    def delete_antibiotic_group(self, group_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_antibiotic_group")
            self.repo.delete_by_id(session, models.RefAntibioticGroup, group_id)

    def add_phage(
        self,
        code: str | None,
        name: str,
        is_active: bool = True,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_phage")
            self.repo.upsert_simple(
                session,
                models.RefPhage,
                [{"code": code, "name": name, "is_active": is_active}],
                identity_field="code",
            )

    def delete_phage(self, phage_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_phage")
            self.repo.delete_by_id(session, models.RefPhage, phage_id)

    def add_ismp_abbreviation(
        self,
        code: str,
        name: str,
        description: str | None = None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="add_ismp_abbreviation")
            self.repo.upsert_simple(
                session,
                models.RefIsmpAbbreviation,
                [{"code": code, "name": name, "description": description}],
                identity_field="code",
            )

    def delete_ismp_abbreviation(self, item_id: int, *, actor_id: int | None = None) -> None:
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="delete_ismp_abbreviation")
            self.repo.delete_by_id(session, models.RefIsmpAbbreviation, item_id)

    def update_department(self, dep_id: int, name: str, *, actor_id: int | None = None) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_department")
            obj = session.get(models.Department, dep_id)
            if not obj:
                raise ValueError("Отделение не найдено")
            obj_any = cast(Any, obj)
            obj_any.name = name

    def update_material_type(
        self,
        mt_id: int,
        code: str,
        name: str,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_material_type")
            obj = session.get(models.RefMaterialType, mt_id)
            if not obj:
                raise ValueError("Тип материала не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name

    def update_icd10(self, code: str, title: str, *, actor_id: int | None = None) -> None:
        if not code or not title:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_icd10")
            obj = session.get(models.RefICD10, code)
            if not obj:
                raise ValueError("МКБ-10 не найден")
            obj_any = cast(Any, obj)
            obj_any.title = title

    def update_antibiotic(
        self,
        abx_id: int,
        code: str,
        name: str,
        group_id: int | None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_antibiotic")
            obj = session.get(models.RefAntibiotic, abx_id)
            if not obj:
                raise ValueError("Антибиотик не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.group_id = group_id

    def update_antibiotic_group(
        self,
        group_id: int,
        code: str | None,
        name: str,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_antibiotic_group")
            obj = session.get(models.RefAntibioticGroup, group_id)
            if not obj:
                raise ValueError("Группа антибиотиков не найдена")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name

    def update_microorganism(
        self,
        micro_id: int,
        code: str | None,
        name: str,
        taxon_group: str | None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_microorganism")
            obj = session.get(models.RefMicroorganism, micro_id)
            if not obj:
                raise ValueError("Микроорганизм не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.taxon_group = taxon_group

    def update_phage(
        self,
        phage_id: int,
        code: str | None,
        name: str,
        is_active: bool,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_phage")
            obj = session.get(models.RefPhage, phage_id)
            if not obj:
                raise ValueError("Фаг не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.is_active = is_active


    def update_ismp_abbreviation(
        self,
        item_id: int,
        code: str,
        name: str,
        description: str | None,
        *,
        actor_id: int | None = None,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with session_scope() as session:
            self._require_admin_write(session, actor_id, action="update_ismp_abbreviation")
            obj = session.get(models.RefIsmpAbbreviation, item_id)
            if not obj:
                raise ValueError("Сокращение не найдено")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.description = description
