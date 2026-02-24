# mypy: ignore-errors

"""Add Form100 V2 schema and migrate legacy Form100 cards.

Revision ID: 0019_form100_v2_schema
Revises: 0018_form100_module
Create Date: 2026-02-18
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0019_form100_v2_schema"
down_revision = "0018_form100_module"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json(value: object, *, default: object) -> object:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(str(value))
    except Exception:  # noqa: BLE001
        return default


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def upgrade() -> None:
    op.create_table(
        "form100",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("legacy_card_id", sa.String(length=36), nullable=True),
        sa.Column("emr_case_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("artifact_sha256", sa.String(), nullable=True),
        sa.Column("main_full_name", sa.String(), nullable=False, server_default=sa.text("''")),
        sa.Column("main_unit", sa.String(), nullable=True),
        sa.Column("main_id_tag", sa.String(), nullable=True),
        sa.Column("main_diagnosis", sa.Text(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("signed_by", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["emr_case_id"], ["emr_case.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_form100_emr_case", "form100", ["emr_case_id"], unique=False)
    op.create_index("ix_form100_created_at", "form100", ["created_at"], unique=False)
    op.create_index("ix_form100_status", "form100", ["status"], unique=False)
    op.create_index("ix_form100_main_full_name", "form100", ["main_full_name"], unique=False)
    op.create_index("ix_form100_main_unit", "form100", ["main_unit"], unique=False)
    op.create_index("ix_form100_legacy_card_id", "form100", ["legacy_card_id"], unique=False)

    op.create_table(
        "form100_data",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("form100_id", sa.String(length=36), nullable=False),
        sa.Column("stub_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("main_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("lesion_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("san_loss_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("mp_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("bottom_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("flags_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("bodymap_gender", sa.String(), nullable=False, server_default=sa.text("'M'")),
        sa.Column("bodymap_annotations_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("bodymap_tissue_types_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("raw_payload_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["form100_id"], ["form100.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ux_form100_data_form", "form100_data", ["form100_id"], unique=True)

    bind = op.get_bind()
    card_rows = bind.execute(sa.text("SELECT * FROM form100_card")).mappings().all()
    if not card_rows:
        return

    mark_rows = bind.execute(sa.text("SELECT * FROM form100_mark ORDER BY created_at ASC")).mappings().all()
    stage_rows = bind.execute(sa.text("SELECT * FROM form100_stage ORDER BY received_at ASC")).mappings().all()

    marks_by_card: dict[str, list[dict[str, object]]] = {}
    for row in mark_rows:
        card_id = _safe_text(row.get("card_id"))
        marks_by_card.setdefault(card_id, []).append(dict(row))

    stages_by_card: dict[str, list[dict[str, object]]] = {}
    for row in stage_rows:
        card_id = _safe_text(row.get("card_id"))
        stages_by_card.setdefault(card_id, []).append(dict(row))

    now = _utc_now()
    for row in card_rows:
        row_dict = dict(row)
        card_id = _safe_text(row.get("id")) or str(uuid4())
        middle_name = _safe_text(row.get("middle_name"))
        full_name_parts = [_safe_text(row.get("last_name")), _safe_text(row.get("first_name")), middle_name]
        full_name = " ".join(part for part in full_name_parts if part)
        trauma_types = _load_json(row.get("trauma_types_json"), default=[])
        wound_types = _load_json(row.get("wound_types_json"), default=[])
        features = _load_json(row.get("features_json"), default=[])

        card_marks = marks_by_card.get(card_id, [])
        card_stages = stages_by_card.get(card_id, [])
        annotations: list[dict[str, object]] = []
        for mark in card_marks:
            shape = _load_json(mark.get("shape_json"), default={})
            meta = _load_json(mark.get("meta_json"), default={})
            if not isinstance(shape, dict):
                shape = {}
            if not isinstance(meta, dict):
                meta = {}
            side = _safe_text(mark.get("side")).upper()
            silhouette = "male_front" if side != "BACK" else "male_back"
            mark_type_raw = _safe_text(mark.get("type")).upper()
            annotation_type = {
                "TOURNIQUET_LINE": "TOURNIQUET",
                "AMPUTATION_FILL": "AMPUTATION",
            }.get(mark_type_raw, mark_type_raw or "NOTE_PIN")
            x = shape.get("x")
            y = shape.get("y")
            if x is None or y is None:
                x1 = shape.get("x1")
                x2 = shape.get("x2")
                y1 = shape.get("y1")
                y2 = shape.get("y2")
                if isinstance(x1, (int, float)) and isinstance(x2, (int, float)):
                    x = (x1 + x2) / 2
                if isinstance(y1, (int, float)) and isinstance(y2, (int, float)):
                    y = (y1 + y2) / 2
            try:
                x_float = float(x if x is not None else 0.5)
                y_float = float(y if y is not None else 0.5)
            except Exception:  # noqa: BLE001
                x_float = 0.5
                y_float = 0.5
            annotations.append(
                {
                    "annotation_type": annotation_type,
                    "x": max(0.0, min(1.0, x_float)),
                    "y": max(0.0, min(1.0, y_float)),
                    "silhouette": silhouette,
                    "note": _safe_text(meta.get("text")),
                }
            )

        stub_json = {
            "stub_rank": _safe_text(row.get("rank")),
            "stub_unit": _safe_text(row.get("unit")),
            "stub_full_name": full_name,
            "stub_id_tag": _safe_text(row.get("dog_tag_number") or row.get("id_doc_number")),
            "stub_injury_date": (row.get("injury_dt").date().isoformat() if row.get("injury_dt") else None),
            "stub_injury_time": (row.get("injury_dt").strftime("%H:%M") if row.get("injury_dt") else None),
            "stub_evacuation_dest": _safe_text(row.get("evac_position")),
            "stub_med_help": [],
            "stub_antibiotic_dose": _safe_text(row.get("care_antibiotic_details")),
            "stub_analgesic_dose": _safe_text(row.get("care_analgesia_details")),
            "stub_transfusion": _as_bool(row.get("transfusion_performed")),
            "stub_immobilization": bool(_safe_text(row.get("care_immobilization"))),
            "stub_tourniquet": bool(_safe_text(row.get("care_bleeding_control"))),
            "stub_diagnosis": _safe_text(row.get("diagnosis_text")),
        }
        main_json = {
            "main_issued_place": "",
            "main_rank": _safe_text(row.get("rank")),
            "main_unit": _safe_text(row.get("unit")),
            "main_full_name": full_name,
            "main_id_tag": _safe_text(row.get("dog_tag_number") or row.get("id_doc_number")),
            "main_injury_date": (row.get("injury_dt").date().isoformat() if row.get("injury_dt") else None),
            "main_injury_time": (row.get("injury_dt").strftime("%H:%M") if row.get("injury_dt") else None),
            "birth_date": (row.get("birth_date").isoformat() if row.get("birth_date") else None),
        }
        lesion_json = {
            "cause_category": _safe_text(row.get("cause_category")),
            "is_combat": _as_bool(row.get("is_combat")),
            "trauma_types": trauma_types if isinstance(trauma_types, list) else [],
            "wound_types": wound_types if isinstance(wound_types, list) else [],
            "features": features if isinstance(features, list) else [],
            "thermal_degree": _safe_text(row.get("thermal_degree")),
            "diagnosis_code": _safe_text(row.get("diagnosis_code")),
            "triage": _safe_text(row.get("triage")),
        }
        mp_json = {
            "first_aid_before": _as_bool(row.get("first_aid_before")),
            "care_bleeding_control": _safe_text(row.get("care_bleeding_control")),
            "care_dressing": _safe_text(row.get("care_dressing")),
            "care_immobilization": _safe_text(row.get("care_immobilization")),
            "care_airway": _safe_text(row.get("care_airway")),
            "care_analgesia_given": _as_bool(row.get("care_analgesia_given")),
            "care_analgesia_details": _safe_text(row.get("care_analgesia_details")),
            "care_antibiotic_given": _as_bool(row.get("care_antibiotic_given")),
            "care_antibiotic_details": _safe_text(row.get("care_antibiotic_details")),
            "care_antidote_given": _as_bool(row.get("care_antidote_given")),
            "care_antidote_details": _safe_text(row.get("care_antidote_details")),
            "care_tetanus": _safe_text(row.get("care_tetanus")),
            "care_other": _safe_text(row.get("care_other")),
            "infusion_performed": _as_bool(row.get("infusion_performed")),
            "infusion_volume_ml": row.get("infusion_volume_ml"),
            "infusion_details": _safe_text(row.get("infusion_details")),
            "transfusion_performed": _as_bool(row.get("transfusion_performed")),
            "transfusion_volume_ml": row.get("transfusion_volume_ml"),
            "transfusion_details": _safe_text(row.get("transfusion_details")),
            "sanitation_performed": _as_bool(row.get("sanitation_performed")),
            "sanitation_type": _safe_text(row.get("sanitation_type")),
            "sanitation_details": _safe_text(row.get("sanitation_details")),
        }
        bottom_json = {
            "arrival_dt": (row.get("arrival_dt").isoformat() if row.get("arrival_dt") else None),
            "evacuation_dest": _safe_text(row.get("evac_position")),
            "transport_type": _safe_text(row.get("evac_transport")),
            "doctor_signature": _safe_text(row.get("signed_by")),
            "main_diagnosis": _safe_text(row.get("diagnosis_text")),
            "evac_destination": _safe_text(row.get("evac_destination")),
            "evac_require_escort": row.get("evac_require_escort"),
            "evac_oxygen_needed": row.get("evac_oxygen_needed"),
            "evac_notes": _safe_text(row.get("evac_notes")),
            "stages": card_stages,
        }
        flags_json = {
            "flag_emergency": _as_bool(row.get("flag_urgent")),
            "flag_radiation": _as_bool(row.get("flag_radiation")),
            "flag_sanitation": _as_bool(row.get("flag_sanitation")),
            "flag_isolation": _as_bool(row.get("flag_isolation")),
        }
        raw_payload = {
            "legacy_card": row_dict,
            "legacy_marks": card_marks,
            "legacy_stages": card_stages,
        }

        bind.execute(
            sa.text(
                """
                INSERT INTO form100 (
                    id, legacy_card_id, emr_case_id, created_at, created_by, updated_at, updated_by,
                    status, version, is_archived, artifact_path, artifact_sha256,
                    main_full_name, main_unit, main_id_tag, main_diagnosis, birth_date, signed_by, signed_at
                ) VALUES (
                    :id, :legacy_card_id, :emr_case_id, :created_at, :created_by, :updated_at, :updated_by,
                    :status, :version, :is_archived, :artifact_path, :artifact_sha256,
                    :main_full_name, :main_unit, :main_id_tag, :main_diagnosis, :birth_date, :signed_by, :signed_at
                )
                """
            ),
            {
                "id": card_id,
                "legacy_card_id": _safe_text(row.get("id")) or None,
                "emr_case_id": None,
                "created_at": row.get("created_at") or now,
                "created_by": _safe_text(row.get("created_by")) or "migration",
                "updated_at": row.get("updated_at") or row.get("created_at") or now,
                "updated_by": _safe_text(row.get("updated_by")) or _safe_text(row.get("created_by")) or "migration",
                "status": _safe_text(row.get("status")) or "DRAFT",
                "version": int(row.get("version") or 1),
                "is_archived": 0,
                "artifact_path": None,
                "artifact_sha256": None,
                "main_full_name": full_name,
                "main_unit": _safe_text(row.get("unit")) or None,
                "main_id_tag": _safe_text(row.get("dog_tag_number") or row.get("id_doc_number")) or None,
                "main_diagnosis": _safe_text(row.get("diagnosis_text")) or None,
                "birth_date": row.get("birth_date"),
                "signed_by": _safe_text(row.get("signed_by")) or None,
                "signed_at": row.get("signed_at"),
            },
        )

        bind.execute(
            sa.text(
                """
                INSERT INTO form100_data (
                    id, form100_id, stub_json, main_json, lesion_json, san_loss_json, mp_json, bottom_json,
                    flags_json, bodymap_gender, bodymap_annotations_json, bodymap_tissue_types_json, raw_payload_json
                ) VALUES (
                    :id, :form100_id, :stub_json, :main_json, :lesion_json, :san_loss_json, :mp_json, :bottom_json,
                    :flags_json, :bodymap_gender, :bodymap_annotations_json, :bodymap_tissue_types_json, :raw_payload_json
                )
                """
            ),
            {
                "id": str(uuid4()),
                "form100_id": card_id,
                "stub_json": json.dumps(stub_json, ensure_ascii=False),
                "main_json": json.dumps(main_json, ensure_ascii=False),
                "lesion_json": json.dumps(lesion_json, ensure_ascii=False),
                "san_loss_json": json.dumps({}, ensure_ascii=False),
                "mp_json": json.dumps(mp_json, ensure_ascii=False),
                "bottom_json": json.dumps(bottom_json, ensure_ascii=False),
                "flags_json": json.dumps(flags_json, ensure_ascii=False),
                "bodymap_gender": "M",
                "bodymap_annotations_json": json.dumps(annotations, ensure_ascii=False),
                "bodymap_tissue_types_json": json.dumps(
                    wound_types if isinstance(wound_types, list) else [],
                    ensure_ascii=False,
                ),
                "raw_payload_json": json.dumps(raw_payload, ensure_ascii=False, default=str),
            },
        )


def downgrade() -> None:
    op.drop_index("ux_form100_data_form", table_name="form100_data")
    op.drop_table("form100_data")

    op.drop_index("ix_form100_legacy_card_id", table_name="form100")
    op.drop_index("ix_form100_main_unit", table_name="form100")
    op.drop_index("ix_form100_main_full_name", table_name="form100")
    op.drop_index("ix_form100_status", table_name="form100")
    op.drop_index("ix_form100_created_at", table_name="form100")
    op.drop_index("ix_form100_emr_case", table_name="form100")
    op.drop_table("form100")
