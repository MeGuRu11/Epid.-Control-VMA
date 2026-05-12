from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.dto.auth_dto import SessionContext
from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CreateV2Request,
    Form100DataV2Dto,
    Form100V2Filters,
)
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.models_sqlalchemy import Base
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.ui.form100_v2.form100_view import Form100ViewV2


class _Form100ServiceStub:
    def list_cards(
        self,
        *,
        filters: Form100V2Filters,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Any]:
        del filters, limit, offset
        return []


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


def _seed_operator(session_factory: Callable[[], AbstractContextManager[Session]]) -> int:
    repo = UserRepository()
    with session_factory() as session:
        operator = repo.create(session, login="operator", password_hash="x", role="operator")
        session.flush()
        return cast(int, operator.id)


def _seed_patient_case(
    session_factory: Callable[[], AbstractContextManager[Session]],
    *,
    full_name: str = "Иванов Иван Иванович",
    dob: date = date(1990, 1, 1),
) -> int:
    with session_factory() as session:
        patient = models.Patient(full_name=full_name, dob=dob, sex="M")
        session.add(patient)
        session.flush()
        emr_case = models.EmrCase(patient_id=cast(int, patient.id), hospital_case_no="EMR-1")
        session.add(emr_case)
        session.flush()
        return cast(int, emr_case.id)


def _create_request(*, emr_case_id: int | None = None) -> Form100CreateV2Request:
    return Form100CreateV2Request(
        emr_case_id=emr_case_id,
        main_full_name="Петров Пётр Петрович",
        main_unit="1 рота",
        main_diagnosis="Диагноз",
        birth_date=date(1992, 2, 2),
        data=Form100DataV2Dto(),
    )


def _card(
    *,
    emr_case_id: int | None,
    main_full_name: str = "Иванов Иван Иванович",
    birth_date: date | None = date(1990, 1, 1),
    patient_full_name: str | None = "Иванов Иван Иванович",
    patient_dob: date | None = date(1990, 1, 1),
) -> Form100CardV2Dto:
    now = datetime.now(tz=UTC)
    return Form100CardV2Dto(
        id="F100-1",
        emr_case_id=emr_case_id,
        created_at=now,
        created_by="operator",
        updated_at=now,
        updated_by="operator",
        status="DRAFT",
        version=1,
        is_archived=False,
        main_full_name=main_full_name,
        main_unit="1 рота",
        main_diagnosis="Диагноз",
        birth_date=birth_date,
        patient_full_name=patient_full_name,
        patient_dob=patient_dob,
    )


def _view(qapp: object) -> Form100ViewV2:
    del qapp
    return Form100ViewV2(
        form100_service=cast(Form100ServiceV2, _Form100ServiceStub()),
        reporting_service=None,
        session=SessionContext(user_id=1, login="operator", role="operator"),
    )

def _shown_view(qtbot: Any) -> Form100ViewV2:
    view = _view(qtbot)
    qtbot.addWidget(view)
    view.show()
    return view


def test_get_card_includes_patient_full_name_when_emr_exists(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "form100_patient_name.db")
    operator_id = _seed_operator(session_factory)
    emr_case_id = _seed_patient_case(session_factory, full_name="Иванов Иван Иванович")
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(_create_request(emr_case_id=emr_case_id), actor_id=operator_id)
    card = service.get_card(created.id)

    assert card.patient_full_name == "Иванов Иван Иванович"


def test_get_card_patient_full_name_is_none_when_no_emr(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "form100_no_emr.db")
    operator_id = _seed_operator(session_factory)
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(_create_request(emr_case_id=None), actor_id=operator_id)
    card = service.get_card(created.id)

    assert card.patient_full_name is None


def test_get_card_patient_dob_included(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path / "form100_patient_dob.db")
    operator_id = _seed_operator(session_factory)
    emr_case_id = _seed_patient_case(session_factory, dob=date(1990, 1, 1))
    service = Form100ServiceV2(session_factory=session_factory)

    created = service.create_card(_create_request(emr_case_id=emr_case_id), actor_id=operator_id)
    card = service.get_card(created.id)

    assert card.patient_dob == date(1990, 1, 1)


def test_check_diff_no_warning_when_names_match(qtbot) -> None:
    view = _shown_view(qtbot)
    try:
        view._check_patient_data_diff(_card(emr_case_id=1))

        assert not view._diff_banner.isVisible()
    finally:
        view.close()


def test_check_diff_shows_banner_when_names_differ(qtbot) -> None:
    view = _shown_view(qtbot)
    try:
        view._check_patient_data_diff(
            _card(
                emr_case_id=1,
                main_full_name="Петров Пётр Петрович",
                patient_full_name="Иванов Иван Иванович",
            )
        )

        assert view._diff_banner.isVisible()
        assert "ФИО в карточке" in view._diff_banner.text()
        assert "Иванов Иван Иванович" in view._diff_banner.text()
    finally:
        view.close()


def test_check_diff_shows_banner_when_dob_differs(qtbot) -> None:
    view = _shown_view(qtbot)
    try:
        view._check_patient_data_diff(
            _card(
                emr_case_id=1,
                birth_date=date(1992, 2, 2),
                patient_dob=date(1990, 1, 1),
            )
        )

        assert view._diff_banner.isVisible()
        assert "Дата рождения" in view._diff_banner.text()
        assert "02.02.1992" in view._diff_banner.text()
        assert "01.01.1990" in view._diff_banner.text()
    finally:
        view.close()


def test_check_diff_no_banner_when_no_emr_case(qtbot) -> None:
    view = _shown_view(qtbot)
    try:
        view._check_patient_data_diff(_card(emr_case_id=None))

        assert not view._diff_banner.isVisible()
    finally:
        view.close()


def test_check_diff_hides_banner_when_names_then_match(qtbot) -> None:
    view = _shown_view(qtbot)
    try:
        view._check_patient_data_diff(
            _card(
                emr_case_id=1,
                main_full_name="Петров Пётр Петрович",
                patient_full_name="Иванов Иван Иванович",
            )
        )
        assert view._diff_banner.isVisible()

        view._check_patient_data_diff(_card(emr_case_id=1))

        assert not view._diff_banner.isVisible()
    finally:
        view.close()
