from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Any, cast

from app import main as main_module


def _reset_stderr_tee() -> None:
    stream = main_module._stderr_tee
    if stream is not None:
        with contextlib.suppress(OSError):
            stream.close()
    main_module._stderr_tee = None


def test_install_stderr_tee_tolerates_non_callable_flush(tmp_path: Path, monkeypatch) -> None:
    class _BrokenStderr:
        def write(self, _data: str) -> int:
            return 0

        flush = None

    _reset_stderr_tee()
    monkeypatch.setattr(sys, "stderr", _BrokenStderr(), raising=False)

    log_path = tmp_path / "app.log"
    main_module._install_stderr_tee(log_path)

    tee = cast(Any, sys.stderr)
    assert hasattr(tee, "_streams")
    # Simulate unexpected runtime mutation in bundled environment.
    streams = cast(list[Any], tee._streams)
    streams.append(None)
    tee.write("test\n")
    tee.flush()

    assert log_path.exists()
    _reset_stderr_tee()
