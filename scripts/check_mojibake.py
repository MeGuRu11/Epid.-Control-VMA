"""Проверка репозитория на типичные признаки mojibake."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SEARCH_ROOTS = ("app", "docs", "scripts", "tests")
GLOBS = ("*.py", "*.md", "*.ps1")

# Типичные паттерны повреждённой кириллицы:
# - UTF-8, прочитанный в неверной кодировке
# - replacement char после неудачной декодировки
PATTERNS: dict[str, re.Pattern[str]] = {
    "cp1251-mojibake": re.compile(
        r"\u0420\u045f\u0421\u0402\u0420\u0455|\u0420\u045f|\u0421\u0403|\u0420\u0406\u0420\u00b5|\u0420\u0451\u0420|\u00d0\u00b0\u00d0|\u00d0\u00bd\u00d0"
    ),
    "replacement-char": re.compile("\uFFFD"),
}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SEARCH_ROOTS:
        root = Path(root_name)
        if not root.exists():
            continue
        for pattern in GLOBS:
            files.extend(root.rglob(pattern))
    return sorted(set(files))


def main() -> int:
    violations: list[str] = []
    for path in iter_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            violations.append(f"NOT UTF-8: {path}")
            continue

        for line_no, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    violations.append(f"{label}: {path}:{line_no}: {line}")
                    break

    if violations:
        print("Mojibake detected:")
        for item in violations:
            print(item)
        return 1

    print("No mojibake detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
