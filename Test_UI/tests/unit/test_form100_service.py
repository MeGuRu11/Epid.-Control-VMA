from __future__ import annotations

import json
import zipfile

import pytest

from app.application.services.auth_service import AuthService
from app.application.services.form100_service import Form100Service
from app.application.services.patient_service import PatientService


def _bootstrap(engine):
    auth = AuthService(engine)
    auth.create_initial_admin("admin", "admin1234")
    session = auth.login("admin", "admin1234")
    assert session is not None
    return session


def _require_reportlab():
    try:
        import reportlab  # noqa: F401
    except Exception:
        pytest.skip("reportlab is required for Form100 ZIP/PDF export tests")


def test_form100_bodymap_payload_and_sign_lock(engine):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)

    patient_id = patients.create("Form100 User", "U", None)
    card_id = f100.create(patient_id, None, {"main_diagnosis": "start"})
    assert card_id > 0

    ok_payload = f100.update_payload(card_id, {"main_diagnosis": "updated note", "main_full_name": "Иванов"})
    assert ok_payload is True
    payload = f100.get_payload(card_id)
    assert payload.get("main_diagnosis") == "updated note"
    assert payload.get("main_full_name") == "Иванов"

    markers = [
        {"x": 0.2, "y": 0.3, "kind": "O", "zone": "front"},
        {"x": 0.8, "y": 0.6, "kind": "X", "zone": "back"},
    ]
    ok_map = f100.update_bodymap(card_id, markers)
    assert ok_map is True
    saved = f100.get_bodymap(card_id)
    assert len(saved) == 2
    assert saved[0].get("annotation_type") in {"WOUND_X", "AMPUTATION", "NOTE_PIN", "BURN_HATCH", "TOURNIQUET"}
    assert saved[0].get("view") in {"front", "back"}

    signed = f100.sign(card_id, "Dr. Test")
    assert signed is True

    with pytest.raises(PermissionError):
        f100.update_payload(card_id, {"main_diagnosis": "locked"})
    with pytest.raises(PermissionError):
        f100.update_bodymap(card_id, [{"x": 0.1, "y": 0.1, "kind": "O", "zone": "front"}])


def test_form100_bodymap_note_pin_note_is_preserved(engine):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)

    patient_id = patients.create("Note Pin User", "U", None)
    card_id = f100.create(patient_id, None, {"main_diagnosis": "note"})
    assert f100.update_bodymap(
        card_id,
        [{"x": 0.4, "y": 0.5, "annotation_type": "NOTE_PIN", "view": "front", "note": "левая голень"}],
    )
    saved = f100.get_bodymap(card_id)
    assert len(saved) == 1
    assert saved[0].get("annotation_type") == "NOTE_PIN"
    assert saved[0].get("note") == "левая голень"


def test_form100_zip_export_import_and_revision(engine):
    _require_reportlab()
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)

    patient_id = patients.create("Zip User", "U", None)
    base_id = f100.create(patient_id, None, {"main_full_name": "Петров", "main_diagnosis": "diag"})
    f100.update_bodymap(base_id, [{"x": 0.33, "y": 0.44, "kind": "O", "zone": "front"}])

    zip_path = f100.export_zip(base_id)
    assert zip_path.exists()
    preview = f100.preview_zip(zip_path)
    assert preview["source_card_id"] == base_id
    assert preview["filled_fields"] >= 2
    assert preview["markers"] == 1

    imported_id = f100.import_zip(zip_path, patient_id=patient_id)
    assert imported_id != base_id
    imported_payload = f100.get_payload(imported_id)
    assert imported_payload.get("main_full_name") == "Петров"
    assert imported_payload.get("main_diagnosis") == "diag"
    assert len(f100.get_bodymap(imported_id)) == 1

    revision_id = f100.import_zip_revision(base_id, zip_path)
    assert revision_id not in (base_id, imported_id)
    revision_row = f100.get(revision_id)
    base_row = f100.get(base_id)
    assert revision_row is not None
    assert base_row is not None
    assert revision_row.patient_id == base_row.patient_id
    assert revision_row.emr_case_id == base_row.emr_case_id

    merged_id = f100.merge_zip_into_card(base_id, zip_path)
    assert merged_id == base_id
    merged_payload = f100.get_payload(base_id)
    assert merged_payload.get("main_full_name") == "Петров"
    assert len(f100.get_bodymap(base_id)) == 1

    f100.sign(base_id, "Signer")
    with pytest.raises(PermissionError):
        f100.merge_zip_into_card(base_id, zip_path)


def test_form100_zip_rejects_unsafe_paths(engine, tmp_path):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)
    patient_id = patients.create("Unsafe Zip User", "U", None)

    bad_zip = tmp_path / "bad_form100.zip"
    manifest = {"files": {"../evil.txt": "abc"}}
    with zipfile.ZipFile(bad_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("form100_card.json", "{}")
        zf.writestr("../evil.txt", "x")

    with pytest.raises(ValueError):
        f100.import_zip(bad_zip, patient_id=patient_id)


def test_form100_legacy_payload_keys_are_mapped(engine):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)
    patient_id = patients.create("Legacy Payload User", "U", None)

    legacy_payload = {
        "main_fio": "Старый ключ",
        "main_doc_no": "LEG-1",
        "main_wound_time": "10:25",
        "main_issued_org": "ПМП",
        "main_evacuation": "lying",
    }
    card_id = f100.create(patient_id, None, legacy_payload)
    payload = f100.get_payload(card_id)
    assert payload.get("main_full_name") == "Старый ключ"
    assert payload.get("main_id_tag") == "LEG-1"
    assert payload.get("main_injury_time") == "10:25"
    assert payload.get("main_issued_place") == "ПМП"
    assert payload.get("evacuation_dest") == "lying"


def test_form100_archive_blocks_edit_sign_and_merge(engine):
    _require_reportlab()
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)
    patient_id = patients.create("Archive User", "U", None)

    card_id = f100.create(patient_id, None, {"main_full_name": "Archive User"})
    assert f100.archive(card_id) is True

    with pytest.raises(PermissionError):
        f100.update_payload(card_id, {"main_diagnosis": "x"})
    with pytest.raises(PermissionError):
        f100.update_bodymap(card_id, [{"x": 0.1, "y": 0.2, "kind": "O", "zone": "front"}])
    with pytest.raises(PermissionError):
        f100.sign(card_id, "Dr")

    src_id = f100.create(patient_id, None, {"main_full_name": "Src"})
    zip_path = f100.export_zip(src_id)
    with pytest.raises(PermissionError):
        f100.merge_zip_into_card(card_id, zip_path)


def test_form100_list_filters_by_case(engine):
    session = _bootstrap(engine)
    patients = PatientService(engine, session)
    f100 = Form100Service(engine, session)

    patient_id = patients.create("Case Filter User", "U", None)
    card_case_1 = f100.create(patient_id, 101, {"main_full_name": "A"})
    card_case_2 = f100.create(patient_id, 202, {"main_full_name": "B"})
    assert card_case_1 != card_case_2

    rows_case_1 = f100.list(patient_id=patient_id, emr_case_id=101)
    rows_case_2 = f100.list(patient_id=patient_id, emr_case_id=202)
    rows_all = f100.list(patient_id=patient_id)
    assert {row.id for row in rows_case_1} == {card_case_1}
    assert {row.id for row in rows_case_2} == {card_case_2}
    assert {row.id for row in rows_all} == {card_case_1, card_case_2}
