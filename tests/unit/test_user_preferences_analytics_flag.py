from __future__ import annotations

from app.application.dto.user_preferences_dto import UserPreferences


def test_use_analytics_v2_default_is_false() -> None:
    prefs = UserPreferences()

    assert prefs.use_analytics_v2 is False


def test_use_analytics_v2_persists_through_serialization() -> None:
    prefs = UserPreferences(use_analytics_v2=True)

    restored = UserPreferences.from_dict(prefs.to_dict())

    assert restored.use_analytics_v2 is True


def test_use_analytics_v2_defaults_when_missing_from_dict() -> None:
    """Старый preferences.json без этого поля получает False."""
    prefs = UserPreferences.from_dict({})

    assert prefs.use_analytics_v2 is False


def test_use_analytics_v2_with_updates() -> None:
    prefs = UserPreferences()

    updated = prefs.with_updates(use_analytics_v2=True)

    assert updated.use_analytics_v2 is True
    assert prefs.use_analytics_v2 is False
