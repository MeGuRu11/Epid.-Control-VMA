from __future__ import annotations

from typing import TypedDict

from app.domain.types import JSONDict


class Form100ManifestFileEntry(TypedDict):
    name: str
    sha256: str
    size: int


class Form100Changes(TypedDict):
    before: dict[str, object]
    after: dict[str, object]


class Form100PackageSummary(TypedDict):
    rows_total: int
    added: int
    updated: int
    skipped: int
    errors: int


class Form100ImportError(TypedDict):
    id: str
    error: str


class Form100PdfExportResult(TypedDict):
    path: str
    card_id: str
    sha256: str


class Form100PackageExportResult(TypedDict):
    path: str
    counts: dict[str, int]
    sha256: str


class Form100PackageImportResult(TypedDict):
    path: str
    counts: dict[str, int]
    summary: Form100PackageSummary
    error_count: int
    errors: list[Form100ImportError]


class Form100PayloadMap(TypedDict, total=False):
    before: JSONDict
    after: JSONDict
