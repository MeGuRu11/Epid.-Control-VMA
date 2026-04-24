from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

TASKS_DIR_RELATIVE = Path("docs/codex/tasks")
TEMPLATE_PATH_RELATIVE = Path("docs/codex/templates/task.md")


def repo_root() -> Path:
    """Return the repository root resolved from the script location."""
    return Path(__file__).resolve().parents[1]


def slugify(value: str) -> str:
    """Build a filesystem-safe slug while preserving Cyrillic letters."""
    lowered = value.strip().lower().replace("_", "-")
    cleaned = re.sub(r"[^\w-]+", "-", lowered, flags=re.UNICODE)
    compacted = re.sub(r"-{2,}", "-", cleaned, flags=re.UNICODE).strip("-")
    return compacted or "task"


def run_git_command(root: Path, args: Sequence[str]) -> str | None:
    """Run a git command and return stripped stdout on success."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    output = completed.stdout.strip()
    return output or None


def get_git_branch(root: Path) -> str:
    """Return the current git branch when available."""
    branch = run_git_command(root, ["branch", "--show-current"])
    return branch or "unknown"


def get_modified_files(root: Path) -> list[str]:
    """Return the current git status lines."""
    status = run_git_command(root, ["status", "--short"])
    if not status:
        return []
    return [line.strip() for line in status.splitlines() if line.strip()]


def tasks_dir(root: Path) -> Path:
    """Return the absolute tasks directory path."""
    return root / TASKS_DIR_RELATIVE


def template_path(root: Path) -> Path:
    """Return the absolute task template path."""
    return root / TEMPLATE_PATH_RELATIVE


def build_task_path(root: Path, slug: str, now: datetime) -> Path:
    """Build the markdown path for a task file."""
    return tasks_dir(root) / f"{now:%Y-%m-%d}-{slug}.md"


def format_modified_files(lines: Sequence[str], *, limit: int = 10) -> str:
    """Format a git status snapshot for the task template."""
    if not lines:
        return "- Рабочее дерево чистое."

    rendered = [f"- `{line}`" for line in lines[:limit]]
    if len(lines) > limit:
        rendered.append(f"- `... ещё {len(lines) - limit}`")
    return "\n".join(rendered)


def extract_task_title(path: Path) -> str:
    """Extract the title from a task markdown file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Задача: "):
            return line.removeprefix("# Задача: ").strip()
    return path.stem


def create_task_file(
    title: str,
    *,
    root: Path | None = None,
    slug: str | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> Path:
    """Create a new Codex long-task markdown file from the repo template."""
    actual_root = root or repo_root()
    actual_now = now or datetime.now(UTC).astimezone()
    actual_slug = slugify(slug or title)
    target = build_task_path(actual_root, actual_slug, actual_now)

    task_template = template_path(actual_root)
    if not task_template.exists():
        raise FileNotFoundError(f"Не найден шаблон task-файла: {task_template}")

    if target.exists() and not force:
        raise FileExistsError(
            f"Task-файл уже существует: {target}. Используйте другой slug или --force."
        )

    rendered = task_template.read_text(encoding="utf-8")
    replacements = {
        "{{title}}": title.strip(),
        "{{slug}}": actual_slug,
        "{{created_at}}": actual_now.strftime("%Y-%m-%d %H:%M"),
        "{{branch}}": get_git_branch(actual_root),
        "{{modified_files}}": format_modified_files(get_modified_files(actual_root)),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target


def list_task_files(root: Path | None = None) -> list[Path]:
    """Return tracked task files sorted from newest to oldest."""
    actual_root = root or repo_root()
    base_dir = tasks_dir(actual_root)
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("*.md"), reverse=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Лёгкий task-state scaffold для долгих Codex-задач."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser(
        "new", help="Создать новый task-файл в docs/codex/tasks/."
    )
    new_parser.add_argument("title", nargs="+", help="Краткое название задачи.")
    new_parser.add_argument("--slug", help="Явный slug для имени файла.")
    new_parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующий task-файл с тем же именем.",
    )

    list_parser = subparsers.add_parser(
        "list", help="Показать существующие task-файлы."
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Сколько последних task-файлов показать.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = repo_root()

    if args.command == "new":
        title = " ".join(args.title)
        created = create_task_file(title, root=root, slug=args.slug, force=args.force)
        print(f"Создан task-файл: {created.relative_to(root)}")
        print("Следующий шаг: заполните цель, границы и план до первых правок.")
        return 0

    if args.command == "list":
        files = list_task_files(root=root)
        if not files:
            print("Task-файлы ещё не создавались.")
            return 0

        for path in files[: args.limit]:
            title = extract_task_title(path)
            print(f"- {path.relative_to(root)} — {title}")
        return 0

    parser.error(f"Неизвестная команда: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
