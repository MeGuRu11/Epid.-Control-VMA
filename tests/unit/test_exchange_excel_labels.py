from __future__ import annotations

from app.application.services.exchange_service import (
    EXCEL_SHEET_TITLES,
    _get_excel_headers,
    _get_excel_sheet_title,
    _map_excel_row,
)


def test_excel_sheet_titles_are_russian_for_user_visible_sheets() -> None:
    assert _get_excel_sheet_title("patients") == "Пациенты"
    assert _get_excel_sheet_title("ref_antibiotics") == "Антибиотики"
    assert EXCEL_SHEET_TITLES["lab_sample"] == "Лабораторные пробы"


def test_excel_headers_for_patients_are_human_readable() -> None:
    headers = _get_excel_headers(
        "patients",
        ["id", "full_name", "dob", "sex", "category", "military_unit"],
    )

    assert headers == [
        "ID пациента",
        "ФИО",
        "Дата рождения",
        "Пол",
        "Категория",
        "Воинская часть",
    ]


def test_excel_import_maps_russian_headers_back_to_technical_names() -> None:
    row = {
        "ID пациента": 1,
        "ФИО": "Иванов Иван Иванович",
        "Дата рождения": "24.01.1997",
        "Пол": "M",
        "Категория": "офицер",
    }

    mapped = _map_excel_row("patients", row)

    assert mapped["id"] == 1
    assert mapped["full_name"] == "Иванов Иван Иванович"
    assert mapped["dob"] == "24.01.1997"
    assert mapped["sex"] == "M"
    assert mapped["category"] == "офицер"
