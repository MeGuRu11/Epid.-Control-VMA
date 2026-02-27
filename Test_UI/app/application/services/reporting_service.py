from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ...config import get_app_dirs
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.report_repo import ReportRepo
from ...infrastructure.security.sha256 import file_sha256
from .analytics_service import AnalyticsService


class ReportingService:
    def __init__(self, engine, session_ctx):
        self._engine = engine
        self._session = session_ctx
        self._analytics = AnalyticsService(engine, session_ctx)
        self._repo = ReportRepo(engine)
        self._audit = AuditLogger(engine)

    def _reports_dir(self) -> Path:
        dirs = get_app_dirs()
        out_dir = dirs.data / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def _log_report(self, report_type: str, summary: dict, path: Path) -> None:
        digest = file_sha256(path)
        report_id = self._repo.create_run(
            created_by=self._session.user_id,
            report_type=report_type,
            filters={},
            summary=summary,
            artifact_path=str(path),
            artifact_sha256=digest,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "report_run",
                str(report_id),
                "export",
                {"type": report_type, "path": str(path), "sha256": digest},
            )
        )

    def export_summary_csv(self) -> Path:
        out_dir = self._reports_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"analytics_summary_{stamp}.csv"
        summary = self._analytics.summary()
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for key, value in summary.items():
                writer.writerow([key, value])
            writer.writerow(["incidence_density", self._analytics.incidence_density()])
            writer.writerow(["prevalence", self._analytics.prevalence()])

        self._log_report("analytics_summary_csv", summary, path)
        return path

    def export_summary_xlsx(self) -> Path:
        try:
            from openpyxl import Workbook
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openpyxl не установлен") from exc

        out_dir = self._reports_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"analytics_summary_{stamp}.xlsx"
        summary = self._analytics.summary()

        wb = Workbook()
        ws = wb.active
        ws.title = "summary"
        ws.append(["metric", "value"])
        for key, value in summary.items():
            ws.append([key, value])
        ws.append(["incidence_density", self._analytics.incidence_density()])
        ws.append(["prevalence", self._analytics.prevalence()])
        wb.save(path)

        self._log_report("analytics_summary_xlsx", summary, path)
        return path

    def export_summary_pdf(self) -> Path:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("reportlab не установлен") from exc

        out_dir = self._reports_dir()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"analytics_summary_{stamp}.pdf"
        summary = self._analytics.summary()

        c = canvas.Canvas(str(path), pagesize=A4)
        y = 800
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "EpiSafe Analytics Summary")
        y -= 30
        c.setFont("Helvetica", 11)
        for key, value in summary.items():
            c.drawString(40, y, f"{key}: {value}")
            y -= 18
        c.drawString(40, y, f"incidence_density: {self._analytics.incidence_density()}")
        y -= 18
        c.drawString(40, y, f"prevalence: {self._analytics.prevalence()}")
        c.save()

        self._log_report("analytics_summary_pdf", summary, path)
        return path

    def history(self, limit: int = 100):
        return self._repo.latest(limit=limit)

