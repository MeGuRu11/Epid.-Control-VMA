"""Корневой conftest.py — выполняется самым первым при любом запуске pytest.

Устанавливает QT_QPA_PLATFORM=offscreen до того, как Qt успеет
инициализироваться. Без этого на Windows/Linux без дисплея pytest
зависает во время сборки тестов (collection).
"""

from __future__ import annotations

import os

# Должно быть установлено ДО любого импорта PySide6/Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
