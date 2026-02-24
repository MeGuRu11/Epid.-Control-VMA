from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, cast

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import Patient


class PatientRepository:
    def find_by_identity(self, session: Session, full_name: str, dob: date | None) -> Patient | None:
        stmt = select(Patient).where(Patient.full_name == full_name)
        if dob:
            stmt = stmt.where(Patient.dob == dob)
        return session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, session: Session, patient_id: int) -> Patient | None:
        return session.get(Patient, patient_id)

    def create(
        self,
        session: Session,
        *,
        full_name: str,
        dob: date | None,
        sex: str,
        category: str | None,
        military_unit: str | None,
        military_district: str | None,
    ) -> Patient:
        patient = Patient(
            full_name=full_name,
            dob=dob,
            sex=sex,
            category=category,
            military_unit=military_unit,
            military_district=military_district,
        )
        session.add(patient)
        session.flush()
        return patient

    def search_by_name(self, session: Session, query: str, limit: int = 10) -> list[Patient]:
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
                            SELECT patient_id
                            FROM patients_fts
                            WHERE patients_fts MATCH :q
                            ORDER BY bm25(patients_fts)
                            LIMIT :limit
                            """
                        ),
                        {"q": fts_query, "limit": limit},
                    )
                    if row[0] is not None
                ]
                if ids:
                    patients = list(session.execute(select(Patient).where(Patient.id.in_(ids))).scalars())
                    by_id = {cast(int, p.id): p for p in patients}
                    return [by_id[i] for i in ids if i in by_id]
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).debug("FTS search_by_name failed", exc_info=True)

        stmt = (
            select(Patient)
            .where(Patient.full_name.ilike(f"%{clean}%"))
            .order_by(Patient.full_name)
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def list_recent(self, session: Session, limit: int = 10) -> list[Patient]:
        stmt = (
            select(Patient)
            .order_by(Patient.created_at.desc(), Patient.id.desc())
            .limit(limit)
        )
        return list(session.execute(stmt).scalars())

    def update_category(self, session: Session, patient_id: int, category: str) -> None:
        patient = session.get(Patient, patient_id)
        if patient:
            patient_obj = cast(Any, patient)
            patient_obj.category = category

    def update_details(
        self,
        session: Session,
        patient_id: int,
        *,
        full_name: str | None = None,
        dob: date | None = None,
        sex: str | None = None,
        category: str | None,
        military_unit: str | None,
        military_district: str | None,
    ) -> None:
        patient = session.get(Patient, patient_id)
        if patient:
            patient_obj = cast(Any, patient)
            if full_name is not None:
                patient_obj.full_name = full_name
            if sex is not None:
                patient_obj.sex = sex
            patient_obj.dob = dob
            if category is not None:
                patient_obj.category = category
            patient_obj.military_unit = military_unit
            patient_obj.military_district = military_district
