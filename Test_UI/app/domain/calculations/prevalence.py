from __future__ import annotations


def prevalence_rate(cases: int, population: int) -> float:
    safe = population if population > 0 else 1
    return round((cases / safe) * 100.0, 2)

