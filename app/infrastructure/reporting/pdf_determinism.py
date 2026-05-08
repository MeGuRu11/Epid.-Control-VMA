from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate


def _invariant_canvas(*args: Any, **kwargs: Any) -> canvas.Canvas:
    kwargs["invariant"] = 1
    return canvas.Canvas(*args, **kwargs)


def build_invariant_pdf(doc: SimpleDocTemplate, flowables: Sequence[Any]) -> None:
    """Собирает PDF через ReportLab в воспроизводимом invariant-режиме."""
    doc.build(list(flowables), canvasmaker=_invariant_canvas)
