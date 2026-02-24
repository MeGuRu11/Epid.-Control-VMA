from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.form100_v2_dto import Form100CreateV2Request, Form100DataV2Dto
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.user_repo import UserRepository


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


def seed_users(session_factory: Callable[[], AbstractContextManager[Session]]) -> tuple[int, int]:
    repo = UserRepository()
    with session_factory() as session:
        admin = repo.create(session, login="admin", password_hash="x", role="admin")
        operator = repo.create(session, login="operator", password_hash="x", role="operator")
        session.flush()
        return cast(int, admin.id), cast(int, operator.id)


def make_create_request() -> Form100CreateV2Request:
    return Form100CreateV2Request(
        main_full_name="Ivanov Ivan",
        main_unit="Unit 1",
        main_id_tag="A12345",
        main_diagnosis="Shoulder injury",
        birth_date=date(1992, 1, 2),
        data=Form100DataV2Dto.model_validate(
            {
                "main": {
                    "main_full_name": "Ivanov Ivan",
                    "main_unit": "Unit 1",
                    "main_id_tag": "A12345",
                },
                "bottom": {"main_diagnosis": "Shoulder injury"},
                "medical_help": {"mp_antibiotic": False, "mp_analgesic": False},
                "flags": {"flag_emergency": False, "flag_radiation": False, "flag_sanitation": False},
                "bodymap_gender": "M",
                "bodymap_annotations": [],
                "bodymap_tissue_types": [],
            }
        ),
    )


def test_form100_v2_delete_requires_admin_role(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path / "form100_v2_roles.db")
    admin_id, operator_id = seed_users(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(make_create_request(), actor_id=operator_id)

    with pytest.raises(ValueError):
        service.delete_card(created.id, actor_id=operator_id)

    still_exists = service.get_card(created.id)
    assert still_exists.id == created.id

    service.delete_card(created.id, actor_id=admin_id)
    with pytest.raises(ValueError):
        service.get_card(created.id)
