from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginIn:
    login: str
    password: str


@dataclass(frozen=True)
class UserCreateIn:
    login: str
    password: str
    role: str = "operator"


@dataclass(frozen=True)
class SessionOut:
    user_id: int
    login: str
    role: str
