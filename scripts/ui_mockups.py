from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import _apply_light_theme  # noqa: E402


def _set_app_icon(app: QApplication) -> None:
    icon_path = ROOT_DIR / "resources" / "icons" / "app.ico"
    if not icon_path.exists():
        icon_path = ROOT_DIR / "resources" / "icons" / "app.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))


def _card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("mockCard")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)
    if title:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
    return frame, layout


def _input_row(label: str, placeholder: str = "") -> QWidget:
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(QLabel(label))
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    layout.addWidget(field)
    return row


def _password_row(label: str, placeholder: str = "") -> QWidget:
    row = QWidget()
    layout = QVBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(QLabel(label))
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    layout.addWidget(field)
    return row


def build_login_a() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет авторизации A — Медицинский кабинет")
    dlg.resize(780, 460)
    dlg.setObjectName("loginA")

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(18)

    header = QHBoxLayout()
    header.addWidget(QLabel("Эпидемиологический контроль"))
    header.addStretch()
    clock = QLabel("14:32  Ср")
    clock.setObjectName("clockBadge")
    header.addWidget(clock)
    root.addLayout(header)

    content = QHBoxLayout()
    content.addStretch()
    card, card_layout = _card("Вход в систему")
    card_layout.addWidget(_input_row("Логин", "Введите логин"))
    card_layout.addWidget(_password_row("Пароль", "Введите пароль"))
    btn = QPushButton("Войти")
    btn.setObjectName("primaryButton")
    card_layout.addWidget(btn)
    hint = QLabel("Подсказка: доступ выдает администратор.")
    hint.setStyleSheet("color: #7A7A78;")
    card_layout.addWidget(hint)
    content.addWidget(card)
    content.addStretch()
    root.addLayout(content)

    dlg.setStyleSheet(
        """
        QDialog#loginA {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #F7F2EC, stop:1 #EFE6DA);
        }
        QLabel#clockBadge {
            color: #61C9B6;
            font-weight: 600;
        }
        QFrame#mockCard {
            background-color: #FFF9F2;
            border: 1px solid #E3D9CF;
            border-radius: 12px;
        }
        """
    )
    return dlg


def build_login_b() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет авторизации B — Панель управления")
    dlg.resize(860, 480)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(16)

    title = QLabel("Эпидемиологический контроль")
    title.setObjectName("pageTitle")
    root.addWidget(title)

    content = QHBoxLayout()
    login_card, login_layout = _card("Вход")
    login_layout.addWidget(_input_row("Логин", "Логин"))
    login_layout.addWidget(_password_row("Пароль", "Пароль"))
    login_btn = QPushButton("Войти")
    login_btn.setObjectName("primaryButton")
    login_layout.addWidget(login_btn)
    content.addWidget(login_card, 2)

    help_card, help_layout = _card("Справка")
    help_layout.addWidget(QLabel("• Доступ выдает администратор"))
    help_layout.addWidget(QLabel("• Рекомендуемый пароль 8+ символов"))
    help_layout.addWidget(QLabel("• При проблемах обратитесь в ИТ-службу"))
    content.addWidget(help_card, 1)

    root.addLayout(content)
    return dlg


def build_login_c() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет авторизации C — Стеклянная карточка")
    dlg.resize(820, 470)
    dlg.setObjectName("loginC")

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.addStretch()

    card, card_layout = _card("Вход")
    card_layout.addWidget(_input_row("Логин", "Логин"))
    card_layout.addWidget(_password_row("Пароль", "Пароль"))
    login_btn = QPushButton("Войти")
    login_btn.setObjectName("primaryButton")
    card_layout.addWidget(login_btn)

    centered = QHBoxLayout()
    centered.addStretch()
    centered.addWidget(card)
    centered.addStretch()
    root.addLayout(centered)
    root.addStretch()

    dlg.setStyleSheet(
        """
        QDialog#loginC {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #F7F2EC, stop:1 #D8EEE9);
        }
        QFrame#mockCard {
            background-color: rgba(255, 249, 242, 0.85);
            border: 1px solid #E3D9CF;
            border-radius: 14px;
        }
        """
    )
    return dlg


def build_first_run_a() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет мастера админа A — Первый запуск")
    dlg.resize(760, 520)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(12)

    title = QLabel("Первый запуск")
    title.setObjectName("pageTitle")
    root.addWidget(title)
    root.addWidget(QLabel("Это окно появилось, потому что администратор ещё не создан."))

    form = QGridLayout()
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)
    form.addWidget(QLabel("Логин администратора"), 0, 0)
    form.addWidget(QLineEdit(), 0, 1)
    form.addWidget(QLabel("Пароль"), 1, 0)
    pw = QLineEdit()
    pw.setEchoMode(QLineEdit.EchoMode.Password)
    form.addWidget(pw, 1, 1)
    form.addWidget(QLabel("Повтор пароля"), 2, 0)
    pw2 = QLineEdit()
    pw2.setEchoMode(QLineEdit.EchoMode.Password)
    form.addWidget(pw2, 2, 1)
    root.addLayout(form)

    ack = QCheckBox("Я понимаю, что создаю администратора системы.")
    root.addWidget(ack)

    btns = QHBoxLayout()
    btns.addStretch()
    create_btn = QPushButton("Создать администратора")
    create_btn.setObjectName("primaryButton")
    btns.addWidget(create_btn)
    btns.addWidget(QPushButton("Отмена"))
    root.addLayout(btns)

    hint = QLabel("Что дальше: войдите в систему и настройте справочники.")
    hint.setStyleSheet("color: #7A7A78;")
    root.addWidget(hint)
    return dlg


def build_first_run_b() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет мастера админа B — Пошаговый")
    dlg.resize(740, 480)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(12)

    title = QLabel("Первый запуск — Шаг 2/3")
    title.setObjectName("pageTitle")
    root.addWidget(title)
    root.addWidget(QLabel("Создайте учетную запись администратора."))

    root.addWidget(_input_row("Логин", "admin"))
    root.addWidget(_password_row("Пароль", "минимум 8 символов"))
    root.addWidget(_password_row("Повтор пароля", "повторите пароль"))

    btns = QHBoxLayout()
    btns.addWidget(QPushButton("Назад"))
    btns.addStretch()
    next_btn = QPushButton("Далее")
    next_btn.setObjectName("primaryButton")
    btns.addWidget(next_btn)
    root.addLayout(btns)
    return dlg


def build_first_run_c() -> QDialog:
    dlg = QDialog()
    dlg.setWindowTitle("Макет мастера админа C — Справка справа")
    dlg.resize(860, 500)

    root = QHBoxLayout(dlg)
    root.setContentsMargins(24, 24, 24, 24)
    root.setSpacing(16)

    left, left_layout = _card("Первый запуск")
    left_layout.addWidget(_input_row("Логин", "admin"))
    left_layout.addWidget(_password_row("Пароль", "минимум 8 символов"))
    left_layout.addWidget(_password_row("Повтор", "повторите пароль"))
    btns = QHBoxLayout()
    btns.addWidget(QPushButton("Отмена"))
    create_btn = QPushButton("Создать")
    create_btn.setObjectName("primaryButton")
    btns.addWidget(create_btn)
    left_layout.addLayout(btns)
    root.addWidget(left, 2)

    right, right_layout = _card("Зачем это нужно?")
    right_layout.addWidget(QLabel("• Создание первого администратора"))
    right_layout.addWidget(QLabel("• Доступ к настройкам и справочникам"))
    right_layout.addWidget(QLabel("• Данные хранятся локально"))
    root.addWidget(right, 1)
    return dlg


def main() -> int:
    app = QApplication(sys.argv)
    _apply_light_theme(app)
    _set_app_icon(app)

    dialogs = [
        build_login_a(),
        build_login_b(),
        build_login_c(),
        build_first_run_a(),
        build_first_run_b(),
        build_first_run_c(),
    ]

    start_x = 80
    start_y = 60
    offset = 40
    for idx, dlg in enumerate(dialogs):
        dlg.move(start_x + offset * idx, start_y + offset * idx)
        dlg.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
