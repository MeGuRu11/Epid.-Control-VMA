from __future__ import annotations

import builtins
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from alembic.util.exc import CommandError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.bootstrap import startup


def test_check_startup_prerequisites_handles_write_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root_dir = tmp_path
    (root_dir / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    (root_dir / "app" / "infrastructure" / "db" / "migrations").mkdir(parents=True)
    db_file = root_dir / "data" / "app.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)

    critical_calls: list[tuple] = []
    monkeypatch.setattr(startup.QMessageBox, "critical", lambda *args, **kwargs: critical_calls.append(args))

    original_write_text = Path.write_text

    def _failing_write(self: Path, data: str, encoding: str = "utf-8", errors: str | None = None) -> int:
        if self.name == ".write_test":
            raise OSError("permission denied")
        kwargs = {"encoding": encoding}
        if errors is not None:
            kwargs["errors"] = errors
        return original_write_text(self, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", _failing_write)

    assert startup.check_startup_prerequisites(root_dir, db_file) is False
    assert len(critical_calls) == 1


def test_has_users_handles_sqlalchemy_error() -> None:
    class _BrokenSession:
        def execute(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise SQLAlchemyError("db unavailable")

    @contextmanager
    def _session_factory() -> Iterator[Session]:
        yield cast(Session, _BrokenSession())

    assert startup.has_users(_session_factory) is False


def test_warn_missing_plot_dependencies_reports_missing(monkeypatch) -> None:
    warning_calls: list[tuple] = []
    monkeypatch.setattr(startup.QMessageBox, "warning", lambda *args, **kwargs: warning_calls.append(args))

    original_import = builtins.__import__

    def _failing_import(name: str, *args, **kwargs):  # noqa: ANN002, ANN003
        if name in {"pyqtgraph", "matplotlib"}:
            raise ImportError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _failing_import)

    startup.warn_missing_plot_dependencies()
    assert len(warning_calls) == 1


def test_run_migrations_falls_back_to_heads_on_multiple_heads_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root_dir = tmp_path
    (root_dir / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    db_file = root_dir / "app.db"
    log_dir = root_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    calls: list[str] = []

    def _upgrade(_cfg, target: str) -> None:  # noqa: ANN001
        calls.append(target)
        if target == "head":
            raise CommandError("Multiple heads are present")

    monkeypatch.setattr(startup.command, "upgrade", _upgrade)

    assert startup.run_migrations(root_dir, "sqlite:///tmp.db", log_dir, db_file) is True
    assert calls == ["head", "heads"]


def test_run_migrations_writes_error_log_when_upgrade_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root_dir = tmp_path
    (root_dir / "alembic.ini").write_text("[alembic]\n", encoding="utf-8")
    db_file = root_dir / "app.db"
    log_dir = root_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    critical_calls: list[tuple] = []
    monkeypatch.setattr(startup.QMessageBox, "critical", lambda *args, **kwargs: critical_calls.append(args))

    def _raise_upgrade(_cfg, _target: str) -> None:  # noqa: ANN001
        raise CommandError("boom")

    monkeypatch.setattr(startup.command, "upgrade", _raise_upgrade)

    ok = startup.run_migrations(root_dir, "sqlite:///tmp.db", log_dir, db_file)
    assert ok is False
    assert len(critical_calls) == 1

    error_log = log_dir / "migration_error.log"
    assert error_log.exists()
    log_text = error_log.read_text(encoding="utf-8")
    assert "Migration error" in log_text
