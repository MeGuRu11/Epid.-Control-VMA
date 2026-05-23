#!/usr/bin/env python
# ruff: noqa: E402, T201
"""Round-trip check: импорт собственных экспортов из docs/sample_exports/.

Usage:
    python scripts/generate_sample_exports.py
    python scripts/test_import_roundtrip.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.application.services.exchange_service import ExchangeService
from app.infrastructure.db.models_sqlalchemy import User
from app.infrastructure.db.session import session_scope

OUT_DIR = Path(__file__).parent.parent / "docs" / "sample_exports"


def _resolve_actor_id() -> int:
    with session_scope() as session:
        actor = session.execute(
            select(User)
            .where(User.role == "admin", User.is_active.is_(True))
            .order_by(User.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        if actor is not None:
            return int(actor.id)

        actor = User(login="demo-admin", password_hash="demo", role="admin", is_active=True)
        session.add(actor)
        session.flush()
        return int(actor.id)


def _result_error_count(result: dict[str, Any]) -> int:
    return int(result.get("error_count", 0) or 0)


def main() -> int:
    svc = ExchangeService()
    actor_id = _resolve_actor_id()
    results: list[tuple[str, bool, str]] = []

    excel_path = OUT_DIR / "full_export.xlsx"
    if excel_path.exists():
        try:
            result = cast(dict[str, Any], svc.import_excel(excel_path, actor_id=actor_id, mode="merge"))
            errors = _result_error_count(result)
            results.append(("Excel", errors == 0, f"{errors} ошибок"))
            for err in cast(list[object], result.get("errors", []))[:5]:
                print(f"  Excel ERR: {err}")
        except Exception as exc:  # noqa: BLE001 - smoke script reports failures compactly.
            results.append(("Excel", False, f"{type(exc).__name__}: {str(exc)[:200]}"))
    else:
        results.append(("Excel", False, "файл не найден"))

    zip_path = OUT_DIR / "full_export.zip"
    if zip_path.exists():
        try:
            result = cast(dict[str, Any], svc.import_zip(zip_path, actor_id=actor_id, mode="merge"))
            errors = _result_error_count(result)
            results.append(("ZIP", errors == 0, f"{errors} ошибок"))
            for err in cast(list[object], result.get("errors", []))[:5]:
                print(f"  ZIP ERR: {err}")
        except Exception as exc:  # noqa: BLE001 - smoke script reports failures compactly.
            results.append(("ZIP", False, f"{type(exc).__name__}: {str(exc)[:200]}"))
    else:
        results.append(("ZIP", False, "файл не найден"))

    for table in ("patients", "lab_sample", "sanitary_sample", "emr_case"):
        csv_path = OUT_DIR / f"csv_{table}.csv"
        if not csv_path.exists():
            results.append((f"CSV {table}", False, "файл не найден"))
            continue
        try:
            result = cast(dict[str, Any], svc.import_csv(csv_path, table, actor_id=actor_id, mode="merge"))
            errors = _result_error_count(result)
            rows = cast(dict[str, Any], result.get("details", {})).get(table, {}).get("rows", "?")
            results.append((f"CSV {table}", errors == 0, f"строк {rows}, ошибок {errors}"))
            for err in cast(list[object], result.get("errors", []))[:3]:
                print(f"  CSV {table} ERR: {err}")
        except Exception as exc:  # noqa: BLE001 - smoke script reports failures compactly.
            results.append((f"CSV {table}", False, f"{type(exc).__name__}: {str(exc)[:200]}"))

    json_path = OUT_DIR / "full_export.json"
    if json_path.exists():
        try:
            result = cast(dict[str, Any], svc.import_json(json_path, actor_id=actor_id, mode="merge"))
            errors = _result_error_count(result)
            results.append(("JSON", errors == 0, f"{errors} ошибок"))
            for err in cast(list[object], result.get("errors", []))[:5]:
                print(f"  JSON ERR: {err}")
        except Exception as exc:  # noqa: BLE001 - smoke script reports failures compactly.
            results.append(("JSON", False, f"{type(exc).__name__}: {str(exc)[:200]}"))
    else:
        results.append(("JSON", False, "файл не найден"))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    print(f"\nИтого: {passed} PASS / {failed} FAIL")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
