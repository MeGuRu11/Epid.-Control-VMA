from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(A5)
    pdf = canvas.Canvas(str(file_path), pagesize=(width, height))
    font = get_pdf_unicode_font_name()
    pdf.setTitle(f"Форма 100 {card.get('id', '')}")

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
    pdf.drawString(body_left, height - margin - 7 * mm, "ФОРМА 100")

    pdf.setFont(font, 8)
    pdf.drawString(margin + 2 * mm, height - margin - 7 * mm, "Корешок")
    content_width = max(10.0, body_right - body_left)
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=height - margin - 14 * mm,
        text=f"ФИО: {_safe(main.get('main_full_name') or card.get('main_full_name'))}",
        max_width=content_width,
    )
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=height - margin - 18 * mm,
        text=f"Подразделение: {_safe(main.get('main_unit') or card.get('main_unit'))}",
        max_width=content_width,
    )
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=height - margin - 22 * mm,
        text=f"Жетон/ID: {_safe(main.get('main_id_tag') or card.get('main_id_tag'))}",
        max_width=content_width,
    )
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=height - margin - 26 * mm,
        text=f"Диагноз: {_safe(bottom.get('main_diagnosis') or card.get('main_diagnosis'))}",
        max_width=content_width,
    )

    # Bodymap summary
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=margin + 32 * mm,
        text=f"Пол схемы тела: {_safe(data.get('bodymap_gender', 'M'))}",
        max_width=content_width,
    )
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=margin + 28 * mm,
        text=f"Метки: {len(annotations)}",
        max_width=content_width,
    )
    _draw_clipped_text(
        pdf,
        font=font,
        size=8,
        x=body_left,
        y=margin + 24 * mm,
        text=f"Подпись врача: {_safe(bottom.get('doctor_signature') or card.get('signed_by'))}",
        max_width=content_width,
    )

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


def _draw_clipped_text(
    pdf: canvas.Canvas,
    *,
    font: str,
    size: int,
    x: float,
    y: float,
    text: str,
    max_width: float,
) -> None:
    clipped = _fit_text(text, font=font, size=size, max_width=max_width)
    pdf.drawString(x, y, clipped)


def _fit_text(text: str, *, font: str, size: int, max_width: float) -> str:
    if not text:
        return ""
    if stringWidth(text, font, size) <= max_width:
        return text
    ellipsis = "..."
    if stringWidth(ellipsis, font, size) > max_width:
        return ""
    left = 0
    right = len(text)
    while left < right:
        mid = (left + right + 1) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if stringWidth(candidate, font, size) <= max_width:
            left = mid
        else:
            right = mid - 1
    return text[:left].rstrip() + ellipsis
