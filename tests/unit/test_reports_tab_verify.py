from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QPushButton


class _ControllerStub:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []
        self.verify_calls: list[bool] = []

    def load_report_history(
        self,
        *,
        report_type: str | None = None,
        query: str | None = None,
        verify_hash: bool = False,
    ) -> list[dict[str, object]]:
        _ = (report_type, query)
        self.verify_calls.append(verify_hash)
        return self.rows


def _build_tab(qtbot: Any, controller: _ControllerStub | None = None) -> Any:
    from app.ui.analytics.tabs.reports_tab import ReportsTab

    tab = ReportsTab(controller=controller or _ControllerStub())  # type: ignore[arg-type]
    qtbot.addWidget(tab)
    return tab


def test_verify_button_exists(qtbot: Any) -> None:
    tab = _build_tab(qtbot)

    labels = [button.text() for button in tab.findChildren(QPushButton)]

    assert any("хеш" in label.lower() for label in labels)


def test_load_report_history_verify_hash_colors_ok_row(qtbot: Any) -> None:
    controller = _ControllerStub(
        [
            {
                "id": 1,
                "report_type": "analytics",
                "created_by": 1,
                "summary": {"total": 1},
                "verification": {"status": "ok"},
                "artifact_sha256": "abc",
                "artifact_path": "C:/tmp/report.pdf",
            }
        ]
    )
    tab = _build_tab(qtbot, controller)

    tab.load_report_history(verify_hash=True)

    item = tab.report_history_table.item(0, 0)
    assert controller.verify_calls[-1] is True
    assert item is not None
    assert item.background().color().name().lower() == "#eaf3de"


def test_load_report_history_verify_hash_colors_mismatch_row(qtbot: Any) -> None:
    controller = _ControllerStub(
        [
            {
                "id": 1,
                "report_type": "analytics",
                "created_by": 1,
                "summary": {"total": 1},
                "verification": {"status": "mismatch"},
                "artifact_sha256": "abc",
                "artifact_path": "C:/tmp/report.pdf",
            }
        ]
    )
    tab = _build_tab(qtbot, controller)

    tab.load_report_history(verify_hash=True)

    item = tab.report_history_table.item(0, 0)
    assert item is not None
    assert item.background().color().name().lower() == "#fecaca"
