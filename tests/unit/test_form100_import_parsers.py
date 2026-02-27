from __future__ import annotations

import importlib
from datetime import UTC, date, datetime

form100_import_mod = importlib.import_module("app.infrastructure.import.form100_import")
_parse_date = form100_import_mod._parse_date
_parse_datetime = form100_import_mod._parse_datetime


def test_parse_datetime_supports_iso_and_legacy_formats() -> None:
    iso = _parse_datetime("2026-02-27T10:15:00+00:00")
    legacy = _parse_datetime("27.02.2026 10:15")

    assert iso == datetime(2026, 2, 27, 10, 15, 0, tzinfo=UTC)
    assert legacy == datetime(2026, 2, 27, 10, 15, 0, tzinfo=UTC)


def test_parse_datetime_returns_none_for_invalid_value() -> None:
    assert _parse_datetime("not-a-date") is None


def test_parse_date_supports_iso_and_legacy_formats() -> None:
    assert _parse_date("2026-02-27") == date(2026, 2, 27)
    assert _parse_date("27.02.2026") == date(2026, 2, 27)


def test_parse_date_returns_none_for_invalid_value() -> None:
    assert _parse_date("31.02.2026") is None
