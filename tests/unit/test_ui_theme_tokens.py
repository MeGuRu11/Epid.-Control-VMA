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


def test_apply_theme_runs_with_default_settings(qapp) -> None:
    settings = Settings()
    apply_theme(qapp, settings)
    assert qapp.styleSheet()
