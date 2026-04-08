from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.exceptions import AppError
from app.application.security import can_manage_references
from app.application.services.reference_service import ReferenceService
from app.ui.widgets.action_bar_layout import update_action_bar_direction
from app.ui.widgets.button_utils import compact_button
from app.ui.widgets.notifications import error_text, show_error

_HANDLED_REFERENCE_ERRORS = (ValueError, RuntimeError, LookupError, TypeError, AppError)


class ReferenceView(QWidget):
    references_updated = Signal()

    def __init__(
        self,
        reference_service: ReferenceService,
        session: SessionContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.reference_service = reference_service
        self.session = session
        self._current_type: str = "departments"
        self._current_id: Any | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._abx_group_map: dict[int, str] = {}
        self._build_ui()
        self._apply_role_policy()
        self.refresh()

    def set_session(self, session: SessionContext) -> None:
        self.session = session
        self._apply_role_policy()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        title = QLabel("РЎРїСЂР°РІРѕС‡РЅРёРєРё")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        main_layout.addLayout(header)

        self.role_hint = QLabel("Р РµРґР°РєС‚РёСЂРѕРІР°РЅРёРµ РґРѕСЃС‚СѓРїРЅРѕ С‚РѕР»СЊРєРѕ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ")
        self.role_hint.setObjectName("muted")
        main_layout.addWidget(self.role_hint)

        self._controls_bar = QWidget()
        self._controls_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._controls_bar)
        self._controls_layout.setContentsMargins(0, 0, 0, 0)
        self._controls_layout.setSpacing(8)

        self._controls_main_group = QWidget()
        controls_main = QHBoxLayout(self._controls_main_group)
        controls_main.setContentsMargins(0, 0, 0, 0)
        controls_main.setSpacing(8)
        self.type_selector = QComboBox()
        self.type_selector.addItem("РћС‚РґРµР»РµРЅРёСЏ", "departments")
        self.type_selector.addItem("РўРёРїС‹ РјР°С‚РµСЂРёР°Р»РѕРІ", "material_types")
        self.type_selector.addItem("РњРљР‘-10", "icd10")
        self.type_selector.addItem("РђРЅС‚РёР±РёРѕС‚РёРєРё", "antibiotics")
        self.type_selector.addItem("Р“СЂСѓРїРїС‹ Р°РЅС‚РёР±РёРѕС‚РёРєРѕРІ", "antibiotic_groups")
        self.type_selector.addItem("РњРёРєСЂРѕРѕСЂРіР°РЅРёР·РјС‹", "microorganisms")
        self.type_selector.addItem("Р¤Р°РіРё", "phages")
        self.type_selector.addItem("РРЎРњРџ (СЃРѕРєСЂР°С‰РµРЅРёСЏ)", "ismp_abbrev")
        self.type_selector.currentIndexChanged.connect(self._on_type_changed)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("РџРѕРёСЃРє")
        self.search_input.textChanged.connect(self.refresh)
        self._clear_search_btn = QPushButton("РЎР±СЂРѕСЃРёС‚СЊ")
        compact_button(self._clear_search_btn)
        self._clear_search_btn.clicked.connect(self._clear_search)

        controls_main.addWidget(QLabel("РўРёРї СЃРїСЂР°РІРѕС‡РЅРёРєР°"))
        controls_main.addWidget(self.type_selector)
        controls_main.addWidget(self.search_input)

        self._controls_action_group = QWidget()
        controls_action = QHBoxLayout(self._controls_action_group)
        controls_action.setContentsMargins(0, 0, 0, 0)
        controls_action.setSpacing(8)
        controls_action.addWidget(self._clear_search_btn)

        self._controls_layout.addWidget(self._controls_main_group)
        self._controls_layout.addStretch()
        self._controls_layout.addWidget(self._controls_action_group)
        main_layout.addWidget(self._controls_bar)

        self._content_container = QWidget()
        self._content_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        self.list_box = QListWidget()
        self.list_box.setAlternatingRowColors(True)
        self.list_box.setSpacing(2)
        self.list_box.itemClicked.connect(self._on_item_selected)
        self.list_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._content_layout.addWidget(self.list_box, 2)

        self.form_box = QGroupBox("Р”Р°РЅРЅС‹Рµ")
        self.form_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form_layout = QVBoxLayout(self.form_box)
        self.form_fields = QFormLayout()
        form_layout.addLayout(self.form_fields)

        self.add_btn = QPushButton("Р”РѕР±Р°РІРёС‚СЊ")
        compact_button(self.add_btn)
        self.add_btn.clicked.connect(self._add_item)
        self.save_btn = QPushButton("РЎРѕС…СЂР°РЅРёС‚СЊ")
        self.save_btn.setObjectName("primaryButton")
        compact_button(self.save_btn)
        self.save_btn.clicked.connect(self._update_item)
        self.delete_btn = QPushButton("РЈРґР°Р»РёС‚СЊ")
        self.delete_btn.setObjectName("secondaryButton")
        compact_button(self.delete_btn)
        self.delete_btn.clicked.connect(self._delete_item)
        self.clear_btn = QPushButton("РћС‡РёСЃС‚РёС‚СЊ")
        self.clear_btn.setObjectName("secondaryButton")
        compact_button(self.clear_btn)
        self.clear_btn.clicked.connect(self._clear_form)
        self._form_actions_bar = QWidget()
        self._form_actions_bar.setObjectName("sectionActionBar")
        self._form_actions_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._form_actions_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, self._form_actions_bar)
        self._form_actions_layout.setContentsMargins(12, 8, 12, 8)
        self._form_actions_layout.setSpacing(10)

        self._form_edit_group = QWidget()
        self._form_edit_group.setObjectName("sectionActionGroup")
        self._form_edit_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        form_edit_layout = QHBoxLayout(self._form_edit_group)
        form_edit_layout.setContentsMargins(0, 0, 0, 0)
        form_edit_layout.setSpacing(8)
        form_edit_layout.addWidget(self.add_btn)
        form_edit_layout.addWidget(self.save_btn)

        self._form_cleanup_group = QWidget()
        self._form_cleanup_group.setObjectName("sectionActionGroup")
        self._form_cleanup_group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        form_cleanup_layout = QHBoxLayout(self._form_cleanup_group)
        form_cleanup_layout.setContentsMargins(0, 0, 0, 0)
        form_cleanup_layout.setSpacing(8)
        form_cleanup_layout.addWidget(self.delete_btn)
        form_cleanup_layout.addWidget(self.clear_btn)

        self._form_actions_layout.addWidget(self._form_edit_group)
        self._form_actions_layout.addStretch()
        self._form_actions_layout.addWidget(self._form_cleanup_group)
        form_layout.addStretch(1)
        form_layout.addWidget(self._form_actions_bar)

        self._content_layout.addWidget(self.form_box, 5)
        main_layout.addWidget(self._content_container, 1)

        self._admin_widgets = [self.add_btn, self.save_btn, self.delete_btn]
        self._build_form_fields()
        self._update_controls_layout()
        self._update_content_layout()
        self._update_form_actions_layout()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_controls_layout"):
            self._update_controls_layout()
        if hasattr(self, "_content_layout"):
            self._update_content_layout()
        if hasattr(self, "_form_actions_layout"):
            self._update_form_actions_layout()

    def _update_controls_layout(self) -> None:
        update_action_bar_direction(
            self._controls_layout,
            self._controls_bar,
            [self._controls_main_group, self._controls_action_group],
        )

    def _update_content_layout(self) -> None:
        width = max(1, self._content_container.width())
        list_required = max(360, self.list_box.sizeHint().width())
        form_required = max(560, self.form_box.sizeHint().width())
        needed = list_required + form_required + self._content_layout.spacing() + 40
        target = (
            QBoxLayout.Direction.LeftToRight
            if width >= max(1260, needed)
            else QBoxLayout.Direction.TopToBottom
        )
        if self._content_layout.direction() != target:
            self._content_layout.setDirection(target)

        if target == QBoxLayout.Direction.LeftToRight:
            self.list_box.setMinimumWidth(320)
            self.list_box.setMinimumHeight(0)
            self.form_box.setMinimumWidth(560)
            self._content_layout.setStretch(0, 2)
            self._content_layout.setStretch(1, 5)
        else:
            self.list_box.setMinimumWidth(0)
            self.list_box.setMinimumHeight(220)
            self.form_box.setMinimumWidth(0)
            self._content_layout.setStretch(0, 0)
            self._content_layout.setStretch(1, 0)

    def _update_form_actions_layout(self) -> None:
        update_action_bar_direction(
            self._form_actions_layout,
            self._form_actions_bar,
            [self._form_edit_group, self._form_cleanup_group],
        )

    def _apply_role_policy(self) -> None:
        is_admin = can_manage_references(self.session.role)
        self.role_hint.setVisible(not is_admin)
        for widget in self._admin_widgets:
            widget.setEnabled(is_admin)
        for field_widget in self._field_widgets.values():
            field_widget.setEnabled(is_admin)

    def _clear_search(self) -> None:
        self.search_input.clear()
        self.refresh()

    def _on_type_changed(self) -> None:
        self._current_type = str(self.type_selector.currentData())
        self._current_id = None
        self._build_form_fields()
        self.refresh()

    def _build_form_fields(self) -> None:
        while self.form_fields.rowCount():
            self.form_fields.removeRow(0)
        self._field_widgets = {}
        for field_key, label, widget_factory in self._get_field_config():
            widget = widget_factory()
            self._field_widgets[field_key] = widget
            self.form_fields.addRow(label, widget)
            if isinstance(widget, QLineEdit):
                widget.setPlaceholderText(label)
        self._clear_form()
        self._apply_role_policy()

    def _get_field_config(self) -> list[tuple[str, str, Callable[[], QWidget]]]:
        if self._current_type == "departments":
            return [("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit)]
        if self._current_type == "material_types":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
            ]
        if self._current_type == "icd10":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("title", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
            ]
        if self._current_type == "antibiotics":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
                ("group_id", "Р“СЂСѓРїРїР°", self._create_abx_group_combo),
            ]
        if self._current_type == "antibiotic_groups":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
            ]
        if self._current_type == "microorganisms":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
                ("taxon_group", "Р“СЂСѓРїРїР°", QLineEdit),
            ]
        if self._current_type == "ismp_abbrev":
            return [
                ("code", "РљРѕРґ", QLineEdit),
                ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
                ("description", "РћРїРёСЃР°РЅРёРµ", QLineEdit),
            ]
        return [
            ("code", "РљРѕРґ", QLineEdit),
            ("name", "РќР°Р·РІР°РЅРёРµ", QLineEdit),
        ]

    def _create_abx_group_combo(self) -> QWidget:
        combo = QComboBox()
        combo.addItem("Р’С‹Р±СЂР°С‚СЊ", None)
        for group in self.reference_service.list_antibiotic_groups():
            combo.addItem(f"{group.code or '-'} - {group.name}", group.id)
        return combo

    def _build_list_data(self) -> list[tuple[str, Any, dict[str, Any]]]:
        if self._current_type == "departments":
            return [
                (str(item.name), item.id, {"name": item.name})
                for item in self.reference_service.list_departments()
            ]
        if self._current_type == "material_types":
            return [
                (f"{item.code} - {item.name}", item.id, {"code": item.code, "name": item.name})
                for item in self.reference_service.list_material_types()
            ]
        if self._current_type == "icd10":
            return [
                (f"{item.code} - {item.title}", item.code, {"code": item.code, "title": item.title})
                for item in self.reference_service.list_icd10()
            ]
        if self._current_type == "antibiotics":
            self._abx_group_map = {
                cast(int, group.id): str(group.name)
                for group in self.reference_service.list_antibiotic_groups()
                if group.id is not None
            }
            return [
                (
                    f"{item.code} - {item.name}"
                    + (
                        f" ({self._abx_group_map.get(cast(int, item.group_id), '-')})"
                        if item.group_id is not None
                        else ""
                    ),
                    item.id,
                    {"code": item.code, "name": item.name, "group_id": item.group_id},
                )
                for item in self.reference_service.list_antibiotics()
            ]
        if self._current_type == "antibiotic_groups":
            return [
                (
                    f"{item.code or '-'} - {item.name}",
                    item.id,
                    {"code": item.code or "", "name": item.name},
                )
                for item in self.reference_service.list_antibiotic_groups()
            ]
        if self._current_type == "microorganisms":
            return [
                (
                    f"{item.code or '-'} - {item.name}",
                    item.id,
                    {"code": item.code or "", "name": item.name, "taxon_group": item.taxon_group or ""},
                )
                for item in self.reference_service.list_microorganisms()
            ]
        if self._current_type == "ismp_abbrev":
            return [
                (
                    f"{item.code} - {item.name}",
                    item.id,
                    {"code": item.code, "name": item.name, "description": item.description or ""},
                )
                for item in self.reference_service.list_ismp_abbreviations()
            ]
        return [
            (
                f"{item.code or '-'} - {item.name}",
                item.id,
                {"code": item.code or "", "name": item.name},
            )
            for item in self.reference_service.list_phages()
        ]

    def refresh(self) -> None:
        self.list_box.clear()
        query = self.search_input.text().strip()
        if self._current_type == "icd10":
            icd_items = (
                self.reference_service.search_icd10(query, limit=200)
                if query
                else self.reference_service.list_icd10()
            )
            for icd in icd_items:
                label = f"{icd.code} - {icd.title}"
                icd_data = {"code": icd.code, "title": icd.title}
                list_item = QListWidgetItem(label)
                list_item.setData(Qt.ItemDataRole.UserRole, {"id": icd.code, "data": icd_data})
                self.list_box.addItem(list_item)
        elif self._current_type == "microorganisms":
            micro_items = (
                self.reference_service.search_microorganisms(query, limit=200)
                if query
                else self.reference_service.list_microorganisms()
            )
            for micro in micro_items:
                label = f"{micro.code or '-'} - {micro.name}"
                micro_data = {
                    "code": str(micro.code or ""),
                    "name": micro.name,
                    "taxon_group": str(micro.taxon_group or ""),
                }
                list_item = QListWidgetItem(label)
                list_item.setData(Qt.ItemDataRole.UserRole, {"id": micro.id, "data": micro_data})
                self.list_box.addItem(list_item)
        else:
            query_lower = query.lower()
            for label, obj_id, data in self._build_list_data():
                if query_lower and query_lower not in label.lower():
                    continue
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, {"id": obj_id, "data": data})
                self.list_box.addItem(item)
        self.references_updated.emit()

    def showEvent(self, event) -> None:  # noqa: D401, N802
        super().showEvent(event)
        self.refresh()

    def _on_item_selected(self, item: QListWidgetItem) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole) or {}
        self._current_id = payload.get("id")
        data = payload.get("data", {})
        for key, widget in self._field_widgets.items():
            if isinstance(widget, QLineEdit):
                widget.setText(str(data.get(key, "")))
            elif isinstance(widget, QComboBox):
                idx = widget.findData(data.get(key))
                widget.setCurrentIndex(idx if idx >= 0 else 0)
        if self._current_type == "icd10":
            code_widget = self._field_widgets.get("code")
            if isinstance(code_widget, QLineEdit):
                code_widget.setReadOnly(True)

    def _collect_form(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key, widget in self._field_widgets.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text().strip()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentData()
        return values

    def _clear_form(self) -> None:
        self._current_id = None
        for widget in self._field_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
                widget.setReadOnly(False)
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)

    def _add_item(self) -> None:
        try:
            data = self._collect_form()
            if self._current_type == "departments":
                self.reference_service.add_department(data["name"], actor_id=self.session.user_id)
            elif self._current_type == "material_types":
                self.reference_service.add_material_type(
                    data["code"], data["name"], actor_id=self.session.user_id
                )
            elif self._current_type == "icd10":
                self.reference_service.add_icd10(data["code"], data["title"], actor_id=self.session.user_id)
            elif self._current_type == "antibiotics":
                self.reference_service.add_antibiotic(
                    data["code"],
                    data["name"],
                    data["group_id"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "antibiotic_groups":
                self.reference_service.add_antibiotic_group(
                    data["code"] or None,
                    data["name"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "microorganisms":
                self.reference_service.add_microorganism(
                    data["code"] or None,
                    data["name"],
                    data.get("taxon_group") or None,
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "ismp_abbrev":
                self.reference_service.add_ismp_abbreviation(
                    data["code"],
                    data["name"],
                    data.get("description") or None,
                    actor_id=self.session.user_id,
                )
            else:
                self.reference_service.add_phage(
                    data["code"] or None,
                    data["name"],
                    actor_id=self.session.user_id,
                )
            self._clear_form()
            self.refresh()
        except _HANDLED_REFERENCE_ERRORS as exc:
            show_error(self, error_text(exc, "РќРµ СѓРґР°Р»РѕСЃСЊ РґРѕР±Р°РІРёС‚СЊ Р·Р°РїРёСЃСЊ"))

    def _update_item(self) -> None:
        if self._current_id is None:
            show_error(self, "Р’С‹Р±РµСЂРёС‚Рµ Р·Р°РїРёСЃСЊ РґР»СЏ РёР·РјРµРЅРµРЅРёСЏ.")
            return
        try:
            data = self._collect_form()
            if self._current_type == "departments":
                self.reference_service.update_department(
                    self._current_id,
                    data["name"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "material_types":
                self.reference_service.update_material_type(
                    self._current_id,
                    data["code"],
                    data["name"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "icd10":
                self.reference_service.update_icd10(
                    data["code"],
                    data["title"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "antibiotics":
                self.reference_service.update_antibiotic(
                    self._current_id,
                    data["code"],
                    data["name"],
                    data["group_id"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "antibiotic_groups":
                self.reference_service.update_antibiotic_group(
                    self._current_id,
                    data["code"] or None,
                    data["name"],
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "microorganisms":
                self.reference_service.update_microorganism(
                    self._current_id,
                    data["code"] or None,
                    data["name"],
                    data.get("taxon_group") or None,
                    actor_id=self.session.user_id,
                )
            elif self._current_type == "ismp_abbrev":
                self.reference_service.update_ismp_abbreviation(
                    self._current_id,
                    data["code"],
                    data["name"],
                    data.get("description") or None,
                    actor_id=self.session.user_id,
                )
            else:
                self.reference_service.update_phage(
                    self._current_id,
                    data["code"] or None,
                    data["name"],
                    True,
                    actor_id=self.session.user_id,
                )
            self.refresh()
        except _HANDLED_REFERENCE_ERRORS as exc:
            show_error(self, error_text(exc, "РќРµ СѓРґР°Р»РѕСЃСЊ РѕР±РЅРѕРІРёС‚СЊ Р·Р°РїРёСЃСЊ"))

    def _delete_item(self) -> None:
        if self._current_id is None:
            show_error(self, "Р’С‹Р±РµСЂРёС‚Рµ Р·Р°РїРёСЃСЊ РґР»СЏ СѓРґР°Р»РµРЅРёСЏ.")
            return
        try:
            if self._current_type == "departments":
                self.reference_service.delete_department(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "material_types":
                self.reference_service.delete_material_type(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "icd10":
                self.reference_service.delete_icd10(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "antibiotics":
                self.reference_service.delete_antibiotic(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "antibiotic_groups":
                self.reference_service.delete_antibiotic_group(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "microorganisms":
                self.reference_service.delete_microorganism(self._current_id, actor_id=self.session.user_id)
            elif self._current_type == "ismp_abbrev":
                self.reference_service.delete_ismp_abbreviation(self._current_id, actor_id=self.session.user_id)
            else:
                self.reference_service.delete_phage(self._current_id, actor_id=self.session.user_id)
            self._clear_form()
            self.refresh()
        except _HANDLED_REFERENCE_ERRORS as exc:
            show_error(self, error_text(exc, "РќРµ СѓРґР°Р»РѕСЃСЊ СѓРґР°Р»РёС‚СЊ Р·Р°РїРёСЃСЊ"))


