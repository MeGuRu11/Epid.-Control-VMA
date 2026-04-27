from __future__ import annotations

import logging
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
    QVBoxLayout,
    QWidget,
)

from app.application.exceptions import AppError
from app.application.services.emz_service import EmzService
from app.application.services.patient_service import PatientService
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import show_error


class ContextBar(QWidget):
    def __init__(
        self,
        emz_service: EmzService,
        patient_service: PatientService,
        on_context_change: Callable[[int | None, int | None], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.emz_service = emz_service
        self.patient_service = patient_service
        self.on_context_change = on_context_change
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
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self._summary_bar = QWidget()
        self._summary_bar.setObjectName("contextCompactRow")
        self._summary_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._summary_bar)
        self._summary_layout.setContentsMargins(0, 0, 0, 0)
        self._summary_layout.setSpacing(8)

        self._title_group = QWidget()
        title_layout = QHBoxLayout(self._title_group)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        context_title = QLabel("Контекст пациента")
        context_title.setObjectName("sectionTitle")
        context_title.setToolTip("Задаёт текущего пациента и госпитализацию для рабочих разделов.")
        title_layout.addWidget(context_title)
        self._title_group.setToolTip(context_title.toolTip())
        self._summary_layout.addWidget(self._title_group)

        self._chips_group = QWidget()
        self._chips_group.setObjectName("contextPinnedChips")
        chips_layout = QHBoxLayout(self._chips_group)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        self._patient_chip = self._build_chip("patientPinnedChip")
        patient_chip_layout = self._patient_chip.layout()
        assert isinstance(patient_chip_layout, QHBoxLayout)
        self.patient_label = QLabel("Пациент не выбран")
        self.patient_label.setObjectName("chipLabel")
        self.patient_label.setToolTip("Текущий закреплённый пациент.")
        self.clear_patient_btn = QPushButton("×")
        self.clear_patient_btn.setObjectName("chipClear")
        self.clear_patient_btn.setToolTip("Очистить пациента и госпитализацию.")
        self.clear_patient_btn.clicked.connect(self._clear_patient)
        patient_chip_layout.addWidget(self.patient_label)
        patient_chip_layout.addWidget(self.clear_patient_btn)
        chips_layout.addWidget(self._patient_chip)

        self._case_chip = self._build_chip("casePinnedChip")
        case_chip_layout = self._case_chip.layout()
        assert isinstance(case_chip_layout, QHBoxLayout)
        self.case_label = QLabel("Госпитализация не выбрана")
        self.case_label.setObjectName("chipLabel")
        self.case_label.setToolTip("Текущая закреплённая госпитализация.")
        self.clear_case_btn = QPushButton("×")
        self.clear_case_btn.setObjectName("chipClear")
        self.clear_case_btn.setToolTip("Очистить только госпитализацию.")
        self.clear_case_btn.clicked.connect(self._clear_case)
        case_chip_layout.addWidget(self.case_label)
        case_chip_layout.addWidget(self.clear_case_btn)
        chips_layout.addWidget(self._case_chip)
        self._summary_layout.addWidget(self._chips_group, stretch=1)

        self._actions_group = QWidget()
        self._actions_group.setObjectName("contextCompactActions")
        actions_layout = QHBoxLayout(self._actions_group)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        self.change_btn = QPushButton("Изменить")
        compact_button(self.change_btn, min_width=86, max_width=128)
        self.change_btn.setToolTip("Показать или скрыть выбор пациента и госпитализации.")
        self.change_btn.clicked.connect(self._toggle_content)
        actions_layout.addWidget(self.change_btn)
        self.last_patient_btn = QPushButton("Последний")
        compact_button(self.last_patient_btn, min_width=86, max_width=128)
        self.last_patient_btn.setToolTip("Вернуть последнего выбранного пациента.")
        self.last_patient_btn.clicked.connect(self._restore_last_patient)
        self.last_patient_btn.setEnabled(False)
        actions_layout.addWidget(self.last_patient_btn)
        self.reset_btn = QPushButton("Сбросить")
        compact_button(self.reset_btn, min_width=86, max_width=128)
        self.reset_btn.setToolTip("Очистить пациента и госпитализацию.")
        self.reset_btn.clicked.connect(self._reset)
        actions_layout.addWidget(self.reset_btn)
        self._summary_layout.addWidget(self._actions_group)
        layout.addWidget(self._summary_bar)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("contextPickerPanel")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 2, 0, 0)
        content_layout.setSpacing(6)

        self._controls_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._controls_row.setSpacing(12)

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
        find_patient_btn = QPushButton("Найти")
        compact_button(find_patient_btn, min_width=74, max_width=104)
        find_patient_btn.setToolTip("Открыть поиск пациента и выбрать нужного.")
        find_patient_btn.clicked.connect(self._find_patient)
        patient_row.addWidget(find_patient_btn)
        patient_block.addLayout(patient_row)
        self._controls_row.addWidget(self._patient_controls_group)

        self._case_controls_group = QWidget()
        case_block = QVBoxLayout(self._case_controls_group)
        case_block.setContentsMargins(0, 0, 0, 0)
        case_block.setSpacing(4)
        case_label = QLabel("Госпитализация")
        case_label.setObjectName("muted")
        case_block.addWidget(case_label)
        case_row = QHBoxLayout()
        self.case_search = QLineEdit()
        self.case_search.setPlaceholderText("Номер истории болезни")
        self.case_search.setToolTip("Введите часть номера истории болезни для поиска.")
        self._case_model = QStringListModel()
        self._case_completer = QCompleter(self._case_model, self)
        self._case_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._case_completer.activated.connect(self._on_case_autocomplete)
        self.case_search.setCompleter(self._case_completer)
        self.case_search.textEdited.connect(self._on_case_search_text)
        case_row.addWidget(self.case_search)
        select_case_btn = QPushButton("Выбрать по ID")
        compact_button(select_case_btn, min_width=112, max_width=144)
        select_case_btn.setToolTip("Введите ID госпитализации вручную.")
        select_case_btn.clicked.connect(self._select_case_by_id)
        case_row.addWidget(select_case_btn)
        case_block.addLayout(case_row)
        self._controls_row.addWidget(self._case_controls_group)
        content_layout.addLayout(self._controls_row)

        self.content_widget.setMaximumHeight(0)
        self.content_widget.setVisible(False)
        self._content_effect = QGraphicsOpacityEffect(self.content_widget)
        self._content_effect.setOpacity(0.0)
        self.content_widget.setGraphicsEffect(self._content_effect)
        layout.addWidget(self.content_widget)
        self._header_height = self.sizeHint().height()
        self._update_chip_states()
        self._update_layout_mode()

    def _build_chip(self, object_name: str) -> QWidget:
        chip = QWidget()
        chip.setObjectName(object_name)
        chip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        chip.setProperty("state", "empty")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(4)
        return chip

    def _toggle_content(self) -> None:
        expanding = not self.content_widget.isVisible()
        if expanding:
            self.content_widget.setVisible(True)
        self.change_btn.setText("Скрыть" if expanding else "Изменить")
        self._animate_content(expanding)

    def _animate_content(self, expanding: bool) -> None:
        target_height = self.content_widget.sizeHint().height()
        start = 0 if expanding else target_height
        end = target_height if expanding else 0
        self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight", self)
        self._anim.setDuration(160)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(lambda: self._on_animation_done(expanding))
        self._anim.valueChanged.connect(lambda _value: self._emit_size_change())
        self._anim.start()
        fade_start = 0.0 if expanding else 1.0
        fade_end = 1.0 if expanding else 0.0
        self._fade_anim = QPropertyAnimation(self._content_effect, b"opacity", self)
        self._fade_anim.setDuration(160)
        self._fade_anim.setStartValue(fade_start)
        self._fade_anim.setEndValue(fade_end)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_anim.start()

    def _on_animation_done(self, expanded: bool) -> None:
        if not expanded:
            self.content_widget.setVisible(False)
            self._content_effect.setOpacity(0.0)
            self.change_btn.setText("Изменить")
        else:
            self._content_effect.setOpacity(1.0)
        self._emit_size_change()

    def set_size_change_callback(self, callback: Callable[[], None] | None) -> None:
        self._on_size_change = callback

    def header_height(self) -> int:
        return self._header_height

    def desired_height(self) -> int:
        return self._header_height + self.content_widget.maximumHeight()

    def _emit_size_change(self) -> None:
        if self._on_size_change:
            self._on_size_change()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_layout_mode()

    def _update_layout_mode(self) -> None:
        update_action_bar_direction(
            self._summary_layout,
            self._summary_bar,
            [self._title_group, self._chips_group, self._actions_group],
            extra_width=18,
        )
        update_action_bar_direction(
            self._controls_row,
            self.content_widget,
            [self._patient_controls_group, self._case_controls_group],
            extra_width=28,
        )

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
        except (LookupError, RuntimeError, ValueError, AppError, TypeError) as exc:
            show_error(self, str(exc))

    def _find_patient(self) -> None:
        query = self.patient_search.text().strip()
        if query.isdigit():
            try:
                patient = self.patient_service.get_by_id(int(query))
            except (LookupError, RuntimeError, ValueError, AppError, TypeError) as exc:
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
        self.patient_label.setText(self._format_patient_label(patient_id, patient_name))
        self.case_label.setText(self._format_case_label(case_id))
        self._update_chip_states()
        if patient_id:
            self.last_patient_id = patient_id
            self.last_patient_name = patient_name
            self.last_patient_btn.setEnabled(True)
        if emit:
            self.on_context_change(patient_id, case_id)

    def _format_patient_label(self, patient_id: int | None, patient_name: str) -> str:
        if patient_id is None:
            return "Пациент не выбран"
        suffix = f" {patient_name}" if patient_name else ""
        return f"Пациент: {patient_id}{suffix}"

    def _format_case_label(self, case_id: int | None) -> str:
        if case_id is None:
            return "Госпитализация не выбрана"
        return f"Госпитализация: {case_id}"

    def _update_chip_states(self) -> None:
        self._set_chip_state(self._patient_chip, "selected" if self.patient_id is not None else "empty")
        self._set_chip_state(self._case_chip, "selected" if self.case_id is not None else "empty")

    def _set_chip_state(self, chip: QWidget, state: str) -> None:
        chip.setProperty("state", state)
        style = chip.style()
        style.unpolish(chip)
        style.polish(chip)
        chip.update()

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
            except (LookupError, RuntimeError, ValueError) as exc:
                logging.getLogger(__name__).debug("Autocomplete lookup by patient id failed: %s", exc)
                self._completer_model.setStringList([])
                return
            self._completer_model.setStringList([f"{patient.id}: {patient.full_name}"])
            return
        if len(query) < 3:
            self._completer_model.setStringList([])
            return
        try:
            patients = self.patient_service.search_by_name(query, limit=10)
        except (LookupError, RuntimeError, ValueError) as exc:
            logging.getLogger(__name__).debug("Autocomplete lookup by patient name failed: %s", exc)
            self._completer_model.setStringList([])
            return
        suggestions = [f"{p.id}: {p.full_name}" for p in patients]
        self._completer_model.setStringList(suggestions)

    def _on_patient_autocomplete(self, text: str) -> None:
        try:
            pid_str, name = text.split(":", 1)
            pid = int(pid_str.strip())
        except ValueError:
            return
        self._set_context(patient_id=pid, case_id=None, patient_name=name.strip(), emit=True)

    def _on_case_search_text(self, text: str) -> None:
        if len(text.strip()) < 3:
            self._case_model.setStringList([])
            return
        try:
            cases = self.emz_service.search_cases_meta(text.strip(), limit=10)
        except (LookupError, RuntimeError, ValueError) as exc:
            logging.getLogger(__name__).debug("Autocomplete lookup by case number failed: %s", exc)
            self._case_model.setStringList([])
            return
        suggestions = [f"{c['id']}: {c['case_no']}" for c in cases]
        self._case_model.setStringList(suggestions)

    def _on_case_autocomplete(self, text: str) -> None:
        try:
            case_id = int(text.split(":", 1)[0].strip())
        except ValueError:
            return
        try:
            detail = self.emz_service.get_current(case_id)
            self._set_context(
                patient_id=detail.patient_id,
                case_id=detail.id,
                patient_name=detail.patient_full_name,
                emit=True,
            )
        except (LookupError, RuntimeError, ValueError, AppError, TypeError) as exc:
            show_error(self, str(exc))

    def _reset(self) -> None:
        self.patient_search.clear()
        self.case_search.clear()
        self._completer_model.setStringList([])
        self._case_model.setStringList([])
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
