from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.infrastructure.reporting.pdf_fonts import get_pdf_unicode_font_name


def _s(data: dict[str, Any], alt: dict[str, Any], card: dict[str, Any], key: str, default: str = "") -> str:
    v = data.get(key) or alt.get(key) or card.get(key)
    return str(v) if v is not None else default


def export_form100_pdf_v2(*, card: dict[str, Any], file_path: str | Path) -> None:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    data_payload = card.get("data") or {}
    main = data_payload.get("main") or {}
    bottom = data_payload.get("bottom") or {}
    flags = data_payload.get("flags") or {}
    
    font = get_pdf_unicode_font_name()
    c = canvas.Canvas(str(file_path), pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Offsets and grid dimensions
    margin_x = 10 * mm
    margin_y = 10 * mm
    usable_w = width - 2 * margin_x
    usable_h = height - 2 * margin_y
    
    # ------------------
    # 1. COLOR BANDS (TEAR OFFS)
    # ------------------
    c.setLineWidth(0.5)
    
    band_height = 10 * mm
    band_width = 10 * mm
    
    # Top RED: Неотложная помощь
    has_red = flags.get("flag_emergency", False)
    if has_red:
        c.setFillColorRGB(0.9, 0.1, 0.1)
    else:
        c.setFillColorRGB(0.95, 0.95, 0.95)
    
    c.rect(margin_x + 90*mm, height - margin_y - band_height, usable_w - 90*mm, band_height, stroke=1, fill=1)
    
    # Bottom BLUE: Радиационное поражение
    has_blue = flags.get("flag_radiation", False)
    if has_blue:
        c.setFillColorRGB(0.1, 0.5, 0.9)
    else:
        c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(margin_x + 90*mm, margin_y, usable_w - 90*mm, band_height, stroke=1, fill=1)
    
    # Left BLACK: Изоляция
    has_black = flags.get("flag_isolation", False)
    if has_black:
        c.setFillColorRGB(0.1, 0.1, 0.1)
    else:
        c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(margin_x + 90*mm, margin_y + band_height, band_width, usable_h - 2*band_height, stroke=1, fill=1)
    
    # Right YELLOW: Санитарная обработка
    has_yellow = flags.get("flag_sanitation", False)
    if has_yellow:
        c.setFillColorRGB(0.9, 0.8, 0.1)
    else:
        c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(width - margin_x - band_width, margin_y + band_height, band_width, usable_h - 2*band_height, stroke=1, fill=1)
    
    # Draw Band Text
    c.setFillColorRGB(0, 0, 0)
    if has_black:
        c.setFillColorRGB(1, 1, 1)
    
    c.saveState()
    c.translate(margin_x + 90*mm + band_width/2, height/2)
    c.rotate(90)
    c.setFont(font, 14)
    c.drawCentredString(0, -4, "ИЗОЛЯЦИЯ")
    c.restoreState()
    
    c.setFillColorRGB(0, 0, 0)
    c.saveState()
    c.translate(width - margin_x - band_width/2, height/2)
    c.rotate(90)
    c.setFont(font, 14)
    c.drawCentredString(0, -4, "САНИТАРНАЯ ОБРАБОТКА")
    c.restoreState()
    
    if has_blue:
        c.setFillColorRGB(1, 1, 1)
    else:
        c.setFillColorRGB(0, 0, 0)
    c.setFont(font, 14)
    c.drawCentredString(margin_x + 90*mm + (usable_w - 90*mm)/2, margin_y + band_height/2 - 4, "РАДИАЦИОННОЕ ПОРАЖЕНИЕ")
    
    if has_red:
        c.setFillColorRGB(1, 1, 1)
    else:
        c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(margin_x + 90*mm + (usable_w - 90*mm)/2, height - margin_y - band_height/2 - 4, "НЕОТЛОЖНАЯ ПОМОЩЬ")
    
    c.setFillColorRGB(0, 0, 0)
    
    # ------------------
    # 2. STUB (КОРЕШОК)
    # ------------------
    stub_w = 85 * mm
    stub_x = margin_x
    top_y = height - margin_y
    
    c.rect(stub_x, margin_y, stub_w, usable_h, stroke=1, fill=0)
    
    def dr_line(x1, y1, x2, y2):
        c.line(x1, y1, x2, y2)
        
    def dr_text(x, y, txt, size=9, align="left", bold=False):
        c.setFont(font, size) # Assuming font is unicode standard. Using basic for now, can't bold natively easily without registering -B font.
        if align == "center":
            c.drawCentredString(x, y, txt)
        elif align == "right":
            c.drawRightString(x, y, txt)
        else:
            c.drawString(x, y, txt)
            
    # Stub Header
    c.setFont(font, 10)
    c.drawCentredString(stub_x + stub_w/2, top_y - 8*mm, "КОРЕШОК ПЕРВИЧНОЙ")
    c.drawCentredString(stub_x + stub_w/2, top_y - 12*mm, "МЕДИЦИНСКОЙ КАРТОЧКИ")
    dr_line(stub_x, top_y - 15*mm, stub_x + stub_w, top_y - 15*mm)
    
    cur_y = top_y - 20*mm
    rank = _s(main, bottom, card, "main_rank")
    c_unit = _s(main, bottom, card, "main_unit")
    time_h = _s(main, bottom, card, "main_time", "  :  ").split(":")[0]
    time_m = _s(main, bottom, card, "main_time", "  :  ")[-2:]
    dr_text(stub_x + 2*mm, cur_y, f"« {time_h} » час ____ {time_m} ____ мин. ________ 20__ г.")
    
    cur_y -= 8*mm
    dr_text(stub_x + 2*mm, cur_y, f"в/звание {rank}")
    dr_text(stub_x + 40*mm, cur_y, f"в/часть {c_unit}")
    dr_line(stub_x + 15*mm, cur_y - 1*mm, stub_x + 38*mm, cur_y - 1*mm) # rank line
    dr_line(stub_x + 52*mm, cur_y - 1*mm, stub_x + stub_w - 2*mm, cur_y - 1*mm) # unit line
    
    cur_y -= 10*mm
    names = _s(main, bottom, card, "main_full_name").split(" ")
    lname = names[0] if len(names) > 0 else ""
    fname = names[1] if len(names) > 1 else ""
    mname = names[2] if len(names) > 2 else ""
    dr_text(stub_x + stub_w/2, cur_y, f"{lname}           {fname}           {mname}", align="center")
    dr_line(stub_x + 2*mm, cur_y - 1*mm, stub_x + stub_w - 2*mm, cur_y - 1*mm)
    dr_text(stub_x + stub_w/2, cur_y - 3*mm, "фамилия                 имя                 отчество", size=6, align="center")
    
    cur_y -= 8*mm
    tag = _s(main, bottom, card, "main_id_tag")
    dr_text(stub_x + 2*mm, cur_y, f"Удостоверение личности, жетон № {tag}")
    dr_line(stub_x + 55*mm, cur_y - 1*mm, stub_x + stub_w - 2*mm, cur_y - 1*mm)
    
    cur_y -= 8*mm
    dr_text(stub_x + 2*mm, cur_y, "Ранен, заболел «   » час «   » __________ 20___ г.")
    
    # Stub Evac Block
    cur_y -= 2*mm
    dr_line(stub_x, cur_y, stub_x + stub_w, cur_y)
    dr_text(stub_x + 2*mm, cur_y - 5*mm, "Эвакуирован са-", size=8)
    dr_text(stub_x + 2*mm, cur_y - 9*mm, "молетом, сан-", size=8)
    dr_text(stub_x + 2*mm, cur_y - 13*mm, "грузавто", size=8)
    dr_text(stub_x + 2*mm, cur_y - 17*mm, "(подчеркнуть)", size=7)
    
    dr_line(stub_x + 30*mm, cur_y, stub_x + 30*mm, cur_y - 20*mm)
    dr_text(stub_x + 32*mm + (stub_w - 30*mm)/2, cur_y - 4*mm, "куда эвакуирован", size=7, align="center")
    dr_line(stub_x + 30*mm, cur_y - 5*mm, stub_x + stub_w, cur_y - 5*mm)
    
    # Draw simple Plus targets
    evac_dest = _s(main, bottom, card, "evac_destination")
    evac_method_str = _s(main, bottom, card, "evacuation_method", "").lower()
    
    # "Эвакуирован самолетом, сангрузавто" underlines
    if "авиа" in evac_method_str or "верт" in evac_method_str or "само" in evac_method_str:
        dr_line(stub_x + 2*mm, cur_y - 6*mm, stub_x + 28*mm, cur_y - 6*mm) # Underline "самолетом"
    elif "авто" in evac_method_str or "маши" in evac_method_str:
        dr_line(stub_x + 2*mm, cur_y - 14*mm, stub_x + 28*mm, cur_y - 14*mm) # Underline "сан-грузавто"

    dr_text(stub_x + 32*mm + (stub_w - 30*mm)/2, cur_y - 15*mm, evac_dest, align="center", size=8)
    dr_line(stub_x + 30*mm, cur_y - 17*mm, stub_x + stub_w, cur_y - 17*mm)
    dr_text(stub_x + 32*mm + (stub_w - 30*mm)/2, cur_y - 19.5*mm, "нужное обвести", size=7, align="center")
    
    # Add fake icon crosses and circle the chosen one loosely based on evac_method
    ico1_x = stub_x + 30*mm + 10*mm
    ico2_x = stub_x + 30*mm + 25*mm
    ico3_x = stub_x + 30*mm + 40*mm
    c.circle(ico1_x, cur_y - 7*mm, 3*mm)
    dr_text(ico1_x, cur_y - 7*mm - 2*mm, "+", align="center")
    c.circle(ico2_x, cur_y - 7*mm, 3*mm)
    dr_text(ico2_x, cur_y - 7*mm - 2*mm, "+", align="center")
    c.rect(ico3_x - 3*mm, cur_y - 10*mm, 6*mm, 6*mm)
    c.line(ico3_x - 4*mm, cur_y - 4*mm, ico3_x, cur_y)
    c.line(ico3_x, cur_y, ico3_x + 4*mm, cur_y - 4*mm)
    dr_text(ico3_x, cur_y - 7*mm - 2*mm, "+", size=6, align="center")
    
    # "Circle" if hospital is chosen
    if "госп" in evac_dest.lower() or "вмед" in evac_dest.lower() or "омедб" in evac_dest.lower():
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.setLineWidth(1)
        # Tight ellipse around the house icon
        c.ellipse(ico3_x - 4*mm, cur_y - 11*mm, ico3_x + 4*mm, cur_y + 1*mm)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)

    cur_y -= 20*mm
    dr_line(stub_x, cur_y, stub_x + stub_w, cur_y)
    
    # Stub Table "МЕДИЦИНСКАЯ ПОМОЩЬ"
    dr_text(stub_x + stub_w/2, cur_y - 5*mm, "МЕДИЦИНСКАЯ ПОМОЩЬ", size=10, align="center")
    cur_y -= 7*mm
    dr_line(stub_x, cur_y, stub_x + stub_w, cur_y)
    
    med_cols = [stub_x, stub_x + 60*mm, stub_x + stub_w]
    med_rows = [cur_y, cur_y - 8*mm, cur_y - 16*mm, cur_y - 24*mm, cur_y - 32*mm, cur_y - 40*mm, cur_y - 48*mm, cur_y - 60*mm, cur_y - 70*mm]
    
    for r in med_rows:
        dr_line(med_cols[0], r, med_cols[-1], r)
    for c_i in med_cols:
        dr_line(c_i, med_rows[0], c_i, med_rows[-1])
        
    dr_text(med_cols[0] + 30*mm, med_rows[0] - 5*mm, "Подчеркнуть", align="center", size=8)
    dr_text(med_cols[1] + 12*mm, med_rows[0] - 4*mm, "Доза", align="center", size=8)
    dr_text(med_cols[1] + 12*mm, med_rows[0] - 7*mm, "(вписать)", align="center", size=6)
    
    dr_text(med_cols[0] + 2*mm, med_rows[1] - 5*mm, "Введено: антибиотик", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[2] - 3.5*mm, "сыворотка ПСС,", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[2] - 7*mm, "ПГС", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[3] - 5*mm, "анатоксин (какой)", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[4] - 5*mm, "антидот (какой)", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[5] - 3.5*mm, "обезболивающее", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[5] - 7*mm, "средство", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[6] - 5*mm, "Произведено: переливание", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[7] - 3.5*mm, "крови, кровезаменителей,", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[7] - 7*mm, "иммобилизация, перевязка,", size=8)
    dr_text(med_cols[0] + 2*mm, med_rows[8] - 5*mm, "наложен жгут, санобработка", size=8)
    
    # Stub Footer
    cur_y = margin_y + 15*mm
    dr_line(stub_x, cur_y, stub_x + stub_w, cur_y)
    
    diag = _s(main, bottom, card, "main_diagnosis")
    dr_text(stub_x + 2*mm, cur_y - 4*mm, "Диагноз", size=9)
    
    # Simple word wrap for diag
    words = diag.split(" ")
    lines = []
    line = ""
    for w in words:
        if stringWidth(line + " " + w, font, 9) < stub_w - 4*mm:
            line += " " + w
        else:
            lines.append(line.strip())
            line = w
    if line:
        lines.append(line.strip())
        
    y_d = cur_y - 8*mm
    for ln in lines[:4]:
        dr_text(stub_x + 2*mm, y_d, ln, size=8)
        dr_line(stub_x + 2*mm, y_d - 1*mm, stub_x + stub_w - 2*mm, y_d - 1*mm)
        y_d -= 4*mm
    
    # Cut line Gap
    dr_line(stub_x + stub_w + 3*mm, top_y, stub_x + stub_w + 3*mm, margin_y)
    for i in range(40):
        dr_text(stub_x + stub_w + 1*mm, margin_y + i*5*mm, "|", size=8)
        
    
    # ------------------
    # 3. MAIN CARD
    # ------------------
    m_x = stub_x + stub_w + 5*mm + 10*mm # plus black band
    m_y_top = top_y - band_height
    m_w = width - margin_x - band_width - m_x
    
    # Header Main
    dr_text(m_x + m_w/2, m_y_top - 6*mm, "Первичная медицинская карточка", size=14, align="center")
    dr_text(m_x + m_w - 2*mm, m_y_top - 6*mm, "Форма 100", align="right", size=9)
    dr_line(m_x, m_y_top - 9*mm, m_x + m_w, m_y_top - 9*mm)
    
    cur_y = m_y_top - 14*mm
    org_name = _s(main, bottom, card, "issued_by")
    dr_text(m_x, cur_y, "Выдана:")
    dr_text(m_x + 15*mm, cur_y, org_name)
    dr_line(m_x + 15*mm, cur_y - 1*mm, m_x + 100*mm, cur_y - 1*mm)
    dr_text(m_x + 15*mm, cur_y - 3*mm, "наименование мед. пункта (учреждения), или их штамп.", size=6)
    
    dr_text(m_x + 130*mm, cur_y, "МЕДИЦИНСКАЯ ПОМОЩЬ", size=10)
    
    cur_y -= 8*mm
    dr_text(m_x, cur_y, f"« {time_h} » час ____ {time_m} ____ мин. ________ 20__ г.")
    
    # ------------------
    # MEDICAL HELP TABLE MAIN Right
    # ------------------
    # Right side table width
    r_tab_w = 75*mm
    r_tab_x = m_x + m_w - r_tab_w
    
    mt_cols = [r_tab_x, r_tab_x + 55*mm, r_tab_x + r_tab_w]
    mt_rows = [cur_y + 3*mm, cur_y - 4*mm, cur_y - 11*mm, cur_y - 18*mm, cur_y - 25*mm, cur_y - 32*mm, cur_y - 39*mm, cur_y - 46*mm, cur_y - 53*mm]
    for r in mt_rows:
        dr_line(mt_cols[0], r, mt_cols[-1], r)
    for c_i in mt_cols:
        dr_line(c_i, mt_rows[0], c_i, mt_rows[-1])
        
    dr_text(mt_cols[0] + 5*mm, mt_rows[0] - 4*mm, "Подчеркнуть", size=8)
    dr_text(mt_cols[1] + 10*mm, mt_rows[0] - 4*mm, "Доза", align="center", size=8)
    dr_text(mt_cols[1] + 10*mm, mt_rows[0] - 6.5*mm, "(вписать)", size=6, align="center")
    
    dr_text(mt_cols[0] + 2*mm, mt_rows[1] - 5*mm, "Введено: антибиотик", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[2] - 5*mm, "Сыворотка ПСС, ПГС", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[3] - 5*mm, "анатоксин (какой)", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[4] - 5*mm, "антидот (какой)", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[5] - 5*mm, "обезболивающее средство", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[6] - 5*mm, "Произведено: переливание", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[7] - 5*mm, "крови, кровезаменителей", size=8)
    dr_text(mt_cols[0] + 2*mm, mt_rows[8] - 5*mm, "иммобилизация, перевязка", size=8)
    
    # ------------------
    # INDENTITY FIELDS MAIN Left
    # ------------------
    cur_y -= 7*mm
    dr_text(m_x, cur_y, f"в/звание {rank}")
    dr_text(m_x + 50*mm, cur_y, f"в/часть {c_unit}")
    dr_line(m_x + 15*mm, cur_y - 1*mm, m_x + 48*mm, cur_y - 1*mm)
    dr_line(m_x + 62*mm, cur_y - 1*mm, r_tab_x - 5*mm, cur_y - 1*mm)
    
    cur_y -= 8*mm
    dr_text(m_x + 55*mm, cur_y, f"{lname}           {fname}           {mname}", align="center")
    dr_line(m_x, cur_y - 1*mm, r_tab_x - 5*mm, cur_y - 1*mm)
    dr_text(m_x + 55*mm, cur_y - 4*mm, "фамилия                 имя                 отчество", size=6, align="center")
    
    cur_y -= 8*mm
    dr_text(m_x, cur_y, f"Удостоверение личности, жетон № {tag}")
    dr_line(m_x + 55*mm, cur_y - 1*mm, r_tab_x - 5*mm, cur_y - 1*mm)
    
    cur_y -= 8*mm
    dr_text(m_x, cur_y, "Ранен, заболел «   » час «   » __________ 20___ г.")
    
    # ------------------
    # SANITARY LOSS SIDEBAR
    # ------------------
    sb_w = 35 * mm
    sb_x = m_x
    sb_y_top = cur_y - 5*mm
    sb_y_bot = margin_y + band_height + 15*mm
    # Sanitary Loss Sidebar Outline
    dr_line(sb_x, sb_y_top, sb_x + sb_w, sb_y_top)
    dr_line(sb_x, sb_y_bot, sb_x + sb_w, sb_y_bot)
    dr_line(sb_x, sb_y_top, sb_x, sb_y_bot)
    dr_line(sb_x + sb_w, sb_y_top, sb_x + sb_w, sb_y_bot)
    dr_line(sb_x + 6*mm, sb_y_top, sb_x + 6*mm, sb_y_bot)
    
    c.saveState()
    c.translate(sb_x + 3*mm, sb_y_bot + (sb_y_top - sb_y_bot)/2)
    c.rotate(90)
    c.setFont(font, 8)
    c.drawCentredString(0, 0, "Вид санитарных потерь (обвести)")
    c.restoreState()
    
    sb_ch = (sb_y_top - sb_y_bot) / 8
    
    def dr_gun(cx, cy):
        # Draw gun with lines to avoid huge fill blobs
        c.line(cx-10*mm, cy+2*mm, cx+5*mm, cy+2*mm) # barrel top
        c.line(cx-10*mm, cy+4*mm, cx+5*mm, cy+4*mm) # barrel thin
        c.line(cx-4*mm, cy+2*mm, cx-4*mm, cy-3*mm) # grip front
        c.line(cx-8*mm, cy+2*mm, cx-8*mm, cy-3*mm) # grip back
        c.line(cx-4*mm, cy-3*mm, cx-8*mm, cy-3*mm) # grip bot
        c.circle(cx-6*mm, cy+0*mm, 1*mm) # trigger
        c.line(cx-5*mm, cy+2*mm, cx-5*mm, cy-1*mm) # guard
        c.drawString(cx-14*mm, cy-2*mm, "О")
        
    def dr_bomb(cx, cy):
        c.circle(cx, cy, 3*mm)
        c.line(cx, cy+3*mm, cx+2*mm, cy+5*mm) # fuse
        c.circle(cx+2*mm, cy+5*mm, 0.5*mm)
        c.line(cx+3*mm, cy+6*mm, cx+4*mm, cy+7*mm) # spark
        c.line(cx+3*mm, cy+4*mm, cx+5*mm, cy+4*mm) # spark
        c.drawString(cx-14*mm, cy-2*mm, "Я")
        
    def dr_mask(cx, cy):
        c.ellipse(cx-4*mm, cy-4*mm, cx+4*mm, cy+4*mm) # face
        c.circle(cx-2*mm, cy+1*mm, 1.5*mm) # eye l
        c.circle(cx+2*mm, cy+1*mm, 1.5*mm) # eye r
        c.circle(cx, cy-2*mm, 1.5*mm) # filter
        c.drawString(cx-14*mm, cy-2*mm, "X")
        
    def dr_bug(cx, cy):
        c.ellipse(cx-4*mm, cy-2*mm, cx+4*mm, cy+2*mm) # body
        c.circle(cx+4*mm, cy, 1.5*mm) # head
        c.line(cx-2*mm, cy+2*mm, cx-3*mm, cy+4*mm) # leg
        c.line(cx+2*mm, cy+2*mm, cx+3*mm, cy+4*mm) # leg
        c.line(cx-2*mm, cy-2*mm, cx-3*mm, cy-4*mm) # leg
        c.line(cx+2*mm, cy-2*mm, cx+3*mm, cy-4*mm) # leg
        c.drawString(cx-14*mm, cy-2*mm, "Бак.")
        
    def dr_knife(cx, cy):
        c.line(cx-6*mm, cy-4*mm, cx+2*mm, cy+2*mm) # blade back
        c.line(cx-4*mm, cy-6*mm, cx+2*mm, cy+2*mm) # blade edge
        c.line(cx-6*mm, cy-4*mm, cx-4*mm, cy-6*mm) # blade base
        c.line(cx-6*mm, cy-6*mm, cx-8*mm, cy-8*mm) # handle
        c.line(cx-7*mm, cy-5*mm, cx-3*mm, cy-7*mm) # guard
        c.setFont(font, 6)
        c.drawString(cx-14*mm, cy, "Другие")
        c.drawString(cx-14*mm, cy-3*mm, "пораж.")
        c.setFont(font, 9)
        
    def dr_flame(cx, cy):
        c.line(cx, cy-4*mm, cx, cy+4*mm)
        c.line(cx-2*mm, cy, cx+2*mm, cy)
        c.line(cx-2*mm, cy-2*mm, cx+2*mm, cy+2*mm)
        c.line(cx-2*mm, cy+2*mm, cx+2*mm, cy-2*mm)
        c.circle(cx, cy, 3*mm, fill=0, stroke=1)
        c.drawString(cx-14*mm, cy-2*mm, "Отм.")
        
    def dr_bed(cx, cy):
        c.rect(cx-6*mm, cy-2*mm, 12*mm, 2*mm) # matress
        c.line(cx-5*mm, cy-2*mm, cx-5*mm, cy-4*mm) # leg
        c.line(cx+5*mm, cy-2*mm, cx+5*mm, cy-4*mm) # leg
        c.line(cx-6*mm, cy, cx-6*mm, cy+3*mm) # headboard
        c.circle(cx+2*mm, cy+1*mm, 1.5*mm) # head
        c.line(cx-4*mm, cy+0.5*mm, cx+1*mm, cy+0.5*mm) # body
        c.drawString(cx-14*mm, cy-2*mm, "Б")
        
    def dr_rad(cx, cy):
        c.ellipse(cx-4*mm, cy-3*mm, cx+4*mm, cy+3*mm)
        c.circle(cx-2*mm, cy+1*mm, 1.5*mm) # eye
        c.circle(cx+2*mm, cy+1*mm, 1.5*mm) # eye
        c.line(cx-4*mm, cy+1*mm, cx-5*mm, cy+3*mm) # antenna
        c.line(cx+4*mm, cy+1*mm, cx+5*mm, cy+3*mm) # antenna
        c.drawString(cx-14*mm, cy-2*mm, "И")

    icon_funcs = [dr_gun, dr_bomb, dr_mask, dr_bug, dr_knife, dr_flame, dr_bed, dr_rad]
    
    for i, func in enumerate(icon_funcs):
        y_box = sb_y_top - (i+1)*sb_ch
        c.line(sb_x, y_box, sb_x + sb_w, y_box)
        func(sb_x + 20*mm, y_box + sb_ch/2)
        c.circle(sb_x + sb_w - 7*mm, y_box + sb_ch/2, 5*mm, fill=0, stroke=1)
        
    # ------------------
    # BODYMAP CENTER
    # ------------------
    bm_y = sb_y_top - 65*mm
    bm_x = sb_x + sb_w + 35*mm
    c.drawCentredString(bm_x, bm_y + 60*mm, "[ Силуэты Человека: спереди / сзади ]")
    c.drawCentredString(bm_x, bm_y + 55*mm, "локализацию обвести")
    
    # Draw simple stickmen
    c.circle(bm_x - 15*mm, bm_y + 45*mm, 4*mm) # head
    c.ellipse(bm_x - 20*mm, bm_y + 20*mm, bm_x - 10*mm, bm_y + 41*mm) # torso
    c.line(bm_x - 21*mm, bm_y + 38*mm, bm_x - 26*mm, bm_y + 15*mm) # left arm
    c.line(bm_x - 9*mm, bm_y + 38*mm, bm_x - 4*mm, bm_y + 15*mm) # right arm
    c.line(bm_x - 17*mm, bm_y + 20*mm, bm_x - 20*mm, bm_y) # left leg
    c.line(bm_x - 13*mm, bm_y + 20*mm, bm_x - 10*mm, bm_y) # right leg

    c.circle(bm_x + 15*mm, bm_y + 45*mm, 4*mm) # head
    c.ellipse(bm_x + 10*mm, bm_y + 20*mm, bm_x + 20*mm, bm_y + 41*mm) # torso
    c.line(bm_x + 9*mm, bm_y + 38*mm, bm_x + 4*mm, bm_y + 15*mm) # left arm
    c.line(bm_x + 21*mm, bm_y + 38*mm, bm_x + 26*mm, bm_y + 15*mm) # right arm
    c.line(bm_x + 13*mm, bm_y + 20*mm, bm_x + 10*mm, bm_y) # left leg
    c.line(bm_x + 17*mm, bm_y + 20*mm, bm_x + 20*mm, bm_y) # right leg
    
    # Map bodymap annotations from DB standard layout to the mini PDF stickmen
    annotations = data_payload.get("bodymap_annotations") or []
    c.setLineWidth(1)
    
    for ann in annotations:
        sil = ann.get("silhouette")
        atype = ann.get("annotation_type", "")
        # The UI maps are approx 200x500 pixels. We map that generic ratio to our 50mm tall stickmen.
        x_norm = float(ann.get("x", 0.5))
        y_norm = float(ann.get("y", 0.5))
        
        base_y = bm_y + (1.0 - y_norm) * 50*mm
        if sil == "male_front":
            base_x = (bm_x - 15*mm) + (x_norm - 0.5) * 20*mm
        else:
            base_x = (bm_x + 15*mm) + (x_norm - 0.5) * 20*mm
            
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.circle(base_x, base_y, 2*mm)
        c.setFillColorRGB(0.8, 0.1, 0.1)
        
        ico_char = "!"
        if atype.startswith("WOUND"): ico_char = "О"
        elif atype.startswith("BURN"): ico_char = "Отм"
        elif atype.startswith("FRACTURE"): ico_char = "К"
        elif atype.startswith("AMPUTATION"): ico_char = "А"
        
        c.setFont(font, 7)
        c.drawString(base_x + 2*mm, base_y + 2*mm, ico_char)
        
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    
    dr_text(bm_x + 2*mm, bm_y + 10*mm, "подчеркнуть", size=6, align="center")
    dr_text(bm_x + 2*mm, bm_y + 7*mm, "мягкие ткани, кости,", size=6, align="center")
    dr_text(bm_x + 2*mm, bm_y + 4*mm, "сосуды, полостные", size=6, align="center")
    dr_text(bm_x + 2*mm, bm_y + 1*mm, "раны, ожоги", size=6, align="center")

    # ------------------
    # EVACUATION BLOCK
    # ------------------
    ev_x = mt_cols[0] - 2*mm
    ev_y = mt_rows[-1] - 30*mm
    
    dr_text(ev_x, ev_y + 14*mm, "Жгут наложен: ____ час. ____ мин.")
    dr_text(ev_x, ev_y + 9*mm, "Санитарная обработка (подчеркнуть)")
    dr_text(ev_x, ev_y + 5*mm, "полная, частичная, не проводилась")
    dr_text(ev_x, ev_y + 1*mm, "Эвакуировать (нужное обвести)")
    
    dr_line(ev_x, ev_y, m_x + m_w, ev_y)
    dr_line(ev_x, ev_y - 15*mm, m_x + m_w, ev_y - 15*mm)
    dr_line(ev_x, ev_y, ev_x, ev_y - 15*mm)
    dr_line(m_x + m_w, ev_y, m_x + m_w, ev_y - 15*mm)
    
    # Internal div (Lying/Sitting Icons)
    dr_line(ev_x + 20*mm, ev_y, ev_x + 20*mm, ev_y - 15*mm)
    
    # Lying Man on Stretcher
    def dr_lying(cx, cy):
        # Stretcher
        c.line(cx-7*mm, cy-1*mm, cx+7*mm, cy-1*mm)
        c.line(cx-5*mm, cy-1*mm, cx-5*mm, cy-3*mm)
        c.line(cx+5*mm, cy-1*mm, cx+5*mm, cy-3*mm)
        # Person
        c.circle(cx-4*mm, cy+1*mm, 1.5*mm) # head
        c.line(cx-2*mm, cy+0.5*mm, cx+3*mm, cy+0.5*mm) # body
        c.line(cx-1*mm, cy-0.5*mm, cx+2*mm, cy-0.5*mm) # arm
        c.line(cx+3*mm, cy+0.5*mm, cx+6*mm, cy+0.5*mm) # legs
        c.circle(cx+2*mm, cy+5*mm, 4*mm, fill=0, stroke=1) # plus sign circle target
        c.line(cx+1*mm, cy+5*mm, cx+3*mm, cy+5*mm)
        c.line(cx+2*mm, cy+4*mm, cx+2*mm, cy+6*mm)
        
    dr_lying(ev_x + 10*mm, ev_y - 6*mm)
    dr_text(ev_x + 10*mm, ev_y - 14*mm, "лежа", size=6, align="center")
    
    dr_line(ev_x + 35*mm, ev_y, ev_x + 35*mm, ev_y - 15*mm)
    
    # Sitting Man on Chair
    def dr_sitting(cx, cy):
        # Chair
        c.line(cx-2*mm, cy-3*mm, cx-2*mm, cy+2*mm) # back
        c.line(cx-2*mm, cy-1*mm, cx+2*mm, cy-1*mm) # seat
        c.line(cx+2*mm, cy-1*mm, cx+2*mm, cy-3*mm) # front leg
        # Person
        c.circle(cx, cy+4*mm, 1.5*mm) # head
        c.line(cx, cy+2.5*mm, cx, cy) # body
        c.line(cx, cy+1*mm, cx+1.5*mm, cy-0.5*mm) # arm
        c.line(cx, cy, cx+3*mm, cy) # thigh
        c.line(cx+3*mm, cy, cx+3*mm, cy-2.5*mm) # calf
        c.circle(cx+4*mm, cy+5*mm, 4*mm, fill=0, stroke=1) # plus sign circle target
        c.line(cx+3*mm, cy+5*mm, cx+5*mm, cy+5*mm)
        c.line(cx+4*mm, cy+4*mm, cx+4*mm, cy+6*mm)
        
    # "Circle" Lying or Sitting based on evac_method
    is_lying = "леж" in evac_method_str
    is_sitting = "сид" in evac_method_str
    if is_lying:
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.ellipse(ev_x + 5*mm, ev_y - 15*mm, ev_x + 15*mm, ev_y - 1*mm)
        c.setStrokeColorRGB(0, 0, 0)
    elif is_sitting:
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.ellipse(ev_x + 22*mm, ev_y - 15*mm, ev_x + 32*mm, ev_y - 1*mm)
        c.setStrokeColorRGB(0, 0, 0)
    
    dr_text(ev_x + 35*mm + (m_w - (ev_x - m_x) - 35*mm)/2, ev_y - 3*mm, "куда эвакуирован", size=7, align="center")
    dr_line(ev_x + 35*mm, ev_y - 4*mm, m_x + m_w, ev_y - 4*mm)
    
    # Destination crosses (Main Card)
    dt_w = (m_w - (ev_x - m_x) - 35*mm) / 3
    dt_x = ev_x + 35*mm
    for i in range(3):
        # House shape for 3rd option
        if i == 2:
            c.rect(dt_x + dt_w/2 + dt_w*i - 3*mm, ev_y - 10*mm, 6*mm, 6*mm)
            c.line(dt_x + dt_w/2 + dt_w*i - 4*mm, ev_y - 4*mm, dt_x + dt_w/2 + dt_w*i, ev_y - 1*mm)
            c.line(dt_x + dt_w/2 + dt_w*i, ev_y - 1*mm, dt_x + dt_w/2 + dt_w*i + 4*mm, ev_y - 4*mm)
            dr_text(dt_x + dt_w/2 + dt_w*i, ev_y - 9.5*mm, "+", align="center", size=7)
        else:
            c.circle(dt_x + dt_w/2 + dt_w*i, ev_y - 7*mm, 3*mm)
            dr_text(dt_x + dt_w/2 + dt_w*i, ev_y - 9*mm, "+", align="center")
        
    if "госп" in evac_dest.lower() or "вмед" in evac_dest.lower() or "омедб" in evac_dest.lower():
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        target_x = dt_x + dt_w/2 + dt_w*2
        c.ellipse(target_x - 4*mm, ev_y - 11*mm, target_x + 4*mm, ev_y + 1*mm)
        c.setStrokeColorRGB(0, 0, 0)
    
    c.setFont(font, 9)
    # Order of evac
    ev_y -= 25*mm
    
    priority = str(main.get("evacuation_priority") or "").strip()
    p1 = "I"
    p2 = "II"
    p3 = "III"
    dr_text(ev_x, ev_y, f"Очередность эвакуации:  {p1}    {p2}    {p3}")
    if priority == "1" or priority == "I" or priority == "Первая":
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.circle(ev_x + 38*mm, ev_y + 1*mm, 2.5*mm)
        c.setStrokeColorRGB(0, 0, 0)
    elif priority == "2" or priority == "II" or priority == "Вторая":
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.circle(ev_x + 44*mm, ev_y + 1*mm, 2.5*mm)
        c.setStrokeColorRGB(0, 0, 0)
    elif priority == "3" or priority == "III" or priority == "Третья":
        c.setStrokeColorRGB(0.8, 0.1, 0.1)
        c.circle(ev_x + 51*mm, ev_y + 1*mm, 2.5*mm)
        c.setStrokeColorRGB(0, 0, 0)
    
    # Icons row
    ev_y -= 15*mm
    dr_line(ev_x, ev_y, m_x + m_w, ev_y)
    dr_line(ev_x, ev_y - 15*mm, m_x + m_w, ev_y - 15*mm)
    dr_line(ev_x, ev_y, ev_x, ev_y - 15*mm)
    dr_line(m_x + m_w, ev_y, m_x + m_w, ev_y - 15*mm)
    
    seg_w = (m_x + m_w - ev_x) / 4
    for i in range(1, 4):
        dr_line(ev_x + i*seg_w, ev_y, ev_x + i*seg_w, ev_y - 15*mm)
        
    def dr_car(cx, cy):
        c.roundRect(cx-7*mm, cy-3*mm, 14*mm, 6*mm, 1*mm)
        c.rect(cx-3*mm, cy+3*mm, 6*mm, 3*mm)
        c.circle(cx-4*mm, cy-3*mm, 1.5*mm)
        c.circle(cx+4*mm, cy-3*mm, 1.5*mm)
        
    def dr_heli(cx, cy):
        c.ellipse(cx-4*mm, cy-2*mm, cx+6*mm, cy+3*mm)
        c.line(cx+6*mm, cy+0.5*mm, cx+10*mm, cy+1.5*mm) # tail
        c.line(cx+10*mm, cy, cx+10*mm, cy+3*mm) # rotor tail
        c.line(cx+1*mm, cy+3*mm, cx+1*mm, cy+5*mm) # mast
        c.line(cx-5*mm, cy+5*mm, cx+7*mm, cy+5*mm) # main rotor
        c.line(cx-2*mm, cy-2*mm, cx-2*mm, cy-4*mm) # skid l
        c.line(cx+4*mm, cy-2*mm, cx+4*mm, cy-4*mm) # skid r
        c.line(cx-4*mm, cy-4*mm, cx+6*mm, cy-4*mm) # skid base
        c.circle(cx, cy, 1*mm, fill=1) # cross center
        c.line(cx-1*mm, cy, cx+1*mm, cy)
        c.line(cx, cy-1*mm, cx, cy+1*mm)

    def dr_train(cx, cy):
        c.rect(cx-8*mm, cy-3*mm, 6*mm, 6*mm)
        c.rect(cx-1*mm, cy-3*mm, 6*mm, 6*mm)
        c.rect(cx+6*mm, cy-3*mm, 6*mm, 6*mm)
        c.line(cx-2*mm, cy, cx-1*mm, cy)
        c.line(cx+5*mm, cy, cx+6*mm, cy)
        
    def dr_ship(cx, cy):
        c.line(cx-6*mm, cy-2*mm, cx+6*mm, cy-2*mm)
        c.line(cx-6*mm, cy-2*mm, cx-8*mm, cy+2*mm)
        c.line(cx+6*mm, cy-2*mm, cx+8*mm, cy+2*mm)
        c.line(cx-8*mm, cy+2*mm, cx+8*mm, cy+2*mm)
        c.rect(cx-3*mm, cy+2*mm, 6*mm, 3*mm)
        c.rect(cx-1*mm, cy+5*mm, 2*mm, 3*mm) # Smoke stack
        
    dr_car(ev_x + seg_w/2, ev_y - 7.5*mm)
    dr_heli(ev_x + seg_w + seg_w/2, ev_y - 7.5*mm)
    dr_train(ev_x + 2*seg_w + seg_w/2, ev_y - 7.5*mm)
    dr_ship(ev_x + 3*seg_w + seg_w/2, ev_y - 7.5*mm)
    
    # "Circle" vehicle
    c.setStrokeColorRGB(0.8, 0.1, 0.1)
    if "авто" in evac_method_str or "маши" in evac_method_str:
        c.ellipse(ev_x + 2*mm, ev_y - 12*mm, ev_x + seg_w - 2*mm, ev_y - 2*mm)
    elif "авиа" in evac_method_str or "верт" in evac_method_str or "само" in evac_method_str:
        c.ellipse(ev_x + seg_w + 2*mm, ev_y - 12*mm, ev_x + 2*seg_w - 2*mm, ev_y - 2*mm)
    elif "поезд" in evac_method_str or "жд" in evac_method_str:
        c.ellipse(ev_x + 2*seg_w + 2*mm, ev_y - 12*mm, ev_x + 3*seg_w - 2*mm, ev_y - 2*mm)
    elif "суд" in evac_method_str or "вод" in evac_method_str or "морс" in evac_method_str:
        c.ellipse(ev_x + 3*seg_w + 2*mm, ev_y - 12*mm, ev_x + 4*seg_w - 2*mm, ev_y - 2*mm)
        
    c.setStrokeColorRGB(0, 0, 0)
    
    # Bottom fields
    dr_text(m_x, margin_y + band_height + 1*mm, "Диагноз", size=9)
    dr_line(m_x + 13*mm, margin_y + band_height + 1*mm, ev_x - 5*mm, margin_y + band_height + 1*mm)
    
    dr_text(ev_x, margin_y + band_height + 1*mm, "врач:", size=9)
    doctor = _s(main, bottom, card, "doctor_signature", _s(main, bottom, card, "signed_by"))
    dr_text(ev_x + 10*mm, margin_y + band_height + 2*mm, doctor)
    dr_line(ev_x + 9*mm, margin_y + band_height + 1*mm, m_x + m_w, margin_y + band_height + 1*mm)
    dr_text(ev_x + 9*mm + (m_w - (ev_x - m_x) - 9*mm)/2, margin_y + band_height - 3*mm, "(подпись разборчиво)", size=6, align="center")
    
    c.save()
