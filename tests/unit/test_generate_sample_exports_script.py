from __future__ import annotations

import dataclasses
import importlib.util
import inspect
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.models_sqlalchemy import Base, User


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).parents[2] / "scripts" / "generate_sample_exports.py"
    spec = importlib.util.spec_from_file_location("generate_sample_exports", script_path)

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_sample_exports_importable() -> None:
    """Скрипт генерации демо-выгрузок должен импортироваться без ошибок."""
    module = _load_script_module()

    assert hasattr(module, "run_exports")
    assert hasattr(module, "main")


def test_seed_stats_has_form100_field() -> None:
    """SeedStats должен содержать поле form100_cards."""
    from scripts.seed_demo_data import SeedStats

    fields = [field.name for field in dataclasses.fields(SeedStats)]
    assert "form100_cards" in fields


def test_seed_demo_uses_russian_patient_categories() -> None:
    """Демо-seed должен использовать доменные категории пациентов."""
    import scripts.seed_demo_data as seed_mod
    from app.domain.constants import MilitaryCategory

    source = inspect.getsource(seed_mod)
    assert any(value in source for value in MilitaryCategory.values())
    assert '"hospital"' not in source
    assert '"outpatient"' not in source


def test_resolve_export_actor_creates_demo_admin_for_empty_db(tmp_path: Path) -> None:
    """Генератор должен сам подготовить admin actor для чистой demo-БД."""
    module = _load_script_module()
    engine = create_engine(f"sqlite:///{(tmp_path / 'demo.db').as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    @contextmanager
    def local_session_scope() -> Iterator[Session]:
        session = session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    actor_id = module._resolve_export_actor_id(local_session_scope)

    with local_session_scope() as session:
        user = session.execute(select(User).where(User.id == actor_id)).scalar_one()
        assert user.login == "demo-admin"
        assert user.role == "admin"
        assert user.is_active is True
