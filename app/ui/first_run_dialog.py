from __future__ import annotations

from pathlib import Path
from typing import cast

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.setup_service import SetupService
from app.config import settings
from app.ui.runtime_ui import resolve_ui_runtime
from app.ui.widgets.animated_background import MedicalBackground
from app.ui.widgets.notifications import clear_status, set_status


class FirstRunDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        setup_service: SetupService | None = None,
    ) -> None:
        super().__init__(parent)
        self.setup_service = setup_service or SetupService()
        self.setObjectName("firstRunDialog")
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication is not initialized")
        assert isinstance(app, QApplication)
        self._ui_runtime = resolve_ui_runtime(self, app, settings)
        self._animated_bg: MedicalBackground | None = None
        self._centered_once = False
        self.setWindowTitle("Первый запуск")
        self.setModal(True)
        self._apply_window_icon()
        self._build_ui()
        self._apply_initial_size()
        self._init_animated_background()
        self._update_background()
        self._animate_card()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Первый запуск")
        title.setObjectName("firstRunTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Это окно появляется на новом устройстве, чтобы создать первого администратора.")
        subtitle.setObjectName("firstRunSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        medical_line = QLabel()
        medical_line.setObjectName("firstRunMedicalLine")
        medical_line.setFixedHeight(3)
        layout.addWidget(medical_line)

        self._card = QFrame()
        self._card.setObjectName("firstRunCard")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(10)

        card_accent = QLabel()
        card_accent.setObjectName("firstRunCardAccent")
        card_accent.setFixedHeight(4)
        card_layout.addWidget(card_accent)

        card_title = QLabel("Создание администратора")
        card_title.setObjectName("firstRunCardTitle")
        card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(card_title)

        card_hint = QLabel("Укажите данные первой учетной записи с правами администратора.")
        card_hint.setObjectName("firstRunCardHint")
        card_hint.setWordWrap(True)
        card_layout.addWidget(card_hint)

        form = QFormLayout()
        form.setContentsMargins(0, 2, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.login_edit = QLineEdit()
        self.login_edit.setObjectName("firstRunInput")
        self.login_edit.setMinimumHeight(45)
        self.login_edit.setPlaceholderText("Логин администратора")
        self.password_edit = QLineEdit()
        self.password_edit.setObjectName("firstRunInput")
        self.password_edit.setMinimumHeight(45)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Пароль")
        self.password_confirm = QLineEdit()
        self.password_confirm.setObjectName("firstRunInput")
        self.password_confirm.setMinimumHeight(45)
        self.password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_confirm.setPlaceholderText("Повторите пароль")

        login_label = QLabel("Логин администратора")
        login_label.setToolTip("Используется для входа в систему.")
        login_label.setObjectName("firstRunFormLabel")
        password_label = QLabel("Пароль (не менее 8 символов)")
        password_label.setToolTip("Рекомендуются буквы и цифры.")
        password_label.setObjectName("firstRunFormLabel")
        confirm_label = QLabel("Повтор пароля")
        confirm_label.setToolTip("Повторите пароль для проверки.")
        confirm_label.setObjectName("firstRunFormLabel")

        form.addRow(login_label, self.login_edit)
        form.addRow(password_label, self.password_edit)
        form.addRow(confirm_label, self.password_confirm)
        card_layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setObjectName("statusLabel")
        set_status(self.error_label, "", "info")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText("Создать")
            ok_btn.setObjectName("firstRunPrimaryButton")
            ok_btn.setMinimumWidth(150)
            ok_btn.setMinimumHeight(42)
            ok_btn.clicked.connect(self._on_create)
            ok_btn.setDefault(True)
        if cancel_btn:
            cancel_btn.setText("Отмена")
            cancel_btn.setObjectName("firstRunGhostButton")
            cancel_btn.setMinimumWidth(120)
            cancel_btn.setMinimumHeight(40)
            cancel_btn.clicked.connect(self.reject)
        buttons_layout = cast(QHBoxLayout | None, buttons.layout())
        if buttons_layout is not None:
            buttons_layout.setContentsMargins(0, 2, 0, 0)
            buttons_layout.setSpacing(10)

        card_meta = QLabel("После создания учетной записи вы получите полный доступ к настройке системы.")
        card_meta.setObjectName("firstRunCardMeta")
        card_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_meta.setWordWrap(True)
        card_layout.addWidget(card_meta)
        card_layout.addWidget(buttons)
        self._card.setMinimumWidth(500)
        self._card.setMaximumWidth(620)

        self._card_container = QWidget()
        container_layout = QVBoxLayout(self._card_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self._card)
        card_row = QVBoxLayout()
        card_row.addWidget(self._card_container, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(card_row)

        badge = QLabel("Создайте первого администратора для доступа к системе.")
        badge.setObjectName("firstRunInfoBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setWordWrap(True)
        layout.addWidget(badge)

        help_box = QLabel(
            "После создания администратора вы сможете войти в систему и настроить справочники."
        )
        help_box.setObjectName("helperText")
        help_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_box.setWordWrap(True)
        layout.addWidget(help_box)

        self._apply_glass_effect(self._card)
        self.login_edit.setFocus()

    def _apply_initial_size(self) -> None:
        app = QApplication.instance()
        if app is None:
            self.resize(1020, 700)
            self.setMinimumSize(840, 580)
            return
        assert isinstance(app, QApplication)
        screen = self.screen() or app.primaryScreen()
        if screen is None:
            self.resize(1020, 700)
            self.setMinimumSize(840, 580)
            return

        geometry = screen.availableGeometry()
        min_width = min(900, max(760, geometry.width() - 80))
        min_height = min(620, max(520, geometry.height() - 80))
        max_width = max(min_width, geometry.width() - 32)
        max_height = max(min_height, geometry.height() - 32)
        target_width = max(min_width, min(1240, int(geometry.width() * 0.74), max_width))
        target_height = max(min_height, min(840, int(geometry.height() * 0.80), max_height))

        self.setMinimumSize(min_width, min_height)
        self.resize(target_width, target_height)

    def _apply_window_icon(self) -> None:
        root = Path(__file__).resolve().parents[2]
        icon_path = root / "resources" / "icons" / "app.ico"
        if not icon_path.exists():
            icon_path = root / "resources" / "icons" / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

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

    def _on_create(self) -> None:
        clear_status(self.error_label)
        self.error_label.setVisible(False)
        login = self.login_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.password_confirm.text()

        if not login:
            set_status(self.error_label, "Введите логин администратора.", "error")
            self.error_label.setVisible(True)
            return
        if not password:
            set_status(self.error_label, "Введите пароль.", "error")
            self.error_label.setVisible(True)
            return
        if password != confirm:
            set_status(self.error_label, "Пароли не совпадают.", "error")
            self.error_label.setVisible(True)
            return

        try:
            self.setup_service.create_initial_user(login=login, password=password)
        except ValueError as exc:
            set_status(self.error_label, str(exc), "error")
            self.error_label.setVisible(True)
            return
        except (SQLAlchemyError, OSError, RuntimeError, TypeError):
            set_status(
                self.error_label,
                "Не удалось создать администратора. Попробуйте позже.",
                "error",
            )
            self.error_label.setVisible(True)
            return

        self.accept()


if __name__ == "__main__":
    app = QApplication([])
    dialog = FirstRunDialog()
    dialog.show()
    app.exec()
