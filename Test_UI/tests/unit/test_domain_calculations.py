from __future__ import annotations

from app.domain.calculations import incidence_density, prevalence_rate
from app.domain.rules import ensure_date_order, normalize_required_text


def test_calculations():
    assert incidence_density(5, 10) == 50.0
    assert prevalence_rate(2, 10) == 20.0
    assert incidence_density(1, 0) == 100.0


def test_rules():
    assert normalize_required_text("") == "н/д"
    assert normalize_required_text("  ok  ") == "ok"
    ensure_date_order(None, None, "x")

