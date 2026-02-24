from __future__ import annotations

import atexit
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure project root on sys.path when running as script or bundled app
_MEIPASS = getattr(sys, "_MEIPASS", None)
ROOT_DIR = Path(_MEIPASS) if _MEIPASS else Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import QtMsgType, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox  # noqa: E402

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

_stderr_tee: object = None


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
        def __init__(self, *streams) -> None:
            self._streams = [stream for stream in streams if stream is not None]

        def write(self, data: str) -> int:
            written = 0
            for stream in self._streams:
                try:
                    written = stream.write(data)
                    if hasattr(stream, "flush"):
                        stream.flush()
                except Exception:  # noqa: BLE001
                    continue
            return written

        def flush(self) -> None:
            for stream in self._streams:
                if hasattr(stream, "flush"):
                    try:
                        stream.flush()
                    except Exception:  # noqa: BLE001
                        continue

        def isatty(self) -> bool:
            return any(getattr(stream, "isatty", lambda: False)() for stream in self._streams)

        def fileno(self) -> int:
            for stream in self._streams:
                if hasattr(stream, "fileno"):
                    try:
                        return stream.fileno()
                    except Exception:  # noqa: BLE001
                        continue
            return -1

    _stderr_tee = log_file
    sys.stderr = _TeeStream(sys.stderr, log_file)


def _install_exception_hook(log_path: Path) -> None:
    def _handle_exception(exc_type, exc, tb) -> None:
        logging.getLogger(__name__).error("Unhandled exception", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(
                None,
                "Ошибка",
                f"Произошла непредвиденная ошибка.\nОтчет: {log_path}",
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

    def _handle_qt_message(msg_type: QtMsgType, _context, message: str) -> None:
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
    if not has_users(session_scope):
        wizard = FirstRunDialog(parent=None)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return 0
    container = build_container()
    seed_core_data(container)
    warn_missing_plot_dependencies()

    login_dialog = LoginDialog(auth_service=container.auth_service)
    if login_dialog.exec() != QDialog.DialogCode.Accepted or not login_dialog.session:
        return 0

    window = MainWindow(session=login_dialog.session, container=container)
    _apply_initial_window_size(window, app)
    window.show()
    return app.exec()


def _apply_initial_window_size(window: QMainWindow, app: QApplication) -> None:
    screen = window.screen() or app.primaryScreen()
    if not screen:
        return
    available = screen.availableGeometry()
    width = max(900, int(available.width() * 0.92))
    height = max(700, int(available.height() * 0.9))
    window.resize(width, height)
    x = available.x() + max(0, (available.width() - width) // 2)
    y = available.y() + max(0, (available.height() - height) // 2)
    window.move(x, y)

if __name__ == "__main__":
    sys.exit(main())
