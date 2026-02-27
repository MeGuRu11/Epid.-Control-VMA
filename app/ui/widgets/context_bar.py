from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QStringListModel, Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QCompleter,
    QDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.application.services.emz_service import EmzService
from app.application.services.patient_service import PatientService
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error
from app.ui.widgets.responsive_actions import ResponsiveActionsPanel


class ContextBar(QWidget):
    def __init__(
        self,
        emz_service: EmzService,
        patient_service: PatientService,
        on_context_change: Callable[[int | None, int | None], None],
        on_quick_action: Callable[[str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.emz_service = emz_service
        self.patient_service = patient_service
        self.on_context_change = on_context_change
        self.on_quick_action = on_quick_action
        self.patient_id: int | None = None
        self.case_id: int | None = None
        self.patient_name: str = ""
        self.last_patient_id: int | None = None
        self.last_patient_name: str = ""
        self._header_height = 0
        self._on_size_change: Callable[[], None] | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("contextBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("contextToggle")
        self.toggle_btn.setText("▸")
        self.toggle_btn.setToolTip("Показать/скрыть контекст пациента и госпитализации.")
        self.toggle_btn.setFixedSize(26, 26)
        self.toggle_btn.clicked.connect(self._toggle_content)
        header_row.addWidget(self.toggle_btn)
        context_title = QLabel("Закрепить пациента")
        context_title.setObjectName("sectionTitle")
        context_title.setToolTip("Задаёт текущего пациента и госпитализацию для всех разделов.")
        header_row.addWidget(context_title)
        header_row.addStretch()
        self._header_helper = QLabel("Быстрый выбор пациента и/или госпитализации для удобной работы.")
        self._header_helper.setObjectName("muted")
        header_row.addWidget(self._header_helper)
        layout.addLayout(header_row)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(6)

        chips_row = QHBoxLayout()
        patient_chip = QHBoxLayout()
        self.patient_label = QLabel("Пациент: -")
        self.patient_label.setObjectName("chipLabel")
        self.patient_label.setToolTip("Текущий пациент (ID и ФИО).")
        self.clear_patient_btn = QPushButton("x")
        self.clear_patient_btn.setObjectName("chipClear")
        self.clear_patient_btn.setToolTip("Очистить пациента и госпитализацию.")
        self.clear_patient_btn.clicked.connect(self._clear_patient)
        patient_chip.addWidget(self.patient_label)
        patient_chip.addWidget(self.clear_patient_btn)
        chips_row.addLayout(patient_chip)

        case_chip = QHBoxLayout()
        self.case_label = QLabel("Госпитализация: -")
        self.case_label.setObjectName("chipLabel")
        self.case_label.setToolTip("Текущая госпитализация (ID).")
        self.clear_case_btn = QPushButton("x")
        self.clear_case_btn.setObjectName("chipClear")
        self.clear_case_btn.setToolTip("Очистить госпитализацию.")
        self.clear_case_btn.clicked.connect(self._clear_case)
        case_chip.addWidget(self.case_label)
        case_chip.addWidget(self.clear_case_btn)
        chips_row.addLayout(case_chip)
        chips_row.addStretch()
        content_layout.addLayout(chips_row)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)
        self._controls_row = controls_row

        self._patient_controls_group = QWidget()
        patient_block = QVBoxLayout(self._patient_controls_group)
        patient_block.setContentsMargins(0, 0, 0, 0)
        patient_block.setSpacing(4)
        patient_label = QLabel("Пациент")
        patient_label.setObjectName("muted")
        patient_block.addWidget(patient_label)
        patient_row = QHBoxLayout()
        self.patient_search = QLineEdit()
        self.patient_search.setPlaceholderText("ФИО или ID пациента")
        self.patient_search.setToolTip("Введите ID пациента или часть ФИО для поиска.")
        self._completer_model = QStringListModel()
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self._on_patient_autocomplete)
        self.patient_search.setCompleter(self._completer)
        self.patient_search.textEdited.connect(self._on_patient_search_text)
        patient_row.addWidget(self.patient_search)
        find_patient_btn = QPushButton("Найти пациента")
        find_patient_btn.setToolTip("Открыть поиск пациента и выбрать нужного.")
        find_patient_btn.clicked.connect(self._find_patient)
        patient_row.addWidget(find_patient_btn)
        self.last_patient_btn = QPushButton("Последний пациент")
        self.last_patient_btn.setToolTip("Вернуть последнего выбранного пациента.")
        self.last_patient_btn.clicked.connect(self._restore_last_patient)
        self.last_patient_btn.setEnabled(False)
        patient_row.addWidget(self.last_patient_btn)
        patient_block.addLayout(patient_row)
        controls_row.addWidget(self._patient_controls_group)

        self._case_controls_group = QWidget()
        case_block = QVBoxLayout(self._case_controls_group)
        case_block.setContentsMargins(0, 0, 0, 0)
        case_block.setSpacing(4)
        case_label = QLabel("Госпитализация")
        case_label.setObjectName("muted")
        case_block.addWidget(case_label)
        case_row = QHBoxLayout()
        self.case_search = QLineEdit()
        self.case_search.setPlaceholderText("Номер истории болезни (>= 3 символа)")
        self.case_search.setToolTip("Введите часть номера истории болезни для поиска.")
        self._case_model = QStringListModel()
        self._case_completer = QCompleter(self._case_model, self)
        self._case_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._case_completer.activated.connect(self._on_case_autocomplete)
        self.case_search.setCompleter(self._case_completer)
        self.case_search.textEdited.connect(self._on_case_search_text)
        case_row.addWidget(self.case_search)
        select_case_btn = QPushButton("Выбрать по ID")
        select_case_btn.setToolTip("Введите ID госпитализации вручную.")
        select_case_btn.clicked.connect(self._select_case_by_id)
        reset_btn = QPushButton("Сбросить")
        reset_btn.setToolTip("Очистить контекст пациента и госпитализации.")
        reset_btn.clicked.connect(self._reset)
        case_row.addWidget(select_case_btn)
        case_row.addWidget(reset_btn)
        case_block.addLayout(case_row)
        controls_row.addWidget(self._case_controls_group)
        controls_row.addStretch()
        content_layout.addLayout(controls_row)
        content_layout.addSpacing(8)

        actions_title = QLabel("Быстрые действия:")
        actions_title.setObjectName("muted")
        content_layout.addWidget(actions_title)
        self._actions_panel = ResponsiveActionsPanel(min_button_width=84, max_columns=5)
        self._actions_panel.setObjectName("contextActions")
        self.open_emz_btn = QPushButton("ЭМЗ")
        compact_button(self.open_emz_btn, min_width=88, max_width=164)
        self.open_emz_btn.clicked.connect(lambda: self._quick_action("emz"))
        self.open_lab_btn = QPushButton("Лаб")
        compact_button(self.open_lab_btn, min_width=88, max_width=164)
        self.open_lab_btn.clicked.connect(lambda: self._quick_action("lab"))
        self.open_form100_btn = QPushButton("Ф100")
        compact_button(self.open_form100_btn, min_width=88, max_width=164)
        self.open_form100_btn.clicked.connect(lambda: self._quick_action("form100"))
        self.open_san_btn = QPushButton("Санитария")
        compact_button(self.open_san_btn, min_width=88, max_width=164)
        self.open_san_btn.clicked.connect(lambda: self._quick_action("sanitary"))
        self.open_analytics_btn = QPushButton("Аналитика")
        compact_button(self.open_analytics_btn, min_width=88, max_width=164)
        self.open_analytics_btn.clicked.connect(lambda: self._quick_action("analytics"))
        self._actions_panel.set_buttons(
            [
                self.open_emz_btn,
                self.open_lab_btn,
                self.open_form100_btn,
                self.open_san_btn,
                self.open_analytics_btn,
            ]
        )
        content_layout.addWidget(self._actions_panel)

        self.content_widget.setMaximumHeight(0)
        self.content_widget.setVisible(False)
        self._content_effect = QGraphicsOpacityEffect(self.content_widget)
        self._content_effect.setOpacity(0.0)
        self.content_widget.setGraphicsEffect(self._content_effect)
        layout.addWidget(self.content_widget)
        self._header_height = self.sizeHint().height()
        self._update_layout_mode()

    def _quick_action(self, key: str) -> None:
        if not self.on_quick_action:
            return
        self.on_quick_action(key)

    def _toggle_content(self) -> None:
        expanding = not self.content_widget.isVisible()
        if expanding:
            self.content_widget.setVisible(True)
        self._animate_content(expanding)
        self.toggle_btn.setText("▾" if expanding else "▸")

    def _animate_content(self, expanding: bool) -> None:
        target_height = self.content_widget.sizeHint().height()
        start = 0 if expanding else target_height
        end = target_height if expanding else 0
        self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight", self)
        anim_ms = 180
        self._anim.setDuration(anim_ms)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(lambda: self._on_animation_done(expanding))
        self._anim.valueChanged.connect(lambda _value: self._emit_size_change())
        self._anim.start()
        fade_start = 0.0 if expanding else 1.0
        fade_end = 1.0 if expanding else 0.0
        self._fade_anim = QPropertyAnimation(self._content_effect, b"opacity", self)
        self._fade_anim.setDuration(anim_ms)
        self._fade_anim.setStartValue(fade_start)
        self._fade_anim.setEndValue(fade_end)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_anim.start()

    def _on_animation_done(self, expanded: bool) -> None:
        if not expanded:
            self.content_widget.setVisible(False)
            self._content_effect.setOpacity(0.0)
        self._emit_size_change()

    def set_size_change_callback(self, callback: Callable[[], None] | None) -> None:
        self._on_size_change = callback

    def header_height(self) -> int:
        return self._header_height

    def desired_height(self) -> int:
        return self._header_height + self.content_widget.maximumHeight() + 8

    def _emit_size_change(self) -> None:
        if self._on_size_change:
            self._on_size_change()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_layout_mode()

    def _update_layout_mode(self) -> None:
        update_action_bar_direction(
            self._controls_row,
            self.content_widget,
            [self._patient_controls_group, self._case_controls_group],
            extra_width=28,
        )
        stacked_controls = self._controls_row.direction() == QBoxLayout.Direction.TopToBottom
        helper_required_width = self._header_helper.sizeHint().width() + 420
        self._header_helper.setVisible(self.width() >= helper_required_width)
        actions_required_width = self._actions_panel.sizeHint().width() + 16
        actions_available = self.content_widget.width()
        compact_mode = stacked_controls or actions_available < actions_required_width
        self._actions_panel.set_compact(compact_mode)

    def _select_case_by_id(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        case_id, ok = QInputDialog.getInt(
            self,
            "Выбор госпитализации",
            "ID госпитализации:",
            value=1,
            minValue=1,
        )
        if not ok:
            return
        try:
            detail = self.emz_service.get_current(case_id)
            self._set_context(
                patient_id=detail.patient_id,
                case_id=detail.id,
                patient_name=detail.patient_full_name,
                emit=True,
            )
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _find_patient(self) -> None:
        query = self.patient_search.text().strip()
        if query.isdigit():
            try:
                patient = self.patient_service.get_by_id(int(query))
            except Exception as exc:  # noqa: BLE001
                show_error(self, f"Пациент не найден: {exc}")
                return
            self._set_context(
                patient_id=patient.id,
                case_id=None,
                patient_name=patient.full_name,
                emit=True,
            )
            return

        from app.ui.widgets.patient_search_dialog import PatientSearchDialog

        dlg = PatientSearchDialog(
            self.patient_service,
            parent=self,
            initial_query=query,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_patient_id:
            self._set_context(
                patient_id=dlg.selected_patient_id,
                case_id=None,
                patient_name=dlg.selected_name,
                emit=True,
            )

    def _set_context(
        self, patient_id: int | None, case_id: int | None, patient_name: str = "", emit: bool = False
    ) -> None:
        self.patient_id = patient_id
        self.case_id = case_id
        self.patient_name = patient_name
        self.patient_label.setText(f"Пациент: {patient_id or '-'} {patient_name}".rstrip())
        self.case_label.setText(f"Госпитализация: {case_id or '-'}")
        if patient_id:
            self.last_patient_id = patient_id
            self.last_patient_name = patient_name
            self.last_patient_btn.setEnabled(True)
        if emit:
            self.on_context_change(patient_id, case_id)

    def update_context(self, patient_id: int | None, case_id: int | None, patient_name: str = "") -> None:
        if patient_id is not None and not patient_name and patient_id == self.patient_id:
            patient_name = self.patient_name
        self._set_context(patient_id, case_id, patient_name, emit=False)

    def clear_context(self) -> None:
        self.last_patient_id = None
        self.last_patient_name = ""
        self.last_patient_btn.setEnabled(False)
        self.patient_search.clear()
        self.case_search.clear()
        self._completer_model.setStringList([])
        self._case_model.setStringList([])
        self._set_context(None, None, emit=False)

    def _on_patient_search_text(self, text: str) -> None:
        query = text.strip()
        if not query:
            self._completer_model.setStringList([])
            return
        if query.isdigit():
            try:
                patient = self.patient_service.get_by_id(int(query))
            except Exception:
                self._completer_model.setStringList([])
                return
            self._completer_model.setStringList([f"{patient.id}: {patient.full_name}"])
            return
        if len(query) < 3:
            self._completer_model.setStringList([])
            return
        try:
            patients = self.patient_service.search_by_name(query, limit=10)
        except Exception:
            self._completer_model.setStringList([])
            return
        suggestions = [f"{p.id}: {p.full_name}" for p in patients]
        self._completer_model.setStringList(suggestions)

    def _on_patient_autocomplete(self, text: str) -> None:
        try:
            pid_str, name = text.split(":", 1)
            pid = int(pid_str.strip())
        except Exception:
            return
        self._set_context(patient_id=pid, case_id=None, patient_name=name.strip(), emit=True)

    def _on_case_search_text(self, text: str) -> None:
        if len(text.strip()) < 3:
            self._case_model.setStringList([])
            return
        try:
            cases = self.emz_service.search_cases_meta(text.strip(), limit=10)
        except Exception:
            self._case_model.setStringList([])
            return
        suggestions = [f"{c['id']}: {c['case_no']}" for c in cases]
        self._case_model.setStringList(suggestions)

    def _on_case_autocomplete(self, text: str) -> None:
        try:
            case_id = int(text.split(":", 1)[0].strip())
        except Exception:
            return
        try:
            detail = self.emz_service.get_current(case_id)
            self._set_context(
                patient_id=detail.patient_id,
                case_id=detail.id,
                patient_name=detail.patient_full_name,
                emit=True,
            )
        except Exception as exc:  # noqa: BLE001
            show_error(self, str(exc))

    def _reset(self) -> None:
        self._set_context(None, None, emit=True)

    def _clear_patient(self) -> None:
        self._set_context(None, None, emit=True)

    def _clear_case(self) -> None:
        self._set_context(self.patient_id, None, self.patient_name, emit=True)

    def _restore_last_patient(self) -> None:
        if not self.last_patient_id:
            return
        self._set_context(
            patient_id=self.last_patient_id,
            case_id=None,
            patient_name=self.last_patient_name,
            emit=True,
        )

    # Compatibility for external calls
    def set_context(self, patient_id: int | None, case_id: int | None, patient_name: str = "") -> None:
        self.update_context(patient_id, case_id, patient_name)
