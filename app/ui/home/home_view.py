from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import (
    QDateTime,
    QEasingCurve,
    QLocale,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QBoxLayout,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.exceptions import AppError
from app.application.services.dashboard_service import DashboardService
from app.ui.widgets.notifications import set_status


@dataclass(frozen=True, slots=True)
class SummaryCardSpec:
    key: str
    title: str
    badge: str
    detail: str


@dataclass(slots=True)
class SummaryCardWidgets:
    value_label: QLabel
    detail_label: QLabel


SUMMARY_CARD_SPECS = (
    SummaryCardSpec("patients", "Пациенты", "PT", "зарегистрировано в системе"),
    SummaryCardSpec("emr_cases", "Истории болезни (ЭМЗ)", "EM", "оформлено историй болезни"),
    SummaryCardSpec("lab_samples", "Лабораторные пробы", "LB", "лабораторных проб в базе"),
    SummaryCardSpec("sanitary_samples", "Санитарные пробы", "SN", "санитарных проб в базе"),
    SummaryCardSpec("new_patients", "Новые пациенты (30 дней)", "NP", "добавлено за последние 30 дней"),
    SummaryCardSpec("top_department", "Топ-отделение (30 дней)", "TD", "Нет данных"),
)


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

    def set_clock(
        self,
        time_text: str,
        seconds_text: str,
        date_prefix: str,
        date_month: str,
        date_suffix: str,
    ) -> None:
        self._time = time_text
        self._seconds = seconds_text
        self._date_prefix = date_prefix
        self._date_month = date_month
        self._date_suffix = date_suffix
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(360, 160)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(280, 160)

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
        self._meta_cards: list[QWidget] = []
        self._summary_widgets: dict[str, SummaryCardWidgets] = {}
        self._summary_cards: list[QWidget] = []
        self._summary_columns = 1
        self._build_ui()
        self._load_stats()

    def refresh_stats(self) -> None:
        self._load_stats()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        self._hero_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._hero_layout.setContentsMargins(0, 0, 0, 0)
        self._hero_layout.setSpacing(18)

        self._hero_card = self._build_hero_card()
        self._hero_layout.addWidget(self._hero_card, 1)

        self._utility_card = self._build_utility_card()
        self._hero_layout.addWidget(self._utility_card, 0)
        self._hero_layout.setStretch(0, 1)
        self._hero_layout.setStretch(1, 0)
        layout.addLayout(self._hero_layout)

        self._stats_box = QGroupBox("Сводные показатели")
        self._stats_grid = QGridLayout(self._stats_box)
        self._stats_grid.setHorizontalSpacing(12)
        self._stats_grid.setVerticalSpacing(12)
        for spec in SUMMARY_CARD_SPECS:
            self._add_summary_card(spec)
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
        self._apply_hero_layout()
        self._reflow_hero_meta_cards()
        self._reflow_summary_cards()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_hero_layout()
        self._reflow_hero_meta_cards()
        self._reflow_summary_cards()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        if not hasattr(self, "_hero_card") or not hasattr(self, "_utility_card"):
            return hint
        layout = self.layout()
        if not isinstance(layout, QVBoxLayout):
            return hint
        margins = layout.contentsMargins()
        utility_min = self._utility_card.minimumSizeHint().width()
        stat_min = max((card.minimumSizeHint().width() for card in self._summary_cards), default=0)
        min_width = max(utility_min, stat_min) + margins.left() + margins.right()
        return QSize(min_width, hint.height())

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._user_name_label.setText(session.login)
        self._role_badge.setText(self._format_role_label(str(session.role)))
        self.refresh_stats()

    def _build_hero_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("homeHeroCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title = QLabel("Главная")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Рабочая сводка текущей сессии")
        subtitle.setObjectName("homeHeroSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        user_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        user_row.setContentsMargins(0, 0, 0, 0)
        user_row.setSpacing(10)
        self._user_name_label = QLabel(self.session.login)
        self._user_name_label.setObjectName("homeUserName")
        self._role_badge = QLabel(self._format_role_label(str(self.session.role)))
        self._role_badge.setObjectName("homeRoleBadge")
        user_row.addWidget(self._user_name_label)
        user_row.addWidget(self._role_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        user_row.addStretch()
        layout.addLayout(user_row)

        meta_grid = QGridLayout()
        meta_grid.setContentsMargins(0, 0, 0, 0)
        meta_grid.setHorizontalSpacing(12)
        meta_grid.setVerticalSpacing(12)
        last_login_card, self.last_login_label = self._build_meta_card("Последний вход")
        last_refresh_card, self.last_refresh_label = self._build_meta_card("Последнее обновление")
        self._hero_meta_grid = meta_grid
        self._meta_cards = [last_login_card, last_refresh_card]
        layout.addLayout(meta_grid)

        status_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(10)
        status_caption = QLabel("Статус")
        status_caption.setObjectName("homeMetaCaption")
        self.status_chip = QLabel("")
        self.status_chip.setObjectName("homeStatusBadge")
        status_row.addWidget(status_caption)
        status_row.addWidget(self.status_chip, 0, Qt.AlignmentFlag.AlignVCenter)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        set_status(self.status_label, "", "info")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self._set_hero_status(ok=True)
        return card

    def _build_utility_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("homeUtilityCard")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        caption = QLabel("Локальное время")
        caption.setObjectName("homeMetaCaption")
        layout.addWidget(caption, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

        self.clock_card = ClockCard(card)
        self.clock_card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.clock_card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
        return card

    def _build_meta_card(self, caption: str) -> tuple[QWidget, QLabel]:
        card = QWidget()
        card.setObjectName("homeMetaCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        caption_label = QLabel(caption)
        caption_label.setObjectName("homeMetaCaption")
        value_label = QLabel("-")
        value_label.setObjectName("homeMetaValue")
        value_label.setWordWrap(True)
        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        return card, value_label

    def _format_role_label(self, role: str) -> str:
        role_map = {
            "admin": "Администратор",
            "operator": "Оператор",
        }
        return role_map.get(role, role)

    def _calculate_meta_columns(self, available_width: int) -> int:
        if not self._meta_cards:
            return 1
        card_min = max(card.minimumSizeHint().width() for card in self._meta_cards)
        spacing = max(0, self._hero_meta_grid.horizontalSpacing())
        margins = self._hero_meta_grid.contentsMargins()
        two_col_needed = card_min * 2 + spacing + margins.left() + margins.right()
        return 2 if available_width >= two_col_needed else 1

    def _reflow_hero_meta_cards(self) -> None:
        if not hasattr(self, "_hero_meta_grid"):
            return
        while self._hero_meta_grid.count():
            item = self._hero_meta_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._hero_card)
        if not self._meta_cards:
            return
        columns = self._calculate_meta_columns(self._hero_card.width())
        for idx, card in enumerate(self._meta_cards):
            row = idx // columns
            col = idx % columns
            self._hero_meta_grid.addWidget(card, row, col)
        self._hero_meta_grid.setColumnStretch(0, 1)
        self._hero_meta_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def _apply_hero_layout(self) -> None:
        if not hasattr(self, "_hero_layout"):
            return
        spacing = max(0, self._hero_layout.spacing())
        margins = self._hero_layout.contentsMargins()
        hero_width = self._hero_card.minimumSizeHint().width()
        utility_width = self._utility_card.minimumSizeHint().width()
        horizontal_needed = hero_width + utility_width + spacing + margins.left() + margins.right()
        direction = (
            QBoxLayout.Direction.LeftToRight
            if self.width() >= horizontal_needed
            else QBoxLayout.Direction.TopToBottom
        )
        self._hero_layout.setDirection(direction)
        if direction == QBoxLayout.Direction.LeftToRight:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        else:
            self._hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._utility_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._hero_card.updateGeometry()
        self._utility_card.updateGeometry()

    def _set_hero_status(self, ok: bool, message: str = "") -> None:
        if ok:
            self.status_chip.setText("Готово")
            self.status_chip.setProperty("tone", "success")
            set_status(self.status_label, "", "info")
            self.status_label.setVisible(False)
        else:
            self.status_chip.setText("Ошибка загрузки")
            self.status_chip.setProperty("tone", "error")
            set_status(self.status_label, message, "error")
            self.status_label.setVisible(True)
        style = self.status_chip.style()
        style.unpolish(self.status_chip)
        style.polish(self.status_chip)
        self.status_chip.update()

    def _add_summary_card(self, spec: SummaryCardSpec) -> None:
        card = QWidget()
        card.setObjectName("summaryCard")
        card.setProperty("toneKey", spec.key)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setMinimumWidth(220)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        header_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        badge = QLabel(spec.badge)
        badge.setObjectName("summaryBadge")
        badge.setProperty("toneKey", spec.key)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(spec.title)
        title_label.setObjectName("summaryTitle")
        title_label.setWordWrap(True)

        header_row.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        header_row.addWidget(title_label, 1)
        card_layout.addLayout(header_row)

        value_label = QLabel(self._format_summary_value(spec.key, 0))
        value_label.setObjectName("summaryValue")
        value_label.setWordWrap(True)

        detail_label = QLabel(spec.detail)
        detail_label.setObjectName("summaryDetail")
        detail_label.setWordWrap(True)

        card_layout.addWidget(value_label)
        card_layout.addWidget(detail_label)
        card_layout.addStretch(1)

        self._summary_widgets[spec.key] = SummaryCardWidgets(
            value_label=value_label,
            detail_label=detail_label,
        )
        self._summary_cards.append(card)

    def _calculate_summary_columns(self, available_width: int) -> int:
        if not self._summary_cards:
            return 1
        card_min = max(
            max(card.minimumSizeHint().width(), card.minimumWidth())
            for card in self._summary_cards
        )
        spacing = max(0, self._stats_grid.horizontalSpacing())
        margins = self._stats_grid.contentsMargins()
        max_columns = min(3, len(self._summary_cards))
        for columns in range(max_columns, 0, -1):
            needed_width = (
                card_min * columns
                + spacing * max(0, columns - 1)
                + margins.left()
                + margins.right()
            )
            if available_width >= needed_width:
                return columns
        return 1

    def _reflow_summary_cards(self) -> None:
        if not hasattr(self, "_stats_grid"):
            return
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.setParent(self._stats_box)
        if not self._summary_cards:
            return
        columns = self._calculate_summary_columns(self._stats_box.width())
        self._summary_columns = columns
        for idx, card in enumerate(self._summary_cards):
            row = idx // columns
            col = idx % columns
            self._stats_grid.addWidget(card, row, col)
        for col in range(3):
            self._stats_grid.setColumnStretch(col, 1 if col < columns else 0)

    def _format_summary_value(self, key: str, value: int | str | None) -> str:
        if key == "top_department":
            if isinstance(value, str) and value:
                return value
            return "Нет данных"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str) and value:
            return value
        return "-"

    def _format_summary_detail(self, key: str, *, count: int | None = None) -> str:
        detail_map = {
            "patients": "зарегистрировано в системе",
            "emr_cases": "оформлено историй болезни",
            "lab_samples": "лабораторных проб в базе",
            "sanitary_samples": "санитарных проб в базе",
            "new_patients": "добавлено за последние 30 дней",
        }
        if key == "top_department":
            if count is None:
                return "Нет данных"
            return f"{count} санитарных проб за 30 дней"
        return detail_map.get(key, "")

    def _set_summary_metric(
        self,
        key: str,
        value: int | str | None,
        *,
        count: int | None = None,
    ) -> None:
        summary_widgets = self._summary_widgets.get(key)
        if summary_widgets is None:
            return
        summary_widgets.value_label.setText(self._format_summary_value(key, value))
        summary_widgets.detail_label.setText(self._format_summary_detail(key, count=count))

    def _load_stats(self) -> None:
        try:
            counts = self.dashboard_service.get_counts()
            for key in ("patients", "emr_cases", "lab_samples", "sanitary_samples"):
                self._set_summary_metric(key, counts.get(key, 0))
            self._load_last_login()
            new_patients = self.dashboard_service.get_new_patients_count(30)
            self._set_summary_metric("new_patients", new_patients)
            top_dep = self.dashboard_service.get_top_department_by_samples(30)
            if top_dep:
                dep_name, count = top_dep
                self._set_summary_metric("top_department", dep_name, count=count)
            else:
                self._set_summary_metric("top_department", None)
            self.last_refresh_label.setText(QDateTime.currentDateTime().toString("dd.MM.yyyy HH:mm:ss"))
            self._set_hero_status(ok=True)
        except (LookupError, RuntimeError, ValueError, AppError, TypeError) as exc:
            self._set_hero_status(ok=False, message=f"Ошибка: {exc}")
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
        self.last_login_label.setText(text)

    def _animate_status(self) -> None:
        self._status_anim.stop()
        self._status_anim.start()
