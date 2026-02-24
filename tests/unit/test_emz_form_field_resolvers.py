from __future__ import annotations

from app.ui.emz.form_field_resolvers import (
    normalize_sex_label,
    parse_optional_int,
    resolve_department_id,
)


class _Department:
    def __init__(self, dep_id: int, name: str) -> None:
        self.id = dep_id
        self.name = name


def test_parse_optional_int_variants() -> None:
    assert parse_optional_int(None, "SOFA") is None
    assert parse_optional_int("   ", "SOFA") is None
    assert parse_optional_int("42", "SOFA") == 42


def test_parse_optional_int_invalid_raises() -> None:
    try:
        parse_optional_int("4a", "SOFA")
    except ValueError as exc:
        assert str(exc) == "Поле 'SOFA' должно быть числом"
    else:
        raise AssertionError("Expected ValueError for non-digit input")


def test_normalize_sex_label() -> None:
    assert normalize_sex_label("М") == "M"
    assert normalize_sex_label("Ж") == "F"


def test_resolve_department_id_prefers_selected_id() -> None:
    departments = [_Department(1, "Хирургия"), _Department(2, "Терапия")]
    assert (
        resolve_department_id(selected_id=99, selected_name="Хирургия", departments=departments)
        == 99
    )


def test_resolve_department_id_by_name_and_empty_cases() -> None:
    departments = [_Department(1, "Хирургия"), _Department(2, "Терапия")]
    assert (
        resolve_department_id(selected_id=None, selected_name="  Терапия  ", departments=departments)
        == 2
    )
    assert resolve_department_id(selected_id=None, selected_name="Выбрать", departments=departments) is None
    assert resolve_department_id(selected_id=None, selected_name="", departments=departments) is None
    assert (
        resolve_department_id(selected_id=None, selected_name="Неизвестное", departments=departments)
        is None
    )
