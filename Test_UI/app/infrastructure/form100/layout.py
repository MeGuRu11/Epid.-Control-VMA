from __future__ import annotations

from pathlib import Path
from typing import Mapping

# Canonical annotation types from Form100 section spec.
FORM100_ANNOTATION_TYPES: tuple[str, ...] = (
    "WOUND_X",
    "BURN_HATCH",
    "AMPUTATION",
    "TOURNIQUET",
    "NOTE_PIN",
)

FORM100_ANNOTATION_LABELS: dict[str, str] = {
    "WOUND_X": "Рана (X)",
    "BURN_HATCH": "Ожог",
    "AMPUTATION": "Ампутация",
    "TOURNIQUET": "Жгут",
    "NOTE_PIN": "Заметка",
}

# Backward-compatible aliases for historical payload/marker values.
FORM100_MARKER_LEGACY_ALIASES: dict[str, str] = {
    "O": "WOUND_X",
    "Я": "NOTE_PIN",
    "X": "AMPUTATION",
    "Бак": "NOTE_PIN",
    "Другие пораж.": "NOTE_PIN",
    "Отм.": "BURN_HATCH",
    "Б": "BURN_HATCH",
    "И": "NOTE_PIN",
}

# Keep legacy public name used across the codebase.
FORM100_MARKER_TYPES: tuple[str, ...] = FORM100_ANNOTATION_TYPES

# Relative to full front template image (0..1).
BODYMAP_ZONES: dict[str, tuple[float, float, float, float]] = {
    "front": (0.365, 0.345, 0.108, 0.318),
    "back": (0.472, 0.345, 0.108, 0.318),
}

# Editable text fields placed over the form template.
# Coordinates are normalized to the full image (top-left anchor + width/height).
FORM100_FIELDS: tuple[dict[str, object], ...] = (
    # Stub (left part)
    {"key": "stub_issued_time", "x": 0.030, "y": 0.100, "w": 0.240, "h": 0.030, "font": 7.5},
    {"key": "stub_rank", "x": 0.030, "y": 0.142, "w": 0.105, "h": 0.026, "font": 7.5},
    {"key": "stub_unit", "x": 0.165, "y": 0.142, "w": 0.105, "h": 0.026, "font": 7.5},
    {"key": "stub_full_name", "x": 0.060, "y": 0.182, "w": 0.205, "h": 0.026, "font": 7.5},
    {"key": "stub_id_tag", "x": 0.038, "y": 0.230, "w": 0.225, "h": 0.026, "font": 7.5},
    {"key": "stub_injury_time", "x": 0.038, "y": 0.270, "w": 0.225, "h": 0.026, "font": 7.5},
    {"key": "stub_diagnosis", "x": 0.048, "y": 0.840, "w": 0.220, "h": 0.050, "font": 8.0, "multiline": True},
    # Main central card
    {"key": "main_issued_place", "x": 0.367, "y": 0.122, "w": 0.275, "h": 0.028, "font": 8.0},
    {"key": "main_issued_time", "x": 0.367, "y": 0.162, "w": 0.275, "h": 0.028, "font": 8.0},
    {"key": "main_rank", "x": 0.367, "y": 0.202, "w": 0.130, "h": 0.028, "font": 8.0},
    {"key": "main_unit", "x": 0.512, "y": 0.202, "w": 0.130, "h": 0.028, "font": 8.0},
    {"key": "main_full_name", "x": 0.402, "y": 0.245, "w": 0.230, "h": 0.028, "font": 8.0},
    {"key": "main_id_tag", "x": 0.367, "y": 0.282, "w": 0.275, "h": 0.028, "font": 8.0},
    {"key": "main_injury_time", "x": 0.367, "y": 0.320, "w": 0.275, "h": 0.028, "font": 8.0},
    {"key": "tourniquet_time", "x": 0.640, "y": 0.548, "w": 0.160, "h": 0.030, "font": 8.0},
    {"key": "sanitation_type", "x": 0.640, "y": 0.584, "w": 0.160, "h": 0.030, "font": 8.0},
    {"key": "evacuation_dest", "x": 0.640, "y": 0.620, "w": 0.160, "h": 0.030, "font": 8.0},
    {"key": "main_diagnosis", "x": 0.405, "y": 0.690, "w": 0.235, "h": 0.074, "font": 8.0, "multiline": True},
    {"key": "evacuation_priority", "x": 0.678, "y": 0.735, "w": 0.118, "h": 0.028, "font": 8.0},
    {"key": "doctor_signature", "x": 0.654, "y": 0.874, "w": 0.188, "h": 0.028, "font": 8.0},
    # Right treatment table
    {"key": "mp_antibiotic_dose", "x": 0.844, "y": 0.190, "w": 0.062, "h": 0.030, "font": 8.0},
    {"key": "mp_antibiotic", "x": 0.712, "y": 0.230, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_serum_dose", "x": 0.712, "y": 0.265, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_toxoid", "x": 0.712, "y": 0.300, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_antidote", "x": 0.712, "y": 0.335, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_analgesic_dose", "x": 0.712, "y": 0.370, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_transfusion_blood", "x": 0.712, "y": 0.407, "w": 0.190, "h": 0.028, "font": 7.7},
    {"key": "mp_immobilization", "x": 0.712, "y": 0.442, "w": 0.190, "h": 0.028, "font": 7.7},
)

# Backward compatibility aliases: old payload key -> canonical key.
FORM100_KEY_ALIASES: dict[str, str] = {
    "stub_fio": "stub_full_name",
    "stub_doc_no": "stub_id_tag",
    "stub_wound_time": "stub_injury_time",
    "main_issued_org": "main_issued_place",
    "main_fio": "main_full_name",
    "main_doc_no": "main_id_tag",
    "main_wound_time": "main_injury_time",
    "main_tourniquet": "tourniquet_time",
    "main_sanitary": "sanitation_type",
    "main_evacuation": "evacuation_dest",
    "main_evac_priority": "evacuation_priority",
    "main_doctor_sign": "doctor_signature",
    "med_dose": "mp_antibiotic_dose",
    "med_antibiotic": "mp_antibiotic",
    "med_serum": "mp_serum_dose",
    "med_anatoxin": "mp_toxoid",
    "med_antidote": "mp_antidote",
    "med_painkiller": "mp_analgesic_dose",
    "med_transfusion": "mp_transfusion_blood",
    "med_immobilization": "mp_immobilization",
    "notes": "main_diagnosis",
}

# Canonical payload keys that are not editable on the current WYSIWYG overlay yet.
FORM100_EXTRA_PAYLOAD_KEYS: tuple[str, ...] = (
    "stub_issued_date",
    "stub_injury_date",
    "stub_evacuation_method",
    "stub_evacuation_dest",
    "stub_med_help_json",
    "stub_antibiotic_dose",
    "stub_pss_pgs_dose",
    "stub_toxoid_type",
    "stub_antidote_type",
    "stub_analgesic_dose",
    "stub_transfusion",
    "stub_immobilization",
    "stub_tourniquet",
    "main_issued_date",
    "main_injury_date",
    "lesion_json",
    "san_loss_json",
    "lesion_gunshot",
    "lesion_nuclear",
    "lesion_chemical",
    "lesion_biological",
    "lesion_other",
    "lesion_frostbite",
    "lesion_burn",
    "lesion_misc",
    "san_loss_gunshot",
    "san_loss_nuclear",
    "san_loss_chemical",
    "san_loss_biological",
    "san_loss_other",
    "san_loss_frostbite",
    "san_loss_burn",
    "san_loss_misc",
    "isolation_required",
    "bodymap_annotations_json",
    "bodymap_tissue_types_json",
    "mp_serum_pss",
    "mp_serum_pgs",
    "mp_analgesic",
    "mp_transfusion_substitute",
    "mp_bandage",
    "transport_type",
    "flag_emergency",
    "flag_radiation",
    "flag_sanitation",
)


def form100_widget_keys() -> tuple[str, ...]:
    return tuple(str(spec["key"]) for spec in FORM100_FIELDS)


def form100_payload_keys() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*form100_widget_keys(), *FORM100_EXTRA_PAYLOAD_KEYS)).keys())


def empty_form100_payload() -> dict[str, str]:
    return {key: "" for key in form100_payload_keys()}


def normalize_form100_payload(payload: Mapping[str, object] | None) -> dict[str, str]:
    payload = payload or {}
    normalized = empty_form100_payload()
    remapped: dict[str, object] = dict(payload)
    for old_key, new_key in FORM100_KEY_ALIASES.items():
        if old_key in remapped and new_key not in remapped:
            remapped[new_key] = remapped[old_key]

    for key in tuple(normalized):
        value = remapped.get(key)
        if value is None:
            normalized[key] = ""
            continue
        normalized[key] = str(value).strip()

    # Keep unknown future keys to avoid data loss in mixed-version environments.
    legacy_keys = set(FORM100_KEY_ALIASES)
    known_keys = set(normalized)
    for key, value in remapped.items():
        if not isinstance(key, str):
            continue
        if key in known_keys or key in legacy_keys:
            continue
        if value is None:
            normalized[key] = ""
            continue
        normalized[key] = str(value).strip()
    return normalized


def resolve_template_path() -> Path | None:
    root = Path.cwd()
    candidates = [
        root / "resources" / "form100" / "template_v22_front.png",
        root / "resources" / "template_v22_front.png",
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None
