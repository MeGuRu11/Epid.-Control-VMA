"""HomeView — главная страница EpiSafe.

Компоненты:
  - Шапка (gradient header) с именем системы, пользователем и датой
  - 6 карточек-счётчиков (пациенты, ЭМК, версии, лаб., сан., Ф100)
  - Строка быстрых действий
  - Административная секция (демо-данные / обновить)
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
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
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...infrastructure.db.models_sqlalchemy import (
    EmrCase,
    EmrCaseVersion,
    Form100Card,
    LabSample,
    Patient,
    SanitarySample,
)
from ..widgets.toast import show_toast


# ── Карточка-счётчик ──────────────────────────────────────────────────────────

class _StatCard(QFrame):
    """Карточка с иконкой, числом и подписью; акцентная полоса сверху."""

    def __init__(
        self,
        icon: str,
        label: str,
        color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame {"
            f"  border-top: 3px solid {color};"
            "  border-left: 1px solid #E3D9CF;"
            "  border-right: 1px solid #E3D9CF;"
            "  border-bottom: 1px solid #E3D9CF;"
            "  border-radius: 12px;"
            "  background: #FFFCF7;"
            "}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(108)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(2)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 22px; color: {color}; background: transparent;"
            " border: none;"
        )
        lay.addWidget(icon_lbl)

        self._value = QLabel("—")
        self._value.setStyleSheet(
            f"font-size: 32px; font-weight: 800; color: {color};"
            " background: transparent; border: none;"
        )
        lay.addWidget(self._value)

        name = QLabel(label.upper())
        name.setStyleSheet(
            "font-size: 10px; color: #9A9490; font-weight: 700;"
            " letter-spacing: 0.6px; background: transparent; border: none;"
        )
        lay.addWidget(name)

    def set_value(self, v: int) -> None:
        self._value.setText(str(v))


# ── Главная страница ──────────────────────────────────────────────────────────

_CARD_DEFS: tuple[tuple[str, str, str], ...] = (
    ("👤", "Пациенты",       "#2E86C1"),
    ("📋", "ЭМК",            "#8E44AD"),
    ("📄", "Версии ЭМЗ",     "#16A085"),
    ("🧪", "Лаб. пробы",     "#E67E22"),
    ("🔬", "Сан. пробы",     "#27AE60"),
    ("🏥", "Карточки Ф100",  "#C0392B"),
)

_ACTION_DEFS: tuple[tuple[str, str, str], ...] = (
    ("👤\nПациенты",    "#2E86C1", "patient"),
    ("📋\nЭМЗ",         "#8E44AD", "emr"),
    ("🏥\nФорма 100",   "#C0392B", "form100"),
    ("🧪\nЛаборатория", "#E67E22", "lab"),
    ("🔬\nСанитария",   "#27AE60", "sanitary"),
    ("📊\nАналитика",   "#16A085", "analytics"),
)


class HomeView(QWidget):
    pageRequested = Signal(str)

    def __init__(self, engine, session_ctx):
        super().__init__()
        self.engine = engine
        self.session = session_ctx

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(28, 24, 28, 28)
        vlay.setSpacing(22)
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # ── Gradient header ───────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient("
            "    x1:0, y1:0, x2:1, y2:0,"
            "    stop:0 #162840, stop:0.6 #1C3A56, stop:1 #1A3346"
            "  );"
            "  border-radius: 16px;"
            "  border: none;"
            "}"
        )
        header.setFixedHeight(96)
        hdr_lay = QHBoxLayout(header)
        hdr_lay.setContentsMargins(28, 0, 28, 0)
        hdr_lay.setSpacing(0)

        # App identity
        id_col = QVBoxLayout()
        id_col.setSpacing(3)
        app_name = QLabel("EpiSafe")
        app_name.setStyleSheet(
            "color: #FFFFFF; font-size: 24px; font-weight: 800;"
            " background: transparent; border: none; letter-spacing: 1.5px;"
        )
        app_sub = QLabel("Военно-медицинская информационная система")
        app_sub.setStyleSheet(
            "color: #7FB8D8; font-size: 12px; background: transparent; border: none;"
        )
        id_col.addStretch(1)
        id_col.addWidget(app_name)
        id_col.addWidget(app_sub)
        id_col.addStretch(1)
        hdr_lay.addLayout(id_col)
        hdr_lay.addStretch(1)

        # Separator line
        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet("background: #2A5070; border: none;")
        hdr_lay.addWidget(vline)
        hdr_lay.addSpacing(28)

        # User info
        usr_col = QVBoxLayout()
        usr_col.setSpacing(4)
        usr_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._user_lbl = QLabel()
        self._user_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._user_lbl.setStyleSheet(
            "color: #ECF0F1; font-size: 14px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        self._role_lbl = QLabel()
        self._role_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._role_lbl.setStyleSheet(
            "color: #85C1E9; font-size: 11px; background: transparent; border: none;"
        )
        today_lbl = QLabel(date.today().strftime("%d.%m.%Y"))
        today_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        today_lbl.setStyleSheet(
            "color: #5A8FAA; font-size: 11px; background: transparent; border: none;"
        )
        usr_col.addStretch(1)
        usr_col.addWidget(self._user_lbl)
        usr_col.addWidget(self._role_lbl)
        usr_col.addWidget(today_lbl)
        usr_col.addStretch(1)
        hdr_lay.addLayout(usr_col)

        vlay.addWidget(header)

        # ── Счётчики ──────────────────────────────────────────────────────
        sect1 = QLabel("Оперативная сводка")
        sect1.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #2F3135;"
        )
        vlay.addWidget(sect1)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._stat_cards: list[_StatCard] = []
        for icon, label, color in _CARD_DEFS:
            card = _StatCard(icon, label, color)
            self._stat_cards.append(card)
            cards_row.addWidget(card)
        vlay.addLayout(cards_row)

        # ── Быстрые действия ──────────────────────────────────────────────
        sect2 = QLabel("Быстрые действия")
        sect2.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #2F3135;"
        )
        vlay.addWidget(sect2)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(12)
        for text, color, page_key in _ACTION_DEFS:
            btn = QPushButton(text)
            btn.setStyleSheet(
                "QPushButton {"
                "  background: #FFFCF7;"
                "  border: 1px solid #E3D9CF;"
                f"  border-bottom: 3px solid {color};"
                "  border-radius: 10px;"
                "  padding: 14px 8px;"
                "  font-size: 12px; font-weight: 700;"
                "  color: #3A3A38;"
                "}"
                "QPushButton:hover {"
                f"  background: {color}18;"
                f"  border-color: {color}88;"
                f"  color: {color};"
                "}"
                "QPushButton:pressed {"
                f"  background: {color}2E;"
                "}"
            )
            btn.setFixedHeight(72)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _checked=False, k=page_key: self.pageRequested.emit(k))
            qa_row.addWidget(btn)
        vlay.addLayout(qa_row)

        # ── Секция администрирования ───────────────────────────────────────
        admin_card = QFrame()
        admin_card.setStyleSheet(
            "QFrame {"
            "  background: #FFFCF7;"
            "  border: 1px solid #E3D9CF;"
            "  border-radius: 12px;"
            "}"
        )
        admin_lay = QHBoxLayout(admin_card)
        admin_lay.setContentsMargins(20, 14, 20, 14)
        admin_lay.setSpacing(14)

        gear = QLabel("⚙")
        gear.setStyleSheet(
            "font-size: 22px; color: #9A9490; background: transparent; border: none;"
        )
        admin_lay.addWidget(gear)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        t1 = QLabel("Инструменты разработчика")
        t1.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #2F3135;"
            " background: transparent; border: none;"
        )
        t2 = QLabel("Генерация демо-данных для тестирования и отладки системы")
        t2.setStyleSheet(
            "font-size: 11px; color: #9A9490; background: transparent; border: none;"
        )
        info_col.addWidget(t1)
        info_col.addWidget(t2)
        admin_lay.addLayout(info_col)
        admin_lay.addStretch(1)

        self.btn_seed = QPushButton("Сгенерировать демо-данные")
        self.btn_seed.clicked.connect(self.seed)
        admin_lay.addWidget(self.btn_seed)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_refresh.setObjectName("secondary")
        self.btn_refresh.clicked.connect(self.refresh)
        admin_lay.addWidget(self.btn_refresh)

        vlay.addWidget(admin_card)
        vlay.addStretch(1)

        self.refresh()

    # ── Методы ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        with Session(self.engine) as db:
            patients = db.execute(select(func.count(Patient.id))).scalar_one()
            cases    = db.execute(select(func.count(EmrCase.id))).scalar_one()
            versions = db.execute(select(func.count(EmrCaseVersion.id))).scalar_one()
            labs     = db.execute(select(func.count(LabSample.id))).scalar_one()
            sanitary = db.execute(select(func.count(SanitarySample.id))).scalar_one()
            form100  = db.execute(select(func.count(Form100Card.id))).scalar_one()

        self._user_lbl.setText(f"👤  {self.session.login}")
        self._role_lbl.setText(f"Роль: {self.session.role}")

        for card, value in zip(
            self._stat_cards,
            (patients, cases, versions, labs, sanitary, form100),
        ):
            card.set_value(value)

    def seed(self) -> None:
        from ...application.services.demo_seed import seed_demo
        seed_demo(self.engine, self.session)
        show_toast(self.window(), "Демо-данные добавлены.", "success")
        self.refresh()
