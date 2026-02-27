from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from .widgets.animated_background import MedicalBackground
from .widgets.toast import show_toast


class _AuthDialogBase(QDialog):
    def __init__(self):
        super().__init__()
        self.setModal(True)
        self._entry_animated = False

        stack = QStackedLayout(self)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self._stack = stack

        self.bg = MedicalBackground(self, intensity="showcase")
        self.bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        stack.addWidget(self.bg)

        content = QWidget(self)
        content.setObjectName("dialogOverlay")
        content.setStyleSheet("background: transparent;")
        stack.addWidget(content)
        stack.setCurrentWidget(content)
        self._content = content

        self._content_fx = QGraphicsOpacityEffect(content)
        self._content_fx.setOpacity(1.0)
        self._content.setGraphicsEffect(self._content_fx)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)

        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(0)
        center.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("authCard")
        self.card.setMaximumWidth(520)
        # Explicit opaque style so background animation never bleeds above auth card.
        self.card.setStyleSheet(
            """
            QFrame#authCard {
                background: rgba(255, 252, 247, 1.0);
                border: 1px solid #E3D9CF;
                border-radius: 20px;
            }
            """
        )
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        self.card_layout = card_layout

        center.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        center.addStretch(1)
        content_layout.addLayout(center, 1)

        self._entry_anim = QPropertyAnimation(self._content_fx, b"opacity", self)
        self._entry_anim.setDuration(220)
        self._entry_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._entry_anim.setStartValue(0.0)
        self._entry_anim.setEndValue(1.0)
        self._content_fx.setOpacity(1.0)

    def showEvent(self, event):
        super().showEvent(event)
        self._stack.setCurrentWidget(self._content)
        self.bg.lower()
        self._content.raise_()
        if not self._entry_animated:
            self._entry_animated = True
            self._content_fx.setOpacity(0.0)
            QTimer.singleShot(0, self._entry_anim.start)


class FirstRunDialog(_AuthDialogBase):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth
        self.setWindowTitle("Первый запуск: создание администратора")
        self.setMinimumSize(640, 420)

        title = QLabel("Первый запуск")
        title.setObjectName("title")
        subtitle = QLabel("База пустая. Создайте учетную запись администратора.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        self.card_layout.addWidget(title)
        self.card_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setContentsMargins(0, 6, 0, 4)

        self.login = QLineEdit("admin")
        self.passw = QLineEdit("admin1234")
        self.passw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Логин", self.login)
        form.addRow("Пароль", self.passw)
        self.card_layout.addLayout(form)

        buttons = QHBoxLayout()
        self.btn_create = QPushButton("Создать")
        self.btn_create.setDefault(True)
        self.cancel = QPushButton("Отмена")
        self.cancel.setObjectName("danger")
        buttons.addWidget(self.btn_create)
        buttons.addWidget(self.cancel)
        self.card_layout.addLayout(buttons)

        self.login.returnPressed.connect(self._create)
        self.passw.returnPressed.connect(self._create)
        self.btn_create.clicked.connect(self._create)
        self.cancel.clicked.connect(self.reject)

        QTimer.singleShot(0, self.login.setFocus)

    def _create(self):
        login = self.login.text().strip()
        pw = self.passw.text()
        if not login or len(pw) < 6:
            show_toast(self, "Введите логин и пароль длиной не менее 6 символов.", "warning")
            return
        try:
            self.auth.create_initial_admin(login, pw)
        except Exception as exc:
            show_toast(self, f"Ошибка создания администратора: {exc}", "error")
            return
        show_toast(self, "Администратор создан.", "success")
        self.accept()


class LoginDialog(_AuthDialogBase):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth
        self.session = None
        self.setWindowTitle("Вход — EpiSafe")
        self.setMinimumSize(700, 460)

        title = QLabel("EpiSafe")
        title.setObjectName("title")
        subtitle = QLabel("Вход по логину и паролю")
        subtitle.setObjectName("subtitle")
        subtitle_note = QLabel("Для теста: admin / admin1234")
        subtitle_note.setObjectName("muted")
        self.card_layout.addWidget(title)
        self.card_layout.addWidget(subtitle)
        self.card_layout.addWidget(subtitle_note)

        form = QFormLayout()
        form.setContentsMargins(0, 8, 0, 2)
        self.login = QLineEdit()
        self.login.setPlaceholderText("Введите логин")
        self.passw = QLineEdit()
        self.passw.setPlaceholderText("Введите пароль")
        self.passw.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Логин", self.login)
        form.addRow("Пароль", self.passw)
        self.card_layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_login = QPushButton("Войти")
        self.btn_login.setDefault(True)
        self.btn_hint = QPushButton("Подставить demo")
        self.btn_hint.setObjectName("secondary")
        btn_row.addWidget(self.btn_login)
        btn_row.addWidget(self.btn_hint)
        self.card_layout.addLayout(btn_row)

        self._lock_lbl = QLabel()
        self._lock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lock_lbl.setWordWrap(True)
        self._lock_lbl.setStyleSheet(
            "color: #922B21; font-size: 12px; font-weight: 600;"
            " background: #FDEDEC; border: 1px solid #F1948A;"
            " border-radius: 8px; padding: 6px 12px;"
        )
        self._lock_lbl.hide()
        self.card_layout.addWidget(self._lock_lbl)

        self._lock_timer = QTimer(self)
        self._lock_timer.setInterval(1000)
        self._lock_timer.timeout.connect(self._tick_lockout)

        self.btn_login.clicked.connect(self._login)
        self.btn_hint.clicked.connect(self._fill_demo)
        self.login.returnPressed.connect(self._login)
        self.passw.returnPressed.connect(self._login)
        self.login.textChanged.connect(self._on_login_changed)

        QTimer.singleShot(0, self.login.setFocus)

    def _fill_demo(self):
        self.login.setText("admin")
        self.passw.setText("admin1234")
        show_toast(self, "Данные для входа заполнены.", "info")
        self.passw.setFocus()

    def _on_login_changed(self) -> None:
        login = self.login.text().strip()
        if not login:
            return
        locked, _ = self.auth.is_locked(login)
        if not locked and self._lock_timer.isActive():
            self._lock_timer.stop()
            self._lock_lbl.hide()
            self.btn_login.setEnabled(True)

    def _tick_lockout(self) -> None:
        login = self.login.text().strip()
        locked, secs = self.auth.is_locked(login)
        if locked:
            mins, s = divmod(secs, 60)
            self._lock_lbl.setText(f"⛔  Слишком много попыток. Подождите {mins}:{s:02d}.")
        else:
            self._lock_timer.stop()
            self._lock_lbl.hide()
            self.btn_login.setEnabled(True)

    def _show_lockout(self, secs: int) -> None:
        mins, s = divmod(secs, 60)
        self._lock_lbl.setText(f"⛔  Слишком много попыток. Подождите {mins}:{s:02d}.")
        self._lock_lbl.show()
        self.btn_login.setEnabled(False)
        if not self._lock_timer.isActive():
            self._lock_timer.start()

    def _login(self):
        login = self.login.text().strip()
        locked, secs = self.auth.is_locked(login)
        if locked:
            self._show_lockout(secs)
            return
        ctx = self.auth.login(login, self.passw.text())
        if not ctx:
            show_toast(self, "Неверный логин/пароль или пользователь отключен.", "error")
            self.passw.selectAll()
            self.passw.setFocus()
            locked2, secs2 = self.auth.is_locked(login)
            if locked2:
                self._show_lockout(secs2)
            return
        self.session = ctx
        show_toast(self, f"Добро пожаловать, {ctx.login}.", "success")
        self.accept()
