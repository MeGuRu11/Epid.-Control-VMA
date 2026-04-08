from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import DATA_DIR, DB_FILE
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope


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
    ) -> None:
        self.audit_repo = audit_repo
        self.user_repo = user_repo or UserRepository()
        self.backup_dir = DATA_DIR / "backups"
        self._prepare_artifacts_dir(self.backup_dir)
        self._meta_path = self.backup_dir / "last_backup.json"

    def _prepare_artifacts_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        # Best-effort: some filesystems/platforms ignore chmod semantics.
        with suppress(OSError):
            os.chmod(path, 0o700)

    def _require_admin_access(self, *, actor_id: int, action: str) -> None:
        if actor_id is None:  # raise on missing actor_id
            raise ValueError("actor_id обязателен для операций записи")
        with session_scope() as session:
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
            path = Path(data["path"])
            created_at = datetime.fromisoformat(data["created_at"])
            reason = data.get("reason", "unknown")
            if not path.exists():
                return None
            return BackupInfo(path=path, created_at=created_at, reason=reason)
        except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as exc:
            logging.getLogger(__name__).warning("Failed to parse backup metadata: %s", exc)
            return None

    def create_backup(self, *, actor_id: int, reason: str = "manual") -> Path:
        self._require_admin_access(actor_id=actor_id, action="backup_create")
        if not DB_FILE.exists():
            raise FileNotFoundError(f"Р‘Р°Р·Р° РґР°РЅРЅС‹С… РЅРµ РЅР°Р№РґРµРЅР°: {DB_FILE}")
        # TODO SECURITY: добавить шифрование бэкапов/экспортов (AES-GCM)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"app_{timestamp}.db"
        try:
            self._create_sqlite_backup(DB_FILE, backup_path)
        except (OSError, sqlite3.Error) as exc:
            # Fallback for environments where sqlite backup API is unavailable.
            logging.getLogger(__name__).warning("SQLite backup API failed, fallback to file copy: %s", exc)
            shutil.copy2(DB_FILE, backup_path)
        self._write_meta(backup_path, reason)
        self._audit_event(actor_id, "backup_create", backup_path, reason)
        return backup_path

    def restore_backup(self, backup_path: Path, *, actor_id: int) -> None:
        self._require_admin_access(actor_id=actor_id, action="backup_restore")
        if not backup_path.exists():
            raise FileNotFoundError(f"Р¤Р°Р№Р» СЂРµР·РµСЂРІРЅРѕР№ РєРѕРїРёРё РЅРµ РЅР°Р№РґРµРЅ: {backup_path}")
        # Close pooled connections before overwriting DB file.
        try:
            from app.infrastructure.db.session import engine as sa_engine

            sa_engine.dispose()
        except (AttributeError, ImportError, RuntimeError) as exc:
            logging.getLogger(__name__).warning("Failed to dispose SQLAlchemy engine before restore: %s", exc)
        # Safety copy of current DB before overwrite.
        if DB_FILE.exists():
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            safety_path = self.backup_dir / f"pre_restore_{timestamp}.db"
            shutil.copy2(DB_FILE, safety_path)
        shutil.copy2(backup_path, DB_FILE)
        self._write_meta(backup_path, "restore")
        self._audit_event(actor_id, "backup_restore", backup_path, "restore")

    def ensure_daily_backup(self) -> bool:
        last = self.get_last_backup()
        backup_user_id = self._resolve_system_actor_id()
        if backup_user_id is None:
            logging.getLogger(__name__).warning("Automatic backup skipped: admin actor not found")
            return False
        if not last:
            self.create_backup(actor_id=backup_user_id, reason="auto")
            return True
        if datetime.now(UTC) - last.created_at >= timedelta(days=1):
            self.create_backup(actor_id=backup_user_id, reason="auto")
            return True
        return False

    def _write_meta(self, path: Path, reason: str) -> None:
        payload = {
            "path": str(path),
            "created_at": datetime.now(UTC).isoformat(),
            "reason": reason,
        }
        self._meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _audit_event(self, actor_id: int, action: str, path: Path, reason: str) -> None:
        payload = json.dumps(
            {"path": str(path), "reason": reason},
            ensure_ascii=False,
        )
        with session_scope() as session:
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
        with session_scope() as session:
            for user in self.user_repo.list_users(session):
                if str(user.role) == "admin":
                    return int(user.id)
        return None



