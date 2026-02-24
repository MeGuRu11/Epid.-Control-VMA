from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 8192) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        _update_hash_stream(h, f, chunk_size)
    return h.hexdigest()


def _update_hash_stream(h, stream: BinaryIO, chunk_size: int) -> None:
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        h.update(chunk)
