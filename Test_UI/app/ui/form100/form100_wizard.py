"""Form100Wizard — полноэкранный QDialog мастера заполнения Формы 100.

Структура:
  Левая колонка (~190 px) — индикатор шагов с нумерованными бейджами
  Центр (QStackedWidget)  — 4 шага
  Нижняя панель           — навигация (← Назад | Далее → | Сохранить | Отмена)
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..widgets.toast import show_toast
from .wizard_steps.step_identification import StepIdentification
from .wizard_steps.step_bodymap import StepBodymap
from .wizard_steps.step_medical import StepMedical
from .wizard_steps.step_evacuation import StepEvacuation


_STEP_NAMES: tuple[str, ...] = (
    "Идентификация",
    "Поражения",
    "Мед. помощь",
    "Эвакуация / Итог",
)

# Цвета боковой панели
_PANEL_BG    = "#1E2D3D"
_DONE_BG     = "#27AE60"
_DONE_TEXT   = "#FFFFFF"
_ACT_BG      = "#2E86C1"
_ACT_TEXT    = "#FFFFFF"
_PEND_BG     = "#2C3E50"
_PEND_BADGE  = "#34495E"
_PEND_TEXT   = "#7F8C8D"
_CONNECTOR   = "#2C4A66"
_NAV_BAR_BG  = "#F4F6F7"


class Form100Wizard(QDialog):
    """Мастер заполнения Формы 100 — 4 шага."""

    def __init__(
        self,
        svc,
        card_id: int,
        payload: dict[str, str],
        markers: list[dict],
        is_locked: bool,
        card_status: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Форма 100 — Карточка #{card_id}")
        self.setMinimumSize(1100, 750)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        self._svc = svc
        self._card_id = card_id
        self._is_locked = is_locked
        self._card_status = card_status
        self._current_step = 0

        # ── Корневой layout ───────────────────────────────────────────────
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Левая панель: индикатор шагов ─────────────────────────────────
        step_panel = QFrame()
        step_panel.setObjectName("wizardStepPanel")
        step_panel.setFixedWidth(190)
        step_panel.setStyleSheet(
            "#wizardStepPanel {"
            f"  background-color: {_PANEL_BG};"
            "  border-right: 1px solid #16202B;"
            "}"
        )
        sp_lay = QVBoxLayout(step_panel)
        sp_lay.setContentsMargins(16, 28, 16, 20)
        sp_lay.setSpacing(0)

        # Заголовок панели
        hdr_icon = QLabel("📋")
        hdr_icon.setStyleSheet(
            "background-color: transparent; color: #5DADE2;"
            " font-size: 20px; padding-bottom: 2px;"
        )
        hdr_icon.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sp_lay.addWidget(hdr_icon)

        hdr_title = QLabel("Форма 100")
        hdr_title.setStyleSheet(
            "background-color: transparent;"
            " color: #ECF0F1; font-size: 14px; font-weight: bold;"
            " letter-spacing: 0.5px;"
        )
        hdr_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sp_lay.addWidget(hdr_title)

        # Тонкий разделитель под заголовком
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {_CONNECTOR}; border: none;")
        sp_lay.addSpacing(14)
        sp_lay.addWidget(sep)
        sp_lay.addSpacing(18)

        # Шаги
        self._step_badges: list[QLabel] = []
        self._step_name_labels: list[QLabel] = []

        for i, name in enumerate(_STEP_NAMES):
            # Строка шага: бейдж + название
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)

            badge = QLabel(str(i + 1))
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background-color: {_PEND_BADGE}; color: {_PEND_TEXT};"
                " border-radius: 15px; font-weight: bold; font-size: 11px;"
            )
            self._step_badges.append(badge)
            row.addWidget(badge)

            name_lbl = QLabel(name)
            name_lbl.setWordWrap(True)
            name_lbl.setStyleSheet(
                f"background-color: transparent; color: {_PEND_TEXT};"
                " font-size: 12px;"
            )
            name_lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self._step_name_labels.append(name_lbl)
            row.addWidget(name_lbl, 1)

            row_widget = QWidget()
            row_widget.setLayout(row)
            row_widget.setStyleSheet("background-color: transparent;")
            sp_lay.addWidget(row_widget)

            # Вертикальный коннектор между шагами
            if i < len(_STEP_NAMES) - 1:
                conn_wrap = QWidget()
                conn_wrap.setStyleSheet("background-color: transparent;")
                conn_lay = QHBoxLayout(conn_wrap)
                conn_lay.setContentsMargins(14, 0, 0, 0)
                conn_lay.setSpacing(0)
                conn_line = QFrame()
                conn_line.setFixedWidth(2)
                conn_line.setMinimumHeight(18)
                conn_line.setMaximumHeight(18)
                conn_line.setStyleSheet(f"background-color: {_CONNECTOR}; border: none;")
                conn_lay.addWidget(conn_line)
                conn_lay.addStretch(1)
                sp_lay.addWidget(conn_wrap)

        sp_lay.addStretch(1)

        if is_locked:
            lock_lbl = QLabel("🔒 Только чтение")
            lock_lbl.setStyleSheet(
                "background-color: transparent; color: #F39C12;"
                " font-size: 11px; padding: 6px 0 0 0;"
            )
            lock_lbl.setWordWrap(True)
            sp_lay.addWidget(lock_lbl)

        outer.addWidget(step_panel)

        # ── Правая часть: стек шагов + навигационная панель ───────────────
        right_frame = QFrame()
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        outer.addWidget(right_frame, 1)

        self._stack = QStackedWidget()
        right_lay.addWidget(self._stack, 1)

        # ── Шаги ─────────────────────────────────────────────────────────
        self._step1 = StepIdentification()
        self._step2 = StepBodymap()
        self._step3 = StepMedical()
        self._step4 = StepEvacuation()
        self._steps: list[
            StepIdentification | StepBodymap | StepMedical | StepEvacuation
        ] = [self._step1, self._step2, self._step3, self._step4]

        for step in self._steps:
            self._stack.addWidget(step)
            step.set_values(payload, markers)
            step.set_locked(is_locked)

        self._step4.set_card_status(card_status)

        # ── Навигационная панель ──────────────────────────────────────────
        nav_bar = QFrame()
        nav_bar.setObjectName("wizardNavBar")
        nav_bar.setFixedHeight(56)
        nav_bar.setStyleSheet(
            "#wizardNavBar {"
            f"  background-color: {_NAV_BAR_BG};"
            "  border-top: 1px solid #DDDDDD;"
            "}"
        )
        nav_lay = QHBoxLayout(nav_bar)
        nav_lay.setContentsMargins(20, 8, 20, 8)
        nav_lay.setSpacing(10)

        self.btn_back = QPushButton("← Назад")
        self.btn_back.setObjectName("secondary")
        self.btn_back.setFixedWidth(100)
        self.btn_back.clicked.connect(self._go_back)

        self.btn_next = QPushButton("Далее →")
        self.btn_next.setFixedWidth(100)
        self.btn_next.clicked.connect(self._go_next)

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setFixedWidth(110)
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setEnabled(not is_locked)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setObjectName("ghost")
        self.btn_cancel.setFixedWidth(90)
        self.btn_cancel.clicked.connect(self.reject)

        nav_lay.addWidget(self.btn_back)
        nav_lay.addWidget(self.btn_next)
        nav_lay.addStretch(1)
        nav_lay.addWidget(self.btn_save)
        nav_lay.addWidget(self.btn_cancel)

        right_lay.addWidget(nav_bar)

        # Подключить кнопку «Подписать» из шага 4
        self._step4.btn_sign.clicked.connect(self._sign)

        # Инициализация
        self._goto_step(0)

    # ── Навигация ────────────────────────────────────────────────────────────

    def _goto_step(self, idx: int) -> None:
        self._current_step = max(0, min(idx, len(self._steps) - 1))
        if self._current_step == 3:
            payload, markers = self._collect_all()
            self._step4.update_review(payload, markers)
        self._stack.setCurrentIndex(self._current_step)
        self._update_nav()
        self._update_step_indicator()

    def _go_back(self) -> None:
        self._goto_step(self._current_step - 1)

    def _go_next(self) -> None:
        self._goto_step(self._current_step + 1)

    def _update_nav(self) -> None:
        idx = self._current_step
        n = len(self._steps)
        self.btn_back.setEnabled(idx > 0)
        self.btn_next.setVisible(idx < n - 1)

    def _update_step_indicator(self) -> None:
        for i, (badge, name_lbl) in enumerate(
            zip(self._step_badges, self._step_name_labels)
        ):
            if i < self._current_step:
                # Выполнен
                badge.setText("✓")
                badge.setStyleSheet(
                    f"background-color: {_DONE_BG}; color: {_DONE_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 12px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_DONE_BG};"
                    " font-size: 12px;"
                )
            elif i == self._current_step:
                # Активен
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    f"background-color: {_ACT_BG}; color: {_ACT_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 12px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_ACT_TEXT};"
                    " font-size: 13px; font-weight: bold;"
                )
            else:
                # Ожидает
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    f"background-color: {_PEND_BADGE}; color: {_PEND_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 11px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_PEND_TEXT};"
                    " font-size: 12px;"
                )

    # ── Сбор данных со всех шагов ────────────────────────────────────────────

    def _collect_all(self) -> tuple[dict[str, str], list[dict]]:
        payload: dict[str, str] = {}
        markers: list[dict] = []
        for step in self._steps:
            p, m = step.collect()
            payload.update(p)
            if m:
                markers = m
        return payload, markers

    # ── Сохранение и подпись ─────────────────────────────────────────────────

    def _save(self) -> None:
        payload, markers = self._collect_all()
        try:
            self._svc.update_payload(self._card_id, payload)
            self._svc.update_bodymap(self._card_id, markers)
        except PermissionError as exc:
            show_toast(self.window(), str(exc), "error")
            return
        except Exception as exc:
            show_toast(self.window(), f"Ошибка сохранения: {exc}", "error")
            return
        self.accept()

    def _sign(self) -> None:
        payload, markers = self._collect_all()
        try:
            self._svc.update_payload(self._card_id, payload)
            self._svc.update_bodymap(self._card_id, markers)
        except PermissionError as exc:
            show_toast(self.window(), str(exc), "error")
            return
        except Exception as exc:
            show_toast(self.window(), f"Ошибка сохранения: {exc}", "error")
            return

        signer, ok = QInputDialog.getText(self, "Подпись", "Подписант (разборчиво):")
        if not ok or not signer.strip():
            return
        try:
            signed = self._svc.sign(self._card_id, signer.strip())
        except PermissionError as exc:
            show_toast(self.window(), str(exc), "error")
            return
        if signed:
            self.accept()
        else:
            show_toast(self.window(), "Не удалось подписать карточку.", "error")
