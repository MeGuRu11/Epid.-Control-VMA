from __future__ import annotations

from datetime import date

from ...application.dto.sanitary_dto import SanitarySampleCreateIn
from ...domain.rules import normalize_required_text
from ...infrastructure.audit.audit_logger import AuditEvent, AuditLogger
from ...infrastructure.db.repositories.sanitary_repo import SanitaryRepo


class SanitaryService:
    def __init__(self, engine, session_ctx):
        self._session = session_ctx
        self._repo = SanitaryRepo(engine)
        self._audit = AuditLogger(engine)

    def list(self, department_id: int | None = None):
        return self._repo.list_samples(department_id=department_id)

    def get_sample(self, sample_id: int):
        return self._repo.get_sample(sample_id)

    def get_panels(self, sample_id: int) -> dict:
        return self._repo.get_panels(sample_id)

    def update_result(self, sample_id: int, payload: dict) -> None:
        self._repo.update_sample_result(sample_id, payload)
        self._audit.log(
            AuditEvent(
                self._session.user_id, self._session.login,
                "sanitary_sample", str(sample_id), "update_result", payload,
            )
        )

    def save_panels(self, sample_id: int, isolates=None, abx=None, phages=None) -> None:
        self._repo.replace_panels(sample_id, isolates=isolates, abx=abx, phages=phages)
        self._audit.log(
            AuditEvent(
                self._session.user_id, self._session.login,
                "sanitary_sample", str(sample_id), "save_panels",
                {"isolates": len(isolates or []), "abx": len(abx or []), "phages": len(phages or [])},
            )
        )

    def generate_lab_no(self, when: date | None = None) -> str:
        day = (when or date.today()).strftime("%Y%m%d")
        rows = self.list()
        prefix = f"SAN-{day}-"
        nums: list[int] = []
        for row in rows:
            if row.lab_no.startswith(prefix):
                try:
                    nums.append(int(row.lab_no.split("-")[-1]))
                except (TypeError, ValueError):
                    continue
        next_no = (max(nums) + 1) if nums else 1
        return f"SAN-{day}-{next_no:03d}"

    def create(
        self,
        lab_no: str,
        sampling_point: str,
        department_id: int | None = None,
        room: str | None = None,
        growth_flag: int | None = None,
        cfu: str | None = None,
    ) -> int:
        dto = SanitarySampleCreateIn(
            lab_no=lab_no.strip(),
            sampling_point=normalize_required_text(sampling_point),
            department_id=department_id,
            room=room,
            growth_flag=growth_flag,
            cfu=cfu,
        )
        sample_id = self._repo.create_sample(
            lab_no=dto.lab_no,
            sampling_point=dto.sampling_point,
            department_id=dto.department_id,
            room=dto.room,
            growth_flag=dto.growth_flag,
            cfu=dto.cfu,
            created_by=self._session.user_id,
        )
        self._audit.log(
            AuditEvent(
                self._session.user_id,
                self._session.login,
                "sanitary_sample",
                str(sample_id),
                "create",
                {"lab_no": dto.lab_no, "sampling_point": dto.sampling_point},
            )
        )
        return sample_id

    def create_auto(self, sampling_point: str, cfu: str | None = None, room: str | None = None) -> int:
        return self.create(
            lab_no=self.generate_lab_no(),
            sampling_point=sampling_point,
            room=room,
            growth_flag=1 if (cfu or "").strip() not in ("", "0") else 0,
            cfu=cfu,
        )
