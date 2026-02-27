from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # admin/operator
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class RefIcd10(Base):
    __tablename__ = "ref_icd10"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RefMicroorganism(Base):
    __tablename__ = "ref_microorganisms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    taxon_group: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RefAntibioticGroup(Base):
    __tablename__ = "ref_antibiotic_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class RefAntibiotic(Base):
    __tablename__ = "ref_antibiotics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotic_groups.id", ondelete="SET NULL"), nullable=True
    )


class RefPhage(Base):
    __tablename__ = "ref_phages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RefMaterialType(Base):
    __tablename__ = "ref_material_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String, default="U", nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    military_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    military_district: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class EmrCase(Base):
    __tablename__ = "emr_case"
    __table_args__ = (UniqueConstraint("patient_id", "hospital_case_no", name="ux_case_patient_no"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    hospital_case_no: Mapped[str] = mapped_column(String, nullable=False)
    # Keep legacy textual department for compatibility with existing UI/data.
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class EmrCaseVersion(Base):
    __tablename__ = "emr_case_version"
    __table_args__ = (UniqueConstraint("emr_case_id", "version_no", name="ux_case_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emr_case_id: Mapped[int] = mapped_column(ForeignKey("emr_case.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    injury_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    outcome_type: Mapped[str | None] = mapped_column(String, nullable=True)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    vph_sp_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vph_p_or_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sofa_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_to_admission: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length_of_stay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EmrDiagnosis(Base):
    __tablename__ = "emr_diagnosis"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emr_case_version_id: Mapped[int] = mapped_column(
        ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    icd10_code: Mapped[str | None] = mapped_column(
        ForeignKey("ref_icd10.code", ondelete="SET NULL"), nullable=True
    )
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmrIntervention(Base):
    __tablename__ = "emr_intervention"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emr_case_version_id: Mapped[int] = mapped_column(
        ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    start_dt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_dt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmrAntibioticCourse(Base):
    __tablename__ = "emr_antibiotic_course"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emr_case_version_id: Mapped[int] = mapped_column(
        ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False
    )
    start_dt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_dt: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    antibiotic_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotics.id", ondelete="SET NULL"), nullable=True
    )
    drug_name_free: Mapped[str | None] = mapped_column(String, nullable=True)
    route: Mapped[str | None] = mapped_column(String, nullable=True)
    dose: Mapped[str | None] = mapped_column(String, nullable=True)


class LabNumberSequence(Base):
    __tablename__ = "lab_number_sequence"
    __table_args__ = (UniqueConstraint("seq_date", "material_type_id", name="ux_lab_seq"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq_date: Mapped[date] = mapped_column(Date, nullable=False)
    material_type_id: Mapped[int] = mapped_column(
        ForeignKey("ref_material_types.id", ondelete="CASCADE"), nullable=False
    )
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LabSample(Base):
    __tablename__ = "lab_sample"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    emr_case_id: Mapped[int | None] = mapped_column(ForeignKey("emr_case.id", ondelete="SET NULL"), nullable=True)
    lab_no: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String, nullable=True)
    material_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_material_types.id", ondelete="SET NULL"), nullable=True
    )
    material_location: Mapped[str | None] = mapped_column(String, nullable=True)
    medium: Mapped[str | None] = mapped_column(String, nullable=True)
    study_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    growth_result_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Legacy/simple columns kept for compatibility with existing UI.
    material: Mapped[str] = mapped_column(String, nullable=False, default="Кровь")
    organism: Mapped[str | None] = mapped_column(String, nullable=True)
    growth_flag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    colony_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    microscopy: Mapped[str | None] = mapped_column(Text, nullable=True)
    mic: Mapped[str | None] = mapped_column(String, nullable=True)
    cfu: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class LabMicrobeIsolation(Base):
    __tablename__ = "lab_microbe_isolation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_sample_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False
    )
    microorganism_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_microorganisms.id", ondelete="SET NULL"), nullable=True
    )
    microorganism_free: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class LabAbxSusceptibility(Base):
    __tablename__ = "lab_abx_susceptibility"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_sample_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False
    )
    antibiotic_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotics.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotic_groups.id", ondelete="SET NULL"), nullable=True
    )
    ris: Mapped[str | None] = mapped_column(String, nullable=True)
    mic_mg_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str | None] = mapped_column(String, nullable=True)


class LabPhagePanelResult(Base):
    __tablename__ = "lab_phage_panel_result"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lab_sample_id: Mapped[int] = mapped_column(
        ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False
    )
    phage_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_phages.id", ondelete="SET NULL"), nullable=True
    )
    phage_free: Mapped[str | None] = mapped_column(String, nullable=True)
    lysis_diameter_mm: Mapped[float | None] = mapped_column(Float, nullable=True)


class SanitarySample(Base):
    __tablename__ = "sanitary_sample"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    room: Mapped[str | None] = mapped_column(String, nullable=True)
    sampling_point: Mapped[str] = mapped_column(String, nullable=False)
    lab_no: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String, nullable=True)
    medium: Mapped[str | None] = mapped_column(String, nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    growth_result_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    growth_flag: Mapped[int | None] = mapped_column(Integer, nullable=True)
    colony_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    microscopy: Mapped[str | None] = mapped_column(Text, nullable=True)
    cfu: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SanMicrobeIsolation(Base):
    __tablename__ = "san_microbe_isolation"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sanitary_sample_id: Mapped[int] = mapped_column(
        ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False
    )
    microorganism_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_microorganisms.id", ondelete="SET NULL"), nullable=True
    )
    microorganism_free: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SanAbxSusceptibility(Base):
    __tablename__ = "san_abx_susceptibility"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sanitary_sample_id: Mapped[int] = mapped_column(
        ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False
    )
    antibiotic_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotics.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_antibiotic_groups.id", ondelete="SET NULL"), nullable=True
    )
    ris: Mapped[str | None] = mapped_column(String, nullable=True)
    mic_mg_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str | None] = mapped_column(String, nullable=True)


class SanPhagePanelResult(Base):
    __tablename__ = "san_phage_panel_result"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sanitary_sample_id: Mapped[int] = mapped_column(
        ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False
    )
    phage_id: Mapped[int | None] = mapped_column(
        ForeignKey("ref_phages.id", ondelete="SET NULL"), nullable=True
    )
    phage_free: Mapped[str | None] = mapped_column(String, nullable=True)
    lysis_diameter_mm: Mapped[float | None] = mapped_column(Float, nullable=True)


class ReportRun(Base):
    __tablename__ = "report_run"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    filters_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    artifact_path: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String, nullable=True)


class DataExchangePackage(Base):
    __tablename__ = "data_exchange_package"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    package_format: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Form100Card(Base):
    __tablename__ = "form100_card"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    emr_case_id: Mapped[int | None] = mapped_column(ForeignKey("emr_case.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="DRAFT", nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    bodymap_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    signed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Form100Orm(Base):
    """Заголовочная запись Формы 100 (v2, новая схема)."""
    __tablename__ = "form100"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emr_case_id: Mapped[int] = mapped_column(ForeignKey("emr_case.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_archived: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)


class Form100DataOrm(Base):
    """Все поля данных Формы 100 (v2, новая схема). Один-к-одному с Form100Orm."""
    __tablename__ = "form100_data"
    __table_args__ = (UniqueConstraint("form100_id", name="ux_form100_data_form"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form100_id: Mapped[int] = mapped_column(ForeignKey("form100.id", ondelete="CASCADE"), nullable=False)
    # ── Корешок ─────────────────────────────────────────────────────────────
    stub_issued_time: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_issued_date: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_rank: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_id_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_injury_time: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_injury_date: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_evacuation_method: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_evacuation_dest: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_med_help_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    stub_antibiotic_dose: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_pss_pgs_dose: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_toxoid_type: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_antidote_type: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_analgesic_dose: Mapped[str | None] = mapped_column(String, nullable=True)
    stub_transfusion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stub_immobilization: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stub_tourniquet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stub_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── Основной бланк — идентификация ──────────────────────────────────────
    main_issued_place: Mapped[str | None] = mapped_column(String, nullable=True)
    main_issued_time: Mapped[str | None] = mapped_column(String, nullable=True)
    main_issued_date: Mapped[str | None] = mapped_column(String, nullable=True)
    main_rank: Mapped[str | None] = mapped_column(String, nullable=True)
    main_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    main_full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    main_id_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    main_injury_time: Mapped[str | None] = mapped_column(String, nullable=True)
    main_injury_date: Mapped[str | None] = mapped_column(String, nullable=True)
    # ── Виды поражений ───────────────────────────────────────────────────────
    lesion_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    san_loss_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    isolation_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # ── Bodymap ──────────────────────────────────────────────────────────────
    bodymap_gender: Mapped[str] = mapped_column(String, default="M", nullable=False)
    bodymap_annotations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    bodymap_tissue_types_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    # ── Медицинская помощь ───────────────────────────────────────────────────
    mp_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    # ── Нижний блок ──────────────────────────────────────────────────────────
    tourniquet_time: Mapped[str | None] = mapped_column(String, nullable=True)
    sanitation_type: Mapped[str | None] = mapped_column(String, nullable=True)
    evacuation_dest: Mapped[str | None] = mapped_column(String, nullable=True)
    evacuation_priority: Mapped[str | None] = mapped_column(String, nullable=True)
    transport_type: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_signature: Mapped[str | None] = mapped_column(String, nullable=True)
    main_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── Флаги ────────────────────────────────────────────────────────────────
    flag_emergency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flag_radiation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    flag_sanitation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_ts: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "event_ts": self.event_ts.isoformat(timespec="seconds"),
            "username": self.username or "",
            "action": self.action,
            "entity": f"{self.entity_type}:{self.entity_id}",
            "payload_json": (self.payload_json or "")[:500],
        }
