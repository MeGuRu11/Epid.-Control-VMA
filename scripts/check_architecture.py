"""Проверка архитектурных ограничений импортов."""

from __future__ import annotations

import re
import sys
from pathlib import Path

RULES = [
    ("app/ui/", r"from app\.infrastructure|import app\.infrastructure", "UI → Infrastructure"),
    ("app/ui/", r"from sqlalchemy|import sqlalchemy", "UI → SQLAlchemy"),
    ("app/domain/", r"from app\.infrastructure|from app\.application|from app\.ui", "Domain → другие слои"),
    ("app/domain/", r"import PySide6|import sqlalchemy", "Domain → внешние фреймворки"),
    ("app/application/", r"from app\.ui|import app\.ui", "Application → UI"),
]


def check() -> int:
    violations = 0
    for base_dir, pattern, description in RULES:
        base = Path(base_dir)
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            for i, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(pattern, line):
                    print(f"VIOLATION [{description}]: {py_file}:{i}: {line.strip()}")
                    violations += 1
    if violations:
        print(f"\n{violations} architectural violation(s) found.")
    else:
        print("No architectural violations found.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(check())
