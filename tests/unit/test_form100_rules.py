from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.rules.form100_rules import build_changed_paths, validate_card_payload


def test_validate_card_payload_rejects_arrival_before_injury() -> None:
    payload = {
        "injury_dt": datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
        "arrival_dt": datetime(2026, 1, 9, 10, 0, tzinfo=UTC),
        "care_analgesia_given": False,
        "care_antibiotic_given": False,
        "care_antidote_given": False,
        "infusion_performed": False,
        "transfusion_performed": False,
        "sanitation_performed": False,
    }
    with pytest.raises(ValueError, match="Дата поступления"):
        validate_card_payload(payload)


def test_validate_card_payload_requires_detail_when_flag_true() -> None:
    payload = {
        "injury_dt": None,
        "arrival_dt": datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
        "care_analgesia_given": True,
        "care_analgesia_details": None,
        "care_antibiotic_given": False,
        "care_antidote_given": False,
        "infusion_performed": False,
        "transfusion_performed": False,
        "sanitation_performed": False,
    }
    with pytest.raises(ValueError, match="Анальгезия"):
        validate_card_payload(payload)


def test_build_changed_paths_returns_only_modified_fields() -> None:
    before = {
        "status": "DRAFT",
        "version": 1,
        "flags": {"urgent": False, "isolation": False},
    }
    after = {
        "status": "SIGNED",
        "version": 2,
        "flags": {"urgent": True, "isolation": False},
    }
    changes = build_changed_paths(before, after)
    assert changes["before"]["status"] == "DRAFT"
    assert changes["after"]["status"] == "SIGNED"
    assert changes["before"]["version"] == 1
    assert changes["after"]["version"] == 2
    assert changes["before"]["flags.urgent"] is False
    assert changes["after"]["flags.urgent"] is True
    assert "flags.isolation" not in changes["before"]
