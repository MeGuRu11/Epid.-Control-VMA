from __future__ import annotations

from pathlib import Path


def test_ui_python_files_do_not_use_inline_stylesheets() -> None:
    root = Path(__file__).resolve().parents[2]
    ui_root = root / "app" / "ui"
    allowed = {
        Path("app/ui/theme.py"),
    }
    violations: list[str] = []
    for path in ui_root.rglob("*.py"):
        rel = path.relative_to(root)
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "setStyleSheet(" in text:
            violations.append(str(rel).replace("\\", "/"))

    assert not violations, (
        "Inline setStyleSheet() is forbidden in app/ui (use theme.py with objectName/properties). "
        f"Violations: {', '.join(sorted(violations))}"
    )
