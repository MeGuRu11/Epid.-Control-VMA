from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime


def pick_latest_case_id(
    case_dates: Iterable[tuple[int, datetime | None, datetime | None]],
) -> int | None:
    latest_id: int | None = None
    latest_dt: datetime | None = None
    for case_id, admission_date, outcome_date in case_dates:
        case_dt = admission_date or outcome_date
        if case_dt and (latest_dt is None or case_dt > latest_dt):
            latest_dt = case_dt
            latest_id = case_id
        elif case_dt is None and latest_dt is None:
            if latest_id is None or case_id > latest_id:
                latest_id = case_id
    return latest_id
