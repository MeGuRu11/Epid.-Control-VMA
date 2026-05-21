from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from app.ui.widgets.susceptibility_panel import SusceptibilityPanel


class _ReferenceServiceStub:
    def list_antibiotics(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(id=1, code="AMK", name="Amikacin"),
            SimpleNamespace(id=2, code="CIP", name="Ciprofloxacin"),
        ]

    def list_phages(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(id=10, code="PH", name="Бактериофаг"),
            SimpleNamespace(id=11, code=None, name="Свободный фаг"),
        ]


def _panel(qtbot: Any) -> SusceptibilityPanel:
    service = _ReferenceServiceStub()
    panel = SusceptibilityPanel(
        antibiotics_service=cast(Any, service),
        phages_service=cast(Any, service),
    )
    qtbot.addWidget(panel)
    return panel


def test_susceptibility_panel_add_row(qtbot: Any) -> None:
    panel = _panel(qtbot)

    assert panel.susc_table.rowCount() == 1

    panel._add_susc_row()

    assert panel.susc_table.rowCount() == 2
    combo = panel.susc_table.cellWidget(1, 0)
    assert isinstance(combo, QComboBox)
    assert combo.findData(2) >= 0


def test_susceptibility_panel_apply_templates_only_fills_empty(qtbot: Any) -> None:
    panel = _panel(qtbot)
    abx_combo = cast(QComboBox, panel.susc_table.cellWidget(0, 0))
    abx_combo.setCurrentIndex(abx_combo.findData(1))
    panel.susc_table.setItem(0, 1, QTableWidgetItem("R"))

    phage_combo = cast(QComboBox, panel.phage_table.cellWidget(0, 0))
    phage_combo.setCurrentIndex(phage_combo.findData(10))
    panel.phage_table.setItem(0, 2, QTableWidgetItem("7"))

    panel.apply_default_templates()

    assert panel.susc_table.item(0, 1).text() == "R"
    assert panel.susc_table.item(0, 3).text() == "disk"
    assert panel.phage_table.item(0, 2).text() == "7"


def test_susceptibility_panel_get_rows(qtbot: Any) -> None:
    panel = _panel(qtbot)
    abx_combo = cast(QComboBox, panel.susc_table.cellWidget(0, 0))
    abx_combo.setCurrentIndex(abx_combo.findData(2))
    panel.susc_table.setItem(0, 1, QTableWidgetItem("S"))
    panel.susc_table.setItem(0, 2, QTableWidgetItem("0.5"))
    panel.susc_table.setItem(0, 3, QTableWidgetItem("disk"))

    phage_combo = cast(QComboBox, panel.phage_table.cellWidget(0, 0))
    phage_combo.setCurrentIndex(phage_combo.findData(10))
    panel.phage_table.setItem(0, 1, QTableWidgetItem("custom"))
    panel.phage_table.setItem(0, 2, QTableWidgetItem("12"))

    susceptibility = panel.get_susceptibility_rows()
    phages = panel.get_phage_rows()

    assert susceptibility[0].row_number == 1
    assert susceptibility[0].antibiotic_id == 2
    assert susceptibility[0].ris == "S"
    assert susceptibility[0].mic_text == "0.5"
    assert susceptibility[0].method == "disk"
    assert phages[0].row_number == 1
    assert phages[0].phage_id == 10
    assert phages[0].phage_free == "custom"
    assert phages[0].diameter_text == "12"
