from __future__ import annotations

from app.ui.form100_v2.wizard_widgets.wizard_steps.step_evacuation import StepEvacuation


def test_step_evacuation_uses_secondary_button_style(qapp) -> None:
    widget = StepEvacuation()
    widget.show()
    qapp.processEvents()

    assert widget.btn_sign.objectName() == "secondaryButton"
    assert widget.btn_sign.isHidden() is True

    widget.close()


def test_step_evacuation_shows_sign_button_only_for_draft(qapp) -> None:
    widget = StepEvacuation()
    widget.show()
    qapp.processEvents()

    widget.set_card_status("DRAFT")
    qapp.processEvents()
    assert widget.btn_sign.isVisible() is True

    widget.set_card_status("SIGNED")
    qapp.processEvents()
    assert widget.btn_sign.isHidden() is True

    widget.close()
