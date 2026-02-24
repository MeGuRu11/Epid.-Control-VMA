"""Add Form100 module tables.

Revision ID: 0018_form100_module
Revises: 0017_analytics_filter_indexes
Create Date: 2026-02-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0018_form100_module"
down_revision = "0017_analytics_filter_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form100_card",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("qr_payload", sa.Text(), nullable=True),
        sa.Column("print_number", sa.String(), nullable=True),
        sa.Column("corrects_id", sa.String(length=36), nullable=True),
        sa.Column("corrected_by_new_id", sa.String(length=36), nullable=True),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("middle_name", sa.String(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("rank", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("dog_tag_number", sa.String(), nullable=True),
        sa.Column("id_doc_type", sa.String(), nullable=True),
        sa.Column("id_doc_number", sa.String(), nullable=True),
        sa.Column("injury_dt", sa.DateTime(), nullable=True),
        sa.Column("arrival_dt", sa.DateTime(), nullable=False),
        sa.Column("first_aid_before", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cause_category", sa.String(), nullable=False),
        sa.Column("is_combat", sa.Boolean(), nullable=True),
        sa.Column("trauma_types_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("thermal_degree", sa.String(), nullable=True),
        sa.Column("wound_types_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("features_json", sa.Text(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("other_text", sa.Text(), nullable=True),
        sa.Column("diagnosis_text", sa.Text(), nullable=False),
        sa.Column("diagnosis_code", sa.String(), nullable=True),
        sa.Column("triage", sa.String(), nullable=True),
        sa.Column("flag_urgent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_sanitation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_isolation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_radiation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_bleeding_control", sa.String(), nullable=True),
        sa.Column("care_dressing", sa.String(), nullable=True),
        sa.Column("care_immobilization", sa.String(), nullable=True),
        sa.Column("care_airway", sa.String(), nullable=True),
        sa.Column("care_analgesia_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_analgesia_details", sa.Text(), nullable=True),
        sa.Column("care_antibiotic_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_antibiotic_details", sa.Text(), nullable=True),
        sa.Column("care_antidote_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_antidote_details", sa.Text(), nullable=True),
        sa.Column("care_tetanus", sa.String(), nullable=True),
        sa.Column("care_other", sa.Text(), nullable=True),
        sa.Column("infusion_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("infusion_volume_ml", sa.Integer(), nullable=True),
        sa.Column("infusion_details", sa.Text(), nullable=True),
        sa.Column("transfusion_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("transfusion_volume_ml", sa.Integer(), nullable=True),
        sa.Column("transfusion_details", sa.Text(), nullable=True),
        sa.Column("sanitation_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("sanitation_type", sa.String(), nullable=True),
        sa.Column("sanitation_details", sa.Text(), nullable=True),
        sa.Column("evac_destination", sa.Text(), nullable=True),
        sa.Column("evac_transport", sa.String(), nullable=True),
        sa.Column("evac_position", sa.String(), nullable=True),
        sa.Column("evac_require_escort", sa.Boolean(), nullable=True),
        sa.Column("evac_oxygen_needed", sa.Boolean(), nullable=True),
        sa.Column("evac_notes", sa.Text(), nullable=True),
        sa.Column("signed_by", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("seal_applied", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "form100_mark",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("card_id", sa.String(length=36), sa.ForeignKey("form100_card.id", ondelete="CASCADE"), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("shape_json", sa.Text(), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
    )
    op.create_index("ix_form100_mark_card_id", "form100_mark", ["card_id"], unique=False)

    op.create_table(
        "form100_stage",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("card_id", sa.String(length=36), sa.ForeignKey("form100_card.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_name", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("updated_diagnosis_text", sa.Text(), nullable=True),
        sa.Column("updated_diagnosis_code", sa.String(), nullable=True),
        sa.Column("procedures_text", sa.Text(), nullable=True),
        sa.Column("evac_next_destination", sa.Text(), nullable=True),
        sa.Column("evac_next_dt", sa.DateTime(), nullable=True),
        sa.Column("condition_at_transfer", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("outcome_date", sa.Date(), nullable=True),
        sa.Column("burial_place", sa.Text(), nullable=True),
        sa.Column("signed_by", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_form100_stage_card_id", "form100_stage", ["card_id"], unique=False)

    op.create_index("idx_form100_status", "form100_card", ["status"], unique=False)
    op.create_index("idx_form100_injury_dt", "form100_card", ["injury_dt"], unique=False)
    op.create_index("idx_form100_arrival_dt", "form100_card", ["arrival_dt"], unique=False)
    op.create_index("idx_form100_dog_tag", "form100_card", ["dog_tag_number"], unique=False)
    op.create_index("idx_form100_unit", "form100_card", ["unit"], unique=False)
    op.create_index("idx_form100_name", "form100_card", ["last_name", "first_name"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_form100_name", table_name="form100_card")
    op.drop_index("idx_form100_unit", table_name="form100_card")
    op.drop_index("idx_form100_dog_tag", table_name="form100_card")
    op.drop_index("idx_form100_arrival_dt", table_name="form100_card")
    op.drop_index("idx_form100_injury_dt", table_name="form100_card")
    op.drop_index("idx_form100_status", table_name="form100_card")

    op.drop_index("ix_form100_stage_card_id", table_name="form100_stage")
    op.drop_table("form100_stage")

    op.drop_index("ix_form100_mark_card_id", table_name="form100_mark")
    op.drop_table("form100_mark")

    op.drop_table("form100_card")
