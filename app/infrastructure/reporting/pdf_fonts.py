from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_UNICODE_FONT_NAME = "EpidControlUnicode"


def _candidate_font_paths() -> list[Path]:
    env_font = os.getenv("EPIDCONTROL_PDF_FONT")
    paths: list[Path] = []
    if env_font:
        paths.append(Path(env_font))

    paths.extend(
        [
            # Windows
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/tahoma.ttf"),
            # Linux
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        ]
    )
    return paths


@lru_cache(maxsize=1)
def get_pdf_unicode_font_name() -> str:
    if _UNICODE_FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return _UNICODE_FONT_NAME

    for font_path in _candidate_font_paths():
        if not font_path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(_UNICODE_FONT_NAME, str(font_path)))
            return _UNICODE_FONT_NAME
        except Exception:  # noqa: BLE001
            continue

    raise RuntimeError(
        "Не найден TTF-шрифт с поддержкой кириллицы для PDF. "
        "Укажите путь через EPIDCONTROL_PDF_FONT."
    )
