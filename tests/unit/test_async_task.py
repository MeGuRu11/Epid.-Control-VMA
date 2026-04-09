from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QObject

from app.ui.widgets.async_task import run_async


def _wait_until(qapp: Any, predicate: Any, timeout: float = 1.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Асинхронная задача не завершилась за ожидаемое время")


def test_run_async_keeps_task_alive_until_callbacks_fire(qapp) -> None:
    owner = QObject()
    state: dict[str, Any] = {"result": None, "finished": False}

    run_async(
        owner,
        lambda: {"ok": 1},
        on_success=lambda result: state.__setitem__("result", result),
        on_finished=lambda: state.__setitem__("finished", True),
    )

    _wait_until(qapp, lambda: state["finished"])

    assert state["result"] == {"ok": 1}
    assert state["finished"] is True
    assert not hasattr(owner, "_codex_async_tasks")
