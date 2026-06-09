from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QLabel, QLayout, QWidget

from app.application.dto.form100_v2_dto import Form100CardV2Dto
from app.ui.form100_v2.form100_editor import Form100EditorV2
from app.ui.form100_v2.signing_errors import FORM100_SIGNING_FIELD_LABELS
from app.ui.form100_v2.wizard_widgets.form100_bottom_widget import Form100BottomWidget
from app.ui.form100_v2.wizard_widgets.form100_main_widget import Form100MainWidget
from app.ui.form100_v2.wizard_widgets.form100_stub_widget import Form100StubWidget
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_bodymap import StepBodymap
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_identification import StepIdentification
from app.ui.form100_v2.wizard_widgets.wizard_steps.step_medical import StepMedical

_REQUIRED_HINT_TEXT = "Обязательные поля отмечены *."


def _label_texts(widget: QWidget) -> set[str]:
    return set(_label_text_list(widget))


def _label_text_list(widget: QWidget) -> list[str]:
    labels = cast(list[QLabel], widget.findChildren(QLabel))
    return [label.text() for label in labels]


def _group_titles(editor: Form100EditorV2) -> set[str]:
    groups = cast(list[QGroupBox], editor.findChildren(QGroupBox))
    return {group.title() for group in groups}


def _checkbox_texts(editor: Form100EditorV2) -> set[str]:
    checkboxes = cast(list[QCheckBox], editor.findChildren(QCheckBox))
    return {checkbox.text() for checkbox in checkboxes}


def _iter_layouts(layout: QLayout | None) -> list[QLayout]:
    if layout is None:
        return []
    layouts = [layout]
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is None:
            continue
        child_layout = item.layout()
        if child_layout is not None:
            layouts.extend(_iter_layouts(child_layout))
        child_widget = item.widget()
        if child_widget is not None:
            layouts.extend(_iter_layouts(child_widget.layout()))
    return layouts


def _form_label_for_field(root: QWidget, field: QWidget) -> str:
    for layout in _iter_layouts(root.layout()):
        if not isinstance(layout, QFormLayout):
            continue
        label = layout.labelForField(field)
        if isinstance(label, QLabel):
            return label.text()
    raise AssertionError(f"label for field {field.objectName() or field.__class__.__name__} not found")


def test_form100_v2_editor_marks_signing_required_fields(qapp) -> None:
    editor = Form100EditorV2()

    assert {
        "ФИО *",
        "Подразделение *",
        "Дата рождения *",
        "В/звание *",
        "Дата ранения *",
        "Время ранения *",
        "Очередность *",
        "Диагноз *",
    }.issubset(_label_texts(editor))
    assert {"Вид поражения *", "Вид санитарных потерь *"}.issubset(_group_titles(editor))
    assert {"Антибиотик *", "Обезболивание *"}.issubset(_checkbox_texts(editor))
    assert "signed_by" in FORM100_SIGNING_FIELD_LABELS


def test_form100_v2_required_hint_is_shown_where_required_marks_are_visible(qapp) -> None:
    widgets = [
        Form100EditorV2(),
        Form100StubWidget(),
        Form100MainWidget(),
        Form100BottomWidget(),
        StepIdentification(),
        StepBodymap(),
        StepMedical(),
    ]

    try:
        for widget in widgets:
            assert _label_text_list(widget).count(_REQUIRED_HINT_TEXT) == 1
    finally:
        for widget in widgets:
            widget.close()


def test_form100_stub_marks_full_name_as_signing_required(qapp) -> None:
    widget = Form100StubWidget()
    try:
        label_texts = _label_text_list(widget)
        assert "ФИО *" in label_texts
        assert "ФИО" not in label_texts
    finally:
        widget.close()


def test_form100_stub_full_name_required_mark_is_bound_to_stub_field(qapp) -> None:
    editor = Form100EditorV2()
    stub = Form100StubWidget()
    step = StepIdentification()
    try:
        assert _form_label_for_field(editor, editor.stub_full_name) == "ФИО *"
        assert _form_label_for_field(stub, stub.stub_full_name) == "ФИО *"
        assert _form_label_for_field(step._stub, step._stub.stub_full_name) == "ФИО *"
    finally:
        editor.close()
        stub.close()
        step.close()


def test_form100_v2_editor_builds_extended_stub_and_main_payload(qapp) -> None:
    editor = Form100EditorV2()

    assert [editor.stub_evac_method.itemText(idx) for idx in range(editor.stub_evac_method.count())] == [
        "Самолётом",
        "Сан. груз. авто.",
    ]

    editor.stub_issued_date.setDate(QDate(2026, 2, 18))
    editor.stub_issued_time.setTime(QTime(8, 15))
    editor.stub_injury_date.setDate(QDate(2026, 2, 17))
    editor.stub_injury_time.setTime(QTime(7, 45))
    editor.stub_pss_pgs_dose.setText("5 мл")
    editor.stub_toxoid_type.setText("АДС-М")
    editor.stub_antidote_type.setText("Атропин")
    editor.stub_med_help_checks["Введено: антибиотик"].setChecked(True)

    editor.main_full_name.setText("Иванов Иван")
    editor.main_unit.setText("1 рота")
    editor.main_issued_date.setDate(QDate(2026, 2, 18))
    editor.main_issued_time.setTime(QTime(8, 0))
    editor.main_injury_date.setDate(QDate(2026, 2, 17))
    editor.main_injury_time.setTime(QTime(7, 30))
    editor.main_diagnosis.setPlainText("Огнестрельное ранение")
    editor.mp_serum_pss.setChecked(True)
    editor.mp_serum_pss_details.setText("ПСС 3000 МЕ")
    editor.mp_transfusion_blood.setChecked(True)
    editor.mp_transfusion_blood_details.setText("эритроцитарная масса 250 мл")
    editor.mp_immobilization.setChecked(True)
    editor.mp_immobilization_details.setText("шина Крамера")
    editor.mp_surgical_intervention.setChecked(True)
    editor.mp_surgical_intervention_details.setText("ПХО раны")

    payload = editor._build_data_payload()

    assert payload["stub"]["stub_issued_date"] == "18.02.2026"
    assert payload["stub"]["stub_issued_time"] == "08:15"
    assert payload["stub"]["stub_pss_pgs_dose"] == "5 мл"
    assert payload["stub"]["stub_toxoid_type"] == "АДС-М"
    assert payload["stub"]["stub_antidote_type"] == "Атропин"
    assert payload["stub"]["stub_med_help_underline"] == ["Введено: антибиотик"]
    assert payload["stub"]["stub_med_help"] == ["Введено: антибиотик"]
    assert payload["main"]["main_issued_date"] == "18.02.2026"
    assert payload["main"]["main_issued_time"] == "08:00"
    assert payload["main"]["main_injury_date"] == "17.02.2026"
    assert payload["main"]["main_injury_time"] == "07:30"
    assert payload["medical_help"]["mp_serum_pss"] is True
    assert payload["medical_help"]["mp_serum_dose"] == "ПСС 3000 МЕ"
    assert payload["medical_help"]["mp_serum_pss_details"] == "ПСС 3000 МЕ"
    assert payload["medical_help"]["mp_transfusion_blood"] is True
    assert payload["medical_help"]["mp_transfusion_blood_details"] == "эритроцитарная масса 250 мл"
    assert payload["medical_help"]["mp_immobilization"] is True
    assert payload["medical_help"]["mp_immobilization_details"] == "шина Крамера"
    assert payload["medical_help"]["mp_surgical_intervention"] is True
    assert payload["medical_help"]["mp_surgical_intervention_details"] == "ПХО раны"


def test_form100_v2_editor_empty_optional_dates_do_not_store_sentinel(qapp) -> None:
    editor = Form100EditorV2()

    payload = editor._build_data_payload()
    create_request = editor.build_create_request()
    update_request = editor.build_update_request()

    assert payload["stub"]["stub_issued_date"] == ""
    assert payload["stub"]["stub_injury_date"] == ""
    assert payload["main"]["main_issued_date"] == ""
    assert payload["main"]["main_injury_date"] == ""
    assert payload["main"]["birth_date"] == ""
    assert create_request.birth_date is None
    assert update_request.birth_date is None


def test_form100_v2_editor_loads_extended_stub_and_main_fields(qapp) -> None:
    editor = Form100EditorV2()
    now = datetime(2026, 2, 18, 12, 0, tzinfo=UTC)
    card = Form100CardV2Dto.model_validate(
        {
            "id": "CARD-1",
            "legacy_card_id": None,
            "emr_case_id": None,
            "created_at": now,
            "created_by": "admin",
            "updated_at": now,
            "updated_by": "admin",
            "status": "DRAFT",
            "version": 1,
            "is_archived": False,
            "artifact_path": None,
            "artifact_sha256": None,
            "main_full_name": "Петров Петр",
            "main_unit": "2 рота",
            "main_id_tag": "TAG-2",
            "main_diagnosis": "Ожог",
            "birth_date": "1990-01-02",
            "signed_by": None,
            "signed_at": None,
            "data": {
                "stub": {
                    "stub_issued_date": "18.02.2026",
                    "stub_issued_time": "09:30",
                    "stub_injury_date": "17.02.2026",
                    "stub_injury_time": "08:40",
                    "stub_pss_pgs_dose": "3 мл",
                    "stub_toxoid_type": "АДС-М",
                    "stub_antidote_type": "Атропин",
                    "stub_evacuation_method": "truck",
                    "stub_med_help_underline": ["Антидот"],
                },
                "main": {
                    "main_full_name": "Петров Петр",
                    "main_unit": "2 рота",
                    "main_issued_date": "18.02.2026",
                    "main_issued_time": "09:20",
                    "main_injury_date": "17.02.2026",
                    "main_injury_time": "08:30",
                },
                "lesion": {},
                "san_loss": {},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
                "medical_help": {},
                "bottom": {"tourniquet_time": "10:10"},
                "flags": {},
                "raw_payload": {},
            },
        }
    )

    editor.load_card(card)

    assert editor.stub_issued_date.date().toString("dd.MM.yyyy") == "18.02.2026"
    assert editor.stub_issued_time.time().toString("HH:mm") == "09:30"
    assert editor.stub_pss_pgs_dose.text() == "3 мл"
    assert editor.stub_toxoid_type.text() == "АДС-М"
    assert editor.stub_antidote_type.text() == "Атропин"
    assert editor.stub_evac_method.currentData() == "ambu"
    assert editor.stub_med_help_checks["Антидот"].isChecked() is True
    assert editor.main_issued_date.date().toString("dd.MM.yyyy") == "18.02.2026"
    assert editor.main_issued_time.time().toString("HH:mm") == "09:20"
    assert editor.main_injury_date.date().toString("dd.MM.yyyy") == "17.02.2026"
    assert editor.main_injury_time.time().toString("HH:mm") == "08:30"
    assert editor.tourniquet_time.time().toString("HH:mm") == "10:10"


def test_form100_v2_editor_loads_medical_help_details(qapp) -> None:
    editor = Form100EditorV2()
    now = datetime(2026, 2, 18, 12, 0, tzinfo=UTC)
    card = Form100CardV2Dto.model_validate(
        {
            "id": "CARD-2",
            "legacy_card_id": None,
            "emr_case_id": None,
            "created_at": now,
            "created_by": "admin",
            "updated_at": now,
            "updated_by": "admin",
            "status": "DRAFT",
            "version": 1,
            "is_archived": False,
            "artifact_path": None,
            "artifact_sha256": None,
            "main_full_name": "Сидоров Сидор",
            "main_unit": "3 рота",
            "main_id_tag": "TAG-3",
            "main_diagnosis": "Ранение",
            "birth_date": "1990-01-02",
            "signed_by": None,
            "signed_at": None,
            "data": {
                "stub": {},
                "main": {},
                "lesion": {},
                "san_loss": {},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
                "medical_help": {
                    "mp_serum_pss": True,
                    "mp_serum_dose": "legacy serum",
                    "mp_transfusion_substitute": True,
                    "mp_transfusion_substitute_details": "полиглюкин 400 мл",
                    "mp_bandage": True,
                    "mp_bandage_details": "асептическая",
                    "mp_surgical_intervention": True,
                    "mp_surgical_intervention_details": "лапаротомия",
                },
                "bottom": {},
                "flags": {},
                "raw_payload": {},
            },
        }
    )

    editor.load_card(card)

    assert editor.mp_serum_pss.isChecked() is True
    assert editor.mp_serum_pss_details.text() == "legacy serum"
    assert editor.mp_transfusion_substitute.isChecked() is True
    assert editor.mp_transfusion_substitute_details.text() == "полиглюкин 400 мл"
    assert editor.mp_bandage.isChecked() is True
    assert editor.mp_bandage_details.text() == "асептическая"
    assert editor.mp_surgical_intervention.isChecked() is True
    assert editor.mp_surgical_intervention_details.text() == "лапаротомия"
