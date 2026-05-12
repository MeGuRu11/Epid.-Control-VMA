from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.reporting.id_resolver import IdResolver
from app.infrastructure.db.models_sqlalchemy import Base, Department, RefMaterialType, User


def _make_session_factory(db_path: Path) -> Callable[[], AbstractContextManager[Session]]:
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


def test_resolve_material_type_returns_code_dash_name(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_material.db")
    with session_factory() as session:
        material = RefMaterialType(code="BLD", name="Кровь")
        session.add(material)
        session.flush()

        resolver = IdResolver(session)

        assert resolver.resolve_material_type(cast(int, material.id)) == "BLD — Кровь"


def test_resolve_material_type_unknown_id_returns_string_id(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_unknown.db")
    with session_factory() as session:
        resolver = IdResolver(session)

        assert resolver.resolve_material_type(999) == "999"


def test_resolve_material_type_none_returns_dash(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_none.db")
    with session_factory() as session:
        resolver = IdResolver(session)

        assert resolver.resolve_material_type(None) == "—"


def test_resolve_user_returns_username(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_user.db")
    with session_factory() as session:
        user = User(login="exchange_admin", password_hash="hash", role="admin", is_active=True)
        session.add(user)
        session.flush()

        resolver = IdResolver(session)

        assert resolver.resolve_user(cast(int, user.id)) == "exchange_admin"


def test_resolve_department_returns_name(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_department.db")
    with session_factory() as session:
        department = Department(name="Хирургия")
        session.add(department)
        session.flush()

        resolver = IdResolver(session)

        assert resolver.resolve_department(cast(int, department.id)) == "Хирургия"


def test_resolver_caches_after_first_load(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "id_resolver_cache.db")
    with session_factory() as session:
        first = RefMaterialType(code="BLD", name="Кровь")
        session.add(first)
        session.flush()

        resolver = IdResolver(session)
        assert resolver.resolve_material_type(cast(int, first.id)) == "BLD — Кровь"

        second = RefMaterialType(code="URN", name="Моча")
        session.add(second)
        session.flush()

        assert resolver.resolve_material_type(cast(int, second.id)) == str(cast(int, second.id))
