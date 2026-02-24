from __future__ import annotations

from dataclasses import dataclass

from app.application.services.analytics_service import AnalyticsService
from app.application.services.auth_service import AuthService
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.emz_service import EmzService
from app.application.services.exchange_service import ExchangeService
from app.application.services.form100_service import Form100Service
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.application.services.lab_service import LabService
from app.application.services.patient_service import PatientService
from app.application.services.reference_service import ReferenceService
from app.application.services.reporting_service import ReportingService
from app.application.services.sanitary_service import SanitaryService
from app.application.services.saved_filter_service import SavedFilterService
from app.application.services.user_admin_service import UserAdminService
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.repositories.analytics_repo import AnalyticsRepository
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.emz_repo import EmzRepository
from app.infrastructure.db.repositories.form100_repo import Form100Repository
from app.infrastructure.db.repositories.form100_repo_v2 import Form100RepositoryV2
from app.infrastructure.db.repositories.lab_repo import LabRepository
from app.infrastructure.db.repositories.patient_repo import PatientRepository
from app.infrastructure.db.repositories.reference_repo import ReferenceRepository
from app.infrastructure.db.repositories.sanitary_repo import SanitaryRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope


@dataclass
class Container:
    user_repo: UserRepository
    audit_repo: AuditLogRepository
    ref_repo: ReferenceRepository
    patient_repo: PatientRepository
    emz_repo: EmzRepository
    form100_repo: Form100Repository
    form100_v2_repo: Form100RepositoryV2
    lab_repo: LabRepository
    san_repo: SanitaryRepository
    analytics_repo: AnalyticsRepository

    auth_service: AuthService
    user_admin_service: UserAdminService
    emz_service: EmzService
    form100_service: Form100Service
    form100_v2_service: Form100ServiceV2
    patient_service: PatientService
    lab_service: LabService
    sanitary_service: SanitaryService
    reference_service: ReferenceService
    analytics_service: AnalyticsService
    exchange_service: ExchangeService
    dashboard_service: DashboardService
    saved_filter_service: SavedFilterService
    reporting_service: ReportingService
    backup_service: BackupService


def build_container() -> Container:
    user_repo = UserRepository()
    audit_repo = AuditLogRepository()
    ref_repo = ReferenceRepository()
    patient_repo = PatientRepository()
    emz_repo = EmzRepository()
    form100_repo = Form100Repository()
    form100_v2_repo = Form100RepositoryV2()
    lab_repo = LabRepository()
    san_repo = SanitaryRepository()
    analytics_repo = AnalyticsRepository()
    fts_manager = FtsManager(session_factory=session_scope)

    auth_service = AuthService(user_repo=user_repo, audit_repo=audit_repo, session_factory=session_scope)
    user_admin_service = UserAdminService(
        user_repo=user_repo, audit_repo=audit_repo, session_factory=session_scope
    )
    emz_service = EmzService(
        emz_repo=emz_repo,
        patient_repo=patient_repo,
        audit_repo=audit_repo,
        session_factory=session_scope,
    )
    form100_service = Form100Service(
        repo=form100_repo,
        user_repo=user_repo,
        audit_repo=audit_repo,
        session_factory=session_scope,
    )
    form100_v2_service = Form100ServiceV2(
        repo=form100_v2_repo,
        user_repo=user_repo,
        audit_repo=audit_repo,
        session_factory=session_scope,
    )
    patient_service = PatientService(
        patient_repo=patient_repo,
        session_factory=session_scope,
        fts_manager=fts_manager,
    )
    lab_service = LabService(
        lab_repo=lab_repo,
        ref_repo=ref_repo,
        audit_repo=audit_repo,
        session_factory=session_scope,
    )
    sanitary_service = SanitaryService(
        repo=san_repo,
        audit_repo=audit_repo,
        session_factory=session_scope,
    )
    analytics_service = AnalyticsService(
        repo=analytics_repo,
        session_factory=session_scope,
    )
    exchange_service = ExchangeService(
        session_factory=session_scope,
        form100_service=form100_service,
        form100_v2_service=form100_v2_service,
    )
    dashboard_service = DashboardService(session_factory=session_scope)
    reference_service = ReferenceService(
        repo=ref_repo,
        user_repo=user_repo,
        audit_repo=audit_repo,
    )
    saved_filter_service = SavedFilterService(session_factory=session_scope)
    reporting_service = ReportingService(
        analytics_service=analytics_service,
        form100_service=form100_service,
        form100_v2_service=form100_v2_service,
        reference_service=reference_service,
        session_factory=session_scope,
    )
    backup_service = BackupService(audit_repo=audit_repo, user_repo=user_repo)

    return Container(
        user_repo=user_repo,
        audit_repo=audit_repo,
        ref_repo=ref_repo,
        patient_repo=patient_repo,
        emz_repo=emz_repo,
        form100_repo=form100_repo,
        form100_v2_repo=form100_v2_repo,
        lab_repo=lab_repo,
        san_repo=san_repo,
        analytics_repo=analytics_repo,
        auth_service=auth_service,
        user_admin_service=user_admin_service,
        emz_service=emz_service,
        form100_service=form100_service,
        form100_v2_service=form100_v2_service,
        patient_service=patient_service,
        lab_service=lab_service,
        sanitary_service=sanitary_service,
        reference_service=reference_service,
        analytics_service=analytics_service,
        exchange_service=exchange_service,
        dashboard_service=dashboard_service,
        saved_filter_service=saved_filter_service,
        reporting_service=reporting_service,
        backup_service=backup_service,
    )
