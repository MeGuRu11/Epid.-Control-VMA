from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class LogoutConfirmDialog(QDialog):
    """Диалог подтверждения выхода из пользовательской сессии."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("logoutConfirmDialog")
        self.setWindowTitle("Выход из системы")
        self.setModal(True)
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 16)
        root.setSpacing(16)

        content = QHBoxLayout()
        content.setSpacing(14)

        icon = QLabel("?")
        icon.setObjectName("logoutDialogIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)
        content.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        title = QLabel("Завершить сеанс?")
        title.setObjectName("logoutDialogTitle")
        body = QLabel("Вы вернётесь на экран входа. Текущая сессия будет закрыта.")
        body.setObjectName("logoutDialogBody")
        body.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(body)
        content.addLayout(text_col, 1)
        root.addLayout(content)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)

        self.cancel_button = QPushButton("Остаться")
        self.cancel_button.setObjectName("logoutCancelButton")
        self.cancel_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.cancel_button)

        self.confirm_button = QPushButton("Выйти")
        self.confirm_button.setObjectName("logoutConfirmButton")
        self.confirm_button.clicked.connect(self.accept)
        actions.addWidget(self.confirm_button)

        root.addLayout(actions)


class ExitConfirmDialog(QDialog):
    """Диалог подтверждения полного закрытия приложения."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("exitConfirmDialog")
        self.setWindowTitle("Закрытие приложения")
        self.setModal(True)
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 16)
        root.setSpacing(16)

        content = QHBoxLayout()
        content.setSpacing(14)

        icon = QLabel("!")
        icon.setObjectName("exitDialogIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(52, 52)
        content.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        title = QLabel("Закрыть Epid Control?")
        title.setObjectName("exitDialogTitle")
        body = QLabel(
            "Приложение будет полностью закрыто.\n"
            "Убедитесь, что все данные сохранены."
        )
        body.setObjectName("exitDialogBody")
        body.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(body)
        content.addLayout(text_col, 1)
        root.addLayout(content)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("exitCancelButton")
        self.cancel_btn.setDefault(True)
        self.cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.cancel_btn)

        self.exit_btn = QPushButton("Закрыть")
        self.exit_btn.setObjectName("exitConfirmButton")
        self.exit_btn.clicked.connect(self.accept)
        actions.addWidget(self.exit_btn)

        root.addLayout(actions)


def confirm_logout(parent: QWidget | None = None) -> bool:
    """Показать подтверждение выхода и вернуть True при подтверждении."""
    dialog = LogoutConfirmDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted


def confirm_exit(parent: QWidget | None = None) -> bool:
    """Показать подтверждение закрытия и вернуть True при подтверждении."""
    dialog = ExitConfirmDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
