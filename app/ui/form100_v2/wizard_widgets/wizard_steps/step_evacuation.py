"""WizardStep4 — Эвакуация + Флаги + Итог/Обзор."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
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

    _ACCENT_KEYS = {"id", "injury", "lesion", "med", "map", "evac", "flags", "diag"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("form100ReviewPanel")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner.setObjectName("form100ReviewPanelInner")
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
        card.setObjectName("form100ReviewNameCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(3)

        name_lbl = QLabel(name or "—")
        name_lbl.setObjectName("form100ReviewName")
        name_lbl.setWordWrap(True)
        lay.addWidget(name_lbl)

        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setObjectName("form100ReviewSub")
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

        tone = color_key if color_key in self._ACCENT_KEYS else "id"
        card = QFrame()
        card.setObjectName("form100ReviewCard")
        card.setProperty("tone", tone)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)

        hdr = QLabel(f"{icon}  {title.upper()}")
        hdr.setObjectName("form100ReviewHeader")
        hdr.setProperty("tone", tone)
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setObjectName("form100ReviewSeparator")
        sep.setProperty("tone", tone)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        lay.addWidget(sep)

        for label, value in filled:
            row = QWidget()
            row.setObjectName("form100ReviewRow")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(6)

            if label:
                label_lbl = QLabel(f"{label}:")
                label_lbl.setObjectName("form100ReviewRowLabel")
                label_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
                row_lay.addWidget(label_lbl, 0)

            value_lbl = QLabel(value)
            value_lbl.setObjectName("form100ReviewRowValue")
            value_lbl.setWordWrap(True)
            value_lbl.setTextFormat(Qt.TextFormat.PlainText)
            row_lay.addWidget(value_lbl, 1)
            lay.addWidget(row)

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

        tone = color_key if color_key in self._ACCENT_KEYS else "lesion"
        card = QFrame()
        card.setObjectName("form100ReviewCard")
        card.setProperty("tone", tone)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(6)

        hdr = QLabel(f"{icon}  {title.upper()}")
        hdr.setObjectName("form100ReviewHeader")
        hdr.setProperty("tone", tone)
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setObjectName("form100ReviewSeparator")
        sep.setProperty("tone", tone)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        lay.addWidget(sep)

        flow = QHBoxLayout()
        flow.setContentsMargins(0, 0, 0, 0)
        flow.setSpacing(6)
        for badge_text in badges:
            b = QLabel(badge_text)
            b.setObjectName("form100ReviewBadge")
            b.setProperty("tone", tone)
            flow.addWidget(b)
        flow.addStretch(1)
        lay.addLayout(flow)

        return card

    def rebuild(self, payload: dict[str, str], markers: list[dict[str, Any]]) -> None:
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
            placeholder.setObjectName("form100ReviewPlaceholder")
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

        self._mid_wrap = QWidget()
        self._mid_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._mid_wrap)
        self._mid_layout.setContentsMargins(0, 0, 0, 0)
        self._mid_layout.setSpacing(12)

        self.bottom_widget = Form100BottomWidget()
        self._bot_scroll = QScrollArea()
        self._bot_scroll.setWidgetResizable(True)
        self._bot_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._bot_scroll.setWidget(self.bottom_widget)
        self._bot_scroll.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self._mid_layout.addWidget(self._bot_scroll, 5)

        self._review_panel = _ReviewPanel()
        self._review_panel.setMinimumWidth(220)
        self._review_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self._mid_layout.addWidget(self._review_panel, 4)

        root.addWidget(self._mid_wrap, 1)

        self.btn_sign = QPushButton("Подписать карточку")
        self.btn_sign.setObjectName("secondaryButton")
        self.btn_sign.setVisible(False)
        root.addWidget(self.btn_sign)
        self._apply_responsive_layout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        if width < 1260:
            self._mid_layout.setDirection(QBoxLayout.Direction.TopToBottom)
            self._mid_layout.setSpacing(8)
            self._review_panel.setMinimumWidth(0)
            self._review_panel.setMinimumHeight(220)
            self._bot_scroll.setMinimumHeight(240)
        else:
            self._mid_layout.setDirection(QBoxLayout.Direction.LeftToRight)
            self._mid_layout.setSpacing(12)
            self._review_panel.setMinimumHeight(0)
            self._review_panel.setMinimumWidth(220)
            self._bot_scroll.setMinimumHeight(0)

    def set_values(self, payload: dict[str, str], markers: list[dict[str, Any]]) -> None:
        self.flags_widget.set_values(payload)
        self.bottom_widget.set_values(payload)
        self._review_panel.rebuild(payload, markers)

    def update_review(self, payload: dict[str, str], markers: list[dict[str, Any]]) -> None:
        self._review_panel.rebuild(payload, markers)

    def collect(self) -> tuple[dict[str, str], list[dict[str, Any]]]:
        out = self.flags_widget.collect()
        out.update(self.bottom_widget.collect())
        return out, []

    def set_locked(self, locked: bool) -> None:
        self.flags_widget.set_enabled(not locked)
        self.bottom_widget.set_locked(locked)

    def set_card_status(self, status: str) -> None:
        self.btn_sign.setVisible(status == "DRAFT")
