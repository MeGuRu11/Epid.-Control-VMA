from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6.QtCore import QObject
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.dto.auth_dto import CreateUserRequest, LoginRequest, ResetPasswordRequest
from app.application.dto.emz_dto import (
    EmzCreateRequest,
    EmzIsmpDto,
    EmzUpdateRequest,
    EmzVersionPayload,
)
from app.application.dto.form100_v2_dto import (
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100SignV2Request,
    Form100UpdateV2Request,
)
from app.application.dto.lab_dto import (
    LabSampleCreateRequest,
    LabSampleResultUpdate,
    LabSampleUpdateRequest,
)
from app.application.dto.patient_dto import PatientCreateRequest
from app.application.dto.sanitary_dto import (
    SanitarySampleUpdateRequest,
)
from app.application.exceptions import PermissionError as AppPermissionError
from app.application.services import (
    backup_service as backup_service_module,
    reporting_service as reporting_service_module,
)
from app.application.services.analytics_service import AnalyticsService
from app.application.services.auth_service import LOCKOUT_MINUTES, AuthService
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.emz_service import EmzService
from app.application.services.exchange_service import ExchangeService
from app.application.services.form100_payload_service import (
    Form100BottomPayloadInput,
    Form100DataPayloadInput,
    Form100FlagsPayloadInput,
    Form100MainPayloadInput,
    Form100MedicalHelpPayloadInput,
    Form100StubPayloadInput,
    build_form100_data_payload,
)
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.application.services.lab_sample_payload_service import (
    build_lab_sample_create_request,
    compose_lab_result_update,
)
from app.application.services.lab_service import LabService
from app.application.services.patient_service import PatientService
from app.application.services.reference_service import ReferenceService
from app.application.services.reporting_service import ReportingService
from app.application.services.sanitary_sample_payload_service import (
    build_sanitary_result_update,
    build_sanitary_sample_create_request,
)
from app.application.services.sanitary_service import SanitaryService
from app.application.services.saved_filter_service import SavedFilterService
from app.application.services.setup_service import SetupService
from app.application.services.user_admin_service import UserAdminService
from app.bootstrap import startup
from app.domain.constants import IsmpType, MilitaryCategory
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.ui.widgets.async_task import run_async

SessionFactory = Callable[[], AbstractContextManager[Session]]


@pytest.fixture
def session_factory() -> Iterator[SessionFactory]:
    """Создает изолированную реальную SQLite :memory: БД для каждого теста."""
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    @contextmanager
    def _session_scope() -> Iterator[Session]:
        session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    yield _session_scope
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def seeded_refs(session_factory: SessionFactory) -> dict[str, int]:
    """Минимальный набор справочников для функциональных сценариев."""
    with session_factory() as session:
        department = models.Department(name="Functional Department")
        material = models.RefMaterialType(code="BLD", name="blood")
        microbe = models.RefMicroorganism(code="ECOLI", name="Escherichia coli", taxon_group="bacteria")
        group = models.RefAntibioticGroup(code="BETA", name="Beta-lactams")
        antibiotic = models.RefAntibiotic(code="AMP", name="Ampicillin", group=group)
        phage = models.RefPhage(code="PH1", name="Phage 1", is_active=True)
        icd10 = models.RefICD10(code="A00", title="Cholera", is_active=True)
        session.add_all([department, material, microbe, group, antibiotic, phage, icd10])
        session.flush()
        return {
            "department_id": cast(int, department.id),
            "material_type_id": cast(int, material.id),
            "microorganism_id": cast(int, microbe.id),
            "antibiotic_group_id": cast(int, group.id),
            "antibiotic_id": cast(int, antibiotic.id),
            "phage_id": cast(int, phage.id),
        }


def _audit_actions(session_factory: SessionFactory, *, entity_type: str | None = None) -> list[str]:
    with session_factory() as session:
        stmt = select(models.AuditLog)
        if entity_type is not None:
            stmt = stmt.where(models.AuditLog.entity_type == entity_type)
        rows = session.execute(stmt.order_by(models.AuditLog.id)).scalars().all()
        return [cast(str, row.action) for row in rows]


def _create_admin(session_factory: SessionFactory, login: str = "admin") -> int:
    SetupService(session_factory=session_factory).create_initial_user(login=login, password="12345678")
    with session_factory() as session:
        return cast(int, session.execute(select(models.User.id).where(models.User.login == login)).scalar_one())


def _create_operator(session_factory: SessionFactory, actor_id: int, login: str = "operator") -> int:
    return UserAdminService(session_factory=session_factory).create_user(
        CreateUserRequest(login=login, password="operator123", role="operator"),
        actor_id=actor_id,
    )


def _patient_request(name: str = "Ivan Petrov") -> PatientCreateRequest:
    return PatientCreateRequest(
        full_name=name,
        dob=date(1990, 1, 2),
        sex="M",
        category=MilitaryCategory.PRIVATE.value,
        military_unit="Unit 1",
        military_district="District 1",
    )


def _create_patient(session_factory: SessionFactory, actor_id: int, name: str = "Ivan Petrov") -> int:
    response = PatientService(session_factory=session_factory).create_or_get(_patient_request(name), actor_id=actor_id)
    return response.id


def _emz_payload() -> EmzVersionPayload:
    return EmzVersionPayload(
        admission_date=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
        injury_date=datetime(2026, 3, 31, 8, 0, tzinfo=UTC),
        outcome_date=datetime(2026, 4, 5, 12, 0, tzinfo=UTC),
        severity="moderate",
        sofa_score=3,
        ismp_cases=[EmzIsmpDto(ismp_type=IsmpType.VAP.value, start_date=date(2026, 4, 2))],
    )


def _create_emz_case(session_factory: SessionFactory, actor_id: int, department_id: int) -> int:
    request = EmzCreateRequest(
        patient_full_name="Emz Patient",
        patient_dob=date(1988, 5, 6),
        patient_sex="M",
        patient_category=MilitaryCategory.OFFICER.value,
        patient_military_unit="Unit 2",
        patient_military_district="District 2",
        hospital_case_no="CASE-1",
        department_id=department_id,
        payload=_emz_payload(),
    )
    return EmzService(session_factory=session_factory).create_emr(request, actor_id=actor_id).id


def _form100_data() -> Form100DataV2Dto:
    return Form100DataV2Dto.model_validate(
        {
            "main": {"main_full_name": "Form Patient", "main_unit": "Unit 100", "birth_date": "1991-02-03"},
            "bottom": {"main_diagnosis": "Test diagnosis"},
            "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
            "flags": {"flag_emergency": True, "flag_radiation": False, "flag_sanitation": False},
            "bodymap_gender": "M",
            "bodymap_annotations": [
                {
                    "annotation_type": "WOUND_X",
                    "x": 0.42,
                    "y": 0.36,
                    "silhouette": "male_front",
                    "note": "",
                    "shape_json": {},
                }
            ],
            "bodymap_tissue_types": ["мягкие ткани"],
        }
    )


def _create_lab_sample(
    session_factory: SessionFactory,
    *,
    actor_id: int,
    patient_id: int,
    material_type_id: int,
    microorganism_id: int | None = None,
) -> int:
    lab_service = LabService(session_factory=session_factory)
    sample = lab_service.create_sample(
        LabSampleCreateRequest(
            patient_id=patient_id,
            material_type_id=material_type_id,
            material_location="wound",
            medium="agar",
            taken_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
        ),
        actor_id=actor_id,
    )
    lab_service.update_result(
        sample.id,
        LabSampleResultUpdate(
            growth_result_at=datetime(2026, 4, 4, 9, 0, tzinfo=UTC),
            growth_flag=1,
            microorganism_id=microorganism_id,
            colony_desc="growth",
        ),
        actor_id=actor_id,
    )
    return sample.id


def _wait_until(qapp: Any, predicate: Callable[[], bool], timeout: float = 1.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Асинхронная задача не завершилась за ожидаемое время")


def test_block_1_authentication_and_user_admin_flow(session_factory: SessionFactory) -> None:
    setup = SetupService(session_factory=session_factory)
    setup.create_initial_user(login="admin", password="12345678")

    with session_factory() as session:
        admin = session.execute(select(models.User).where(models.User.login == "admin")).scalar_one()
        assert admin.password_hash != "12345678"
        assert str(admin.password_hash).startswith("$")

    with pytest.raises(ValueError):
        setup.create_initial_user(login="weak", password="123")

    auth = AuthService(session_factory=session_factory)
    ctx = auth.login(LoginRequest(login="admin", password="12345678"))
    assert ctx.login == "admin"
    assert ctx.role == "admin"

    user_admin = UserAdminService(session_factory=session_factory)
    operator_id = user_admin.create_user(
        CreateUserRequest(login="operator", password="operator123", role="operator"), actor_id=ctx.user_id
    )
    user_admin.reset_password(ResetPasswordRequest(user_id=operator_id, new_password="operator456"), actor_id=ctx.user_id)
    user_admin.set_active(operator_id, False, actor_id=ctx.user_id)

    with pytest.raises(ValueError):
        auth.login(LoginRequest(login="operator", password="operator456"))

    for _ in range(5):
        with pytest.raises(ValueError):
            auth.login(LoginRequest(login="admin", password="wrong-password"))

    with session_factory() as session:
        locked_admin = session.get(models.User, ctx.user_id)
        assert locked_admin is not None
        assert int(cast(int, locked_admin.failed_login_count)) >= 5
        assert locked_admin.locked_until is not None

    future_auth = AuthService(
        session_factory=session_factory,
        clock=lambda: datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES + 1),
    )
    unlocked = future_auth.login(LoginRequest(login="admin", password="12345678"))
    assert unlocked.user_id == ctx.user_id
    assert {"create_user", "reset_password", "set_active"}.issubset(set(_audit_actions(session_factory, entity_type="user")))


def test_block_2_patient_crud_search_delete_audit(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    admin_id = _create_admin(session_factory)
    patient_service = PatientService(session_factory=session_factory)
    patient = patient_service.create_or_get(_patient_request("Patient Cascade"), actor_id=admin_id)
    _create_lab_sample(
        session_factory,
        actor_id=admin_id,
        patient_id=patient.id,
        material_type_id=seeded_refs["material_type_id"],
    )

    assert patient_service.get_by_id(patient.id).full_name == "Patient Cascade"
    patient_service.update_details(
        patient.id,
        actor_id=admin_id,
        full_name="Patient Updated",
        dob=date(1991, 2, 3),
        sex="M",
        category=MilitaryCategory.SERGEANT.value,
        military_unit="Updated Unit",
        military_district="Updated District",
    )
    assert [item.id for item in patient_service.search_by_name("Updated")] == [patient.id]

    patient_service.delete_patient(patient.id, actor_id=admin_id)
    with pytest.raises(ValueError):
        patient_service.get_by_id(patient.id)
    with session_factory() as session:
        assert session.execute(select(models.LabSample).where(models.LabSample.patient_id == patient.id)).first() is None
        assert session.execute(select(models.AuditLog).where(models.AuditLog.user_id == admin_id)).first() is not None


def test_block_3_emz_create_update_read_actor_required(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    admin_id = _create_admin(session_factory)
    service = EmzService(session_factory=session_factory)
    emr_case_id = _create_emz_case(session_factory, admin_id, seeded_refs["department_id"])
    updated = service.update_emr(EmzUpdateRequest(emr_case_id=emr_case_id, payload=_emz_payload()), actor_id=admin_id)
    assert updated.version_no == 2

    service.update_case_meta(
        emr_case_id,
        hospital_case_no="CASE-1A",
        department_id=seeded_refs["department_id"],
        actor_id=admin_id,
    )
    detail = service.get_current(emr_case_id)
    assert detail.hospital_case_no == "CASE-1A"
    assert detail.patient_full_name == "Emz Patient"
    with pytest.raises(AppPermissionError):
        service.update_emr(EmzUpdateRequest(emr_case_id=emr_case_id, payload=_emz_payload()), actor_id=cast(int, None))


def test_block_4_lab_sample_crud_payload_validation_actor(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    admin_id = _create_admin(session_factory)
    patient_id = _create_patient(session_factory, admin_id, "Lab Patient")
    request = build_lab_sample_create_request(
        patient_id=patient_id,
        emr_case_id=None,
        material_type_id=seeded_refs["material_type_id"],
        material_location="wound",
        medium="agar",
        study_kind="primary",
        ordered_at=None,
        taken_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
        delivered_at=None,
    )
    service = LabService(session_factory=session_factory)
    sample = service.create_sample(request, actor_id=admin_id)
    assert sample.id > 0

    updated = service.update_result(
        sample.id,
        compose_lab_result_update(
            has_results=True,
            growth_flag=True,
            growth_result_at=datetime(2026, 4, 4, 9, 0, tzinfo=UTC),
            colony_desc="colonies",
            microscopy="gram negative",
            cfu="10^5",
            qc_status="valid",
            microorganism_id=seeded_refs["microorganism_id"],
            microorganism_free="",
            susceptibility=[],
            phages=[],
        ),
        actor_id=admin_id,
    )
    assert updated.growth_flag == 1
    detail_after_result = service.get_detail(sample.id)
    assert detail_after_result["isolation"][0].microorganism_id == seeded_refs["microorganism_id"]

    service.update_sample(
        sample.id,
        LabSampleUpdateRequest(
            material_type_id=seeded_refs["material_type_id"],
            material_location="blood culture",
            medium="broth",
        ),
        actor_id=admin_id,
    )
    detail = service.get_detail(sample.id)
    assert detail["sample"].material_location == "blood culture"
    assert service.list_samples(patient_id)

    with pytest.raises(ValueError):
        build_lab_sample_create_request(
            patient_id=patient_id,
            emr_case_id=None,
            material_type_id=None,
            material_location="",
            medium="",
            study_kind="primary",
            ordered_at=None,
            taken_at=None,
            delivered_at=None,
        )
    with pytest.raises(ValueError):
        service.create_sample(request, actor_id=cast(int, None))


def test_block_5_sanitary_sample_crud_payload_validation_actor(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    admin_id = _create_admin(session_factory)
    service = SanitaryService(session_factory=session_factory)
    request = build_sanitary_sample_create_request(
        department_id=seeded_refs["department_id"],
        sampling_point="table",
        room="101",
        medium="swab",
        taken_at=datetime(2026, 4, 3, 9, 0, tzinfo=UTC),
        delivered_at=None,
    )
    sample = service.create_sample(request, actor_id=admin_id)
    assert sample.id > 0

    updated = service.update_result(
        sample.id,
        build_sanitary_result_update(
            has_results=True,
            growth_flag=True,
            growth_result_at=datetime(2026, 4, 4, 9, 0, tzinfo=UTC),
            colony_desc="colonies",
            microscopy="gram positive",
            cfu="10^3",
            microorganism_id=seeded_refs["microorganism_id"],
            microorganism_free="",
            susceptibility=[],
            phages=[],
        ),
        actor_id=admin_id,
    )
    assert updated.growth_flag == 1

    service.update_sample(sample.id, SanitarySampleUpdateRequest(sampling_point="sink", room="102", medium="swab"), actor_id=admin_id)
    detail = service.get_detail(sample.id)
    assert detail["sample"].sampling_point == "sink"
    assert service.list_samples_by_department(seeded_refs["department_id"])

    with pytest.raises(ValueError):
        build_sanitary_sample_create_request(
            department_id=seeded_refs["department_id"],
            sampling_point="",
            room="",
            medium="",
            taken_at=None,
            delivered_at=None,
        )
    with pytest.raises(ValueError):
        service.create_sample(request, actor_id=cast(int, None))


def test_block_6_form100_lifecycle_payload_and_privacy_audit(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    admin_id = _create_admin(session_factory)
    emr_case_id = _create_emz_case(session_factory, admin_id, seeded_refs["department_id"])
    service = Form100ServiceV2(session_factory=session_factory)
    card = service.create_card(
        Form100CreateV2Request(
            emr_case_id=emr_case_id,
            main_full_name="Form Patient",
            main_unit="Unit 100",
            main_id_tag="TAG-100",
            main_diagnosis="Sensitive diagnosis text",
            birth_date=date(1991, 2, 3),
            data=_form100_data(),
        ),
        actor_id=admin_id,
    )
    assert card.status == "DRAFT"

    payload = build_form100_data_payload(
        Form100DataPayloadInput(
            stub=Form100StubPayloadInput(
                issued_date="2026-04-01",
                issued_time="10:00",
                rank="rank",
                unit="Unit 101",
                full_name="Form Patient Updated",
                id_tag="TAG-101",
                injury_date="2026-04-01",
                injury_time="09:00",
                evacuation_method=None,
                evacuation_dest=None,
                med_help_underlined=[],
                antibiotic_dose="",
                pss_pgs_dose="",
                toxoid_type="",
                antidote_type="",
                analgesic_dose="",
                transfusion=False,
                immobilization=False,
                tourniquet=False,
                diagnosis="Updated diagnosis",
            ),
            main=Form100MainPayloadInput(
                full_name="Form Patient Updated",
                unit="Unit 101",
                id_tag="TAG-101",
                rank="rank",
                issued_place="place",
                issued_date="2026-04-01",
                issued_time="10:00",
                injury_date="2026-04-01",
                injury_time="09:00",
                birth_date_iso="1991-02-03",
            ),
            lesion={"lesion_gunshot": True},
            san_loss={},
            bodymap_gender="M",
            bodymap_annotations=[],
            bodymap_tissue_types=["мягкие ткани"],
            medical_help=Form100MedicalHelpPayloadInput(
                antibiotic=False,
                antibiotic_dose="",
                serum_pss=False,
                serum_pgs=False,
                serum_dose="",
                toxoid="",
                antidote="",
                analgesic=False,
                analgesic_dose="",
                transfusion_blood=False,
                transfusion_substitute=False,
                immobilization=False,
                bandage=False,
            ),
            bottom=Form100BottomPayloadInput(
                tourniquet_time="",
                sanitation_type=None,
                evacuation_dest=None,
                evacuation_priority="I",
                transport_type=None,
                doctor_signature="doctor",
                main_diagnosis="Updated diagnosis",
            ),
            flags=Form100FlagsPayloadInput(emergency=True, radiation=False, sanitation=False),
        )
    )
    updated = service.update_card(
        card.id,
        Form100UpdateV2Request(
            main_full_name="Form Patient Updated",
            main_unit="Unit 101",
            main_id_tag="TAG-101",
            main_diagnosis="Updated diagnosis",
            birth_date=date(1991, 2, 3),
            data=Form100DataV2Dto.model_validate(payload),
        ),
        actor_id=admin_id,
        expected_version=card.version,
    )
    signed = service.sign_card(
        updated.id,
        Form100SignV2Request(signed_by="doctor"),
        actor_id=admin_id,
        expected_version=updated.version,
    )
    archived = service.archive_card(signed.id, actor_id=admin_id, expected_version=signed.version)
    fetched = service.get_card(archived.id)
    assert fetched.is_archived is True
    assert fetched.status == "SIGNED"

    with pytest.raises(AppPermissionError):
        service.create_card(
            Form100CreateV2Request(
                main_full_name="No Actor",
                main_unit="Unit",
                main_diagnosis="Diagnosis",
                data=_form100_data(),
            ),
            actor_id=cast(int, None),
        )

    with session_factory() as session:
        audit_rows = list(session.execute(select(models.AuditLog).where(models.AuditLog.entity_type == "form100")).scalars())
    assert {row.action for row in audit_rows} >= {"form100_create", "form100_update", "form100_sign", "form100_archive"}
    joined_payload = "\n".join(str(row.payload_json) for row in audit_rows)
    assert "Sensitive diagnosis text" not in joined_payload
    assert "Form Patient Updated" not in joined_payload
    assert "data_hash" in joined_payload
    assert "changed_fields" in joined_payload


def test_block_7_analytics_and_dashboard_empty_and_with_data_cache(
    session_factory: SessionFactory, seeded_refs: dict[str, int]
) -> None:
    analytics = AnalyticsService(session_factory=session_factory, cache_ttl_seconds=60)
    empty_request = AnalyticsSearchRequest()
    empty = analytics.get_aggregates(empty_request)
    assert empty["total"] == 0

    admin_id = _create_admin(session_factory)
    patient_id = _create_patient(session_factory, admin_id, "Analytics Patient")
    _create_lab_sample(
        session_factory,
        actor_id=admin_id,
        patient_id=patient_id,
        material_type_id=seeded_refs["material_type_id"],
        microorganism_id=seeded_refs["microorganism_id"],
    )
    result = analytics.get_aggregates(empty_request)
    cached = analytics.get_aggregates(empty_request)
    assert result == cached
    assert result["total"] == 0
    assert len(analytics._cache) >= 1
    analytics.clear_cache()
    refreshed = analytics.get_aggregates(empty_request)
    assert refreshed["total"] == 1

    dashboard = DashboardService(session_factory=session_factory)
    counts = dashboard.get_counts()
    assert counts["patients"] >= 1
    assert counts["lab_samples"] >= 1
    assert dashboard.list_recent_audit(limit=5)
    assert dashboard.get_new_patients_count(days=30) >= 1


def test_block_8_reference_crud_permissions(session_factory: SessionFactory) -> None:
    admin_id = _create_admin(session_factory)
    operator_id = _create_operator(session_factory, admin_id)
    service = ReferenceService(session_factory=session_factory)

    assert service.list_antibiotics() == []
    service.add_antibiotic_group("GRP", "Group", actor_id=admin_id)
    group_id = cast(int, service.list_antibiotic_groups()[0].id)
    service.add_antibiotic("ABX", "Antibiotic", group_id=group_id, actor_id=admin_id)
    antibiotic = service.list_antibiotics()[0]
    assert antibiotic.code == "ABX"

    service.update_antibiotic(cast(int, antibiotic.id), "ABX2", "Antibiotic 2", group_id, actor_id=admin_id)
    assert service.list_antibiotics()[0].code == "ABX2"
    service.delete_antibiotic(cast(int, antibiotic.id), actor_id=admin_id)
    assert service.list_antibiotics() == []

    service.add_microorganism("MIC", "Microbe", taxon_group="group", actor_id=admin_id)
    microbe = service.list_microorganisms()[0]
    assert microbe.code == "MIC"
    service.update_microorganism(cast(int, microbe.id), "MIC2", "Microbe 2", "group2", actor_id=admin_id)
    assert service.list_microorganisms()[0].code == "MIC2"
    service.delete_microorganism(cast(int, microbe.id), actor_id=admin_id)
    assert service.list_microorganisms() == []

    with pytest.raises(ValueError):
        service.add_antibiotic("DENIED", "Denied", group_id=group_id, actor_id=operator_id)
    with pytest.raises(ValueError):
        service.add_antibiotic("NOACTOR", "No Actor", group_id=group_id, actor_id=cast(int, None))
    actions = set(_audit_actions(session_factory, entity_type="reference"))
    assert "reference_create_antibiotic" in actions
    assert "reference_update_antibiotic" in actions
    assert "reference_delete_antibiotic" in actions
    assert "reference_create_microorganism" in actions
    assert "reference_update_microorganism" in actions
    assert "reference_delete_microorganism" in actions
    assert "access_denied" in actions


def test_block_8_reference_success_audit(session_factory: SessionFactory) -> None:
    admin_id = _create_admin(session_factory)
    service = ReferenceService(session_factory=session_factory)
    service.add_department("Audit Department", actor_id=admin_id)
    assert "reference_create_department" in _audit_actions(session_factory, entity_type="reference")


def test_block_9_exchange_json_and_backup_permissions(
    session_factory: SessionFactory,
    seeded_refs: dict[str, int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_id = _create_admin(session_factory)
    operator_id = _create_operator(session_factory, admin_id)
    _create_patient(session_factory, admin_id, "Exchange Patient")

    exchange = ExchangeService(session_factory=session_factory)
    export_path = tmp_path / "exchange.json"
    export_result = exchange.export_json(export_path, exported_by="admin", actor_id=admin_id)
    assert export_path.exists()
    assert export_result["counts"]["patients"] == 1

    import_result = exchange.import_json(export_path, actor_id=admin_id, mode="merge")
    assert import_result["summary"]["rows_total"] >= 1
    with pytest.raises(ValueError):
        exchange.export_json(tmp_path / "denied.json", actor_id=operator_id)

    db_file = tmp_path / "app.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE smoke(id INTEGER PRIMARY KEY)")
        conn.commit()
    data_dir = tmp_path / "data"
    monkeypatch.setattr(backup_service_module, "DATA_DIR", data_dir)
    monkeypatch.setattr(backup_service_module, "DB_FILE", db_file)
    backup = BackupService(AuditLogRepository(), session_factory=session_factory)
    backup_path = backup.create_backup(actor_id=admin_id, reason="functional")
    assert backup_path.exists()
    assert backup_path.parent == data_dir / "backups"
    with pytest.raises(ValueError):
        backup.create_backup(actor_id=operator_id, reason="denied")


def test_block_10_reporting_masks_sensitive_filters(
    session_factory: SessionFactory,
    seeded_refs: dict[str, int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_id = _create_admin(session_factory)
    patient_id = _create_patient(session_factory, admin_id, "Secret Patient")
    _create_lab_sample(
        session_factory,
        actor_id=admin_id,
        patient_id=patient_id,
        material_type_id=seeded_refs["material_type_id"],
        microorganism_id=seeded_refs["microorganism_id"],
    )
    monkeypatch.setattr(reporting_service_module, "REPORT_ARTIFACT_DIR", tmp_path / "artifacts" / "reports")
    reporting = ReportingService(
        AnalyticsService(session_factory=session_factory),
        reference_service=ReferenceService(session_factory=session_factory),
        session_factory=session_factory,
    )
    output = tmp_path / "analytics.xlsx"
    result = reporting.export_analytics_xlsx(
        AnalyticsSearchRequest(patient_name="Secret Patient", lab_no="BLD", search_text="secret"),
        output,
        actor_id=admin_id,
    )
    assert output.exists()
    assert Path(str(result["artifact_path"])).exists()

    runs = reporting.list_report_runs()
    assert runs
    filters = runs[0]["filters"]
    assert filters["patient_name"] == "***"
    assert filters["lab_no"] == "***"
    assert filters["search_text"] == "***"


def test_block_11_saved_filter_create_list_actor(session_factory: SessionFactory) -> None:
    admin_id = _create_admin(session_factory)
    service = SavedFilterService(session_factory=session_factory)
    item = service.save_filter("analytics", "My filter", {"patient_name": "Secret"}, actor_id=admin_id)
    filters = service.list_filters("analytics")
    assert len(filters) == 1
    assert filters[0].id == item.id
    assert filters[0].created_by == admin_id
    with pytest.raises(AppPermissionError):
        service.save_filter("analytics", "No actor", {"x": 1}, actor_id=cast(int, None))
    assert "saved_filter_create" in _audit_actions(session_factory, entity_type="saved_filter")


def test_block_11_saved_filter_delete(session_factory: SessionFactory) -> None:
    admin_id = _create_admin(session_factory)
    service = SavedFilterService(session_factory=session_factory)
    item = service.save_filter("analytics", "Temporary filter", {"patient_name": "Secret"}, actor_id=admin_id)

    service.delete_filter(cast(int, item.id), actor_id=admin_id)

    assert service.list_filters("analytics") == []
    assert "saved_filter_delete" in _audit_actions(session_factory, entity_type="saved_filter")
    with pytest.raises(AppPermissionError):
        service.delete_filter(cast(int, item.id), actor_id=cast(int, None))
    with pytest.raises(ValueError):
        service.delete_filter(cast(int, item.id), actor_id=admin_id)


def test_block_12_startup_fts_and_async_task(
    session_factory: SessionFactory,
    seeded_refs: dict[str, int],
    qapp: Any,
) -> None:
    admin_id = _create_admin(session_factory)
    patient_id = _create_patient(session_factory, admin_id, "Fts Searchable")
    assert startup.has_users(session_factory) is True
    assert startup.ensure_fts_objects(session_factory) is True

    fts = FtsManager(session_factory=session_factory)
    assert fts.ensure_all() is True
    search_results = PatientService(session_factory=session_factory).search_by_name("Searchable")
    assert [item.id for item in search_results] == [patient_id]

    owner = QObject()
    state: dict[str, Any] = {"result": None, "finished": False}
    run_async(
        owner,
        lambda: {"ok": True},
        on_success=lambda result: state.__setitem__("result", result),
        on_finished=lambda: state.__setitem__("finished", True),
    )
    _wait_until(qapp, lambda: bool(state["finished"]))
    assert state["result"] == {"ok": True}
    assert not hasattr(owner, "_codex_async_tasks")
