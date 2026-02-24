from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import QComboBox, QCompleter

from app.ui.emz.form_widget_factories import IcdLike, populate_icd_combo

PopulateIcdComboFn = Callable[..., None]
SearchIcdItemsFn = Callable[[str], Sequence[IcdLike]]
SignalBlockerFactory = Callable[[QComboBox], AbstractContextManager[object]]


def wire_icd_search(combo: QComboBox, on_text: Callable[[str], None]) -> None:
    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)

    editor = combo.lineEdit()
    if editor is None:
        return
    editor.textEdited.connect(on_text)


def resolve_icd_items(
    *,
    text: str,
    default_icd_items: Sequence[IcdLike],
    search_icd_items: SearchIcdItemsFn,
) -> Sequence[IcdLike]:
    query = text.strip()
    if not query:
        return default_icd_items
    return search_icd_items(query)


def refresh_icd_combo(
    *,
    combo: QComboBox,
    text: str,
    default_icd_items: Sequence[IcdLike],
    search_icd_items: SearchIcdItemsFn,
    populate_combo: PopulateIcdComboFn = populate_icd_combo,
    blocker_factory: SignalBlockerFactory = QSignalBlocker,
) -> None:
    current_data = combo.currentData()
    icd_items = resolve_icd_items(
        text=text,
        default_icd_items=default_icd_items,
        search_icd_items=search_icd_items,
    )
    with blocker_factory(combo):
        populate_combo(
            combo=combo,
            icd_items=icd_items,
            selected_data=current_data,
            edit_text=text,
        )
