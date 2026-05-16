from __future__ import annotations

import atexit
import logging
import sys
import time
from io import UnsupportedOperation
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import TextIO, cast

# Ensure project root on sys.path when running as script or bundled app
_MEIPASS = getattr(sys, "_MEIPASS", None)
ROOT_DIR = Path(_MEIPASS) if _MEIPASS else Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import (  # noqa: E402
    QMessageLogContext,
    QRect,
    QSize,
    QTimer,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtGui import QCursor, QIcon, QScreen  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox, QWidget  # noqa: E402

from app.bootstrap.startup import (  # noqa: E402
    has_users,
    initialize_database,
    seed_core_data,
    warn_missing_plot_dependencies,
)
from app.config import DB_FILE, LOG_DIR, settings  # noqa: E402
from app.container import build_container  # noqa: E402
from app.infrastructure.db.session import session_scope  # noqa: E402
from app.ui.first_run_dialog import FirstRunDialog  # noqa: E402
from app.ui.login_dialog import LoginDialog  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from app.ui.theme import apply_theme  # noqa: E402
from app.ui.widgets.date_input_flow import DateInputAutoFlow  # noqa: E402
from app.ui.widgets.dialog_utils import exec_message_box  # noqa: E402

_stderr_tee: TextIO | None = None


def _setup_logging() -> Path:
    log_path = LOG_DIR / "app.log"
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    return log_path


def _install_stderr_tee(log_path: Path) -> None:
    global _stderr_tee
    if _stderr_tee is not None:
        return

    log_file = open(log_path, "a", encoding="utf-8")  # noqa: SIM115
    atexit.register(log_file.close)

    class _TeeStream:
        def __init__(self, *streams: object | None) -> None:
            # Keep only stream-like objects with callable write/flush methods.
            self._streams: list[object] = []
            for stream in streams:
                if stream is None:
                    continue
                write_fn = getattr(stream, "write", None)
                flush_fn = getattr(stream, "flush", None)
                if callable(write_fn) and callable(flush_fn):
                    self._streams.append(stream)

        def write(self, data: str) -> int:
            written = 0
            for stream in self._streams:
                try:
                    write_fn = getattr(stream, "write", None)
                    flush_fn = getattr(stream, "flush", None)
                    if not callable(write_fn):
                        continue
                    result = write_fn(data)
                    if isinstance(result, int):
                        written = result
                    if callable(flush_fn):
                        flush_fn()
                except (AttributeError, OSError, ValueError, UnsupportedOperation, TypeError):
                    continue
            return written

        def flush(self) -> None:
            for stream in self._streams:
                try:
                    flush_fn = getattr(stream, "flush", None)
                    if callable(flush_fn):
                        flush_fn()
                except (AttributeError, OSError, ValueError, UnsupportedOperation, TypeError):
                    continue

        def isatty(self) -> bool:
            for stream in self._streams:
                try:
                    isatty_fn = getattr(stream, "isatty", None)
                    if callable(isatty_fn) and isatty_fn():
                        return True
                except (AttributeError, OSError, ValueError, UnsupportedOperation, TypeError):
                    continue
            return False

        def fileno(self) -> int:
            for stream in self._streams:
                try:
                    fileno_fn = getattr(stream, "fileno", None)
                    if callable(fileno_fn):
                        fileno_value = fileno_fn()
                        if isinstance(fileno_value, int):
                            return fileno_value
                except (AttributeError, OSError, ValueError, UnsupportedOperation, TypeError):
                    continue
            return -1

    _stderr_tee = log_file
    sys.stderr = _TeeStream(sys.stderr, log_file)


def _install_exception_hook(log_path: Path) -> None:
    def _handle_exception(exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            logging.getLogger(__name__).info("Interrupted by user (KeyboardInterrupt)")
            return
        logging.getLogger(__name__).error("Unhandled exception", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            exec_message_box(
                cast(QWidget, QApplication.activeWindow()),
                "Ошибка",
                f"Произошла непредвиденная ошибка.\nОтчет: {log_path}",
                icon=QMessageBox.Icon.Critical,
            )
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _handle_exception


def _install_qt_message_handler() -> None:
    last_msg: dict[str, float] = {}
    suppress_prefixes = (
        "QPainter::begin: A paint device can only be painted by one painter at a time.",
        "QPainter::translate: Painter not active",
        "QPainter::worldTransform: Painter not active",
        "QPainter::setWorldTransform: Painter not active",
        "QWidgetEffectSourcePrivate::pixmap: Painter not active",
    )

    def _handle_qt_message(msg_type: QtMsgType, _context: QMessageLogContext, message: str) -> None:
        now = time.monotonic()
        if message.startswith(suppress_prefixes):
            last_time = last_msg.get(message)
            if last_time and now - last_time < 2.0:
                return
            last_msg[message] = now
        logger = logging.getLogger("qt")
        if msg_type == QtMsgType.QtCriticalMsg:
            logger.error("Qt: %s", message)
        elif msg_type == QtMsgType.QtWarningMsg:
            logger.warning("Qt: %s", message)
        else:
            logger.info("Qt: %s", message)

    qInstallMessageHandler(_handle_qt_message)


def _apply_light_theme(app: QApplication) -> None:
    apply_theme(app, settings)


def _create_application() -> QApplication:
    app = QApplication(sys.argv)
    icon_path = ROOT_DIR / "resources" / "icons" / "app.ico"
    if not icon_path.exists():
        icon_path = ROOT_DIR / "resources" / "icons" / "app.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    date_input_flow = DateInputAutoFlow(app)
    app.installEventFilter(date_input_flow)
    _apply_light_theme(app)
    return app


def _teardown_completed_dialog(dialog: QDialog, app: QApplication) -> None:
    if dialog.isVisible():
        dialog.hide()
    app.processEvents()
    dialog.deleteLater()
    app.processEvents()


def _exec_first_run_dialog(dialog: QDialog, app: QApplication) -> QDialog.DialogCode:
    result = QDialog.DialogCode(dialog.exec())
    _teardown_completed_dialog(dialog, app)
    return result


def main() -> int:
    log_path = _setup_logging()
    _install_stderr_tee(log_path)
    _install_exception_hook(log_path)
    _install_qt_message_handler()
    app = _create_application()
    if not initialize_database(
        root_dir=ROOT_DIR,
        db_file=DB_FILE,
        database_url=settings.database_url,
        log_dir=LOG_DIR,
        session_factory=session_scope,
    ):
        return 1
    if (
        not has_users(session_scope)
        and _exec_first_run_dialog(FirstRunDialog(parent=None), app) != QDialog.DialogCode.Accepted
    ):
        return 0
    container = build_container()
    seed_core_data(container)
    warn_missing_plot_dependencies()

    # Регистрируем сервис настроек как источник дефолтных папок экспорта
    # (используется в QFileDialog по всему приложению).
    from app.ui.settings.export_paths import install_preferences_service

    install_preferences_service(container.user_preferences_service)

    login_dialog = LoginDialog(auth_service=container.auth_service)
    if login_dialog.exec() != QDialog.DialogCode.Accepted or not login_dialog.session:
        return 0

    window = MainWindow(session=login_dialog.session, container=container)
    prefs = container.user_preferences_service.current
    if prefs.window_initial_state == "maximized":
        window.showMaximized()
    else:
        window.show()
    _schedule_initial_window_size(window, app, prefs=prefs)
    return app.exec()


def _resolve_window_handle_screen(window: QMainWindow) -> QScreen | None:
    handle = window.windowHandle()
    if handle is None:  # pyright: ignore[reportUnnecessaryComparison]  # PySide6 stubs incorrect
        return None
    return handle.screen()


def _resolve_initial_screen(
    window: QMainWindow,
    app: QApplication,
    *,
    allow_fallback: bool = True,
) -> QScreen | None:
    screen = _resolve_window_handle_screen(window)
    if screen is not None:
        return screen
    if not allow_fallback:
        return None

    cursor_screen = app.screenAt(QCursor.pos())
    if cursor_screen is not None:
        return cursor_screen

    return window.screen() or app.primaryScreen()


def _compute_initial_window_size(available: QRect, minimum_size: QSize) -> tuple[int, int]:
    target_width = max(900, int(available.width() * 0.92))
    target_height = max(700, int(available.height() * 0.9))
    width = min(available.width(), max(minimum_size.width(), target_width))
    height = min(available.height(), max(minimum_size.height(), target_height))
    return max(0, width), max(0, height)


def _apply_initial_window_size(
    window: QMainWindow,
    app: QApplication,
    *,
    prefs: object | None = None,
) -> None:
    from app.application.dto.user_preferences_dto import UserPreferences

    # Если в настройках указан maximized — не трогаем геометрию вообще.
    # Qt сам применит maximized state корректно через showMaximized().
    # Пересчёт адаптивных layouts во вьюхах (HomeView и др.) происходит
    # автоматически через их собственный showEvent.
    if isinstance(prefs, UserPreferences) and prefs.window_initial_state == "maximized":
        return

    # Runtime-страховка: если по любой причине окно уже максимизировано/fullscreen —
    # тоже не трогаем.
    if window.isMaximized() or window.isFullScreen():
        return

    screen = _resolve_initial_screen(window, app)
    if not screen:
        return
    available = screen.availableGeometry()

    # Восстанавливаем последнюю сохранённую геометрию, если включено в настройках.
    if isinstance(prefs, UserPreferences) and prefs.window_initial_state != "maximized":
        saved = prefs.last_window_geometry
        if saved is not None and prefs.remember_window_geometry:
            sx, sy, sw, sh = saved
            # Если сохранённый размер близок к полному экрану (>= 95% доступной
            # области по обеим осям) — пользователь явно работал в развёрнутом
            # окне. Восстанавливаем как maximized, а не через setGeometry,
            # чтобы не уйти в borderless-режим без декораций.
            if sw >= int(available.width() * 0.95) and sh >= int(available.height() * 0.95):
                window.showMaximized()
                return
            min_size = window.minimumSizeHint()
            sw = max(min_size.width(), min(available.width(), sw))
            sh = max(min_size.height(), min(available.height(), sh))
            # Удерживаем окно в пределах видимой области.
            sx = max(available.x(), min(available.x() + available.width() - sw, sx))
            sy = max(available.y(), min(available.y() + available.height() - sh, sy))
            window.setGeometry(sx, sy, sw, sh)
            return

    width, height = _compute_initial_window_size(available, window.minimumSizeHint())
    x = available.x() + max(0, (available.width() - width) // 2)
    y = available.y() + max(0, (available.height() - height) // 2)
    # Windows applies monitor limits more predictably when size and position are set together.
    window.setGeometry(x, y, width, height)


def _schedule_initial_window_size(
    window: QMainWindow,
    app: QApplication,
    retries: int = 3,
    *,
    prefs: object | None = None,
) -> None:
    def _apply_when_ready(remaining_retries: int) -> None:
        if not window.isVisible():
            return
        if _resolve_initial_screen(window, app, allow_fallback=False) is None and remaining_retries > 0:
            QTimer.singleShot(0, lambda: _apply_when_ready(remaining_retries - 1))
            return
        _apply_initial_window_size(window, app, prefs=prefs)

    QTimer.singleShot(0, lambda: _apply_when_ready(retries))

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrupted by user (KeyboardInterrupt)")
        sys.exit(130)
