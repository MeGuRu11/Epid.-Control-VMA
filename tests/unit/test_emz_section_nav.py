from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import Qt

from app.ui.emz.widgets.emz_section_nav import EmzSectionNavBar


@pytest.fixture
def nav(qtbot: Any) -> EmzSectionNavBar:
    widget = EmzSectionNavBar()
    qtbot.addWidget(widget)
    return widget


def test_default_chip_titles(nav: EmzSectionNavBar) -> None:
    assert nav._chips["patient"].text() == "Основное"
    assert nav._chips["diagnoses"].text() == "Диагнозы"
    assert nav._chips["interventions"].text() == "Вмешательства"
    assert nav._chips["antibiotics"].text() == "Антибиотики"
    assert nav._chips["ismp"].text() == "ИСМП"


def test_update_counts_shows_count(nav: EmzSectionNavBar) -> None:
    nav.update_counts(
        {
            "patient": 0,
            "diagnoses": 3,
            "interventions": 0,
            "antibiotics": 1,
            "ismp": 0,
        }
    )

    assert nav._chips["diagnoses"].text() == "Диагнозы (3)"
    assert nav._chips["interventions"].text() == "Вмешательства"
    assert nav._chips["antibiotics"].text() == "Антибиотики (1)"


def test_patient_chip_has_error_when_missing(nav: EmzSectionNavBar) -> None:
    nav.update_counts(
        {
            "patient": 2,
            "diagnoses": 0,
            "interventions": 0,
            "antibiotics": 0,
            "ismp": 0,
        }
    )

    assert nav._chips["patient"].property("hasError") is True


def test_navigate_signal(nav: EmzSectionNavBar, qtbot: Any) -> None:
    with qtbot.waitSignal(nav.navigate_requested, timeout=200) as blocker:
        qtbot.mouseClick(nav._chips["diagnoses"], Qt.MouseButton.LeftButton)

    assert blocker.args == ["diagnoses"]
