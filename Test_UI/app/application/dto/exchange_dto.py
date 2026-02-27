from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangePackageIn:
    direction: str
    package_format: str
    file_path: str
    sha256: str
    notes: str | None = None
