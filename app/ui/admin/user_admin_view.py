from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict, cast

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import CreateUserRequest, ResetPasswordRequest, SessionContext
from app.application.exceptions import AppError
from app.application.security import can_manage_backups, can_manage_users
from app.application.services.backup_service import BackupService
from app.application.services.dashboard_service import DashboardService
from app.application.services.user_admin_service import UserAdminService
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.async_task import run_async
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.dialog_utils import exec_message_box
from app.ui.widgets.notifications import error_text
from app.ui.widgets.table_utils import connect_combo_autowidth, resize_columns_to_content

_HANDLED_UI_ERRORS = (ValueError, RuntimeError, LookupError, TypeError, AppError)
UserRole = Literal["admin", "operator"]


class UserPayload(TypedDict):
    id: int
    login: str
    role: str
    is_active: bool


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
        self._layout_update_pending = False
        self._build_ui()
        self._apply_role_policy()
        self._refresh_all()

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._apply_role_policy()
        self._refresh_all()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setObjectName("adminPageScrollArea")
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(self._build_header())

        self.admin_tabs = QTabWidget()
        self.admin_tabs.setObjectName("adminTabs")
        self.admin_tabs.addTab(self._build_users_tab(), "Пользователи")
        self.admin_tabs.addTab(self._build_audit_tab(), "Аудит")
        self.admin_tabs.addTab(self._build_backup_tab(), "Резервные копии")
        self.admin_tabs.installEventFilter(self)
        self._content_container.installEventFilter(self)
        layout.addWidget(self.admin_tabs)

        self.status = QLabel("")
        self.status.setObjectName("adminStatus")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

        self._create_widgets = [
            self.create_login,
            self.create_password,
            self.create_role,
            self.create_btn,
        ]
        self._backup_widgets = [self.backup_create_btn, self.backup_restore_btn]
        self._admin_widgets = [
            *self._create_widgets,
            self.reset_password,
            self.reset_deactivate,
            self.reset_btn,
            self.activate_btn,
            self.deactivate_btn,
            *self._backup_widgets,
        ]

        self._update_backup_actions_layout()
        self._update_create_actions_layout()
        self._update_manage_actions_layout()
        self._update_content_layout()
        self._schedule_responsive_layout_update()

    def _build_header(self) -> QWidget:
        header_card = QWidget()
        header_card.setObjectName("adminHeroCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(12)

        text_block = QWidget()
        text_block.setObjectName("adminHeroTextBlock")
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        title = QLabel("Администрирование")
        title.setObjectName("pageTitle")
        text_layout.addWidget(title)

        subtitle = QLabel("Пользователи, аудит и резервные копии в отдельных рабочих вкладках")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        text_layout.addWidget(subtitle)

        self.role_hint = QLabel("Редактирование доступно только администратору")
        self.role_hint.setObjectName("muted")
        text_layout.addWidget(self.role_hint)

        header_layout.addWidget(text_block, 1)
        self.role_badge = QLabel("")
        self.role_badge.setObjectName("adminRoleBadge")
        header_layout.addWidget(self.role_badge)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setObjectName("secondaryButton")
        compact_button(self.refresh_btn)
        self.refresh_btn.clicked.connect(self._refresh_all)
        header_layout.addWidget(self.refresh_btn)
        return header_card

    def _build_users_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 12, 0, 0)
        tab_layout.setSpacing(12)

        self._content_container = QWidget()
        self._content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)

        self._left_col = QWidget()
        self._left_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_col_layout = QVBoxLayout(self._left_col)
        left_col_layout.setContentsMargins(0, 0, 0, 0)
        left_col_layout.setSpacing(12)

        self._right_col = QWidget()
        self._right_col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_col_layout = QVBoxLayout(self._right_col)
        right_col_layout.setContentsMargins(0, 0, 0, 0)
        right_col_layout.setSpacing(12)

        self._users_frame, users_frame_layout = self._make_card("Пользователи")
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по логину")
        self.search_input.textChanged.connect(self._load_users)
        filter_row.addWidget(QLabel("Поиск"))
        filter_row.addWidget(self.search_input, 1)
        users_frame_layout.addLayout(filter_row)

        self.user_table = QTableWidget(0, 4)
        self.user_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль", "Статус"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.user_table.setMinimumHeight(320)
        self.user_table.itemSelectionChanged.connect(self._update_selected_user_panel)
        users_frame_layout.addWidget(self.user_table)

        self.user_empty_label = QLabel("Пользователи не найдены")
        self.user_empty_label.setObjectName("muted")
        self.user_empty_label.setWordWrap(True)
        users_frame_layout.addWidget(self.user_empty_label)
        left_col_layout.addWidget(self._users_frame)
        left_col_layout.addStretch()

        self._manage_box, manage_layout = self._make_card("Выбранный пользователь")
        detail_header = QHBoxLayout()
        detail_header.setContentsMargins(0, 0, 0, 0)
        self.selected_user_title = QLabel("Пользователь не выбран")
        self.selected_user_title.setObjectName("adminDetailTitle")
        detail_header.addWidget(self.selected_user_title, 1)
        self.selected_user_status = QLabel("Нет выбора")
        self.selected_user_status.setObjectName("adminStateBadge")
        detail_header.addWidget(self.selected_user_status)
        manage_layout.addLayout(detail_header)

        detail_form = QFormLayout()
        self.selected_user_id = QLabel("—")
        self.selected_user_login = QLabel("—")
        self.selected_user_role = QLabel("—")
        detail_form.addRow("ID", self.selected_user_id)
        detail_form.addRow("Логин", self.selected_user_login)
        detail_form.addRow("Роль", self.selected_user_role)
        manage_layout.addLayout(detail_form)

        reset_form = QFormLayout()
        self.reset_password = QLineEdit()
        self.reset_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_password.setPlaceholderText("Новый пароль")
        self.reset_deactivate = QCheckBox("Деактивировать после сброса")
        reset_form.addRow("Новый пароль", self.reset_password)
        reset_form.addRow("", self.reset_deactivate)
        manage_layout.addLayout(reset_form)

        self.reset_btn = QPushButton("Сбросить пароль")
        self.reset_btn.setObjectName("primaryButton")
        compact_button(self.reset_btn)
        self.reset_btn.clicked.connect(self._reset_password)
        self.activate_btn = QPushButton("Активировать")
        self.activate_btn.setObjectName("secondaryButton")
        compact_button(self.activate_btn)
        self.activate_btn.clicked.connect(lambda: self._set_active(True))
        self.deactivate_btn = QPushButton("Деактивировать")
        self.deactivate_btn.setObjectName("secondaryButton")
        compact_button(self.deactivate_btn)
        self.deactivate_btn.clicked.connect(lambda: self._set_active(False))

        self._manage_actions_bar = QWidget()
        self._manage_actions_bar.setObjectName("sectionActionBar")
        self._manage_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._manage_actions_bar)
        self._manage_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._manage_actions_layout.setSpacing(10)
        self._manage_main_group = QWidget()
        self._manage_main_group.setObjectName("sectionActionGroup")
        manage_main_layout = QHBoxLayout(self._manage_main_group)
        manage_main_layout.setContentsMargins(0, 0, 0, 0)
        manage_main_layout.setSpacing(8)
        manage_main_layout.addWidget(self.reset_btn)
        manage_main_layout.addWidget(self.activate_btn)
        manage_main_layout.addWidget(self.deactivate_btn)
        self._manage_actions_layout.addWidget(self._manage_main_group)
        self._manage_actions_layout.addStretch()
        manage_layout.addWidget(self._manage_actions_bar)
        right_col_layout.addWidget(self._manage_box)

        self._create_box, create_layout = self._make_card("Создать пользователя")
        create_form = QFormLayout()
        self.create_login = QLineEdit()
        self.create_login.setPlaceholderText("Логин")
        self.create_password = QLineEdit()
        self.create_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_password.setPlaceholderText("Минимум 8 символов")
        self.create_role = QComboBox()
        self.create_role.addItem("Оператор", "operator")
        self.create_role.addItem("Администратор", "admin")
        connect_combo_autowidth(self.create_role)
        create_form.addRow("Логин", self.create_login)
        create_form.addRow("Пароль", self.create_password)
        create_form.addRow("Роль", self.create_role)
        create_layout.addLayout(create_form)

        self.create_btn = QPushButton("Создать")
        self.create_btn.setObjectName("primaryButton")
        compact_button(self.create_btn)
        self.create_btn.clicked.connect(self._create_user)
        self._create_actions_bar = QWidget()
        self._create_actions_bar.setObjectName("sectionActionBar")
        self._create_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._create_actions_bar)
        self._create_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._create_group = QWidget()
        self._create_group.setObjectName("sectionActionGroup")
        create_group_layout = QHBoxLayout(self._create_group)
        create_group_layout.setContentsMargins(0, 0, 0, 0)
        create_group_layout.addWidget(self.create_btn)
        self._create_actions_layout.addStretch()
        self._create_actions_layout.addWidget(self._create_group)
        create_layout.addWidget(self._create_actions_bar)
        right_col_layout.addWidget(self._create_box)
        right_col_layout.addStretch()

        self._content_layout.addWidget(self._left_col, 6)
        self._content_layout.addWidget(self._right_col, 5)
        tab_layout.addWidget(self._content_container)
        return tab

    def _build_audit_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 12, 0, 0)
        tab_layout.setSpacing(12)

        self._audit_box, audit_layout = self._make_card("События аудита")
        self.audit_empty_label = QLabel("Событий аудита пока нет")
        self.audit_empty_label.setObjectName("muted")
        self.audit_empty_label.setWordWrap(True)
        audit_layout.addWidget(self.audit_empty_label)

        self.audit_table = QTableWidget(0, 5)
        self.audit_table.setHorizontalHeaderLabels(["Время", "Пользователь", "Действие", "Тип", "ID"])
        self.audit_table.horizontalHeader().setStretchLastSection(True)
        self.audit_table.verticalHeader().setVisible(False)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.audit_table.setMinimumHeight(360)
        audit_layout.addWidget(self.audit_table)
        tab_layout.addWidget(self._audit_box)
        tab_layout.addStretch()
        return tab

    def _build_backup_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 12, 0, 0)
        tab_layout.setSpacing(12)

        self._backup_box, backup_layout = self._make_card("Резервные копии")
        self.backup_status = QLabel("Последняя резервная копия: -")
        self.backup_status.setWordWrap(True)
        backup_layout.addWidget(self.backup_status)

        backup_hint = QLabel("Создание и восстановление используют текущие сервисы резервного копирования.")
        backup_hint.setObjectName("muted")
        backup_hint.setWordWrap(True)
        backup_layout.addWidget(backup_hint)

        self.backup_create_btn = QPushButton("Создать резервную копию")
        self.backup_create_btn.setObjectName("primaryButton")
        compact_button(self.backup_create_btn)
        self.backup_create_btn.clicked.connect(self._create_backup)
        self.backup_restore_btn = QPushButton("Восстановить из файла")
        self.backup_restore_btn.setObjectName("secondaryButton")
        compact_button(self.backup_restore_btn)
        self.backup_restore_btn.clicked.connect(self._restore_backup)

        self._backup_actions_bar = QWidget()
        self._backup_actions_bar.setObjectName("sectionActionBar")
        self._backup_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._backup_actions_bar)
        self._backup_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._backup_actions_layout.setSpacing(10)
        self._backup_main_group = QWidget()
        self._backup_main_group.setObjectName("sectionActionGroup")
        backup_main_layout = QHBoxLayout(self._backup_main_group)
        backup_main_layout.setContentsMargins(0, 0, 0, 0)
        backup_main_layout.setSpacing(8)
        backup_main_layout.addWidget(self.backup_restore_btn)
        self._backup_create_group = QWidget()
        self._backup_create_group.setObjectName("sectionActionGroup")
        backup_create_layout = QHBoxLayout(self._backup_create_group)
        backup_create_layout.setContentsMargins(0, 0, 0, 0)
        backup_create_layout.addWidget(self.backup_create_btn)
        self._backup_actions_layout.addWidget(self._backup_main_group)
        self._backup_actions_layout.addStretch()
        self._backup_actions_layout.addWidget(self._backup_create_group)
        backup_layout.addWidget(self._backup_actions_bar)
        tab_layout.addWidget(self._backup_box)
        tab_layout.addStretch()
        return tab

    def _make_card(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        card = QWidget()
        card.setObjectName("adminPanelCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)
        return card, layout

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_responsive_layouts()
        self._schedule_responsive_layout_update()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        super().showEvent(event)
        self._schedule_responsive_layout_update()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() in {QEvent.Type.Resize, QEvent.Type.Show} and watched in {
            getattr(self, "_content_container", None),
            getattr(self, "admin_tabs", None),
        }:
            self._schedule_responsive_layout_update()
        return super().eventFilter(watched, event)

    def _schedule_responsive_layout_update(self) -> None:
        if self._layout_update_pending:
            return
        self._layout_update_pending = True
        QTimer.singleShot(0, self._run_deferred_responsive_layout_update)

    def _run_deferred_responsive_layout_update(self) -> None:
        self._layout_update_pending = False
        self._update_responsive_layouts()

    def _update_responsive_layouts(self) -> None:
        self._update_backup_actions_layout()
        self._update_create_actions_layout()
        self._update_manage_actions_layout()
        self._update_content_layout()

    def _update_content_layout(self) -> None:
        if not hasattr(self, "_content_layout"):
            return
        width = max(1, self._content_container.width())
        left_required = max(620, self._users_frame.sizeHint().width())
        right_required = max(
            560,
            self._manage_box.sizeHint().width(),
            self._create_box.sizeHint().width(),
        )
        needed = left_required + right_required + self._content_layout.spacing() + 56
        target = (
            QBoxLayout.Direction.LeftToRight
            if width >= max(1420, needed)
            else QBoxLayout.Direction.TopToBottom
        )
        if self._content_layout.direction() != target:
            self._content_layout.setDirection(target)

        if target == QBoxLayout.Direction.LeftToRight:
            self._left_col.setMinimumWidth(560)
            self._right_col.setMinimumWidth(500)
            self._content_layout.setStretch(0, 6)
            self._content_layout.setStretch(1, 5)
        else:
            self._left_col.setMinimumWidth(0)
            self._right_col.setMinimumWidth(0)
            self._content_layout.setStretch(0, 0)
            self._content_layout.setStretch(1, 0)

    def _update_backup_actions_layout(self) -> None:
        update_action_bar_direction(
            self._backup_actions_layout,
            self._backup_actions_bar,
            [self._backup_main_group, self._backup_create_group],
        )

    def _update_create_actions_layout(self) -> None:
        update_action_bar_direction(
            self._create_actions_layout,
            self._create_actions_bar,
            [self._create_group],
        )

    def _update_manage_actions_layout(self) -> None:
        update_action_bar_direction(
            self._manage_actions_layout,
            self._manage_actions_bar,
            [self._manage_main_group],
        )

    def _apply_role_policy(self) -> None:
        can_edit_users = can_manage_users(self.session.role)
        can_edit_backups = can_manage_backups(self.session.role)
        self.role_hint.setVisible(not can_edit_users)
        self.role_badge.setText(self._role_label(self.session.role))
        self._set_label_tone(self.role_badge, "success" if can_edit_users else "info")
        self.refresh_btn.setEnabled(True)

        for widget in self._create_widgets:
            widget.setEnabled(can_edit_users)
        for widget in self._backup_widgets:
            widget.setEnabled(can_edit_backups)
        if not can_edit_users:
            self.status.setText("Доступно только администратору")
        self._update_selected_user_panel()

    def _load_users(self) -> None:
        previous_id = self._selected_user_id()
        try:
            query = self.search_input.text().strip() or None
            users = self.user_admin_service.list_users(query=query)
        except _HANDLED_UI_ERRORS as exc:
            self.status.setText(error_text(exc, "Не удалось загрузить список пользователей"))
            return

        self.user_table.blockSignals(True)
        self.user_table.clearContents()
        self.user_table.setRowCount(len(users))
        selected_row: int | None = None
        for row, user in enumerate(users):
            payload: UserPayload = {
                "id": int(user.id),
                "login": str(user.login),
                "role": str(user.role),
                "is_active": bool(user.is_active),
            }
            if previous_id == payload["id"]:
                selected_row = row
            values = [
                str(payload["id"]),
                payload["login"],
                self._role_label(payload["role"]),
                self._status_label(payload["is_active"]),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, payload)
                self.user_table.setItem(row, column, item)
        self.user_empty_label.setVisible(not users)
        if selected_row is None:
            self.user_table.clearSelection()
        else:
            self.user_table.selectRow(selected_row)
        self.user_table.blockSignals(False)
        resize_columns_to_content(self.user_table)
        self._update_selected_user_panel()

    def _load_audit(self) -> None:
        try:
            rows = self.dashboard_service.list_recent_audit(limit=20)
        except _HANDLED_UI_ERRORS as exc:
            self.status.setText(error_text(exc, "Не удалось загрузить журнал аудита"))
            return
        self.audit_table.clearContents()
        self.audit_table.setRowCount(len(rows))
        self.audit_empty_label.setVisible(not rows)
        for row, item in enumerate(rows):
            ts_value = item.get("event_ts")
            ts = ts_value.strftime("%d.%m.%Y %H:%M:%S") if isinstance(ts_value, datetime) else ""
            values = [
                ts,
                str(item.get("login") or ""),
                str(item.get("action") or ""),
                str(item.get("entity_type") or ""),
                str(item.get("entity_id") or ""),
            ]
            for column, value in enumerate(values):
                self.audit_table.setItem(row, column, QTableWidgetItem(value))
        resize_columns_to_content(self.audit_table)

    def _refresh_all(self) -> None:
        self._load_users()
        self._load_audit()
        self._refresh_backup_info()

    def _refresh_backup_info(self) -> None:
        try:
            last = self.backup_service.get_last_backup()
        except _HANDLED_UI_ERRORS as exc:
            self.backup_status.setText(error_text(exc, "Не удалось загрузить статус резервных копий"))
            return
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
            self.backup_status.setText(
                f"Ошибка резервного копирования: {error_text(exc, 'операция не выполнена')}"
            )

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=_on_error,
            on_finished=lambda: self._set_backup_busy(False),
        )

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
            self.backup_status.setText(f"Ошибка восстановления: {error_text(exc, 'операция не выполнена')}")

        run_async(
            self,
            _run,
            on_success=_on_success,
            on_error=_on_error,
            on_finished=lambda: self._set_backup_busy(False),
        )

    def _selected_user_payload(self) -> UserPayload | None:
        selected_items = self.user_table.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        item = self.user_table.item(row, 0)
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return None
        try:
            return {
                "id": int(payload["id"]),
                "login": str(payload["login"]),
                "role": str(payload["role"]),
                "is_active": bool(payload["is_active"]),
            }
        except (KeyError, TypeError, ValueError):
            return None

    def _selected_user_id(self) -> int | None:
        payload = self._selected_user_payload()
        if payload is None:
            return None
        return payload["id"]

    def _update_selected_user_panel(self) -> None:
        payload = self._selected_user_payload()
        if payload is None:
            self.selected_user_title.setText("Пользователь не выбран")
            self.selected_user_id.setText("—")
            self.selected_user_login.setText("—")
            self.selected_user_role.setText("—")
            self.selected_user_status.setText("Нет выбора")
            self._set_label_tone(self.selected_user_status, "info")
            self._set_user_actions_enabled(False)
            return

        self.selected_user_title.setText(payload["login"])
        self.selected_user_id.setText(str(payload["id"]))
        self.selected_user_login.setText(payload["login"])
        self.selected_user_role.setText(self._role_label(payload["role"]))
        self.selected_user_status.setText(self._status_label(payload["is_active"]))
        self._set_label_tone(self.selected_user_status, "success" if payload["is_active"] else "warning")
        self._set_user_actions_enabled(can_manage_users(self.session.role))

    def _set_user_actions_enabled(self, enabled: bool) -> None:
        payload = self._selected_user_payload()
        has_selection = payload is not None
        can_edit = enabled and has_selection
        self.reset_password.setEnabled(can_edit)
        self.reset_deactivate.setEnabled(can_edit)
        self.reset_btn.setEnabled(can_edit)
        self.activate_btn.setEnabled(can_edit and not bool(payload["is_active"]) if payload else False)
        self.deactivate_btn.setEnabled(can_edit and bool(payload["is_active"]) if payload else False)

    def _create_user(self) -> None:
        login = self.create_login.text().strip()
        password = self.create_password.text()
        role = cast(UserRole, self.create_role.currentData())
        if not login or not password:
            self.status.setText("Укажите логин и пароль")
            return
        try:
            req = CreateUserRequest(login=login, password=password, role=role)
            user_id = self.user_admin_service.create_user(req, actor_id=self.session.user_id)
            self.status.setText(f"Пользователь создан: id={user_id}")
            self.create_login.clear()
            self.create_password.clear()
            self._load_users()
        except _HANDLED_UI_ERRORS as exc:
            self.status.setText(error_text(exc, "Не удалось создать пользователя"))

    def _reset_password(self) -> None:
        user_id = self._selected_user_id()
        if not user_id:
            self.status.setText("Пользователь не выбран")
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
            self.status.setText("Пароль обновлён")
            self.reset_password.clear()
            self._load_users()
        except _HANDLED_UI_ERRORS as exc:
            self.status.setText(error_text(exc, "Не удалось обновить пароль"))

    def _set_active(self, is_active: bool) -> None:
        payload = self._selected_user_payload()
        if payload is None:
            self.status.setText("Пользователь не выбран")
            return
        if not is_active and not self._confirm_deactivate(payload):
            self.status.setText("Деактивация отменена")
            return
        try:
            self.user_admin_service.set_active(payload["id"], is_active, actor_id=self.session.user_id)
            state = "активирован" if is_active else "деактивирован"
            self.status.setText(f"Пользователь {state}")
            self._load_users()
        except _HANDLED_UI_ERRORS as exc:
            self.status.setText(error_text(exc, "Не удалось изменить статус пользователя"))

    def _confirm_deactivate(self, payload: UserPayload) -> bool:
        confirm = exec_message_box(
            self,
            "Деактивация пользователя",
            f"Деактивировать пользователя «{payload['login']}»?",
            icon=QMessageBox.Icon.Warning,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
            informative_text="После деактивации пользователь не сможет войти в систему.",
        )
        return confirm == QMessageBox.StandardButton.Yes

    def _role_label(self, role: str) -> str:
        if role == "admin":
            return "Администратор"
        if role == "operator":
            return "Оператор"
        return role

    def _status_label(self, is_active: bool) -> str:
        return "Активен" if is_active else "Неактивен"

    def _set_label_tone(self, label: QLabel, tone: str) -> None:
        label.setProperty("tone", tone)
        label.style().unpolish(label)
        label.style().polish(label)
