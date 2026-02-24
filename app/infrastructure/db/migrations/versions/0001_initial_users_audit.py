"""Initial users and audit tables"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_users_audit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.CheckConstraint("role in ('admin','operator')", name="ck_users_role"),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_ts", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
    )

    op.create_index("ix_users_login", "users", ["login"], unique=False)
    op.create_index("ix_audit_log_event_ts", "audit_log", ["event_ts"], unique=False)
    op.create_index("ix_audit_log_user_id_event_ts", "audit_log", ["user_id", "event_ts"], unique=False)
    op.create_index("ix_audit_log_entity_type_entity_id", "audit_log", ["entity_type", "entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity_type_entity_id", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id_event_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_event_ts", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_users_login", table_name="users")
    op.drop_table("users")
