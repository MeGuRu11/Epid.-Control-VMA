"""Диалог пользовательских настроек приложения.

Реализован как один файл для удобства навигации: семь вкладок небольшого размера
строятся методами ``_build_*_tab``. Если вкладок станет больше — стоит вынести
их в отдельные классы в этом же пакете.

Архитектурные ограничения:
- UI обращается только к ``UserPreferencesService``; никакого прямого ввода/вывода
  в файловую систему помимо ``QFileDialog`` и открытия проводника.
- Изменения применяются по нажатию «Сохранить»; «Применить» сохраняет, не закрывая.
- «Сбросить настройки» возвращает все значения к умолчаниям (с подтверждением).
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess  # noqa: S404 - использование контролируется (см. _open_path)
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.application.dto.user_preferences_dto import (
    BACKUP_RETENTION_MAX,
    BACKUP_RETENTION_MIN,
    SESSION_TIMEOUT_MAX,
    SESSION_TIMEOUT_MIN,
    UserPreferences,
)
from app.application.services.user_preferences_service import UserPreferencesService
from app.config import DATA_DIR, DB_FILE, LOG_DIR
from app.ui.settings.widgets import (
    FolderPickerRow,
    make_section_hint,
    make_section_title,
)
from app.ui.widgets.dialog_utils import exec_message_box, localize_button_box

logger = logging.getLogger(__name__)


_DENSITY_LABELS: list[tuple[str, str]] = [
    ("normal", "Обычная"),
    ("compact", "Компактная"),
]
_ANIMATION_LABELS: list[tuple[str, str]] = [
    ("adaptive", "Адаптивные (по конфигурации)"),
    ("full", "Полные эффекты"),
    ("minimal", "Минимальные (повышенная производительность)"),
]
_WINDOW_STATE_LABELS: list[tuple[str, str]] = [
    ("last", "Восстанавливать последний размер"),
    ("normal", "Стандартный размер"),
    ("maximized", "Развёрнуто на весь экран"),
]
_BACKUP_FREQ_LABELS: list[tuple[str, str]] = [
    ("startup_daily", "При запуске (раз в сутки)"),
    ("startup_only", "Только при первом запуске"),
    ("manual", "Только вручную"),
]


class SettingsDialog(QDialog):
    """Диалог редактирования пользовательских настроек."""

    def __init__(
        self,
        preferences_service: UserPreferencesService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = preferences_service
        self._initial = preferences_service.current

        self.setObjectName("settingsDialog")
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.setMinimumSize(640, 560)
        self.resize(720, 620)

        self._build_ui()
        self._apply_to_form(self._initial)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        header = QLabel("Настройки приложения")
        header.setObjectName("settingsHeader")
        root.addWidget(header)

        subtitle = QLabel(
            "Часть параметров применяется сразу. Параметры внешнего вида,"
            " отмеченные значком ⟳, требуют перезапуска приложения."
        )
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("settingsTabs")
        self._tabs.addTab(self._build_appearance_tab(), "Внешний вид")
        self._tabs.addTab(self._build_window_tab(), "Окно")
        self._tabs.addTab(self._build_paths_tab(), "Папки")
        self._tabs.addTab(self._build_security_tab(), "Безопасность")
        self._tabs.addTab(self._build_backup_tab(), "Резервные копии")
        self._tabs.addTab(self._build_notifications_tab(), "Уведомления")
        self._tabs.addTab(self._build_about_tab(), "О программе")
        root.addWidget(self._tabs, 1)

        # Низ: кнопки «Сбросить», «Отмена», «Применить», «Сохранить»
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)

        self._reset_btn = QPushButton("Сбросить настройки")
        self._reset_btn.setObjectName("secondaryButton")
        self._reset_btn.setToolTip("Восстановить все настройки к значениям по умолчанию")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        button_row.addWidget(self._reset_btn)

        button_row.addStretch(1)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        localize_button_box(self._button_box)
        apply_btn = self._button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn is not None:
            apply_btn.setText("Применить")
        save_btn = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_btn is not None:
            save_btn.setObjectName("primaryButton")
        self._button_box.accepted.connect(self._on_save_clicked)
        self._button_box.rejected.connect(self.reject)
        if apply_btn is not None:
            apply_btn.clicked.connect(self._on_apply_clicked)
        button_row.addWidget(self._button_box)

        root.addLayout(button_row)

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------

    def _wrap_in_scroll(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("settingsTabScroll")
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    def _build_appearance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Внешний вид интерфейса"))
        layout.addWidget(
            make_section_hint(
                "Настройки оформления окон, плотности элементов и анимаций. "
                "Параметры со значком ⟳ применяются после перезапуска приложения."
            )
        )

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._density_combo = self._make_combo(_DENSITY_LABELS)
        form.addRow("Плотность интерфейса:", self._density_combo)

        self._animation_combo = self._make_combo(_ANIMATION_LABELS)
        form.addRow("Анимации ⟳:", self._animation_combo)

        self._premium_check = QCheckBox("Включить премиум-эффекты ⟳")
        self._premium_check.setToolTip(
            "Расширенные визуальные эффекты: фоновые градиенты, "
            "анимация кнопок и переходов между разделами."
        )
        form.addRow("", self._premium_check)

        self._background_check = QCheckBox("Анимированный медицинский фон")
        form.addRow("", self._background_check)

        layout.addLayout(form)
        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_window_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Окно и разрешение"))
        layout.addWidget(
            make_section_hint(
                "Управление поведением окна при запуске, запоминанием размеров "
                "и положения. Сброс размера полезен, если окно ушло за границы экрана."
            )
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._remember_geometry_check = QCheckBox("Запоминать размер и положение окна")
        form.addRow("", self._remember_geometry_check)

        self._window_state_combo = self._make_combo(_WINDOW_STATE_LABELS)
        form.addRow("Состояние при запуске:", self._window_state_combo)

        layout.addLayout(form)

        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        self._reset_geometry_btn = QPushButton("Сбросить сохранённый размер окна")
        self._reset_geometry_btn.setObjectName("secondaryButton")
        self._reset_geometry_btn.setToolTip(
            "Очистить сохранённую геометрию окна. При следующем запуске будет "
            "использован стандартный размер."
        )
        self._reset_geometry_btn.clicked.connect(self._on_reset_geometry_clicked)
        reset_row.addWidget(self._reset_geometry_btn)
        reset_row.addStretch(1)
        layout.addLayout(reset_row)

        self._geometry_status = QLabel()
        self._geometry_status.setObjectName("settingsSectionHint")
        self._geometry_status.setWordWrap(True)
        layout.addWidget(self._geometry_status)

        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_paths_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Папки для сохранения данных"))
        layout.addWidget(
            make_section_hint(
                "Каталоги по умолчанию для экспорта отчётов и резервных копий. "
                "Если поле оставить пустым — будет использован путь по умолчанию."
            )
        )

        self._pdf_dir_picker = FolderPickerRow(
            "Папка для PDF-отчётов (Form 100, выписки):",
            "",
            self._open_path,
        )
        layout.addWidget(self._pdf_dir_picker)

        self._excel_dir_picker = FolderPickerRow(
            "Папка для Excel/CSV-отчётов (аналитика, выгрузки):",
            "",
            self._open_path,
        )
        layout.addWidget(self._excel_dir_picker)

        self._zip_dir_picker = FolderPickerRow(
            "Папка для ZIP-архивов (импорт/экспорт пакетов):",
            "",
            self._open_path,
        )
        layout.addWidget(self._zip_dir_picker)

        self._backup_dir_picker = FolderPickerRow(
            "Папка для резервных копий БД ⟳:",
            "",
            self._open_path,
        )
        layout.addWidget(self._backup_dir_picker)

        restart_hint = make_section_hint(
            "⟳ — Изменение папки резервных копий применяется только после перезапуска приложения."
        )
        layout.addWidget(restart_hint)

        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_security_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Безопасность и сессия"))
        layout.addWidget(
            make_section_hint(
                "Параметры сессии, защита от неавторизованного доступа в "
                "оставленном без присмотра приложении."
            )
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._session_timeout_spin = QSpinBox()
        self._session_timeout_spin.setRange(SESSION_TIMEOUT_MIN, SESSION_TIMEOUT_MAX)
        self._session_timeout_spin.setSuffix(" мин")
        self._session_timeout_spin.setSingleStep(5)
        self._session_timeout_spin.setToolTip(
            "Через какое время бездействия сессия автоматически завершится."
        )
        form.addRow("Таймаут сессии:", self._session_timeout_spin)

        self._auto_logout_check = QCheckBox("Автоматический выход при бездействии")
        form.addRow("", self._auto_logout_check)
        self._auto_logout_check.toggled.connect(self._on_auto_logout_toggled)

        self._confirm_exit_check = QCheckBox("Запрашивать подтверждение при выходе из системы")
        form.addRow("", self._confirm_exit_check)

        layout.addLayout(form)
        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_backup_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Автоматическое резервное копирование"))
        layout.addWidget(
            make_section_hint(
                "Резервные копии создаются автоматически по расписанию. "
                "Управление создаваемыми копиями (восстановление, удаление) "
                "доступно администратору в разделе «Администрирование»."
            )
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._auto_backup_check = QCheckBox("Создавать резервные копии автоматически")
        form.addRow("", self._auto_backup_check)
        self._auto_backup_check.toggled.connect(self._on_auto_backup_toggled)

        self._backup_freq_combo = self._make_combo(_BACKUP_FREQ_LABELS)
        form.addRow("Частота создания:", self._backup_freq_combo)

        self._backup_retention_spin = QSpinBox()
        self._backup_retention_spin.setRange(BACKUP_RETENTION_MIN, BACKUP_RETENTION_MAX)
        self._backup_retention_spin.setSuffix(" копий")
        form.addRow("Хранить последних:", self._backup_retention_spin)

        layout.addLayout(form)
        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_notifications_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("Уведомления"))
        layout.addWidget(
            make_section_hint(
                "Системные тосты с информацией о результатах операций "
                "и звуковые сигналы при критических событиях."
            )
        )

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._toasts_check = QCheckBox("Показывать всплывающие уведомления (тосты)")
        form.addRow("", self._toasts_check)

        self._sound_check = QCheckBox("Звуковые сигналы при ошибках и завершении операций")
        form.addRow("", self._sound_check)

        layout.addLayout(form)
        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    def _build_about_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(make_section_title("О программе"))
        layout.addWidget(
            make_section_hint(
                "Сведения о приложении, расположении файлов и быстрый доступ "
                "к каталогам данных. Полезно при диагностике проблем."
            )
        )

        info_form = QFormLayout()
        info_form.setSpacing(8)
        info_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        info_form.addRow("Приложение:", self._make_info_label("Эпид. Контроль (Epid Control)"))
        info_form.addRow("Версия:", self._make_info_label(self._read_version()))
        info_form.addRow("Каталог данных:", self._make_info_label(str(DATA_DIR)))
        info_form.addRow("Файл базы данных:", self._make_info_label(str(DB_FILE)))
        info_form.addRow("Каталог логов:", self._make_info_label(str(LOG_DIR)))
        info_form.addRow(
            "Файл настроек:",
            self._make_info_label(str(self._service._repo.file_path)),  # noqa: SLF001
        )
        info_form.addRow("Платформа:", self._make_info_label(platform.platform()))
        info_form.addRow("Python:", self._make_info_label(sys.version.split()[0]))
        layout.addLayout(info_form)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 8, 0, 0)
        actions_row.setSpacing(8)
        open_data_btn = QPushButton("Открыть папку данных")
        open_data_btn.setObjectName("secondaryButton")
        open_data_btn.clicked.connect(lambda: self._open_path(str(DATA_DIR)))
        actions_row.addWidget(open_data_btn)

        open_logs_btn = QPushButton("Открыть папку логов")
        open_logs_btn.setObjectName("secondaryButton")
        open_logs_btn.clicked.connect(lambda: self._open_path(str(LOG_DIR)))
        actions_row.addWidget(open_logs_btn)

        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        layout.addStretch(1)
        return self._wrap_in_scroll(page)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_combo(self, items: list[tuple[str, str]]) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("settingsCombo")
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for value, label in items:
            combo.addItem(label, value)
        return combo

    def _make_info_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("settingsInfoValue")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setWordWrap(True)
        return label

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _read_version(self) -> str:
        try:
            from importlib.metadata import PackageNotFoundError, version

            return version("codex-emr-lab")
        except (PackageNotFoundError, ImportError, ModuleNotFoundError):
            pass
        try:
            changelog = Path(__file__).resolve().parents[3] / "CHANGELOG.md"
            if changelog.exists():
                for line in changelog.read_text(encoding="utf-8").splitlines():
                    text = line.strip()
                    if text.startswith("## "):
                        return text.lstrip("# ").strip()
        except OSError:
            logger.exception("Failed to read CHANGELOG version")
        return "—"

    def _open_path(self, path: str) -> None:
        """Открыть путь во внешнем проводнике (Windows/macOS/Linux)."""
        if not path:
            return
        target = Path(path)
        if not target.exists():
            try:
                target.mkdir(parents=True, exist_ok=True)
            except OSError:
                exec_message_box(
                    self,
                    "Не удалось открыть папку",
                    f"Каталог не существует и не может быть создан:\n{path}",
                    icon=QMessageBox.Icon.Warning,
                )
                return
        url = QUrl.fromLocalFile(str(target))
        if QDesktopServices.openUrl(url):
            return
        # Fallback на системные команды (например, в headless-окружении openUrl
        # может вернуть False).
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))  # type: ignore[attr-defined]  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)], check=False)  # noqa: S603, S607
            else:
                subprocess.run(["xdg-open", str(target)], check=False)  # noqa: S603, S607
        except OSError:
            logger.exception("Failed to open path in file manager: %s", path)

    # ------------------------------------------------------------------
    # State sync
    # ------------------------------------------------------------------

    def _apply_to_form(self, prefs: UserPreferences) -> None:
        # Внешний вид
        self._set_combo_value(self._density_combo, prefs.ui_density)
        self._set_combo_value(self._animation_combo, prefs.ui_animation_policy)
        self._premium_check.setChecked(prefs.ui_premium_enabled)
        self._background_check.setChecked(prefs.ui_background_enabled)

        # Окно
        self._remember_geometry_check.setChecked(prefs.remember_window_geometry)
        self._set_combo_value(self._window_state_combo, prefs.window_initial_state)
        self._update_geometry_status(prefs)

        # Папки
        self._pdf_dir_picker.set_value(prefs.pdf_export_dir)
        self._excel_dir_picker.set_value(prefs.excel_export_dir)
        self._zip_dir_picker.set_value(prefs.zip_export_dir)
        self._backup_dir_picker.set_value(prefs.backup_dir)

        # Безопасность
        self._session_timeout_spin.setValue(prefs.session_timeout_minutes)
        self._auto_logout_check.setChecked(prefs.auto_logout_enabled)
        self._confirm_exit_check.setChecked(prefs.confirm_before_exit)
        self._on_auto_logout_toggled(prefs.auto_logout_enabled)

        # Бэкапы
        self._auto_backup_check.setChecked(prefs.auto_backup_enabled)
        self._set_combo_value(self._backup_freq_combo, prefs.auto_backup_frequency)
        self._backup_retention_spin.setValue(prefs.backup_retention_count)
        self._on_auto_backup_toggled(prefs.auto_backup_enabled)

        # Уведомления
        self._toasts_check.setChecked(prefs.toasts_enabled)
        self._sound_check.setChecked(prefs.sound_enabled)

    def _update_geometry_status(self, prefs: UserPreferences) -> None:
        geom = prefs.last_window_geometry
        if geom is None:
            self._geometry_status.setText("Сохранённая геометрия отсутствует.")
        else:
            x, y, w, h = geom
            self._geometry_status.setText(
                f"Сохранённая геометрия: {w}×{h} (положение {x}, {y})."
            )

    def _collect_prefs(self) -> UserPreferences:
        return self._initial.with_updates(
            ui_density=self._density_combo.currentData(),
            ui_animation_policy=self._animation_combo.currentData(),
            ui_premium_enabled=self._premium_check.isChecked(),
            ui_background_enabled=self._background_check.isChecked(),
            remember_window_geometry=self._remember_geometry_check.isChecked(),
            window_initial_state=self._window_state_combo.currentData(),
            pdf_export_dir=self._pdf_dir_picker.value,
            excel_export_dir=self._excel_dir_picker.value,
            zip_export_dir=self._zip_dir_picker.value,
            backup_dir=self._backup_dir_picker.value,
            session_timeout_minutes=self._session_timeout_spin.value(),
            auto_logout_enabled=self._auto_logout_check.isChecked(),
            confirm_before_exit=self._confirm_exit_check.isChecked(),
            auto_backup_enabled=self._auto_backup_check.isChecked(),
            auto_backup_frequency=self._backup_freq_combo.currentData(),
            backup_retention_count=self._backup_retention_spin.value(),
            toasts_enabled=self._toasts_check.isChecked(),
            sound_enabled=self._sound_check.isChecked(),
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_auto_logout_toggled(self, enabled: bool) -> None:
        self._session_timeout_spin.setEnabled(enabled)

    def _on_auto_backup_toggled(self, enabled: bool) -> None:
        self._backup_freq_combo.setEnabled(enabled)
        self._backup_retention_spin.setEnabled(enabled)

    def _on_apply_clicked(self) -> None:
        if self._save_current_form():
            self._initial = self._service.current
            self._update_geometry_status(self._initial)

    def _on_save_clicked(self) -> None:
        if self._save_current_form():
            self.accept()

    def _save_current_form(self) -> bool:
        new_prefs = self._collect_prefs()
        try:
            self._service.update(new_prefs)
        except OSError as exc:
            exec_message_box(
                self,
                "Не удалось сохранить настройки",
                f"Возникла ошибка при записи файла настроек.\n{exc}",
                icon=QMessageBox.Icon.Critical,
            )
            return False
        return True

    def _on_reset_geometry_clicked(self) -> None:
        # Просто очищаем сохранённую геометрию в текущих настройках, фактическая
        # запись произойдёт при «Сохранить» или «Применить».
        self._initial = self._initial.with_updates(last_window_geometry=None)
        self._update_geometry_status(self._initial)
        exec_message_box(
            self,
            "Сохранённый размер окна сброшен",
            "Сохранённая геометрия будет очищена после нажатия «Сохранить» или «Применить».",
        )

    def _on_reset_clicked(self) -> None:
        result = exec_message_box(
            self,
            "Сброс настроек",
            "Все настройки будут возвращены к значениям по умолчанию. Продолжить?",
            icon=QMessageBox.Icon.Question,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        try:
            new_prefs = self._service.reset_to_defaults()
        except OSError as exc:
            exec_message_box(
                self,
                "Не удалось сбросить настройки",
                f"Возникла ошибка при сбросе настроек.\n{exc}",
                icon=QMessageBox.Icon.Critical,
            )
            return
        self._initial = new_prefs
        self._apply_to_form(new_prefs)
