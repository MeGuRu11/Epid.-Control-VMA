from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.application.dto.analytics_dto import AnalyticsSampleRow, AnalyticsSearchRequest
from app.application.reporting.formatters import format_percent
from app.application.services.analytics_service import AnalyticsService
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.application.services.reference_service import ReferenceService
from app.config import DATA_DIR
from app.domain.constants import MilitaryCategory
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.session import session_scope
from app.infrastructure.reporting.pdf_determinism import build_invariant_pdf
from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name
from app.infrastructure.security.sha256 import sha256_file

REPORT_ARTIFACT_DIR = DATA_DIR / "artifacts" / "reports"

FILTER_LABELS: dict[str, str] = {
    "date_from": "Дата от",
    "date_to": "Дата до",
    "department_id": "Отделение",
    "icd10_code": "МКБ-10",
    "microorganism_id": "Микроорганизм",
    "antibiotic_id": "Антибиотик",
    "material_type_id": "Материал",
    "growth_flag": "Рост",
    "patient_category": "Категория",
    "patient_name": "ФИО пациента",
    "lab_no": "Лаб. номер",
    "search_text": "Поиск",
}

SENSITIVE_FILTER_KEYS = {"patient_name", "fio", "search_text", "lab_no", "passport", "snils"}

logger = logging.getLogger(__name__)

def _format_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        if "T" in value and len(value) >= 19:
            try:
                dt = datetime.fromisoformat(value)
                return dt.strftime("%d.%m.%Y %H:%M")
            except ValueError:
                pass
        elif len(value) == 10 and "-" in value:
            try:
                d = date.fromisoformat(value)
                return d.strftime("%d.%m.%Y")
            except ValueError:
                pass
    return value

def _format_filter_label(key: str) -> str:
    return FILTER_LABELS.get(key, key)



def _build_ismp_summary(agg: dict[str, Any], ismp: dict[str, Any]) -> dict[str, Any]:
    return {
        **agg,
        "ismp_cases": ismp.get("ismp_cases", 0),
        "ismp_incidence": ismp.get("incidence", 0.0),
        "ismp_incidence_density": ismp.get("incidence_density", 0.0),
        "ismp_prevalence": ismp.get("prevalence", 0.0),
        "ismp_by_type": ismp.get("by_type") or [],
    }

def _as_int(value: object) -> int:
    return int(cast(Any, value))


def _compute_top_microbes(rows: list[AnalyticsSampleRow], top_n: int = 10) -> list[tuple[str, int]]:
    """Топ микроорганизмов по числу положительных изолятов."""
    counts: dict[str, int] = {}
    for row in rows:
        if row.growth_flag != 1 or not row.microorganism:
            continue
        micro = str(row.microorganism)
        counts[micro] = counts.get(micro, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top_n]


def _compute_heatmap(
    rows: list[AnalyticsSampleRow],
    top_n: int = 10,
) -> tuple[dict[str, dict[str, int]], list[str], list[str]]:
    """Матрица отделение -> микроорганизм -> число положительных изолятов."""
    matrix: dict[str, dict[str, int]] = {}
    dept_totals: dict[str, int] = {}
    micro_totals: dict[str, int] = {}
    for row in rows:
        if row.growth_flag != 1 or not row.department_name or not row.microorganism:
            continue
        dept = str(row.department_name)
        micro = str(row.microorganism)
        dept_map = matrix.setdefault(dept, {})
        dept_map[micro] = dept_map.get(micro, 0) + 1
        dept_totals[dept] = dept_totals.get(dept, 0) + 1
        micro_totals[micro] = micro_totals.get(micro, 0) + 1

    top_depts = sorted(dept_totals, key=dept_totals.__getitem__, reverse=True)[:top_n]
    top_micros = sorted(micro_totals, key=micro_totals.__getitem__, reverse=True)[:top_n]
    filtered = {
        dept: {micro: matrix[dept].get(micro, 0) for micro in top_micros}
        for dept in top_depts
    }
    return filtered, top_depts, top_micros


def _compute_resistance(
    rows: list[AnalyticsSampleRow],
    top_n: int = 10,
) -> dict[str, dict[str, dict[str, int]]]:
    """Матрица микроорганизм -> антибиотик -> счетчики S/I/R."""
    matrix: dict[str, dict[str, dict[str, int]]] = {}
    micro_totals: dict[str, int] = {}
    for row in rows:
        if not row.microorganism or not row.antibiotic or not row.ris:
            continue
        ris = str(row.ris).upper()
        if ris not in {"S", "I", "R"}:
            continue
        micro = str(row.microorganism)
        antibiotic = str(row.antibiotic)
        micro_map = matrix.setdefault(micro, {})
        cell = micro_map.setdefault(antibiotic, {"S": 0, "I": 0, "R": 0, "total": 0})
        cell[ris] += 1
        cell["total"] += 1
        micro_totals[micro] = micro_totals.get(micro, 0) + 1

    top_micros = sorted(micro_totals, key=micro_totals.__getitem__, reverse=True)[:top_n]
    return {micro: matrix[micro] for micro in top_micros if micro in matrix}


class ReportingService:
    def __init__(
        self,
        analytics_service: AnalyticsService,
        form100_v2_service: Form100ServiceV2 | None = None,
        reference_service: ReferenceService | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.analytics_service = analytics_service
        self.form100_v2_service = form100_v2_service
        self.reference_service = reference_service
        self.session_factory = session_factory

    def export_analytics_xlsx(
        self,
        request: AnalyticsSearchRequest,
        file_path: str | Path,
        actor_id: int | None,
    ) -> dict[str, Any]:
        file_path = Path(file_path)
        rows = self.analytics_service.search_samples(request)
        agg = self.analytics_service.get_aggregates(request)
        ismp = self.analytics_service.get_ismp_metrics(
            date_from=request.date_from,
            date_to=request.date_to,
            department_id=request.department_id,
        )
        extended_summary = _build_ismp_summary(agg, ismp)

        wb = Workbook()
        summary_ws = wb.active
        if summary_ws is None:
            raise RuntimeError("Не удалось создать лист сводки")
        summary_ws.title = "Сводка"
        summary_ws.append(["Параметр", "Значение"])
        summary_ws.append(["Дата отчета", datetime.now(UTC).strftime("%d.%m.%Y %H:%M")])
        summary_ws.append(["Всего", agg.get("total", 0)])
        summary_ws.append(["Положительные", agg.get("positives", 0)])
        summary_ws.append(["Доля положительных", agg.get("positive_share", 0)])

        filters_ws = wb.create_sheet(title="Фильтры")
        filters_ws.append(["Фильтр", "Значение"])
        filters = request.model_dump(exclude_none=True)
        filter_maps = self._build_filter_maps()
        for key, value in filters.items():
            filters_ws.append(
                [_format_filter_label(key), self._format_filter_value(key, value, filter_maps)]
            )

        data_ws = wb.create_sheet(title="Данные")
        columns = [
            "ID",
            "Лаб. номер",
            "ФИО пациента",
            "Категория",
            "Дата взятия",
            "Отделение",
            "Материал",
            "Микроорганизм",
            "Антибиотик",
        ]
        data_ws.append(columns)
        for row in rows:
            data_ws.append(
                [
                    row.lab_sample_id,
                    row.lab_no,
                    row.patient_name,
                    row.patient_category,
                    _format_value(row.taken_at),
                    row.department_name,
                    row.material_type,
                    row.microorganism,
                    row.antibiotic,
                ]
            )

        ismp_ws = wb.create_sheet(title="ИСМП")
        ismp_ws.append(["Показатель", "Значение"])
        ismp_ws["A1"].font = Font(bold=True)
        ismp_ws["B1"].font = Font(bold=True)

        ismp_rows = [
            ("Всего госпитализаций", ismp.get("total_cases", 0)),
            ("Госпитализаций с ИСМП", ismp.get("ismp_cases", 0)),
            ("Инцидентность (на 1000 госпит.)", ismp.get("incidence", 0.0)),
            ("Плотность (на 1000 койко-дн.)", ismp.get("incidence_density", 0.0)),
            ("Превалентность", ismp.get("prevalence", 0.0) / 100),
        ]
        for label, value in ismp_rows:
            ismp_ws.append([label, value])

        for row_idx, (_, value) in enumerate(ismp_rows, start=2):
            cell = ismp_ws.cell(row=row_idx, column=2)
            if isinstance(value, float):
                if row_idx == 6:
                    cell.number_format = "0.0%"
                else:
                    cell.number_format = "0.0"

        ismp_ws.column_dimensions["A"].width = 38
        ismp_ws.column_dimensions["B"].width = 16

        by_type = cast(list[dict[str, Any]], ismp.get("by_type") or [])
        if by_type:
            ismp_ws.append([])
            ismp_ws.append(["Тип ИСМП", "Случаев", "Доля (%)"])
            header_row = ismp_ws.max_row
            for col in range(1, 4):
                ismp_ws.cell(row=header_row, column=col).font = Font(bold=True)

            total_ismp = ismp.get("ismp_total") or sum(entry.get("count", 0) for entry in by_type)
            for entry in by_type:
                count = entry.get("count", 0)
                share = (count / total_ismp * 100) if total_ismp else 0.0
                ismp_ws.append([entry.get("type", ""), count, round(share, 1)])
                share_cell = ismp_ws.cell(row=ismp_ws.max_row, column=3)
                share_cell.number_format = "0.0"
        elif ismp.get("ismp_cases", 0) == 0:
            ismp_ws.append(["Случаев ИСМП в выбранном периоде не зарегистрировано"])
        file_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(file_path)

        artifact_path = self._save_artifact_copy(report_type="analytics", source_path=file_path)
        report_hash = sha256_file(artifact_path)
        report_run_id = self._log_report_run(
            report_type="analytics",
            filters=filters,
            summary=extended_summary,
            file_path=artifact_path,
            sha256=report_hash,
            created_by=actor_id,
        )
        return {
            "path": str(file_path),
            "artifact_path": str(artifact_path),
            "count": len(rows),
            "sha256": report_hash,
            "report_run_id": report_run_id,
        }

    def export_analytics_pdf(
        self,
        request: AnalyticsSearchRequest,
        file_path: str | Path,
        actor_id: int | None,
    ) -> dict[str, Any]:
        file_path = Path(file_path)
        rows = self.analytics_service.search_samples(request)
        agg = self.analytics_service.get_aggregates(request)
        ismp = self.analytics_service.get_ismp_metrics(
            date_from=request.date_from,
            date_to=request.date_to,
            department_id=request.department_id,
        )
        dept_summary = self.analytics_service.get_department_summary(
            request.date_from,
            request.date_to,
            request.patient_category,
        )
        trend_rows = self.analytics_service.get_trend_by_day(
            request.date_from,
            request.date_to,
            request.patient_category,
        )
        ismp_by_dept = self.analytics_service.get_ismp_by_department(
            request.date_from,
            request.date_to,
        )
        top_microbes = _compute_top_microbes(rows)
        heatmap_matrix, ordered_depts, ordered_micros = _compute_heatmap(rows)
        resistance = _compute_resistance(rows)
        extended_summary = _build_ismp_summary(agg, ismp)
        filters = request.model_dump(exclude_none=True)
        filter_maps = self._build_filter_maps()
        unicode_font = get_pdf_unicode_font_name()

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        cell_style = ParagraphStyle(
            "PdfCell",
            parent=normal_style,
            fontName=unicode_font,
            fontSize=7,
            leading=8,
            wordWrap="CJK",
        )
        title_style = ParagraphStyle(
            "PdfTitle",
            parent=normal_style,
            fontName=unicode_font,
            fontSize=14,
            leading=18,
            spaceAfter=6,
        )
        section_style = ParagraphStyle(
            "PdfSection",
            parent=normal_style,
            fontName=unicode_font,
            fontSize=10,
            leading=12,
            spaceAfter=4,
            spaceBefore=4,
        )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(A4),
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
        )

        available_width = landscape(A4)[0] - 20 * mm

        filter_data: list[list[Paragraph]] = [
            [Paragraph("Фильтр", cell_style), Paragraph("Значение", cell_style)]
        ]
        for key, value in filters.items():
            filter_data.append(
                [
                    Paragraph(_format_filter_label(key), cell_style),
                    Paragraph(self._format_filter_value(key, value, filter_maps), cell_style),
                ]
            )

        headers = [
            "ID",
            "Лаб. номер",
            "ФИО пациента",
            "Категория",
            "Дата взятия",
            "Отделение",
            "Материал",
            "Микроорганизм",
            "Антибиотик",
        ]
        table_data: list[list[Paragraph]] = [[Paragraph(h, cell_style) for h in headers]]
        for row in rows:
            table_data.append(
                [
                    Paragraph(str(row.lab_sample_id), cell_style),
                    Paragraph(str(row.lab_no or ""), cell_style),
                    Paragraph(row.patient_name or "", cell_style),
                    Paragraph(row.patient_category or "", cell_style),
                    Paragraph(str(_format_value(row.taken_at) or ""), cell_style),
                    Paragraph(row.department_name or "", cell_style),
                    Paragraph(row.material_type or "", cell_style),
                    Paragraph(row.microorganism or "", cell_style),
                    Paragraph(row.antibiotic or "", cell_style),
                ]
            )

        col_widths = [
            available_width * 0.05,  # ID
            available_width * 0.08,  # Lab No
            available_width * 0.15,  # Patient
            available_width * 0.08,  # Category
            available_width * 0.08,  # Date
            available_width * 0.12,  # Department
            available_width * 0.12,  # Material
            available_width * 0.15,  # Microorganism
            available_width * 0.17,  # Antibiotic
        ]

        filter_table = Table(
            filter_data,
            repeatRows=1,
            colWidths=[available_width * 0.3, available_width * 0.7],
        )
        filter_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ]
            )
        )

        data_table = Table(table_data, repeatRows=1, colWidths=col_widths)
        data_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                ]
            )
        )

        elements: list[Any] = []
        report_date = datetime.now(UTC).strftime("%d.%m.%Y %H:%M")
        date_label = (
            f"{request.date_from} - {request.date_to}"
            if request.date_from and request.date_to
            else "весь период"
        )
        total = int(agg.get("total", 0) or 0)
        positives = int(agg.get("positives", 0) or 0)
        positive_share = float(agg.get("positive_share", 0.0) or 0.0)
        ismp_cases = int(ismp.get("ismp_cases", 0) or 0)

        elements.append(
            Paragraph(
                "<b>Аналитический отчёт по пробам</b>",
                title_style,
            )
        )
        elements.append(Paragraph(f"Период: {date_label}   Сформирован: {report_date}", cell_style))
        elements.append(Spacer(1, 8))

        kpi_data = [
            [
                Paragraph(f"<b>Всего проб</b><br/>{total}", cell_style),
                Paragraph(f"<b>Положительных</b><br/>{positives}", cell_style),
                Paragraph(f"<b>Доля положительных</b><br/>{positive_share * 100:.1f}%", cell_style),
                Paragraph(f"<b>Случаев ИСМП</b><br/>{ismp_cases}", cell_style),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[available_width * 0.25] * 4)
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F4EF")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        elements.append(kpi_table)
        elements.append(Spacer(1, 10))

        elements.append(Paragraph("<b>Параметры отчёта</b>", section_style))
        if len(filter_data) > 1:
            elements.append(filter_table)
        else:
            elements.append(Paragraph("Фильтры: не заданы.", cell_style))
        elements.append(Spacer(1, 10))

        elements.append(
            Paragraph(
                "<b>ИСМП — Инфекции, связанные с оказанием медицинской помощи</b>",
                section_style,
            )
        )
        elements.append(Spacer(1, 4))

        if ismp_cases == 0:
            elements.append(Paragraph("Случаев ИСМП в выбранном периоде не зарегистрировано.", cell_style))
        else:
            ismp_metrics_data = [
                [Paragraph("Показатель", cell_style), Paragraph("Значение", cell_style)],
                [Paragraph("Всего госпитализаций", cell_style), Paragraph(str(ismp.get("total_cases", 0)), cell_style)],
                [Paragraph("Госпитализаций с ИСМП", cell_style), Paragraph(str(ismp_cases), cell_style)],
                [
                    Paragraph("Инцидентность (на 1000 госпит.)", cell_style),
                    Paragraph(f"{ismp.get('incidence', 0.0):.1f}", cell_style),
                ],
                [
                    Paragraph("Плотность (на 1000 койко-дн.)", cell_style),
                    Paragraph(f"{ismp.get('incidence_density', 0.0):.1f}", cell_style),
                ],
                [
                    Paragraph("Превалентность", cell_style),
                    Paragraph(format_percent(ismp.get("prevalence", 0.0) / 100), cell_style),
                ],
            ]
            ismp_table = Table(ismp_metrics_data, colWidths=[available_width * 0.6, available_width * 0.4])
            ismp_table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDE4D8")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5EFE8")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(ismp_table)

            by_type = cast(list[dict[str, Any]], ismp.get("by_type") or [])
            if by_type:
                elements.append(Spacer(1, 8))
                elements.append(Paragraph("<b>Разбивка по типам ИСМП:</b>", cell_style))
                elements.append(Spacer(1, 4))
                total_ismp = ismp.get("ismp_total") or sum(entry.get("count", 0) for entry in by_type)
                type_data = [
                    [
                        Paragraph("Тип ИСМП", cell_style),
                        Paragraph("Случаев", cell_style),
                        Paragraph("Доля", cell_style),
                    ]
                ]
                for entry in by_type:
                    count = entry.get("count", 0)
                    share = (count / total_ismp * 100) if total_ismp else 0.0
                    type_data.append(
                        [
                            Paragraph(str(entry.get("type", "")), cell_style),
                            Paragraph(str(count), cell_style),
                            Paragraph(f"{share:.1f}%", cell_style),
                        ]
                    )
                type_table = Table(type_data, colWidths=[available_width * 0.5, available_width * 0.25, available_width * 0.25])
                type_table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDE4D8")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5EFE8")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                elements.append(type_table)
        if ismp_by_dept:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("<b>ИСМП по отделениям:</b>", cell_style))
            elements.append(Spacer(1, 4))
            total_dept_ismp = sum(count for _, count in ismp_by_dept)
            dept_ismp_data = [
                [
                    Paragraph("Отделение", cell_style),
                    Paragraph("Случаев", cell_style),
                    Paragraph("Доля", cell_style),
                ]
            ]
            for dept_name, count in ismp_by_dept:
                share = (count / total_dept_ismp * 100) if total_dept_ismp else 0.0
                dept_ismp_data.append(
                    [
                        Paragraph(str(dept_name), cell_style),
                        Paragraph(str(count), cell_style),
                        Paragraph(f"{share:.1f}%", cell_style),
                    ]
                )
            dept_ismp_table = Table(
                dept_ismp_data,
                colWidths=[available_width * 0.5, available_width * 0.25, available_width * 0.25],
            )
            dept_ismp_table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EDE4D8")),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5EFE8")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            elements.append(dept_ismp_table)
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Сводка по отделениям</b>", section_style))
        elements.append(Spacer(1, 6))
        if dept_summary:
            dept_headers = ["Отделение", "Всего проб", "Положительных", "Доля пол.", "Последняя проба"]
            dept_data: list[list[Paragraph]] = [[Paragraph(h, cell_style) for h in dept_headers]]
            for item in sorted(dept_summary, key=lambda row: row.get("total", 0), reverse=True):
                last = item.get("last_date")
                last_str = str(_format_value(last) or "-")
                dept_data.append(
                    [
                        Paragraph(str(item.get("department_name", "-")), cell_style),
                        Paragraph(str(item.get("total", 0)), cell_style),
                        Paragraph(str(item.get("positives", 0)), cell_style),
                        Paragraph(f"{float(item.get('positive_share', 0) or 0) * 100:.1f}%", cell_style),
                        Paragraph(last_str, cell_style),
                    ]
                )
            dept_table = Table(
                dept_data,
                repeatRows=1,
                colWidths=[
                    available_width * 0.35,
                    available_width * 0.15,
                    available_width * 0.15,
                    available_width * 0.15,
                    available_width * 0.20,
                ],
            )
            dept_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                    ]
                )
            )
            elements.append(dept_table)
        else:
            elements.append(Paragraph("Данных по отделениям нет.", cell_style))
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Топ микроорганизмов</b>", section_style))
        elements.append(Spacer(1, 6))
        if top_microbes:
            total_isolates = sum(count for _, count in top_microbes)
            micro_headers = ["Микроорганизм", "Изолятов", "Доля"]
            micro_data: list[list[Paragraph]] = [[Paragraph(h, cell_style) for h in micro_headers]]
            for name, count in top_microbes:
                share = count / total_isolates * 100 if total_isolates else 0.0
                micro_data.append(
                    [
                        Paragraph(name, cell_style),
                        Paragraph(str(count), cell_style),
                        Paragraph(f"{share:.1f}%", cell_style),
                    ]
                )
            micro_table = Table(
                micro_data,
                repeatRows=1,
                colWidths=[available_width * 0.6, available_width * 0.2, available_width * 0.2],
            )
            micro_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                    ]
                )
            )
            elements.append(micro_table)
        else:
            elements.append(Paragraph("Роста нет или данные отсутствуют.", cell_style))
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Паттерн резистентности</b>", section_style))
        elements.append(Spacer(1, 6))
        if resistance:
            all_antibiotics: list[str] = []
            for ab_map in resistance.values():
                for antibiotic in ab_map:
                    if antibiotic not in all_antibiotics:
                        all_antibiotics.append(antibiotic)
            all_antibiotics.sort()

            res_data: list[list[Paragraph]] = [
                [Paragraph("Микроорганизм", cell_style)]
                + [Paragraph(antibiotic, cell_style) for antibiotic in all_antibiotics]
            ]
            for micro, ab_map in resistance.items():
                row_cells = [Paragraph(micro, cell_style)]
                for antibiotic in all_antibiotics:
                    cell = ab_map.get(antibiotic, {})
                    if cell:
                        row_cells.append(
                            Paragraph(
                                f"R:{cell.get('R', 0)} I:{cell.get('I', 0)} S:{cell.get('S', 0)}",
                                cell_style,
                            )
                        )
                    else:
                        row_cells.append(Paragraph("-", cell_style))
                res_data.append(row_cells)

            first_col_w = available_width * 0.30
            rest_w = (available_width - first_col_w) / max(len(all_antibiotics), 1)
            res_table = Table(
                res_data,
                repeatRows=1,
                colWidths=[first_col_w] + [rest_w] * len(all_antibiotics),
            )
            res_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
            ]
            for row_idx, (_micro, ab_map) in enumerate(resistance.items(), start=1):
                for col_idx, antibiotic in enumerate(all_antibiotics, start=1):
                    cell = ab_map.get(antibiotic, {})
                    total_cell = int(cell.get("total", 0) or 0)
                    if not cell or total_cell == 0:
                        continue
                    r_share = int(cell.get("R", 0) or 0) / total_cell
                    s_share = int(cell.get("S", 0) or 0) / total_cell
                    if r_share >= 0.5:
                        bg = colors.HexColor("#FADADD")
                    elif s_share >= 0.5:
                        bg = colors.HexColor("#D5F0D5")
                    else:
                        bg = colors.HexColor("#FFF5CC")
                    res_style.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), bg))
            res_table.setStyle(TableStyle(res_style))
            elements.append(res_table)
        else:
            elements.append(Paragraph("Данных о резистентности нет (нет проб с RIS-разметкой).", cell_style))
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Heatmap: отделения × микроорганизмы</b>", section_style))
        elements.append(Spacer(1, 6))
        if heatmap_matrix and ordered_micros:
            heat_data: list[list[Paragraph]] = [
                [Paragraph("Отделение", cell_style)] + [Paragraph(micro, cell_style) for micro in ordered_micros]
            ]
            all_vals = [
                heatmap_matrix[dept].get(micro, 0)
                for dept in ordered_depts
                for micro in ordered_micros
            ]
            max_val = max(all_vals) if all_vals else 1
            for dept in ordered_depts:
                row_cells = [Paragraph(dept, cell_style)]
                for micro in ordered_micros:
                    value = heatmap_matrix[dept].get(micro, 0)
                    row_cells.append(Paragraph(str(value) if value else "-", cell_style))
                heat_data.append(row_cells)

            first_col_w = available_width * 0.30
            rest_w = (available_width - first_col_w) / max(len(ordered_micros), 1)
            heat_table = Table(
                heat_data,
                repeatRows=1,
                colWidths=[first_col_w] + [rest_w] * len(ordered_micros),
            )
            heat_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
            ]
            for row_idx, dept in enumerate(ordered_depts, start=1):
                for col_idx, micro in enumerate(ordered_micros, start=1):
                    value = heatmap_matrix[dept].get(micro, 0)
                    if value == 0 or max_val == 0:
                        continue
                    intensity = value / max_val
                    bg = colors.Color(
                        1.0,
                        (255 - intensity * (255 - 140)) / 255,
                        (255 - intensity * 255) / 255,
                    )
                    heat_style.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), bg))
            heat_table.setStyle(TableStyle(heat_style))
            elements.append(heat_table)
        else:
            elements.append(Paragraph("Недостаточно данных для построения тепловой карты.", cell_style))
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Тренд по периодам</b>", section_style))
        elements.append(Spacer(1, 6))
        if trend_rows:
            trend_headers = ["Дата", "Всего проб", "Положительных", "Доля пол."]
            trend_data: list[list[Paragraph]] = [[Paragraph(h, cell_style) for h in trend_headers]]
            for item in trend_rows:
                day_value = item.get("day")
                day_str = str(_format_value(day_value) or "-")
                total_trend = int(item.get("total", 0) or 0)
                positives_trend = int(item.get("positives", 0) or 0)
                share_trend = positives_trend / total_trend * 100 if total_trend else 0.0
                trend_data.append(
                    [
                        Paragraph(day_str, cell_style),
                        Paragraph(str(total_trend), cell_style),
                        Paragraph(str(positives_trend), cell_style),
                        Paragraph(f"{share_trend:.1f}%", cell_style),
                    ]
                )
            trend_table = Table(
                trend_data,
                repeatRows=1,
                colWidths=[available_width * 0.25] * 4,
            )
            trend_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E0D8")),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("FONTNAME", (0, 0), (-1, -1), unicode_font),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                        ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                    ]
                )
            )
            elements.append(trend_table)
        else:
            elements.append(Paragraph("Данных для построения тренда нет.", cell_style))
        elements.append(PageBreak())

        elements.append(Paragraph("<b>Таблица проб</b>", section_style))
        elements.append(Spacer(1, 6))
        elements.append(data_table)
        build_invariant_pdf(doc, elements)

        artifact_path = self._save_artifact_copy(report_type="analytics", source_path=file_path)
        report_hash = sha256_file(artifact_path)
        report_run_id = self._log_report_run(
            report_type="analytics",
            filters=filters,
            summary=extended_summary,
            file_path=artifact_path,
            sha256=report_hash,
            created_by=actor_id,
        )
        return {
            "path": str(file_path),
            "artifact_path": str(artifact_path),
            "count": len(rows),
            "sha256": report_hash,
            "report_run_id": report_run_id,
        }

    def export_form100_pdf(
        self,
        *,
        card_id: str,
        file_path: str | Path,
        actor_id: int | None,
    ) -> dict[str, Any]:
        if self.form100_v2_service is None:
            raise ValueError("Form100 service is not configured")
        if actor_id is None:
            raise ValueError("actor_id обязателен для экспорта Form100 PDF")
        file_path = Path(file_path)
        render_result = self.form100_v2_service.export_pdf(card_id=card_id, file_path=file_path, actor_id=actor_id)
        report_type = "form100"

        artifact_path = self._save_artifact_copy(report_type=report_type, source_path=file_path)
        report_hash = sha256_file(artifact_path)
        report_run_id = self._log_report_run(
            report_type=report_type,
            filters={"card_id": card_id},
            summary={"path": str(render_result.get("path", file_path)), "card_id": card_id},
            file_path=artifact_path,
            sha256=report_hash,
            created_by=actor_id,
        )
        return {
            "path": str(file_path),
            "artifact_path": str(artifact_path),
            "sha256": report_hash,
            "report_run_id": report_run_id,
            "card_id": card_id,
        }

    def list_report_runs(
        self,
        *,
        limit: int = 100,
        report_type: str | None = None,
        query: str | None = None,
        verify_hash: bool = False,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            stmt = select(models.ReportRun)
            if report_type:
                stmt = stmt.where(models.ReportRun.report_type == report_type)
            if query:
                like_pattern = f"%{query}%"
                stmt = stmt.where(
                    models.ReportRun.artifact_path.ilike(like_pattern)
                    | models.ReportRun.artifact_sha256.ilike(like_pattern)
                    | models.ReportRun.filters_json.ilike(like_pattern)
                )
            stmt = stmt.order_by(models.ReportRun.created_at.desc()).limit(limit)
            rows = list(session.execute(stmt).scalars())

        return [self._build_report_history_row(item, verify_hash=verify_hash) for item in rows]

    def verify_report_run(self, report_run_id: int) -> dict[str, Any]:
        with self.session_factory() as session:
            item = session.get(models.ReportRun, report_run_id)
            if item is None:
                raise ValueError("Запись отчета не найдена")
            artifact_path = cast(str | None, item.artifact_path)
            expected_sha256 = cast(str | None, item.artifact_sha256)
        return self._verify_artifact(
            report_run_id=report_run_id,
            artifact_path=artifact_path,
            expected_sha256=expected_sha256,
            compute_hash=True,
        )

    def _log_report_run(
        self,
        report_type: str,
        filters: dict,
        summary: dict,
        file_path: Path,
        sha256: str,
        created_by: int | None,
    ) -> int:
        safe_filters = self._sanitize_filters(cast(dict[str, Any], filters))
        with self.session_factory() as session:
            row = models.ReportRun(
                report_type=report_type,
                filters_json=self._json_dumps(safe_filters),
                result_summary_json=self._json_dumps(summary),
                artifact_path=str(file_path),
                artifact_sha256=sha256,
                created_by=created_by,
            )
            session.add(row)
            session.flush()
            return _as_int(row.id)

    def _sanitize_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, value in filters.items():
            if key.lower() in SENSITIVE_FILTER_KEYS:
                sanitized[key] = "***"
                continue
            sanitized[key] = value
        return sanitized

    def _json_dumps(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=self._json_default)

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        return str(value)

    def _build_report_history_row(
        self,
        item: models.ReportRun,
        *,
        verify_hash: bool,
    ) -> dict[str, Any]:
        summary = self._safe_json_loads(cast(str, item.result_summary_json))
        filters = self._safe_json_loads(cast(str, item.filters_json))
        artifact_path = cast(str | None, item.artifact_path)
        artifact_sha256 = cast(str | None, item.artifact_sha256)
        verification = self._verify_artifact(
            report_run_id=_as_int(item.id),
            artifact_path=artifact_path,
            expected_sha256=artifact_sha256,
            compute_hash=verify_hash,
        )
        return {
            "id": _as_int(item.id),
            "created_at": item.created_at,
            "created_by": item.created_by,
            "report_type": item.report_type,
            "filters": filters,
            "summary": summary,
            "artifact_path": artifact_path,
            "artifact_sha256": artifact_sha256,
            "verification": verification,
        }

    def _verify_artifact(
        self,
        *,
        report_run_id: int,
        artifact_path: str | None,
        expected_sha256: str | None,
        compute_hash: bool,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "report_run_id": report_run_id,
            "artifact_path": artifact_path,
            "artifact_exists": False,
            "expected_sha256": expected_sha256,
            "actual_sha256": None,
            "verified": None,
            "status": "pending",
            "message": "Ожидает проверки",
        }
        if not artifact_path:
            result["status"] = "missing"
            result["verified"] = False
            result["message"] = "Артефакт не указан"
            return result

        path = Path(artifact_path)
        if not path.exists():
            result["status"] = "missing"
            result["verified"] = False
            result["message"] = "Файл артефакта не найден"
            return result

        result["artifact_exists"] = True
        if not compute_hash:
            result["status"] = "available"
            result["message"] = "Файл найден"
            return result

        if not expected_sha256:
            result["status"] = "error"
            result["verified"] = False
            result["message"] = "Эталонный SHA256 не сохранен"
            return result
        try:
            actual_sha256 = sha256_file(path)
        except OSError as exc:
            result["status"] = "error"
            result["verified"] = False
            result["message"] = f"Ошибка чтения файла: {exc}"
            return result

        result["actual_sha256"] = actual_sha256
        if actual_sha256 == expected_sha256:
            result["status"] = "ok"
            result["verified"] = True
            result["message"] = "SHA256 совпадает"
            return result

        result["status"] = "mismatch"
        result["verified"] = False
        result["message"] = "SHA256 не совпадает"
        return result

    def _save_artifact_copy(self, *, report_type: str, source_path: Path) -> Path:
        if not source_path.exists():
            raise FileNotFoundError(f"Файл отчета не найден: {source_path}")

        now = datetime.now(UTC)
        artifact_dir = REPORT_ARTIFACT_DIR / report_type / now.strftime("%Y") / now.strftime("%m")
        artifact_dir.mkdir(parents=True, exist_ok=True)

        suffix = source_path.suffix or ".bin"
        artifact_name = f"{report_type}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{suffix}"
        artifact_path = artifact_dir / artifact_name
        shutil.copy2(source_path, artifact_path)
        return artifact_path

    def _safe_json_loads(self, payload: str) -> dict[str, Any]:
        try:
            value = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {}
        if isinstance(value, dict):
            return value
        return {}

    def _build_filter_maps(self) -> dict[str, dict]:
        if not self.reference_service:
            return {}
        try:
            return {
                "department_id": {d.id: d.name for d in self.reference_service.list_departments()},
                "microorganism_id": {
                    m.id: f"{m.code or '-'} - {m.name}"
                    for m in self.reference_service.list_microorganisms()
                },
                "antibiotic_id": {
                    a.id: f"{a.code} - {a.name}" for a in self.reference_service.list_antibiotics()
                },
                "material_type_id": {
                    m.id: f"{m.code} - {m.name}"
                    for m in self.reference_service.list_material_types()
                },
                "icd10_code": {
                    i.code: f"{i.code} - {i.title}" for i in self.reference_service.list_icd10()
                },
            }
        except (AttributeError, SQLAlchemyError, TypeError, ValueError) as exc:
            logger.warning("Failed to build filter maps for report export: %s", exc)
            return {}

    def _format_filter_value(self, key: str, value: Any, filter_maps: dict[str, dict]) -> str:
        if key == "growth_flag":
            if value == 1:
                return "Да"
            if value == 0:
                return "Нет"
        if key == "patient_category":
            if isinstance(value, MilitaryCategory):
                return value.value
            if isinstance(value, str):
                try:
                    return MilitaryCategory[value].value
                except KeyError:
                    return value
        if key in filter_maps:
            mapped = filter_maps[key].get(value)
            if mapped is not None:
                return str(mapped)
        return str(_format_value(value))
