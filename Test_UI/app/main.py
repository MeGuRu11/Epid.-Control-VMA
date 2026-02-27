
import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication, QDialog

ACCEPTED = int(QDialog.DialogCode.Accepted)

if __package__ in (None, ""):
    # Support direct script execution: python app/main.py
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.config import get_app_dirs
    from app.infrastructure.db.engine import init_engine, create_all
    from app.application.services.auth_service import AuthService
    from app.ui.style import apply_theme
    from app.ui.login_dialog import LoginDialog
    from app.ui.first_run_dialog import FirstRunDialog
    from app.ui.main_window import MainWindow
else:
    from .config import get_app_dirs
    from .infrastructure.db.engine import init_engine, create_all
    from .application.services.auth_service import AuthService
    from .ui.style import apply_theme
    from .ui.login_dialog import LoginDialog
    from .ui.first_run_dialog import FirstRunDialog
    from .ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EpiSafe")

    # Загружаем русский перевод Qt (кнопки Save/Cancel/OK/Yes/No → на русский)
    _translator = QTranslator(app)
    _tr_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if _translator.load(QLocale(QLocale.Language.Russian), "qtbase", "_", _tr_path):
        app.installTranslator(_translator)

    apply_theme(app)

    dirs = get_app_dirs()
    engine = init_engine(dirs.db_path)
    create_all(engine)

    auth = AuthService(engine)

    if auth.is_first_run():
        d = FirstRunDialog(auth)
        if d.exec() != ACCEPTED:
            return 0

    login = LoginDialog(auth)
    if login.exec() != ACCEPTED:
        return 0

    win = MainWindow(engine, login.session)
    win.show()
    return app.exec()

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
