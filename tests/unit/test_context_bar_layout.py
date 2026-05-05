from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, cast

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from app.config import Settings
from app.ui.theme import apply_theme
from app.ui.widgets.context_bar import ContextBar


def _make_context_bar(qapp, width: int) -> tuple[QWidget, ContextBar]:
    apply_theme(qapp, Settings())
    parent = QWidget()
    parent.resize(width, 280)
    bar = ContextBar(
        emz_service=cast(Any, SimpleNamespace()),
        patient_service=cast(Any, SimpleNamespace()),
        on_context_change=lambda _patient_id, _case_id: None,
        parent=parent,
    )
    parent.show()
    qapp.processEvents()
    return parent, bar


def _expand_context_bar(qapp, parent: QWidget, bar: ContextBar) -> None:
    bar.content_widget.setVisible(True)
    bar.prepare_for_width(parent.width() - 16)
    bar.content_widget.setMaximumHeight(bar.content_widget.sizeHint().height())
    bar._content_effect.setOpacity(1.0)
    bar.setGeometry(8, 6, parent.width() - 16, bar.desired_height())
    bar.prepare_for_width(parent.width() - 16)
    qapp.processEvents()


def _label_by_text(bar: ContextBar, text: str) -> QLabel:
    for label in bar.findChildren(QLabel):
        if label.text() == text:
            return label
    raise AssertionError(f"Label not found: {text}")


def _button_by_text(bar: ContextBar, text: str) -> QPushButton:
    for button in bar.findChildren(QPushButton):
        if button.text() == text:
            return button
    raise AssertionError(f"Button not found: {text}")


def _assert_button_inside_parent_and_bar(bar: ContextBar, button: QPushButton) -> None:
    parent = button.parentWidget()
    assert parent is not None
    assert button.isVisible()
    assert parent.rect().contains(button.geometry())

    button_rect_in_bar = QRect(button.mapTo(bar, QPoint(0, 0)), button.size())
    assert bar.rect().contains(button_rect_in_bar)


def test_context_bar_labels_use_local_transparent_style_hooks(qapp) -> None:
    parent, bar = _make_context_bar(qapp, width=900)

    title_label = _label_by_text(bar, "Контекст пациента")
    patient_label = _label_by_text(bar, "Пациент")
    case_label = _label_by_text(bar, "Госпитализация")

    assert title_label.objectName() == "contextBarTitleLabel"
    assert patient_label.objectName() == "contextBarFieldLabel"
    assert case_label.objectName() == "contextBarFieldLabel"
    assert title_label.styleSheet() == ""
    assert patient_label.styleSheet() == ""
    assert case_label.styleSheet() == ""
    assert "QWidget#contextBar QLabel#contextBarTitleLabel" in qapp.styleSheet()
    assert "QWidget#contextBar QLabel#contextBarFieldLabel" in qapp.styleSheet()
    assert "background: transparent;" in qapp.styleSheet()

    parent.close()


def test_context_bar_field_labels_use_local_bold_font(qapp) -> None:
    parent, bar = _make_context_bar(qapp, width=900)
    _expand_context_bar(qapp, parent, bar)

    patient_label = _label_by_text(bar, "Пациент")
    case_label = _label_by_text(bar, "Госпитализация")
    title_label = _label_by_text(bar, "Контекст пациента")
    patient_value_label = _label_by_text(bar, "Пациент не выбран")
    case_value_label = _label_by_text(bar, "Госпитализация не выбрана")
    stylesheet = qapp.styleSheet()

    assert patient_label.objectName() == "contextBarFieldLabel"
    assert case_label.objectName() == "contextBarFieldLabel"
    assert patient_label.styleSheet() == ""
    assert case_label.styleSheet() == ""
    assert patient_label.font().bold() is True
    assert case_label.font().bold() is True
    assert patient_label.font().weight() >= QFont.Weight.Bold
    assert case_label.font().weight() >= QFont.Weight.Bold
    assert "QWidget#contextBar QLabel#contextBarFieldLabel" in stylesheet
    assert re.search(r"(?m)^\s*QLabel#contextBarFieldLabel\b", stylesheet) is None
    assert "font-weight: bold;" in stylesheet
    assert title_label.objectName() == "contextBarTitleLabel"
    assert title_label.objectName() != "contextBarFieldLabel"
    assert bar.patient_search.font().bold() is False
    assert bar.case_search.font().bold() is False
    assert bar.patient_search.font().weight() < QFont.Weight.Bold
    assert bar.case_search.font().weight() < QFont.Weight.Bold
    assert patient_value_label.objectName() == "chipLabel"
    assert case_value_label.objectName() == "chipLabel"
    assert patient_value_label.font().weight() < QFont.Weight.Bold
    assert case_value_label.font().weight() < QFont.Weight.Bold
    for button in (
        bar.find_patient_btn,
        bar.select_case_btn,
        bar.change_btn,
        bar.last_patient_btn,
        bar.reset_btn,
    ):
        assert button.objectName() != "contextBarFieldLabel"
        assert button.styleSheet() == ""

    parent.close()


def test_context_bar_title_host_uses_local_transparent_contract(qapp) -> None:
    parent, bar = _make_context_bar(qapp, width=1600)

    title_label = _label_by_text(bar, "Контекст пациента")
    title_host = title_label.parentWidget()

    assert title_host is not None
    assert title_host.objectName() == "contextBarTitleHost"
    assert title_host.styleSheet() == ""
    assert title_host.autoFillBackground() is False
    assert title_label.objectName() == "contextBarTitleLabel"
    assert title_host.objectName() not in {
        "sectionTitle",
        "chip",
        "card",
        "surface",
        "contextPinnedChips",
        "patientPinnedChip",
        "casePinnedChip",
    }
    assert "QWidget#contextBar QWidget#contextBarTitleHost" in qapp.styleSheet()

    parent.close()


@pytest.mark.parametrize("width", [1600, 900, 560])
def test_context_bar_actions_group_uses_local_transparent_contract(
    qapp,
    width: int,
) -> None:
    parent, bar = _make_context_bar(qapp, width=width)
    bar.prepare_for_width(parent.width() - 16)
    bar.setGeometry(8, 6, parent.width() - 16, bar.desired_height())
    bar.prepare_for_width(parent.width() - 16)
    qapp.processEvents()

    actions_group = bar._actions_group

    assert actions_group.objectName() == "contextCompactActions"
    assert actions_group.styleSheet() == ""
    assert actions_group.autoFillBackground() is False
    assert actions_group.objectName() not in {
        "sectionTitle",
        "chip",
        "card",
        "surface",
        "contextPinnedChips",
        "patientPinnedChip",
        "casePinnedChip",
    }
    assert "QWidget#contextBar QWidget#contextCompactActions" in qapp.styleSheet()
    for button in (bar.change_btn, bar.last_patient_btn, bar.reset_btn):
        _assert_button_inside_parent_and_bar(bar, button)

    parent.close()


@pytest.mark.parametrize("width", [1600, 900, 560])
def test_context_bar_find_button_stays_inside_container(qapp, width: int) -> None:
    parent, bar = _make_context_bar(qapp, width=width)
    _expand_context_bar(qapp, parent, bar)

    _assert_button_inside_parent_and_bar(bar, _button_by_text(bar, "Найти"))

    parent.close()


@pytest.mark.parametrize("width", [1600, 900, 560])
def test_context_bar_select_by_id_button_stays_inside_container(qapp, width: int) -> None:
    parent, bar = _make_context_bar(qapp, width=width)
    _expand_context_bar(qapp, parent, bar)

    _assert_button_inside_parent_and_bar(bar, _button_by_text(bar, "Выбрать по ID"))

    parent.close()
