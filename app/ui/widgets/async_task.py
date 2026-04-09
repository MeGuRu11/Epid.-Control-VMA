from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_TASK_STORE_ATTR = "_codex_async_tasks"


class TaskSignals(QObject):
    success = Signal(object)
    error = Signal(Exception)
    finished = Signal()


class AsyncTask(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = TaskSignals()

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(exc)
        else:
            self.signals.success.emit(result)
        finally:
            self.signals.finished.emit()


def run_async(
    parent: QObject,
    fn: Callable[[], Any],
    on_success: Callable[[Any], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    on_finished: Callable[[], None] | None = None,
) -> AsyncTask:
    task = AsyncTask(fn)
    task_store = getattr(parent, _TASK_STORE_ATTR, None)
    if task_store is None:
        task_store = set()
        setattr(parent, _TASK_STORE_ATTR, task_store)
    task_store.add(task)

    def _cleanup() -> None:
        task_store.discard(task)
        if not task_store:
            with suppress(AttributeError):
                delattr(parent, _TASK_STORE_ATTR)
        if on_finished:
            on_finished()

    if on_success:
        task.signals.success.connect(on_success)
    if on_error:
        task.signals.error.connect(on_error)
    task.signals.finished.connect(_cleanup)
    QThreadPool.globalInstance().start(task)
    return task

