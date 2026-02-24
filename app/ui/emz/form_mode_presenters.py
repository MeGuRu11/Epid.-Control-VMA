from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditModeUiState:
    quick_save_text: str
    show_quick_actions: bool
    patient_hint: str | None
    patient_read_only: bool
    form_read_only: bool


def patient_hint_for_read_only(*, read_only: bool, edit_mode: bool) -> str:
    if read_only:
        return "Просмотр ЭМЗ: данные пациента редактируются кнопкой «Редактировать пациента»."
    if edit_mode:
        return "Редактирование ЭМЗ: внесите изменения и сохраните."
    return "Создание ЭМЗ: заполните данные пациента."


def build_edit_mode_ui_state(enabled: bool) -> EditModeUiState:
    if enabled:
        return EditModeUiState(
            quick_save_text="Сохранить изменения",
            show_quick_actions=False,
            patient_hint="Редактирование ЭМЗ: внесите изменения и сохраните.",
            patient_read_only=False,
            form_read_only=False,
        )
    return EditModeUiState(
        quick_save_text="Сохранить ЭМЗ",
        show_quick_actions=True,
        patient_hint=None,
        patient_read_only=False,
        form_read_only=False,
    )


def build_new_case_access_state(edit_mode: bool) -> tuple[bool, bool, str | None]:
    if edit_mode:
        return False, False, None
    return True, False, "Новая госпитализация: заполните данные."
