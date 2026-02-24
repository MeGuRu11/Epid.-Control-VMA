from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class ReportHistoryViewRow:
    report_run_id: int
    report_type: str
    created_text: str
    created_by: str
    total_text: str
    verification_text: str
    artifact_sha256: str
    artifact_path: str


def report_history_column_widths() -> dict[int, int]:
    return {
        0: 60,
        1: 90,
        2: 150,
        3: 110,
        4: 70,
        5: 140,
        6: 220,
    }


def format_report_verification(verification: dict[str, Any]) -> str:
    status = str(verification.get("status") or "")
    mapping = {
        "ok": "OK",
        "mismatch": "Хэш не совпал",
        "missing": "Файл не найден",
        "error": "Ошибка проверки",
        "available": "Файл найден",
        "pending": "Не проверен",
    }
    if status in mapping:
        return mapping[status]
    message = str(verification.get("message") or "")
    return message or "Не проверен"


def to_report_history_view_row(item: dict[str, Any]) -> ReportHistoryViewRow:
    row_id = int(item.get("id", 0))
    summary = item.get("summary", {})
    verification = item.get("verification", {})
    created_at = item.get("created_at")
    created_text = _format_created_text(created_at)
    total_text = str(summary.get("total", "")) if isinstance(summary, dict) else ""
    return ReportHistoryViewRow(
        report_run_id=row_id,
        report_type=str(item.get("report_type") or ""),
        created_text=created_text,
        created_by=str(item.get("created_by") or ""),
        total_text=total_text,
        verification_text=format_report_verification(verification if isinstance(verification, dict) else {}),
        artifact_sha256=str(item.get("artifact_sha256") or ""),
        artifact_path=str(item.get("artifact_path") or ""),
    )


def _format_created_text(value: object) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return ""
