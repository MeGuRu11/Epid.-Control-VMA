from __future__ import annotations

import json
import zipfile
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db.models_sqlalchemy import Base, User


def make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    @contextmanager
    def _session_scope() -> Iterator[Session]:
        session: Session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _session_scope


def seed_actor(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    with session_factory() as session:
        actor = User(login="exchange_admin", password_hash="hash", role="admin", is_active=True)
        session.add(actor)
        session.flush()
        return cast(int, actor.id)


def _write_zip(zip_path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)


def test_import_zip_rejects_unsafe_archive_path(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_unsafe.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    archive_path = tmp_path / "unsafe.zip"
    _write_zip(archive_path, {"../evil.txt": "bad"})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path, actor_id=actor_id)

    message = str(exc_info.value)
    assert "ZIP" in message
    assert "evil.txt" in message


def test_import_zip_reports_missing_manifest(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_no_manifest.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    archive_path = tmp_path / "no_manifest.zip"
    _write_zip(archive_path, {"export.xlsx": "placeholder"})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path, actor_id=actor_id)

    assert "manifest.json" in str(exc_info.value)


def test_import_zip_reports_missing_file_from_manifest(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "exchange_missing_payload.db")
    actor_id = seed_actor(session_factory)
    service = ExchangeService(session_factory=session_factory)
    archive_path = tmp_path / "missing_payload.zip"
    manifest = {
        "schema_version": "1.0",
        "files": [{"name": "export.xlsx", "sha256": "deadbeef"}],
    }
    _write_zip(archive_path, {"manifest.json": json.dumps(manifest, ensure_ascii=False)})

    with pytest.raises(ValueError) as exc_info:
        service.import_zip(archive_path, actor_id=actor_id)

    assert "export.xlsx" in str(exc_info.value)
