from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import CreateUserRequest, ResetPasswordRequest, SessionContext
from app.application.security import can_manage_backups, can_manage_users
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.user_admin_service import UserAdminService
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.table_utils import connect_combo_autowidth, resize_columns_by_first_row


class UserAdminView(QWidget):
    def __init__(
        self,
        user_admin_service: UserAdminService,
        dashboard_service: DashboardService,
        backup_service: BackupService,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.user_admin_service = user_admin_service
        self.dashboard_service = dashboard_service
        self.backup_service = backup_service
        self.session = session
        self._build_ui()
        self._apply_role_policy()
        self._refresh_all()

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._apply_role_policy()
        self._refresh_all()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        title = QLabel("Администрирование")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        self.refresh_btn = QPushButton("Обновить")
        compact_button(self.refresh_btn)
        self.refresh_btn.clicked.connect(self._refresh_all)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        self.role_hint = QLabel("Редактирование доступно только администратору")
        self.role_hint.setObjectName("muted")
        layout.addWidget(self.role_hint)

        users_frame = QGroupBox("Список пользователей")
        users_frame_layout = QVBoxLayout(users_frame)

        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по логину")
        self.search_input.textChanged.connect(self._load_users)
        filter_row.addWidget(QLabel("Поиск"))
        filter_row.addWidget(self.search_input)
        users_frame_layout.addLayout(filter_row)

        self.user_table = QTableWidget(0, 4)
        self.user_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль", "Статус"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.user_table.setMinimumHeight(200)
        users_frame_layout.addWidget(self.user_table)

        users_actions = QHBoxLayout()
        users_actions.addStretch()
        users_frame_layout.addLayout(users_actions)

        layout.addWidget(users_frame)

        backup_box = QGroupBox("Резервные копии")
        backup_layout = QVBoxLayout(backup_box)
        self.backup_status = QLabel("Последняя резервная копия: -")
        backup_layout.addWidget(self.backup_status)
        backup_actions = QHBoxLayout()
        self.backup_create_btn = QPushButton("Создать резервную копию")
        compact_button(self.backup_create_btn)
        self.backup_create_btn.clicked.connect(self._create_backup)
        self.backup_restore_btn = QPushButton("Восстановить из файла")
        compact_button(self.backup_restore_btn)
        self.backup_restore_btn.clicked.connect(self._restore_backup)
        backup_actions.addWidget(self.backup_create_btn)
        backup_actions.addWidget(self.backup_restore_btn)
        backup_actions.addStretch()
        backup_layout.addLayout(backup_actions)
        layout.addWidget(backup_box)

        audit_box = QGroupBox("События аудита")
        audit_layout = QVBoxLayout(audit_box)
        self.audit_table = QTableWidget(0, 5)
        self.audit_table.setHorizontalHeaderLabels(
            ["Время", "Пользователь", "Действие", "Тип", "ID"]
        )
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.verticalHeader().setVisible(False)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.setMinimumHeight(220)
        audit_layout.addWidget(self.audit_table)
        layout.addWidget(audit_box)

        create_box = QGroupBox("Создать пользователя")
        create_layout = QVBoxLayout(create_box)
        create_form = QFormLayout()
        self.create_login = QLineEdit()
        self.create_password = QLineEdit()
        self.create_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_role = QComboBox()
        self.create_role.addItem("Оператор", "operator")
        self.create_role.addItem("Администратор", "admin")
        connect_combo_autowidth(self.create_role)
        create_form.addRow("Логин", self.create_login)
        create_form.addRow("Пароль", self.create_password)
        create_form.addRow("Роль", self.create_role)
        create_layout.addLayout(create_form)
        create_btn = QPushButton("Создать")
        compact_button(create_btn)
        create_btn.clicked.connect(self._create_user)
        create_actions = QHBoxLayout()
        create_actions.addWidget(create_btn)
        create_actions.addStretch()
        create_layout.addLayout(create_actions)
        layout.addWidget(create_box)

        manage_box = QGroupBox("Сброс пароля / статус")
        manage_layout = QVBoxLayout(manage_box)
        reset_form = QFormLayout()
        self.reset_password = QLineEdit()
        self.reset_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_deactivate = QCheckBox("Деактивировать пользователя")
        reset_form.addRow("Новый пароль", self.reset_password)
        reset_form.addRow("", self.reset_deactivate)
        manage_layout.addLayout(reset_form)
        reset_btn = QPushButton("Сбросить пароль")
        compact_button(reset_btn)
        reset_btn.clicked.connect(self._reset_password)
        self.activate_btn = QPushButton("Активировать")
        compact_button(self.activate_btn)
        self.activate_btn.clicked.connect(lambda: self._set_active(True))
        self.deactivate_btn = QPushButton("Деактивировать")
        compact_button(self.deactivate_btn)
        self.deactivate_btn.clicked.connect(lambda: self._set_active(False))
        manage_actions = QHBoxLayout()
        manage_actions.addWidget(reset_btn)
        manage_actions.addWidget(self.activate_btn)
        manage_actions.addWidget(self.deactivate_btn)
        manage_actions.addStretch()
        manage_layout.addLayout(manage_actions)
        layout.addWidget(manage_box)

        self.status = QLabel("")
        self.status.setObjectName("adminStatus")
        layout.addWidget(self.status)
        layout.addStretch()

        self._admin_widgets = [
            self.create_login,
            self.create_password,
            self.create_role,
            create_btn,
            self.reset_password,
            self.reset_deactivate,
            reset_btn,
            self.activate_btn,
            self.deactivate_btn,
            self.refresh_btn,
            self.backup_create_btn,
            self.backup_restore_btn,
        ]

    def _apply_role_policy(self) -> None:
        is_admin = can_manage_users(self.session.role)
        self.role_hint.setVisible(not is_admin)
        for widget in self._admin_widgets:
            widget.setEnabled(is_admin)
        if not is_admin:
            self.status.setText("Доступно только администратору")

    def _load_users(self) -> None:
        try:
            query = self.search_input.text().strip() or None
            users = self.user_admin_service.list_users(query=query)
        except Exception as exc:  # noqa: BLE001
            self.status.setText(str(exc))
            return

        self.user_table.clearContents()
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
            self.user_table.setItem(row, 1, QTableWidgetItem(user.login))
            self.user_table.setItem(row, 2, QTableWidgetItem(user.role))
            self.user_table.setItem(row, 3, QTableWidgetItem("Активен" if user.is_active else "Неактивен"))
        resize_columns_by_first_row(self.user_table)

    def _load_audit(self) -> None:
        rows = self.dashboard_service.list_recent_audit(limit=20)
        self.audit_table.clearContents()
        self.audit_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            ts = item["event_ts"].strftime("%d.%m.%Y %H:%M:%S") if item["event_ts"] else ""
            self.audit_table.setItem(row, 0, QTableWidgetItem(ts))
            self.audit_table.setItem(row, 1, QTableWidgetItem(item["login"]))
            self.audit_table.setItem(row, 2, QTableWidgetItem(item["action"]))
            self.audit_table.setItem(row, 3, QTableWidgetItem(item["entity_type"]))
            self.audit_table.setItem(row, 4, QTableWidgetItem(item["entity_id"]))
        resize_columns_by_first_row(self.audit_table)

    def _refresh_all(self) -> None:
        self._load_users()
        self._load_audit()
        self._refresh_backup_info()

    def _refresh_backup_info(self) -> None:
        last = self.backup_service.get_last_backup()
        if not last:
            self.backup_status.setText("Последняя резервная копия: -")
            return
        ts = last.created_at.astimezone().strftime("%d.%m.%Y %H:%M:%S")
        self.backup_status.setText(f"Последняя резервная копия: {ts} ({last.reason})")

    def _set_backup_busy(self, busy: bool, message: str | None = None) -> None:
        is_admin = can_manage_backups(self.session.role)
        self.backup_create_btn.setEnabled(is_admin and not busy)
        self.backup_restore_btn.setEnabled(is_admin and not busy)
        if message is not None:
            self.backup_status.setText(message)

    def _create_backup(self) -> None:
        self._set_backup_busy(True, "Создание резервной копии...")

        def _run() -> Path:
            return self.backup_service.create_backup(actor_id=self.session.user_id, reason="manual")

        def _on_success(path: Path) -> None:
            self.backup_status.setText(f"Создана резервная копия: {path.name}")

        def _on_error(exc: Exception) -> None:
            self.backup_status.setText(f"Ошибка резервного копирования: {exc}")

        run_async(self, _run, on_success=_on_success, on_error=_on_error, on_finished=lambda: self._set_backup_busy(False))

    def _restore_backup(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Восстановить резервную копию",
            str(self.backup_service.backup_dir),
            "SQLite DB (*.db)",
        )
        if not filename:
            return
        backup_path = Path(filename)
        self._set_backup_busy(True, "Восстановление из резервной копии...")

        def _run() -> None:
            self.backup_service.restore_backup(backup_path, actor_id=self.session.user_id)

        def _on_success(_: object) -> None:
            self.backup_status.setText("Восстановление завершено. Перезапустите приложение.")

        def _on_error(exc: Exception) -> None:
            self.backup_status.setText(f"Ошибка восстановления: {exc}")

        run_async(self, _run, on_success=_on_success, on_error=_on_error, on_finished=lambda: self._set_backup_busy(False))

    def _selected_user_id(self) -> int | None:
        items = self.user_table.selectedItems()
        if not items:
            return None
        return int(items[0].text())

    def _create_user(self) -> None:
        login = self.create_login.text().strip()
        password = self.create_password.text()
        role = self.create_role.currentData()
        if not login or not password:
            self.status.setText("Укажите логин и пароль")
            return
        try:
            req = CreateUserRequest(login=login, password=password, role=role)
            user_id = self.user_admin_service.create_user(req, actor_id=self.session.user_id)
            self.status.setText(f"Создан пользователь id={user_id}")
            self.create_login.clear()
            self.create_password.clear()
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            self.status.setText(str(exc))

    def _reset_password(self) -> None:
        user_id = self._selected_user_id()
        if not user_id:
            self.status.setText("Выберите пользователя в списке")
            return
        new_password = self.reset_password.text()
        if not new_password:
            self.status.setText("Укажите новый пароль")
            return
        try:
            req = ResetPasswordRequest(
                user_id=user_id,
                new_password=new_password,
                deactivate=self.reset_deactivate.isChecked(),
            )
            self.user_admin_service.reset_password(req, actor_id=self.session.user_id)
            self.status.setText("Пароль обновлен")
            self.reset_password.clear()
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            self.status.setText(str(exc))

    def _set_active(self, is_active: bool) -> None:
        user_id = self._selected_user_id()
        if not user_id:
            self.status.setText("Выберите пользователя в списке")
            return
        try:
            self.user_admin_service.set_active(user_id, is_active, actor_id=self.session.user_id)
            state = "активирован" if is_active else "деактивирован"
            self.status.setText(f"Пользователь {state}")
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            self.status.setText(str(exc))
