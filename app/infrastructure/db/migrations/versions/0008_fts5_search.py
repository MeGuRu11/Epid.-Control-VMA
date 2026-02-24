"""FTS5 tables for search"""
from __future__ import annotations

from alembic import op

revision = "0008_fts5_search"
down_revision = "0007_report_run"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE patients_fts
        USING fts5(full_name, patient_id UNINDEXED);
        """
    )
    op.execute(
        """
        INSERT INTO patients_fts(rowid, full_name, patient_id)
        SELECT id, full_name, id FROM patients;
        """
    )
    op.execute(
        """
        CREATE TRIGGER patients_ai AFTER INSERT ON patients BEGIN
            INSERT INTO patients_fts(rowid, full_name, patient_id)
            VALUES (new.id, new.full_name, new.id);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER patients_ad AFTER DELETE ON patients BEGIN
            INSERT INTO patients_fts(patients_fts, rowid, full_name, patient_id)
            VALUES ('delete', old.id, old.full_name, old.id);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER patients_au AFTER UPDATE ON patients BEGIN
            INSERT INTO patients_fts(patients_fts, rowid, full_name, patient_id)
            VALUES ('delete', old.id, old.full_name, old.id);
            INSERT INTO patients_fts(rowid, full_name, patient_id)
            VALUES (new.id, new.full_name, new.id);
        END;
        """
    )

    op.execute(
        """
        CREATE VIRTUAL TABLE ref_microorganisms_fts
        USING fts5(name, code UNINDEXED, taxon_group UNINDEXED, microorganism_id UNINDEXED);
        """
    )
    op.execute(
        """
        INSERT INTO ref_microorganisms_fts(rowid, name, code, taxon_group, microorganism_id)
        SELECT id, name, code, taxon_group, id FROM ref_microorganisms;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_microorganisms_ai AFTER INSERT ON ref_microorganisms BEGIN
            INSERT INTO ref_microorganisms_fts(rowid, name, code, taxon_group, microorganism_id)
            VALUES (new.id, new.name, new.code, new.taxon_group, new.id);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_microorganisms_ad AFTER DELETE ON ref_microorganisms BEGIN
            INSERT INTO ref_microorganisms_fts(ref_microorganisms_fts, rowid, name, code, taxon_group, microorganism_id)
            VALUES ('delete', old.id, old.name, old.code, old.taxon_group, old.id);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_microorganisms_au AFTER UPDATE ON ref_microorganisms BEGIN
            INSERT INTO ref_microorganisms_fts(ref_microorganisms_fts, rowid, name, code, taxon_group, microorganism_id)
            VALUES ('delete', old.id, old.name, old.code, old.taxon_group, old.id);
            INSERT INTO ref_microorganisms_fts(rowid, name, code, taxon_group, microorganism_id)
            VALUES (new.id, new.name, new.code, new.taxon_group, new.id);
        END;
        """
    )

    op.execute(
        """
        CREATE VIRTUAL TABLE ref_icd10_fts
        USING fts5(title, code UNINDEXED);
        """
    )
    op.execute(
        """
        INSERT INTO ref_icd10_fts(rowid, title, code)
        SELECT rowid, title, code FROM ref_icd10;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_icd10_ai AFTER INSERT ON ref_icd10 BEGIN
            INSERT INTO ref_icd10_fts(rowid, title, code)
            VALUES (new.rowid, new.title, new.code);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_icd10_ad AFTER DELETE ON ref_icd10 BEGIN
            INSERT INTO ref_icd10_fts(ref_icd10_fts, rowid, title, code)
            VALUES ('delete', old.rowid, old.title, old.code);
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ref_icd10_au AFTER UPDATE ON ref_icd10 BEGIN
            INSERT INTO ref_icd10_fts(ref_icd10_fts, rowid, title, code)
            VALUES ('delete', old.rowid, old.title, old.code);
            INSERT INTO ref_icd10_fts(rowid, title, code)
            VALUES (new.rowid, new.title, new.code);
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS patients_ai")
    op.execute("DROP TRIGGER IF EXISTS patients_ad")
    op.execute("DROP TRIGGER IF EXISTS patients_au")
    op.execute("DROP TABLE IF EXISTS patients_fts")

    op.execute("DROP TRIGGER IF EXISTS ref_microorganisms_ai")
    op.execute("DROP TRIGGER IF EXISTS ref_microorganisms_ad")
    op.execute("DROP TRIGGER IF EXISTS ref_microorganisms_au")
    op.execute("DROP TABLE IF EXISTS ref_microorganisms_fts")

    op.execute("DROP TRIGGER IF EXISTS ref_icd10_ai")
    op.execute("DROP TRIGGER IF EXISTS ref_icd10_ad")
    op.execute("DROP TRIGGER IF EXISTS ref_icd10_au")
    op.execute("DROP TABLE IF EXISTS ref_icd10_fts")
