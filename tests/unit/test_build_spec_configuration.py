from __future__ import annotations

from pathlib import Path


def _spec_text() -> str:
    spec_path = Path(__file__).resolve().parents[2] / "EpidControl.spec"
    return spec_path.read_text(encoding="utf-8")


def test_spec_collects_pyqtgraph_submodules() -> None:
    text = _spec_text()

    assert 'collect_submodules("pyqtgraph")' in text


def test_spec_disables_upx_for_runtime_stability() -> None:
    text = _spec_text()

    assert "upx=False" in text
