from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A5)
    pdf = canvas.Canvas(str(file_path), pagesize=(width, height))
    font = get_pdf_unicode_font_name()
    pdf.setTitle(f"Форма 100 V2 {card.get('id', '')}")

    _draw_frame(pdf, width=width, height=height)
    _draw_content(pdf, width=width, height=height, card=card, font=font)

    pdf.showPage()
    pdf.save()


def _draw_frame(pdf: canvas.Canvas, *, width: float, height: float) -> None:
    margin = 6 * mm
    pdf.setLineWidth(0.7)
    pdf.rect(margin, margin, width - 2 * margin, height - 2 * margin)

    stub_width = 42 * mm
    flag_width = 8 * mm
    pdf.line(margin + stub_width, margin, margin + stub_width, height - margin)
    pdf.line(width - margin - flag_width * 3, margin, width - margin - flag_width * 3, height - margin)
    pdf.line(width - margin - flag_width * 2, margin, width - margin - flag_width * 2, height - margin)
    pdf.line(width - margin - flag_width, margin, width - margin - flag_width, height - margin)

    # Top title row
    pdf.line(margin, height - margin - 10 * mm, width - margin, height - margin - 10 * mm)
    # Body map region
    body_left = margin + stub_width + 4 * mm
    body_right = width - margin - flag_width * 3 - 4 * mm
    body_top = height - margin - 18 * mm
    body_bottom = margin + 38 * mm
    pdf.rect(body_left, body_bottom, body_right - body_left, body_top - body_bottom)
    # Bottom block
    pdf.line(body_left, margin + 30 * mm, body_right, margin + 30 * mm)


def _draw_content(
    pdf: canvas.Canvas,
    *,
    width: float,
    height: float,
    card: dict[str, Any],
    font: str,
) -> None:
    margin = 6 * mm
    stub_width = 42 * mm
    flag_width = 8 * mm
    body_left = margin + stub_width + 4 * mm
    body_right = width - margin - flag_width * 3 - 4 * mm

    data = card.get("data") or {}
    main = data.get("main") or {}
    bottom = data.get("bottom") or {}
    flags = data.get("flags") or {}
    annotations = data.get("bodymap_annotations") or []

    pdf.setFont(font, 11)
    pdf.drawString(body_left, height - margin - 7 * mm, "ФОРМА 100 (V2)")

    pdf.setFont(font, 8)
    pdf.drawString(margin + 2 * mm, height - margin - 7 * mm, "Корешок")
    pdf.drawString(body_left, height - margin - 14 * mm, f"ФИО: {_safe(main.get('main_full_name') or card.get('main_full_name'))}")
    pdf.drawString(body_left, height - margin - 18 * mm, f"Подразделение: {_safe(main.get('main_unit') or card.get('main_unit'))}")
    pdf.drawString(body_left, height - margin - 22 * mm, f"Жетон/ID: {_safe(main.get('main_id_tag') or card.get('main_id_tag'))}")
    pdf.drawString(body_left, height - margin - 26 * mm, f"Диагноз: {_safe(bottom.get('main_diagnosis') or card.get('main_diagnosis'))}")

    # Bodymap summary
    pdf.drawString(body_left, margin + 32 * mm, f"Пол схемы тела: {_safe(data.get('bodymap_gender', 'M'))}")
    pdf.drawString(body_left, margin + 28 * mm, f"Метки: {len(annotations)}")
    pdf.drawString(body_left, margin + 24 * mm, f"Подпись врача: {_safe(bottom.get('doctor_signature') or card.get('signed_by'))}")

    # Flags
    fx = width - margin - flag_width * 3
    flags_state = [
        ("НЕОТЛОЖНАЯ", bool(flags.get("flag_emergency"))),
        ("РАДИАЦИЯ", bool(flags.get("flag_radiation"))),
        ("САНОБРАБ.", bool(flags.get("flag_sanitation"))),
    ]
    colors = [(0.75, 0.22, 0.17), (0.12, 0.47, 0.71), (0.96, 0.84, 0.55)]
    for idx, ((label, enabled), rgb) in enumerate(zip(flags_state, colors, strict=False)):
        col_x = fx + idx * flag_width
        alpha = 0.95 if enabled else 0.28
        pdf.saveState()
        pdf.setFillColorRGB(*rgb, alpha=alpha)
        pdf.rect(col_x, margin, flag_width, height - 2 * margin, fill=1, stroke=0)
        pdf.restoreState()
        pdf.saveState()
        pdf.translate(col_x + flag_width / 2, margin + 8 * mm)
        pdf.rotate(90)
        pdf.setFont(font, 7)
        pdf.setFillColorRGB(0.1, 0.1, 0.1, alpha=1)
        pdf.drawCentredString((height - 2 * margin) / 2, 0, label)
        pdf.restoreState()

    # Minimal annotation rendering
    marker_start_x = body_left + 4 * mm
    marker_y = margin + 14 * mm
    pdf.setFont(font, 7)
    for idx, item in enumerate(annotations[:10]):
        x = marker_start_x + (idx % 5) * 26 * mm
        y = marker_y + (idx // 5) * 7 * mm
        label = f"{_safe(item.get('annotation_type'))}@{_safe(item.get('silhouette'))}"
        pdf.drawString(x, y, label)

    # Truncate hint
    if len(annotations) > 10:
        pdf.drawString(body_right - 34 * mm, marker_y + 7 * mm, f"... +{len(annotations) - 10}")


def _safe(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
