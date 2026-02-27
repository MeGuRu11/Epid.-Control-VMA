from __future__ import annotations

from sqlalchemy import select

from app.infrastructure.db.models_sqlalchemy import Form100Card
from .base import RepoBase


class Form100Repo(RepoBase):
    def list_cards(
        self,
        patient_id: int | None = None,
        emr_case_id: int | None = None,
    ) -> list[Form100Card]:
        with self.tx() as s:
            q = select(Form100Card).order_by(Form100Card.created_at.desc())
            if patient_id is not None:
                q = q.where(Form100Card.patient_id == patient_id)
            if emr_case_id is not None:
                q = q.where(Form100Card.emr_case_id == emr_case_id)
            return list(s.execute(q).scalars())

    def get(self, card_id: int) -> Form100Card | None:
        with self.tx() as s:
            return s.get(Form100Card, card_id)

    def create(
        self,
        *,
        patient_id: int,
        emr_case_id: int | None,
        payload_json: str,
        bodymap_json: str,
        created_by: int | None,
    ) -> int:
        with self.tx() as s:
            row = Form100Card(
                patient_id=patient_id,
                emr_case_id=emr_case_id,
                status="DRAFT",
                payload_json=payload_json,
                bodymap_json=bodymap_json,
                created_by=created_by,
            )
            s.add(row)
            s.flush()
            return int(row.id)

    def set_bodymap(self, card_id: int, bodymap_json: str) -> bool:
        with self.tx() as s:
            row = s.get(Form100Card, card_id)
            if row is None:
                return False
            row.bodymap_json = bodymap_json
            return True

    def set_payload(self, card_id: int, payload_json: str) -> bool:
        with self.tx() as s:
            row = s.get(Form100Card, card_id)
            if row is None:
                return False
            row.payload_json = payload_json
            return True

    def sign(self, card_id: int, signer: str, signed_at) -> bool:
        with self.tx() as s:
            row = s.get(Form100Card, card_id)
            if row is None:
                return False
            row.status = "SIGNED"
            row.signed_by = signer
            row.signed_at = signed_at
            return True

    def set_status(self, card_id: int, status: str) -> bool:
        with self.tx() as s:
            row = s.get(Form100Card, card_id)
            if row is None:
                return False
            row.status = status
            return True
