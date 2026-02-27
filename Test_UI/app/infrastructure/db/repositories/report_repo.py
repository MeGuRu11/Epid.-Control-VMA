from __future__ import annotations

import json

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import ReportRun
from .base import RepoBase


class ReportRepo(RepoBase):
    def create_run(
        self,
        created_by: int | None,
        report_type: str,
        filters: dict,
        summary: dict,
        artifact_path: str | None = None,
        artifact_sha256: str | None = None,
    ) -> int:
        with self.tx() as s:
            row = ReportRun(
                created_by=created_by,
                report_type=report_type,
                filters_json=json.dumps(filters, ensure_ascii=False),
                result_summary_json=json.dumps(summary, ensure_ascii=False),
                artifact_path=artifact_path,
                artifact_sha256=artifact_sha256,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def latest(self, limit: int = 100) -> list[ReportRun]:
        with self.tx() as s:
            return list(s.execute(select(ReportRun).order_by(ReportRun.created_at.desc()).limit(limit)).scalars())
