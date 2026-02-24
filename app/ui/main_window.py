from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.security import can_access_admin_view
from app.config import settings
from app.container import Container
from app.ui.admin.user_admin_view import UserAdminView
from app.ui.analytics.analytics_view import AnalyticsSearchView
from app.ui.emz.emz_form import EmzForm
from app.ui.form100.form100_view import Form100View
from app.ui.form100_v2.form100_view import Form100ViewV2
from app.ui.home.home_view import HomeView
from app.ui.import_export.import_export_view import ImportExportView
from app.ui.lab.lab_samples_view import LabSamplesView
from app.ui.login_dialog import LoginDialog
from app.ui.patient.patient_edit_dialog import PatientEditDialog
from app.ui.patient.patient_emk_view import PatientEmkView
from app.ui.references.reference_view import ReferenceView
from app.ui.runtime_ui import apply_density_property, resolve_ui_runtime
from app.ui.sanitary.sanitary_dashboard import SanitaryDashboard
from app.ui.widgets.animated_background import MedicalBackground
from app.ui.widgets.context_bar import ContextBar
from app.ui.widgets.transition_stack import TransitionStack


class NavMenuBar(QMenuBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._highlight_action: QAction | None = None
        self._logout_btn: QPushButton | None = None

    def set_highlight_action(self, action: QAction | None) -> None:
        self._highlight_action = action
        self.update()

    def set_logout_button(self, button: QPushButton | None) -> None:
        self._logout_btn = button
        if self._logout_btn:
            self._logout_btn.setParent(self)
            self._logout_btn.show()
            self._position_logout_button()

    def resizeEvent(self, event) -> None:  # noqa: D401, N802
        super().resizeEvent(event)
        self._position_logout_button()

    def _position_logout_button(self) -> None:
        if not self._logout_btn:
            return
        margin = 8
        height = max(20, self.height() - 6)
        self._logout_btn.setFixedHeight(height)
        width = max(80, self._logout_btn.sizeHint().width())
        self._logout_btn.setFixedWidth(width)
        x = max(margin, self.width() - width - margin)
        y = max(2, (self.height() - height) // 2)
        self._logout_btn.move(x, y)

    def trailing_reserved_width(self) -> int:
        if not self._logout_btn:
            return 0
        btn_width = self._logout_btn.width()
        if btn_width <= 0:
            btn_width = max(80, self._logout_btn.sizeHint().width())
        return btn_width + 20

    def paintEvent(self, event) -> None:  # noqa: D401, N802
        super().paintEvent(event)
        if not self._highlight_action:
            return
        rect = self.actionGeometry(self._highlight_action)
        if rect.isNull():
            return
        rect = rect.adjusted(2, 2, -2, -2)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#6FB9AD"), 1))
        painter.setBrush(QColor(143, 220, 207, 140))
        painter.drawRoundedRect(rect, 8, 8)


class MainWindow(QMainWindow):
    _NAV_SHORT_TITLE_MAP = {
        "Главная": "Главн.",
        "ЭМЗ": "ЭМЗ",
        "Форма 100": "Ф100",
        "Поиск и ЭМК": "Поиск",
        "Лаборатория": "Лаб.",
        "Санитария": "Сан.",
        "Аналитика": "Анал.",
        "Импорт/Экспорт": "Имп/Эксп",
        "Справочники": "Справ.",
        "Администрирование": "Админ",
    }

    _NAV_MINI_TITLE_MAP = {
        "Главная": "Гл",
        "ЭМЗ": "ЭМЗ",
        "Форма 100": "100",
        "Поиск и ЭМК": "ЭМК",
        "Лаборатория": "Лаб",
        "Санитария": "Сан",
        "Аналитика": "Анал",
        "Импорт/Экспорт": "И/Э",
        "Справочники": "Спр",
        "Администрирование": "Адм",
    }

    def __init__(self, session: SessionContext, container: Container, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.container = container
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication is not initialized")
        assert isinstance(app, QApplication)
        self._ui_runtime = resolve_ui_runtime(self, app, settings)
        self.setWindowTitle(f"Эпид. Контроль - {session.login} ({session.role})")
        self._stack = TransitionStack(animations_enabled=self._ui_runtime.enable_animations)
        self._nav_actions: dict[QWidget, QAction] = {}
        self._nav_order: list[QWidget] = []
        self._nav_action_group = QActionGroup(self)
        self._nav_action_titles: dict[QAction, str] = {}
        self._nav_action_short_titles: dict[QAction, str] = {}
        self._nav_action_mini_titles: dict[QAction, str] = {}
        self._nav_label_mode: str = "full"
        self._nav_separator_count: int = 0
        self._current_patient_id: int | None = None
        self._current_case_id: int | None = None
        self._case_selection_in_progress = False
        self._home_dirty = False
        self._menubar: NavMenuBar | None = None
        self._admin_action: QAction | None = None

        central = QWidget()
        layer_stack = QStackedLayout(central)
        layer_stack.setContentsMargins(0, 0, 0, 0)
        layer_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._background = MedicalBackground(central, intensity="subtle")
        self._background.setObjectName("bg")
        self._background.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._background.setVisible(self._ui_runtime.enable_background)
        layer_stack.addWidget(self._background)

        self._foreground = QWidget(central)
        self._foreground.setObjectName("contentOverlay")
        layer_stack.addWidget(self._foreground)
        layer_stack.setCurrentWidget(self._foreground)

        vlayout = QVBoxLayout(self._foreground)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self._stack)
        self.setCentralWidget(central)
        apply_density_property(self, settings)

        self._context_bar = ContextBar(
            emz_service=self.container.emz_service,
            patient_service=self.container.patient_service,
            on_context_change=self._on_case_selected,
            on_quick_action=self._on_quick_action,
            parent=self._foreground,
        )
        self._context_bar.set_size_change_callback(self._position_context_bar)
        self._context_bar.raise_()
        self._position_context_bar()
        vlayout.setContentsMargins(0, self._context_bar.header_height() + 6, 0, 0)

        self._init_views()
        self._build_menu()

    def _build_menu(self) -> None:
        menubar = NavMenuBar(self)
        menubar.setNativeMenuBar(False)
        self.setMenuBar(menubar)
        self._menubar = menubar
        self._nav_action_group = QActionGroup(self)
        self._nav_action_group.setExclusive(True)
        self._nav_actions = {}
        self._nav_action_titles = {}

        home_action = self._add_nav_action(menubar, "Главная", self._home_view)
        emr_action = self._add_nav_action(menubar, "ЭМЗ", self._emr_form)
        form100_action = self._add_nav_action(menubar, "Форма 100", self._form100_view)
        emk_action = self._add_nav_action(menubar, "Поиск и ЭМК", self._emk_view)
        lab_action = self._add_nav_action(menubar, "Лаборатория", self._lab_view)
        menubar.addSeparator()
        sanitary_action = self._add_nav_action(menubar, "Санитария", self._sanitary_view)
        analytics_action = self._add_nav_action(menubar, "Аналитика", self._analytics_view)
        menubar.addSeparator()
        exchange_action = self._add_nav_action(menubar, "Импорт/Экспорт", self._exchange_view)
        ref_action = self._add_nav_action(menubar, "Справочники", self._ref_view)
        admin_action = self._add_nav_action(menubar, "Администрирование", self._admin_view)
        self._admin_action = admin_action
        if not can_access_admin_view(self.session.role):
            admin_action.setEnabled(False)
            admin_action.setToolTip("Доступно только администратору")

        logout_btn = QPushButton("Выйти")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setToolTip("Выйти из системы")
        logout_btn.clicked.connect(self._logout)
        menubar.set_logout_button(logout_btn)

        self._nav_actions = {
            self._home_view: home_action,
            self._emr_form: emr_action,
            self._form100_view: form100_action,
            self._emk_view: emk_action,
            self._lab_view: lab_action,
            self._sanitary_view: sanitary_action,
            self._analytics_view: analytics_action,
            self._exchange_view: exchange_action,
            self._ref_view: ref_action,
            self._admin_view: admin_action,
        }
        self._nav_order = list(self._nav_actions.keys())
        self._nav_separator_count = 2
        self._add_nav_tooltips()
        self._set_active_view(self._stack.currentWidget())
        self._update_nav_presentation()

    def _add_nav_action(self, menubar: QMenuBar, title: str, widget: QWidget) -> QAction:
        action = menubar.addAction(title)
        action.setCheckable(True)
        self._nav_action_group.addAction(action)
        self._nav_action_titles[action] = title
        self._nav_action_short_titles[action] = self._NAV_SHORT_TITLE_MAP.get(title, title)
        self._nav_action_mini_titles[action] = self._NAV_MINI_TITLE_MAP.get(
            title,
            self._nav_action_short_titles[action],
        )
        action.triggered.connect(lambda _checked=False, w=widget: self._set_active_view(w))
        return action

    def _estimated_nav_required_width(self, mode: str) -> int:
        menubar = self._menubar
        if menubar is None:
            return 0
        fm = menubar.fontMetrics()
        per_item_padding = 28
        if mode == "compact":
            per_item_padding = 20
        elif mode == "mini":
            per_item_padding = 14
        width = 16
        for action, title in self._nav_action_titles.items():
            if mode == "full":
                text = title
            elif mode == "compact":
                text = self._nav_action_short_titles.get(action, title)
            else:
                text = self._nav_action_mini_titles.get(action, self._nav_action_short_titles.get(action, title))
            width += fm.horizontalAdvance(text) + per_item_padding
        width += self._nav_separator_count * 12
        return width

    def _choose_nav_label_mode(self, available_width: int) -> str:
        required_full = self._estimated_nav_required_width("full")
        if required_full <= available_width:
            return "full"
        required_compact = self._estimated_nav_required_width("compact")
        if required_compact <= available_width:
            return "compact"
        return "mini"

    def _update_nav_presentation(self) -> None:
        menubar = self._menubar
        if menubar is None or not self._nav_action_titles:
            return
        available_width = max(0, menubar.width() - menubar.trailing_reserved_width() - 8)
        mode = self._choose_nav_label_mode(available_width)
        text_changed = False
        for action, title in self._nav_action_titles.items():
            if mode == "full":
                target = title
            elif mode == "compact":
                target = self._nav_action_short_titles.get(action, title)
            else:
                target = self._nav_action_mini_titles.get(action, self._nav_action_short_titles.get(action, title))
            if action.text() != target:
                action.setText(target)
                text_changed = True

        mode_changed = mode != self._nav_label_mode
        self._nav_label_mode = mode
        menubar.setProperty("compactNav", mode != "full")
        menubar.setProperty("miniNav", mode == "mini")
        if mode_changed or text_changed:
            menubar.style().unpolish(menubar)
            menubar.style().polish(menubar)
        menubar.update()

    def _add_nav_tooltips(self) -> None:
        tooltips = {
            "Главная": "Сводка и последние события",
            "ЭМЗ": "Электронная медицинская запись",
            "Форма 100": "Карточка медицинской эвакуации",
            "Поиск и ЭМК": "Поиск пациента и карта пациента",
            "Лаборатория": "Пробы пациента и результаты",
            "Санитария": "Санитарные пробы отделений",
            "Аналитика": "Поиск, сводка и графики",
            "Импорт/Экспорт": "Обмен данными и пакеты",
            "Справочники": "Справочники и классификаторы",
            "Администрирование": "Пользователи и роли",
        }
        for action, title in self._nav_action_titles.items():
            if not action.isEnabled() and action.toolTip():
                continue
            action.setToolTip(tooltips.get(title, title))

    def _show_placeholder(self) -> None:
        self._placeholder = QLabel("Добро пожаловать! Разделы в разработке.", alignment=Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)
        self._stack.setCurrentWidget(self._placeholder)

    def _init_views(self) -> None:
        self._home_view = HomeView(session=self.session, dashboard_service=self.container.dashboard_service)
        self._emr_form = EmzForm(
            container=self.container,
            on_case_selected=self._on_case_selected,
            on_edit_patient=self._open_patient_edit_dialog,
            on_data_changed=self._notify_data_changed,
        )
        self._lab_view = LabSamplesView(
            lab_service=self.container.lab_service,
            reference_service=self.container.reference_service,
            on_open_emz=self._open_emz_from_emk,
            on_data_changed=self._notify_data_changed,
        )
        self._emk_view = PatientEmkView(
            patient_service=self.container.patient_service,
            emz_service=self.container.emz_service,
            reference_service=self.container.reference_service,
            on_open_emz=self._open_emz_from_emk,
            on_open_lab=self._open_lab_from_emk,
            on_edit_patient=self._open_patient_edit_dialog,
            on_data_changed=self._notify_data_changed,
        )
        self._analytics_view = AnalyticsSearchView(
            analytics_service=self.container.analytics_service,
            reference_service=self.container.reference_service,
            saved_filter_service=self.container.saved_filter_service,
            reporting_service=self.container.reporting_service,
            session=self.session,
        )
        self._exchange_view = ImportExportView(
            exchange_service=self.container.exchange_service,
            session=self.session,
        )
        if settings.form100_v2_enabled:
            self._form100_view: Form100ViewV2 | Form100View = Form100ViewV2(
                form100_service=self.container.form100_v2_service,
                reporting_service=self.container.reporting_service,
                session=self.session,
                on_data_changed=self._notify_data_changed,
            )
        else:
            self._form100_view = Form100View(
                form100_service=self.container.form100_service,
                reporting_service=self.container.reporting_service,
                session=self.session,
                on_data_changed=self._notify_data_changed,
            )
        self._sanitary_view = SanitaryDashboard(
            sanitary_service=self.container.sanitary_service,
            reference_service=self.container.reference_service,
        )
        self._ref_view = ReferenceView(
            reference_service=self.container.reference_service,
            session=self.session,
        )
        self._ref_view.references_updated.connect(self._on_references_updated)
        self._admin_view = UserAdminView(
            user_admin_service=self.container.user_admin_service,
            dashboard_service=self.container.dashboard_service,
            backup_service=self.container.backup_service,
            session=self.session,
        )
        self._stack.addWidget(self._home_view)
        self._stack.addWidget(self._emr_form)
        self._stack.addWidget(self._form100_view)
        self._stack.addWidget(self._emk_view)
        self._stack.addWidget(self._lab_view)
        self._stack.addWidget(self._sanitary_view)
        self._stack.addWidget(self._analytics_view)
        self._stack.addWidget(self._exchange_view)
        self._stack.addWidget(self._ref_view)
        self._stack.addWidget(self._admin_view)
        self._set_active_view(self._home_view)

    def _apply_session(self, session: SessionContext) -> None:
        self.session = session
        self.setWindowTitle(f"Эпид. Контроль - {session.login} ({session.role})")
        self._home_view.set_session(session)
        self._analytics_view.set_session(session)
        self._exchange_view.set_session(session)
        self._form100_view.set_session(session)
        self._ref_view.set_session(session)
        self._admin_view.set_session(session)
        if self._admin_action:
            is_admin = can_access_admin_view(session.role)
            self._admin_action.setEnabled(is_admin)
            if is_admin:
                self._admin_action.setToolTip("Пользователи и роли")
            else:
                self._admin_action.setToolTip("Доступно только администратору")
        if not can_access_admin_view(session.role) and self._stack.currentWidget() is self._admin_view:
            self._set_active_view(self._home_view)
        self._update_nav_presentation()

    def _logout(self) -> None:
        confirm = QMessageBox(self)
        confirm.setWindowTitle("Выход")
        confirm.setText("Вы точно хотите выйти?")
        confirm.setIcon(QMessageBox.Icon.Question)
        yes_btn = confirm.addButton("Да", QMessageBox.ButtonRole.YesRole)
        no_btn = confirm.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        confirm.setDefaultButton(no_btn)
        confirm.exec()
        if confirm.clickedButton() is not yes_btn:
            return
        self._clear_context()
        self.hide()
        dlg = LoginDialog(auth_service=self.container.auth_service, parent=None)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.session:
            self.close()
            return
        self._apply_session(dlg.session)
        self.show()

    def _clear_context(self) -> None:
        self._current_patient_id = None
        self._current_case_id = None
        self._context_bar.clear_context()
        self._emr_form.clear_context()
        self._form100_view.clear_context()
        self._emk_view.clear_context()
        self._lab_view.clear_context()

    def _set_active_view(self, widget: QWidget) -> None:
        if widget is self._admin_view and not can_access_admin_view(self.session.role):
            widget = self._home_view
        direction = self._resolve_direction(self._stack.currentWidget(), widget)
        self._stack.setCurrentWidgetAnimated(widget, direction=direction)
        active = self._nav_actions.get(widget)
        for action in self._nav_action_titles:
            action.setChecked(action is active)
            action.setProperty("active", action is active)
        self._update_nav_presentation()
        if self._menubar:
            self._menubar.set_highlight_action(active)
        if widget is self._home_view:
            self._refresh_home(force=True)

    def _resolve_direction(self, current: QWidget | None, target: QWidget) -> int:
        if current is None:
            return 0
        try:
            current_index = self._nav_order.index(current)
        except ValueError:
            current_index = 0
        try:
            target_index = self._nav_order.index(target)
        except ValueError:
            target_index = 0
        if target_index > current_index:
            return 1
        if target_index < current_index:
            return -1
        return 0

    def _on_case_selected(self, patient_id: int | None, emr_case_id: int | None) -> None:
        if self._case_selection_in_progress:
            return
        self._case_selection_in_progress = True
        try:
            self._current_patient_id = patient_id
            self._current_case_id = emr_case_id
            self._lab_view.set_context(patient_id, emr_case_id)
            self._emk_view.set_context(patient_id, emr_case_id)
            if patient_id is None and emr_case_id is None:
                self._emr_form.clear_context()
            else:
                self._emr_form.load_case(patient_id, emr_case_id, emit_context=False)
            self._context_bar.update_context(patient_id, emr_case_id)
        finally:
            self._case_selection_in_progress = False

    def _on_quick_action(self, key: str) -> None:
        patient_id = self._current_patient_id
        emr_case_id = self._current_case_id
        if key == "emz":
            self._on_case_selected(patient_id, emr_case_id)
            self._set_active_view(self._emr_form)
            return
        if key == "lab":
            self._on_case_selected(patient_id, emr_case_id)
            self._set_active_view(self._lab_view)
            return
        if key == "form100":
            self._set_active_view(self._form100_view)
            return
        if key == "sanitary":
            self._set_active_view(self._sanitary_view)
            return
        if key == "analytics":
            self._set_active_view(self._analytics_view)
            return

    def _on_references_updated(self) -> None:
        self._emr_form.refresh_references()
        self._lab_view.refresh_references()
        self._sanitary_view.refresh_references()
        self._analytics_view.refresh_references()
        self._emk_view.refresh_references()
        self._form100_view.refresh_references()

    def _refresh_home(self, force: bool = False) -> None:
        if force or self._home_dirty:
            self._home_view.refresh_stats()
            self._home_dirty = False

    def _notify_data_changed(self) -> None:
        if self._stack.currentWidget() is self._home_view:
            self._refresh_home(force=True)
        else:
            self._home_dirty = True

    def _open_emz_from_emk(self, patient_id: int | None, emr_case_id: int | None) -> None:
        self._on_case_selected(patient_id, emr_case_id)
        self._set_active_view(self._emr_form)

    def _open_lab_from_emk(self, patient_id: int | None, emr_case_id: int | None) -> None:
        self._on_case_selected(patient_id, emr_case_id)
        self._set_active_view(self._lab_view)

    def _open_patient_edit_dialog(self, patient_id: int) -> None:
        dlg = PatientEditDialog(
            patient_service=self.container.patient_service,
            patient_id=patient_id,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._after_patient_edit_saved(patient_id)

    def _after_patient_edit_saved(self, patient_id: int) -> None:
        self._emk_view.refresh_patient(patient_id)
        self._emr_form.refresh_patient(patient_id)
        if self._current_patient_id == patient_id:
            try:
                patient = self.container.patient_service.get_by_id(patient_id)
                patient_name = patient.full_name
            except Exception:  # noqa: BLE001
                patient_name = ""
            self._context_bar.update_context(self._current_patient_id, self._current_case_id, patient_name)
        self._notify_data_changed()

    def resizeEvent(self, event) -> None:  # noqa: D401, N802
        super().resizeEvent(event)
        self._position_context_bar()
        self._update_nav_presentation()
        if self._menubar:
            active = self._nav_actions.get(self._stack.currentWidget())
            self._menubar.set_highlight_action(active)

    def _position_context_bar(self) -> None:
        if not self._context_bar:
            return
        margin_x = 8
        margin_y = 6
        parent = self._foreground
        if not parent:
            return
        width = max(0, parent.width() - 2 * margin_x)
        height = self._context_bar.desired_height()
        self._context_bar.setGeometry(margin_x, margin_y, width, height)
