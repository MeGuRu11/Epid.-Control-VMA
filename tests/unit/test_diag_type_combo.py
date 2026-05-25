from __future__ import annotations

from typing import Any

from app.ui.emz.form_widget_factories import create_diag_type_combo


def test_default_is_empty(qtbot: Any) -> None:
    combo = create_diag_type_combo()
    qtbot.addWidget(combo)

    assert combo.objectName() == "emzDiagTypeCombo"
    assert combo.currentText() == ""
    assert combo.property("pillVariant") == ""


def test_pill_variant_on_selection(qtbot: Any) -> None:
    combo = create_diag_type_combo()
    qtbot.addWidget(combo)

    combo.setCurrentText("Поступление")
    assert combo.property("pillVariant") == "accent"
    combo.setCurrentText("Выписка")
    assert combo.property("pillVariant") == "success"
    combo.setCurrentText("Осложнение")
    assert combo.property("pillVariant") == "danger"
    combo.setCurrentText("Перевод")
    assert combo.property("pillVariant") == "info"
