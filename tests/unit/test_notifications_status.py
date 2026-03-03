from __future__ import annotations

from PySide6.QtWidgets import QLabel

from app.ui.widgets.notifications import clear_status, error_text, set_status


def test_set_status_uses_dynamic_level_property(qapp) -> None:  # noqa: ARG001
    label = QLabel()
    label.setProperty("status_pill", False)

    set_status(label, "ok", "warning")

    assert label.objectName() == "statusLabel"
    assert label.property("statusLevel") == "warning"
    assert label.text() == "ok"


def test_clear_status_resets_dynamic_level_property(qapp) -> None:  # noqa: ARG001
    label = QLabel()
    label.setProperty("status_pill", False)
    set_status(label, "error", "error")

    clear_status(label)

    assert label.objectName() == "statusLabel"
    assert label.property("statusLevel") == ""
    assert label.text() == ""


def test_error_text_returns_fallback_for_empty_message() -> None:
    assert error_text(ValueError(""), fallback="fallback message") == "fallback message"
    assert error_text(ValueError("   "), fallback="fallback message") == "fallback message"
    assert error_text(ValueError("None"), fallback="fallback message") == "fallback message"


def test_error_text_keeps_original_message() -> None:
    assert error_text(ValueError("Неверные данные"), fallback="fallback message") == "Неверные данные"
