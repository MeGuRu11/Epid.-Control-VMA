from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.infrastructure.db.session import session_scope


class FtsManager:
    def __init__(self, session_factory: Callable = session_scope) -> None:
        self.session_factory = session_factory
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def _session_or_new(self, session: Session | None = None) -> Iterator[Session]:
        if session is not None:
            yield session
            return
        with self.session_factory() as managed:
            yield managed

    def ensure_all(self, session: Session | None = None) -> bool:
        try:
            with self._session_or_new(session) as db:
                self.logger.debug("[FTS] ensure_all start")
                ok_patients = self._ensure_patients(db)
                ok_micro = self._ensure_microorganisms(db)
                ok_icd10 = self._ensure_icd10(db)
                ok = ok_patients and ok_micro and ok_icd10
                self.logger.debug("[FTS] ensure_all done: %s", ok)
                return ok
        except Exception:  # noqa: BLE001
            self.logger.exception("[FTS] ensure_all failed")
            return False

    def ensure_patients(self, session: Session | None = None) -> bool:
        try:
            with self._session_or_new(session) as db:
                return self._ensure_patients(db)
        except Exception:  # noqa: BLE001
            self.logger.exception("[FTS] ensure_patients failed")
            return False

    def drop_patients_fts(self, session: Session | None = None) -> None:
        with self._session_or_new(session) as db:
            self._drop_triggers_for_table(db, "patients")
            db.execute(text("DROP TABLE IF EXISTS patients_fts"))

    def hard_reset_patients_fts(self, session: Session | None = None) -> None:
        with self._session_or_new(session) as db:
            trigger_names = list(
                db.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='trigger' AND (tbl_name='patients' OR sql LIKE :pattern)"
                    ),
                    {"pattern": "%patients_fts%"},
                ).scalars()
            )
            for name in trigger_names:
                db.execute(text(f'DROP TRIGGER IF EXISTS "{name}"'))
            for table_name in (
                "patients_fts",
                "patients_fts_data",
                "patients_fts_idx",
                "patients_fts_content",
                "patients_fts_docsize",
                "patients_fts_config",
            ):
                db.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))

    def rebuild_patients_fts(self, session: Session | None = None) -> bool:
        return self.ensure_patients(session)

    def _fts_exists(self, session: Session, table_name: str) -> bool:
        return (
            session.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name=:name"
                ),
                {"name": table_name},
            ).first()
            is not None
        )

    def _drop_triggers_for_table(self, session: Session, table_name: str) -> None:
        trigger_names = list(
            session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='trigger' AND tbl_name = :tbl"
                ),
                {"tbl": table_name},
            ).scalars()
        )
        for name in trigger_names:
            session.execute(text(f'DROP TRIGGER IF EXISTS "{name}"'))

    def _integrity_failed(self, session: Session, table_name: str) -> bool:
        try:
            session.execute(text(f"INSERT INTO {table_name}({table_name}) VALUES('integrity-check')"))
            return False
        except OperationalError:
            return True

    def _ensure_fts_table(
        self,
        session: Session,
        *,
        table_name: str,
        ddl: str,
        source_table: str,
        unavailable_cleanup: Callable[[Session], None],
    ) -> tuple[bool, bool]:
        exists = self._fts_exists(session, table_name)
        rebuild = not exists
        try:
            session.execute(text(ddl))
        except OperationalError as exc:
            if not self._is_fts_unavailable(exc):
                raise
            self.logger.warning("[FTS] %s unavailable: %s", table_name, exc)
            unavailable_cleanup(session)
            session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            return False, False
        if self._integrity_failed(session, table_name):
            self.logger.warning("[FTS] integrity failed for %s, rebuilding", table_name)
            rebuild = True
            session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            session.execute(text(ddl))
        self._drop_triggers_for_table(session, source_table)
        return True, rebuild

    def _ensure_patients(self, session: Session) -> bool:
        available, rebuild = self._ensure_fts_table(
            session,
            table_name="patients_fts",
            ddl=(
                "CREATE VIRTUAL TABLE IF NOT EXISTS patients_fts "
                "USING fts5(full_name, patient_id UNINDEXED);"
            ),
            source_table="patients",
            unavailable_cleanup=lambda s: self._drop_triggers_for_table(s, "patients"),
        )
        if not available:
            return True
        self._drop_known_triggers(
            session,
            "patients_ai",
            "patients_ad",
            "patients_au",
        )
        session.execute(
            text(
                """
                CREATE TRIGGER patients_ai AFTER INSERT ON patients BEGIN
                    INSERT INTO patients_fts(rowid, full_name, patient_id)
                    VALUES (new.id, new.full_name, new.id);
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER patients_ad AFTER DELETE ON patients BEGIN
                    DELETE FROM patients_fts WHERE rowid = old.id;
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER patients_au AFTER UPDATE ON patients BEGIN
                    DELETE FROM patients_fts WHERE rowid = old.id;
                    INSERT INTO patients_fts(rowid, full_name, patient_id)
                    VALUES (new.id, new.full_name, new.id);
                END;
                """
            )
        )
        if rebuild:
            session.execute(text("INSERT INTO patients_fts(patients_fts) VALUES('rebuild')"))
        return True

    def _ensure_microorganisms(self, session: Session) -> bool:
        available, rebuild = self._ensure_fts_table(
            session,
            table_name="ref_microorganisms_fts",
            ddl=(
                "CREATE VIRTUAL TABLE IF NOT EXISTS ref_microorganisms_fts "
                "USING fts5(name, code UNINDEXED, taxon_group UNINDEXED, microorganism_id UNINDEXED);"
            ),
            source_table="ref_microorganisms",
            unavailable_cleanup=lambda s: self._drop_triggers_for_table(s, "ref_microorganisms"),
        )
        if not available:
            return True
        self._drop_known_triggers(
            session,
            "ref_microorganisms_ai",
            "ref_microorganisms_ad",
            "ref_microorganisms_au",
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_microorganisms_ai AFTER INSERT ON ref_microorganisms BEGIN
                    INSERT INTO ref_microorganisms_fts(rowid, name, code, taxon_group, microorganism_id)
                    VALUES (new.id, new.name, new.code, new.taxon_group, new.id);
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_microorganisms_ad AFTER DELETE ON ref_microorganisms BEGIN
                    DELETE FROM ref_microorganisms_fts WHERE rowid = old.id;
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_microorganisms_au AFTER UPDATE ON ref_microorganisms BEGIN
                    DELETE FROM ref_microorganisms_fts WHERE rowid = old.id;
                    INSERT INTO ref_microorganisms_fts(rowid, name, code, taxon_group, microorganism_id)
                    VALUES (new.id, new.name, new.code, new.taxon_group, new.id);
                END;
                """
            )
        )
        if rebuild:
            session.execute(
                text("INSERT INTO ref_microorganisms_fts(ref_microorganisms_fts) VALUES('rebuild')")
            )
        return True

    def _ensure_icd10(self, session: Session) -> bool:
        available, rebuild = self._ensure_fts_table(
            session,
            table_name="ref_icd10_fts",
            ddl=(
                "CREATE VIRTUAL TABLE IF NOT EXISTS ref_icd10_fts "
                "USING fts5(title, code UNINDEXED);"
            ),
            source_table="ref_icd10",
            unavailable_cleanup=lambda s: self._drop_triggers_for_table(s, "ref_icd10"),
        )
        if not available:
            return True
        self._drop_known_triggers(
            session,
            "ref_icd10_ai",
            "ref_icd10_ad",
            "ref_icd10_au",
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_icd10_ai AFTER INSERT ON ref_icd10 BEGIN
                    INSERT INTO ref_icd10_fts(rowid, title, code)
                    VALUES (new.rowid, new.title, new.code);
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_icd10_ad AFTER DELETE ON ref_icd10 BEGIN
                    DELETE FROM ref_icd10_fts WHERE rowid = old.rowid;
                END;
                """
            )
        )
        session.execute(
            text(
                """
                CREATE TRIGGER ref_icd10_au AFTER UPDATE ON ref_icd10 BEGIN
                    DELETE FROM ref_icd10_fts WHERE rowid = old.rowid;
                    INSERT INTO ref_icd10_fts(rowid, title, code)
                    VALUES (new.rowid, new.title, new.code);
                END;
                """
            )
        )
        if rebuild:
            session.execute(text("INSERT INTO ref_icd10_fts(ref_icd10_fts) VALUES('rebuild')"))
        return True

    def _drop_known_triggers(self, session: Session, *names: str) -> None:
        for name in names:
            session.execute(text(f"DROP TRIGGER IF EXISTS {name}"))

    def _is_fts_unavailable(self, exc: OperationalError) -> bool:
        text_value = str(exc).lower()
        return "fts5" in text_value and "no such module" in text_value
