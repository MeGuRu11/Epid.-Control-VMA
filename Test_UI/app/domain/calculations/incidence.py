from __future__ import annotations


def incidence_density(events: int, denominator: int) -> float:
    safe = denominator if denominator > 0 else 1
    return round((events / safe) * 100.0, 2)

