from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image as PILImage, ImageDraw

from app.infrastructure.reporting import form100_pdf_report_v2 as report_module


def _make_card_payload(*, with_annotations: bool = True) -> dict[str, Any]:
    annotations: list[dict[str, Any]] = []
    if with_annotations:
        annotations = [
            {
                "annotation_type": "WOUND_X",
                "x": 0.4,
                "y": 0.3,
                "silhouette": "male_front",
                "note": "",
            },
            {
                "annotation_type": "NOTE_PIN",
                "x": 0.7,
                "y": 0.6,
                "silhouette": "male_back",
                "note": "Контроль",
            },
        ]
    return {
        "id": 101,
        "version": 2,
        "status": "DRAFT",
        "birth_date": "1991-05-06",
        "data": {
            "main": {
                "main_full_name": "Иванов Иван Иванович",
                "main_rank": "капитан",
                "main_unit": "в/ч 12345",
                "main_id_tag": "Ж-100",
                "main_injury_date": "03.03.2026",
                "main_injury_time": "11:45",
            },
            "bottom": {
                "main_diagnosis": "Огнестрельное ранение",
                "doctor_signature": "д-р Петров",
            },
            "flags": {
                "flag_emergency": True,
                "flag_radiation": False,
                "flag_sanitation": False,
            },
            "medical_help": {
                "mp_antibiotic": False,
                "mp_analgesic": False,
                "mp_surgical_intervention": True,
                "mp_surgical_intervention_details": "ПХО раны",
                "mp_transfusion_blood": True,
                "mp_transfusion_blood_details": "эритроцитарная масса 250 мл",
            },
            "bodymap_gender": "M",
            "bodymap_annotations": annotations,
            "bodymap_tissue_types": ["мягкие ткани"],
        },
    }


def _create_template_png(image_root: Path) -> None:
    image_root.mkdir(parents=True, exist_ok=True)
    canvas = PILImage.new("RGBA", (1200, 500), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((40, 50, 560, 460), outline=(20, 20, 20, 255), width=3)
    draw.rectangle((640, 50, 1160, 460), outline=(20, 20, 20, 255), width=3)
    canvas.save(image_root / "form_100_bd.png")


def test_export_form100_pdf_v2_uses_template_image_for_bodymap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_root = tmp_path / "images"
    _create_template_png(image_root)
    monkeypatch.setattr(report_module, "_bodymap_image_root", lambda: image_root)

    pdf_path = tmp_path / "form100_report.pdf"
    report_module.export_form100_pdf_v2(card=_make_card_payload(with_annotations=True), file_path=pdf_path)

    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"/Image" in pdf_bytes
    assert len(pdf_bytes) > 2_000


def test_export_form100_pdf_v2_falls_back_to_vector_when_template_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"value": False}
    original_render = report_module._render_bodymap_drawing

    def _spy_render(*args: Any, **kwargs: Any) -> Any:
        called["value"] = True
        return original_render(*args, **kwargs)

    monkeypatch.setattr(report_module, "_bodymap_image_root", lambda: tmp_path / "missing_images")
    monkeypatch.setattr(report_module, "_render_bodymap_drawing", _spy_render)

    pdf_path = tmp_path / "form100_report_fallback.pdf"
    report_module.export_form100_pdf_v2(card=_make_card_payload(with_annotations=True), file_path=pdf_path)

    assert called["value"] is True
    assert pdf_path.read_bytes().startswith(b"%PDF-")
