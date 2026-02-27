from __future__ import annotations

from pathlib import Path
import zipfile

from app.application.services.auth_service import AuthService
from app.application.services.exchange_service import ExchangeService
from app.application.services.reporting_service import ReportingService


def _bootstrap(engine):
    auth = AuthService(engine)
    auth.create_initial_admin("admin", "admin1234")
    session = auth.login("admin", "admin1234")
    assert session is not None
    return session


def test_reporting_and_exchange_history(engine):
    session = _bootstrap(engine)
    reporting = ReportingService(engine, session)
    exchange = ExchangeService(engine, session)

    csv_path = reporting.export_summary_csv()
    assert isinstance(csv_path, Path)
    assert csv_path.exists()

    zip_path = exchange.export_package()
    assert zip_path.exists()
    import_id = exchange.import_package(zip_path)
    assert import_id > 0

    history = exchange.history(limit=10)
    assert len(history) >= 2


def test_exchange_rejects_tampered_zip(engine, tmp_path):
    session = _bootstrap(engine)
    exchange = ExchangeService(engine, session)
    zip_path = exchange.export_package()
    bad_path = tmp_path / "tampered.zip"
    bad_path.write_bytes(zip_path.read_bytes())

    with zipfile.ZipFile(bad_path, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", b'{"schema_version":"1.1","data":"tampered"}')

    failed = False
    try:
        exchange.import_package(bad_path)
    except ValueError:
        failed = True
    assert failed is True
