from __future__ import annotations

from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.reference_repo import ReferenceRepo


class ReferenceService:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._repo = ReferenceRepo(engine)
        self._audit = AuditLogger(engine)
        self._repo.seed_min_references()

    def departments(self):
        return self._repo.list_departments()

    def create_department(self, name: str) -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        dep_id = self._repo.create_department(name.strip())
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "departments",
                str(dep_id),
                "create",
                {"name": name},
            )
        )
        return dep_id

    def material_types(self):
        return self._repo.list_material_types()

    def create_material_type(self, code: str, name: str) -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        return self._repo.create_material_type(code, name)

    # ── МКБ-10 ────────────────────────────────────────────────────────────
    def icd10_list(self, q: str = "") -> list:
        return self._repo.list_icd10(q=q)

    def create_icd10(self, code: str, title: str) -> str:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        result = self._repo.create_icd10(code, title)
        self._audit.log(
            AuditEvent(self._session.user_id, self._session.login, "ref_icd10", code, "create", {"title": title})
        )
        return result

    def set_icd10_active(self, code: str, is_active: bool) -> None:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        self._repo.set_icd10_active(code, is_active)

    # ── Микроорганизмы ────────────────────────────────────────────────────
    def microorganisms(self, q: str = "") -> list:
        return self._repo.list_microorganisms(q=q)

    def create_microorganism(self, code: str, name: str, taxon_group: str = "") -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        org_id = self._repo.create_microorganism(code, name, taxon_group)
        self._audit.log(
            AuditEvent(self._session.user_id, self._session.login, "ref_microorganism", str(org_id), "create", {"name": name})
        )
        return org_id

    def set_microorganism_active(self, organism_id: int, is_active: bool) -> None:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        self._repo.set_microorganism_active(organism_id, is_active)

    # ── Группы антибиотиков ───────────────────────────────────────────────
    def antibiotic_groups(self) -> list:
        return self._repo.list_antibiotic_groups()

    def create_antibiotic_group(self, code: str, name: str) -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        grp_id = self._repo.create_antibiotic_group(code, name)
        self._audit.log(
            AuditEvent(self._session.user_id, self._session.login, "ref_abx_group", str(grp_id), "create", {"name": name})
        )
        return grp_id

    # ── Антибиотики ───────────────────────────────────────────────────────
    def antibiotics(self, group_id: int | None = None) -> list:
        return self._repo.list_antibiotics(group_id=group_id)

    def create_antibiotic(self, code: str, name: str, group_id: int | None = None) -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        abx_id = self._repo.create_antibiotic(code, name, group_id)
        self._audit.log(
            AuditEvent(self._session.user_id, self._session.login, "ref_antibiotic", str(abx_id), "create", {"name": name})
        )
        return abx_id

    # ── Бактериофаги ──────────────────────────────────────────────────────
    def phages(self) -> list:
        return self._repo.list_phages()

    def create_phage(self, code: str, name: str) -> int:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        phage_id = self._repo.create_phage(code, name)
        self._audit.log(
            AuditEvent(self._session.user_id, self._session.login, "ref_phage", str(phage_id), "create", {"name": name})
        )
        return phage_id

    def set_phage_active(self, phage_id: int, is_active: bool) -> None:
        if self._session.role != "admin":
            raise PermissionError("Only admin can modify references.")
        self._repo.set_phage_active(phage_id, is_active)
