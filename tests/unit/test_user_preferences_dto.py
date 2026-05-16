from __future__ import annotations

from app.application.dto.user_preferences_dto import (
    BACKUP_RETENTION_MAX,
    BACKUP_RETENTION_MIN,
    SESSION_TIMEOUT_MAX,
    SESSION_TIMEOUT_MIN,
    UserPreferences,
)

# ----------------------------------------------------------------------
# Defaults & round-trip
# ----------------------------------------------------------------------


def test_defaults_match_expected_baseline() -> None:
    prefs = UserPreferences()

    assert prefs.ui_density == "normal"
    assert prefs.ui_animation_policy == "adaptive"
    assert prefs.ui_premium_enabled is True
    assert prefs.session_timeout_minutes == 30
    assert prefs.auto_logout_enabled is True
    assert prefs.auto_backup_enabled is True
    assert prefs.auto_backup_frequency == "startup_daily"
    assert prefs.backup_retention_count == 10


def test_to_dict_serializes_geometry_as_list() -> None:
    prefs = UserPreferences(last_window_geometry=(10, 20, 800, 600))
    data = prefs.to_dict()

    assert data["last_window_geometry"] == [10, 20, 800, 600]


def test_to_dict_keeps_geometry_none_when_missing() -> None:
    prefs = UserPreferences()
    data = prefs.to_dict()

    assert data["last_window_geometry"] is None


def test_round_trip_preserves_all_fields() -> None:
    original = UserPreferences(
        ui_density="compact",
        ui_animation_policy="minimal",
        ui_premium_enabled=False,
        session_timeout_minutes=60,
        auto_logout_enabled=False,
        last_window_geometry=(0, 0, 1024, 768),
        pdf_export_dir="/tmp/pdfs",
    )

    restored = UserPreferences.from_dict(original.to_dict())

    assert restored == original


# ----------------------------------------------------------------------
# Validation / coercion
# ----------------------------------------------------------------------


def test_invalid_density_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"ui_density": "ultra-tight"})
    assert prefs.ui_density == "normal"


def test_invalid_animation_policy_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"ui_animation_policy": "fancy"})
    assert prefs.ui_animation_policy == "adaptive"


def test_invalid_window_state_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"window_initial_state": "spinning"})
    assert prefs.window_initial_state == "maximized"


def test_invalid_backup_frequency_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"auto_backup_frequency": "every_hour"})
    assert prefs.auto_backup_frequency == "startup_daily"


def test_session_timeout_below_minimum_is_clamped_up() -> None:
    prefs = UserPreferences.from_dict({"session_timeout_minutes": 1})
    assert prefs.session_timeout_minutes == SESSION_TIMEOUT_MIN


def test_session_timeout_above_maximum_is_clamped_down() -> None:
    prefs = UserPreferences.from_dict({"session_timeout_minutes": 100_000})
    assert prefs.session_timeout_minutes == SESSION_TIMEOUT_MAX


def test_session_timeout_invalid_string_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"session_timeout_minutes": "lots"})
    assert prefs.session_timeout_minutes == 30  # default


def test_session_timeout_string_number_is_coerced() -> None:
    prefs = UserPreferences.from_dict({"session_timeout_minutes": "45"})
    assert prefs.session_timeout_minutes == 45


def test_backup_retention_is_clamped_to_range() -> None:
    high = UserPreferences.from_dict({"backup_retention_count": 9999})
    low = UserPreferences.from_dict({"backup_retention_count": 0})

    assert high.backup_retention_count == BACKUP_RETENTION_MAX
    assert low.backup_retention_count == BACKUP_RETENTION_MIN


def test_geometry_with_wrong_shape_is_dropped() -> None:
    prefs = UserPreferences.from_dict({"last_window_geometry": [10, 20, 30]})
    assert prefs.last_window_geometry is None


def test_geometry_with_non_numeric_values_is_dropped() -> None:
    prefs = UserPreferences.from_dict({"last_window_geometry": ["a", "b", "c", "d"]})
    assert prefs.last_window_geometry is None


def test_geometry_accepts_list_form_from_json() -> None:
    prefs = UserPreferences.from_dict({"last_window_geometry": [5, 6, 7, 8]})
    assert prefs.last_window_geometry == (5, 6, 7, 8)


def test_geometry_accepts_explicit_none() -> None:
    prefs = UserPreferences.from_dict({"last_window_geometry": None})
    assert prefs.last_window_geometry is None


def test_invalid_bool_falls_back_to_default() -> None:
    # Если в файле вместо булева пришла строка — берём дефолт (True),
    # а не пытаемся приводить «истиноподобные» строки к True.
    prefs = UserPreferences.from_dict({"auto_logout_enabled": "yes"})
    assert prefs.auto_logout_enabled is True


def test_invalid_string_field_falls_back_to_default() -> None:
    prefs = UserPreferences.from_dict({"pdf_export_dir": 12345})
    assert prefs.pdf_export_dir == ""


# ----------------------------------------------------------------------
# with_updates
# ----------------------------------------------------------------------


def test_with_updates_returns_new_instance_and_keeps_old_immutable() -> None:
    original = UserPreferences()
    updated = original.with_updates(ui_density="compact")

    assert updated.ui_density == "compact"
    assert original.ui_density == "normal"
    assert updated is not original


def test_with_updates_revalidates_passed_values() -> None:
    prefs = UserPreferences().with_updates(session_timeout_minutes=10_000)
    assert prefs.session_timeout_minutes == SESSION_TIMEOUT_MAX
