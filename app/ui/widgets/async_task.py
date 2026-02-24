from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


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
    if on_success:
        task.signals.success.connect(on_success)
    if on_error:
        task.signals.error.connect(on_error)
    if on_finished:
        task.signals.finished.connect(on_finished)
    QThreadPool.globalInstance().start(task)
    return task
