from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

if TYPE_CHECKING:
    from app.application.dto.analytics_dto import AnalyticsSearchRequest


class QuickFilterChip(QPushButton):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setObjectName("quickFilterChip")


class QuickFilterChips(QWidget):
    """Быстрые фильтры для вкладки микробиологии."""

    filter_changed = Signal(object)

    _CHIPS: list[tuple[str, dict[str, Any]]] = [
        ("Только положительные", {"growth_flag": 1}),
        ("Только из крови", {"material_type_name": "кровь"}),
        ("Только из ран", {"material_type_name": "рана"}),
    ]

    def __init__(
        self,
        base_request_getter: Callable[[], AnalyticsSearchRequest | None],
        material_type_ids: dict[str, int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_base = base_request_getter
        self._material_type_ids = {key.lower(): value for key, value in (material_type_ids or {}).items()}
        self._chips: list[QuickFilterChip] = []
        self._material_chip_indices = [
            index for index, (_label, overrides) in enumerate(self._CHIPS) if "material_type_name" in overrides
        ]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        for label, _overrides in self._CHIPS:
            chip = QuickFilterChip(label)
            chip.toggled.connect(self._on_toggled)
            layout.addWidget(chip)
            self._chips.append(chip)

        layout.addStretch()

    def reset(self) -> None:
        for chip in self._chips:
            blocker = QSignalBlocker(chip)
            chip.setChecked(False)
            del blocker

    def _on_toggled(self, _checked: bool) -> None:
        sender = self.sender()
        if isinstance(sender, QuickFilterChip):
            sender_idx = self._chips.index(sender)
            if sender_idx in self._material_chip_indices and sender.isChecked():
                for idx in self._material_chip_indices:
                    if idx == sender_idx:
                        continue
                    blocker = QSignalBlocker(self._chips[idx])
                    self._chips[idx].setChecked(False)
                    del blocker

        request = self._get_base()
        if request is None:
            return

        updates: dict[str, object] = {}
        has_growth_chip = False
        has_material_chip = False

        for chip, (_label, overrides) in zip(self._chips, self._CHIPS, strict=True):
            if not chip.isChecked():
                continue
            if "growth_flag" in overrides:
                updates["growth_flag"] = overrides["growth_flag"]
                has_growth_chip = True
            material_name = overrides.get("material_type_name")
            if isinstance(material_name, str):
                material_id = self._resolve_material_type_id(material_name)
                if material_id is not None:
                    updates["material_type_id"] = material_id
                    has_material_chip = True

        if not has_growth_chip:
            updates["growth_flag"] = None
        if not has_material_chip:
            updates["material_type_id"] = None

        request = request.model_copy(update=updates)
        self.filter_changed.emit(request)

    def _resolve_material_type_id(self, label: str) -> int | None:
        needle = label.lower()
        if needle in self._material_type_ids:
            return self._material_type_ids[needle]
        for name, material_type_id in self._material_type_ids.items():
            if needle in name:
                return material_type_id
        return None
