from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, QEasingCurve, QLocale, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.services.dashboard_service import DashboardService
from app.ui.widgets.notifications import set_status


class ClockCard(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._time = "--:--"
        self._seconds = "--"
        self._date_prefix = "--, -- "
        self._date_month = "--"
        self._date_suffix = " ----"
        self._bg = QColor(255, 249, 242)
        self._border = QColor(227, 217, 207)
        self._text = QColor(58, 58, 56)
        self._accent = QColor(97, 201, 182)
        self.setMinimumHeight(160)
        self.setMinimumWidth(360)

    def set_clock(self, time_text: str, seconds_text: str, date_prefix: str, date_month: str, date_suffix: str) -> None:
        self._time = time_text
        self._seconds = seconds_text
        self._date_prefix = date_prefix
        self._date_month = date_month
        self._date_suffix = date_suffix
        self.update()

    def paintEvent(self, event) -> None:  # noqa: D401, N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(self._bg)
        painter.setPen(QPen(self._border, 1))
        painter.drawRoundedRect(rect, 12, 12)

        time_font = QFont(self.font())
        time_font.setPixelSize(72)
        sec_font = QFont(self.font())
        sec_font.setPixelSize(32)
        date_font = QFont(self.font())
        date_font.setPixelSize(14)

        time_metrics = QFontMetrics(time_font)
        sec_metrics = QFontMetrics(sec_font)
        date_metrics = QFontMetrics(date_font)

        gap = 8
        total_width = time_metrics.horizontalAdvance(self._time) + gap + sec_metrics.horizontalAdvance(
            self._seconds
        )
        start_x = rect.left() + max(0, (rect.width() - total_width) // 2)
        time_height = max(time_metrics.height(), sec_metrics.height())
        total_height = time_height + 10 + date_metrics.height()
        start_top = rect.top() + max(8, (rect.height() - total_height) // 2)
        base_y = start_top + time_metrics.ascent()

        painter.setFont(time_font)
        painter.setPen(self._text)
        painter.drawText(start_x, base_y, self._time)

        painter.setFont(sec_font)
        painter.setPen(self._accent)
        sec_x = start_x + time_metrics.horizontalAdvance(self._time) + gap
        painter.drawText(sec_x, base_y, self._seconds)

        painter.setFont(date_font)
        painter.setPen(self._text)
        date_y = start_top + time_height + 10 + date_metrics.ascent()
        date_width = (
            date_metrics.horizontalAdvance(self._date_prefix)
            + date_metrics.horizontalAdvance(self._date_month)
            + date_metrics.horizontalAdvance(self._date_suffix)
        )
        date_x = rect.left() + max(0, (rect.width() - date_width) // 2)
        painter.drawText(date_x, date_y, self._date_prefix)
        painter.setPen(self._accent)
        month_x = date_x + date_metrics.horizontalAdvance(self._date_prefix)
        painter.drawText(month_x, date_y, self._date_month)
        painter.setPen(self._text)
        suffix_x = month_x + date_metrics.horizontalAdvance(self._date_month)
        painter.drawText(suffix_x, date_y, self._date_suffix)


class HomeView(QWidget):
    pageRequested = Signal(str)  # noqa: N815

    def __init__(
        self,
        session: SessionContext,
        dashboard_service: DashboardService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.dashboard_service = dashboard_service
        self._stats_labels: dict[str, QLabel] = {}
        self._stat_cards: list[QWidget] = []
        self._build_ui()
        self._load_stats()

    def refresh_stats(self) -> None:
        self._load_stats()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        clock_row = QHBoxLayout()
        clock_row.addStretch()
        self.clock_card = ClockCard()
        clock_row.addWidget(self.clock_card)
        clock_row.addStretch()
        layout.addLayout(clock_row)

        header_row = QHBoxLayout()
        title = QLabel("Главная")
        title.setObjectName("pageTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        layout.addLayout(header_row)

        subtitle_row = QHBoxLayout()
        self._user_info_label = QLabel(f"Пользователь: {self.session.login} ({self.session.role})")
        self._user_info_label.setObjectName("homeUserInfo")
        subtitle_row.addWidget(self._user_info_label)
        subtitle_row.addStretch()
        self.status_label = QLabel("")
        set_status(self.status_label, "", "info")
        self.status_label.setVisible(False)
        subtitle_row.addWidget(self.status_label)
        layout.addLayout(subtitle_row)

        meta_row = QHBoxLayout()
        self.last_login_label = QLabel("Последний вход: -")
        self.last_login_label.setObjectName("chipLabel")
        self.last_refresh_label = QLabel("Последнее обновление: -")
        self.last_refresh_label.setObjectName("chipLabel")
        self.status_chip = QLabel("Статус: готово")
        self.status_chip.setObjectName("chipLabel")
        meta_row.addWidget(self.last_login_label)
        meta_row.addWidget(self.last_refresh_label)
        meta_row.addWidget(self.status_chip)
        meta_row.addStretch()
        layout.addLayout(meta_row)

        self._stats_box = QGroupBox("Сводные показатели")
        self._stats_grid = QGridLayout(self._stats_box)
        self._stats_grid.setHorizontalSpacing(12)
        self._stats_grid.setVerticalSpacing(12)
        self._add_stat("Пациенты", "patients")
        self._add_stat("Истории болезни (ЭМЗ)", "emr_cases")
        self._add_stat("Лабораторные пробы", "lab_samples")
        self._add_stat("Санитарные пробы", "sanitary_samples")
        self._add_stat("Новые пациенты (30 дней)", "new_patients")
        self._add_stat("Топ-отделение (30 дней)", "top_department")
        layout.addWidget(self._stats_box)

        layout.addStretch()

        self._status_effect = QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self._status_effect)
        self._status_anim = QPropertyAnimation(self._status_effect, b"opacity")
        self._status_anim.setDuration(600)
        self._status_anim.setStartValue(0.4)
        self._status_anim.setEndValue(1.0)
        self._status_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()
        self._reflow_stat_cards()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow_stat_cards()

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._user_info_label.setText(f"Пользователь: {session.login} ({session.role})")
        self.refresh_stats()

    def _add_stat(self, label: str, key: str) -> None:
        badge_map = {
            "patients": "PT",
            "emr_cases": "EM",
            "lab_samples": "LB",
            "sanitary_samples": "SN",
            "new_patients": "NP",
            "top_department": "TD",
        }
        badge_text = badge_map.get(key, "--")
        card = QWidget()
        card.setObjectName("statCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(10)
        badge = QLabel(badge_text)
        badge.setObjectName("statBadge")
        badge.setProperty("toneKey", key if key in badge_map else "default")
        badge.setFixedSize(40, 24)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(label)
        name_label.setObjectName("muted")
        value_label = QLabel("0")
        value_label.setObjectName("metricValue")
        value_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        info_layout.addWidget(value_label)
        card_layout.addWidget(badge)
        card_layout.addLayout(info_layout)
        self._stats_labels[key] = value_label
        self._stat_cards.append(card)

    def _reflow_stat_cards(self) -> None:
        if not hasattr(self, "_stats_grid"):
            return
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._stats_box)
        if not self._stat_cards:
            return
        card_min = max(card.minimumSizeHint().width() for card in self._stat_cards)
        spacing = max(0, self._stats_grid.horizontalSpacing())
        margins = self._stats_grid.contentsMargins()
        two_col_needed = card_min * 2 + spacing + margins.left() + margins.right()
        columns = 2 if self._stats_box.width() >= two_col_needed else 1
        for idx, card in enumerate(self._stat_cards):
            row = idx // columns
            col = idx % columns
            self._stats_grid.addWidget(card, row, col)
        self._stats_grid.setColumnStretch(0, 1)
        self._stats_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def _load_stats(self) -> None:
        try:
            counts = self.dashboard_service.get_counts()
            for key, value in counts.items():
                if key in self._stats_labels:
                    self._stats_labels[key].setText(str(value))
            self._load_last_login()
            new_patients = self.dashboard_service.get_new_patients_count(30)
            if "new_patients" in self._stats_labels:
                self._stats_labels["new_patients"].setText(str(new_patients))
            top_dep = self.dashboard_service.get_top_department_by_samples(30)
            if "top_department" in self._stats_labels:
                if top_dep:
                    dep_name, count = top_dep
                    self._stats_labels["top_department"].setText(f"{dep_name} · {count}")
                else:
                    self._stats_labels["top_department"].setText("-")
            self.last_refresh_label.setText(
                f"Последнее обновление: {QDateTime.currentDateTime().toString('dd.MM.yyyy HH:mm:ss')}"
            )
            set_status(self.status_label, "", "info")
            self.status_label.setVisible(False)
        except Exception as exc:  # noqa: BLE001
            set_status(self.status_label, f"Ошибка: {exc}", "error")
            self.status_label.setVisible(True)
            self._animate_status()

    def _update_clock(self) -> None:
        now = QDateTime.currentDateTime()
        locale = QLocale(QLocale.Language.Russian, QLocale.Country.Russia)
        day = locale.dayName(now.date().dayOfWeek(), QLocale.FormatType.ShortFormat)
        month = locale.monthName(now.date().month(), QLocale.FormatType.ShortFormat)
        self.clock_card.set_clock(
            now.toString("HH:mm"),
            now.toString("ss"),
            f"{day}, {now.toString('dd')} ",
            month,
            f" {now.toString('yyyy')}",
        )

    def _load_last_login(self) -> None:
        last_login = self.dashboard_service.get_last_login(self.session.user_id)
        last_login_dt = last_login if isinstance(last_login, datetime) else None
        text = last_login_dt.strftime("%d.%m.%Y %H:%M:%S") if last_login_dt else "-"
        self.last_login_label.setText(f"Последний вход: {text}")


    def _animate_status(self) -> None:
        self._status_anim.stop()
        self._status_anim.start()
