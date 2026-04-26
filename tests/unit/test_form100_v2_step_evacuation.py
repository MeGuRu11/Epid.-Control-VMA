from __future__ import annotations

from app.ui.form100_v2.wizard_widgets.form100_stub_widget import Form100StubWidget
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_evacuation import StepEvacuation


def test_form100_stub_evacuation_has_two_transport_choices(qapp) -> None:
    widget = Form100StubWidget()
    widget.show()
    qapp.processEvents()

    buttons = widget.stub_evacuation_method.buttons()
    assert [button.text() for button in buttons] == ["Самолётом", "Сан. груз. авто."]

    widget._set_evacuation_method("airplane")
    assert widget.collect()["stub_evacuation_method"] == "airplane"

    widget._set_evacuation_method("ambu")
    assert widget.collect()["stub_evacuation_method"] == "ambu"

    widget._set_evacuation_method("truck")
    assert widget.collect()["stub_evacuation_method"] == "ambu"

    widget.close()


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
