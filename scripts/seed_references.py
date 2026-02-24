from __future__ import annotations

import json

from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.repositories.reference_repo import ReferenceRepository
from app.infrastructure.db.session import session_scope


def seed():
    data = {
        "departments": [
            {"name": "Хирургия"},
            {"name": "Терапия"},
            {"name": "Реанимация"},
        ],
        "ref_material_types": [
            {"code": "BLD", "name": "Кровь"},
            {"code": "UR", "name": "Моча"},
            {"code": "SW", "name": "Смыв"},
        ],
        "ref_antibiotic_groups": [
            {"code": "PEN", "name": "Пенициллины"},
            {"code": "CEF", "name": "Цефалоспорины"},
        ],
        "ref_antibiotics": [
            {"code": "AMX", "name": "Амоксициллин", "group_id": None},
            {"code": "CRO", "name": "Цефтриаксон", "group_id": None},
        ],
        "ref_phages": [
            {"code": "PH1", "name": "Бактериофаг 1", "is_active": True},
        ],
    }
    repo = ReferenceRepository()
    with session_scope() as session:
        repo.upsert_simple(session, models.Department, data["departments"], identity_field="name")
        repo.upsert_simple(session, models.RefMaterialType, data["ref_material_types"], identity_field="code")
        repo.upsert_simple(session, models.RefAntibioticGroup, data["ref_antibiotic_groups"], identity_field="code")
        repo.upsert_simple(session, models.RefAntibiotic, data["ref_antibiotics"], identity_field="code")
        repo.upsert_simple(session, models.RefPhage, data["ref_phages"], identity_field="code")
    print("Seeded:", json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    seed()
