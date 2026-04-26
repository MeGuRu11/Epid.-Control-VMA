from __future__ import annotations

from app.ui.form100_v2.wizard_widgets.wizard_steps.step_medical import StepMedical


def test_step_medical_collects_details_for_all_help_rows(qapp) -> None:
    step = StepMedical()

    step.mp_serum_pss.setChecked(True)
    step.mp_serum_pss_details.setText("ПСС 3000 МЕ")
    step.mp_serum_pgs.setChecked(True)
    step.mp_serum_pgs_details.setText("ПГС 1 доза")
    step.mp_transfusion_blood.setChecked(True)
    step.mp_transfusion_blood_details.setText("эритроцитарная масса 250 мл")
    step.mp_transfusion_substitute.setChecked(True)
    step.mp_transfusion_substitute_details.setText("полиглюкин 400 мл")
    step.mp_immobilization.setChecked(True)
    step.mp_immobilization_details.setText("шина Крамера")
    step.mp_bandage.setChecked(True)
    step.mp_bandage_details.setText("асептическая")
    step.mp_surgical_intervention.setChecked(True)
    step.mp_surgical_intervention_details.setText("ПХО раны")

    payload, markers = step.collect()

    assert markers == []
    assert payload["mp_serum_pss"] == "1"
    assert payload["mp_serum_pgs"] == "1"
    assert payload["mp_serum_dose"] == "ПСС 3000 МЕ"
    assert payload["mp_serum_pss_details"] == "ПСС 3000 МЕ"
    assert payload["mp_serum_pgs_details"] == "ПГС 1 доза"
    assert payload["mp_transfusion_blood_details"] == "эритроцитарная масса 250 мл"
    assert payload["mp_transfusion_substitute_details"] == "полиглюкин 400 мл"
    assert payload["mp_immobilization_details"] == "шина Крамера"
    assert payload["mp_bandage_details"] == "асептическая"
    assert payload["mp_surgical_intervention"] == "1"
    assert payload["mp_surgical_intervention_details"] == "ПХО раны"


def test_step_medical_loads_new_details_and_legacy_serum_dose(qapp) -> None:
    step = StepMedical()

    step.set_values(
        {
            "mp_serum_pss": "1",
            "mp_serum_pgs": "1",
            "mp_serum_dose": "старая общая доза",
            "mp_transfusion_blood": "1",
            "mp_transfusion_blood_details": "цельная кровь 200 мл",
            "mp_surgical_intervention": "1",
            "mp_surgical_intervention_details": "лапаротомия",
        },
        [],
    )

    assert step.mp_serum_pss.isChecked() is True
    assert step.mp_serum_pgs.isChecked() is True
    assert step.mp_serum_pss_details.text() == "старая общая доза"
    assert step.mp_serum_pgs_details.text() == "старая общая доза"
    assert step.mp_transfusion_blood.isChecked() is True
    assert step.mp_transfusion_blood_details.text() == "цельная кровь 200 мл"
    assert step.mp_surgical_intervention.isChecked() is True
    assert step.mp_surgical_intervention_details.text() == "лапаротомия"
