from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def transactional(session_factory) -> Iterator[Session]:
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
