from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import DataExchangePackage
from .base import RepoBase


class ExchangeRepo(RepoBase):
    def create(
        self,
        direction: str,
        package_format: str,
        file_path: str,
        sha256: str,
        created_by: int | None,
        notes: str | None = None,
    ) -> int:
        with self.tx() as s:
            row = DataExchangePackage(
                direction=direction,
                package_format=package_format,
                file_path=file_path,
                sha256=sha256,
                notes=notes,
                created_by=created_by,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def latest(self, limit: int = 100) -> list[DataExchangePackage]:
        with self.tx() as s:
            return list(
                s.execute(
                    select(DataExchangePackage).order_by(DataExchangePackage.created_at.desc()).limit(limit)
                ).scalars()
            )
