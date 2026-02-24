from __future__ import annotations

from app.ui.form100.widgets.bodymap_editor import (
    _marks_stats,
    _normalize_mark_payload,
    _normalize_side,
)


def test_normalize_side_keeps_supported_values() -> None:
    assert _normalize_side("FRONT") == "FRONT"
    assert _normalize_side("back") == "BACK"


def test_normalize_side_fallbacks_to_default() -> None:
    assert _normalize_side("", default="BACK") == "BACK"
    assert _normalize_side(None, default="FRONT") == "FRONT"
    assert _normalize_side("LEFT", default="BACK") == "BACK"


def test_normalize_mark_payload_applies_defaults() -> None:
    payload = _normalize_mark_payload({"shape_json": {"x": 0.1, "y": 0.2}}, default_side="BACK")
    assert payload["side"] == "BACK"
    assert payload["type"] == "NOTE_PIN"
    assert payload["shape_json"] == {"x": 0.1, "y": 0.2}
    assert payload["meta_json"] == {}


def test_marks_stats_aggregates_human_readable_counts() -> None:
    marks = [
        {"type": "WOUND_X"},
        {"type": "WOUND_X"},
        {"type": "NOTE_PIN"},
    ]
    assert _marks_stats(marks) == "рана: 2, пин: 1"
