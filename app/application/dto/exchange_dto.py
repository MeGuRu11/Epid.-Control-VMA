from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import NotRequired, Protocol, TypedDict

from app.application.dto.form100_v2_dto import Form100V2Filters


class ExchangeManifestFileEntry(TypedDict):
    name: str
    sha256: str
    size: int


class ExchangeManifest(TypedDict):
    schema_version: str
    exported_at: str
    exported_by: str | None
    files: list[ExchangeManifestFileEntry]


class ExchangeImportErrorEntry(TypedDict):
    scope: str
    row: int
    message: str


class ExchangeTableStats(TypedDict):
    rows: int
    added: int
    updated: int
    skipped: int
    errors: int


class ExchangeImportSummary(TypedDict):
    rows_total: int
    added: int
    updated: int
    skipped: int
    errors: int


class ExcelExportResult(TypedDict):
    path: str
    counts: dict[str, int]


class ZipExportResult(ExcelExportResult):
    sha256: str


class ExcelImportResult(TypedDict):
    path: str
    counts: dict[str, int]
    details: dict[str, ExchangeTableStats]
    errors: list[ExchangeImportErrorEntry]
    error_count: int
    summary: ExchangeImportSummary
    error_log_path: NotRequired[str | None]


class ZipImportResult(TypedDict):
    path: str
    counts: dict[str, int]
    details: dict[str, ExchangeTableStats]
    errors: list[ExchangeImportErrorEntry]
    error_count: int
    error_log_path: str | None
    summary: ExchangeImportSummary
    sha256: str


class CsvExportResult(TypedDict):
    path: str
    count: int


class CsvImportResult(TypedDict):
    path: str
    count: int
    counts: dict[str, int]
    details: dict[str, ExchangeTableStats]
    errors: list[ExchangeImportErrorEntry]
    error_count: int
    error_log_path: str | None
    summary: ExchangeImportSummary


class LegacyJsonExportResult(TypedDict):
    path: str
    counts: dict[str, int]


class LegacyJsonImportResult(TypedDict):
    path: str
    counts: dict[str, int]
    details: dict[str, ExchangeTableStats]
    errors: list[ExchangeImportErrorEntry]
    error_count: int
    error_log_path: str | None
    summary: ExchangeImportSummary


class Form100ExchangeService(Protocol):
    def export_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int,
        card_id: str | None = None,
        filters: Form100V2Filters | None = None,
        exported_by: str | None = None,
    ) -> Mapping[str, object]: ...

    def import_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int | None,
        mode: str = "merge",
        system: bool = False,
    ) -> Mapping[str, object]: ...
