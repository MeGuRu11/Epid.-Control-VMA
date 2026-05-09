from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image as PILImage, ImageDraw

from app.domain.services.bodymap_geometry import denormalize_for_pil
from app.infrastructure.reporting import form100_pdf_report_v2 as report_module


def _create_template_png(image_root: Path, *, width: int = 800, height: int = 1000) -> None:
    image_root.mkdir(parents=True, exist_ok=True)
    canvas = PILImage.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((20, 20, width // 2 - 20, height - 20), outline=(20, 20, 20, 255), width=3)
    draw.rectangle((width // 2 + 20, 20, width - 20, height - 20), outline=(20, 20, 20, 255), width=3)
    canvas.save(image_root / "form_100_bd.png")


def test_pil_bodymap_marker_uses_shared_geometry(tmp_path: Path, monkeypatch) -> None:
    image_root = tmp_path / "images"
    _create_template_png(image_root)
    captured: list[tuple[float, float]] = []

    def _capture_marker(_draw: Any, *, annotation_type: str, x: float, y: float, note: str = "") -> None:
        del annotation_type, note
        captured.append((x, y))

    monkeypatch.setattr(report_module, "_bodymap_image_root", lambda: image_root)
    monkeypatch.setattr(report_module, "_draw_annotation_marker", _capture_marker)

    flowable = report_module._build_bodymap_image_flowable(
        annotations=[{"annotation_type": "WOUND_X", "x": 0.25, "y": 0.99, "silhouette": "male_front"}],
        max_width_pt=400,
        max_height_pt=500,
    )

    assert flowable is not None
    assert captured
    expected = denormalize_for_pil(
        0.25,
        0.99,
        panel_width_px=400,
        canvas_height_px=1000,
        is_back=False,
    )
    assert captured[0] == expected
    assert captured[0][1] < 1000 * 0.97


def test_drawing_bodymap_marker_uses_shared_geometry(monkeypatch) -> None:
    calls: list[tuple[float, float, float, float, bool]] = []

    def _spy_denormalize(
        x_norm: float,
        y_norm: float,
        *,
        panel_width_pt: float,
        total_height_pt: float,
        is_back: bool,
    ) -> tuple[float, float]:
        calls.append((x_norm, y_norm, panel_width_pt, total_height_pt, is_back))
        return 123.0, 45.0

    monkeypatch.setattr(report_module, "denormalize_for_drawing", _spy_denormalize)

    drawing = report_module._render_bodymap_drawing(
        annotations=[{"annotation_type": "NOTE_PIN", "x": 0.4, "y": 0.7, "silhouette": "male_back"}],
        width_pt=440,
        height_pt=300,
    )

    assert drawing is not None
    assert calls == [(0.4, 0.7, 220.0, 300, True)]
