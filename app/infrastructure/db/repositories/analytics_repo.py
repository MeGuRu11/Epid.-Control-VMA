from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import (
    Department,
    EmrCase,
    EmrCaseVersion,
    EmrDiagnosis,
    IsmpCase,
    LabAbxSusceptibility,
    LabMicrobeIsolation,
    LabSample,
    Patient,
    PatientsFts,
    RefAntibiotic,
    RefIcd10Fts,
    RefMaterialType,
    RefMicroorganism,
    RefMicroorganismsFts,
)


class AnalyticsRepository:
    @staticmethod
    def _date_floor(value: date) -> datetime:
        return datetime.combine(value, datetime.min.time())

    @staticmethod
    def _date_ceiling_exclusive(value: date) -> datetime:
        return datetime.combine(value + timedelta(days=1), datetime.min.time())

    def _build_filtered_sample_ids_subquery(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        department_id: int | None,
        icd10_code: str | None,
        microorganism_id: int | None,
        antibiotic_id: int | None,
        material_type_id: int | None,
        growth_flag: int | None,
        patient_category: str | None,
        patient_name: str | None,
        lab_no: str | None,
        search_text: str | None,
    ):
        stmt = (
            select(LabSample.id.label("sample_id"))
            .select_from(LabSample)
            .join(Patient, Patient.id == LabSample.patient_id)
            .outerjoin(EmrCase, EmrCase.id == LabSample.emr_case_id)
        )

        if date_from:
            stmt = stmt.where(LabSample.taken_at >= self._date_floor(date_from))
        if date_to:
            stmt = stmt.where(LabSample.taken_at < self._date_ceiling_exclusive(date_to))
        if department_id:
            stmt = stmt.where(EmrCase.department_id == department_id)
        if material_type_id:
            stmt = stmt.where(LabSample.material_type_id == material_type_id)
        if growth_flag is not None:
            stmt = stmt.where(LabSample.growth_flag == growth_flag)
        if patient_category:
            stmt = stmt.where(Patient.category == patient_category)
        if patient_name:
            stmt = stmt.where(Patient.full_name.ilike(f"%{patient_name}%"))
        if lab_no:
            stmt = stmt.where(LabSample.lab_no.ilike(f"%{lab_no}%"))

        if microorganism_id:
            micro_match = (
                select(LabMicrobeIsolation.id)
                .where(
                    LabMicrobeIsolation.lab_sample_id == LabSample.id,
                    LabMicrobeIsolation.microorganism_id == microorganism_id,
                )
                .exists()
            )
            stmt = stmt.where(micro_match)

        if antibiotic_id:
            abx_match = (
                select(LabAbxSusceptibility.id)
                .where(
                    LabAbxSusceptibility.lab_sample_id == LabSample.id,
                    LabAbxSusceptibility.antibiotic_id == antibiotic_id,
                )
                .exists()
            )
            stmt = stmt.where(abx_match)

        if search_text:
            patient_ids = select(PatientsFts.c.patient_id).where(PatientsFts.c.full_name.match(search_text))
            micro_ids = select(RefMicroorganismsFts.c.microorganism_id).where(
                RefMicroorganismsFts.c.name.match(search_text)
            )
            icd_codes = select(RefIcd10Fts.c.code).where(RefIcd10Fts.c.title.match(search_text))

            micro_match = (
                select(LabMicrobeIsolation.id)
                .where(
                    LabMicrobeIsolation.lab_sample_id == LabSample.id,
                    LabMicrobeIsolation.microorganism_id.in_(micro_ids),
                )
                .exists()
            )
            icd_match = (
                select(EmrDiagnosis.id)
                .select_from(EmrCaseVersion)
                .join(EmrDiagnosis, EmrDiagnosis.emr_case_version_id == EmrCaseVersion.id)
                .where(
                    EmrCaseVersion.emr_case_id == LabSample.emr_case_id,
                    EmrCaseVersion.is_current == True,  # noqa: E712
                    EmrDiagnosis.icd10_code.in_(icd_codes),
                )
                .exists()
            )
            stmt = stmt.where(or_(Patient.id.in_(patient_ids), micro_match, icd_match))

        if icd10_code:
            icd_filter = (
                select(EmrDiagnosis.id)
                .select_from(EmrCaseVersion)
                .join(EmrDiagnosis, EmrDiagnosis.emr_case_version_id == EmrCaseVersion.id)
                .where(
                    EmrCaseVersion.emr_case_id == LabSample.emr_case_id,
                    EmrCaseVersion.is_current == True,  # noqa: E712
                    EmrDiagnosis.icd10_code == icd10_code,
                )
                .exists()
            )
            stmt = stmt.where(icd_filter)

        return stmt.distinct().subquery()

    def get_department_summary(
        self,
        session: Session,
        date_from: date | None,
        date_to: date | None,
        patient_category: str | None,
    ) -> list[dict]:
        stmt = (
            select(
                Department.id.label("department_id"),
                Department.name.label("department_name"),
                func.count(LabSample.id).label("total"),
                func.sum(case((LabSample.growth_flag == 1, 1), else_=0)).label("positives"),
                func.max(LabSample.taken_at).label("last_date"),
            )
            .select_from(LabSample)
            .join(Patient, Patient.id == LabSample.patient_id)
            .outerjoin(EmrCase, EmrCase.id == LabSample.emr_case_id)
            .outerjoin(Department, Department.id == EmrCase.department_id)
            .group_by(Department.id, Department.name)
        )
        if date_from:
            stmt = stmt.where(LabSample.taken_at >= self._date_floor(date_from))
        if date_to:
            stmt = stmt.where(LabSample.taken_at < self._date_ceiling_exclusive(date_to))
        if patient_category:
            stmt = stmt.where(Patient.category == patient_category)
        rows = session.execute(stmt).all()
        result = []
        for row in rows:
            total = row.total or 0
            positives = row.positives or 0
            share = (positives / total) if total else 0
            result.append(
                {
                    "department_id": row.department_id,
                    "department_name": row.department_name or "Без отделения",
                    "total": total,
                    "positives": positives,
                    "positive_share": share,
                    "last_date": row.last_date,
                }
            )
        return result

    def get_trend_by_day(
        self,
        session: Session,
        date_from: date | None,
        date_to: date | None,
        patient_category: str | None,
    ) -> list[dict]:
        day_col = func.date(LabSample.taken_at).label("day")
        stmt = (
            select(
                day_col,
                func.count(LabSample.id).label("total"),
                func.sum(case((LabSample.growth_flag == 1, 1), else_=0)).label("positives"),
            )
            .select_from(LabSample)
            .join(Patient, Patient.id == LabSample.patient_id)
            .group_by(day_col)
            .order_by(day_col.asc())
        )
        if date_from:
            stmt = stmt.where(LabSample.taken_at >= self._date_floor(date_from))
        if date_to:
            stmt = stmt.where(LabSample.taken_at < self._date_ceiling_exclusive(date_to))
        if patient_category:
            stmt = stmt.where(Patient.category == patient_category)
        rows = session.execute(stmt).all()
        result = []
        for row in rows:
            result.append(
                {
                    "day": row.day,
                    "total": row.total or 0,
                    "positives": row.positives or 0,
                }
            )
        return result

    def get_aggregate_counts(
        self, session: Session, date_from: date, date_to: date, patient_category: str | None
    ) -> dict:
        stmt = select(
            func.count(LabSample.id).label("total"),
            func.sum(case((LabSample.growth_flag == 1, 1), else_=0)).label("positives"),
        ).select_from(LabSample).join(Patient, Patient.id == LabSample.patient_id)
        stmt = stmt.where(
            LabSample.taken_at >= self._date_floor(date_from),
            LabSample.taken_at < self._date_ceiling_exclusive(date_to),
        )
        if patient_category:
            stmt = stmt.where(Patient.category == patient_category)
        row = session.execute(stmt).one()
        total = row.total or 0
        positives = row.positives or 0
        share = (positives / total) if total else 0
        return {"total": total, "positives": positives, "positive_share": share}

    def get_ismp_metrics(
        self,
        session: Session,
        date_from: date | None,
        date_to: date | None,
        department_id: int | None,
    ) -> dict:
        case_stmt = (
            select(
                func.count(EmrCase.id).label("total_cases"),
                func.sum(EmrCaseVersion.length_of_stay_days).label("total_patient_days"),
            )
            .select_from(EmrCaseVersion)
            .join(EmrCase, EmrCase.id == EmrCaseVersion.emr_case_id)
            .where(EmrCaseVersion.is_current == True)  # noqa: E712
        )
        if date_from:
            case_stmt = case_stmt.where(EmrCaseVersion.admission_date >= self._date_floor(date_from))
        if date_to:
            case_stmt = case_stmt.where(EmrCaseVersion.admission_date < self._date_ceiling_exclusive(date_to))
        if department_id:
            case_stmt = case_stmt.where(EmrCase.department_id == department_id)
        case_row = session.execute(case_stmt).one()
        total_cases = case_row.total_cases or 0
        total_patient_days = case_row.total_patient_days or 0

        ismp_stmt = (
            select(
                func.count(IsmpCase.id).label("ismp_total"),
                func.count(func.distinct(IsmpCase.emr_case_id)).label("ismp_cases"),
            )
            .select_from(IsmpCase)
            .join(EmrCase, EmrCase.id == IsmpCase.emr_case_id)
        )
        if date_from:
            ismp_stmt = ismp_stmt.where(IsmpCase.start_date >= date_from)
        if date_to:
            ismp_stmt = ismp_stmt.where(IsmpCase.start_date <= date_to)
        if department_id:
            ismp_stmt = ismp_stmt.where(EmrCase.department_id == department_id)
        ismp_row = session.execute(ismp_stmt).one()
        ismp_total = ismp_row.ismp_total or 0
        ismp_cases = ismp_row.ismp_cases or 0

        type_stmt = select(
            IsmpCase.ismp_type,
            func.count(IsmpCase.id).label("count_value"),
        ).select_from(IsmpCase).join(EmrCase, EmrCase.id == IsmpCase.emr_case_id)
        if date_from:
            type_stmt = type_stmt.where(IsmpCase.start_date >= date_from)
        if date_to:
            type_stmt = type_stmt.where(IsmpCase.start_date <= date_to)
        if department_id:
            type_stmt = type_stmt.where(EmrCase.department_id == department_id)
        type_stmt = type_stmt.group_by(IsmpCase.ismp_type).order_by(IsmpCase.ismp_type.asc())
        by_type = [
            {
                "type": row.ismp_type,
                "count": int(row.count_value) if row.count_value is not None else 0,
            }
            for row in session.execute(type_stmt).all()
        ]

        return {
            "total_cases": total_cases,
            "total_patient_days": total_patient_days,
            "ismp_total": ismp_total,
            "ismp_cases": ismp_cases,
            "by_type": by_type,
        }

    def search_samples(
        self,
        session: Session,
        *,
        date_from: date | None,
        date_to: date | None,
        department_id: int | None,
        icd10_code: str | None,
        microorganism_id: int | None,
        antibiotic_id: int | None,
        material_type_id: int | None,
        growth_flag: int | None,
        patient_category: str | None,
        patient_name: str | None,
        lab_no: str | None,
        search_text: str | None,
    ):
        filtered = self._build_filtered_sample_ids_subquery(
            date_from=date_from,
            date_to=date_to,
            department_id=department_id,
            icd10_code=icd10_code,
            microorganism_id=microorganism_id,
            antibiotic_id=antibiotic_id,
            material_type_id=material_type_id,
            growth_flag=growth_flag,
            patient_category=patient_category,
            patient_name=patient_name,
            lab_no=lab_no,
            search_text=search_text,
        )
        micro_label = (
            select(func.coalesce(RefMicroorganism.code, "-") + " - " + RefMicroorganism.name)
            .select_from(LabMicrobeIsolation)
            .join(RefMicroorganism, RefMicroorganism.id == LabMicrobeIsolation.microorganism_id)
            .where(LabMicrobeIsolation.lab_sample_id == LabSample.id)
            .order_by(LabMicrobeIsolation.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        abx_label = (
            select(func.coalesce(RefAntibiotic.code, "-") + " - " + RefAntibiotic.name)
            .select_from(LabAbxSusceptibility)
            .join(RefAntibiotic, RefAntibiotic.id == LabAbxSusceptibility.antibiotic_id)
            .where(LabAbxSusceptibility.lab_sample_id == LabSample.id)
            .order_by(LabAbxSusceptibility.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(
                LabSample,
                Patient,
                EmrCase,
                Department,
                RefMaterialType,
                micro_label.label("microorganism"),
                abx_label.label("antibiotic"),
            )
            .select_from(LabSample)
            .join(filtered, filtered.c.sample_id == LabSample.id)
            .join(Patient, Patient.id == LabSample.patient_id)
            .outerjoin(EmrCase, EmrCase.id == LabSample.emr_case_id)
            .outerjoin(Department, Department.id == EmrCase.department_id)
            .outerjoin(RefMaterialType, RefMaterialType.id == LabSample.material_type_id)
            .order_by(LabSample.taken_at.desc())
        )
        return list(session.execute(stmt).all())

    def get_aggregates(
        self,
        session: Session,
        *,
        date_from: date | None,
        date_to: date | None,
        department_id: int | None,
        icd10_code: str | None,
        microorganism_id: int | None,
        antibiotic_id: int | None,
        material_type_id: int | None,
        growth_flag: int | None,
        patient_category: str | None,
        patient_name: str | None,
        lab_no: str | None,
        search_text: str | None,
    ) -> dict:
        filtered = self._build_filtered_sample_ids_subquery(
            date_from=date_from,
            date_to=date_to,
            department_id=department_id,
            icd10_code=icd10_code,
            microorganism_id=microorganism_id,
            antibiotic_id=antibiotic_id,
            material_type_id=material_type_id,
            growth_flag=growth_flag,
            patient_category=patient_category,
            patient_name=patient_name,
            lab_no=lab_no,
            search_text=search_text,
        )

        counts_stmt = (
            select(
                func.count(LabSample.id).label("total"),
                func.sum(case((LabSample.growth_flag == 1, 1), else_=0)).label("positives"),
            )
            .select_from(LabSample)
            .join(filtered, filtered.c.sample_id == LabSample.id)
        )
        counts_row = session.execute(counts_stmt).one()
        total = int(counts_row.total or 0)
        positives = int(counts_row.positives or 0)
        positive_share = (positives / total) if total else 0.0

        micro_label = (func.coalesce(RefMicroorganism.code, "-") + " - " + RefMicroorganism.name).label(
            "microorganism"
        )
        top_stmt = (
            select(micro_label, func.count(LabMicrobeIsolation.id).label("count_value"))
            .select_from(LabMicrobeIsolation)
            .join(filtered, filtered.c.sample_id == LabMicrobeIsolation.lab_sample_id)
            .join(RefMicroorganism, RefMicroorganism.id == LabMicrobeIsolation.microorganism_id)
            .group_by(micro_label)
            .order_by(func.count(LabMicrobeIsolation.id).desc())
            .limit(5)
        )
        top_microbes = [(str(row.microorganism), int(row.count_value)) for row in session.execute(top_stmt).all()]

        return {
            "total": total,
            "positives": positives,
            "positive_share": positive_share,
            "top_microbes": top_microbes,
        }
