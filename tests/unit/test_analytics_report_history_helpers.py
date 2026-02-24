from __future__ import annotations

from datetime import UTC, date, datetime

from app.ui.analytics.report_history_helpers import (
    format_report_verification,
    report_history_column_widths,
    to_report_history_view_row,
)


def test_format_report_verification_known_status_and_fallback() -> None:
    assert format_report_verification({"status": "ok"}) == "OK"
    assert format_report_verification({"status": "mismatch"}) == "Хэш не совпал"
    assert format_report_verification({"status": "custom", "message": "msg"}) == "msg"
    assert format_report_verification({"status": "custom"}) == "Не проверен"


def test_to_report_history_view_row_formats_datetime_summary_and_artifact() -> None:
    row = to_report_history_view_row(
        {
            "id": 12,
            "report_type": "analytics",
            "created_at": datetime(2026, 2, 13, 14, 25, tzinfo=UTC),
            "created_by": "admin",
            "summary": {"total": 17},
            "verification": {"status": "ok"},
            "artifact_sha256": "abc123",
            "artifact_path": "C:/tmp/report.xlsx",
        }
    )

    assert row.report_run_id == 12
    assert row.report_type == "analytics"
    assert row.created_text == "13.02.2026 14:25"
    assert row.created_by == "admin"
    assert row.total_text == "17"
    assert row.verification_text == "OK"
    assert row.artifact_sha256 == "abc123"
    assert row.artifact_path == "C:/tmp/report.xlsx"


def test_to_report_history_view_row_supports_date_created_at() -> None:
    row = to_report_history_view_row({"id": 1, "created_at": date(2026, 2, 1)})
    assert row.created_text == "01.02.2026"


def test_report_history_column_widths_match_expected_contract() -> None:
    assert report_history_column_widths() == {
        0: 60,
        1: 90,
        2: 150,
        3: 110,
        4: 70,
        5: 140,
        6: 220,
    }
