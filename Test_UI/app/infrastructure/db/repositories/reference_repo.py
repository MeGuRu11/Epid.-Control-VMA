from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import (
    Department,
    RefAntibiotic,
    RefAntibioticGroup,
    RefIcd10,
    RefMaterialType,
    RefMicroorganism,
    RefPhage,
)
from .base import RepoBase


class ReferenceRepo(RepoBase):
    def list_departments(self) -> list[Department]:
        with self.tx() as s:
            return list(s.execute(select(Department).order_by(Department.name.asc())).scalars().all())

    def create_department(self, name: str) -> int:
        with self.tx() as s:
            row = Department(name=name)
            s.add(row)
            s.flush()
            return int(row.id)

    def list_material_types(self) -> list[RefMaterialType]:
        with self.tx() as s:
            return list(s.execute(select(RefMaterialType).order_by(RefMaterialType.code.asc())).scalars().all())

    def create_material_type(self, code: str, name: str) -> int:
        with self.tx() as s:
            row = RefMaterialType(code=code.strip().upper(), name=name.strip())
            s.add(row)
            s.flush()
            return int(row.id)

    def ensure_material_type(self, code: str, name: str) -> int:
        with self.tx() as s:
            row = s.execute(select(RefMaterialType).where(RefMaterialType.code == code)).scalar_one_or_none()
            if row:
                return int(row.id)
            row = RefMaterialType(code=code, name=name)
            s.add(row)
            s.flush()
            return int(row.id)

    # ── МКБ-10 ────────────────────────────────────────────────────────────
    def list_icd10(self, q: str = "", limit: int = 300) -> list[RefIcd10]:
        with self.tx() as s:
            stmt = select(RefIcd10).order_by(RefIcd10.code.asc())
            if q:
                qlike = f"%{q}%"
                stmt = stmt.where((RefIcd10.code.ilike(qlike)) | (RefIcd10.title.ilike(qlike)))
            return list(s.execute(stmt.limit(limit)).scalars().all())

    def create_icd10(self, code: str, title: str) -> str:
        with self.tx() as s:
            row = RefIcd10(code=code.strip().upper(), title=title.strip())
            s.add(row)
            s.flush()
            return str(row.code)

    def set_icd10_active(self, code: str, is_active: bool) -> None:
        with self.tx() as s:
            row = s.execute(select(RefIcd10).where(RefIcd10.code == code)).scalar_one_or_none()
            if row:
                row.is_active = is_active

    # ── Микроорганизмы ────────────────────────────────────────────────────
    def list_microorganisms(self, q: str = "") -> list[RefMicroorganism]:
        with self.tx() as s:
            stmt = select(RefMicroorganism).order_by(RefMicroorganism.name.asc())
            if q:
                stmt = stmt.where(RefMicroorganism.name.ilike(f"%{q}%"))
            return list(s.execute(stmt).scalars().all())

    def create_microorganism(self, code: str, name: str, taxon_group: str = "") -> int:
        with self.tx() as s:
            row = RefMicroorganism(
                code=code.strip() or None,
                name=name.strip(),
                taxon_group=taxon_group.strip() or None,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def set_microorganism_active(self, organism_id: int, is_active: bool) -> None:
        with self.tx() as s:
            row = s.get(RefMicroorganism, organism_id)
            if row:
                row.is_active = is_active

    # ── Группы антибиотиков ───────────────────────────────────────────────
    def list_antibiotic_groups(self) -> list[RefAntibioticGroup]:
        with self.tx() as s:
            return list(
                s.execute(select(RefAntibioticGroup).order_by(RefAntibioticGroup.name.asc())).scalars().all()
            )

    def create_antibiotic_group(self, code: str, name: str) -> int:
        with self.tx() as s:
            row = RefAntibioticGroup(code=code.strip() or None, name=name.strip())
            s.add(row)
            s.flush()
            return int(row.id)

    # ── Антибиотики ───────────────────────────────────────────────────────
    def list_antibiotics(self, group_id: int | None = None) -> list[RefAntibiotic]:
        with self.tx() as s:
            stmt = select(RefAntibiotic).order_by(RefAntibiotic.name.asc())
            if group_id is not None:
                stmt = stmt.where(RefAntibiotic.group_id == group_id)
            return list(s.execute(stmt).scalars().all())

    def create_antibiotic(self, code: str, name: str, group_id: int | None = None) -> int:
        with self.tx() as s:
            row = RefAntibiotic(code=code.strip() or None, name=name.strip(), group_id=group_id)
            s.add(row)
            s.flush()
            return int(row.id)

    # ── Бактериофаги ──────────────────────────────────────────────────────
    def list_phages(self) -> list[RefPhage]:
        with self.tx() as s:
            return list(s.execute(select(RefPhage).order_by(RefPhage.name.asc())).scalars().all())

    def create_phage(self, code: str, name: str) -> int:
        with self.tx() as s:
            row = RefPhage(code=code.strip() or None, name=name.strip())
            s.add(row)
            s.flush()
            return int(row.id)

    def set_phage_active(self, phage_id: int, is_active: bool) -> None:
        with self.tx() as s:
            row = s.get(RefPhage, phage_id)
            if row:
                row.is_active = is_active

    def seed_min_references(self) -> None:
        with self.tx() as s:
            if not s.execute(select(Department.id).limit(1)).first():
                for name in ["Хирургия", "ОРИТ", "Терапия", "Лаборатория"]:
                    s.add(Department(name=name))

            if not s.execute(select(RefMaterialType.id).limit(1)).first():
                s.add(RefMaterialType(code="BLD", name="Кровь"))
                s.add(RefMaterialType(code="URN", name="Моча"))
                s.add(RefMaterialType(code="SPT", name="Мокрота"))

            if not s.execute(select(RefMicroorganism.id).limit(1)).first():
                s.add(RefMicroorganism(code="SAUR", name="S. aureus", taxon_group="bacteria"))
                s.add(RefMicroorganism(code="ECOL", name="E. coli", taxon_group="bacteria"))

            if not s.execute(select(RefAntibioticGroup.id).limit(1)).first():
                grp = RefAntibioticGroup(code="BETAL", name="Бета-лактамы")
                s.add(grp)
                s.flush()
                s.add(RefAntibiotic(code="CTX", name="Цефотаксим", group_id=grp.id))

            if not s.execute(select(RefPhage.id).limit(1)).first():
                s.add(RefPhage(code="STPH", name="Стафилококковый бактериофаг"))

            if not s.execute(select(RefIcd10.code).limit(1)).first():
                s.add(RefIcd10(code="A41.9", title="Сепсис неуточненный"))

