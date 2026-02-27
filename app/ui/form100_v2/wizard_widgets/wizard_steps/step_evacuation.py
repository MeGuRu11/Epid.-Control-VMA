"""WizardStep4 — Эвакуация + Флаги + Итог/Обзор."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.form100_v2.wizard_widgets.form100_bottom_widget import Form100BottomWidget
from app.ui.form100_v2.wizard_widgets.form100_flags_widget import Form100FlagsWidget


class _ReviewPanel(QScrollArea):
    """Прокручиваемая панель с карточками-секциями сводки Формы 100."""

    _ACCENT_COLORS = {
        "id":     "#2E86C1",
        "injury": "#E74C3C",
        "lesion": "#E67E22",
        "med":    "#27AE60",
        "map":    "#8E44AD",
        "evac":   "#16A085",
        "flags":  "#C0392B",
        "diag":   "#2C3E50",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("background: #F0F4F8;")

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent;")
        self._vlay = QVBoxLayout(self._inner)
        self._vlay.setContentsMargins(14, 14, 14, 14)
        self._vlay.setSpacing(10)
        self.setWidget(self._inner)

    def _clear(self) -> None:
        while self._vlay.count():
            item = self._vlay.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.deleteLater()

    def _make_name_header(self, name: str, sub: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background: #1A2C42; border-radius: 8px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(3)

        name_lbl = QLabel(name or "—")
        name_lbl.setStyleSheet(
            "background: transparent; color: #ECF0F1;"
            " font-size: 16px; font-weight: bold;"
        )
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setStyleSheet(
                "background: transparent; color: #85C1E9; font-size: 12px;"
            )
            sub_lbl.setWordWrap(True)
            lay.addWidget(sub_lbl)

        return card

    def _make_card(
        self,
        icon: str,
        title: str,
        rows: list[tuple[str, str]],
        color_key: str,
    ) -> QFrame | None:
        filled = [(k, v) for k, v in rows if v]
        if not filled:
            return None

        color = self._ACCENT_COLORS.get(color_key, "#2E86C1")
        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background: white;"
            f"  border-left: 4px solid {color};"
            "  border-radius: 4px;"
            "}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        hdr = QLabel(f"{icon}  {title.upper()}")
        hdr.setStyleSheet(
            f"background: transparent; color: {color};"
            " font-size: 10px; font-weight: bold; letter-spacing: 0.6px;"
        )
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {color}22; border: none;")
        lay.addWidget(sep)

        for label, value in filled:
            row_lbl = QLabel(
                f'<span style="color:#8899AA;">{label}:</span>'
                f'<span style="color:#1A252F;"> {value}</span>'
            )
            row_lbl.setTextFormat(Qt.TextFormat.RichText)
            row_lbl.setWordWrap(True)
            row_lbl.setStyleSheet("background: transparent; font-size: 12px;")
            lay.addWidget(row_lbl)

        return card

    def _make_badge_card(
        self,
        icon: str,
        title: str,
        badges: list[str],
        color_key: str,
    ) -> QFrame | None:
        if not badges:
            return None

        color = self._ACCENT_COLORS.get(color_key, "#E67E22")
        card = QFrame()
        card.setStyleSheet(
            "QFrame {"
            "  background: white;"
            f"  border-left: 4px solid {color};"
            "  border-radius: 4px;"
            "}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(6)

        hdr = QLabel(f"{icon}  {title.upper()}")
        hdr.setStyleSheet(
            f"background: transparent; color: {color};"
            " font-size: 10px; font-weight: bold; letter-spacing: 0.6px;"
        )
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {color}22; border: none;")
        lay.addWidget(sep)

        flow = QHBoxLayout()
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setSpacing(6)
        for badge_text in badges:
            b = QLabel(badge_text)
            b.setStyleSheet(
                f"background: {color}1A; color: {color};"
                " border: 1px solid " + color + "66;"
                " border-radius: 3px; padding: 2px 8px; font-size: 11px;"
            )
            flow.addWidget(b)
        flow.addStretch(1)
        lay.addLayout(flow)

        return card

    def rebuild(self, payload: dict[str, str], markers: list[dict]) -> None:  # type: ignore[type-arg]
        self._clear()

        name = (
            payload.get("stub_full_name") or payload.get("main_full_name") or ""
        )
        rank = payload.get("stub_rank") or payload.get("main_rank") or ""
        unit = payload.get("stub_unit") or payload.get("main_unit") or ""
        sub_parts = [p for p in (rank, unit) if p]
        header = self._make_name_header(name, " | ".join(sub_parts))
        self._vlay.addWidget(header)

        id_tag = payload.get("stub_id_tag") or payload.get("main_id_tag") or ""
        card = self._make_card(
            "🪪", "Идентификация",
            [("Жетон / уд.", id_tag)],
            "id",
        )
        if card:
            self._vlay.addWidget(card)

        inj_time = payload.get("stub_injury_time") or payload.get("main_injury_time") or ""
        inj_date = payload.get("stub_injury_date") or payload.get("main_injury_date") or ""
        issued_time = payload.get("stub_issued_time") or ""
        issued_date = payload.get("stub_issued_date") or ""
        injury_str = (inj_time + " " + inj_date).strip()
        issued_str = (issued_time + " " + issued_date).strip()
        card = self._make_card(
            "🕐", "Время",
            [("Ранен / заболел", injury_str), ("Выдана карточка", issued_str)],
            "injury",
        )
        if card:
            self._vlay.addWidget(card)

        if markers:
            _type_names = {
                "WOUND_X":    "Раны",
                "BURN_HATCH":  "Ожоги",
                "AMPUTATION":  "Ампутации",
                "TOURNIQUET":  "Жгуты",
                "NOTE_PIN":    "Заметки",
            }
            counts: dict[str, int] = {}
            for m in markers:
                t = str(m.get("annotation_type") or "")
                counts[t] = counts.get(t, 0) + 1
            badges = [
                f"{_type_names.get(t, t)}: {n}" for t, n in counts.items()
            ]
            card = self._make_badge_card("📍", "Схема тела", badges, "map")
            if card:
                self._vlay.addWidget(card)

        _lesion_map = {
            "lesion_gunshot":    "Огнестрельное",
            "lesion_nuclear":    "Ядерное",
            "lesion_chemical":   "Химическое",
            "lesion_biological": "Бактериол.",
            "lesion_burn":       "Ожог",
            "lesion_frostbite":  "Отморожение",
            "lesion_other":      "Другие",
            "lesion_misc":       "Иное",
        }
        lesions = [v for k, v in _lesion_map.items() if str(payload.get(k) or "0") == "1"]
        card = self._make_badge_card("💥", "Вид поражения", lesions, "lesion")
        if card:
            self._vlay.addWidget(card)

        _mp_map = {
            "mp_antibiotic":        "Антибиотик",
            "mp_serum_pss":         "Сыворотка ПСС",
            "mp_serum_pgs":         "Сыворотка ПГС",
            "mp_analgesic":         "Обезболивающее",
            "mp_transfusion_blood": "Переливание",
            "mp_immobilization":    "Иммобилизация",
            "mp_bandage":           "Перевязка",
        }
        mp_badges = [v for k, v in _mp_map.items() if str(payload.get(k) or "0") == "1"]
        card = self._make_badge_card("🏥", "Мед. помощь", mp_badges, "med")
        if card:
            self._vlay.addWidget(card)

        mp_extra: list[tuple[str, str]] = []
        if payload.get("mp_toxoid"):
            mp_extra.append(("Анатоксин", str(payload["mp_toxoid"])))
        if payload.get("mp_antidote"):
            mp_extra.append(("Антидот", str(payload["mp_antidote"])))
        if mp_extra:
            card = self._make_card("💊", "Препараты", mp_extra, "med")
            if card:
                self._vlay.addWidget(card)

        _dest_names = {
            "lying": "Лёжа", "sitting": "Сидя", "stretcher": "Носилки",
        }
        _transport_names = {
            "car": "Авто", "ambu": "Сан.", "ship": "Корабль",
            "heli": "Вертолёт", "plane": "Самолёт",
        }
        evac_dest = _dest_names.get(payload.get("evacuation_dest") or "", "")
        evac_prio = payload.get("evacuation_priority") or ""
        transport = _transport_names.get(payload.get("transport_type") or "", "")
        card = self._make_card(
            "🚑", "Эвакуация",
            [
                ("Позиция",    evac_dest),
                ("Очерёдность", evac_prio),
                ("Транспорт",  transport),
            ],
            "evac",
        )
        if card:
            self._vlay.addWidget(card)

        _flag_map = {
            "flag_emergency":  "⚡ Неотложная",
            "flag_radiation":  "☢ Радиация",
            "flag_sanitation": "🧪 Санобработка",
        }
        flags = [v for k, v in _flag_map.items() if str(payload.get(k) or "0") == "1"]
        card = self._make_badge_card("⚠", "Флаги", flags, "flags")
        if card:
            self._vlay.addWidget(card)

        diag = payload.get("main_diagnosis") or payload.get("stub_diagnosis") or ""
        card = self._make_card(
            "📋", "Диагноз",
            [("", diag)],
            "diag",
        )
        if card:
            self._vlay.addWidget(card)

        if self._vlay.count() == 1:
            placeholder = QLabel("Данные не введены")
            placeholder.setStyleSheet(
                "color: #95A5A6; font-size: 13px; font-style: italic;"
            )
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._vlay.addWidget(placeholder)

        self._vlay.addStretch(1)


class StepEvacuation(QWidget):
    """Шаг 4 мастера: флаги + эвакуация/заключение + обзор + подпись."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.flags_widget = Form100FlagsWidget()
        root.addWidget(self.flags_widget)

        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(12)

        self.bottom_widget = Form100BottomWidget()
        bot_scroll = QScrollArea()
        bot_scroll.setWidgetResizable(True)
        bot_scroll.setFrameShape(QFrame.Shape.NoFrame)
        bot_scroll.setWidget(self.bottom_widget)
        bot_scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        mid.addWidget(bot_scroll, 5)

        self._review_panel = _ReviewPanel()
        self._review_panel.setMinimumWidth(280)
        mid.addWidget(self._review_panel, 4)

        root.addLayout(mid, 1)

        self.btn_sign = QPushButton("Подписать карточку")
        self.btn_sign.setObjectName("secondary")
        self.btn_sign.setVisible(False)
        root.addWidget(self.btn_sign)

    def set_values(self, payload: dict[str, str], markers: list[dict]) -> None:  # type: ignore[type-arg]
        self.flags_widget.set_values(payload)
        self.bottom_widget.set_values(payload)
        self._review_panel.rebuild(payload, markers)

    def update_review(self, payload: dict[str, str], markers: list[dict]) -> None:  # type: ignore[type-arg]
        self._review_panel.rebuild(payload, markers)

    def collect(self) -> tuple[dict[str, str], list[dict]]:  # type: ignore[type-arg]
        out = self.flags_widget.collect()
        out.update(self.bottom_widget.collect())
        return out, []

    def set_locked(self, locked: bool) -> None:
        self.flags_widget.set_enabled(not locked)
        self.bottom_widget.set_locked(locked)

    def set_card_status(self, status: str) -> None:
        self.btn_sign.setVisible(status == "DRAFT")
