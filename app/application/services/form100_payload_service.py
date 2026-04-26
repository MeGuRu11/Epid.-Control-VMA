from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Form100StubPayloadInput:
    """Нормализованные значения блока «Корешок» формы 100."""

    issued_date: str
    issued_time: str
    rank: str
    unit: str
    full_name: str
    id_tag: str
    injury_date: str
    injury_time: str
    evacuation_method: str | None
    evacuation_dest: str | None
    med_help_underlined: list[str]
    antibiotic_dose: str
    pss_pgs_dose: str
    toxoid_type: str
    antidote_type: str
    analgesic_dose: str
    transfusion: bool
    immobilization: bool
    tourniquet: bool
    diagnosis: str


@dataclass(frozen=True)
class Form100MainPayloadInput:
    """Нормализованные значения основного идентификационного блока."""

    full_name: str
    unit: str
    id_tag: str
    rank: str
    issued_place: str
    issued_date: str
    issued_time: str
    injury_date: str
    injury_time: str
    birth_date_iso: str


@dataclass(frozen=True)
class Form100MedicalHelpPayloadInput:
    """Нормализованные значения блока медицинской помощи."""

    antibiotic: bool
    antibiotic_dose: str
    serum_pss: bool
    serum_pgs: bool
    serum_dose: str
    toxoid: str
    antidote: str
    analgesic: bool
    analgesic_dose: str
    transfusion_blood: bool
    transfusion_substitute: bool
    immobilization: bool
    bandage: bool
    serum_pss_details: str = ""
    serum_pgs_details: str = ""
    transfusion_blood_details: str = ""
    transfusion_substitute_details: str = ""
    immobilization_details: str = ""
    bandage_details: str = ""
    surgical_intervention: bool = False
    surgical_intervention_details: str = ""


@dataclass(frozen=True)
class Form100BottomPayloadInput:
    """Нормализованные значения нижнего блока формы."""

    tourniquet_time: str
    sanitation_type: str | None
    evacuation_dest: str | None
    evacuation_priority: str | None
    transport_type: str | None
    doctor_signature: str
    main_diagnosis: str


@dataclass(frozen=True)
class Form100FlagsPayloadInput:
    """Нормализованные булевы флаги формы 100."""

    emergency: bool
    radiation: bool
    sanitation: bool


@dataclass(frozen=True)
class Form100DataPayloadInput:
    """Агрегированный контейнер всех секций payload формы 100."""

    stub: Form100StubPayloadInput
    main: Form100MainPayloadInput
    lesion: dict[str, bool]
    san_loss: dict[str, bool]
    bodymap_gender: str
    bodymap_annotations: list[dict[str, Any]]
    bodymap_tissue_types: list[str]
    medical_help: Form100MedicalHelpPayloadInput
    bottom: Form100BottomPayloadInput
    flags: Form100FlagsPayloadInput


def build_form100_data_payload(payload: Form100DataPayloadInput) -> dict[str, Any]:
    """Формирует итоговый словарь `Form100DataV2Dto` из секционных входных данных."""
    return {
        "stub": {
            "stub_issued_date": payload.stub.issued_date,
            "stub_issued_time": payload.stub.issued_time,
            "stub_rank": payload.stub.rank,
            "stub_unit": payload.stub.unit,
            "stub_full_name": payload.stub.full_name,
            "stub_id_tag": payload.stub.id_tag,
            "stub_injury_date": payload.stub.injury_date,
            "stub_injury_time": payload.stub.injury_time,
            "stub_evacuation_method": payload.stub.evacuation_method,
            "stub_evacuation_dest": payload.stub.evacuation_dest,
            "stub_med_help_underline": payload.stub.med_help_underlined,
            "stub_med_help": payload.stub.med_help_underlined,
            "stub_antibiotic_dose": payload.stub.antibiotic_dose,
            "stub_pss_pgs_dose": payload.stub.pss_pgs_dose,
            "stub_toxoid_type": payload.stub.toxoid_type,
            "stub_antidote_type": payload.stub.antidote_type,
            "stub_analgesic_dose": payload.stub.analgesic_dose,
            "stub_transfusion": payload.stub.transfusion,
            "stub_immobilization": payload.stub.immobilization,
            "stub_tourniquet": payload.stub.tourniquet,
            "stub_diagnosis": payload.stub.diagnosis,
        },
        "main": {
            "main_full_name": payload.main.full_name,
            "main_unit": payload.main.unit,
            "main_id_tag": payload.main.id_tag,
            "main_rank": payload.main.rank,
            "main_issued_place": payload.main.issued_place,
            "main_issued_date": payload.main.issued_date,
            "main_issued_time": payload.main.issued_time,
            "main_injury_date": payload.main.injury_date,
            "main_injury_time": payload.main.injury_time,
            "birth_date": payload.main.birth_date_iso,
        },
        "lesion": payload.lesion,
        "san_loss": payload.san_loss,
        "bodymap_gender": payload.bodymap_gender,
        "bodymap_annotations": payload.bodymap_annotations,
        "bodymap_tissue_types": payload.bodymap_tissue_types,
        "medical_help": {
            "mp_antibiotic": payload.medical_help.antibiotic,
            "mp_antibiotic_dose": payload.medical_help.antibiotic_dose,
            "mp_serum_pss": payload.medical_help.serum_pss,
            "mp_serum_pgs": payload.medical_help.serum_pgs,
            "mp_serum_dose": payload.medical_help.serum_dose,
            "mp_serum_pss_details": payload.medical_help.serum_pss_details,
            "mp_serum_pgs_details": payload.medical_help.serum_pgs_details,
            "mp_toxoid": payload.medical_help.toxoid,
            "mp_antidote": payload.medical_help.antidote,
            "mp_analgesic": payload.medical_help.analgesic,
            "mp_analgesic_dose": payload.medical_help.analgesic_dose,
            "mp_transfusion_blood": payload.medical_help.transfusion_blood,
            "mp_transfusion_blood_details": payload.medical_help.transfusion_blood_details,
            "mp_transfusion_substitute": payload.medical_help.transfusion_substitute,
            "mp_transfusion_substitute_details": payload.medical_help.transfusion_substitute_details,
            "mp_immobilization": payload.medical_help.immobilization,
            "mp_immobilization_details": payload.medical_help.immobilization_details,
            "mp_bandage": payload.medical_help.bandage,
            "mp_bandage_details": payload.medical_help.bandage_details,
            "mp_surgical_intervention": payload.medical_help.surgical_intervention,
            "mp_surgical_intervention_details": payload.medical_help.surgical_intervention_details,
        },
        "bottom": {
            "tourniquet_time": payload.bottom.tourniquet_time,
            "sanitation_type": payload.bottom.sanitation_type,
            "evacuation_dest": payload.bottom.evacuation_dest,
            "evacuation_priority": payload.bottom.evacuation_priority,
            "transport_type": payload.bottom.transport_type,
            "doctor_signature": payload.bottom.doctor_signature,
            "main_diagnosis": payload.bottom.main_diagnosis,
        },
        "flags": {
            "flag_emergency": payload.flags.emergency,
            "flag_radiation": payload.flags.radiation,
            "flag_sanitation": payload.flags.sanitation,
        },
    }
