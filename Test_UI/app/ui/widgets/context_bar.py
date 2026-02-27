from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ContextBar(QFrame):
    """Постоянно открытая контекстная панель.

    Левая часть: иконка + ФИО пациента + статус госпитализации + кнопки выбора.
    Правая часть: кнопки быстрого перехода по разделам.
    """

    pickPatientRequested = Signal()
    pickCaseRequested = Signal()
    openPageRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("contextBar")

        self._patient_name: str | None = None
        self._patient_id: int | None = None
        self._case_id: int | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 8)
        root.setSpacing(0)

        # ── Левый блок: информация о пациенте ─────────────────────────────
        left = QHBoxLayout()
        left.setSpacing(10)

        self._icon_lbl = QLabel("👤")
        self._icon_lbl.setStyleSheet(
            "font-size: 18px; background: transparent; border: none;"
        )
        left.addWidget(self._icon_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(0)

        self._name_lbl = QLabel("Пациент не выбран")
        self._name_lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #2F3135;"
            " background: transparent; border: none;"
        )
        self._name_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self._status_lbl = QLabel("Выберите пациента для работы")
        self._status_lbl.setStyleSheet(
            "font-size: 10px; color: #9A9490;"
            " background: transparent; border: none;"
        )

        info_col.addWidget(self._name_lbl)
        info_col.addWidget(self._status_lbl)
        left.addLayout(info_col, 1)

        # Кнопки выбора пациента / госпитализации
        self.pick_patient_btn = QPushButton("Выбрать пациента")
        self.pick_patient_btn.setObjectName("ghost")
        self.pick_patient_btn.setFixedHeight(28)
        self.pick_patient_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 11px; padding: 2px 10px;"
            "  border-radius: 8px;"
            "  border: 1px solid #C8BEB2;"
            "  background: transparent; color: #5D6D7E;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(239, 230, 218, 0.80);"
            "  border-color: #A8A098;"
            "}"
        )
        self.pick_patient_btn.clicked.connect(self._emit_pick_patient)
        left.addWidget(self.pick_patient_btn)

        self.pick_case_btn = QPushButton("Госпитализация")
        self.pick_case_btn.setObjectName("ghost")
        self.pick_case_btn.setFixedHeight(28)
        self.pick_case_btn.setStyleSheet(
            "QPushButton {"
            "  font-size: 11px; padding: 2px 10px;"
            "  border-radius: 8px;"
            "  border: 1px solid #C8BEB2;"
            "  background: transparent; color: #5D6D7E;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(239, 230, 218, 0.80);"
            "  border-color: #A8A098;"
            "}"
            "QPushButton:disabled {"
            "  color: #C0B8B0; border-color: #DEDBD6;"
            "}"
        )
        self.pick_case_btn.clicked.connect(self._emit_pick_case)
        left.addWidget(self.pick_case_btn)

        root.addLayout(left, 1)

        # ── Разделитель ───────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #DDD5C8; border: none;")
        sep.setContentsMargins(0, 4, 0, 4)
        root.addSpacing(12)
        root.addWidget(sep)
        root.addSpacing(12)

        # ── Правый блок: кнопки навигации ─────────────────────────────────
        nav = QHBoxLayout()
        nav.setSpacing(6)

        _NAV: tuple[tuple[str, str, str], ...] = (
            ("ЭМЗ",         "emr",       "#8E44AD"),
            ("Лаборатория", "lab",       "#E67E22"),
            ("Форма 100",   "form100",   "#C0392B"),
            ("Санитария",   "sanitary",  "#27AE60"),
            ("Аналитика",   "analytics", "#16A085"),
        )

        self._nav_buttons: dict[str, QPushButton] = {}
        for label, key, color in _NAV:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setStyleSheet(
                "QPushButton {"
                f"  font-size: 12px; font-weight: 600; padding: 2px 12px;"
                "  border-radius: 8px;"
                f"  border: 1px solid {color}55;"
                f"  color: {color};"
                "  background: transparent;"
                "}"
                "QPushButton:hover {"
                f"  background: {color}18;"
                f"  border-color: {color}AA;"
                "}"
                "QPushButton:pressed {"
                f"  background: {color}2E;"
                "}"
                "QPushButton:disabled {"
                "  color: #C0B8B0; border-color: #DEDAD4;"
                "  background: transparent;"
                "}"
            )
            btn.clicked.connect(lambda _checked=False, k=key: self._emit_page(k))
            nav.addWidget(btn)
            self._nav_buttons[key] = btn

        root.addLayout(nav)

    # ── Публичный API ─────────────────────────────────────────────────────────

    def set_context(
        self,
        patient_id: int | None,
        case_id: int | None,
        status_text: str,
        patient_name: str | None = None,
    ) -> None:
        self._patient_id = patient_id
        self._case_id = case_id
        self._patient_name = patient_name

        if patient_name:
            self._icon_lbl.setText("👤")
            self._name_lbl.setText(patient_name)
            self._name_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #1A3A2A;"
                " background: transparent; border: none;"
            )
            if case_id:
                sub = f"Госпитализация #{case_id}  •  Все данные доступны"
                self._status_lbl.setStyleSheet(
                    "font-size: 10px; color: #4A8A6A;"
                    " background: transparent; border: none;"
                )
            else:
                sub = "Госпитализация не выбрана"
                self._status_lbl.setStyleSheet(
                    "font-size: 10px; color: #9A7A50;"
                    " background: transparent; border: none;"
                )
            self._status_lbl.setText(sub)
            self.pick_patient_btn.setText("Сменить пациента")
        elif patient_id:
            self._icon_lbl.setText("👤")
            self._name_lbl.setText(f"Пациент #{patient_id}")
            self._name_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #2F3135;"
                " background: transparent; border: none;"
            )
            self._status_lbl.setText(status_text)
            self._status_lbl.setStyleSheet(
                "font-size: 10px; color: #9A9490;"
                " background: transparent; border: none;"
            )
            self.pick_patient_btn.setText("Сменить пациента")
        else:
            self._icon_lbl.setText("ℹ")
            self._name_lbl.setText("Пациент не выбран")
            self._name_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #7A7A78;"
                " background: transparent; border: none;"
            )
            self._status_lbl.setText("Выберите пациента для работы с данными")
            self._status_lbl.setStyleSheet(
                "font-size: 10px; color: #9A9490;"
                " background: transparent; border: none;"
            )
            self.pick_patient_btn.setText("Выбрать пациента")

    def set_actions_enabled(self, has_patient: bool, has_case: bool) -> None:
        self.pick_case_btn.setEnabled(has_patient)
        self._nav_buttons["emr"].setEnabled(has_patient)
        self._nav_buttons["lab"].setEnabled(has_patient)
        self._nav_buttons["form100"].setEnabled(has_patient and has_case)
        self._nav_buttons["sanitary"].setEnabled(True)
        self._nav_buttons["analytics"].setEnabled(True)

    # ── Внутренние эмиттеры ───────────────────────────────────────────────────

    def _emit_page(self, key: str) -> None:
        self.openPageRequested.emit(key)

    def _emit_pick_patient(self) -> None:
        self.pickPatientRequested.emit()

    def _emit_pick_case(self) -> None:
        self.pickCaseRequested.emit()
