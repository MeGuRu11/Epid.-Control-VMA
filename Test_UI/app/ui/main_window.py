from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from ..application.services.emr_service import EmrService
from ..application.services.patient_service import PatientService
from .form100.form100_view import Form100View
from .pages.admin_view import AdminView
from .pages.analytics_view import AnalyticsView
from .pages.emr_view import EmrView
from .pages.home_view import HomeView
from .pages.import_export_view import ImportExportView
from .pages.lab_view import LabView
from .pages.patient_view import PatientView
from .pages.references_view import ReferencesView
from .pages.sanitary_view import SanitaryView
from .widgets.animated_background import MedicalBackground
from .widgets.context_bar import ContextBar
from .widgets.sidebar_drawer import SidebarDrawer
from .widgets.stack_transition import TransitionStack
from .widgets.toast import show_toast

NAV_KEYS: list[str] = [
    "home",
    "emr",
    "form100",
    "patient",
    "lab",
    "sanitary",
    "analytics",
    "import_export",
    "references",
    "admin",
]


class MainWindow(QMainWindow):
    def __init__(self, engine, session_ctx):
        super().__init__()
        self.engine = engine
        self.session = session_ctx
        self._patient_svc = PatientService(engine, session_ctx)
        self._emr_svc = EmrService(engine, session_ctx)

        self._current_key = "home"
        self._context_patient_id: int | None = None
        self._context_case_id: int | None = None
        self._context_patient_name: str | None = None
        self._context_status = "Пациент не выбран"

        self.setWindowTitle("EpiSafe")
        self.resize(1320, 820)
        self.setMinimumSize(1120, 720)

        # Sidebar is primary navigation; top menubar is intentionally disabled.
        self.menuBar().setVisible(False)

        self._build_layout()
        self._build_pages()
        self._wire_signals()

        self.open_page("home")
        show_toast(self, "Система готова к работе.", "success")

    def _build_layout(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        layer_stack = QStackedLayout(root)
        layer_stack.setContentsMargins(0, 0, 0, 0)
        layer_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.background = MedicalBackground(root, intensity="subtle")
        self.background.setObjectName("bg")
        self.background.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layer_stack.addWidget(self.background)

        self.content_overlay = QWidget(root)
        self.content_overlay.setObjectName("contentOverlay")
        layer_stack.addWidget(self.content_overlay)
        layer_stack.setCurrentWidget(self.content_overlay)

        overlay_layout = QVBoxLayout(self.content_overlay)
        overlay_layout.setContentsMargins(14, 14, 14, 14)
        overlay_layout.setSpacing(12)

        shell = QHBoxLayout()
        shell.setSpacing(12)
        overlay_layout.addLayout(shell, 1)

        self.sidebar = SidebarDrawer()
        self.sidebar.set_visible_for_role(self.session.role)
        shell.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setSpacing(12)
        shell.addLayout(right, 1)

        self.context_bar = ContextBar()

        right.addWidget(self.context_bar)

        self.stack = TransitionStack()
        right.addWidget(self.stack, 1)

        self._refresh_context_bar()

    def _build_pages(self) -> None:
        self.pages: dict[str, Any] = {
            "home": HomeView(self.engine, self.session),
            "patient": PatientView(self.engine, self.session),
            "emr": EmrView(self.engine, self.session),
            "lab": LabView(self.engine, self.session),
            "sanitary": SanitaryView(self.engine, self.session),
            "analytics": AnalyticsView(self.engine, self.session),
            "import_export": ImportExportView(self.engine, self.session),
            "references": ReferencesView(self.engine, self.session),
            "form100": Form100View(self.engine, self.session),
            "admin": AdminView(self.engine, self.session),
        }
        for key in NAV_KEYS:
            self.stack.addWidget(self.pages[key])

    def _wire_signals(self) -> None:
        self.sidebar.pageRequested.connect(self.open_page)
        self.pages["home"].pageRequested.connect(self.open_page)
        self.pages["patient"].patientSelected.connect(lambda patient_id: self._set_patient_context(patient_id, True))
        self.pages["patient"].patientContextSelected.connect(
            lambda patient_id: self._set_patient_context(patient_id, False)
        )
        self.pages["emr"].backRequested.connect(lambda: self.open_page("patient"))
        self.pages["emr"].caseSelected.connect(self._set_case_context)
        self.pages["emr"].createForm100Requested.connect(lambda: self.open_page("form100"))
        self.context_bar.pickPatientRequested.connect(self._pick_patient_context)
        self.context_bar.pickCaseRequested.connect(self._pick_case_context)
        self.context_bar.openPageRequested.connect(self.open_page)

    def _refresh_context_bar(self) -> None:
        has_patient = self._context_patient_id is not None
        has_case = self._context_case_id is not None
        self.context_bar.set_context(
            self._context_patient_id,
            self._context_case_id,
            self._context_status,
            patient_name=self._context_patient_name,
        )
        self.context_bar.set_actions_enabled(has_patient, has_case)

    def _set_patient_context(self, patient_id: int, open_emr: bool = False) -> None:
        self._context_patient_id = patient_id
        self._context_case_id = None
        try:
            p = self._patient_svc.details(patient_id)
            self._context_patient_name = str(p.full_name or "").strip() or None
        except Exception:
            self._context_patient_name = None
        self._context_status = "Пациент выбран"
        self.pages["emr"].set_context(patient_id)
        self.pages["lab"].set_context(patient_id, None, self._context_patient_name)
        self.pages["form100"].set_context(patient_id, None)
        cases = self._emr_svc.cases_for_patient(patient_id)
        if cases:
            self._set_case_context(int(cases[0].id), silent=True)
        self._refresh_context_bar()
        if open_emr:
            self.open_page("emr")

    def _set_case_context(self, case_id: int, silent: bool = False) -> None:
        self._context_case_id = case_id
        self._context_status = "Госпитализация выбрана"
        self.pages["emr"].set_case_context(case_id)
        self.pages["lab"].set_context(
            self._context_patient_id, case_id, self._context_patient_name
        )
        self.pages["form100"].set_context(self._context_patient_id, case_id)
        self._refresh_context_bar()
        if not silent:
            show_toast(self, "Контекст госпитализации обновлен.", "info")

    def _pick_patient_context(self) -> None:
        patients = self._patient_svc.list("")
        if not patients:
            show_toast(self, "Пациенты не найдены. Создайте пациента в разделе 'Поиск и ЭМК'.", "warning")
            return
        items = [str(p.full_name or "").strip() or "Пациент без имени" for p in patients]
        selected, ok = QInputDialog.getItem(self, "Выбор пациента", "Пациент:", items, 0, False)
        if not ok or not selected:
            return
        selected_idx = items.index(selected)
        patient_id = int(patients[selected_idx].id)
        self._set_patient_context(patient_id, open_emr=False)
        show_toast(self, "Контекст пациента установлен.", "success")

    def _pick_case_context(self) -> None:
        if self._context_patient_id is None:
            show_toast(self, "Сначала выберите пациента.", "warning")
            return
        cases = self._emr_svc.cases_for_patient(self._context_patient_id)
        if not cases:
            show_toast(self, "У пациента нет госпитализаций. Создайте запись в ЭМЗ.", "warning")
            return
        items = [
            f"ИБ {c.hospital_case_no} | {c.department or 'н/д'}"
            for c in cases
        ]
        selected, ok = QInputDialog.getItem(self, "Выбор госпитализации", "Госпитализация:", items, 0, False)
        if not ok or not selected:
            return
        selected_idx = items.index(selected)
        case_id = int(cases[selected_idx].id)
        self._set_case_context(case_id)

    def open_page(self, key: str) -> None:
        if key == "admin" and self.session.role != "admin":
            show_toast(self, "Доступ к администрированию только для admin.", "error")
            self._sync_nav_state(self._current_key)
            return
        if key == "form100" and (self._context_patient_id is None or self._context_case_id is None):
            show_toast(self, "Для Формы 100 выберите пациента и госпитализацию (ЭМЗ).", "warning")
            self._sync_nav_state(self._current_key)
            return

        page = self.pages.get(key)
        if page is None:
            return

        if key == "home":
            self.pages["home"].refresh()
        if key == "patient":
            self.pages["patient"].refresh()
        if key == "lab":
            self.pages["lab"].refresh()
        if key == "sanitary":
            self.pages["sanitary"].refresh()
        if key == "references":
            self.pages["references"].refresh()
        if key == "import_export":
            self.pages["import_export"].refresh()
        if key == "analytics":
            self.pages["analytics"].refresh()
        if key == "form100":
            self.pages["form100"].refresh()
        if key == "admin":
            self.pages["admin"].refresh()

        self.stack.setCurrentWidgetAnimated(page, direction=self._direction_to(key))
        self._current_key = key
        self._sync_nav_state(key)

    def _sync_nav_state(self, key: str) -> None:
        self.sidebar.set_current_page(key)

    def _direction_to(self, key: str) -> int:
        index_map = {k: i for i, k in enumerate(NAV_KEYS)}
        prev = index_map.get(self._current_key, 0)
        nxt = index_map.get(key, 0)
        if nxt > prev:
            return 1
        if nxt < prev:
            return -1
        return 0
