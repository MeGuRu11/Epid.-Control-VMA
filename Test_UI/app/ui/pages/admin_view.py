from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...application.dto.auth_dto import UserCreateIn
from ...application.services.auth_service import AuthService
from ...application.services.exchange_service import ExchangeService
from ...infrastructure.audit.audit_logger import AuditLogger
from ..widgets.toast import show_toast


class AdminView(QWidget):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self.engine = engine
        self.session = session_ctx
        self.audit = AuditLogger(engine)
        self.auth = AuthService(engine)
        self._exchange = ExchangeService(engine, session_ctx)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Администрирование")
        title.setObjectName("title")
        layout.addWidget(title)

        self.role_hint = QLabel(f"Текущая роль: {self.session.role}")
        self.role_hint.setObjectName("muted")
        layout.addWidget(self.role_hint)

        shell = QGridLayout()
        shell.setHorizontalSpacing(12)
        shell.setVerticalSpacing(12)
        layout.addLayout(shell, 1)

        # ── Пользователи ──────────────────────────────────────────────────
        users_card = QFrame()
        users_card.setObjectName("card")
        users_layout = QVBoxLayout(users_card)
        users_layout.setContentsMargins(12, 12, 12, 12)
        users_layout.setSpacing(10)

        users_title = QLabel("Пользователи")
        users_title.setObjectName("subtitle")
        users_layout.addWidget(users_title)

        user_actions = QHBoxLayout()
        self.btn_user_create = QPushButton("Создать")
        self.btn_user_create.clicked.connect(self.create_user)
        self.btn_user_disable = QPushButton("Отключить")
        self.btn_user_disable.setObjectName("secondary")
        self.btn_user_disable.clicked.connect(lambda: self.set_user_active(False))
        self.btn_user_enable = QPushButton("Включить")
        self.btn_user_enable.setObjectName("secondary")
        self.btn_user_enable.clicked.connect(lambda: self.set_user_active(True))
        self.btn_user_reset = QPushButton("Сбросить пароль")
        self.btn_user_reset.setObjectName("ghost")
        self.btn_user_reset.clicked.connect(self.reset_password)
        user_actions.addWidget(self.btn_user_create)
        user_actions.addWidget(self.btn_user_disable)
        user_actions.addWidget(self.btn_user_enable)
        user_actions.addWidget(self.btn_user_reset)
        user_actions.addStretch(1)
        users_layout.addLayout(user_actions)

        self.users_table = QTableWidget(0, 5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль", "Активен", "Создан"])
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.verticalHeader().setVisible(False)
        self.users_table.verticalHeader().setDefaultSectionSize(30)
        hdr = self.users_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        users_layout.addWidget(self.users_table, 1)

        # ── Резервное копирование ─────────────────────────────────────────
        backup_card = QFrame()
        backup_card.setObjectName("card")
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(12, 12, 12, 12)
        backup_layout.setSpacing(10)

        backup_title = QLabel("Резервное копирование")
        backup_title.setObjectName("subtitle")
        backup_layout.addWidget(backup_title)

        backup_actions = QHBoxLayout()
        self.btn_backup_create = QPushButton("Создать резервную копию")
        self.btn_backup_create.clicked.connect(self._create_backup)
        self.btn_backup_restore = QPushButton("Восстановить из файла")
        self.btn_backup_restore.setObjectName("secondary")
        self.btn_backup_restore.clicked.connect(self._restore_backup)
        backup_actions.addWidget(self.btn_backup_create)
        backup_actions.addWidget(self.btn_backup_restore)
        backup_actions.addStretch(1)
        backup_layout.addLayout(backup_actions)

        self.backup_table = QTableWidget(0, 5)
        self.backup_table.setHorizontalHeaderLabels(["ID", "Дата", "Направление", "Формат", "Файл"])
        self.backup_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.backup_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.backup_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.verticalHeader().setVisible(False)
        self.backup_table.verticalHeader().setDefaultSectionSize(30)
        bhdr = self.backup_table.horizontalHeader()
        bhdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        bhdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        bhdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        bhdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        bhdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        backup_layout.addWidget(self.backup_table, 1)

        # ── Аудит ─────────────────────────────────────────────────────────
        audit_card = QFrame()
        audit_card.setObjectName("card")
        audit_layout = QVBoxLayout(audit_card)
        audit_layout.setContentsMargins(12, 12, 12, 12)
        audit_layout.setSpacing(10)

        audit_title = QLabel("Аудит")
        audit_title.setObjectName("subtitle")
        audit_layout.addWidget(audit_title)

        self.audit_table = QTableWidget(0, 4)
        self.audit_table.setHorizontalHeaderLabels(["Время", "Пользователь", "Действие", "Entity / Payload"])
        self.audit_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.audit_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.audit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.verticalHeader().setVisible(False)
        self.audit_table.verticalHeader().setDefaultSectionSize(30)
        ahdr = self.audit_table.horizontalHeader()
        ahdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        ahdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        ahdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        ahdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        audit_layout.addWidget(self.audit_table, 1)

        # Layout: users (top-left), backup (top-right), audit (bottom, full width)
        shell.addWidget(users_card, 0, 0)
        shell.addWidget(backup_card, 0, 1)
        shell.addWidget(audit_card, 1, 0, 1, 2)
        shell.setRowStretch(0, 2)
        shell.setRowStretch(1, 3)
        shell.setColumnStretch(0, 1)
        shell.setColumnStretch(1, 1)

        self._apply_role_policy()
        self.refresh()

    def _apply_role_policy(self) -> None:
        is_admin = self.session.role == "admin"
        self.btn_user_create.setEnabled(is_admin)
        self.btn_user_disable.setEnabled(is_admin)
        self.btn_user_enable.setEnabled(is_admin)
        self.btn_user_reset.setEnabled(is_admin)
        self.btn_backup_create.setEnabled(is_admin)
        self.btn_backup_restore.setEnabled(is_admin)

    def _selected_user_id(self) -> int | None:
        row = self.users_table.currentRow()
        if row < 0:
            return None
        item = self.users_table.item(row, 0)
        if item is None:
            return None
        return int(item.text())

    def create_user(self) -> None:
        if self.session.role != "admin":
            show_toast(self.window(), "Недостаточно прав.", "error")
            return
        login, ok = QInputDialog.getText(self, "Создание пользователя", "Логин:")
        if not ok or not login.strip():
            return
        password, ok = QInputDialog.getText(self, "Создание пользователя", "Пароль:")
        if not ok or not password.strip():
            return
        role, ok = QInputDialog.getItem(
            self,
            "Создание пользователя",
            "Роль:",
            ["operator", "admin"],
            0,
            False,
        )
        if not ok:
            return
        try:
            self.auth.create_user(UserCreateIn(login=login.strip(), password=password, role=role), self.session)
            show_toast(self.window(), "Пользователь создан.", "success")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка создания: {exc}", "error")

    def set_user_active(self, is_active: bool) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            show_toast(self.window(), "Выберите пользователя.", "warning")
            return
        if user_id == self.session.user_id and not is_active:
            show_toast(self.window(), "Нельзя отключить текущую сессию.", "warning")
            return
        try:
            ok = self.auth.set_user_active(user_id, is_active, self.session)
            if ok:
                show_toast(self.window(), "Статус пользователя обновлен.", "success")
            else:
                show_toast(self.window(), "Пользователь не найден.", "error")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")

    def reset_password(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            show_toast(self.window(), "Выберите пользователя.", "warning")
            return
        password, ok = QInputDialog.getText(self, "Сброс пароля", "Новый пароль:")
        if not ok or not password.strip():
            return
        try:
            done = self.auth.reset_password(user_id, password, self.session)
            if done:
                show_toast(self.window(), "Пароль обновлен.", "success")
            else:
                show_toast(self.window(), "Пользователь не найден.", "error")
            self.refresh()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка: {exc}", "error")

    def _create_backup(self) -> None:
        try:
            path = self._exchange.export_package()
            show_toast(self.window(), f"Резервная копия создана: {path.name}", "success")
            self._refresh_backup_table()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка создания резервной копии: {exc}", "error")

    def _restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать файл резервной копии",
            "",
            "Пакеты обмена (*.zip *.json);;Все файлы (*)",
        )
        if not path:
            return
        try:
            pkg_id = self._exchange.import_package(path)
            show_toast(self.window(), f"Пакет импортирован (ID={pkg_id}).", "success")
            self._refresh_backup_table()
        except Exception as exc:
            show_toast(self.window(), f"Ошибка импорта: {exc}", "error")

    def _refresh_backup_table(self) -> None:
        try:
            rows = self._exchange.history(limit=50)
        except Exception:
            return
        self.backup_table.setRowCount(0)
        for row in rows:
            r = self.backup_table.rowCount()
            self.backup_table.insertRow(r)
            ts = row.created_at.isoformat(timespec="seconds") if row.created_at else ""
            self.backup_table.setItem(r, 0, QTableWidgetItem(str(row.id)))
            self.backup_table.setItem(r, 1, QTableWidgetItem(ts))
            direction_label = "Экспорт" if row.direction == "export" else "Импорт"
            self.backup_table.setItem(r, 2, QTableWidgetItem(direction_label))
            self.backup_table.setItem(r, 3, QTableWidgetItem(row.package_format or ""))
            self.backup_table.setItem(r, 4, QTableWidgetItem(row.file_path or ""))

    def refresh(self):
        users = self.auth.list_users()
        self.users_table.setRowCount(len(users))
        for idx, row in enumerate(users):
            self.users_table.setItem(idx, 0, QTableWidgetItem(str(row.id)))
            self.users_table.setItem(idx, 1, QTableWidgetItem(row.login))
            self.users_table.setItem(idx, 2, QTableWidgetItem(row.role))
            self.users_table.setItem(idx, 3, QTableWidgetItem("Да" if row.is_active else "Нет"))
            self.users_table.setItem(idx, 4, QTableWidgetItem(row.created_at.isoformat(timespec="seconds")))

        audit_rows = self.audit.latest(200)
        self.audit_table.setRowCount(len(audit_rows))
        for idx, row in enumerate(audit_rows):
            self.audit_table.setItem(idx, 0, QTableWidgetItem(row["event_ts"]))
            self.audit_table.setItem(idx, 1, QTableWidgetItem(row["username"]))
            self.audit_table.setItem(idx, 2, QTableWidgetItem(row["action"]))
            self.audit_table.setItem(idx, 3, QTableWidgetItem(f'{row["entity"]} | {row["payload_json"]}'))

        self._refresh_backup_table()
