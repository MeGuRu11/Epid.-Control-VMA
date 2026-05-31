from __future__ import annotations

import re

from app.domain.rules.form100_rules_v2 import FieldError, Form100SigningError
from app.ui.form100_v2.signing_errors import (
    FORM100_SIGNING_FIELD_LABELS,
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
