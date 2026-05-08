from __future__ import annotations

import json
import os
import shutil
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import DATA_DIR, DB_FILE
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope

logger = getLogger(__name__)

if TYPE_CHECKING:
    from app.application.dto.user_preferences_dto import UserPreferences

PreferencesProvider = Callable[[], "UserPreferences"]


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    created_at: datetime
    reason: str


class BackupService:
    def __init__(
        self,
        audit_repo: AuditLogRepository,
        user_repo: UserRepository | None = None,
        session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
        preferences_provider: PreferencesProvider | None = None,
    ) -> None:
        self.audit_repo = audit_repo
        self.user_repo = user_repo or UserRepository()
        self.session_factory = session_factory or session_scope
        self._preferences_provider = preferences_provider
        # backup_dir резолвится один раз при инициализации — смена каталога
        # через настройки требует перезапуска (отмечено в UI значком ⟳).
        self.backup_dir = self._resolve_backup_dir()
        self._prepare_artifacts_dir(self.backup_dir)
        self._meta_path = self.backup_dir / "last_backup.json"

    # ------------------------------------------------------------------
    # Preferences helpers
    # ------------------------------------------------------------------

    def _get_prefs(self) -> UserPreferences | None:
        """Безопасно получить текущие настройки. None при ошибке провайдера."""
        if self._preferences_provider is None:
            return None
        try:
            return self._preferences_provider()
        except Exception:  # noqa: BLE001
            logger.exception("BackupService: preferences_provider raised an exception")
            return None

    def _resolve_backup_dir(self) -> Path:
        """Определить каталог резервных копий из настроек или дефолт."""
        prefs = self._get_prefs()
        if prefs is not None and prefs.backup_dir:
            candidate = Path(prefs.backup_dir)
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                return candidate
            except OSError:
                logger.warning(
                    "BackupService: configured backup_dir is not accessible (%s);"
                    " falling back to default.",
                    candidate,
                )
        return DATA_DIR / "backups"

    def _enforce_retention(self) -> None:
        """Удалить лишние резервные копии согласно backup_retention_count."""
        prefs = self._get_prefs()
        if prefs is None:
            return
        keep = max(1, prefs.backup_retention_count)
        all_backups = self.list_backups()  # отсортированы новые-первые
        for old_path in all_backups[keep:]:
            with suppress(OSError):
                old_path.unlink()
                logger.debug("BackupService: removed old backup %s (retention=%d)", old_path.name, keep)

    def _prepare_artifacts_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        # Best-effort: some filesystems/platforms ignore chmod semantics.
        with suppress(OSError):
            os.chmod(path, 0o700)

    def _require_admin_access(self, *, actor_id: int, action: str) -> None:
        if actor_id is None:  # raise on missing actor_id
            raise ValueError("actor_id обязателен для операций записи")
        with self.session_factory() as session:
            actor = self.user_repo.get_by_id(session, actor_id)
            if actor is not None and str(actor.role) == "admin":
                return
            payload = json.dumps(
                {
                    "reason": "admin_required",
                    "permission": "manage_backups",
                    "action": action,
                },
                ensure_ascii=False,
            )
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="backup",
                entity_id=action,
                action="access_denied",
                payload_json=payload,
            )
        raise ValueError("Недостаточно прав для управления резервными копиями")

    def list_backups(self) -> list[Path]:
        return sorted(self.backup_dir.glob("app_*.db"), reverse=True)

    def get_last_backup(self) -> BackupInfo | None:
        if not self._meta_path.exists():
            return None
        try:
            data = json.loads(self._meta_path.read_text(encoding="utf-8"))
            raw_path = data["path"]
            if not isinstance(raw_path, str):
                raise TypeError("backup metadata path must be a string")
            path = self._resolve_metadata_path(raw_path)
            created_at = datetime.fromisoformat(data["created_at"])
            reason = data.get("reason", "unknown")
            if path is None or not path.exists():
                return None
            return BackupInfo(path=path, created_at=created_at, reason=reason)
        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as exc:
            logger.warning("Failed to parse backup metadata: %s", exc)
            return None

    def create_backup(self, *, actor_id: int, reason: str = "manual") -> Path:
        self._require_admin_access(actor_id=actor_id, action="backup_create")
        if not DB_FILE.exists():
            raise FileNotFoundError(f"База данных не найдена: {DB_FILE}")
        # TODO SECURITY: добавить шифрование бэкапов/экспортов (AES-GCM)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"app_{timestamp}.db"
        try:
            self._create_sqlite_backup(DB_FILE, backup_path)
        except (OSError, sqlite3.Error) as exc:
            # Fallback for environments where sqlite backup API is unavailable.
            logger.warning("SQLite backup API failed, fallback to file copy: %s", exc)
            shutil.copy2(DB_FILE, backup_path)
        self._write_meta(backup_path, reason)
        self._audit_event(actor_id, "backup_create", backup_path, reason)
        # Подрезаем устаревшие копии согласно настройке retention.
        self._enforce_retention()
        return backup_path

    def restore_backup(self, backup_path: Path, *, actor_id: int) -> None:
        self._require_admin_access(actor_id=actor_id, action="backup_restore")
        if not backup_path.exists():
            raise FileNotFoundError(f"Файл резервной копии не найден: {backup_path}")
        # Close pooled connections before overwriting DB file.
        try:
            from app.infrastructure.db.session import engine as sa_engine

            sa_engine.dispose()
        except (AttributeError, ImportError, RuntimeError) as exc:
            logger.warning("Failed to dispose SQLAlchemy engine before restore: %s", exc)
        # Safety copy of current DB before overwrite.
        if DB_FILE.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            safety_path = self.backup_dir / f"pre_restore_{timestamp}.db"
            shutil.copy2(DB_FILE, safety_path)
        shutil.copy2(backup_path, DB_FILE)
        self._write_meta(backup_path, "restore")
        self._audit_event(actor_id, "backup_restore", backup_path, "restore")

    def ensure_daily_backup(self) -> bool:
        prefs = self._get_prefs()

        # Если автоматические бэкапы выключены в настройках — ничего не делаем.
        if prefs is not None and not prefs.auto_backup_enabled:
            return False

        # Режим "manual" — автоматика полностью отключена.
        if prefs is not None and prefs.auto_backup_frequency == "manual":
            return False

        last = self.get_last_backup()
        backup_user_id = self._resolve_system_actor_id()
        if backup_user_id is None:
            logger.warning("Automatic backup skipped: admin actor not found")
            return False

        # Режим "startup_only" — создать только если бэкапов ещё нет ни одного.
        if prefs is not None and prefs.auto_backup_frequency == "startup_only":
            if last is not None:
                return False
            self.create_backup(actor_id=backup_user_id, reason="auto")
            return True

        # Режим "startup_daily" (дефолт) — создавать раз в сутки.
        if not last:
            self.create_backup(actor_id=backup_user_id, reason="auto")
            return True
        if datetime.now(UTC) - last.created_at >= timedelta(days=1):
            self.create_backup(actor_id=backup_user_id, reason="auto")
            return True
        return False

    def _write_meta(self, path: Path, reason: str) -> None:
        payload = {
            "path": self._metadata_path_value(path),
            "created_at": datetime.now(UTC).isoformat(),
            "reason": reason,
        }
        self._meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _metadata_path_value(self, path: Path) -> str:
        try:
            return path.resolve(strict=False).relative_to(self.backup_dir.resolve(strict=False)).as_posix()
        except (OSError, RuntimeError, ValueError):
            return path.name

    def _resolve_metadata_path(self, raw_path: str) -> Path | None:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        posix_path = PurePosixPath(raw_path.replace("\\", "/"))
        if posix_path.is_absolute() or ".." in posix_path.parts:
            return None
        return self.backup_dir.joinpath(*posix_path.parts)

    def _audit_event(self, actor_id: int, action: str, path: Path, reason: str) -> None:
        payload = json.dumps(
            {"path": str(path), "reason": reason},
            ensure_ascii=False,
        )
        with self.session_factory() as session:
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="backup",
                entity_id=path.name,
                action=action,
                payload_json=payload,
            )

    def _create_sqlite_backup(self, source: Path, target: Path) -> None:
        source_conn = sqlite3.connect(str(source), timeout=10)
        try:
            with suppress(sqlite3.DatabaseError):
                source_conn.execute("PRAGMA wal_checkpoint(FULL)")
            with sqlite3.connect(str(target), timeout=10) as target_conn:
                source_conn.backup(target_conn)
        finally:
            source_conn.close()

    def _resolve_system_actor_id(self) -> int | None:
        with self.session_factory() as session:
            for user in self.user_repo.list_users(session):
                if str(user.role) == "admin":
                    return int(user.id)
        return None
