from __future__ import annotations

from app.domain.services.bodymap_zones import coordinates_to_zone


def test_head_zone() -> None:
    assert coordinates_to_zone(0.5, 0.05, "male_front") == "голова, по центру"


def test_chest_zone() -> None:
    assert coordinates_to_zone(0.5, 0.36, "male_front") == "грудь, по центру"


def test_foot_zone() -> None:
    assert coordinates_to_zone(0.5, 0.95, "male_front") == "стопа, по центру"


def test_left_side() -> None:
    assert coordinates_to_zone(0.2, 0.36, "male_front") == "грудь, левая сторона"


def test_right_side() -> None:
    assert coordinates_to_zone(0.8, 0.36, "male_front") == "грудь, правая сторона"


def test_center_side() -> None:
    assert coordinates_to_zone(0.5, 0.36, "male_front") == "грудь, по центру"
