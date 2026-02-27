from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import User
from .base import RepoBase


class UserRepo(RepoBase):
    def has_any(self) -> bool:
        with self.tx() as s:
            return s.execute(select(User.id).limit(1)).first() is not None

    def get_by_login(self, login: str) -> User | None:
        with self.tx() as s:
            return s.execute(select(User).where(User.login == login)).scalar_one_or_none()

    def create(self, login: str, password_hash: str, role: str = "operator") -> int:
        with self.tx() as s:
            user = User(login=login, password_hash=password_hash, role=role, is_active=True)
            s.add(user)
            s.flush()
            return int(user.id)

    def set_active(self, user_id: int, is_active: bool) -> bool:
        with self.tx() as s:
            user = s.get(User, user_id)
            if not user:
                return False
            user.is_active = is_active
            return True

    def set_password_hash(self, user_id: int, password_hash: str) -> bool:
        with self.tx() as s:
            user = s.get(User, user_id)
            if not user:
                return False
            user.password_hash = password_hash
            return True

    def list_users(self) -> list[User]:
        with self.tx() as s:
            return list(s.execute(select(User).order_by(User.created_at.desc())).scalars().all())
