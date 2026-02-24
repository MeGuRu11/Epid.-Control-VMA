from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.application.dto.patient_dto import PatientCreateRequest, PatientResponse
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import (
    AuditLog,
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
)
from app.infrastructure.db.repositories.patient_repo import PatientRepository
from app.infrastructure.db.session import session_scope


class PatientService:
    def __init__(
        self,
        patient_repo: PatientRepository | None = None,
        session_factory: Callable = session_scope,
        fts_manager: FtsManager | None = None,
    ) -> None:
        self.patient_repo = patient_repo or PatientRepository()
        self.session_factory = session_factory
        self.fts_manager = fts_manager or FtsManager(session_factory=session_factory)

    def _apply_identity_updates(self, existing_obj: Any, request: PatientCreateRequest) -> None:
        if existing_obj.category != request.category:
            existing_obj.category = request.category
        if request.military_unit is not None and existing_obj.military_unit != request.military_unit:
            existing_obj.military_unit = request.military_unit
        if request.military_district is not None and existing_obj.military_district != request.military_district:
            existing_obj.military_district = request.military_district

    def create_or_get(self, request: PatientCreateRequest) -> PatientResponse:
        with self.session_factory() as session:
            existing = self.patient_repo.find_by_identity(session, request.full_name, request.dob)
            if existing:
                existing_obj = cast(Any, existing)
                self._apply_identity_updates(existing_obj, request)
                try:
                    session.flush()
                except OperationalError as exc:
                    session.rollback()
                    logging.getLogger(__name__).warning(
                        "Update patient failed, attempting FTS repair: %s", exc
                    )
                    try:
                        self.fts_manager.ensure_patients(session)
                        existing_retry = self.patient_repo.get_by_id(session, cast(int, existing.id))
                        if existing_retry:
                            existing_obj = cast(Any, existing_retry)
                            self._apply_identity_updates(existing_obj, request)
                            session.flush()
                    except OperationalError:
                        session.rollback()
                        self.fts_manager.hard_reset_patients_fts(session)
                        self._update_patient_raw(
                            session,
                            cast(int, existing.id),
                            full_name=None,
                            dob=None,
                            sex=None,
                            category=request.category,
                            military_unit=request.military_unit,
                            military_district=request.military_district,
                        )
                        self.fts_manager.rebuild_patients_fts(session)
                patient_id = cast(int, existing.id)
                full_name = cast(str, existing.full_name)
                dob = cast("date | None", existing.dob)
                sex = cast(str, existing.sex)
                category = cast(str | None, existing.category)
                military_unit = cast(str | None, existing.military_unit)
                military_district = cast(str | None, existing.military_district)
                return PatientResponse(
                    id=patient_id,
                    full_name=full_name,
                    dob=dob,
                    sex=sex,
                    category=category,
                    military_unit=military_unit,
                    military_district=military_district,
                )

            patient = self.patient_repo.create(
                session,
                full_name=request.full_name,
                dob=request.dob,
                sex=request.sex,
                category=request.category,
                military_unit=request.military_unit,
                military_district=request.military_district,
            )
            patient_id = cast(int, patient.id)
            full_name = cast(str, patient.full_name)
            dob = cast("date | None", patient.dob)
            sex = cast(str, patient.sex)
            category = cast(str | None, patient.category)
            military_unit = cast(str | None, patient.military_unit)
            military_district = cast(str | None, patient.military_district)
            return PatientResponse(
                id=patient_id,
                full_name=full_name,
                dob=dob,
                sex=sex,
                category=category,
                military_unit=military_unit,
                military_district=military_district,
            )

    def get_by_id(self, patient_id: int) -> PatientResponse:
        with self.session_factory() as session:
            patient = self.patient_repo.get_by_id(session, patient_id)
            if not patient:
                raise ValueError("Пациент не найден")
            patient_id_value = cast(int, patient.id)
            full_name = cast(str, patient.full_name)
            dob = cast("date | None", patient.dob)
            sex = cast(str, patient.sex)
            category = cast(str | None, patient.category)
            military_unit = cast(str | None, patient.military_unit)
            military_district = cast(str | None, patient.military_district)
            return PatientResponse(
                id=patient_id_value,
                full_name=full_name,
                dob=dob,
                sex=sex,
                category=category,
                military_unit=military_unit,
                military_district=military_district,
            )

    def search_by_name(self, query: str, limit: int = 10) -> list[PatientResponse]:
        with self.session_factory() as session:
            patients = self.patient_repo.search_by_name(session, query, limit=limit)
            results: list[PatientResponse] = []
            for patient in patients:
                patient_id_value = cast(int, patient.id)
                full_name = cast(str, patient.full_name)
                dob = cast("date | None", patient.dob)
                sex = cast(str, patient.sex)
                category = cast(str | None, patient.category)
                military_unit = cast(str | None, patient.military_unit)
                military_district = cast(str | None, patient.military_district)
                results.append(
                    PatientResponse(
                        id=patient_id_value,
                        full_name=full_name,
                        dob=dob,
                        sex=sex,
                        category=category,
                        military_unit=military_unit,
                        military_district=military_district,
                    )
                )
            return results

    def list_recent(self, limit: int = 10) -> list[PatientResponse]:
        with self.session_factory() as session:
            patients = self.patient_repo.list_recent(session, limit=limit)
            results: list[PatientResponse] = []
            for patient in patients:
                patient_id_value = cast(int, patient.id)
                full_name = cast(str, patient.full_name)
                dob = cast("date | None", patient.dob)
                sex = cast(str, patient.sex)
                category = cast(str | None, patient.category)
                military_unit = cast(str | None, patient.military_unit)
                military_district = cast(str | None, patient.military_district)
                results.append(
                    PatientResponse(
                        id=patient_id_value,
                        full_name=full_name,
                        dob=dob,
                        sex=sex,
                        category=category,
                        military_unit=military_unit,
                        military_district=military_district,
                    )
                )
            return results

    def update_category(self, patient_id: int, category: str) -> None:
        with self.session_factory() as session:
            try:
                self.patient_repo.update_category(session, patient_id, category)
                session.flush()
            except OperationalError as exc:
                session.rollback()
                logging.getLogger(__name__).warning(
                    "Update patient failed, attempting FTS repair: %s", exc
                )
                with self.session_factory() as retry_session:
                    self.fts_manager.hard_reset_patients_fts(retry_session)
                    try:
                        self.patient_repo.update_category(retry_session, patient_id, category)
                        retry_session.flush()
                    except OperationalError:
                        retry_session.rollback()
                        self._repair_database_raw(retry_session)
                        try:
                            self.patient_repo.update_category(retry_session, patient_id, category)
                            retry_session.flush()
                        except OperationalError:
                            retry_session.rollback()
                            self.fts_manager.hard_reset_patients_fts(retry_session)
                            self._update_patient_raw(
                                retry_session,
                                patient_id,
                                full_name=None,
                                dob=None,
                                sex=None,
                                category=category,
                                military_unit=None,
                                military_district=None,
                            )
                            self.fts_manager.rebuild_patients_fts(retry_session)
                    try:
                        self.fts_manager.ensure_patients(retry_session)
                    except OperationalError:
                        logging.getLogger(__name__).warning(
                            "FTS rebuild failed after update_category", exc_info=True
                        )

    def update_details(
        self,
        patient_id: int,
        *,
        full_name: str | None,
        dob: date | None,
        sex: str | None,
        category: str | None,
        military_unit: str | None,
        military_district: str | None,
    ) -> None:
        with self.session_factory() as session:
            try:
                self.patient_repo.update_details(
                    session,
                    patient_id,
                    full_name=full_name,
                    dob=dob,
                    sex=sex,
                    category=category,
                    military_unit=military_unit,
                    military_district=military_district,
                )
                session.flush()
            except OperationalError as exc:
                session.rollback()
                logging.getLogger(__name__).warning(
                    "Update patient failed, attempting FTS repair: %s", exc
                )
                with self.session_factory() as retry_session:
                    self.fts_manager.hard_reset_patients_fts(retry_session)
                    try:
                        self.patient_repo.update_details(
                            retry_session,
                            patient_id,
                            full_name=full_name,
                            dob=dob,
                            sex=sex,
                            category=category,
                            military_unit=military_unit,
                            military_district=military_district,
                        )
                        retry_session.flush()
                    except OperationalError:
                        retry_session.rollback()
                        self._repair_database_raw(retry_session)
                        try:
                            self.patient_repo.update_details(
                                retry_session,
                                patient_id,
                                full_name=full_name,
                                dob=dob,
                                sex=sex,
                                category=category,
                                military_unit=military_unit,
                                military_district=military_district,
                            )
                            retry_session.flush()
                        except OperationalError:
                            retry_session.rollback()
                            self.fts_manager.hard_reset_patients_fts(retry_session)
                            self._update_patient_raw(
                                retry_session,
                                patient_id,
                                full_name=full_name,
                                dob=dob,
                                sex=sex,
                                category=category,
                                military_unit=military_unit,
                                military_district=military_district,
                            )
                            self.fts_manager.rebuild_patients_fts(retry_session)
                    try:
                        self.fts_manager.ensure_patients(retry_session)
                    except OperationalError:
                        logging.getLogger(__name__).warning(
                            "FTS rebuild failed after update_details", exc_info=True
                        )

    def _repair_database_raw(self, session) -> None:
        bind = session.get_bind()
        db_path = getattr(bind.url, "database", None)
        if not db_path or db_path == ":memory:":
            return
        import sqlite3

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA wal_checkpoint(FULL)")
            cur.execute("PRAGMA integrity_check")
            rows = [r[0] for r in cur.fetchall()]
            if rows != ["ok"]:
                logging.getLogger(__name__).warning(
                    "SQLite integrity_check failed: %s", "; ".join(rows)
                )
            cur.execute("REINDEX")
            cur.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()


    def _update_patient_raw(
        self,
        session,
        patient_id: int,
        *,
        full_name: str | None,
        dob: date | None,
        sex: str | None,
        category: str | None,
        military_unit: str | None,
        military_district: str | None,
    ) -> None:
        bind = session.get_bind()
        db_path = getattr(bind.url, "database", None)
        if not db_path or db_path == ":memory:":
            raise ValueError("Database path not available")
        import sqlite3

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT full_name, dob, sex, category, military_unit, military_district "
                "FROM patients WHERE id = ?",
                (patient_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("Пациент не найден")
            current_full_name, current_dob, current_sex, current_category, current_unit, current_district = row
            full_name_val = full_name if full_name is not None else current_full_name
            sex_val = sex if sex is not None else current_sex
            category_val = category if category is not None else current_category
            unit_val = military_unit if military_unit is not None else current_unit
            district_val = military_district if military_district is not None else current_district
            dob_val = dob.isoformat() if dob is not None else current_dob
            cur.execute(
                "UPDATE patients SET full_name=?, dob=?, sex=?, category=?, military_unit=?, military_district=? "
                "WHERE id = ?",
                (full_name_val, dob_val, sex_val, category_val, unit_val, district_val, patient_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete_patient_impl(self, session, patient_id: int) -> None:
        patient = session.get(Patient, patient_id)
        if not patient:
            raise ValueError("Пациент не найден")

        case_ids = list(
            session.execute(select(EmrCase.id).where(EmrCase.patient_id == patient_id)).scalars()
        )
        if case_ids:
            version_ids = list(
                session.execute(
                    select(EmrCaseVersion.id).where(EmrCaseVersion.emr_case_id.in_(case_ids))
                ).scalars()
            )
            if version_ids:
                session.query(EmrDiagnosis).filter(
                    EmrDiagnosis.emr_case_version_id.in_(version_ids)
                ).delete(synchronize_session=False)
                session.query(EmrIntervention).filter(
                    EmrIntervention.emr_case_version_id.in_(version_ids)
                ).delete(synchronize_session=False)
                session.query(EmrAntibioticCourse).filter(
                    EmrAntibioticCourse.emr_case_version_id.in_(version_ids)
                ).delete(synchronize_session=False)
                session.query(EmrCaseVersion).filter(
                    EmrCaseVersion.id.in_(version_ids)
                ).delete(synchronize_session=False)
            session.query(IsmpCase).filter(IsmpCase.emr_case_id.in_(case_ids)).delete(
                synchronize_session=False
            )
            session.query(EmrCase).filter(EmrCase.id.in_(case_ids)).delete(
                synchronize_session=False
            )

        sample_ids = list(
            session.execute(select(LabSample.id).where(LabSample.patient_id == patient_id)).scalars()
        )
        if sample_ids:
            session.query(LabMicrobeIsolation).filter(
                LabMicrobeIsolation.lab_sample_id.in_(sample_ids)
            ).delete(synchronize_session=False)
            session.query(LabAbxSusceptibility).filter(
                LabAbxSusceptibility.lab_sample_id.in_(sample_ids)
            ).delete(synchronize_session=False)
            session.query(LabPhagePanelResult).filter(
                LabPhagePanelResult.lab_sample_id.in_(sample_ids)
            ).delete(synchronize_session=False)
            session.query(LabSample).filter(LabSample.id.in_(sample_ids)).delete(
                synchronize_session=False
            )

        audit_filters = []
        if case_ids:
            audit_filters.append(
                (AuditLog.entity_type == "emr_case") & (AuditLog.entity_id.in_([str(i) for i in case_ids]))
            )
        if sample_ids:
            audit_filters.append(
                (AuditLog.entity_type == "lab_sample")
                & (AuditLog.entity_id.in_([str(i) for i in sample_ids]))
            )
        audit_filters.append(
            (AuditLog.entity_type == "patient") & (AuditLog.entity_id == str(patient_id))
        )
        for flt in audit_filters:
            session.query(AuditLog).filter(flt).delete(synchronize_session=False)

        session.query(Patient).filter(Patient.id == patient_id).delete(synchronize_session=False)

    def delete_patient(self, patient_id: int) -> None:
        with self.session_factory() as session:
            try:
                # Ensure no stale FTS triggers block deletion.
                self.fts_manager.drop_patients_fts(session)
                self._delete_patient_impl(session, patient_id)
                self.fts_manager.ensure_patients(session)
            except OperationalError as exc:
                session.rollback()
                logging.getLogger(__name__).warning("Delete patient failed, attempting FTS repair: %s", exc)
                # Drop any broken triggers on patients (often from old FTS setups), then retry.
                self.fts_manager.drop_patients_fts(session)
                try:
                    self._delete_patient_impl(session, patient_id)
                    self.fts_manager.ensure_patients(session)
                except OperationalError:
                    session.rollback()
                    if self.fts_manager.ensure_patients(session):
                        self._delete_patient_impl(session, patient_id)
                        self.fts_manager.ensure_patients(session)
                    else:
                        raise
