from __future__ import annotations

import json

from app.application.dto.form100_v2_dto import Form100DataV2Dto
from app.ui.form100_v2.form100_wizard import _build_structured_data, _build_wizard_payload


def test_build_structured_data_maps_flat_payload_and_markers() -> None:
    payload = {
        "stub_full_name": "Иванов Иван",
        "main_full_name": "Иванов Иван",
        "main_unit": "1 рота",
        "main_diagnosis": "Огнестрельное ранение",
        "lesion_gunshot": "1",
        "isolation_required": "0",
        "mp_antibiotic": "1",
        "mp_antibiotic_dose": "500 мг",
        "flag_emergency": "1",
        "bodymap_gender": "F",
        "bodymap_tissue_types_json": json.dumps(["мягкие ткани"], ensure_ascii=False),
    }
    markers = [
        {
            "annotation_type": "WOUND_X",
            "x": 0.4,
            "y": 0.2,
            "silhouette": "female_front",
            "note": "",
            "shape_json": {},
        }
    ]

    data = _build_structured_data(payload, markers)

    assert data.main["main_full_name"] == "Иванов Иван"
    assert data.main["main_unit"] == "1 рота"
    assert data.bottom["main_diagnosis"] == "Огнестрельное ранение"
    assert data.lesion["lesion_gunshot"] is True
    assert data.lesion["isolation_required"] is False
    assert data.medical_help["mp_antibiotic"] is True
    assert data.medical_help["mp_antibiotic_dose"] == "500 мг"
    assert data.flags["flag_emergency"] is True
    assert data.bodymap_gender == "F"
    assert data.bodymap_tissue_types == ["мягкие ткани"]
    assert len(data.bodymap_annotations) == 1
    assert data.raw_payload["main_full_name"] == "Иванов Иван"


def test_build_wizard_payload_prefers_structured_sections_over_raw() -> None:
    data = Form100DataV2Dto.model_validate(
        {
            "stub": {},
            "main": {"main_full_name": "Структурный ФИО", "main_unit": "2 рота"},
            "lesion": {"lesion_gunshot": True},
            "san_loss": {},
            "bodymap_gender": "M",
            "bodymap_annotations": [
                {
                    "annotation_type": "WOUND_X",
                    "x": 0.1,
                    "y": 0.2,
                    "silhouette": "male_front",
                    "note": "",
                    "shape_json": {},
                }
            ],
            "bodymap_tissue_types": ["мягкие ткани"],
            "medical_help": {"mp_antibiotic": True},
            "bottom": {"main_diagnosis": "Диагноз"},
            "flags": {},
            "raw_payload": {
                "main_full_name": "Raw Name",
                "mp_antibiotic": "0",
                "lesion_gunshot": "0",
            },
        }
    )

    payload, markers = _build_wizard_payload(data)

    assert payload["main_full_name"] == "Структурный ФИО"
    assert payload["main_unit"] == "2 рота"
    assert payload["mp_antibiotic"] == "1"
    assert payload["lesion_gunshot"] == "1"
    assert payload["main_diagnosis"] == "Диагноз"
    assert json.loads(payload["bodymap_tissue_types_json"]) == ["мягкие ткани"]
    assert len(markers) == 1
