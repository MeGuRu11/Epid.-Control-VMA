from __future__ import annotations

from app.config import Settings
from app.ui.theme import COL, apply_theme, theme_qcolor


def test_theme_contains_required_semantic_tokens() -> None:
    required = {
        "bg",
        "surface",
        "border",
        "text_primary",
        "accent2",
        "success",
        "warn",
        "error",
        "info",
    }
    assert required.issubset(COL.keys())
    assert COL["bg"] != ""


def test_apply_theme_runs_with_default_settings(qapp) -> None:
    settings = Settings()
    apply_theme(qapp, settings)
    stylesheet = qapp.styleSheet()
    assert stylesheet
    assert len(stylesheet) > 0
    assert "QPushButton#iconSelectToggle" in stylesheet
    assert "QGroupBox#form100Tissue QCheckBox#form100TissueCheck::indicator:checked" in stylesheet
    assert "QFrame#form100ReviewNameCard" in stylesheet


def test_theme_defines_interactive_states_for_secondary_buttons(qapp) -> None:
    settings = Settings()
    apply_theme(qapp, settings)
    stylesheet = qapp.styleSheet()

    assert "QPushButton#secondaryButton:hover" in stylesheet
    assert "QPushButton#secondaryButton:pressed" in stylesheet


def test_theme_defines_logout_dialog_and_button_styles(qapp) -> None:
    settings = Settings()
    apply_theme(qapp, settings)
    stylesheet = qapp.styleSheet()

    assert "QDialog#logoutConfirmDialog" in stylesheet
    assert "QLabel#logoutDialogIcon" in stylesheet
    assert "QPushButton#logoutConfirmButton:hover" in stylesheet
    assert "QPushButton#logoutCancelButton:hover" in stylesheet
    assert "QWidget#logoutCorner" in stylesheet
    assert f"QPushButton#logoutButton {{\n        background: transparent;\n        border: 1px solid {COL['danger_pressed']}" in stylesheet
    assert f"QPushButton#logoutButton:hover {{\n        background: {COL['error_bg']};\n        border: 1px solid {COL['danger_pressed']}" in stylesheet
    assert "QPushButton#logoutButton:pressed" in stylesheet


def test_theme_defines_antibiotic_popup_styles(qapp) -> None:
    settings = Settings()
    apply_theme(qapp, settings)
    stylesheet = qapp.styleSheet()

    assert "QFrame#abxComboPopup" in stylesheet
    assert "QListView#abxComboPopupView" in stylesheet
    assert "QListView#abxComboPopupView::item:selected" in stylesheet


def test_theme_qcolor_reads_token_and_applies_alpha() -> None:
    accent = theme_qcolor("accent2")
    faded = theme_qcolor("accent2", alpha=140)

    assert accent.name().upper() == COL["accent2"]
    assert accent.alpha() == 255
    assert faded.name().upper() == COL["accent2"]
    assert faded.alpha() == 140
