#!/usr/bin/env python
# ruff: noqa: E402,I001
"""Seed demo data for checking Analytics with a non-empty database.

Usage:
    python scripts/seed_demo_data.py [--clear]

The ``--clear`` flag removes patients, EMR cases, lab samples, ISMP cases,
and sanitary samples before seeding. Users, references, and settings are not
cleared.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR, DB_FILE  # noqa: E402
from app.domain.constants import IsmpType  # noqa: E402
from app.infrastructure.db.models_sqlalchemy import (  # noqa: E402
    Department,
    EmrAntibioticCourse,
    EmrCase,
    EmrCaseVersion,
    EmrDiagnosis,
    EmrIntervention,
    IsmpCase,
    LabAbxSusceptibility,
    LabMicrobeIsolation,
    LabPhagePanelResult,
    LabSample,
    Patient,
    RefAntibiotic,
    RefAntibioticGroup,
    RefICD10,
    RefMaterialType,
    RefMicroorganism,
    SanAbxSusceptibility,
    SanMicrobeIsolation,
    SanPhagePanelResult,
    SanitarySample,
)
from app.infrastructure.db.session import session_scope  # noqa: E402


@dataclass(frozen=True)
class SeedStats:
    patients: int
    emr_cases: int
    lab_samples: int
    positive_lab_samples: int
    resistance_anchor_samples: int
    ismp_cases: int
    sanitary_samples: int


@dataclass(frozen=True)
class DemoCase:
    case: EmrCase
    version: EmrCaseVersion
    department: Department


_PATIENTS = [
    {
        "last_name": "Иванов",
        "first_name": "Пётр",
        "middle_name": "Алексеевич",
        "birth_date": "1975-03-15",
        "gender": "M",
    },
    {
        "last_name": "Петрова",
        "first_name": "Мария",
        "middle_name": "Ивановна",
        "birth_date": "1962-07-22",
        "gender": "F",
    },
    {
        "last_name": "Сидоров",
        "first_name": "Алексей",
        "middle_name": "Викторович",
        "birth_date": "1988-11-08",
        "gender": "M",
    },
    {
        "last_name": "Козлова",
        "first_name": "Наталья",
        "middle_name": "Павловна",
        "birth_date": "1950-02-14",
        "gender": "F",
    },
    {
        "last_name": "Новиков",
        "first_name": "Игорь",
        "middle_name": "Дмитриевич",
        "birth_date": "1970-09-30",
        "gender": "M",
    },
]

_DEPARTMENT_NAMES = ("Реанимация (ОРИТ)", "Хирургия", "Терапия", "Неврология")

_ICD10 = {
    "J18.0": "Бронхопневмония неуточненная",
    "A41.9": "Сепсис неуточненный",
    "K35.2": "Острый аппендицит с генерализованным перитонитом",
    "I21.0": "Острый трансмуральный инфаркт передней стенки миокарда",
    "G40.3": "Генерализованная идиопатическая эпилепсия",
}

_MATERIALS = {
    "BLD": "Кровь",
    "UR": "Моча",
    "WND": "Раневое отделяемое",
    "SPT": "Мокрота",
}

_MICROBES = {
    "ECOL": ("E. coli", "bacteria"),
    "SAUR": ("S. aureus", "bacteria"),
    "KPNE": ("K. pneumoniae", "bacteria"),
    "PAER": ("P. aeruginosa", "bacteria"),
    "CALB": ("Candida albicans", "fungi"),
}

_ABX_GROUPS = {
    "PEN": "Пенициллины",
    "CEF": "Цефалоспорины",
    "FQ": "Фторхинолоны",
    "CARB": "Карбапенемы",
    "GLY": "Гликопептиды",
}

_ABX = [
    {"code": "AMP", "name": "Ампициллин", "group_code": "PEN"},
    {"code": "CRO", "name": "Цефтриаксон", "group_code": "CEF"},
    {"code": "CIP", "name": "Ципрофлоксацин", "group_code": "FQ"},
    {"code": "MEM", "name": "Меропенем", "group_code": "CARB"},
    {"code": "VAN", "name": "Ванкомицин", "group_code": "GLY"},
]

_SANITARY_OBJECTS = (
    "Воздух операционной",
    "Смыв со стола",
    "Поверхность медоборудования",
)

_RIS_WEIGHTS = ("R", "R", "R", "R", "I", "I", "I", "S", "S", "S")
_RESISTANCE_ANCHORS = (
    ("ECOL", "E. coli", "AMP", "Ампициллин", ("R", "R", "R", "R", "I", "R", "R")),
    ("ECOL", "E. coli", "CIP", "Ципрофлоксацин", ("S", "S", "S", "S", "I", "S")),
    ("SAUR", "S. aureus", "VAN", "Ванкомицин", ("S", "S", "S", "S", "S")),
    ("KPNE", "K. pneumoniae", "MEM", "Меропенем", ("R", "R", "I", "R", "I")),
)
_DEMO_ID_STORE = DATA_DIR / "seed_demo_ids.json"


def _as_dt(value: date, *, hour: int = 9, minute: int = 0) -> datetime:
    return datetime.combine(value, time(hour=hour, minute=minute))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _load_demo_patient_ids(id_store_path: Path | None) -> set[int]:
    if id_store_path is None or not id_store_path.exists():
        return set()
    try:
        payload: Any = json.loads(id_store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, dict):
        return set()
    raw_ids = payload.get("patient_ids", [])
    if not isinstance(raw_ids, list):
        return set()
    patient_ids: set[int] = set()
    for raw_id in raw_ids:
        try:
            patient_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue
    return patient_ids


def _write_demo_ids(session: Session, id_store_path: Path | None, *, run_tag: str) -> None:
    if id_store_path is None:
        return
    case_ids = list(
        session.scalars(select(EmrCase.id).where(EmrCase.hospital_case_no.like(f"DEMO-{run_tag}-%"))).all()
    )
    lab_ids = list(
        session.scalars(select(LabSample.id).where(LabSample.lab_no.like(f"DEMO-LAB-{run_tag}-%"))).all()
    )
    sanitary_ids = list(
        session.scalars(
            select(SanitarySample.id).where(SanitarySample.lab_no.like(f"DEMO-SAN-{run_tag}-%"))
        ).all()
    )
    patient_ids = set(
        session.scalars(select(EmrCase.patient_id).where(EmrCase.id.in_(case_ids))).all()
    )
    patient_ids.update(session.scalars(select(LabSample.patient_id).where(LabSample.id.in_(lab_ids))).all())
    payload = {
        "run_tag": run_tag,
        "patient_ids": sorted(int(patient_id) for patient_id in patient_ids if patient_id is not None),
        "emr_case_ids": [int(case_id) for case_id in case_ids if case_id is not None],
        "lab_sample_ids": [int(sample_id) for sample_id in lab_ids if sample_id is not None],
        "sanitary_sample_ids": [int(sample_id) for sample_id in sanitary_ids if sample_id is not None],
    }
    id_store_path.parent.mkdir(parents=True, exist_ok=True)
    id_store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_data(session: Session, *, id_store_path: Path | None = None) -> None:
    patient_ids = _load_demo_patient_ids(id_store_path)
    patient_ids.update(
        int(patient_id)
        for patient_id in session.scalars(
            select(LabSample.patient_id).where(LabSample.lab_no.like("DEMO-%"))
        ).all()
        if patient_id is not None
    )
    patient_ids.update(
        int(patient_id)
        for patient_id in session.scalars(
            select(EmrCase.patient_id).where(EmrCase.hospital_case_no.like("DEMO-%"))
        ).all()
        if patient_id is not None
    )

    demo_lab_ids = select(LabSample.id).where(LabSample.lab_no.like("DEMO-%"))
    demo_sanitary_ids = select(SanitarySample.id).where(SanitarySample.lab_no.like("DEMO-%"))
    demo_case_ids = select(EmrCase.id).where(EmrCase.hospital_case_no.like("DEMO-%"))
    demo_version_ids = select(EmrCaseVersion.id).where(EmrCaseVersion.emr_case_id.in_(demo_case_ids))

    session.execute(delete(SanAbxSusceptibility).where(SanAbxSusceptibility.sanitary_sample_id.in_(demo_sanitary_ids)))
    session.execute(delete(SanPhagePanelResult).where(SanPhagePanelResult.sanitary_sample_id.in_(demo_sanitary_ids)))
    session.execute(delete(SanMicrobeIsolation).where(SanMicrobeIsolation.sanitary_sample_id.in_(demo_sanitary_ids)))
    session.execute(delete(SanitarySample).where(SanitarySample.lab_no.like("DEMO-%")))

    session.execute(delete(LabAbxSusceptibility).where(LabAbxSusceptibility.lab_sample_id.in_(demo_lab_ids)))
    session.execute(delete(LabPhagePanelResult).where(LabPhagePanelResult.lab_sample_id.in_(demo_lab_ids)))
    session.execute(delete(LabMicrobeIsolation).where(LabMicrobeIsolation.lab_sample_id.in_(demo_lab_ids)))
    session.execute(delete(LabSample).where(LabSample.lab_no.like("DEMO-%")))

    session.execute(delete(IsmpCase).where(IsmpCase.emr_case_id.in_(demo_case_ids)))
    session.execute(delete(EmrAntibioticCourse).where(EmrAntibioticCourse.emr_case_version_id.in_(demo_version_ids)))
    session.execute(delete(EmrIntervention).where(EmrIntervention.emr_case_version_id.in_(demo_version_ids)))
    session.execute(delete(EmrDiagnosis).where(EmrDiagnosis.emr_case_version_id.in_(demo_version_ids)))
    session.execute(delete(EmrCaseVersion).where(EmrCaseVersion.emr_case_id.in_(demo_case_ids)))
    session.execute(delete(EmrCase).where(EmrCase.hospital_case_no.like("DEMO-%")))

    session.flush()
    for patient_id in sorted(patient_ids):
        has_cases = session.scalar(select(EmrCase.id).where(EmrCase.patient_id == patient_id).limit(1))
        has_samples = session.scalar(select(LabSample.id).where(LabSample.patient_id == patient_id).limit(1))
        if has_cases is None and has_samples is None:
            session.execute(delete(Patient).where(Patient.id == patient_id))
    session.flush()
    if id_store_path is not None:
        with suppress(FileNotFoundError):
            id_store_path.unlink()


def _get_or_create_departments(session: Session) -> dict[str, Department]:
    departments: dict[str, Department] = {}
    for name in _DEPARTMENT_NAMES:
        department = session.execute(select(Department).where(Department.name == name)).scalar_one_or_none()
        if department is None:
            department = Department(name=name)
            session.add(department)
        departments[name] = department
    session.flush()
    return departments


def _get_or_create_icd10(session: Session) -> dict[str, RefICD10]:
    refs: dict[str, RefICD10] = {}
    for code, title in _ICD10.items():
        ref = session.get(RefICD10, code)
        if ref is None:
            ref = RefICD10(code=code, title=title, is_active=True)
            session.add(ref)
        refs[code] = ref
    session.flush()
    return refs


def _get_or_create_materials(session: Session) -> dict[str, RefMaterialType]:
    refs: dict[str, RefMaterialType] = {}
    for code, name in _MATERIALS.items():
        ref = session.execute(select(RefMaterialType).where(RefMaterialType.code == code)).scalar_one_or_none()
        if ref is None:
            ref = RefMaterialType(code=code, name=name)
            session.add(ref)
        refs[code] = ref
    session.flush()
    return refs


def _get_or_create_microbes(session: Session) -> dict[str, RefMicroorganism]:
    refs: dict[str, RefMicroorganism] = {}
    for code, (name, taxon_group) in _MICROBES.items():
        ref = session.execute(select(RefMicroorganism).where(RefMicroorganism.code == code)).scalar_one_or_none()
        if ref is None:
            ref = RefMicroorganism(code=code, name=name, taxon_group=taxon_group, is_active=True)
            session.add(ref)
        refs[code] = ref
    session.flush()
    return refs


def _get_or_create_antibiotics(session: Session) -> tuple[dict[str, RefAntibioticGroup], dict[str, RefAntibiotic]]:
    groups: dict[str, RefAntibioticGroup] = {}
    for code, name in _ABX_GROUPS.items():
        group = session.execute(
            select(RefAntibioticGroup).where(RefAntibioticGroup.code == code)
        ).scalar_one_or_none()
        if group is None:
            group = RefAntibioticGroup(code=code, name=name)
            session.add(group)
        groups[code] = group
    session.flush()

    antibiotics: dict[str, RefAntibiotic] = {}
    for item in _ABX:
        code = item["code"]
        antibiotic = session.execute(select(RefAntibiotic).where(RefAntibiotic.code == code)).scalar_one_or_none()
        group = groups[item["group_code"]]
        if antibiotic is None:
            antibiotic = RefAntibiotic(code=code, name=item["name"], group_id=group.id)
            session.add(antibiotic)
        antibiotics[code] = antibiotic
    session.flush()
    return groups, antibiotics


def _create_patients(session: Session) -> list[Patient]:
    patients: list[Patient] = []
    for index, item in enumerate(_PATIENTS):
        full_name = f"{item['last_name']} {item['first_name']} {item['middle_name']}"
        patient = Patient(
            full_name=full_name,
            dob=_parse_date(item["birth_date"]),
            sex=item["gender"],
            category="hospital" if index % 2 == 0 else "outpatient",
        )
        session.add(patient)
        patients.append(patient)
    session.flush()
    return patients


def _create_emr_cases(
    session: Session,
    *,
    patients: Sequence[Patient],
    departments: dict[str, Department],
    icd10_refs: dict[str, RefICD10],
    today: date,
    run_tag: str,
    rng: random.Random,
) -> list[DemoCase]:
    cases: list[DemoCase] = []
    patient_department_names = ("Терапия", "Хирургия", "Реанимация (ОРИТ)", "Неврология", "Терапия")
    icd_codes = list(icd10_refs)

    for patient_index, patient in enumerate(patients):
        department = departments[patient_department_names[patient_index % len(patient_department_names)]]
        for case_offset in range(3):
            index = len(cases)
            admission_date = today - timedelta(days=rng.randint(3, 88))
            length_of_stay = rng.randint(4, 18)
            outcome_date = min(today, admission_date + timedelta(days=length_of_stay))
            case = EmrCase(
                patient_id=patient.id,
                hospital_case_no=f"DEMO-{run_tag}-{index + 1:03d}",
                department_id=department.id,
            )
            session.add(case)
            session.flush()

            version = EmrCaseVersion(
                emr_case_id=case.id,
                version_no=1,
                valid_from=_as_dt(admission_date, hour=8),
                is_current=True,
                admission_date=_as_dt(admission_date, hour=9),
                outcome_date=_as_dt(outcome_date, hour=12),
                outcome_type="discharge",
                severity=("mild", "moderate", "severe")[case_offset % 3],
                sofa_score=index % 8,
                length_of_stay_days=max(1, (outcome_date - admission_date).days),
            )
            session.add(version)
            session.flush()

            diagnosis_code = icd_codes[index % len(icd_codes)]
            session.add(
                EmrDiagnosis(
                    emr_case_version_id=version.id,
                    kind="admission",
                    icd10_code=diagnosis_code,
                    free_text=cast(str, icd10_refs[diagnosis_code].title),
                )
            )
            cases.append(DemoCase(case=case, version=version, department=department))
    session.flush()
    return cases


def _sample_date_for_case(demo_case: DemoCase, today: date, rng: random.Random) -> date:
    admission_dt = cast(datetime, demo_case.version.admission_date)
    admission = admission_dt.date()
    stay_days = max(1, cast(int, demo_case.version.length_of_stay_days) or 1)
    return min(today, admission + timedelta(days=rng.randint(0, stay_days)))


def _create_lab_samples(
    session: Session,
    *,
    demo_cases: Sequence[DemoCase],
    materials: dict[str, RefMaterialType],
    microbes: dict[str, RefMicroorganism],
    antibiotics: dict[str, RefAntibiotic],
    today: date,
    run_tag: str,
    rng: random.Random,
) -> tuple[int, int]:
    material_refs = list(materials.values())
    microbe_refs = list(microbes.values())
    sample_count = 0
    positive_count = 0

    for case_index, demo_case in enumerate(demo_cases):
        samples_for_case = (3, 2, 2)[case_index % 3]
        for _ in range(samples_for_case):
            sample_count += 1
            material = material_refs[(sample_count - 1) % len(material_refs)]
            taken_date = _sample_date_for_case(demo_case, today, rng)
            positive = sample_count % 6 not in {0, 5}
            sample = LabSample(
                patient_id=demo_case.case.patient_id,
                emr_case_id=demo_case.case.id,
                lab_no=f"DEMO-LAB-{run_tag}-{sample_count:03d}",
                material_type_id=material.id,
                material_location="отделение",
                medium="агар",
                study_kind="primary",
                ordered_at=_as_dt(taken_date, hour=8),
                taken_at=_as_dt(taken_date, hour=9),
                delivered_at=_as_dt(taken_date, hour=11),
                growth_result_at=_as_dt(min(today, taken_date + timedelta(days=1)), hour=12),
                growth_flag=1 if positive else 0,
                colony_desc="рост микрофлоры" if positive else "рост не выявлен",
                microscopy="лейкоциты, бактерии" if positive else "без особенностей",
                cfu="10^5" if positive else None,
                qc_status="valid",
            )
            session.add(sample)
            session.flush()

            if positive:
                positive_count += 1
                microbe = microbe_refs[(sample_count - 1) % len(microbe_refs)]
                session.add(LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=microbe.id))
                for abx_index, abx_item in enumerate(_ABX):
                    antibiotic = antibiotics[abx_item["code"]]
                    ris = _RIS_WEIGHTS[((positive_count - 1) * len(_ABX) + abx_index) % len(_RIS_WEIGHTS)]
                    session.add(
                        LabAbxSusceptibility(
                            lab_sample_id=sample.id,
                            antibiotic_id=antibiotic.id,
                            group_id=antibiotic.group_id,
                            ris=ris,
                            method="disk",
                        )
                    )
    session.flush()
    return sample_count, positive_count


def _create_resistance_anchor_samples(
    session: Session,
    *,
    demo_cases: Sequence[DemoCase],
    materials: dict[str, RefMaterialType],
    microbes: dict[str, RefMicroorganism],
    antibiotics: dict[str, RefAntibiotic],
    today: date,
    run_tag: str,
    rng: random.Random,
) -> int:
    cases_by_patient: dict[int, list[DemoCase]] = {}
    for demo_case in demo_cases:
        patient_id = cast(int | None, demo_case.case.patient_id)
        if patient_id is None:
            continue
        cases_by_patient.setdefault(patient_id, []).append(demo_case)

    if not cases_by_patient:
        return 0

    blood = materials["BLD"]
    patient_ids = sorted(cases_by_patient)
    anchor_count = 0

    for microbe_code, _microbe_name, antibiotic_code, _antibiotic_name, ris_values in _RESISTANCE_ANCHORS:
        microbe = microbes[microbe_code]
        antibiotic = antibiotics[antibiotic_code]
        for ris in ris_values:
            patient_id = rng.choice(patient_ids)
            demo_case = rng.choice(cases_by_patient[patient_id])
            anchor_count += 1
            taken_date = _sample_date_for_case(demo_case, today, rng)
            sample = LabSample(
                patient_id=demo_case.case.patient_id,
                emr_case_id=demo_case.case.id,
                lab_no=f"DEMO-LAB-{run_tag}-R{anchor_count:03d}",
                material_type_id=blood.id,
                material_location="отделение",
                medium="агар",
                study_kind="primary",
                ordered_at=_as_dt(taken_date, hour=8),
                taken_at=_as_dt(taken_date, hour=9),
                delivered_at=_as_dt(taken_date, hour=11),
                growth_result_at=_as_dt(min(today, taken_date + timedelta(days=1)), hour=12),
                growth_flag=1,
                colony_desc="рост микрофлоры",
                microscopy="лейкоциты, бактерии",
                cfu="10^5",
                qc_status="valid",
            )
            session.add(sample)
            session.flush()
            session.add(LabMicrobeIsolation(lab_sample_id=sample.id, microorganism_id=microbe.id))
            session.add(
                LabAbxSusceptibility(
                    lab_sample_id=sample.id,
                    antibiotic_id=antibiotic.id,
                    group_id=antibiotic.group_id,
                    ris=ris,
                    method="disk",
                )
            )

    session.flush()
    return anchor_count


def _create_ismp_cases(session: Session, *, demo_cases: Sequence[DemoCase], rng: random.Random) -> int:
    eligible = [
        demo_case
        for demo_case in demo_cases
        if cast(str, demo_case.department.name) in {"Реанимация (ОРИТ)", "Хирургия"}
    ]
    ismp_types = [
        IsmpType.CA_BSI.value,
        IsmpType.VAP.value,
        IsmpType.CA_UTI.value,
        IsmpType.SSI.value,
    ]
    for index, demo_case in enumerate(eligible[:4]):
        admission_dt = cast(datetime, demo_case.version.admission_date)
        admission = admission_dt.date()
        stay_days = max(1, cast(int, demo_case.version.length_of_stay_days) or 1)
        start_date = admission + timedelta(days=rng.randint(1, stay_days))
        session.add(
            IsmpCase(
                emr_case_id=demo_case.case.id,
                ismp_type=ismp_types[index % len(ismp_types)],
                start_date=start_date,
            )
        )
    session.flush()
    return min(4, len(eligible))


def _create_sanitary_samples(
    session: Session,
    *,
    departments: dict[str, Department],
    microbes: dict[str, RefMicroorganism],
    today: date,
    run_tag: str,
    rng: random.Random,
) -> int:
    department_refs = list(departments.values())
    microbe_refs = list(microbes.values())
    for index in range(8):
        department = department_refs[index % len(department_refs)]
        taken_date = today - timedelta(days=rng.randint(1, 88))
        non_compliant = index % 3 == 0
        sample = SanitarySample(
            department_id=department.id,
            room=("операционная", "перевязочная", "палата")[index % 3],
            sampling_point=_SANITARY_OBJECTS[index % len(_SANITARY_OBJECTS)],
            lab_no=f"DEMO-SAN-{run_tag}-{index + 1:03d}",
            medium="агар",
            ordered_at=_as_dt(taken_date, hour=8),
            taken_at=_as_dt(taken_date, hour=9),
            delivered_at=_as_dt(taken_date, hour=10),
            growth_result_at=_as_dt(min(today, taken_date + timedelta(days=1)), hour=12),
            growth_flag=1 if non_compliant else 0,
            colony_desc="не соответствует" if non_compliant else "соответствует",
            microscopy="единичные колонии" if non_compliant else "рост не выявлен",
            cfu="10^2" if non_compliant else None,
        )
        session.add(sample)
        session.flush()
        if non_compliant:
            microbe = microbe_refs[index % len(microbe_refs)]
            session.add(SanMicrobeIsolation(sanitary_sample_id=sample.id, microorganism_id=microbe.id))
    session.flush()
    return 8


def seed(session: Session, *, clear: bool = False, id_store_path: Path | None = None) -> SeedStats:
    """Fill the current database session with demo analytics data."""

    if clear:
        _clear_data(session, id_store_path=id_store_path)

    rng = random.Random(20260518)
    now = datetime.now(UTC)
    today = now.date()
    run_tag = now.strftime("%Y%m%d%H%M%S")

    departments = _get_or_create_departments(session)
    icd10_refs = _get_or_create_icd10(session)
    materials = _get_or_create_materials(session)
    microbes = _get_or_create_microbes(session)
    _, antibiotics = _get_or_create_antibiotics(session)

    patients = _create_patients(session)
    demo_cases = _create_emr_cases(
        session,
        patients=patients,
        departments=departments,
        icd10_refs=icd10_refs,
        today=today,
        run_tag=run_tag,
        rng=rng,
    )
    lab_samples, positive_lab_samples = _create_lab_samples(
        session,
        demo_cases=demo_cases,
        materials=materials,
        microbes=microbes,
        antibiotics=antibiotics,
        today=today,
        run_tag=run_tag,
        rng=rng,
    )
    resistance_anchor_samples = _create_resistance_anchor_samples(
        session,
        demo_cases=demo_cases,
        materials=materials,
        microbes=microbes,
        antibiotics=antibiotics,
        today=today,
        run_tag=run_tag,
        rng=rng,
    )
    lab_samples += resistance_anchor_samples
    positive_lab_samples += resistance_anchor_samples
    ismp_cases = _create_ismp_cases(session, demo_cases=demo_cases, rng=rng)
    sanitary_samples = _create_sanitary_samples(
        session,
        departments=departments,
        microbes=microbes,
        today=today,
        run_tag=run_tag,
        rng=rng,
    )
    _write_demo_ids(session, id_store_path, run_tag=run_tag)

    return SeedStats(
        patients=len(patients),
        emr_cases=len(demo_cases),
        lab_samples=lab_samples,
        positive_lab_samples=positive_lab_samples,
        resistance_anchor_samples=resistance_anchor_samples,
        ismp_cases=ismp_cases,
        sanitary_samples=sanitary_samples,
    )


def _format_stats(stats: SeedStats) -> str:
    return (
        "OK Seed завершён:\n"
        f"  Пациентов: {stats.patients}\n"
        f"  ЭМЗ / госпитализаций: {stats.emr_cases}\n"
        f"  Лабораторных проб: {stats.lab_samples} "
        f"(из них положительных: {stats.positive_lab_samples})\n"
        f"  Resistance anchors: {stats.resistance_anchor_samples} доп. проб "
        f"({len(_RESISTANCE_ANCHORS)} пары микроорганизм×антибиотик)\n"
        f"  ИСМП случаев: {stats.ismp_cases}\n"
        f"  Санитарных проб: {stats.sanitary_samples}"
    )


def _configure_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(
        description="Наполнить БД демонстрационными данными для проверки аналитики."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Очистить только demo-данные пациентов/ЭМЗ/лабпроб/ИСМП/санпроб и выйти.",
    )
    args = parser.parse_args(argv)

    with session_scope() as session:
        if args.clear:
            _clear_data(session, id_store_path=_DEMO_ID_STORE)
            stats = None
        else:
            stats = seed(session, clear=True, id_store_path=_DEMO_ID_STORE)

    print(f"База данных: {DB_FILE}")
    if stats is None:
        print("OK Demo-данные очищены.")
    else:
        print(_format_stats(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
