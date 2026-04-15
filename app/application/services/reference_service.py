from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    ) -> None:
        self.repo = repo or ReferenceRepository()
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory or session_scope
        self._logger = logging.getLogger(__name__)

    def _require_admin_write(self, session: Session, actor_id: int, *, action: str) -> None:
        if actor_id is None:  # raise on missing actor_id
            raise ValueError("actor_id обязателен для операций записи")
        actor = self.user_repo.get_by_id(session, actor_id)
        if actor is not None and str(actor.role) == "admin":
            return
        with self.session_factory() as audit_session:
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

    def _audit_reference_write(
        self,
        session: Session,
        *,
        actor_id: int,
        action: str,
        item_type: str,
        item_id: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        audit_payload: dict[str, object] = {"item_type": item_type}
        if payload:
            audit_payload.update(payload)
        self.audit_repo.add_event(
            session,
            user_id=actor_id,
            entity_type="reference",
            entity_id=f"{item_type}:{item_id}",
            action=f"reference_{action}_{item_type}",
            payload_json=json.dumps(audit_payload, ensure_ascii=False),
        )

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

        with self.session_factory() as session:
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
            self._cleanup_obsolete_seed_rows(
                session,
                valid_group_codes={
                    str(item["code"])
                    for item in payload.get("antibiotic_groups", [])
                    if isinstance(item, dict) and item.get("code")
                },
                valid_antibiotic_codes={
                    str(item["code"])
                    for item in abx_payload
                    if isinstance(item, dict) and item.get("code")
                },
                valid_microorganism_codes={
                    str(item["code"])
                    for item in payload.get("microorganisms", [])
                    if isinstance(item, dict) and item.get("code")
                },
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

    def _cleanup_obsolete_seed_rows(
        self,
        session: Session,
        *,
        valid_group_codes: set[str],
        valid_antibiotic_codes: set[str],
        valid_microorganism_codes: set[str],
    ) -> None:
        for antibiotic in session.scalars(
            select(models.RefAntibiotic).where(models.RefAntibiotic.code.like("ABX-%"))
        ):
            antibiotic_code = str(antibiotic.code or "")
            antibiotic_id = cast(int | None, antibiotic.id)
            if antibiotic_code in valid_antibiotic_codes or antibiotic_id is None:
                continue
            if self._is_antibiotic_referenced(session, antibiotic_id):
                continue
            session.delete(antibiotic)

        for microorganism in session.scalars(
            select(models.RefMicroorganism).where(models.RefMicroorganism.code.like("MIC-%"))
        ):
            microorganism_code = str(microorganism.code or "")
            microorganism_id = cast(int | None, microorganism.id)
            if microorganism_code in valid_microorganism_codes or microorganism_id is None:
                continue
            if self._is_microorganism_referenced(session, microorganism_id):
                continue
            session.delete(microorganism)

        session.flush()

        for group in session.scalars(
            select(models.RefAntibioticGroup).where(models.RefAntibioticGroup.code.like("ABG-%"))
        ):
            group_code = str(group.code or "")
            group_id = cast(int | None, group.id)
            if group_code in valid_group_codes or group_id is None:
                continue
            has_antibiotics = session.scalar(
                select(models.RefAntibiotic.id).where(models.RefAntibiotic.group_id == group_id).limit(1)
            )
            if has_antibiotics is not None:
                continue
            session.delete(group)

    def _is_antibiotic_referenced(self, session: Session, antibiotic_id: int) -> bool:
        return any(
            session.scalar(query) is not None
            for query in (
                select(models.EmrAntibioticCourse.id).where(
                    models.EmrAntibioticCourse.antibiotic_id == antibiotic_id
                ).limit(1),
                select(models.LabAbxSusceptibility.id).where(
                    models.LabAbxSusceptibility.antibiotic_id == antibiotic_id
                ).limit(1),
                select(models.SanAbxSusceptibility.id).where(
                    models.SanAbxSusceptibility.antibiotic_id == antibiotic_id
                ).limit(1),
            )
        )

    def _is_microorganism_referenced(self, session: Session, microorganism_id: int) -> bool:
        return any(
            session.scalar(query) is not None
            for query in (
                select(models.LabMicrobeIsolation.id).where(
                    models.LabMicrobeIsolation.microorganism_id == microorganism_id
                ).limit(1),
                select(models.SanMicrobeIsolation.id).where(
                    models.SanMicrobeIsolation.microorganism_id == microorganism_id
                ).limit(1),
            )
        )

    def seed_defaults_if_empty(self) -> None:
        with self.session_factory() as session:
            has_groups = session.query(models.RefAntibioticGroup).first() is not None
            has_abx = session.query(models.RefAntibiotic).first() is not None
            has_micro = session.query(models.RefMicroorganism).first() is not None
        if not (has_groups or has_abx or has_micro):
            self.seed_defaults()

    def list_material_types(self) -> list[models.RefMaterialType]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefMaterialType)

    def list_departments(self) -> list[models.Department]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.Department)

    def upsert_bulk(self, model: type, items: Iterable[dict]) -> None:
        with self.session_factory() as session:
            self.repo.upsert_simple(session, model, items)

    def list_microorganisms(self) -> list[models.RefMicroorganism]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefMicroorganism)

    def list_icd10(self) -> list[models.RefICD10]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefICD10)

    def search_microorganisms(self, query: str, limit: int = 50) -> list[models.RefMicroorganism]:
        with self.session_factory() as session:
            return self.repo.search_microorganisms(session, query, limit=limit)

    def search_icd10(self, query: str, limit: int = 50) -> list[models.RefICD10]:
        with self.session_factory() as session:
            return self.repo.search_icd10(session, query, limit=limit)

    def search_antibiotics(self, query: str, limit: int = 50) -> list[models.RefAntibiotic]:
        with self.session_factory() as session:
            return self.repo.search_antibiotics(session, query, limit=limit)

    def search_material_types(self, query: str, limit: int = 50) -> list[models.RefMaterialType]:
        with self.session_factory() as session:
            return self.repo.search_material_types(session, query, limit=limit)

    def list_antibiotics(self) -> list[models.RefAntibiotic]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefAntibiotic)

    def list_antibiotic_groups(self) -> list[models.RefAntibioticGroup]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefAntibioticGroup)

    def list_phages(self) -> list[models.RefPhage]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefPhage)

    def list_ismp_abbreviations(self) -> list[models.RefIsmpAbbreviation]:
        with self.session_factory() as session:
            return self.repo.list_all(session, models.RefIsmpAbbreviation)

    def add_department(self, name: str, *, actor_id: int) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_department")
            self.repo.upsert_simple(session, models.Department, [{"name": name}], identity_field="name")
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="department",
                item_id=name,
                payload={"name": name},
            )

    def add_material_type(self, code: str, name: str, *, actor_id: int) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_material_type")
            self.repo.upsert_simple(
                session,
                models.RefMaterialType,
                [{"code": code, "name": name}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="material_type",
                item_id=code,
                payload={"code": code, "name": name},
            )

    def delete_department(self, dep_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_department")
            obj = session.get(models.Department, dep_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="department",
                    item_id=str(dep_id),
                )

    def delete_material_type(self, mt_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_material_type")
            obj = session.get(models.RefMaterialType, mt_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="material_type",
                    item_id=str(mt_id),
                )

    def add_icd10(self, code: str, title: str, *, actor_id: int) -> None:
        if not code or not title:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_icd10")
            self.repo.upsert_simple(
                session,
                models.RefICD10,
                [{"code": code, "title": title, "is_active": True}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="icd10",
                item_id=code,
                payload={"code": code},
            )

    def delete_icd10(self, code: str, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_icd10")
            obj = session.get(models.RefICD10, code)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="icd10",
                    item_id=code,
                )

    def add_antibiotic(
        self,
        code: str,
        name: str,
        group_id: int | None = None,
        *,
        actor_id: int,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_antibiotic")
            self.repo.upsert_simple(
                session,
                models.RefAntibiotic,
                [{"code": code, "name": name, "group_id": group_id}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="antibiotic",
                item_id=code,
                payload={"code": code, "group_id": group_id},
            )

    def delete_antibiotic(self, abx_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_antibiotic")
            obj = session.get(models.RefAntibiotic, abx_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="antibiotic",
                    item_id=str(abx_id),
                )

    def add_microorganism(
        self,
        code: str | None,
        name: str,
        taxon_group: str | None = None,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_microorganism")
            payload = {"code": code, "name": name, "taxon_group": taxon_group}
            self.repo.upsert_simple(session, models.RefMicroorganism, [payload], identity_field="code")
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="microorganism",
                item_id=code or name,
                payload={"code": code, "taxon_group": taxon_group},
            )

    def delete_microorganism(self, micro_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_microorganism")
            obj = session.get(models.RefMicroorganism, micro_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="microorganism",
                    item_id=str(micro_id),
                )

    def add_antibiotic_group(
        self,
        code: str | None,
        name: str,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_antibiotic_group")
            self.repo.upsert_simple(
                session,
                models.RefAntibioticGroup,
                [{"code": code, "name": name}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="antibiotic_group",
                item_id=code or name,
                payload={"code": code},
            )

    def delete_antibiotic_group(self, group_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_antibiotic_group")
            obj = session.get(models.RefAntibioticGroup, group_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="antibiotic_group",
                    item_id=str(group_id),
                )

    def add_phage(
        self,
        code: str | None,
        name: str,
        is_active: bool = True,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_phage")
            self.repo.upsert_simple(
                session,
                models.RefPhage,
                [{"code": code, "name": name, "is_active": is_active}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="phage",
                item_id=code or name,
                payload={"code": code, "is_active": is_active},
            )

    def delete_phage(self, phage_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_phage")
            obj = session.get(models.RefPhage, phage_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="phage",
                    item_id=str(phage_id),
                )

    def add_ismp_abbreviation(
        self,
        code: str,
        name: str,
        description: str | None = None,
        *,
        actor_id: int,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="add_ismp_abbreviation")
            self.repo.upsert_simple(
                session,
                models.RefIsmpAbbreviation,
                [{"code": code, "name": name, "description": description}],
                identity_field="code",
            )
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="create",
                item_type="ismp_abbreviation",
                item_id=code,
                payload={"code": code},
            )

    def delete_ismp_abbreviation(self, item_id: int, *, actor_id: int) -> None:
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="delete_ismp_abbreviation")
            obj = session.get(models.RefIsmpAbbreviation, item_id)
            if obj:
                session.delete(obj)
                self._audit_reference_write(
                    session,
                    actor_id=actor_id,
                    action="delete",
                    item_type="ismp_abbreviation",
                    item_id=str(item_id),
                )

    def update_department(self, dep_id: int, name: str, *, actor_id: int) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_department")
            obj = session.get(models.Department, dep_id)
            if not obj:
                raise ValueError("Отделение не найдено")
            obj_any = cast(Any, obj)
            obj_any.name = name
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="department",
                item_id=str(dep_id),
                payload={"name": name},
            )

    def update_material_type(
        self,
        mt_id: int,
        code: str,
        name: str,
        *,
        actor_id: int,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_material_type")
            obj = session.get(models.RefMaterialType, mt_id)
            if not obj:
                raise ValueError("Тип материала не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="material_type",
                item_id=str(mt_id),
                payload={"code": code, "name": name},
            )

    def update_icd10(self, code: str, title: str, *, actor_id: int) -> None:
        if not code or not title:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_icd10")
            obj = session.get(models.RefICD10, code)
            if not obj:
                raise ValueError("МКБ-10 не найден")
            obj_any = cast(Any, obj)
            obj_any.title = title
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="icd10",
                item_id=code,
                payload={"code": code},
            )

    def update_antibiotic(
        self,
        abx_id: int,
        code: str,
        name: str,
        group_id: int | None,
        *,
        actor_id: int,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_antibiotic")
            obj = session.get(models.RefAntibiotic, abx_id)
            if not obj:
                raise ValueError("Антибиотик не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.group_id = group_id
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="antibiotic",
                item_id=str(abx_id),
                payload={"code": code, "group_id": group_id},
            )

    def update_antibiotic_group(
        self,
        group_id: int,
        code: str | None,
        name: str,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_antibiotic_group")
            obj = session.get(models.RefAntibioticGroup, group_id)
            if not obj:
                raise ValueError("Группа антибиотиков не найдена")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="antibiotic_group",
                item_id=str(group_id),
                payload={"code": code},
            )

    def update_microorganism(
        self,
        micro_id: int,
        code: str | None,
        name: str,
        taxon_group: str | None,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_microorganism")
            obj = session.get(models.RefMicroorganism, micro_id)
            if not obj:
                raise ValueError("Микроорганизм не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.taxon_group = taxon_group
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="microorganism",
                item_id=str(micro_id),
                payload={"code": code, "taxon_group": taxon_group},
            )

    def update_phage(
        self,
        phage_id: int,
        code: str | None,
        name: str,
        is_active: bool,
        *,
        actor_id: int,
    ) -> None:
        if not name:
            raise ValueError("Название обязательно")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_phage")
            obj = session.get(models.RefPhage, phage_id)
            if not obj:
                raise ValueError("Фаг не найден")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.is_active = is_active
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="phage",
                item_id=str(phage_id),
                payload={"code": code, "is_active": is_active},
            )

    def update_ismp_abbreviation(
        self,
        item_id: int,
        code: str,
        name: str,
        description: str | None,
        *,
        actor_id: int,
    ) -> None:
        if not code or not name:
            raise ValueError("Код и название обязательны")
        with self.session_factory() as session:
            self._require_admin_write(session, actor_id, action="update_ismp_abbreviation")
            obj = session.get(models.RefIsmpAbbreviation, item_id)
            if not obj:
                raise ValueError("Сокращение не найдено")
            obj_any = cast(Any, obj)
            obj_any.code = code
            obj_any.name = name
            obj_any.description = description
            self._audit_reference_write(
                session,
                actor_id=actor_id,
                action="update",
                item_type="ismp_abbreviation",
                item_id=str(item_id),
                payload={"code": code},
            )

