from app.infrastructure.security.password_hash import hash_password, verify_password


def test_hash_and_verify_argon2():
    raw = "Secret123!"
    hashed = hash_password(raw, scheme="argon2")
    assert hashed.startswith("$argon2")
    assert verify_password(raw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_and_verify_bcrypt():
    raw = "AnotherPass#1"
    hashed = hash_password(raw, scheme="bcrypt")
    assert hashed.startswith("$2")
    assert verify_password(raw, hashed) is True
    assert verify_password("nope", hashed) is False
