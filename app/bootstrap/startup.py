from __future__ import annotations

import logging
import shutil
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.infrastructure.db.engine import get_engine
from app.infrastructure.db.fts_manager import FtsManager
from app.infrastructure.db.models_sqlalchemy import User

if TYPE_CHECKING:
    from app.container import Container

_SessionFactory = Callable[[], AbstractContextManager[Session]]
_HANDLED_STARTUP_ERRORS = (
    CommandError,
    SQLAlchemyError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
    ImportError,
)
_HANDLED_SEED_ERRORS = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
)


def _message_parent() -> QWidget:
    return cast(QWidget, QApplication.activeWindow())


def _show_critical(title: str, text: str) -> None:
    QMessageBox.critical(_message_parent(), title, text)


def _show_warning(title: str, text: str) -> None:
    QMessageBox.warning(_message_parent(), title, text)


def _is_multiple_heads_error(exc: BaseException) -> bool:
    text = str(exc)
    return "MultipleHeads" in str(type(exc)) or "Multiple head" in text


def _migration_root_candidates(root_dir: Path) -> list[Path]:
    candidates: list[Path] = [root_dir]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir not in candidates:
            candidates.append(exe_dir)
    return candidates


def _resolve_migration_root(root_dir: Path) -> Path | None:
    for candidate in _migration_root_candidates(root_dir):
        alembic_ini = candidate / "alembic.ini"
        migrations_dir = candidate / "app" / "infrastructure" / "db" / "migrations"
        if alembic_ini.exists() and migrations_dir.exists():
            return candidate
    return None


def check_startup_prerequisites(root_dir: Path, db_file: Path) -> bool:
    migration_root = _resolve_migration_root(root_dir)
    if migration_root is None:
        checked_roots = ", ".join(str(path) for path in _migration_root_candidates(root_dir))
        _show_critical(
            "РћС€РёР±РєР°",
            "РћС‚СЃСѓС‚СЃС‚РІСѓСЋС‚ С„Р°Р№Р»С‹ РјРёРіСЂР°С†РёР№ (alembic.ini Рё РєР°С‚Р°Р»РѕРі migrations).\n"
            f"РџСЂРѕРІРµСЂРµРЅС‹ РїСѓС‚Рё: {checked_roots}",
        )
        return False
    try:
        test_file = db_file.parent / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except OSError:
        _show_critical(
            "РћС€РёР±РєР°",
            f"РќРµС‚ РїСЂР°РІ РЅР° Р·Р°РїРёСЃСЊ РІ РєР°С‚Р°Р»РѕРі Р‘Р”: {db_file.parent}",
        )
        return False
    return True


def run_migrations(root_dir: Path, database_url: str, log_dir: Path, db_file: Path) -> bool:
    try:
        migration_root = _resolve_migration_root(root_dir) or root_dir
        cfg = Config(str(migration_root / "alembic.ini"))
        cfg.set_main_option(
            "script_location",
            str(migration_root / "app" / "infrastructure" / "db" / "migrations"),
        )
        cfg.set_main_option("sqlalchemy.url", database_url)
        try:
            command.upgrade(cfg, "head")
            return True
        except CommandError as exc:
            if _is_multiple_heads_error(exc):
                try:
                    command.upgrade(cfg, "heads")
                    return True
                except CommandError:
                    logging.getLogger(__name__).exception("Failed to upgrade multiple heads")
                    raise
            raise
    except _HANDLED_STARTUP_ERRORS:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to run migrations")
        try:
            import traceback

            error_path = log_dir / "migration_error.log"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            with error_path.open("a", encoding="utf-8") as handle:
                handle.write("\n--- Migration error ---\n")
                handle.write(f"DB: {db_file}\n")
                handle.write(f"Migrations: {migration_root / 'app' / 'infrastructure' / 'db' / 'migrations'}\n")
                handle.write(traceback.format_exc())
        except OSError:
            logger.exception("Failed to write migration error log")
        _show_critical(
            "РћС€РёР±РєР°",
            "РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРёРјРµРЅРёС‚СЊ РјРёРіСЂР°С†РёРё Р±Р°Р·С‹ РґР°РЅРЅС‹С….\n"
            f"РџРѕРґСЂРѕР±РЅРѕСЃС‚Рё: {log_dir / 'migration_error.log'}",
        )
        return False


def ensure_schema_compatibility(
    root_dir: Path,
    database_url: str,
    log_dir: Path,
    db_file: Path,
) -> bool:
    try:
        engine = get_engine()
        inspector = inspect(engine)
        if "patients" not in inspector.get_table_names():
            return True
        columns = {col["name"] for col in inspector.get_columns("patients")}
        required = {"category", "military_unit", "military_district"}
        missing = required - columns
        if not missing:
            return True
        logging.getLogger(__name__).warning(
            "DB schema mismatch in 'patients' table. Missing columns: %s. DB path: %s",
            ", ".join(sorted(missing)),
            db_file,
        )
        if not run_migrations(root_dir, database_url, log_dir, db_file):
            return False
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("patients")}
        if required - columns:
            _show_critical(
                "РћС€РёР±РєР°",
                "Р‘Р°Р·Р° РґР°РЅРЅС‹С… СѓСЃС‚Р°СЂРµР»Р° Рё РЅРµ РјРѕР¶РµС‚ Р±С‹С‚СЊ РѕР±РЅРѕРІР»РµРЅР° Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё.",
            )
            return False
        return True
    except _HANDLED_STARTUP_ERRORS as exc:
        logging.getLogger(__name__).exception("Failed to verify database schema")
        _show_critical(
            "РћС€РёР±РєР°",
            f"РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕРІРµСЂРёС‚СЊ СЃС‚СЂСѓРєС‚СѓСЂСѓ Р±Р°Р·С‹ РґР°РЅРЅС‹С…: {exc}",
        )
        return False


def ensure_fts_objects(session_factory: _SessionFactory) -> bool:
    fts_manager = FtsManager(session_factory=session_factory)
    if fts_manager.ensure_all():
        return True
    _show_critical(
        "РћС€РёР±РєР°",
        "РќРµ СѓРґР°Р»РѕСЃСЊ РёРЅРёС†РёР°Р»РёР·РёСЂРѕРІР°С‚СЊ FTS-РїРѕРёСЃРє.",
    )
    return False


def has_users(session_factory: _SessionFactory) -> bool:
    try:
        with session_factory() as session:
            return session.execute(select(User.id).limit(1)).first() is not None
    except SQLAlchemyError:
        logging.getLogger(__name__).exception("Failed to check users")
        return False


def cleanup_stale_temp_dirs() -> None:
    """Remove orphaned temp directories left by crashed import/export operations."""
    logger = logging.getLogger(__name__)
    tmp_run = Path.cwd() / "tmp_run"
    if not tmp_run.is_dir():
        return
    prefixes = ("epid-temp-", "form100-v2-")
    removed = 0
    for child in tmp_run.iterdir():
        if child.is_dir() and child.name.startswith(prefixes):
            try:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
            except OSError:
                logger.debug("Failed to remove stale temp dir: %s", child)
    if removed:
        logger.info("Cleaned up %d stale temp directories in tmp_run", removed)


def initialize_database(
    *,
    root_dir: Path,
    db_file: Path,
    database_url: str,
    log_dir: Path,
    session_factory: _SessionFactory,
) -> bool:
    cleanup_stale_temp_dirs()
    if not check_startup_prerequisites(root_dir, db_file):
        return False
    if not run_migrations(root_dir, database_url, log_dir, db_file):
        return False
    if not ensure_schema_compatibility(root_dir, database_url, log_dir, db_file):
        return False
    return ensure_fts_objects(session_factory)


def seed_core_data(container: Container) -> None:
    try:
        container.reference_service.seed_defaults()
    except _HANDLED_SEED_ERRORS:
        logging.getLogger(__name__).exception("Failed to seed reference defaults")
    try:
        container.backup_service.ensure_daily_backup()
    except _HANDLED_SEED_ERRORS:
        logging.getLogger(__name__).exception("Failed to run automatic backup")


def warn_missing_plot_dependencies() -> None:
    missing = []
    try:
        import pyqtgraph  # noqa: F401
    except ImportError:
        missing.append("pyqtgraph")
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        missing.append("matplotlib")
    if missing:
        _show_warning(
            "Р‘РёР±Р»РёРѕС‚РµРєРё РЅРµ РЅР°Р№РґРµРЅС‹",
            "РќРµ СѓСЃС‚Р°РЅРѕРІР»РµРЅС‹ Р±РёР±Р»РёРѕС‚РµРєРё РґР»СЏ РіСЂР°С„РёРєРѕРІ: " + ", ".join(missing),
        )

