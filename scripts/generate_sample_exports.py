#!/usr/bin/env python
# ruff: noqa: E402,T201
"""Generate all possible export files with demo data.

Usage:
    python scripts/generate_sample_exports.py [--skip-seed] [--out-dir PATH]

Options:
    --skip-seed   Skip seeding demo data and use existing DB content.
    --out-dir     Output directory (default: docs/sample_exports).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import NamedTuple
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.application.dto.analytics_dto import AnalyticsSearchRequest
from app.application.services.analytics_service import AnalyticsService
from app.application.services.exchange_service import ExchangeService
from app.application.services.form100_service_v2 import Form100ServiceV2
from app.application.services.reference_service import ReferenceService
from app.application.services.reporting_service import ReportingService
from app.config import DB_FILE
from app.infrastructure.db.models_sqlalchemy import Form100V2, User
from app.infrastructure.db.session import session_scope
from app.infrastructure.security.password_hash import hash_password

ACTOR_ID = 1
DEMO_ADMIN_LOGIN = "demo-admin"
EXPORT_TABLES = ("lab_sample", "sanitary_sample", "patients", "emr_case")


class ExportResult(NamedTuple):
    filename: str
    status: str
    size_kb: float
    error: str


def _file_size_kb(path: Path) -> float:
    return round(path.stat().st_size / 1024, 1)


def _first_form100_card_id() -> str | None:
    with session_scope() as session:
        card = session.execute(select(Form100V2).limit(1)).scalar_one_or_none()
        return str(card.id) if card is not None else None


def _resolve_export_actor_id(
    session_factory: Callable[[], AbstractContextManager[Session]] = session_scope,
) -> int:
    with session_factory() as session:
        preferred_actor = session.get(User, ACTOR_ID)
        if (
            preferred_actor is not None
            and preferred_actor.role == "admin"
            and preferred_actor.is_active is True
        ):
            return ACTOR_ID

        admin = (
            session.execute(
                select(User)
                .where(User.role == "admin")
                .where(User.is_active.is_(True))
                .order_by(User.id)
                .limit(1)
            )
            .scalars()
            .first()
        )
        if admin is not None:
            return int(admin.id)

        login = DEMO_ADMIN_LOGIN
        suffix = 2
        while session.execute(select(User.id).where(User.login == login)).first() is not None:
            login = f"{DEMO_ADMIN_LOGIN}-{suffix}"
            suffix += 1

        demo_admin = User(
            login=login,
            password_hash=hash_password(uuid4().hex),
            role="admin",
            is_active=True,
        )
        session.add(demo_admin)
        session.flush()
        return int(demo_admin.id)


def run_exports(out_dir: Path, skip_seed: bool) -> list[ExportResult]:
    results: list[ExportResult] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    if not skip_seed:
        print("Засеваем демо-данные...")
        from scripts.seed_demo_data import seed

        with session_scope() as session:
            seed(session, clear=True)
        print("OK")

    actor_id = _resolve_export_actor_id()
    analytics_service = AnalyticsService(session_factory=session_scope)
    form100_service = Form100ServiceV2(session_factory=session_scope)
    reference_service = ReferenceService(session_factory=session_scope)
    exchange_service = ExchangeService(
        session_factory=session_scope,
        form100_v2_service=form100_service,
    )
    reporting_service = ReportingService(
        analytics_service=analytics_service,
        form100_v2_service=form100_service,
        reference_service=reference_service,
        session_factory=session_scope,
    )
    request = AnalyticsSearchRequest()

    def _run(filename: str, export_fn: Callable[[Path], object]) -> None:
        path = out_dir / filename
        try:
            path.unlink(missing_ok=True)
            export_fn(path)
            if not path.exists():
                raise RuntimeError("Файл не был создан")
            size_kb = _file_size_kb(path)
            results.append(ExportResult(filename, "OK", size_kb, ""))
            print(f"  OK  {filename} ({size_kb:.1f} KB)")
        except Exception as exc:  # noqa: BLE001
            results.append(ExportResult(filename, "ERROR", 0.0, str(exc)))
            print(f"  ERR {filename}: {exc}")

    print("\n[A] Analytics-отчёты")
    _run(
        "analytics.pdf",
        lambda path: reporting_service.export_analytics_pdf(
            request,
            path,
            actor_id,
        ),
    )
    _run(
        "analytics.xlsx",
        lambda path: reporting_service.export_analytics_xlsx(
            request,
            path,
            actor_id,
        ),
    )

    print("\n[B] Form100 PDF")
    card_id = _first_form100_card_id()
    if card_id is None:
        results.append(ExportResult("form100_card.pdf", "SKIP", 0.0, "Нет Form100 в БД"))
        print("  SKIP form100_card.pdf: нет Form100 в БД")
    else:
        _run(
            "form100_card.pdf",
            lambda path: reporting_service.export_form100_pdf(
                card_id=card_id,
                file_path=path,
                actor_id=actor_id,
            ),
        )

    print("\n[C] Полный пакет обмена")
    _run("full_export.xlsx", lambda path: exchange_service.export_excel(path, actor_id=actor_id))
    _run(
        "full_export.zip",
        lambda path: exchange_service.export_zip(path, exported_by="demo", actor_id=actor_id),
    )
    _run(
        "full_export.json",
        lambda path: exchange_service.export_json(path, exported_by="demo", actor_id=actor_id),
    )
    _run(
        "form100_package.zip",
        lambda path: exchange_service.export_form100_package_zip(path, actor_id=actor_id),
    )

    print("\n[D] CSV по таблицам")
    for table in EXPORT_TABLES:
        def export_table_csv(path: Path, table_name: str = table) -> object:
            return exchange_service.export_csv(path, table_name, actor_id=actor_id)

        _run(
            f"csv_{table}.csv",
            export_table_csv,
        )

    print("\n[E] PDF по таблицам")
    for table in EXPORT_TABLES:
        def export_table_pdf(path: Path, table_name: str = table) -> object:
            return exchange_service.export_pdf(path, table_name, actor_id=actor_id)

        _run(
            f"pdf_{table}.pdf",
            export_table_pdf,
        )

    return results


def _print_summary(results: list[ExportResult], out_dir: Path) -> None:
    ok = [result for result in results if result.status == "OK"]
    skip = [result for result in results if result.status == "SKIP"]
    error = [result for result in results if result.status == "ERROR"]
    total_kb = sum(result.size_kb for result in ok)

    print(f"\n{'=' * 72}")
    print(f"Итого: {len(ok)} OK / {len(skip)} SKIP / {len(error)} ERROR")
    print(f"Каталог: {out_dir.resolve()}")
    print(f"Общий размер: {total_kb:.1f} KB")
    print("-" * 72)
    print(f"{'Файл':<28} {'Размер':>12}  Статус")
    print("-" * 72)
    for result in results:
        size = f"{result.size_kb:.1f} KB" if result.status == "OK" else "-"
        detail = f" - {result.error}" if result.error else ""
        print(f"{result.filename:<28} {size:>12}  {result.status}{detail}")
    print(f"{'=' * 72}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "sample_exports",
    )
    args = parser.parse_args(argv)

    print(f"База данных: {DB_FILE}")
    print(f"Выходной каталог: {args.out_dir.resolve()}")

    results = run_exports(args.out_dir, skip_seed=args.skip_seed)
    _print_summary(results, args.out_dir)

    error_count = sum(1 for result in results if result.status == "ERROR")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
