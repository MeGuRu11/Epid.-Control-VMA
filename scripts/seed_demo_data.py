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
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_FILE  # noqa: E402
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
    {"code": "AMP", "name": "Ампициллин", "group_code": "PEN", "ris": "R"},
    {"code": "CRO", "name": "Цефтриаксон", "group_code": "CEF", "ris": "S"},
    {"code": "CIP", "name": "Ципрофлоксацин", "group_code": "FQ", "ris": "I"},
    {"code": "MEM", "name": "Меропенем", "group_code": "CARB", "ris": "S"},
    {"code": "VAN", "name": "Ванкомицин", "group_code": "GLY", "ris": "S"},
]

_SANITARY_OBJECTS = (
    "Воздух операционной",
    "Смыв со стола",
    "Поверхность медоборудования",
)


def _as_dt(value: date, *, hour: int = 9, minute: int = 0) -> datetime:
    return datetime.combine(value, time(hour=hour, minute=minute))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _clear_data(session: Session) -> None:
    for model in (
        SanAbxSusceptibility,
        SanPhagePanelResult,
        SanMicrobeIsolation,
        SanitarySample,
        LabAbxSusceptibility,
        LabPhagePanelResult,
        LabMicrobeIsolation,
        LabSample,
        IsmpCase,
        EmrAntibioticCourse,
        EmrIntervention,
        EmrDiagnosis,
        EmrCaseVersion,
        EmrCase,
        Patient,
    ):
        session.execute(delete(model))
    session.flush()


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
    department_cycle = [departments[name] for name in _DEPARTMENT_NAMES]
    icd_codes = list(icd10_refs)

    for index in range(12):
        patient = patients[index % len(patients)]
        department = department_cycle[index % len(department_cycle)]
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
            severity=("mild", "moderate", "severe")[index % 3],
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
        samples_for_case = 3 if case_index < 4 else 2
        for _ in range(samples_for_case):
            sample_count += 1
            material = material_refs[(sample_count - 1) % len(material_refs)]
            taken_date = _sample_date_for_case(demo_case, today, rng)
            positive = sample_count % 10 not in {0, 8, 9}
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
                for abx_item in _ABX:
                    antibiotic = antibiotics[abx_item["code"]]
                    session.add(
                        LabAbxSusceptibility(
                            lab_sample_id=sample.id,
                            antibiotic_id=antibiotic.id,
                            group_id=antibiotic.group_id,
                            ris=abx_item["ris"],
                            method="disk",
                        )
                    )
    session.flush()
    return sample_count, positive_count


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
    for index in range(7):
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
    return 7


def seed(session: Session, *, clear: bool = False) -> SeedStats:
    """Fill the current database session with demo analytics data."""

    if clear:
        _clear_data(session)

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
    ismp_cases = _create_ismp_cases(session, demo_cases=demo_cases, rng=rng)
    sanitary_samples = _create_sanitary_samples(
        session,
        departments=departments,
        microbes=microbes,
        today=today,
        run_tag=run_tag,
        rng=rng,
    )

    return SeedStats(
        patients=len(patients),
        emr_cases=len(demo_cases),
        lab_samples=lab_samples,
        positive_lab_samples=positive_lab_samples,
        ismp_cases=ismp_cases,
        sanitary_samples=sanitary_samples,
    )


def _format_stats(stats: SeedStats) -> str:
    return (
        "✓ Seed завершён:\n"
        f"  Пациентов: {stats.patients}\n"
        f"  ЭМЗ / госпитализаций: {stats.emr_cases}\n"
        f"  Лабораторных проб: {stats.lab_samples} "
        f"(из них положительных: {stats.positive_lab_samples})\n"
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
        help="Очистить данные пациентов/ЭМЗ/лабпроб/ИСМП/санпроб перед заполнением.",
    )
    args = parser.parse_args(argv)

    with session_scope() as session:
        stats = seed(session, clear=bool(args.clear))

    print(f"База данных: {DB_FILE}")
    print(_format_stats(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
