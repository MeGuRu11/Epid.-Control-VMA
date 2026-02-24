from __future__ import annotations

import pytest

from app.domain.rules.form100_rules_v2 import build_changed_paths_v2, validate_card_payload_v2


def test_validate_card_payload_v2_requires_main_fields() -> None:
    payload = {
        "main": {"main_full_name": "", "main_unit": "1-я рота"},
        "bottom": {"main_diagnosis": "Диагноз"},
        "medical_help": {},
        "flags": {},
        "bodymap_gender": "M",
        "bodymap_annotations": [],
        "bodymap_tissue_types": [],
    }
    with pytest.raises(ValueError, match="ФИО"):
        validate_card_payload_v2(payload)


def test_validate_card_payload_v2_requires_details_for_antibiotic() -> None:
    payload = {
        "main": {"main_full_name": "Иванов Иван", "main_unit": "1-я рота"},
        "bottom": {"main_diagnosis": "Диагноз"},
        "medical_help": {"mp_antibiotic": True, "mp_antibiotic_dose": ""},
        "flags": {},
        "bodymap_gender": "M",
        "bodymap_annotations": [],
        "bodymap_tissue_types": [],
    }
    with pytest.raises(ValueError, match="Антибиотик"):
        validate_card_payload_v2(payload)


def test_validate_card_payload_v2_checks_annotations() -> None:
    payload = {
        "main": {"main_full_name": "Иванов Иван", "main_unit": "1-я рота"},
        "bottom": {"main_diagnosis": "Диагноз"},
        "medical_help": {},
        "flags": {},
        "bodymap_gender": "M",
        "bodymap_annotations": [
            {"annotation_type": "WOUND_X", "x": 0.4, "y": 0.2, "silhouette": "male_front"},
        ],
        "bodymap_tissue_types": ["мягкие ткани"],
    }
    validate_card_payload_v2(payload)


def test_build_changed_paths_v2_returns_only_changes() -> None:
    before = {
        "status": "DRAFT",
        "version": 1,
        "flags": {"flag_emergency": False, "flag_radiation": False},
    }
    after = {
        "status": "SIGNED",
        "version": 2,
        "flags": {"flag_emergency": True, "flag_radiation": False},
    }
    changes = build_changed_paths_v2(before, after)
    assert changes["before"]["status"] == "DRAFT"
    assert changes["after"]["status"] == "SIGNED"
    assert changes["before"]["version"] == 1
    assert changes["after"]["version"] == 2
    assert changes["before"]["flags.flag_emergency"] is False
    assert changes["after"]["flags.flag_emergency"] is True
    assert "flags.flag_radiation" not in changes["before"]
