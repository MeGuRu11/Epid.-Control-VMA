from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from app.application.dto.auth_dto import SessionContext
from app.ui.form100_v2.form100_wizard import Form100Wizard


class _Form100ServiceStub:
    pass


def _make_wizard(qapp) -> Form100Wizard:
    wizard = Form100Wizard(
        form100_service=cast(Any, _Form100ServiceStub()),
        session=SessionContext(user_id=1, login="tester", role="admin"),
        card=None,
    )
    wizard.show()
    qapp.processEvents()
    return wizard


def test_form100_enter_does_not_trigger_evacuation_button(qapp) -> None:
    wizard = _make_wizard(qapp)
    try:
        assert wizard._step1._stub.stub_evacuation_dest.value() == ""
        assert wizard._current_step == 0

        wizard._step1.birth_date.setDate(wizard._step1.birth_date.minimumDate())
        wizard._step1.birth_date.setFocus()
        qapp.processEvents()
        QTest.keyClick(wizard._step1.birth_date, Qt.Key.Key_Return)
        qapp.processEvents()

        assert wizard._step1._stub.stub_evacuation_dest.value() == ""
        assert wizard._current_step == 0
    finally:
        wizard.close()


def test_form100_no_button_is_default(qapp) -> None:
    wizard = _make_wizard(qapp)
    try:
        buttons = cast(list[QPushButton], wizard.findChildren(QPushButton))
        assert buttons
        for button in buttons:
            assert not button.isDefault()
            assert not button.autoDefault()
    finally:
        wizard.close()
