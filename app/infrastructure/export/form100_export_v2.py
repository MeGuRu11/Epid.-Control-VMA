from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.infrastructure.security.sha256 import sha256_file


def export_form100_json(cards: list[dict[str, Any]], file_path: str | Path) -> dict[str, int]:
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(
            {
                "schema": "form100.v2",
                "exported_at": datetime.now(UTC).isoformat(),
                "cards": cards,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return {"form100": len(cards)}


def build_manifest_v2(*, files: list[Path], exported_by: str | None, base_dir: Path | None = None) -> dict[str, Any]:
    entries = []
    for file in files:
        if base_dir is not None:
            try:
                name = file.resolve().relative_to(base_dir.resolve()).as_posix()
            except Exception:  # noqa: BLE001
                name = file.name
        else:
            name = file.name
        entries.append(
            {
                "name": name,
                "sha256": sha256_file(file),
                "size": file.stat().st_size,
            }
        )
    return {
        "schema": "form100.exchange.v2",
        "created_at": datetime.now(UTC).isoformat(),
        "exported_by": exported_by,
        "files": entries,
    }
