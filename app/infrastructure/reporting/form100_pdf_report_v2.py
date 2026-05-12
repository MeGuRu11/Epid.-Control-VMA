"""Форма 100 — структурированный текстовый PDF-отчёт.

Вместо рисования канвасом точной копии бланка, генерирует чистый, читаемый
отчёт со всеми заполненными полями и встроенной схемой тела (bodymap) с
нанесёнными врачом метками.
"""
from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.graphics.shapes import (
    Circle,
    Drawing,
    Ellipse,
    Line,
    Polygon,
    Rect,
    String,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as PlatypusImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.application.reporting.formatters import (
    format_annotation_type,
    format_date,
    format_datetime,
    format_silhouette_short,
)
from app.domain.services.bodymap_geometry import denormalize_for_drawing, denormalize_for_pil
from app.domain.services.bodymap_zones import coordinates_to_zone
from app.infrastructure.reporting.pdf_determinism import build_invariant_pdf
from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name

_PILImageModule: Any
_ImageDrawModule: Any
try:
    from PIL import Image as _PILImageModule, ImageDraw as _ImageDrawModule
except ImportError:  # pragma: no cover - handled by vector fallback
    _PILImageModule = None
    _ImageDrawModule = None

PILImage: Any = _PILImageModule
ImageDraw: Any = _ImageDrawModule

# ── Константы ────────────────────────────────────────────────────────────────

_ANNOTATION_LABELS: dict[str, str] = {
    "WOUND_X": "Рана (✕)",
    "BURN_HATCH": "Ожог (○)",
    "AMPUTATION": "Ампутация (▲)",
    "TOURNIQUET": "Жгут (─)",
    "NOTE_PIN": "Заметка (◎)",
}

_SAN_LOSS_LABELS: dict[str, str] = {
    "san_loss_gunshot": "О  Огнестрельное",
    "san_loss_nuclear": "Я  Ядерное",
    "san_loss_chemical": "Х  Химическое",
    "san_loss_biological": "Бак.  Бактериологическое",
    "san_loss_other": "Другие",
    "san_loss_frostbite": "Отм.  Отморожение",
    "san_loss_burn": "Б  Ожог",
    "san_loss_misc": "И  Иное",
}

_LESION_LABELS: dict[str, str] = {
    "lesion_gunshot": "Огнестрельное",
    "lesion_nuclear": "Ядерное",
    "lesion_chemical": "Химическое",
    "lesion_biological": "Бактериологическое",
    "lesion_other": "Другие",
    "lesion_frostbite": "Отморожение",
    "lesion_burn": "Ожог",
    "lesion_misc": "Иное",
}

_SILHOUETTE_LABELS: dict[str, str] = {
    "male_front": "Вид спереди",
    "male_back": "Вид сзади",
    "female_front": "Вид спереди",
    "female_back": "Вид сзади",
}

_BODYMAP_TEMPLATE_FILES: tuple[str, ...] = ("form_100_bd.png", "form_100_body.png")


# ── Помощники ────────────────────────────────────────────────────────────────

def _g(d: dict[str, Any], key: str, default: str = "") -> str:
    """Безопасно достать строку из dict."""
    v = d.get(key)
    if v is None:
        return default
    return str(v).strip() or default


def _is_truthy(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _fmt_optional(value: object) -> str:
    """None -> 'не указано'; иначе str(value)."""
    if value is None:
        return "не указано"
    return str(value)


def _fmt_bool_field(value: object) -> str:
    """True/1 -> 'Да'; False/0 -> 'Нет'; None -> 'не указано'."""
    if value is None:
        return "не указано"
    return "Да" if _is_truthy(value) else "Нет"


def _checked_items(d: dict[str, Any], labels: dict[str, str]) -> list[str]:
    return [label for key, label in labels.items() if _is_truthy(d.get(key, ""))]


def _parse_annotations(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def _to_float(value: object, default: float = 0.5) -> float:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _body_side(x: float | None) -> str:
    if x is None:
        return "—"
    if x < 0.35:
        return "Левая"
    if x > 0.65:
        return "Правая"
    return "По центру"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_silhouette(silhouette: str) -> str:
    sil = silhouette.strip().lower()
    if sil in {"female_front", "front", "male_front"}:
        return "male_front"
    if sil in {"female_back", "back", "male_back"}:
        return "male_back"
    return "male_back" if "back" in sil else "male_front"


def _bodymap_image_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and isinstance(meipass, str):
        return Path(meipass) / "app" / "image" / "main"
    return Path(__file__).resolve().parents[2] / "image" / "main"


def _load_bodymap_template_image() -> Any | None:
    if PILImage is None:
        return None
    image_root = _bodymap_image_root()
    for file_name in _BODYMAP_TEMPLATE_FILES:
        image_path = image_root / file_name
        if not image_path.exists():
            continue
        with PILImage.open(image_path) as source:
            image = source.convert("RGBA")
        width, height = image.size
        if width <= 0 or height <= 0:
            continue
        # Legacy sprite: 4 segments (front/back + female front/back), keep only first 2.
        if width >= int(height * 2.2):
            image = image.crop((0, 0, width // 2, height))
        return image
    return None


def _draw_annotation_marker(
    draw: Any,
    *,
    annotation_type: str,
    x: float,
    y: float,
    note: str = "",
) -> None:
    if annotation_type == "WOUND_X":
        size = 9
        color = (225, 55, 48, 255)
        draw.line((x - size, y - size, x + size, y + size), fill=color, width=4)
        draw.line((x - size, y + size, x + size, y - size), fill=color, width=4)
        return

    if annotation_type == "BURN_HATCH":
        size = 11
        color = (241, 148, 38, 255)
        draw.ellipse((x - size, y - size, x + size, y + size), outline=color, width=4)
        return

    if annotation_type == "AMPUTATION":
        color = (201, 62, 53, 255)
        points = [(x, y - 12), (x - 10, y + 8), (x + 10, y + 8)]
        draw.polygon(points, outline=color, fill=(201, 62, 53, 80))
        return

    if annotation_type == "TOURNIQUET":
        color = (226, 126, 36, 255)
        draw.line((x - 13, y, x + 13, y), fill=color, width=5)
        draw.line((x - 13, y - 5, x - 13, y + 5), fill=color, width=4)
        draw.line((x + 13, y - 5, x + 13, y + 5), fill=color, width=4)
        return

    # NOTE_PIN / fallback
    color = (54, 122, 191, 255)
    draw.ellipse((x - 7, y - 7, x + 7, y + 7), outline=color, width=3)
    draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
    draw.line((x, y + 7, x, y + 14), fill=color, width=3)
    if note:
        draw.text((x + 10, y - 10), note[:24], fill=color)


def _build_bodymap_image_flowable(
    *,
    annotations: list[dict[str, Any]],
    max_width_pt: float,
    max_height_pt: float,
) -> PlatypusImage | None:
    if PILImage is None or ImageDraw is None:
        return None

    template = _load_bodymap_template_image()
    if template is None:
        return None

    canvas = template.copy()
    draw = ImageDraw.Draw(canvas)
    panel_width = canvas.width / 2.0
    canvas_height = float(canvas.height)

    for ann in annotations:
        ann_type = str(ann.get("annotation_type") or "WOUND_X")
        silhouette = _normalize_silhouette(str(ann.get("silhouette") or "male_front"))
        x_norm = _clamp01(_to_float(ann.get("x"), 0.5))
        y_norm = _clamp01(_to_float(ann.get("y"), 0.5))
        x, y = denormalize_for_pil(
            x_norm,
            y_norm,
            panel_width_px=panel_width,
            canvas_height_px=canvas_height,
            is_back=silhouette.endswith("back"),
        )
        _draw_annotation_marker(
            draw,
            annotation_type=ann_type,
            x=x,
            y=y,
            note=str(ann.get("note") or ""),
        )

    payload = BytesIO()
    canvas.save(payload, format="PNG")
    payload.seek(0)
    flowable = PlatypusImage(payload)
    scale = min(max_width_pt / max(1.0, float(canvas.width)), max_height_pt / max(1.0, float(canvas.height)))
    flowable.drawWidth = max(1.0, float(canvas.width) * scale)
    flowable.drawHeight = max(1.0, float(canvas.height) * scale)
    flowable.hAlign = "CENTER"
    # keep in-memory PNG alive until document build completes
    flowable._source_buffer = payload
    return flowable


# ── Bodymap как Drawing (Platypus flowable) ──────────────────────────────────

def _render_bodymap_drawing(
    annotations: list[dict[str, Any]],
    tissue_types: list[str] | None = None,
    width_pt: float = 440,
    height_pt: float = 300,
) -> Drawing:
    """Создаёт Drawing-объект со схемой тела и нанесёнными метками врача."""
    font = get_pdf_unicode_font_name()
    d = Drawing(width_pt, height_pt)

    # Фон
    background_kwargs: dict[str, Any] = {
        "fillColor": colors.Color(0.97, 0.97, 0.97),
        "strokeColor": colors.Color(0.85, 0.85, 0.85),
        "strokeWidth": 0.5,
    }
    d.add(Rect(0, 0, width_pt, height_pt, **background_kwargs))

    mid = width_pt / 2
    body_h = height_pt - 35
    body_top = height_pt - 18

    # Заголовки
    d.add(String(mid / 2, height_pt - 14, "Вид спереди", fontName=font, fontSize=9, textAnchor="middle"))
    d.add(String(mid + mid / 2, height_pt - 14, "Вид сзади", fontName=font, fontSize=9, textAnchor="middle"))

    # Разделитель
    d.add(Line(mid, 8, mid, height_pt - 8, strokeColor=colors.Color(0.75, 0.75, 0.75), strokeWidth=0.8, strokeDashArray=[3, 3]))

    sil_color = colors.Color(0.3, 0.3, 0.3)

    for i in range(2):
        cx = mid / 2 if i == 0 else mid + mid / 2
        top = body_top - 6

        # Head
        head_r = 11
        d.add(Circle(cx, top, head_r, strokeColor=sil_color, strokeWidth=1.2, fillColor=None))

        # Neck
        d.add(Line(cx, top - head_r, cx, top - head_r - 4, strokeColor=sil_color, strokeWidth=1.2))

        # Torso
        torso_top = top - head_r - 4
        torso_h = body_h * 0.33
        torso_w = 18
        d.add(Ellipse(cx, torso_top - torso_h / 2, torso_w, torso_h / 2, strokeColor=sil_color, strokeWidth=1.2, fillColor=None))

        # Arms
        shoulder_y = torso_top - 4
        hand_y = torso_top - torso_h + 8
        d.add(Line(cx - torso_w, shoulder_y, cx - torso_w - 16, hand_y, strokeColor=sil_color, strokeWidth=1.2))
        d.add(Line(cx + torso_w, shoulder_y, cx + torso_w + 16, hand_y, strokeColor=sil_color, strokeWidth=1.2))

        # Legs
        hip_y = torso_top - torso_h
        foot_y = 18
        d.add(Line(cx - 7, hip_y, cx - 16, foot_y, strokeColor=sil_color, strokeWidth=1.2))
        d.add(Line(cx + 7, hip_y, cx + 16, foot_y, strokeColor=sil_color, strokeWidth=1.2))

    # Annotation marks
    for ann in annotations:
        sil = str(ann.get("silhouette", "male_front"))
        atype = str(ann.get("annotation_type", "WOUND_X"))
        x_norm = _clamp01(_to_float(ann.get("x"), 0.5))
        y_norm = _clamp01(_to_float(ann.get("y"), 0.5))
        ax, ay = denormalize_for_drawing(
            x_norm,
            y_norm,
            panel_width_pt=mid,
            total_height_pt=height_pt,
            is_back="back" in sil,
        )

        if "WOUND" in atype:
            sc = colors.Color(0.9, 0.15, 0.15)
            sz = 5
            d.add(Line(ax - sz, ay - sz, ax + sz, ay + sz, strokeColor=sc, strokeWidth=1.8))
            d.add(Line(ax - sz, ay + sz, ax + sz, ay - sz, strokeColor=sc, strokeWidth=1.8))
        elif "BURN" in atype:
            d.add(Circle(ax, ay, 6, strokeColor=colors.Color(0.95, 0.6, 0.1), strokeWidth=1.5, fillColor=None))
        elif "AMPUTATION" in atype:
            fc = colors.Color(0.75, 0.2, 0.15, 0.3)
            sc2 = colors.Color(0.75, 0.2, 0.15)
            d.add(Polygon([ax, ay + 6, ax - 5, ay - 4, ax + 5, ay - 4], strokeColor=sc2, fillColor=fc, strokeWidth=1.5))
        elif "TOURNIQUET" in atype:
            d.add(Line(ax - 8, ay, ax + 8, ay, strokeColor=colors.Color(0.9, 0.5, 0.1), strokeWidth=2.5))
        elif "NOTE" in atype:
            d.add(Circle(ax, ay, 4, strokeColor=colors.Color(0.2, 0.6, 0.85), strokeWidth=1.2, fillColor=None))
            d.add(Circle(ax, ay, 1.5, strokeColor=colors.Color(0.2, 0.6, 0.85), fillColor=colors.Color(0.2, 0.6, 0.85)))
            note = str(ann.get("note", ""))
            if note:
                d.add(String(ax + 6, ay + 2, note[:20], fontName=font, fontSize=6, fillColor=colors.Color(0.2, 0.6, 0.85)))

    # Tissue types footer
    if tissue_types:
        txt = "Ткани: " + ", ".join(tissue_types)
        d.add(String(width_pt / 2, 4, txt, fontName=font, fontSize=7, textAnchor="middle", fillColor=colors.Color(0.35, 0.35, 0.35)))

    return d


# ── Основная функция ─────────────────────────────────────────────────────────

def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    """Генерирует структурированный PDF-отчёт по карточке Формы 100."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    font = get_pdf_unicode_font_name()
    data = card.get("data") or {}
    stub = data.get("stub") or {}
    main = data.get("main") or {}
    bottom = data.get("bottom") or {}
    flags = data.get("flags") or {}
    san_loss = data.get("san_loss") or {}
    lesion = data.get("lesion") or {}
    medical_help = data.get("medical_help") or {}
    tissue_types = data.get("bodymap_tissue_types") or []
    raw_annotations = data.get("bodymap_annotations") or []
    annotations = _parse_annotations(raw_annotations)

    # ── Стили ──────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    s_title = ParagraphStyle(
        "F100Title", parent=styles["Heading1"], fontName=font,
        fontSize=16, alignment=TA_CENTER, spaceAfter=4 * mm,
        textColor=colors.Color(0.12, 0.12, 0.12),
    )
    s_subtitle = ParagraphStyle(
        "F100Subtitle", parent=styles["Heading3"], fontName=font,
        fontSize=10, alignment=TA_CENTER, spaceAfter=2 * mm,
        textColor=colors.Color(0.3, 0.3, 0.3),
    )
    s_section = ParagraphStyle(
        "F100Section", parent=styles["Heading2"], fontName=font,
        fontSize=12, spaceBefore=5 * mm, spaceAfter=2 * mm,
        textColor=colors.Color(0.15, 0.3, 0.5),
    )
    s_small = ParagraphStyle(
        "F100Small", parent=styles["Normal"], fontName=font,
        fontSize=8, leading=10, textColor=colors.Color(0.35, 0.35, 0.35),
    )
    s_cell = ParagraphStyle(
        "F100Cell", parent=styles["Normal"], fontName=font,
        fontSize=9, leading=11,
    )
    s_unset = ParagraphStyle(
        "F100Unset", parent=s_cell, fontName=font,
        fontSize=9, leading=11, textColor=colors.HexColor("#888780"),
    )
    s_cell_bold = ParagraphStyle(
        "F100CellBold", parent=s_cell, fontName=font,
        fontSize=9, leading=11,
    )
    s_flag_on = ParagraphStyle(
        "F100FlagOn", parent=s_cell, fontName=font,
        textColor=colors.Color(0.8, 0.15, 0.1),
    )
    s_flag_off = ParagraphStyle(
        "F100FlagOff", parent=s_cell, fontName=font,
        textColor=colors.Color(0.5, 0.5, 0.5),
    )

    def P(text: str, style: ParagraphStyle = s_cell) -> Paragraph:  # noqa: N802
        return Paragraph(str(text or "—"), style)

    def _field_row(label: str, value: object, style: ParagraphStyle = s_cell) -> list[Paragraph]:
        value_text = "—" if value is None or value == "" else str(value)
        return [P(f"<b>{label}</b>", s_cell_bold), P(value_text, style)]

    # ── Построение документа ───────────────────────────────────────────
    elements: list[Any] = []
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    page_w = A4[0] - 30 * mm  # usable width

    # ── Заголовок ──────────────────────────────────────────────────────
    elements.append(Paragraph("ПЕРВИЧНАЯ МЕДИЦИНСКАЯ КАРТОЧКА", s_title))
    elements.append(Paragraph("Форма 100", s_subtitle))
    elements.append(Spacer(1, 2 * mm))

    # ── Сигнальные полосы (флаги) ──────────────────────────────────────
    flag_data: list[list[Paragraph]] = []
    flag_items = [
        ("Неотложная помощь", flags.get("flag_emergency")),
        ("Радиационное поражение", flags.get("flag_radiation")),
        ("Санитарная обработка", flags.get("flag_sanitation")),
    ]
    for label, val in flag_items:
        is_on = _is_truthy(val)
        st = s_flag_on if is_on else s_flag_off
        icon = "● ДА" if is_on else "○ НЕТ"
        flag_data.append([P(label, s_cell_bold), P(icon, st)])

    if flag_data:
        cols = [page_w * 0.55, page_w * 0.45]
        t = Table(flag_data, colWidths=cols)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.97, 0.97, 0.97)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 3 * mm))

    # ── 1. Личные данные ───────────────────────────────────────────────
    elements.append(Paragraph("1. Личные данные", s_section))

    fn = _g(main, "main_full_name") or _g(stub, "stub_full_name") or _g(card, "main_full_name")
    rank = _g(main, "main_rank") or _g(stub, "stub_rank")
    unit = _g(main, "main_unit") or _g(stub, "stub_unit") or _g(card, "main_unit")
    tag = _g(main, "main_id_tag") or _g(stub, "stub_id_tag") or _g(card, "main_id_tag")
    birth = format_date(card.get("birth_date"))
    issued_place = _g(main, "main_issued_place") or _g(bottom, "issued_by")

    ident_rows = [
        _field_row("ФИО", fn),
        _field_row("Звание", rank),
        _field_row("В/часть", unit),
        _field_row("Удостоверение личности, жетон №", tag),
        _field_row("Дата рождения", birth),
        _field_row("Выдана (мед. пункт)", issued_place),
    ]

    # Дата/время выдачи
    iss_date = _g(main, "main_issued_date") or _g(stub, "stub_issued_date")
    iss_time = _g(main, "main_issued_time") or _g(stub, "stub_issued_time")
    if iss_date or iss_time:
        ident_rows.append(_field_row("Дата/время выдачи", f"{iss_date} {iss_time}".strip()))

    cols = [page_w * 0.4, page_w * 0.6]
    t = Table(ident_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    emr_context_raw = card.get("emr_context") or {}
    emr_context = emr_context_raw if isinstance(emr_context_raw, dict) else {}
    if emr_context:
        emr_rows: list[list[Paragraph]] = []
        if emr_context.get("hospital_case_no"):
            emr_rows.append(_field_row("Номер ЭМЗ", emr_context["hospital_case_no"]))
        if emr_context.get("department_name"):
            emr_rows.append(_field_row("Отделение", emr_context["department_name"]))
        patient_name = emr_context.get("patient_full_name")
        card_name = str(card.get("main_full_name") or "")
        if (
            isinstance(patient_name, str)
            and patient_name.strip()
            and card_name.strip()
            and patient_name.strip() != card_name.strip()
        ):
            emr_rows.append(
                _field_row(
                    "ФИО пациента в ЭМЗ",
                    f"{patient_name}  Отличается от ФИО в карточке",
                )
            )
        if emr_context.get("admission_date"):
            emr_rows.append(_field_row("Дата поступления", format_datetime(emr_context["admission_date"])))
        if emr_context.get("injury_date"):
            emr_rows.append(_field_row("Дата травмы", format_datetime(emr_context["injury_date"])))
        if emr_rows:
            elements.append(Paragraph("Связанная госпитализация", s_section))
            emr_table = Table(emr_rows, colWidths=cols)
            emr_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
                ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(emr_table)

    # ── 2. Обстоятельства ──────────────────────────────────────────────
    elements.append(Paragraph("2. Дата/время ранения (заболевания)", s_section))

    inj_date = _g(main, "main_injury_date") or _g(stub, "stub_injury_date")
    inj_time = _g(main, "main_injury_time") or _g(stub, "stub_injury_time")
    circ_rows = [
        _field_row("Дата ранения/заболевания", inj_date or "—"),
        _field_row("Время", inj_time or "—"),
    ]
    t = Table(circ_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── 3. Вид поражения и санитарных потерь ───────────────────────────
    elements.append(Paragraph("3. Вид поражения и санитарных потерь", s_section))

    # Поражения
    all_data = {**main, **lesion}
    lesion_list = _checked_items(all_data, _LESION_LABELS)
    san_list = _checked_items({**main, **san_loss}, _SAN_LOSS_LABELS)

    loss_rows = [
        _field_row("Вид поражения", ", ".join(lesion_list) if lesion_list else "—"),
        _field_row("Вид санитарных потерь", ", ".join(san_list) if san_list else "—"),
    ]

    # Ткани
    if tissue_types:
        loss_rows.append(_field_row("Ткани (подчеркнуть)", ", ".join(tissue_types)))

    # Изоляция
    isolation = _is_truthy(main.get("isolation_required"))
    loss_rows.append(_field_row("Изоляция", "Да" if isolation else "Нет"))

    t = Table(loss_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── 4. Схема тела ──────────────────────────────────────────────────
    heading_4_element = Paragraph("4. Схема тела (локализация повреждений)", s_section)

    bodymap_flowable = _build_bodymap_image_flowable(
        annotations=annotations,
        max_width_pt=page_w,
        max_height_pt=page_w * 0.62,
    )
    if bodymap_flowable is None:
        # Fallback path: if template image is unavailable, keep vector rendering.
        bodymap_flowable = _render_bodymap_drawing(
            annotations,
            tissue_types,
            width_pt=page_w,
            height_pt=page_w * 300 / 440,
        )
    elements.append(KeepTogether([heading_4_element, bodymap_flowable]))
    elements.append(Spacer(1, 2 * mm))

    # Таблица аннотаций
    if annotations:
        ann_header = [
            P("<b>№</b>"),
            P("<b>Тип</b>"),
            P("<b>Проекция</b>"),
            P("<b>Сторона тела</b>"),
            P("<b>Локализация</b>"),
            P("<b>Заметка</b>"),
        ]
        ann_rows = [ann_header]
        for idx, ann in enumerate(annotations, 1):
            x_val = _to_optional_float(ann.get("x"))
            y_val = _to_optional_float(ann.get("y"))
            sil = str(ann.get("silhouette") or "")
            location = coordinates_to_zone(x_val, y_val, sil) if x_val is not None and y_val is not None else "—"
            note = str(ann.get("note", ""))
            ann_rows.append([
                P(str(idx)),
                P(format_annotation_type(ann.get("annotation_type"))),
                P(format_silhouette_short(sil)),
                P(_body_side(x_val)),
                P(location, s_small),
                P(note or "—"),
            ])

        ann_cols = [page_w * 0.06, page_w * 0.16, page_w * 0.15, page_w * 0.17, page_w * 0.22, page_w * 0.24]
        t = Table(ann_rows, colWidths=ann_cols)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.88, 0.92, 0.96)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)
    else:
        elements.append(P("Метки на схеме тела отсутствуют.", s_small))
    # ── 5. Медицинская помощь ──────────────────────────────────────────
    elements.append(Paragraph("5. Медицинская помощь", s_section))

    mp = {**main, **medical_help}
    mp_rows: list[list[Paragraph]] = [
        [P("<b>Мероприятие</b>"), P("<b>Выполнено</b>"), P("<b>Доза / Тип</b>")],
    ]

    mp_items = [
        ("Антибиотик", "mp_antibiotic", "mp_antibiotic_dose", None),
        ("Сыворотка ПСС", "mp_serum_pss", "mp_serum_pss_details", "mp_serum_dose"),
        ("Сыворотка ПГС", "mp_serum_pgs", "mp_serum_pgs_details", "mp_serum_dose"),
        ("Анатоксин", None, "mp_toxoid", None),
        ("Антидот", None, "mp_antidote", None),
        ("Обезболивающее средство", "mp_analgesic", "mp_analgesic_dose", None),
        ("Переливание крови", "mp_transfusion_blood", "mp_transfusion_blood_details", None),
        ("Кровезаменители", "mp_transfusion_substitute", "mp_transfusion_substitute_details", None),
        ("Иммобилизация", "mp_immobilization", "mp_immobilization_details", None),
        ("Перевязка", "mp_bandage", "mp_bandage_details", None),
        ("Оперативное вмешательство", "mp_surgical_intervention", "mp_surgical_intervention_details", None),
    ]

    for label, check_key, dose_key, fallback_key in mp_items:
        if check_key:
            raw_done = mp.get(check_key)
            done_style = s_unset if raw_done is None else s_cell
            done_cell = P(_fmt_bool_field(raw_done), done_style)
        else:
            done_cell = P("—")

        dose = _g(mp, dose_key) if dose_key else "—"
        if not dose and fallback_key:
            dose = _g(mp, fallback_key)
        if not check_key:
            done_cell = P("—" if not dose or dose == "—" else "Да")
        mp_rows.append([P(label), done_cell, P(dose or "—")])
    # Дополнительно из корешка
    stub_checks = [
        ("Антибиотик (корешок)", "stub_med_help_antibiotic", "stub_antibiotic_dose"),
        ("Сыворотка ПСС/ПГС (корешок)", "stub_med_help_serum", "stub_pss_pgs_dose"),
        ("Анатоксин (корешок)", "stub_med_help_toxoid", "stub_toxoid_type"),
        ("Антидот (корешок)", "stub_med_help_antidote", "stub_antidote_type"),
        ("Обезболивающее (корешок)", "stub_med_help_analgesic", "stub_analgesic_dose"),
        ("Переливание (корешок)", "stub_transfusion", None),
        ("Иммобилизация (корешок)", "stub_immobilization", None),
        ("Жгут/санобработка (корешок)", "stub_tourniquet", None),
    ]
    has_stub_data = any(_is_truthy(stub.get(k)) for _, k, _ in stub_checks)
    if has_stub_data:
        for label, check_key, stub_dose_key in stub_checks:
            raw_done = stub.get(check_key)
            done_style = s_unset if raw_done is None else s_small
            done = _fmt_bool_field(raw_done)
            dose = _g(stub, stub_dose_key) if stub_dose_key else "—"
            mp_rows.append([P(label, s_small), P(done, done_style), P(dose, s_small)])

    mp_cols = [page_w * 0.45, page_w * 0.2, page_w * 0.35]
    t = Table(mp_rows, colWidths=mp_cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.88, 0.92, 0.96)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── 6. Эвакуация ──────────────────────────────────────────────────
    elements.append(Paragraph("6. Эвакуация", s_section))

    tourniquet_time = _g(bottom, "tourniquet_time")
    sanitation_type = _g(bottom, "sanitation_type")
    evac_dest = _g(bottom, "evacuation_dest") or _g(stub, "stub_evacuation_dest")
    evac_priority = _g(bottom, "evacuation_priority")
    transport_type = _g(bottom, "transport_type")
    stub_evac_method = _g(stub, "stub_evacuation_method")

    evac_rows = [
        _field_row("Жгут наложен (время)", tourniquet_time or "—"),
        _field_row("Санитарная обработка", sanitation_type or "—"),
        _field_row("Эвакуирован (корешок)", stub_evac_method or "—"),
        _field_row("Куда эвакуирован", evac_dest or "—"),
        _field_row("Очерёдность эвакуации", evac_priority or "—"),
        _field_row("Вид транспорта", transport_type or "—"),
    ]

    t = Table(evac_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── 7. Диагноз ────────────────────────────────────────────────────
    elements.append(Paragraph("7. Диагноз", s_section))

    diag_main = _g(bottom, "main_diagnosis") or _g(main, "main_diagnosis") or _g(card, "main_diagnosis")
    diag_stub = _g(stub, "stub_diagnosis")

    diag_rows = [
        _field_row("Диагноз (основной)", diag_main),
    ]
    if diag_stub and diag_stub != diag_main:
        diag_rows.append(_field_row("Диагноз (корешок)", diag_stub))

    t = Table(diag_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── 8. Подпись врача ───────────────────────────────────────────────
    elements.append(Paragraph("8. Подпись врача", s_section))

    doctor = _g(bottom, "doctor_signature")
    signed_by = str(card.get("signed_by") or "")
    signed_at = format_datetime(card.get("signed_at"))
    status = str(card.get("status") or "DRAFT")

    sign_rows = [
        _field_row("Врач (подпись)", doctor or signed_by or "—"),
        _field_row("Статус карточки", "Подписано" if status == "SIGNED" else "Черновик"),
    ]
    if card.get("signed_at") is not None:
        sign_rows.append(_field_row("Дата подписания", signed_at))

    t = Table(sign_rows, colWidths=cols)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.8, 0.8, 0.8)),
        ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.94, 0.96, 0.98)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── Нижний колонтитул ──────────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))
    card_id = str(card.get("id") or "")
    if status == "SIGNED":
        version = str(card.get("signed_version") or card.get("version") or "")
    else:
        version = "(черновик)"
    short_id = card_id[:8] if card_id else "—"
    footer_text = f"ID: {card_id or short_id}   Ревизия: {version}"
    elements.append(Paragraph(footer_text, s_small))

    # ── Сборка ─────────────────────────────────────────────────────────
    build_invariant_pdf(doc, elements)
