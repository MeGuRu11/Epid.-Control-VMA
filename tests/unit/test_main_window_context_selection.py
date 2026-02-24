from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from app.ui.main_window import MainWindow


class _FakeView:
    def __init__(self) -> None:
        self.calls: list[tuple[int | None, int | None]] = []

    def set_context(self, patient_id: int | None, emr_case_id: int | None) -> None:
        self.calls.append((patient_id, emr_case_id))


class _FakeContextBar:
    def __init__(self) -> None:
        self.calls: list[tuple[int | None, int | None]] = []

    def update_context(self, patient_id: int | None, emr_case_id: int | None) -> None:
        self.calls.append((patient_id, emr_case_id))


class _FakeContextBarWithName:
    def __init__(self) -> None:
        self.calls: list[tuple[int | None, int | None, str]] = []

    def update_context(self, patient_id: int | None, emr_case_id: int | None, patient_name: str = "") -> None:
        self.calls.append((patient_id, emr_case_id, patient_name))


class _FakeEmrForm:
    def __init__(self) -> None:
        self.clear_calls = 0
        self.load_calls: list[tuple[int | None, int | None, bool]] = []

    def clear_context(self) -> None:
        self.clear_calls += 1

    def load_case(self, patient_id: int | None, emr_case_id: int | None, *, emit_context: bool = True) -> None:
        self.load_calls.append((patient_id, emr_case_id, emit_context))


class _ReentrantEmrForm(_FakeEmrForm):
    def __init__(self, callback) -> None:
        super().__init__()
        self._callback = callback

    def clear_context(self) -> None:
        self.clear_calls += 1
        if self.clear_calls == 1:
            self._callback(None, None)


class _FakeRefreshView:
    def __init__(self) -> None:
        self.refreshed: list[int] = []

    def refresh_patient(self, patient_id: int) -> None:
        self.refreshed.append(patient_id)


def test_on_case_selected_loads_case_once_for_non_empty_context() -> None:
    window = SimpleNamespace()
    window._current_patient_id = None
    window._current_case_id = None
    window._case_selection_in_progress = False
    window._lab_view = _FakeView()
    window._emk_view = _FakeView()
    window._context_bar = _FakeContextBar()
    window._emr_form = _FakeEmrForm()

    MainWindow._on_case_selected(cast(MainWindow, window), 11, 22)

    assert window._current_patient_id == 11
    assert window._current_case_id == 22
    assert window._lab_view.calls == [(11, 22)]
    assert window._emk_view.calls == [(11, 22)]
    assert window._emr_form.load_calls == [(11, 22, False)]
    assert window._emr_form.clear_calls == 0
    assert window._context_bar.calls == [(11, 22)]
    assert window._case_selection_in_progress is False


def test_on_case_selected_blocks_reentrant_clear_context_callback() -> None:
    window = SimpleNamespace()
    window._current_patient_id = 33
    window._current_case_id = 44
    window._case_selection_in_progress = False
    window._lab_view = _FakeView()
    window._emk_view = _FakeView()
    window._context_bar = _FakeContextBar()
    window._emr_form = _ReentrantEmrForm(
        lambda pid, cid: MainWindow._on_case_selected(cast(MainWindow, window), pid, cid)
    )

    MainWindow._on_case_selected(cast(MainWindow, window), None, None)

    assert window._current_patient_id is None
    assert window._current_case_id is None
    assert window._emr_form.clear_calls == 1
    assert window._emr_form.load_calls == []
    assert window._lab_view.calls == [(None, None)]
    assert window._emk_view.calls == [(None, None)]
    assert window._context_bar.calls == [(None, None)]
    assert window._case_selection_in_progress is False


def test_after_patient_edit_saved_refreshes_views_and_context() -> None:
    window = SimpleNamespace()
    window._emk_view = _FakeRefreshView()
    window._emr_form = _FakeRefreshView()
    window._current_patient_id = 7
    window._current_case_id = 9
    window._context_bar = _FakeContextBarWithName()
    window.container = SimpleNamespace(
        patient_service=SimpleNamespace(get_by_id=lambda patient_id: SimpleNamespace(full_name="Иванов Иван")),
    )
    changed = {"count": 0}
    window._notify_data_changed = lambda: changed.__setitem__("count", changed["count"] + 1)

    MainWindow._after_patient_edit_saved(cast(MainWindow, window), 7)

    assert window._emk_view.refreshed == [7]
    assert window._emr_form.refreshed == [7]
    assert window._context_bar.calls == [(7, 9, "Иванов Иван")]
    assert changed["count"] == 1


def test_after_patient_edit_saved_skips_context_update_for_non_current_patient() -> None:
    window = SimpleNamespace()
    window._emk_view = _FakeRefreshView()
    window._emr_form = _FakeRefreshView()
    window._current_patient_id = 5
    window._current_case_id = 9
    window._context_bar = _FakeContextBarWithName()
    window.container = SimpleNamespace(patient_service=SimpleNamespace(get_by_id=lambda patient_id: None))
    changed = {"count": 0}
    window._notify_data_changed = lambda: changed.__setitem__("count", changed["count"] + 1)

    MainWindow._after_patient_edit_saved(cast(MainWindow, window), 7)

    assert window._emk_view.refreshed == [7]
    assert window._emr_form.refreshed == [7]
    assert window._context_bar.calls == []
    assert changed["count"] == 1
