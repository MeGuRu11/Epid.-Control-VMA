
from __future__ import annotations
import hashlib, secrets, hmac, base64

_ITER = 210_000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER, dklen=32)
    return "pbkdf2_sha256$%d$%s$%s" % (_ITER, base64.b64encode(salt).decode(), base64.b64encode(dk).decode())

def verify_password(password: str, hashed: str) -> bool:
    try:
        algo, it_s, salt_b64, dk_b64 = hashed.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        it = int(it_s)
        salt = base64.b64decode(salt_b64.encode())
        dk = base64.b64decode(dk_b64.encode())
        cand = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, it, dklen=len(dk))
        return hmac.compare_digest(cand, dk)
    except Exception:
        return False
