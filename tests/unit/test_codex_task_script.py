from __future__ import annotations

from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_script_module():
    script_path = Path("scripts/codex_task.py")
    spec = spec_from_file_location("codex_task_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slugify_preserves_cyrillic_and_collapses_separators() -> None:
    module = _load_script_module()

    assert module.slugify("  Сложная   задача / Codex  ") == "сложная-задача-codex"


def test_create_task_file_scaffolds_markdown_and_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    template = tmp_path / "docs" / "codex" / "templates" / "task.md"
    template.parent.mkdir(parents=True)
    template.write_text(
        "\n".join(
            [
                "# Задача: {{title}}",
                "slug={{slug}}",
                "created={{created_at}}",
                "branch={{branch}}",
                "{{modified_files}}",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "get_git_branch", lambda _root: "feature/codex")
    monkeypatch.setattr(
        module,
        "get_modified_files",
        lambda _root: ["M AGENTS.md", "?? docs/codex_workflow.md"],
    )

    created = module.create_task_file(
        "Усилить workflow Codex",
        root=tmp_path,
        now=datetime(2026, 4, 22, 15, 30, tzinfo=UTC),
    )

    assert created == tmp_path / "docs" / "codex" / "tasks" / "2026-04-22-усилить-workflow-codex.md"
    content = created.read_text(encoding="utf-8")
    assert "# Задача: Усилить workflow Codex" in content
    assert "slug=усилить-workflow-codex" in content
    assert "branch=feature/codex" in content
    assert "- `M AGENTS.md`" in content
    assert "- `?? docs/codex_workflow.md`" in content


def test_list_command_prints_newest_tasks_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    task_dir = tmp_path / "docs" / "codex" / "tasks"
    task_dir.mkdir(parents=True)
    (task_dir / "2026-04-20-older.md").write_text("# Задача: Старая\n", encoding="utf-8")
    (task_dir / "2026-04-22-newer.md").write_text("# Задача: Новая\n", encoding="utf-8")

    monkeypatch.setattr(module, "repo_root", lambda: tmp_path)

    exit_code = module.main(["list"])

    assert exit_code == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert "2026-04-22-newer.md" in lines[0]
    assert lines[0].endswith("Новая")
    assert "2026-04-20-older.md" in lines[1]
    assert lines[1].endswith("Старая")
