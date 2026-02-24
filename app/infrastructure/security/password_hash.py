from __future__ import annotations

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_argon2_hasher = PasswordHasher()


def hash_password(password: str, scheme: str = "argon2") -> str:
    if not password:
        raise ValueError("Password must not be empty")

    if scheme == "argon2":
        return _argon2_hasher.hash(password)
    if scheme == "bcrypt":
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    raise ValueError(f"Unsupported scheme: {scheme}")


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("$argon2"):
        try:
            return _argon2_hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False
    if hashed.startswith(("$2a$", "$2b$", "$2y$")):
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    raise ValueError("Unknown password hash format")
