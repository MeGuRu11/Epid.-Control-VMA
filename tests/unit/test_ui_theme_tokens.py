from __future__ import annotations

from app.config import Settings
from app.ui.theme import COL, apply_theme


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
