from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import expression

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # avoid constraint_name token to allow unnamed CheckConstraint
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)


class Base(DeclarativeBase):
    metadata = metadata

PatientsFts = Table(
    "patients_fts",
    metadata,
    Column("full_name", Text),
    Column("patient_id", Integer),
)

RefMicroorganismsFts = Table(
    "ref_microorganisms_fts",
    metadata,
    Column("name", Text),
    Column("code", String),
    Column("taxon_group", String),
    Column("microorganism_id", Integer),
)

RefIcd10Fts = Table(
    "ref_icd10_fts",
    metadata,
    Column("title", Text),
    Column("code", String),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=expression.true())
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("role in ('admin','operator')", name="ck_users_role"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    event_ts = Column(DateTime, nullable=False, default=utc_now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload_json = Column(Text, nullable=True)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


class RefICD10(Base):
    __tablename__ = "ref_icd10"

    code = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=expression.true())


class RefMicroorganism(Base):
    __tablename__ = "ref_microorganisms"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(Text, nullable=False)
    taxon_group = Column(String)
    is_active = Column(Boolean, nullable=False, server_default=expression.true())


class RefAntibioticGroup(Base):
    __tablename__ = "ref_antibiotic_groups"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)


class RefAntibiotic(Base):
    __tablename__ = "ref_antibiotics"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey("ref_antibiotic_groups.id"))

    group = relationship("RefAntibioticGroup")


class RefPhage(Base):
    __tablename__ = "ref_phages"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=expression.true())


class RefMaterialType(Base):
    __tablename__ = "ref_material_types"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)


class RefIsmpAbbreviation(Base):
    __tablename__ = "ref_ismp_abbreviations"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    full_name = Column(Text, nullable=False)
    dob = Column(Date)
    sex = Column(String, CheckConstraint("sex in ('M','F','U')"), server_default=expression.literal("U"))
    category = Column(String)
    military_unit = Column(String)
    military_district = Column(String)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class EmrCase(Base):
    __tablename__ = "emr_case"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_case_no = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("patient_id", "hospital_case_no", name="uq_emr_case_patient_case"),
    )


class IsmpCase(Base):
    __tablename__ = "ismp_case"

    id = Column(Integer, primary_key=True)
    emr_case_id = Column(Integer, ForeignKey("emr_case.id", ondelete="CASCADE"), nullable=False)
    ismp_type = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        CheckConstraint("ismp_type in ('ВАП','КА-ИК','КА-ИМП','ИОХВ','ПАП','БАК','СЕПСИС')", name="ck_ismp_case_ismp_type"),
        Index("ix_ismp_case_emr_case_id", "emr_case_id"),
        Index("ix_ismp_case_start_date", "start_date"),
    )


class EmrCaseVersion(Base):
    __tablename__ = "emr_case_version"

    id = Column(Integer, primary_key=True)
    emr_case_id = Column(Integer, ForeignKey("emr_case.id", ondelete="CASCADE"), nullable=False)
    version_no = Column(Integer, nullable=False)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime)
    is_current = Column(Boolean, nullable=False)
    entered_by = Column(Integer, ForeignKey("users.id"))

    admission_date = Column(DateTime)
    injury_date = Column(DateTime)
    outcome_date = Column(DateTime)
    outcome_type = Column(String)
    severity = Column(String)
    vph_sp_score = Column(Integer)
    vph_p_or_score = Column(Integer)
    sofa_score = Column(Integer)
    days_to_admission = Column(Integer)
    length_of_stay_days = Column(Integer)

    __table_args__ = (
        UniqueConstraint("emr_case_id", "version_no", name="uq_emr_case_version_no"),
    )


class EmrDiagnosis(Base):
    __tablename__ = "emr_diagnosis"

    id = Column(Integer, primary_key=True)
    emr_case_version_id = Column(Integer, ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String, CheckConstraint("kind in ('admission','discharge','complication')"))
    icd10_code = Column(String, ForeignKey("ref_icd10.code"))
    free_text = Column(Text)


class EmrIntervention(Base):
    __tablename__ = "emr_intervention"

    id = Column(Integer, primary_key=True)
    emr_case_version_id = Column(Integer, ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False)
    start_dt = Column(DateTime)
    end_dt = Column(DateTime)
    duration_minutes = Column(Integer)
    performed_by = Column(String)
    notes = Column(Text)


class EmrAntibioticCourse(Base):
    __tablename__ = "emr_antibiotic_course"

    id = Column(Integer, primary_key=True)
    emr_case_version_id = Column(Integer, ForeignKey("emr_case_version.id", ondelete="CASCADE"), nullable=False)
    start_dt = Column(DateTime)
    end_dt = Column(DateTime)
    antibiotic_id = Column(Integer, ForeignKey("ref_antibiotics.id"))
    drug_name_free = Column(Text)
    route = Column(String)
    dose = Column(String)


class LabNumberSequence(Base):
    __tablename__ = "lab_number_sequence"

    id = Column(Integer, primary_key=True)
    seq_date = Column(Date, nullable=False)
    material_type_id = Column(Integer, ForeignKey("ref_material_types.id"), nullable=False)
    last_number = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("seq_date", "material_type_id", name="uq_lab_number_sequence"),)


class LabSample(Base):
    __tablename__ = "lab_sample"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    emr_case_id = Column(Integer, ForeignKey("emr_case.id"))
    lab_no = Column(String, nullable=False, unique=True)
    barcode = Column(String)
    material_type_id = Column(Integer, ForeignKey("ref_material_types.id"), nullable=False)
    material_location = Column(String)
    medium = Column(String)
    study_kind = Column(String, CheckConstraint("study_kind in ('primary','repeat')"))
    ordered_at = Column(DateTime)
    taken_at = Column(DateTime)
    delivered_at = Column(DateTime)
    growth_result_at = Column(DateTime)
    growth_flag = Column(Integer, CheckConstraint("growth_flag in (0,1)"))
    colony_desc = Column(Text)
    microscopy = Column(Text)
    cfu = Column(String)
    qc_due_at = Column(DateTime)
    qc_status = Column(String, CheckConstraint("qc_status in ('valid','conditional','rejected')"))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))


class LabMicrobeIsolation(Base):
    __tablename__ = "lab_microbe_isolation"

    id = Column(Integer, primary_key=True)
    lab_sample_id = Column(Integer, ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False)
    microorganism_id = Column(Integer, ForeignKey("ref_microorganisms.id"))
    microorganism_free = Column(Text)
    notes = Column(Text)


class LabAbxSusceptibility(Base):
    __tablename__ = "lab_abx_susceptibility"

    id = Column(Integer, primary_key=True)
    lab_sample_id = Column(Integer, ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False)
    antibiotic_id = Column(Integer, ForeignKey("ref_antibiotics.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("ref_antibiotic_groups.id"))
    ris = Column(String, CheckConstraint("ris in ('R','I','S')"))
    mic_mg_l = Column(Integer)
    method = Column(String)


class LabPhagePanelResult(Base):
    __tablename__ = "lab_phage_panel_result"

    id = Column(Integer, primary_key=True)
    lab_sample_id = Column(Integer, ForeignKey("lab_sample.id", ondelete="CASCADE"), nullable=False)
    phage_id = Column(Integer, ForeignKey("ref_phages.id"))
    phage_free = Column(Text)
    lysis_diameter_mm = Column(Integer)


class SanitarySample(Base):
    __tablename__ = "sanitary_sample"

    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    room = Column(String)
    sampling_point = Column(String, nullable=False)
    lab_no = Column(String, nullable=False, unique=True)
    barcode = Column(String)
    medium = Column(String)
    ordered_at = Column(DateTime)
    taken_at = Column(DateTime)
    delivered_at = Column(DateTime)
    growth_result_at = Column(DateTime)
    growth_flag = Column(Integer, CheckConstraint("growth_flag in (0,1)"))
    colony_desc = Column(Text)
    microscopy = Column(Text)
    cfu = Column(String)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))


class SanitaryNumberSequence(Base):
    __tablename__ = "sanitary_number_sequence"

    id = Column(Integer, primary_key=True)
    seq_date = Column(Date, nullable=False)
    last_number = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("seq_date", name="uq_sanitary_number_sequence"),)


class SanMicrobeIsolation(Base):
    __tablename__ = "san_microbe_isolation"

    id = Column(Integer, primary_key=True)
    sanitary_sample_id = Column(Integer, ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False)
    microorganism_id = Column(Integer, ForeignKey("ref_microorganisms.id"))
    microorganism_free = Column(Text)
    notes = Column(Text)


class SanAbxSusceptibility(Base):
    __tablename__ = "san_abx_susceptibility"

    id = Column(Integer, primary_key=True)
    sanitary_sample_id = Column(Integer, ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False)
    antibiotic_id = Column(Integer, ForeignKey("ref_antibiotics.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("ref_antibiotic_groups.id"))
    ris = Column(String, CheckConstraint("ris in ('R','I','S')"))
    mic_mg_l = Column(Integer)
    method = Column(String)


class SanPhagePanelResult(Base):
    __tablename__ = "san_phage_panel_result"

    id = Column(Integer, primary_key=True)
    sanitary_sample_id = Column(Integer, ForeignKey("sanitary_sample.id", ondelete="CASCADE"), nullable=False)
    phage_id = Column(Integer, ForeignKey("ref_phages.id"))
    phage_free = Column(Text)
    lysis_diameter_mm = Column(Integer)


class Form100Card(Base):
    __tablename__ = "form100_card"

    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)

    status = Column(String, nullable=False, server_default=expression.literal("DRAFT"))
    version = Column(Integer, nullable=False, server_default=expression.literal("1"))

    qr_payload = Column(Text)
    print_number = Column(String)
    corrects_id = Column(String(36))
    corrected_by_new_id = Column(String(36))

    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    middle_name = Column(String)
    birth_date = Column(Date, nullable=False)
    rank = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    dog_tag_number = Column(String)
    id_doc_type = Column(String)
    id_doc_number = Column(String)

    injury_dt = Column(DateTime)
    arrival_dt = Column(DateTime, nullable=False)
    first_aid_before = Column(Boolean, nullable=False, server_default=expression.false())
    cause_category = Column(String, nullable=False)
    is_combat = Column(Boolean)

    trauma_types_json = Column(Text, nullable=False, server_default=expression.literal("[]"))
    thermal_degree = Column(String)
    wound_types_json = Column(Text, nullable=False, server_default=expression.literal("[]"))
    features_json = Column(Text, nullable=False, server_default=expression.literal("[]"))
    other_text = Column(Text)
    diagnosis_text = Column(Text, nullable=False)
    diagnosis_code = Column(String)
    triage = Column(String)

    flag_urgent = Column(Boolean, nullable=False, server_default=expression.false())
    flag_sanitation = Column(Boolean, nullable=False, server_default=expression.false())
    flag_isolation = Column(Boolean, nullable=False, server_default=expression.false())
    flag_radiation = Column(Boolean, nullable=False, server_default=expression.false())

    care_bleeding_control = Column(String)
    care_dressing = Column(String)
    care_immobilization = Column(String)
    care_airway = Column(String)

    care_analgesia_given = Column(Boolean, nullable=False, server_default=expression.false())
    care_analgesia_details = Column(Text)
    care_antibiotic_given = Column(Boolean, nullable=False, server_default=expression.false())
    care_antibiotic_details = Column(Text)
    care_antidote_given = Column(Boolean, nullable=False, server_default=expression.false())
    care_antidote_details = Column(Text)
    care_tetanus = Column(String)
    care_other = Column(Text)

    infusion_performed = Column(Boolean, nullable=False, server_default=expression.false())
    infusion_volume_ml = Column(Integer)
    infusion_details = Column(Text)

    transfusion_performed = Column(Boolean, nullable=False, server_default=expression.false())
    transfusion_volume_ml = Column(Integer)
    transfusion_details = Column(Text)

    sanitation_performed = Column(Boolean, nullable=False, server_default=expression.false())
    sanitation_type = Column(String)
    sanitation_details = Column(Text)

    evac_destination = Column(Text)
    evac_transport = Column(String)
    evac_position = Column(String)
    evac_require_escort = Column(Boolean)
    evac_oxygen_needed = Column(Boolean)
    evac_notes = Column(Text)

    signed_by = Column(String)
    signed_at = Column(DateTime)
    seal_applied = Column(Boolean, nullable=False, server_default=expression.false())

    marks = relationship("Form100Mark", back_populates="card", cascade="all, delete-orphan")
    stages = relationship("Form100Stage", back_populates="card", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_form100_status", "status"),
        Index("idx_form100_injury_dt", "injury_dt"),
        Index("idx_form100_arrival_dt", "arrival_dt"),
        Index("idx_form100_dog_tag", "dog_tag_number"),
        Index("idx_form100_unit", "unit"),
        Index("idx_form100_name", "last_name", "first_name"),
    )


class Form100Mark(Base):
    __tablename__ = "form100_mark"

    id = Column(String(36), primary_key=True)
    card_id = Column(String(36), ForeignKey("form100_card.id", ondelete="CASCADE"), nullable=False, index=True)

    side = Column(String, nullable=False)
    type = Column(String, nullable=False)
    shape_json = Column(Text, nullable=False)
    meta_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(String)

    card = relationship("Form100Card", back_populates="marks")


class Form100Stage(Base):
    __tablename__ = "form100_stage"

    id = Column(String(36), primary_key=True)
    card_id = Column(String(36), ForeignKey("form100_card.id", ondelete="CASCADE"), nullable=False, index=True)

    stage_name = Column(String, nullable=False)
    received_at = Column(DateTime)
    updated_diagnosis_text = Column(Text)
    updated_diagnosis_code = Column(String)
    procedures_text = Column(Text)
    evac_next_destination = Column(Text)
    evac_next_dt = Column(DateTime)
    condition_at_transfer = Column(Text)
    outcome = Column(String)
    outcome_date = Column(Date)
    burial_place = Column(Text)
    signed_by = Column(String)
    signed_at = Column(DateTime)

    card = relationship("Form100Card", back_populates="stages")


class Form100V2(Base):
    __tablename__ = "form100"

    id = Column(String(36), primary_key=True)
    legacy_card_id = Column(String(36), index=True)
    emr_case_id = Column(Integer, ForeignKey("emr_case.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utc_now)
    updated_by = Column(String, nullable=False)
    status = Column(String, nullable=False, server_default=expression.literal("DRAFT"))
    version = Column(Integer, nullable=False, server_default=expression.literal("1"))
    is_archived = Column(Boolean, nullable=False, server_default=expression.false())
    artifact_path = Column(Text)
    artifact_sha256 = Column(String)

    # Denormalized fields to speed up list/filter without JSON traversal.
    main_full_name = Column(String, nullable=False, server_default=expression.literal(""))
    main_unit = Column(String)
    main_id_tag = Column(String)
    main_diagnosis = Column(Text)
    birth_date = Column(Date)
    signed_by = Column(String)
    signed_at = Column(DateTime)

    data = relationship("Form100DataV2", back_populates="form", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        Index("ix_form100_created_at", "created_at"),
        Index("ix_form100_status", "status"),
        Index("ix_form100_main_full_name", "main_full_name"),
        Index("ix_form100_main_unit", "main_unit"),
    )


class Form100DataV2(Base):
    __tablename__ = "form100_data"

    id = Column(String(36), primary_key=True)
    form100_id = Column(String(36), ForeignKey("form100.id", ondelete="CASCADE"), nullable=False, unique=True)

    stub_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    main_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    lesion_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    san_loss_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    mp_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    bottom_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    flags_json = Column(Text, nullable=False, server_default=expression.literal("{}"))
    bodymap_gender = Column(String, nullable=False, server_default=expression.literal("M"))
    bodymap_annotations_json = Column(Text, nullable=False, server_default=expression.literal("[]"))
    bodymap_tissue_types_json = Column(Text, nullable=False, server_default=expression.literal("[]"))
    raw_payload_json = Column(Text, nullable=False, server_default=expression.literal("{}"))

    form = relationship("Form100V2", back_populates="data")

    __table_args__ = (
        Index("ux_form100_data_form", "form100_id", unique=True),
    )


class DataExchangePackage(Base):
    __tablename__ = "data_exchange_package"

    id = Column(Integer, primary_key=True)
    direction = Column(String, CheckConstraint("direction in ('export','import')"))
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))
    package_format = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    notes = Column(Text)

    __table_args__ = (
        Index("ix_data_exchange_package_direction_created_at", "direction", "created_at"),
    )


class ReportRun(Base):
    __tablename__ = "report_run"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String, nullable=False)
    filters_json = Column(Text, nullable=False)
    result_summary_json = Column(Text, nullable=False)
    artifact_path = Column(String)
    artifact_sha256 = Column(String)

    __table_args__ = (
        Index("ix_report_run_created_at", "created_at"),
        Index("ix_report_run_report_type_created_at", "report_type", "created_at"),
    )


class SavedFilter(Base):
    __tablename__ = "saved_filters"

    id = Column(Integer, primary_key=True)
    filter_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    created_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("filter_type", "name", name="uq_saved_filters_type_name"),
        Index("ix_saved_filters_type_created_at", "filter_type", "created_at"),
    )
