from __future__ import annotations

import sys

from pydantic import ValidationError
from PySide6.QtCore import QDateTime, QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import LoginRequest, SessionContext
from app.application.services.auth_service import AuthService
from app.config import settings
from app.ui.runtime_ui import resolve_ui_runtime
from app.ui.widgets.animated_background import MedicalBackground
from app.ui.widgets.notifications import clear_status, set_status

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60


class LoginDialog(QDialog):
    Accepted = QDialog.DialogCode.Accepted
    Rejected = QDialog.DialogCode.Rejected

    def __init__(self, auth_service: AuthService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self.session: SessionContext | None = None
        self.setObjectName("loginDialog")
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication is not initialized")
        assert isinstance(app, QApplication)
        self._ui_runtime = resolve_ui_runtime(self, app, settings)
        self._animated_bg: MedicalBackground | None = None
        self._centered_once = False
        self._failed_attempts: int = 0
        self._lockout_remaining: int = 0
        self._lockout_timer: QTimer | None = None
        self.setWindowTitle("Вход - Эпидемиологический контроль")
        self.setModal(True)
        self._build_ui()
        self._apply_initial_size()
        self._init_animated_background()
        self._update_background()
        self._animate_card()
        self._start_clock()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Эпидемиологический контроль")
        title.setObjectName("loginAppTitle")
        title_font = QFont("Georgia", 30, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        time_panel = QFrame()
        time_panel.setObjectName("loginTimePanel")
        time_panel_layout = QVBoxLayout(time_panel)
        time_panel_layout.setContentsMargins(18, 12, 18, 12)
        time_panel_layout.setSpacing(4)

        time_label = QLabel("Текущие дата и время")
        time_label.setObjectName("loginTimeCaption")
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("loginTimeValue")
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_panel_layout.addWidget(time_label)
        time_panel_layout.addWidget(self.datetime_label)

        time_row = QHBoxLayout()
        time_row.addStretch()
        time_row.addWidget(time_panel)
        time_row.addStretch()

        layout.addWidget(title)
        layout.addLayout(time_row)
        medical_line = QLabel()
        medical_line.setObjectName("loginMedicalLine")
        medical_line.setFixedHeight(3)
        layout.addWidget(medical_line)

        self._card = QFrame()
        self._card.setObjectName("loginCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        card_title = QLabel("Вход в систему")
        card_title.setObjectName("loginCardTitle")
        card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        demo_hint = QLabel("Для теста: admin / admin1234")
        demo_hint.setObjectName("muted")
        demo_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("Введите логин")
        self.login_edit.setClearButtonEnabled(True)
        self.login_edit.textChanged.connect(self._on_login_text_changed)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.returnPressed.connect(self._on_login)
        form.addRow("Логин", self.login_edit)
        form.addRow("Пароль", self.password_edit)

        self.error_label = QLabel("")
        self.error_label.setObjectName("statusLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        self._lock_label = QLabel()
        self._lock_label.setObjectName("statusLabel")
        self._lock_label.setProperty("statusLevel", "error")
        self._lock_label.setWordWrap(True)
        self._lock_label.setVisible(False)

        self._login_btn = QPushButton("Войти")
        self._login_btn.setDefault(True)
        self._login_btn.clicked.connect(self._on_login)

        demo_btn = QPushButton("Подставить demo")
        demo_btn.setObjectName("secondaryButton")
        demo_btn.clicked.connect(self._fill_demo)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self._login_btn)
        btn_row.addWidget(demo_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)

        card_layout.addWidget(card_title)
        card_layout.addWidget(demo_hint)
        card_layout.addLayout(form)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self._lock_label)
        card_layout.addLayout(btn_row)

        self._card.setMaximumWidth(520)
        self._card_container = QWidget()
        container_layout = QVBoxLayout(self._card_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self._card)
        card_row = QHBoxLayout()
        card_row.addStretch()
        card_row.addWidget(self._card_container)
        card_row.addStretch()

        layout.addLayout(card_row)
        layout.addStretch()

        self.login_edit.setFocus()
        self._apply_glass_effect(self._card)

    def _fill_demo(self) -> None:
        self.login_edit.setText("admin")
        self.password_edit.setText("admin1234")

    def _on_login_text_changed(self) -> None:
        # Attempts are tracked per dialog session; editing login must not reset lockout counters.
        return

    def _start_lockout(self) -> None:
        self._lockout_remaining = _LOCKOUT_SECONDS
        self._login_btn.setEnabled(False)
        self._lock_label.setText(
            f"Слишком много неудачных попыток. Подождите {self._lockout_remaining} с."
        )
        self._lock_label.setVisible(True)
        timer = QTimer(self)
        timer.setInterval(1000)
        timer.timeout.connect(self._tick_lockout)
        self._lockout_timer = timer
        timer.start()

    def _tick_lockout(self) -> None:
        self._lockout_remaining -= 1
        if self._lockout_remaining <= 0:
            if self._lockout_timer is not None:
                self._lockout_timer.stop()
                self._lockout_timer = None
            self._failed_attempts = 0
            self._login_btn.setEnabled(True)
            self._lock_label.setVisible(False)
        else:
            self._lock_label.setText(
                f"Слишком много неудачных попыток. Подождите {self._lockout_remaining} с."
            )

    def _apply_initial_size(self) -> None:
        app = QApplication.instance()
        if app is None:
            self.resize(1080, 720)
            self.setMinimumSize(860, 560)
            return
        assert isinstance(app, QApplication)
        screen = self.screen() or app.primaryScreen()
        if screen is None:
            self.resize(1080, 720)
            self.setMinimumSize(860, 560)
            return

        geometry = screen.availableGeometry()
        min_width = min(920, max(760, geometry.width() - 80))
        min_height = min(640, max(520, geometry.height() - 80))
        max_width = max(min_width, geometry.width() - 32)
        max_height = max(min_height, geometry.height() - 32)
        target_width = max(min_width, min(1280, int(geometry.width() * 0.78), max_width))
        target_height = max(min_height, min(860, int(geometry.height() * 0.82), max_height))

        self.setMinimumSize(min_width, min_height)
        self.resize(target_width, target_height)

    def _update_background(self) -> None:
        if self._animated_bg is not None:
            return
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return
        pixmap = QPixmap(size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, size.width(), size.height())
        gradient.setColorAt(0, QColor(247, 242, 236))
        gradient.setColorAt(1, QColor(239, 230, 218))
        painter.fillRect(self.rect(), gradient)
        pen = QPen(QColor(58, 58, 56, 14))
        pen.setWidth(1)
        painter.setPen(pen)
        step = 40
        radius = 1
        for x in range(0, size.width(), step):
            for y in range(0, size.height(), step):
                painter.drawEllipse(x, y, radius, radius)
        painter.end()
        palette = self.palette()
        palette.setBrush(QPalette.ColorRole.Window, pixmap)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def _apply_glass_effect(self, card: QFrame) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 60))
        card.setGraphicsEffect(shadow)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._animated_bg is not None:
            self._animated_bg.setGeometry(self.rect())
            self._animated_bg.lower()
            self._card_container.raise_()
        self._update_background()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._centered_once:
            return
        self._center_dialog_on_screen()
        self._centered_once = True

    def _init_animated_background(self) -> None:
        if not self._ui_runtime.enable_background:
            return
        self._animated_bg = MedicalBackground(self, intensity="showcase")
        self._animated_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._animated_bg.setGeometry(self.rect())
        self._animated_bg.lower()
        self._card_container.raise_()

    def _animate_card(self) -> None:
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade_anim.setDuration(240)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        QTimer.singleShot(50, self._fade_anim.start)

    def _start_clock(self) -> None:
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_datetime)
        self._clock_timer.start(1000)
        self._update_datetime()

    def _update_datetime(self) -> None:
        now = QDateTime.currentDateTime()
        self.datetime_label.setText(now.toString("dd.MM.yyyy HH:mm:ss"))

    def _center_dialog_on_screen(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        assert isinstance(app, QApplication)
        screen = self.screen() or app.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())

    def _on_login(self) -> None:
        if self._lockout_timer is not None:
            return
        clear_status(self.error_label)
        self.error_label.setVisible(False)
        login = self.login_edit.text().strip()
        password = self.password_edit.text()
        if not login or not password:
            set_status(self.error_label, "Введите логин и пароль.", "error")
            self.error_label.setVisible(True)
            return
        try:
            request = LoginRequest(login=login, password=password)
        except ValidationError as exc:
            msg = exc.errors()[0].get("msg", "Проверьте логин и пароль.")
            set_status(self.error_label, msg, "error")
            self.error_label.setVisible(True)
            self._failed_attempts += 1
            if self._failed_attempts >= _MAX_ATTEMPTS:
                self._start_lockout()
            return
        try:
            session_ctx = self.auth_service.login(request)
        except Exception as exc:  # noqa: BLE001
            set_status(self.error_label, str(exc), "error")
            self.error_label.setVisible(True)
            self._failed_attempts += 1
            if self._failed_attempts >= _MAX_ATTEMPTS:
                self._start_lockout()
            return

        self._failed_attempts = 0
        self.session = session_ctx
        self.accept()


if __name__ == "__main__":
    # Allow manual run for smoke testing the dialog
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dlg = LoginDialog(auth_service=AuthService())
    dlg.show()
    sys.exit(app.exec())
