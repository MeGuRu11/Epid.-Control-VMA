from __future__ import annotations

from typing import Any

import pytest

from app.ui.emz.widgets.emz_save_footer import EmzSaveFooter


@pytest.fixture
def footer(qtbot: Any) -> EmzSaveFooter:
    widget = EmzSaveFooter()
    qtbot.addWidget(widget)
    return widget


def test_disabled_when_missing(footer: EmzSaveFooter) -> None:
    footer.set_state(missing_required=2, save_label="Сохранить ЭМЗ")

    assert not footer.save_btn.isEnabled()
    assert "2" in footer.status_label.text()


def test_enabled_when_complete(footer: EmzSaveFooter) -> None:
    footer.set_state(missing_required=0, save_label="Сохранить ЭМЗ")

    assert footer.save_btn.isEnabled()


def test_save_label_in_edit_mode(footer: EmzSaveFooter) -> None:
    footer.set_state(missing_required=0, save_label="Сохранить изменения")

    assert footer.save_btn.text() == "Сохранить изменения"


def test_save_signal(footer: EmzSaveFooter, qtbot: Any) -> None:
    footer.set_state(missing_required=0, save_label="Сохранить ЭМЗ")

    with qtbot.waitSignal(footer.save_requested, timeout=200):
        footer.save_btn.click()
