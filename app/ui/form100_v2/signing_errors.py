from __future__ import annotations

from PySide6.QtWidgets import QLabel

from app.domain.rules.form100_rules_v2 import (
    FORM100_SIGNING_REQUIRED_FIELDS,
    FieldError,
    Form100SigningError,
)
from app.ui.widgets.notifications import error_text

FORM100_REQUIRED_HINT_TEXT = "Обязательные поля отмечены *."
FORM100_SIGNING_FIELD_LABELS: dict[str, str] = {
    "main.main_full_name": "ФИО",
    "main.main_rank": "Воинское звание",
    "main.main_unit": "Воинская часть",
    "main.birth_date": "Дата рождения",
    "bottom.main_diagnosis": "Основной диагноз",
    "main.main_injury_date": "Дата ранения",
    "main.main_injury_time": "Время ранения",
    "signed_by": "Подписант",
    "lesion_or_san_loss": "Вид поражения",
    "bottom.evacuation_priority": "Очередность эвакуации",
    "medical_help.mp_antibiotic_dose": "Антибиотик",
    "medical_help.mp_analgesic_dose": "Обезболивающее",
}
FORM100_SIGNING_UI_REQUIRED_FIELDS = FORM100_SIGNING_REQUIRED_FIELDS - {"signed_by"}

_SIGNING_ERROR_HEADER = "Карточку Формы 100 нельзя подписать. Заполните обязательные поля:"


def form100_signing_error_text(exc: BaseException, fallback: str) -> str:
    if isinstance(exc, Form100SigningError):
        return format_form100_signing_errors(exc.errors)
    return error_text(exc, fallback)


def form100_required_label(field: str, text: str) -> str:
    if field not in FORM100_SIGNING_UI_REQUIRED_FIELDS:
        return text
    stripped = text.rstrip()
    suffix = ":" if stripped.endswith(":") else ""
    base = stripped[:-1].rstrip() if suffix else stripped
    if base.endswith("*"):
        return text
    return f"{base} *{suffix}"


def form100_required_hint_label() -> QLabel:
    label = QLabel(FORM100_REQUIRED_HINT_TEXT)
    label.setObjectName("muted")
    return label


def format_form100_signing_errors(errors: list[FieldError]) -> str:
    error_lines = [_humanize_validation_error(error) for error in errors]
    if not error_lines:
        return _SIGNING_ERROR_HEADER
    return f"{_SIGNING_ERROR_HEADER}\n" + "\n".join(error_lines)


def _humanize_validation_error(error: FieldError) -> str:
    message = _lowercase_first(error.message.strip())
    label = FORM100_SIGNING_FIELD_LABELS.get(error.field)
    if label is None:
        return f"• {message}"
    return f"• {label}: {message}"


def _lowercase_first(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]
