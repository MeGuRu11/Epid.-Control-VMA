# План: подтверждение закрытия приложения через системные кнопки

**Дата:** 2026-05-09
**Статус:** Утверждён? — нет, ждёт ревью.

---

## Текущее состояние

В `app/ui/main_window.py` есть два пути выхода — обрабатываются по-разному:

### Путь 1 — кнопка «Выйти» (logout)

```python
def _logout(self) -> None:
    if not confirm_logout(self):
        return
    self._relogin_or_close(show_timeout_message=False)
```

`confirm_logout` (`app/ui/widgets/logout_dialog.py`) — диалог:
- Заголовок: «Выход из системы»
- Текст: «Завершить сеанс? Вы вернётесь на экран входа. Текущая сессия будет закрыта.»
- Кнопки: «Остаться» (default) / «Выйти»

Семантика — **logout до экрана логина**, не выход из приложения.

### Путь 2 — системное закрытие окна (✗ / Alt+F4 / Cmd+Q / `closeEvent`)

```python
def closeEvent(self, event) -> None:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.removeEventFilter(self)
    # сохраняет геометрию окна
    ...
    super().closeEvent(event)
```

**Подтверждения нет**. Закрытие происходит мгновенно. Это и есть проблема, которую надо чинить.

### Путь 3 — авто-logout по timeout

```python
def _relogin_or_close(self, *, show_timeout_message: bool) -> None:
    ...  # внутри может быть self.close()
```

Программное закрытие. Подтверждение **не должно** спрашиваться.

---

## Семантическое разграничение

Это два разных действия с разным смыслом:

| Действие | Что значит | Что делать |
|----------|-----------|-----------|
| Кнопка «Выйти» в шапке | Logout — вернуться на экран входа, сессия закрывается | `confirm_logout` (есть) |
| ✗ окна / Alt+F4 / системное закрытие | Exit — полностью закрыть приложение | `confirm_exit` (надо добавить) |
| Авто-logout по timeout | Программное действие | Без подтверждения |
| Программное закрытие из кода | Программное действие | Без подтверждения |

Важно не объединять Logout и Exit в один диалог — у них разный текст и разные последствия.

---

## План работ

### Шаг 1. Новый диалог `confirm_exit`

**Решение:** добавить `ExitConfirmDialog` и функцию `confirm_exit` в существующий
`app/ui/widgets/logout_dialog.py` (по аналогии с `LogoutConfirmDialog`/`confirm_logout`).
Не плодить отдельный модуль — обе функции близки по смыслу.

Альтернатива: вынести в новый `app/ui/widgets/confirmation_dialogs.py` если файл вырастает —
но пока двух диалогов достаточно.

```python
class ExitConfirmDialog(QDialog):
    """Диалог подтверждения закрытия приложения."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("exitConfirmDialog")
        self.setWindowTitle("Закрытие приложения")
        self.setModal(True)
        self.setMinimumWidth(380)

        # ... структура аналогична LogoutConfirmDialog ...

        title = QLabel("Закрыть Epid Control?")
        body = QLabel(
            "Приложение будет полностью закрыто. "
            "Все несохранённые изменения будут потеряны."
        )

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setDefault(True)         # ← безопасный default
        self.cancel_button.clicked.connect(self.reject)

        self.confirm_button = QPushButton("Закрыть")
        self.confirm_button.clicked.connect(self.accept)


def confirm_exit(parent: QWidget | None = None) -> bool:
    """Показать подтверждение закрытия приложения и вернуть True при подтверждении."""
    dialog = ExitConfirmDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
```

Стилизация — добавить новые objectName'ы (`exitConfirmDialog`, `exitDialogIcon`, ...) в `theme.py`,
переиспользовав те же визуальные правила что у logout-диалога.

### Шаг 2. Обновить `MainWindow.closeEvent`

```python
def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
    # Программное закрытие (logout, timeout) выставляет флаг — не спрашивать.
    if not self._close_confirmed:
        if not confirm_exit(self):
            event.ignore()
            return

    # Дальше — существующая логика (event filters, geometry save, unsubscribe).
    app = QApplication.instance()
    if isinstance(app, QApplication):
        app.removeEventFilter(self)

    with contextlib.suppress(RuntimeError, OSError, AttributeError):
        prefs_service = getattr(self.container, "user_preferences_service", None)
        if (
            prefs_service is not None
            and not self.isMaximized()
            and not self.isFullScreen()
        ):
            geom = self.geometry()
            prefs_service.update_window_geometry(
                (geom.x(), geom.y(), geom.width(), geom.height())
            )

    with contextlib.suppress(RuntimeError, AttributeError):
        self._unsubscribe_preferences()

    super().closeEvent(event)
```

Добавить в `__init__`:

```python
self._close_confirmed: bool = False
```

### Шаг 3. Программное закрытие — выставлять флаг

Найти все места, где код **сам** вызывает `self.close()` или `app.quit()`:

1. `_relogin_or_close` — там, где после неудачи перелогина вызывается `self.close()` или
   эквивалент. Перед этим выставить `self._close_confirmed = True`.
2. Любые auto-logout / session-timeout пути, заканчивающиеся закрытием окна.

Поиск:
```powershell
grep -n "self\.close()\|app\.quit()\|QApplication\.quit" app/ui/main_window.py
```

В каждом найденном месте — выставить флаг **до** вызова `close()`:

```python
self._close_confirmed = True
self.close()
```

### Шаг 4. Edge cases

| Случай | Что должно произойти |
|--------|---------------------|
| Пользователь нажал ✗ окна | `confirm_exit` → если «Закрыть» → закрытие; если «Отмена» → остаёмся |
| Alt+F4 / Cmd+Q | То же |
| Кнопка «Выйти» в шапке | `confirm_logout` → logout (без exit-диалога) |
| Auto-logout по timeout | Тихое закрытие без диалога |
| Открыт модальный диалог (визард, настройки) | `confirm_exit` корректно поднимается поверх; `Esc` на нём = «Отмена» |
| Запрос закрытия пришёл из ОС (выключение Windows) | По умолчанию Qt ловит это в `closeEvent`. Если хотим — игнорировать confirm в shutdown-сценарии. **Считаю это отдельным улучшением (P3)** — стандартный Qt-обработчик уже делает разумную вещь, лишний confirm допустим. |

### Шаг 5. Тесты

`tests/unit/test_main_window_close_event.py`:

```python
def test_close_event_shows_confirm_dialog(qtbot, main_window, monkeypatch):
    """При обычном закрытии вызывается confirm_exit."""
    called = {"v": False}
    def fake_confirm(_parent):
        called["v"] = True
        return False  # отмена
    monkeypatch.setattr("app.ui.main_window.confirm_exit", fake_confirm)

    event = QCloseEvent()
    main_window.closeEvent(event)
    assert called["v"] is True
    assert not event.isAccepted()  # пользователь отменил → событие игнорировано

def test_close_event_proceeds_when_confirmed(qtbot, main_window, monkeypatch):
    """При подтверждении — закрытие проходит."""
    monkeypatch.setattr("app.ui.main_window.confirm_exit", lambda _p: True)
    # подменяем prefs_service чтобы не падало на сохранении геометрии
    main_window.container.user_preferences_service = SimpleNamespace(
        update_window_geometry=lambda _g: None,
    )
    event = QCloseEvent()
    main_window.closeEvent(event)
    assert event.isAccepted()

def test_programmatic_close_skips_confirm(qtbot, main_window, monkeypatch):
    """Программное закрытие (флаг _close_confirmed=True) обходит confirm."""
    confirm_called = {"v": False}
    monkeypatch.setattr(
        "app.ui.main_window.confirm_exit",
        lambda _p: confirm_called.__setitem__("v", True) or True,
    )
    main_window._close_confirmed = True
    main_window.container.user_preferences_service = SimpleNamespace(
        update_window_geometry=lambda _g: None,
    )
    event = QCloseEvent()
    main_window.closeEvent(event)
    assert confirm_called["v"] is False  # confirm НЕ вызывался

def test_logout_path_does_not_trigger_exit_confirm(qtbot, main_window, monkeypatch):
    """Кнопка «Выйти» вызывает confirm_logout, но НЕ confirm_exit."""
    exit_called = {"v": False}
    monkeypatch.setattr(
        "app.ui.main_window.confirm_exit",
        lambda _p: exit_called.__setitem__("v", True) or True,
    )
    monkeypatch.setattr("app.ui.main_window.confirm_logout", lambda _p: True)
    monkeypatch.setattr(main_window, "_relogin_or_close", lambda *, show_timeout_message: None)
    main_window._logout()
    assert exit_called["v"] is False
```

И юнит-тест на сам `ExitConfirmDialog`:

```python
def test_exit_dialog_default_button_is_cancel(qtbot):
    dlg = ExitConfirmDialog()
    qtbot.addWidget(dlg)
    assert dlg.cancel_button.isDefault()
    assert not dlg.confirm_button.isDefault()
```

### Шаг 6. Стили (theme.py)

Добавить правила для `#exitConfirmDialog` по образцу `#logoutConfirmDialog`. Проверить:
- что иконка корректно отображается (вопросительный знак / предупреждение);
- что кнопка-default («Отмена») имеет акцентный стиль;
- что кнопка «Закрыть» — деструктивная (опционально красноватая, как в большинстве UI).

---

## Список изменений

| Файл | Тип |
|------|-----|
| `app/ui/widgets/logout_dialog.py` | расширить — добавить `ExitConfirmDialog` и `confirm_exit` |
| `app/ui/main_window.py` | `closeEvent` — confirm + флаг `_close_confirmed`; программные `close()` — выставлять флаг |
| `app/ui/theme.py` | стили для `#exitConfirmDialog` |
| `tests/unit/test_main_window_close_event.py` | **новый** — 4 теста выше |
| `tests/unit/test_exit_dialog.py` | **новый** — 1-2 теста на default-кнопку |

---

## Conventional commit

```
feat: confirm exit on system close — ✗ button, Alt+F4, Cmd+Q
```

Один коммит, объём небольшой, изолированно.

---

## Открытые вопросы

1. **Текст диалога** — устраивает «Закрыть Epid Control? Все несохранённые изменения будут потеряны.»?
   Или предложишь свой?
2. **Кнопка по умолчанию** — «Отмена»? Я предлагаю да (безопаснее, случайный Enter не закроет).
3. **Деструктивный стиль** для кнопки «Закрыть» (красноватая) или нейтральный?
4. **Системный shutdown** (Windows shutdown / logoff) — игнорировать confirm? Считаю что нет смысла усложнять — Qt уже корректно обрабатывает, текущий поведение OK.
