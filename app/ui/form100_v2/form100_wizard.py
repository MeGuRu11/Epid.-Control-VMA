"""Form100Wizard вЂ” QDialog РјР°СЃС‚РµСЂР° Р·Р°РїРѕР»РЅРµРЅРёСЏ Р¤РѕСЂРјС‹ 100 (4 С€Р°РіР°).

Р›РµРІР°СЏ РєРѕР»РѕРЅРєР° (~190 px) вЂ” РёРЅРґРёРєР°С‚РѕСЂ С€Р°РіРѕРІ (Р±РµР¶РµРІР°СЏ С‚РµРјР° РїСЂРѕРµРєС‚Р°).
Р¦РµРЅС‚СЂ (QStackedWidget)  вЂ” 4 С€Р°РіР°.
РќРёР¶РЅСЏСЏ РїР°РЅРµР»СЊ           вЂ” РЅР°РІРёРіР°С†РёСЏ.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100SignV2Request,
    Form100UpdateV2Request,
)
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_bodymap import StepBodymap
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_evacuation import StepEvacuation
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_identification import StepIdentification
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_medical import StepMedical

_STEP_NAMES: tuple[str, ...] = (
    "РРґРµРЅС‚РёС„РёРєР°С†РёСЏ",
    "РџРѕСЂР°Р¶РµРЅРёСЏ",
    "РњРµРґ. РїРѕРјРѕС‰СЊ",
    "Р­РІР°РєСѓР°С†РёСЏ / РС‚РѕРі",
)

# Р‘РµР¶РµРІР°СЏ С‚РµРјР° (РїРѕРґ СЃС‚РёР»СЊ РїСЂРѕРµРєС‚Р°)
_PANEL_BG    = "#EDE8E1"
_DONE_BG     = "#27AE60"
_DONE_TEXT   = "#FFFFFF"
_ACT_BG      = "#8FDCCF"
_ACT_TEXT    = "#3A3A38"
_PEND_BG     = "#EDE8E1"
_PEND_BADGE  = "#D4CEC8"
_PEND_TEXT   = "#7A7A78"
_CONNECTOR   = "#C8C2BC"
_NAV_BAR_BG  = "#FFF9F2"

_STUB_BOOL_KEYS = {
    "stub_transfusion",
    "stub_immobilization",
    "stub_tourniquet",
    "stub_med_help_antibiotic",
    "stub_med_help_serum",
    "stub_med_help_toxoid",
    "stub_med_help_antidote",
    "stub_med_help_analgesic",
    "stub_med_help_transfusion",
    "stub_med_help_immobilization",
    "stub_med_help_tourniquet",
}
_LESION_BOOL_KEYS = {
    "lesion_gunshot",
    "lesion_nuclear",
    "lesion_chemical",
    "lesion_biological",
    "lesion_other",
    "lesion_frostbite",
    "lesion_burn",
    "lesion_misc",
}
_SAN_LOSS_BOOL_KEYS = {
    "san_loss_gunshot",
    "san_loss_nuclear",
    "san_loss_chemical",
    "san_loss_biological",
    "san_loss_other",
    "san_loss_frostbite",
    "san_loss_burn",
    "san_loss_misc",
}
_MP_BOOL_KEYS = {
    "mp_antibiotic",
    "mp_serum_pss",
    "mp_serum_pgs",
    "mp_analgesic",
    "mp_transfusion_blood",
    "mp_transfusion_substitute",
    "mp_immobilization",
    "mp_bandage",
}
_FLAG_BOOL_KEYS = {"flag_emergency", "flag_radiation", "flag_sanitation"}
_BOTTOM_KEYS = {
    "tourniquet_time",
    "sanitation_type",
    "evacuation_dest",
    "evacuation_priority",
    "transport_type",
    "doctor_signature",
    "main_diagnosis",
}


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _bool_to_flag(value: object) -> str:
    return "1" if _as_bool(value) else "0"


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return _bool_to_flag(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_json_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _parse_json_markers(raw: object) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _merge_section(
    target: dict[str, str],
    section: Mapping[str, object],
    *,
    bool_keys: set[str] | None = None,
) -> None:
    bool_keys = bool_keys or set()
    for key, value in section.items():
        key_name = str(key)
        if key_name in bool_keys:
            target[key_name] = _bool_to_flag(value)
        else:
            target[key_name] = _stringify(value)


def _build_wizard_payload(data: Form100DataV2Dto) -> tuple[dict[str, str], list[dict[str, Any]]]:
    payload: dict[str, str] = {
        str(key): _stringify(value)
        for key, value in (data.raw_payload or {}).items()
    }
    _merge_section(payload, data.stub)
    _merge_section(payload, data.main)
    _merge_section(payload, data.lesion, bool_keys=_LESION_BOOL_KEYS | {"isolation_required"})
    _merge_section(payload, data.san_loss, bool_keys=_SAN_LOSS_BOOL_KEYS)
    _merge_section(payload, data.medical_help, bool_keys=_MP_BOOL_KEYS)
    _merge_section(payload, data.bottom)
    _merge_section(payload, data.flags, bool_keys=_FLAG_BOOL_KEYS)

    lesion_selected = [key for key in _LESION_BOOL_KEYS if _as_bool(data.lesion.get(key))]
    san_selected = [key for key in _SAN_LOSS_BOOL_KEYS if _as_bool(data.san_loss.get(key))]
    payload["lesion_json"] = json.dumps(lesion_selected, ensure_ascii=False)
    payload["san_loss_json"] = json.dumps(san_selected, ensure_ascii=False)
    payload["bodymap_tissue_types_json"] = json.dumps(list(data.bodymap_tissue_types or []), ensure_ascii=False)
    payload["bodymap_gender"] = str(data.bodymap_gender or "M")

    markers = [item.model_dump() for item in (data.bodymap_annotations or [])]
    if not markers:
        markers = _parse_json_markers(payload.get("bodymap_annotations_json"))
    payload["bodymap_annotations_json"] = json.dumps(markers, ensure_ascii=False)
    return payload, markers


def _build_structured_data(payload: Mapping[str, str], markers: list[dict[str, Any]]) -> Form100DataV2Dto:
    stub: dict[str, Any] = {
        key: value
        for key, value in payload.items()
        if key.startswith("stub_")
    }
    for key in _STUB_BOOL_KEYS:
        if key in stub:
            stub[key] = _as_bool(stub[key])
    selected_stub_help = _parse_json_list(payload.get("stub_med_help_json"))
    if selected_stub_help:
        stub["stub_med_help_json"] = selected_stub_help
        stub["stub_med_help"] = selected_stub_help
        stub["stub_med_help_underline"] = selected_stub_help

    main: dict[str, Any] = {
        key: value
        for key, value in payload.items()
        if key.startswith("main_") and key != "main_diagnosis"
    }
    lesion: dict[str, Any] = {
        key: _as_bool(payload.get(key))
        for key in _LESION_BOOL_KEYS
        if key in payload
    }
    if "isolation_required" in payload:
        lesion["isolation_required"] = _as_bool(payload.get("isolation_required"))

    san_loss: dict[str, Any] = {
        key: _as_bool(payload.get(key))
        for key in _SAN_LOSS_BOOL_KEYS
        if key in payload
    }

    medical_help: dict[str, Any] = {
        key: (_as_bool(value) if key in _MP_BOOL_KEYS else value)
        for key, value in payload.items()
        if key.startswith("mp_")
    }

    bottom: dict[str, Any] = {
        key: payload.get(key, "")
        for key in _BOTTOM_KEYS
        if key in payload
    }

    flags: dict[str, Any] = {
        key: _as_bool(payload.get(key))
        for key in _FLAG_BOOL_KEYS
        if key in payload
    }

    tissue_types = _parse_json_list(payload.get("bodymap_tissue_types_json"))
    annotations: list[dict[str, Any]] = markers or _parse_json_markers(payload.get("bodymap_annotations_json"))

    bodymap_gender = str(payload.get("bodymap_gender") or "M").upper()
    if bodymap_gender not in {"M", "F"}:
        bodymap_gender = "M"

    return Form100DataV2Dto.model_validate(
        {
            "stub": stub,
            "main": main,
            "lesion": lesion,
            "san_loss": san_loss,
            "bodymap_gender": bodymap_gender,
            "bodymap_annotations": annotations,
            "bodymap_tissue_types": tissue_types,
            "medical_help": medical_help,
            "bottom": bottom,
            "flags": flags,
            "raw_payload": dict(payload),
        }
    )


class Form100Wizard(QDialog):
    """РњР°СЃС‚РµСЂ Р·Р°РїРѕР»РЅРµРЅРёСЏ Р¤РѕСЂРјС‹ 100 вЂ” 4 С€Р°РіР°."""

    def __init__(
        self,
        form100_service: Form100ServiceV2,
        session: SessionContext,
        card: Form100CardV2Dto | None,
        emr_case_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._form100_service = form100_service
        self._session = session
        self._card = card
        self._emr_case_id = emr_case_id
        self._current_step = 0

        title_suffix = f"РљР°СЂС‚РѕС‡РєР° #{card.id[:8]}" if card else "РќРѕРІР°СЏ РєР°СЂС‚РѕС‡РєР°"
        self.setWindowTitle(f"Р¤РѕСЂРјР° 100 вЂ” {title_suffix}")
        self.setMinimumSize(1100, 750)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        # в”Ђв”Ђ РљРѕСЂРЅРµРІРѕР№ layout в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # в”Ђв”Ђ Р›РµРІР°СЏ РїР°РЅРµР»СЊ: РёРЅРґРёРєР°С‚РѕСЂ С€Р°РіРѕРІ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        step_panel = QFrame()
        step_panel.setObjectName("wizardStepPanel")
        step_panel.setFixedWidth(190)
        step_panel.setStyleSheet(
            "#wizardStepPanel {"
            f"  background-color: {_PANEL_BG};"
            "  border-right: 1px solid #D4CEC8;"
            "}"
        )
        sp_lay = QVBoxLayout(step_panel)
        sp_lay.setContentsMargins(16, 28, 16, 20)
        sp_lay.setSpacing(0)

        hdr_title = QLabel("Р¤РѕСЂРјР° 100")
        hdr_title.setStyleSheet(
            "background-color: transparent;"
            " color: #3A3A38; font-size: 14px; font-weight: bold;"
            " letter-spacing: 0.5px;"
        )
        hdr_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        sp_lay.addWidget(hdr_title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {_CONNECTOR}; border: none;")
        sp_lay.addSpacing(14)
        sp_lay.addWidget(sep)
        sp_lay.addSpacing(18)

        self._step_badges: list[QLabel] = []
        self._step_name_labels: list[QLabel] = []

        for i, name in enumerate(_STEP_NAMES):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)

            badge = QLabel(str(i + 1))
            badge.setFixedSize(30, 30)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(
                f"background-color: {_PEND_BADGE}; color: {_PEND_TEXT};"
                " border-radius: 15px; font-weight: bold; font-size: 11px;"
            )
            self._step_badges.append(badge)
            row.addWidget(badge)

            name_lbl = QLabel(name)
            name_lbl.setWordWrap(True)
            name_lbl.setStyleSheet(
                f"background-color: transparent; color: {_PEND_TEXT};"
                " font-size: 12px;"
            )
            name_lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self._step_name_labels.append(name_lbl)
            row.addWidget(name_lbl, 1)

            row_widget = QWidget()
            row_widget.setLayout(row)
            row_widget.setStyleSheet("background-color: transparent;")
            sp_lay.addWidget(row_widget)

            if i < len(_STEP_NAMES) - 1:
                conn_wrap = QWidget()
                conn_wrap.setStyleSheet("background-color: transparent;")
                conn_lay = QHBoxLayout(conn_wrap)
                conn_lay.setContentsMargins(14, 0, 0, 0)
                conn_lay.setSpacing(0)
                conn_line = QFrame()
                conn_line.setFixedWidth(2)
                conn_line.setMinimumHeight(18)
                conn_line.setMaximumHeight(18)
                conn_line.setStyleSheet(f"background-color: {_CONNECTOR}; border: none;")
                conn_lay.addWidget(conn_line)
                conn_lay.addStretch(1)
                sp_lay.addWidget(conn_wrap)

        sp_lay.addStretch(1)

        is_locked = card is not None and card.status == "SIGNED"
        if is_locked:
            lock_lbl = QLabel("РўРѕР»СЊРєРѕ С‡С‚РµРЅРёРµ")
            lock_lbl.setStyleSheet(
                "background-color: transparent; color: #C0392B;"
                " font-size: 11px; padding: 6px 0 0 0;"
            )
            lock_lbl.setWordWrap(True)
            sp_lay.addWidget(lock_lbl)

        outer.addWidget(step_panel)

        # в”Ђв”Ђ РџСЂР°РІР°СЏ С‡Р°СЃС‚СЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        right_frame = QFrame()
        right_lay = QVBoxLayout(right_frame)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        outer.addWidget(right_frame, 1)

        self._stack = QStackedWidget()
        right_lay.addWidget(self._stack, 1)

        # в”Ђв”Ђ РЁР°РіРё в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        self._step1 = StepIdentification()
        self._step2 = StepBodymap()
        self._step3 = StepMedical()
        self._step4 = StepEvacuation()
        self._steps: list[
            StepIdentification | StepBodymap | StepMedical | StepEvacuation
        ] = [self._step1, self._step2, self._step3, self._step4]

        # Р—Р°РіСЂСѓР¶Р°РµРј РґР°РЅРЅС‹Рµ РµСЃР»Рё РєР°СЂС‚РѕС‡РєР° СЃСѓС‰РµСЃС‚РІСѓРµС‚
        if card is not None:
            wizard_payload, markers = _build_wizard_payload(card.data)
        else:
            wizard_payload = {}
            markers = []

        for step in self._steps:
            self._stack.addWidget(step)
            step.set_values(wizard_payload, markers)
            step.set_locked(is_locked)

        card_status = card.status if card is not None else "DRAFT"
        self._step4.set_card_status(card_status)

        # в”Ђв”Ђ РќР°РІРёРіР°С†РёРѕРЅРЅР°СЏ РїР°РЅРµР»СЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
        nav_bar = QFrame()
        nav_bar.setObjectName("wizardNavBar")
        nav_bar.setFixedHeight(56)
        nav_bar.setStyleSheet(
            "#wizardNavBar {"
            f"  background-color: {_NAV_BAR_BG};"
            "  border-top: 1px solid #E0DAD3;"
            "}"
        )
        nav_lay = QHBoxLayout(nav_bar)
        nav_lay.setContentsMargins(20, 8, 20, 8)
        nav_lay.setSpacing(10)

        self._btn_back = QPushButton("в†ђ РќР°Р·Р°Рґ")
        self._btn_back.setObjectName("secondary")
        self._btn_back.setFixedWidth(100)
        self._btn_back.clicked.connect(self._go_back)

        self._btn_next = QPushButton("Р”Р°Р»РµРµ в†’")
        self._btn_next.setFixedWidth(100)
        self._btn_next.clicked.connect(self._go_next)

        self._btn_save = QPushButton("РЎРѕС…СЂР°РЅРёС‚СЊ")
        self._btn_save.setFixedWidth(110)
        self._btn_save.clicked.connect(self._save)
        self._btn_save.setEnabled(not is_locked)

        btn_cancel = QPushButton("РћС‚РјРµРЅР°")
        btn_cancel.setObjectName("ghost")
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(self.reject)

        nav_lay.addWidget(self._btn_back)
        nav_lay.addWidget(self._btn_next)
        nav_lay.addStretch(1)
        nav_lay.addWidget(self._btn_save)
        nav_lay.addWidget(btn_cancel)

        right_lay.addWidget(nav_bar)

        self._step4.btn_sign.clicked.connect(self._sign)

        self._goto_step(0)

    # в”Ђв”Ђ РќР°РІРёРіР°С†РёСЏ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _goto_step(self, idx: int) -> None:
        self._current_step = max(0, min(idx, len(self._steps) - 1))
        if self._current_step == 3:
            payload, markers = self._collect_all()
            self._step4.update_review(payload, markers)
        self._stack.setCurrentIndex(self._current_step)
        self._update_nav()
        self._update_step_indicator()

    def _go_back(self) -> None:
        self._goto_step(self._current_step - 1)

    def _go_next(self) -> None:
        self._goto_step(self._current_step + 1)

    def _update_nav(self) -> None:
        idx = self._current_step
        n = len(self._steps)
        self._btn_back.setEnabled(idx > 0)
        self._btn_next.setVisible(idx < n - 1)

    def _update_step_indicator(self) -> None:
        for i, (badge, name_lbl) in enumerate(
            zip(self._step_badges, self._step_name_labels, strict=False)
        ):
            if i < self._current_step:
                badge.setText("вњ“")
                badge.setStyleSheet(
                    f"background-color: {_DONE_BG}; color: {_DONE_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 12px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_DONE_BG};"
                    " font-size: 12px;"
                )
            elif i == self._current_step:
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    f"background-color: {_ACT_BG}; color: {_ACT_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 12px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_ACT_TEXT};"
                    " font-size: 13px; font-weight: bold;"
                )
            else:
                badge.setText(str(i + 1))
                badge.setStyleSheet(
                    f"background-color: {_PEND_BADGE}; color: {_PEND_TEXT};"
                    " border-radius: 15px; font-weight: bold; font-size: 11px;"
                )
                name_lbl.setStyleSheet(
                    f"background-color: transparent; color: {_PEND_TEXT};"
                    " font-size: 12px;"
                )

    # в”Ђв”Ђ РЎР±РѕСЂ РґР°РЅРЅС‹С… в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _collect_all(self) -> tuple[dict[str, str], list[dict]]:  # type: ignore[type-arg]
        payload: dict[str, str] = {}
        markers: list[dict] = []  # type: ignore[type-arg]
        for step in self._steps:
            p, m = step.collect()
            payload.update(p)
            if m:
                markers = m
        return payload, markers

    # в”Ђв”Ђ РЎРѕС…СЂР°РЅРµРЅРёРµ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _save(self) -> None:
        payload, markers = self._collect_all()
        try:
            self._do_save(payload, markers)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "РћС€РёР±РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ", str(exc))
            return
        self.accept()

    def _do_save(self, payload: dict[str, str], markers: list[dict]) -> Form100CardV2Dto:  # type: ignore[type-arg]
        data = _build_structured_data(payload, markers)
        main_full_name = payload.get("main_full_name") or payload.get("stub_full_name") or ""
        main_unit = payload.get("main_unit") or payload.get("stub_unit") or ""
        main_id_tag = payload.get("main_id_tag") or payload.get("stub_id_tag") or None
        main_diagnosis = payload.get("main_diagnosis") or payload.get("stub_diagnosis") or ""

        if self._card is None:
            request = Form100CreateV2Request(
                emr_case_id=self._emr_case_id,
                main_full_name=main_full_name,
                main_unit=main_unit,
                main_id_tag=main_id_tag,
                main_diagnosis=main_diagnosis,
                data=data,
            )
            saved = self._form100_service.create_card(request, actor_id=self._session.user_id)
            self._card = saved
            self._step4.set_card_status(saved.status)
            return saved

        request_upd = Form100UpdateV2Request(
            emr_case_id=self._emr_case_id,
            main_full_name=main_full_name,
            main_unit=main_unit,
            main_id_tag=main_id_tag,
            main_diagnosis=main_diagnosis,
            data=data,
        )
        saved = self._form100_service.update_card(
            self._card.id,
            request_upd,
            actor_id=self._session.user_id,
            expected_version=self._card.version,
        )
        self._card = saved
        self._step4.set_card_status(saved.status)
        return saved

    # в”Ђв”Ђ РџРѕРґРїРёСЃСЊ в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ

    def _sign(self) -> None:
        signer, ok = QInputDialog.getText(self, "Подпись", "Подписант (разборчиво):")
        if not ok or not signer.strip():
            return

        payload, markers = self._collect_all()
        try:
            saved = self._do_save(payload, markers)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))
            return

        try:
            sign_request = Form100SignV2Request(signed_by=signer.strip())
            signed = self._form100_service.sign_card(
                saved.id,
                sign_request,
                actor_id=self._session.user_id,
                expected_version=saved.version,
            )
            self._card = signed
            self._step4.set_card_status(signed.status)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка подписи", str(exc))
            return
        self.accept()

