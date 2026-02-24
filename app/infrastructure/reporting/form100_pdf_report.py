from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def export_form100_pdf(
    *,
    card: dict[str, Any],
    marks: list[dict[str, Any]],
    stages: list[dict[str, Any]],
    file_path: Path,
) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    unicode_font = get_pdf_unicode_font_name()
    doc = SimpleDocTemplate(str(file_path), pagesize=A4)

    header_data = [
        ["Форма 100", "Карточка медицинской эвакуации"],
        ["ID", str(card.get("id", ""))],
        ["Статус", str(card.get("status", ""))],
        [
            "Пациент",
            " ".join(
                part for part in [card.get("last_name"), card.get("first_name"), card.get("middle_name")] if part
            ),
        ],
        ["Дата рождения", _fmt(card.get("birth_date"))],
        ["Подразделение", str(card.get("unit", ""))],
        ["Дата поступления", _fmt(card.get("arrival_dt"))],
    ]
    diagnosis_data = [
        ["Диагноз", str(card.get("diagnosis_text", ""))],
        ["МКБ-10", str(card.get("diagnosis_code", "") or "")],
        ["Категория причины", str(card.get("cause_category", "") or "")],
        ["Триаж", str(card.get("triage", "") or "")],
    ]
    stage_table_data = [["Этап", "Время", "Диагноз", "Исход"]]
    for stage in stages:
        stage_table_data.append(
            [
                str(stage.get("stage_name", "")),
                _fmt(stage.get("received_at")),
                str(stage.get("updated_diagnosis_text", "") or ""),
                str(stage.get("outcome", "") or ""),
            ]
        )
    if len(stage_table_data) == 1:
        stage_table_data.append(["-", "-", "-", "-"])

    mark_table_data = [["Отметки bodymap", "Количество"]]
    mark_table_data.append(["Всего", str(len(marks))])

    elements = [
        _styled_table(header_data, unicode_font=unicode_font, col_widths=[45 * mm, 140 * mm]),
        Spacer(1, 6 * mm),
        _styled_table(diagnosis_data, unicode_font=unicode_font, col_widths=[45 * mm, 140 * mm]),
        Spacer(1, 6 * mm),
        _styled_table(stage_table_data, unicode_font=unicode_font, repeat_rows=1),
        Spacer(1, 6 * mm),
        _styled_table(mark_table_data, unicode_font=unicode_font),
    ]
    doc.build(elements)


def _styled_table(
    data: list[list[str]],
    *,
    unicode_font: str,
    repeat_rows: int = 0,
    col_widths: list[float] | None = None,
) -> Table:
    table = Table(data, repeatRows=repeat_rows, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _fmt(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value or "")
