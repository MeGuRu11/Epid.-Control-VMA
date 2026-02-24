from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.infrastructure.db.models_sqlalchemy import User


class UserRepository:
    def get_by_login(self, session: Session, login: str) -> User | None:
        stmt = select(User).where(User.login == login)
        return session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, session: Session, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    def list_users(self, session: Session, query: str | None = None) -> list[User]:
        stmt = select(User)
        if query:
            stmt = stmt.where(User.login.ilike(f"%{query}%"))
        stmt = stmt.order_by(User.login.asc())
        return list(session.execute(stmt).scalars())

    def create(self, session: Session, login: str, password_hash: str, role: str) -> User:
        user = User(login=login, password_hash=password_hash, role=role, is_active=True)
        session.add(user)
        session.flush()  # populate id
        return user

    def set_password(self, session: Session, user_id: int, password_hash: str) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
        )
        session.execute(stmt)

    def set_active(self, session: Session, user_id: int, is_active: bool) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active)
        )
        session.execute(stmt)
