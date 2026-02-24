from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from app.ui.widgets.patient_search_dialog import PatientSearchDialog
from app.ui.widgets.patient_selector import PatientSelector


class _FakeLineEdit:
    def __init__(self, value: str) -> None:
        self._value = value

    def text(self) -> str:
        return self._value


class _FakeStatus:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = value


class _FakeList:
    def __init__(self) -> None:
        self.cleared = 0

    def clear(self) -> None:
        self.cleared += 1


def test_patient_selector_apply_sets_error_when_on_select_fails(monkeypatch) -> None:
    statuses: list[tuple[str, str]] = []
    cleared = {"count": 0}

    def _fake_set_status(_label: Any, message: str, level: str = "info") -> None:
        statuses.append((message, level))

    monkeypatch.setattr("app.ui.widgets.patient_selector.set_status", _fake_set_status)
    monkeypatch.setattr("app.ui.widgets.patient_selector.clear_status", lambda _label: cleared.__setitem__("count", 1))

    opened = {"count": 0}
    selector = SimpleNamespace(
        status=object(),
        patient_id=_FakeLineEdit("101"),
        on_select=lambda _pid: (_ for _ in ()).throw(RuntimeError("db down")),
        _open_search=lambda: opened.__setitem__("count", opened["count"] + 1),
        _get_patient_name=lambda _pid: "Иванов Иван",
    )

    PatientSelector._apply(cast(PatientSelector, selector))

    assert cleared["count"] == 1
    assert opened["count"] == 0
    assert statuses == [("Не удалось выбрать пациента: db down", "error")]


def test_patient_selector_apply_sets_warning_for_invalid_id(monkeypatch) -> None:
    statuses: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.ui.widgets.patient_selector.set_status",
        lambda _label, message, level="info": statuses.append((message, level)),
    )
    monkeypatch.setattr("app.ui.widgets.patient_selector.clear_status", lambda _label: None)

    opened = {"count": 0}
    selector = SimpleNamespace(
        status=object(),
        patient_id=_FakeLineEdit("abc"),
        on_select=lambda _pid: None,
        _open_search=lambda: opened.__setitem__("count", opened["count"] + 1),
        _get_patient_name=lambda _pid: "Иванов Иван",
    )

    PatientSelector._apply(cast(PatientSelector, selector))

    assert opened["count"] == 0
    assert statuses == [("ID пациента должен быть положительным числом", "warning")]


def test_patient_search_dialog_load_recent_sets_error_status(monkeypatch) -> None:
    def _fake_run_async(_owner, _run, on_success, on_error, on_finished=None) -> None:
        on_error(RuntimeError("recent failed"))
        if on_finished:
            on_finished()

    monkeypatch.setattr("app.ui.widgets.patient_search_dialog.run_async", _fake_run_async)

    dialog = SimpleNamespace(
        recent_list=_FakeList(),
        _recent_token=0,
        patient_service=SimpleNamespace(list_recent=lambda limit=10: []),
        status=_FakeStatus(),
    )

    PatientSearchDialog._load_recent(cast(PatientSearchDialog, dialog))

    assert dialog.recent_list.cleared == 1
    assert dialog.status.text == "Не удалось загрузить последних пациентов: recent failed"
