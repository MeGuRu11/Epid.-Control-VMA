from __future__ import annotations

import logging

from PySide6.QtWidgets import QLabel, QMessageBox, QSizePolicy, QWidget

from app.ui.widgets.toast import show_toast as _show_toast

STATUS_COLORS = {
    "success": "#9AD8A6",
    "warning": "#F4D58D",
    "error": "#E18A85",
    "info": "#7A7A78",
}


def _pill_max_width(label: QLabel) -> int:
    raw = label.property("status_pill_max_width")
    if raw is None:
        return 560
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 560
    return max(180, min(1200, value))


def _refresh_status_style(label: QLabel) -> None:
    style = label.style()
    style.unpolish(label)
    style.polish(label)
    label.update()


def set_status(label: QLabel, message: str, level: str = "info") -> None:
    if not message:
        clear_status(label)
        return
    normalized_level = level if level in STATUS_COLORS else "info"
    label.setText(message)
    label.setObjectName("statusLabel")
    label.setProperty("statusLevel", normalized_level)
    label.setWordWrap(not label.property("status_pill"))
    use_pill = bool(label.property("status_pill"))
    if use_pill:
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        label.setMaximumWidth(min(_pill_max_width(label), label.sizeHint().width() + 16))
    else:
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    _refresh_status_style(label)


def clear_status(label: QLabel) -> None:
    label.clear()
    label.setObjectName("statusLabel")
    label.setProperty("statusLevel", "")
    if label.property("status_pill"):
        label.setMaximumWidth(_pill_max_width(label))
        label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
    else:
        label.setMaximumWidth(16777215)
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
    _refresh_status_style(label)


def show_message(parent: QWidget | None, title: str, message: str, level: str = "info") -> None:
    logger = logging.getLogger(__name__)
    if level == "error":
        logger.error("%s: %s", title, message)
    elif level == "warning":
        logger.warning("%s: %s", title, message)
    else:
        logger.info("%s: %s", title, message)
    if level != "error":
        _show_toast(parent, message, level=level)
        return
    icon_map = {
        "success": QMessageBox.Icon.Information,
        "warning": QMessageBox.Icon.Warning,
        "error": QMessageBox.Icon.Critical,
        "info": QMessageBox.Icon.Information,
    }
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(icon_map.get(level, QMessageBox.Icon.Information))
    box.exec()


def show_error(parent: QWidget | None, message: str, title: str = "Ошибка") -> None:
    show_message(parent, title, message, level="error")


def show_warning(parent: QWidget | None, message: str, title: str = "Предупреждение") -> None:
    show_message(parent, title, message, level="warning")


def show_info(parent: QWidget | None, message: str, title: str = "Информация") -> None:
    show_message(parent, title, message, level="info")


def show_toast(parent: QWidget | None, message: str, level: str = "info") -> None:
    _show_toast(parent, message, level=level)
