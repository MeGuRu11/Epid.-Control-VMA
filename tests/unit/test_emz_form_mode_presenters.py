from __future__ import annotations

from app.ui.emz.form_mode_presenters import (
    build_edit_mode_ui_state,
    build_new_case_access_state,
    patient_hint_for_read_only,
)


def test_patient_hint_for_read_only_variants() -> None:
    assert (
        patient_hint_for_read_only(read_only=True, edit_mode=False)
        == "Просмотр ЭМЗ: данные пациента редактируются кнопкой «Редактировать пациента»."
    )
    assert (
        patient_hint_for_read_only(read_only=False, edit_mode=True)
        == "Редактирование ЭМЗ: внесите изменения и сохраните."
    )
    assert (
        patient_hint_for_read_only(read_only=False, edit_mode=False)
        == "Создание ЭМЗ: заполните данные пациента."
    )


def test_build_edit_mode_ui_state_enabled() -> None:
    state = build_edit_mode_ui_state(True)
    assert state.quick_save_text == "Сохранить изменения"
    assert state.show_quick_actions is False
    assert state.patient_hint == "Редактирование ЭМЗ: внесите изменения и сохраните."
    assert state.patient_read_only is False
    assert state.form_read_only is False


def test_build_edit_mode_ui_state_disabled() -> None:
    state = build_edit_mode_ui_state(False)
    assert state.quick_save_text == "Сохранить ЭМЗ"
    assert state.show_quick_actions is True
    assert state.patient_hint is None
    assert state.patient_read_only is False
    assert state.form_read_only is False


def test_build_new_case_access_state_values() -> None:
    assert build_new_case_access_state(True) == (False, False, None)
    assert build_new_case_access_state(False) == (True, False, "Новая госпитализация: заполните данные.")
