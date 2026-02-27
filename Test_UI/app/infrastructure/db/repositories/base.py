from __future__ import annotations

from app.infrastructure.db.session import make_session_factory, transactional


class RepoBase:
    def __init__(self, engine):
        self._engine = engine
        self._session_factory = make_session_factory(engine)

    def tx(self):
        return transactional(self._session_factory)
