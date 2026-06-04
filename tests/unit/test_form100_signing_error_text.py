from __future__ import annotations

import re

import pytest

from app.domain.rules.form100_rules_v2 import (
    FORM100_SIGNING_REQUIRED_FIELDS,
    FieldError,
    Form100SigningError,
    validate_for_signing,
)
from app.ui.form100_v2.signing_errors import (
    FORM100_SIGNING_FIELD_LABELS,
    FORM100_SIGNING_UI_REQUIRED_FIELDS,
    form100_signing_error_text,
)


def test_form100_sign_errors_have_no_raw_field_keys() -> None:
    text = form100_signing_error_text(
        Form100SigningError(
            [
                FieldError("main.main_injury_date", "Укажите дату ранения или заболевания."),
                FieldError(
                    "lesion_or_san_loss",
                    "Укажите вид поражения или вид санитарных потерь.",
                ),
                FieldError("bottom.evacuation_priority", "Укажите очередность эвакуации."),
            ]
        ),
        "Не удалось подписать карточку",
    )

    assert "main.main_injury_date" not in text
    assert "lesion_or_san_loss" not in text
    assert "bottom.evacuation_priority" not in text
    assert not re.search(r"\b[a-z]+\.[a-z_]+\b", text), text
    assert not re.search(r"\b[a-z]+_[a-z]+_[a-z]+\b", text), text


def test_form100_sign_error_uses_human_label() -> None:
    text = form100_signing_error_text(
        Form100SigningError(
            [FieldError("main.main_injury_date", "Укажите дату ранения или заболевания.")]
        ),
        "Не удалось подписать карточку",
    )

    assert "• Дата ранения: укажите дату ранения или заболевания." in text
    assert "main.main_injury_date" not in text


def test_form100_sign_error_hides_unknown_key_in_fallback() -> None:
    text = form100_signing_error_text(
        Form100SigningError([FieldError("future.raw_field_key", "Проверьте новое поле.")]),
        "Не удалось подписать карточку",
    )

    assert "future.raw_field_key" not in text
    assert "raw_field_key" not in text
    assert "• проверьте новое поле." in text


def test_form100_signing_field_labels_cover_validator_keys() -> None:
    assert {
        "main.main_full_name",
        "main.main_rank",
        "main.main_unit",
        "main.birth_date",
        "bottom.main_diagnosis",
        "main.main_injury_date",
        "main.main_injury_time",
        "signed_by",
        "lesion_or_san_loss",
        "bottom.evacuation_priority",
        "medical_help.mp_antibiotic_dose",
        "medical_help.mp_analgesic_dose",
    } <= FORM100_SIGNING_FIELD_LABELS.keys()


def test_form100_ui_required_marks_use_validator_required_field_source() -> None:
    assert set(FORM100_SIGNING_FIELD_LABELS) == FORM100_SIGNING_REQUIRED_FIELDS
    assert FORM100_SIGNING_REQUIRED_FIELDS - {"signed_by"} == FORM100_SIGNING_UI_REQUIRED_FIELDS


def test_form100_signing_validator_emits_required_field_source_keys() -> None:
    payload = {
        "main": {},
        "stub": {},
        "lesion": {},
        "san_loss": {},
        "medical_help": {"mp_antibiotic": True, "mp_analgesic": True},
        "bottom": {},
        "flags": {"flag_emergency": True},
    }

    with pytest.raises(Form100SigningError) as exc_info:
        validate_for_signing(payload, signed_by=None)

    assert {error.field for error in exc_info.value.errors} == FORM100_SIGNING_REQUIRED_FIELDS


def test_form100_signing_accepts_previously_valid_payload_without_stub_full_name() -> None:
    payload = {
        "main": {
            "main_full_name": "Иванов Иван",
            "main_rank": "капитан",
            "main_unit": "1 рота",
            "birth_date": "1990-01-02",
            "main_injury_date": "17.02.2026",
            "main_injury_time": "07:30",
        },
        "stub": {
            "stub_rank": "капитан",
            "stub_unit": "1 рота",
            "stub_injury_date": "17.02.2026",
            "stub_injury_time": "07:30",
        },
        "lesion": {"lesion_gunshot": True},
        "san_loss": {},
        "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
        "bottom": {"main_diagnosis": "Огнестрельное ранение"},
        "flags": {"flag_emergency": False},
    }

    validate_for_signing(payload, signed_by="doctor")
    assert "stub.stub_full_name" not in FORM100_SIGNING_REQUIRED_FIELDS
