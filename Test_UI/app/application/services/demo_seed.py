from __future__ import annotations

import random
from datetime import date, timedelta

from .emr_service import EmrService
from .form100_service import Form100Service
from .lab_service import LabService
from .patient_service import PatientService
from .reference_service import ReferenceService
from .sanitary_service import SanitaryService


def seed_demo(engine, session_ctx):
    ReferenceService(engine, session_ctx)

    ps = PatientService(engine, session_ctx)
    es = EmrService(engine, session_ctx)
    ls = LabService(engine, session_ctx)
    ss = SanitaryService(engine, session_ctx)
    f100 = Form100Service(engine, session_ctx)

    names = [
        "Иванов Иван Иванович",
        "Петров Петр Петрович",
        "Сидоров Сергей Сергеевич",
        "Кузнецов Андрей Олегович",
    ]
    patient_ids = [ps.create(n, "M", None) for n in names]

    for pid in patient_ids:
        case_id = es.ensure_case(pid, f"ИБ-{random.randint(1000, 9999)}", "Хирургия")
        for _ in range(2):
            adm = date.today() - timedelta(days=random.randint(1, 20))
            inj = adm - timedelta(days=random.randint(0, 5))
            out = adm + timedelta(days=random.randint(2, 12))
            version_id = es.create_new_version(
                case_id,
                {
                    "admission_date": adm,
                    "injury_date": inj,
                    "outcome_date": out,
                    "severity": random.choice(["легкая", "средняя", "тяжелая"]),
                    "sofa_score": random.randint(0, 18),
                    "notes": "Демо-версия ЭМЗ",
                },
            )
            es.save_children(
                version_id,
                diagnoses=[{"kind": "admission", "icd10_code": "A41.9", "free_text": "Сепсис"}],
                interventions=[{"type": "ventilation", "duration_minutes": random.randint(60, 480)}],
                abx_courses=[{"drug_name_free": "Цефотаксим", "route": "iv", "dose": "1g bid"}],
            )

        for _ in range(2):
            ls.create_auto(pid, emr_case_id=case_id, material="Кровь", organism="S. aureus")
        f100.create(pid, case_id, {"evac_stage": "Role 2"})

    for idx in range(5):
        ss.create(
            lab_no=f"SAN-{date.today().strftime('%Y%m%d')}-{idx + 1:03d}",
            sampling_point=f"Палата {idx + 1}",
            room=str(100 + idx),
            growth_flag=1 if idx % 2 == 0 else 0,
            cfu="1e3" if idx % 2 == 0 else "0",
        )

