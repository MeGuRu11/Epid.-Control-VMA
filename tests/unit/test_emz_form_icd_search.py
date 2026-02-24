from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast

from PySide6.QtWidgets import QComboBox

import app.ui.emz.form_icd_search as icd_search


@dataclass(frozen=True)
class _Icd:
    code: str
    title: str


class _FakeSignal:
    def __init__(self) -> None:
        self.callbacks: list[Callable[[str], None]] = []

    def connect(self, callback: Callable[[str], None]) -> None:
        self.callbacks.append(callback)


class _FakeLineEdit:
    def __init__(self) -> None:
        self.textEdited = _FakeSignal()


class _FakeCombo:
    def __init__(self, current_data: object | None = None) -> None:
        self._current_data = current_data
        self._model = object()
        self._line_edit = _FakeLineEdit()
        self.completer: object | None = None

    def currentData(self) -> object | None:  # noqa: N802
        return self._current_data

    def model(self) -> object:
        return self._model

    def setCompleter(self, completer: object) -> None:  # noqa: N802
        self.completer = completer

    def lineEdit(self) -> _FakeLineEdit:  # noqa: N802
        return self._line_edit


class _FakeCompleter:
    class CompletionMode:
        PopupCompletion = 9

    def __init__(self, model: object, parent: object) -> None:
        self.model = model
        self.parent = parent
        self.case_sensitivity: object | None = None
        self.filter_mode: object | None = None
        self.completion_mode: object | None = None

    def setCaseSensitivity(self, value: object) -> None:  # noqa: N802
        self.case_sensitivity = value

    def setFilterMode(self, value: object) -> None:  # noqa: N802
        self.filter_mode = value

    def setCompletionMode(self, value: object) -> None:  # noqa: N802
        self.completion_mode = value


class _FakeQt:
    class CaseSensitivity:
        CaseInsensitive = 1

    class MatchFlag:
        MatchContains = 2


class _FakeBlocker:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def __enter__(self) -> _FakeBlocker:
        self._events.append("enter")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self._events.append("exit")


def test_resolve_icd_items_returns_default_for_empty_query() -> None:
    default_items = [_Icd(code="A00", title="Cholera")]
    calls: list[str] = []

    def _search(query: str) -> Sequence[_Icd]:
        calls.append(query)
        return []

    resolved = icd_search.resolve_icd_items(
        text="  ",
        default_icd_items=default_items,
        search_icd_items=_search,
    )
    assert resolved == default_items
    assert calls == []


def test_resolve_icd_items_uses_search_for_query() -> None:
    default_items = [_Icd(code="A00", title="Cholera")]
    searched_items = [_Icd(code="B00", title="Herpes")]
    calls: list[str] = []

    def _search(query: str) -> Sequence[_Icd]:
        calls.append(query)
        return searched_items

    resolved = icd_search.resolve_icd_items(
        text="  her  ",
        default_icd_items=default_items,
        search_icd_items=_search,
    )
    assert resolved == searched_items
    assert calls == ["her"]


def test_refresh_icd_combo_populates_with_found_items() -> None:
    default_items = [_Icd(code="A00", title="Cholera")]
    searched_items = [_Icd(code="B00", title="Herpes")]
    combo = _FakeCombo(current_data="B00")
    captured: dict[str, object] = {}
    events: list[str] = []

    def _search(query: str) -> Sequence[_Icd]:
        assert query == "her"
        return searched_items

    def _populate(*, combo: object, icd_items: Sequence[_Icd], selected_data: object | None, edit_text: str) -> None:
        captured["combo"] = combo
        captured["items"] = icd_items
        captured["selected"] = selected_data
        captured["text"] = edit_text

    icd_search.refresh_icd_combo(
        combo=cast(QComboBox, combo),
        text="her",
        default_icd_items=default_items,
        search_icd_items=_search,
        populate_combo=_populate,
        blocker_factory=lambda _combo: _FakeBlocker(events),
    )
    assert events == ["enter", "exit"]
    assert captured["combo"] is combo
    assert captured["items"] == searched_items
    assert captured["selected"] == "B00"
    assert captured["text"] == "her"


def test_wire_icd_search_sets_completer_and_connects_handler(monkeypatch) -> None:
    monkeypatch.setattr(icd_search, "QCompleter", _FakeCompleter)
    monkeypatch.setattr(icd_search, "Qt", _FakeQt)
    combo = _FakeCombo()
    received: list[str] = []

    icd_search.wire_icd_search(cast(QComboBox, combo), lambda text: received.append(text))

    completer = cast(_FakeCompleter, combo.completer)
    assert isinstance(completer, _FakeCompleter)
    assert completer.model is combo.model()
    assert completer.parent is combo
    assert completer.case_sensitivity == _FakeQt.CaseSensitivity.CaseInsensitive
    assert completer.filter_mode == _FakeQt.MatchFlag.MatchContains
    assert completer.completion_mode == _FakeCompleter.CompletionMode.PopupCompletion
    assert len(combo.lineEdit().textEdited.callbacks) == 1
    combo.lineEdit().textEdited.callbacks[0]("abc")
    assert received == ["abc"]
