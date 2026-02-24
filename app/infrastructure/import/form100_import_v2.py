from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_form100_json(file_path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(file_path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    cards = payload.get("cards", [])
    if not isinstance(cards, list):
        raise ValueError("Некорректный формат form100 JSON: cards должен быть списком")
    normalized: list[dict[str, Any]] = []
    for item in cards:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized
