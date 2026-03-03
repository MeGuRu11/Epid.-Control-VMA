from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import KeepInFrame, Flowable

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A4)
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=(width, height),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"Форма 100 {card.get('id', '')}"
    )

    font = get_pdf_unicode_font_name()
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    p_small = ParagraphStyle("PdfCellSmall", parent=normal_style, fontName=font, fontSize=7, leading=8)
    p_normal = ParagraphStyle("PdfCell", parent=normal_style, fontName=font, fontSize=9, leading=10)
    p_bold = ParagraphStyle("PdfCellBold", parent=normal_style, fontName=font, fontSize=10, leading=11)
    p_title = ParagraphStyle("PdfTitle", parent=normal_style, fontName=font, fontSize=14, alignment=1, spaceAfter=5)

    data = card.get("data") or {}
    main = data.get("main") or {}
    bottom = data.get("bottom") or {}
    flags = data.get("flags") or {}
    annotations = data.get("bodymap_annotations") or []

    def _s(key: str, default: str = "") -> str:
        v = main.get(key) or bottom.get(key) or card.get(key)
        return str(v) if v is not None else default

    datetime_str = f"{_s('main_date')} {_s('main_time')}".strip()
    
    # 1. Colored bands can be created as a header row in the main table or we can just use colored background cells.
    # Platypus Table is excellent for this.

    elements = []

    # Building a large grid
    # Stub (Корешок) = Column 1 (0 to 1) 
    # Gap = Column 2
    # Main Card = Column 3 to 10
    
    col_widths = [
        35*mm, 35*mm,  # Stub
        2*mm,          # Gap Cut Line
        15*mm,         # Colored Isolation
        30*mm, 30*mm, 30*mm, 30*mm, 30*mm, 20*mm, # Main parts
        15*mm,         # Yellow Sanitation
    ]

    t_data = []

    # ROW 0: Titles
    t1 = Paragraph("<b>КОРЕШОК ПЕРВИЧНОЙ<br/>МЕДИЦИНСКОЙ КАРТОЧКИ</b>", p_bold)
    t1.alignment = 1
    t2 = Paragraph("<b>ПЕРВИЧНАЯ МЕДИЦИНСКАЯ КАРТОЧКА (Форма 100)</b>", p_title)
    
    # Colored Cells logic
    c_red = colors.Color(0.8, 0.1, 0.1, alpha=0.9 if flags.get("flag_emergency") else 0.15)
    c_blue = colors.Color(0.1, 0.4, 0.8, alpha=0.9 if flags.get("flag_radiation") else 0.15)
    c_black = colors.Color(0.1, 0.1, 0.1, alpha=0.9 if flags.get("flag_isolation") else 0.15)
    c_yellow = colors.Color(0.96, 0.84, 0.2, alpha=0.9 if flags.get("flag_sanitation") else 0.15)
    
    class RotatedText(Flowable):
        def __init__(self, text, font, size):
            Flowable.__init__(self)
            self.text = text
            self.font = font
            self.size = size
        def draw(self):
            self.canv.saveState()
            self.canv.rotate(90)
            self.canv.setFillColorRGB(1,1,1)
            self.canv.setFont(self.font, self.size)
            self.canv.drawString(20, -10, self.text)
            self.canv.restoreState()

    h_black = RotatedText("ИЗОЛЯЦИЯ", font, 11)
    h_yellow = RotatedText("САНОБРАБОТКА", font, 11)

    t_data.append([
        t1, "", "", h_black, Paragraph("<b>НЕОТЛОЖНАЯ ПОМОЩЬ</b>", ParagraphStyle("R", parent=p_bold, textColor=colors.white, alignment=1)), "", "", "", "", "", h_yellow
    ])

    t_data.append([
        Paragraph("<b>МЕДИЦИНСКАЯ ПОМОЩЬ</b>", p_bold), "", "", "", t2, "", "", "", "", "", ""
    ])

    # Stub content
    stub_info = [
        Paragraph(f"Дата: <b>{datetime_str}</b>", p_normal),
        Paragraph(f"в/зв <b>{_s('main_rank')}</b>   в/ч <b>{_s('main_unit')}</b>", p_normal),
        Paragraph(f"ФИО: <b>{_s('main_full_name')}</b>", p_normal),
        Paragraph(f"Жетон: <b>{_s('main_id_tag')}</b>", p_normal),
        Paragraph("<b>Диагноз:</b><br/>" + _s('main_diagnosis'), p_normal),
    ]
    
    # Main Content
    main_info = [
        Paragraph(f"Выдана: <b>{_s('issued_by', 'Не указано')}</b>", p_normal),
        Paragraph(f"Дата: <b>{datetime_str}</b>", p_normal),
        Paragraph(f"Звание: <b>{_s('main_rank')}</b>", p_normal),
        Paragraph(f"Подразделение: <b>{_s('main_unit')}</b>", p_normal),
    ]

    t_data.append([
        stub_info[0], stub_info[1], "", "", main_info[0], "", main_info[1], "", "", "", ""
    ])
    t_data.append([
        stub_info[2], stub_info[3], "", "", main_info[2], "", main_info[3], "", "", "", ""
    ])
    t_data.append([
        stub_info[4], "", "", "", Paragraph(f"ФИО: <b>{_s('main_full_name')}</b>", p_normal), "", "", Paragraph(f"Жетон: <b>{_s('main_id_tag')}</b>", p_normal), "", "", ""
    ])

    # Big Block: Diagnosis and Help
    med_help_str = "<b>ОКАЗАННАЯ ПОМОЩЬ:</b><br/>"
    for item in ["Антибиотик", "Сыворотка ПСС", "Анатоксин", "Антидот", "Обезболивающее", "Переливание крови", "Жгут"]:
        med_help_str += f"- {item}: ______________<br/>"

    t_data.append([
        "", "", "", "", Paragraph("<b>Диагноз:</b><br/>" + _s('main_diagnosis'), p_normal), "", "", Paragraph(med_help_str, p_normal), "", "", ""
    ])

    # Bodymap Text
    bodymap_str = "<b>СХЕМА ТРАВМ:</b><br/>"
    for ann in annotations[:10]:
        bodymap_str += f"- {_s('annotation_type', ann)} ({_s('silhouette', ann)})<br/>"

    t_data.append([
        "", "", "", "", Paragraph(bodymap_str, p_small), "", "", "", "", "", ""
    ])

    # Bottom fields
    t_data.append([
        Paragraph("<b>РАДИАЦИЯ</b>", p_bold), "", "", "", Paragraph(f"<b>Эвакуировать в:</b> {_s('evac_destination')}", p_normal), "", Paragraph("<b>Транспорт:</b> [АВТО] [ВЕРТ]", p_normal), "", Paragraph(f"<b>Врач:</b> {_s('doctor_signature', _s('signed_by'))}", p_normal), "", ""
    ])

    # Normalize Rows to have same len
    max_len = len(col_widths)
    for i, r in enumerate(t_data):
        while len(r) < max_len:
            r.append("")

    table = Table(t_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        # Stub Spans
        ('SPAN', (0,0), (1,0)),
        ('SPAN', (0,1), (1,1)),
        ('SPAN', (0,4), (1,6)),
        ('SPAN', (0,7), (1,7)),
        
        # Main Title Spans
        ('SPAN', (4,0), (9,0)),
        ('SPAN', (4,1), (9,1)),
        ('SPAN', (4,2), (5,2)), ('SPAN', (6,2), (9,2)),
        ('SPAN', (4,3), (5,3)), ('SPAN', (6,3), (9,3)),
        ('SPAN', (4,4), (6,4)), ('SPAN', (7,4), (9,4)),
        
        # Diagnosis and Help Spans
        ('SPAN', (4,5), (6,6)), ('SPAN', (7,5), (9,6)),
        
        # Bodymap Span
        ('SPAN', (4,7), (9,7)),
        
        # Bottom Span
        ('SPAN', (4,7), (5,7)), ('SPAN', (6,7), (7,7)), ('SPAN', (8,7), (9,7)),

        # Tall Colored Column Spans
        ('SPAN', (3,0), (3,7)), # Black band
        ('SPAN', (10,0), (10,7)), # Yellow band

        # Coloring Top Bands
        ('BACKGROUND', (4,0), (9,0), c_red),
        ('BACKGROUND', (4,7), (9,7), c_blue),
        
        # Coloring Edge Bands
        ('BACKGROUND', (3,0), (3,7), c_black),
        ('BACKGROUND', (10,0), (10,7), c_yellow),
        
        # Grid lines
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
        ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
    ]))

    elements.append(table)
    doc.build(elements)
