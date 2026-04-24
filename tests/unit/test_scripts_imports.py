from __future__ import annotations

import importlib


def test_audit_relevant_scripts_are_importable() -> None:
    for module_name in ("scripts.codex_task", "scripts.test_form100_pdf"):
        module = importlib.import_module(module_name)
        assert module is not None
