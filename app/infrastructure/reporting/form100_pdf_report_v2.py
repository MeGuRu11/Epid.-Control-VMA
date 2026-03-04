"""Форма 100 — структурированный текстовый PDF-отчёт.

Вместо рисования канвасом точной копии бланка, генерирует чистый, читаемый
отчёт со всеми заполненными полями и встроенной схемой тела (bodymap) с
нанесёнными врачом метками.
"""
from __future__ import annotations

import json
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
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name

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


# ── Помощники ────────────────────────────────────────────────────────────────

def _g(d: dict[str, Any], key: str, default: str = "") -> str:
    """Безопасно достать строку из dict."""
    v = d.get(key)
    if v is None:
        return default
    return str(v).strip() or default


def _is_truthy(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


def _checked_items(d: dict[str, Any], labels: dict[str, str]) -> list[str]:
    return [label for key, label in labels.items() if _is_truthy(d.get(key, ""))]


def _parse_annotations(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return raw  # type: ignore[return-value]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed  # type: ignore[return-value]
        except (json.JSONDecodeError, ValueError):
            pass
    return []


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
    d.add(Rect(0, 0, width_pt, height_pt, fillColor=colors.Color(0.97, 0.97, 0.97), strokeColor=colors.Color(0.85, 0.85, 0.85), strokeWidth=0.5))

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
        x_norm = float(ann.get("x", 0.5))
        y_norm = float(ann.get("y", 0.5))

        cx_base = mid / 2 if "back" not in sil else mid + mid / 2
        body_w_half = 45
        ax = cx_base + (x_norm - 0.5) * body_w_half * 2
        ay = body_top - 6 - y_norm * (body_h - 12)

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

    def _field_row(label: str, value: str) -> list[Paragraph]:
        return [P(f"<b>{label}</b>", s_cell_bold), P(value or "—")]

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
    birth = str(card.get("birth_date") or "")
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
    elements.append(Paragraph("4. Схема тела (локализация повреждений)", s_section))

    if annotations:
        bm_drawing = _render_bodymap_drawing(annotations, tissue_types, width_pt=page_w, height_pt=page_w * 300 / 440)
        elements.append(bm_drawing)
        elements.append(Spacer(1, 2 * mm))

        # Таблица аннотаций
        ann_header = [P("<b>№</b>"), P("<b>Тип</b>"), P("<b>Сторона</b>"), P("<b>Координаты</b>"), P("<b>Заметка</b>")]
        ann_rows = [ann_header]
        for idx, ann in enumerate(annotations, 1):
            atype = str(ann.get("annotation_type", ""))
            sil = str(ann.get("silhouette", ""))
            ax = float(ann.get("x", 0))
            ay = float(ann.get("y", 0))
            note = str(ann.get("note", ""))
            ann_rows.append([
                P(str(idx)),
                P(_ANNOTATION_LABELS.get(atype, atype)),
                P(_SILHOUETTE_LABELS.get(sil, sil)),
                P(f"X={ax:.2f}, Y={ay:.2f}", s_small),
                P(note or "—"),
            ])

        ann_cols = [page_w * 0.06, page_w * 0.22, page_w * 0.2, page_w * 0.22, page_w * 0.3]
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
        ("Антибиотик", "mp_antibiotic", "mp_antibiotic_dose"),
        ("Сыворотка ПСС", "mp_serum_pss", "mp_serum_dose"),
        ("Сыворотка ПГС", "mp_serum_pgs", "mp_serum_dose"),
        ("Анатоксин", None, "mp_toxoid"),
        ("Антидот", None, "mp_antidote"),
        ("Обезболивающее средство", "mp_analgesic", "mp_analgesic_dose"),
        ("Переливание крови", "mp_transfusion_blood", None),
        ("Кровезаменители", "mp_transfusion_substitute", None),
        ("Иммобилизация", "mp_immobilization", None),
        ("Перевязка", "mp_bandage", None),
    ]

    for label, check_key, dose_key in mp_items:
        done = "Да" if check_key and _is_truthy(mp.get(check_key)) else ("—" if check_key else "—")
        dose = _g(mp, dose_key) if dose_key else "—"
        if not check_key:
            done = "—" if not dose or dose == "—" else "Да"
        mp_rows.append([P(label), P(done), P(dose)])

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
        for label, check_key, dose_key in stub_checks:
            done = "Да" if _is_truthy(stub.get(check_key)) else "—"
            dose = _g(stub, dose_key) if dose_key else "—"
            mp_rows.append([P(label, s_small), P(done, s_small), P(dose, s_small)])

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
    signed_at = str(card.get("signed_at") or "")
    status = str(card.get("status") or "DRAFT")

    sign_rows = [
        _field_row("Врач (подпись)", doctor or signed_by or "—"),
        _field_row("Статус карточки", "Подписано" if status == "SIGNED" else "Черновик"),
    ]
    if signed_at:
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
    version = str(card.get("version") or "")
    footer_text = f"Карточка ID: {card_id}   Версия: {version}"
    elements.append(Paragraph(footer_text, s_small))

    # ── Сборка ─────────────────────────────────────────────────────────
    doc.build(elements)
