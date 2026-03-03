from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A4)
    pdf = canvas.Canvas(str(file_path), pagesize=(width, height))
    font = get_pdf_unicode_font_name()
    pdf.setTitle(f"Форма 100 {card.get('id', '')}")

    _draw_form100_layout(pdf, width=width, height=height, card=card, font=font)

    pdf.showPage()
    pdf.save()


def _safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _draw_form100_layout(
    pdf: canvas.Canvas, *, width: float, height: float, card: dict[str, Any], font: str
) -> None:
    margin = 8 * mm
    stub_w = 75 * mm
    stub_left = margin
    stub_right = margin + stub_w

    black_w = 10 * mm
    yellow_w = 12 * mm
    red_h = 12 * mm
    blue_h = 12 * mm

    main_left = stub_right + black_w
    main_right = width - margin - yellow_w
    main_top = height - margin - red_h
    main_bottom = margin + blue_h

    data = card.get("data") or {}
    main = data.get("main") or {}
    bottom = data.get("bottom") or {}
    flags = data.get("flags") or {}
    annotations = data.get("bodymap_annotations") or []

    pdf.setLineWidth(1)

    # 1. Colored Bands
    # BLACK (ИЗОЛЯЦИЯ)
    pdf.setFillColorRGB(0.1, 0.1, 0.1, alpha=0.9 if flags.get("flag_isolation") else 0.15)
    pdf.rect(stub_right, margin, black_w, height - 2 * margin, fill=1, stroke=1)

    # YELLOW (САНИТАРНАЯ ОБРАБОТКА)
    pdf.setFillColorRGB(0.96, 0.84, 0.2, alpha=0.9 if flags.get("flag_sanitation") else 0.15)
    pdf.rect(main_right, margin, yellow_w, height - 2 * margin, fill=1, stroke=1)

    # RED (НЕОТЛОЖНАЯ ПОМОЩЬ)
    pdf.setFillColorRGB(0.8, 0.1, 0.1, alpha=0.9 if flags.get("flag_emergency") else 0.15)
    pdf.rect(stub_right, main_top, width - margin - stub_right, red_h, fill=1, stroke=1)

    # BLUE (РАДИАЦИОННОЕ ПОРАЖЕНИЕ)
    pdf.setFillColorRGB(0.1, 0.4, 0.8, alpha=0.9 if flags.get("flag_radiation") else 0.15)
    pdf.rect(stub_right, margin, width - margin - stub_right, blue_h, fill=1, stroke=1)

    # Main structural frames
    pdf.setFillColorRGB(0, 0, 0, alpha=1)
    pdf.rect(stub_left, margin, stub_w, height - 2 * margin, fill=0, stroke=1)
    pdf.rect(main_left, main_bottom, main_right - main_left, main_top - main_bottom, fill=0, stroke=1)

    # Draw Band Titles
    pdf.setFillColorRGB(1, 1, 1, alpha=0.9)
    pdf.setFont(font, 12)
    center_x = main_left + (main_right - main_left) / 2
    pdf.drawCentredString(center_x, main_top + 3 * mm, "НЕОТЛОЖНАЯ ПОМОЩЬ")
    pdf.drawCentredString(center_x, margin + 3 * mm, "РАДИАЦИОННОЕ ПОРАЖЕНИЕ")

    pdf.saveState()
    pdf.translate(stub_right + 6 * mm, margin + (height - 2 * margin) / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, "ИЗОЛЯЦИЯ")
    pdf.restoreState()

    pdf.setFillColorRGB(0, 0, 0, alpha=0.9)
    pdf.saveState()
    pdf.translate(main_right + 7 * mm, margin + (height - 2 * margin) / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, "САНИТАРНАЯ ОБРАБОТКА")
    pdf.restoreState()

    # Parse standard fields
    full_name = _safe(main.get("main_full_name") or card.get("main_full_name"))
    unit = _safe(main.get("main_unit") or card.get("main_unit"))
    id_tag = _safe(main.get("main_id_tag") or card.get("main_id_tag"))
    rank = _safe(main.get("main_rank"))
    diagnosis = _safe(bottom.get("main_diagnosis") or card.get("main_diagnosis"))
    signature = _safe(bottom.get("doctor_signature") or card.get("signed_by"))
    datetime_str = _safe(main.get("main_date", "")) + " " + _safe(main.get("main_time", ""))

    # --- 2. Fill Stub ---
    pdf.setFillColorRGB(0, 0, 0, alpha=1)
    pdf.setFont(font, 10)
    pdf.drawCentredString(stub_left + stub_w / 2, height - margin - 7 * mm, "КОРЕШОК ПЕРВИЧНОЙ")
    pdf.drawCentredString(stub_left + stub_w / 2, height - margin - 12 * mm, "МЕДИЦИНСКОЙ КАРТОЧКИ")
    pdf.line(stub_left, height - margin - 14 * mm, stub_right, height - margin - 14 * mm)

    sy = height - margin - 20 * mm
    pdf.setFont(font, 9)
    pdf.drawString(stub_left + 2 * mm, sy, f"Дата: {datetime_str}")
    sy -= 7 * mm
    pdf.drawString(stub_left + 2 * mm, sy, f"в/зв {rank}   в/ч {unit}")
    sy -= 7 * mm
    _draw_clipped_text(pdf, font, 9, stub_left + 2 * mm, sy, f"ФИО: {full_name}", stub_w - 4 * mm)
    sy -= 7 * mm
    _draw_clipped_text(pdf, font, 9, stub_left + 2 * mm, sy, f"Жетон №: {id_tag}", stub_w - 4 * mm)

    sy -= 15 * mm
    pdf.setFont(font, 10)
    pdf.drawCentredString(stub_left + stub_w / 2, sy, "МЕДИЦИНСКАЯ ПОМОЩЬ")
    sy -= 2 * mm
    pdf.line(stub_left, sy, stub_right, sy)

    # Simple Stub Med Table
    pdf.setFont(font, 8)
    med_items = [
        "Антибиотик:", "Сыворотка ПСС:", "Анатоксин:", "Антидот:",
        "Обезболивающее:", "Переливание крови:", "Жгут / Санобработка:"
    ]
    for item in med_items:
        sy -= 6 * mm
        pdf.drawString(stub_left + 2 * mm, sy, item)
        pdf.line(stub_left, sy - 2 * mm, stub_right, sy - 2 * mm)

    pdf.setFont(font, 10)
    pdf.drawString(stub_left + 2 * mm, margin + 8 * mm, "Диагноз:")
    _draw_clipped_text(pdf, font, 8, stub_left + 2 * mm, margin + 4 * mm, diagnosis, stub_w - 4 * mm)

    # --- 3. Fill Main Card ---
    my = main_top - 8 * mm
    pdf.setFont(font, 14)
    pdf.drawCentredString(center_x, my, "Первичная медицинская карточка     Форма 100")
    my -= 8 * mm
    pdf.setFont(font, 9)
    pdf.drawString(main_left + 3 * mm, my, f"Выдана: {_safe(bottom.get('issued_by'))}")
    pdf.line(main_left, my - 2 * mm, main_right, my - 2 * mm)

    my -= 6 * mm
    pdf.drawString(main_left + 3 * mm, my, f"Дата: {datetime_str}")
    pdf.drawString(main_left + 80 * mm, my, f"в/зв {rank}   в/ч {unit}")
    my -= 6 * mm
    pdf.drawString(main_left + 3 * mm, my, f"ФИО: {full_name}")
    pdf.drawString(main_left + 80 * mm, my, f"Жетон №: {id_tag}")
    pdf.line(main_left, my - 3 * mm, main_right, my - 3 * mm)

    # 3.1 Medical Help Table
    table_x = main_left + 3 * mm
    table_y = my - 10 * mm
    pdf.setFont(font, 10)
    pdf.drawCentredString(table_x + 35 * mm, table_y, "МЕДИЦИНСКАЯ ПОМОЩЬ")
    pdf.rect(table_x, table_y - 45 * mm, 70 * mm, 42 * mm)

    ty = table_y - 6 * mm
    pdf.setFont(font, 8)
    for item in med_items:
        pdf.drawString(table_x + 2 * mm, ty + 1 * mm, item)
        pdf.line(table_x, ty, table_x + 70 * mm, ty)
        ty -= 6 * mm
    pdf.line(table_x + 45 * mm, table_y - 3 * mm, table_x + 45 * mm, table_y - 45 * mm) # dose column line

    # 3.2 Silhouette
    bx = center_x
    by = table_y - 8 * mm
    _draw_bodymap(pdf, font, bx, by, annotations)

    # 3.3 Evacuation & Signatures
    pdf.setFont(font, 10)
    pdf.drawString(main_left + 3 * mm, main_bottom + 12 * mm, "Диагноз:")
    _draw_clipped_text(pdf, font, 9, main_left + 20 * mm, main_bottom + 12 * mm, diagnosis, main_right - main_left - 80 * mm)

    pdf.line(main_left, main_bottom + 8 * mm, main_right, main_bottom + 8 * mm)
    pdf.drawString(main_right - 70 * mm, main_bottom + 3 * mm, f"Врач: {signature}")

    # Evacuation blocks on right
    ev_x = main_right - 75 * mm
    ev_y = table_y - 5 * mm
    pdf.setFont(font, 9)
    pdf.drawString(ev_x, ev_y, "Санитарная обработка (подчеркнуть):")
    pdf.drawString(ev_x + 3 * mm, ev_y - 5 * mm, "полная, частичная, не проводилась")
    pdf.drawString(ev_x, ev_y - 12 * mm, "Эвакуировать (куда): " + _safe(bottom.get("evac_destination")))

    pdf.rect(ev_x, ev_y - 35 * mm, 70 * mm, 20 * mm)
    pdf.drawString(ev_x + 2 * mm, ev_y - 20 * mm, "Транспорт:    [АВТО]  [ПОЕЗД]  [САМОЛЕТ]  [ВЕРТОЛ]")
    pdf.drawString(ev_x + 2 * mm, ev_y - 30 * mm, "Положение:    [ЛЕЖА]  [СИДЯ]")

    pdf.drawString(ev_x, ev_y - 45 * mm, "Очередность эвакуации:  I    II    III")


def _draw_bodymap(pdf: canvas.Canvas, font: str, bx: float, by: float, annotations: list[dict[str, Any]]) -> None:
    # Stick figure approximation for body schematic
    pdf.circle(bx, by, 7 * mm)
    pdf.roundRect(bx - 10 * mm, by - 40 * mm, 20 * mm, 30 * mm, 3 * mm)
    pdf.line(bx - 10 * mm, by - 14 * mm, bx - 25 * mm, by - 35 * mm)
    pdf.line(bx + 10 * mm, by - 14 * mm, bx + 25 * mm, by - 35 * mm)
    pdf.line(bx - 5 * mm, by - 40 * mm, bx - 8 * mm, by - 65 * mm)
    pdf.line(bx + 5 * mm, by - 40 * mm, bx + 8 * mm, by - 65 * mm)

    pdf.setFont(font, 7)
    pdf.drawCentredString(bx, by - 70 * mm, "СХЕМА ТРАВМ")
    for i, ann in enumerate(annotations[:5]):
        label = f"- {_safe(ann.get('annotation_type'))} ({_safe(ann.get('silhouette'))})"
        pdf.drawString(bx + 30 * mm, by - i * 6 * mm, label)


def _draw_clipped_text(
    pdf: canvas.Canvas, font: str, size: int, x: float, y: float, text: str, max_width: float
) -> None:
    if not text:
        return
    if stringWidth(text, font, size) <= max_width:
        pdf.setFont(font, size)
        pdf.drawString(x, y, text)
        return
    ellipsis = "..."
    left = 0
    right = len(text)
    while left < right:
        mid = (left + right + 1) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if stringWidth(candidate, font, size) <= max_width:
            left = mid
        else:
            right = mid - 1
    clipped = text[:left].rstrip() + ellipsis
    pdf.setFont(font, size)
    pdf.drawString(x, y, clipped)
