# Сборка и выпуск Epid Control

## 1. Назначение документа

Документ описывает, как подготовить релиз, собрать исполняемый файл и инсталляторы, а затем провести минимальную приёмку сборки.

## 2. Предварительные условия

Перед сборкой убедитесь, что:

- установлен `Python 3.11+` (`3.12` рекомендуется);
- создано и активировано виртуальное окружение;
- установлены зависимости из `requirements-dev.txt`;
- доступен хотя бы один упаковщик инсталляторов:
  - `NSIS` для `scripts\build_nsis.bat`;
  - `Inno Setup 6` для `scripts\build_installer.ps1`.

Подготовка окружения:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
```

## 3. Обязательный quality gate перед релизом

Перед любой сборкой выполните полный локальный прогон:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Релиз собирается только если этот прогон полностью зелёный.

Скрипт проверяет:

1. `ruff check app tests`
2. `python scripts/check_architecture.py`
3. `mypy app tests`
4. `pytest -q`
5. `python -m compileall -q app tests scripts`
6. `python -m alembic upgrade head`
7. `python -m alembic check`
8. `python scripts/check_mojibake.py`

## 4. Сборка исполняемого файла

Основная команда:

```powershell
scripts\build_exe.bat
```

Внутри вызывается `scripts\build_windows.ps1`.

Что делает сборка:

1. находит рабочий интерпретатор Python;
2. проверяет наличие `PyInstaller`;
3. по умолчанию очищает `build/` и `dist/`;
4. собирает `EpidControl.exe` из `EpidControl.spec`;
5. создаёт `dist\RELEASE_INFO.txt` с версией и временем сборки;
6. запускает `scripts\verify_exe.ps1`.

Опции `scripts\build_windows.ps1`:

- `-SkipClean` — не очищать `build/` и `dist/`;
- `-SkipVerify` — не запускать пост-проверку `EXE`.

Пример:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -SkipVerify
```

Ожидаемые артефакты:

- `dist\EpidControl.exe`
- `dist\RELEASE_INFO.txt`

## 5. Проверка собранного EXE

Скрипт проверки:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_exe.ps1
```

Что он проверяет:

- существует ли `dist\EpidControl.exe`;
- найден ли runtime в `_internal` для собранного дистрибутива;
- создан ли `dist\RELEASE_INFO.txt`.

Если проверка упала, инсталляторы собирать не нужно — сначала исправьте проблему в `EXE`.

## 6. Сборка NSIS-инсталлятора

Команда:

```powershell
scripts\build_nsis.bat
```

Внутри вызывается `scripts\build_installer_nsis.ps1`.

Что использует сборка:

- `dist\EpidControl.exe` как обязательный входной файл;
- `scripts\installer.nsi` как скрипт NSIS;
- версию из `pyproject.toml`, если она не передана явно.

Ожидаемый артефакт:

- `dist\EpidControlSetup_NSIS.exe`

Если нужно передать кастомное имя приложения:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer_nsis.ps1 -AppName "Epid Control VMA"
```

## 7. Сборка Inno Setup-инсталлятора

Команда:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

Что использует сборка:

- `dist\EpidControl.exe` как обязательный входной файл;
- `scripts\installer.iss` как сценарий Inno Setup;
- `ISCC.exe` из `PATH` или из стандартного каталога установки Inno Setup.

Ожидаемый артефакт:

- `dist\EpidControlSetup.exe`

Допустимые параметры:

- `-Version`
- `-Publisher`
- `-AppName`

Пример:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -Publisher "MeGuRu11"
```

## 8. Рекомендуемый релизный сценарий

### 8.1 Подготовка

1. Обновите рабочую ветку.
2. Убедитесь, что документация и changelog синхронизированы.
3. Выполните `quality_gates.ps1`.

### 8.2 Сборка

1. Соберите `EXE` через `scripts\build_exe.bat`.
2. Убедитесь, что `verify_exe.ps1` прошёл успешно.
3. Соберите минимум один инсталлятор:
   - `scripts\build_nsis.bat`, или
   - `scripts\build_installer.ps1`.

### 8.3 Приёмка артефакта

1. Установите приложение на чистую машину или чистый профиль.
2. Запустите приложение.
3. Проверьте первый старт и создание БД.
4. Проверьте логин.
5. Проверьте открытие основных разделов.
6. Прогоните ключевые сценарии из `docs/manual_regression_scenarios.md`.

## 9. Минимальный smoke после сборки

После сборки проверьте хотя бы следующие шаги:

1. приложение стартует без падения;
2. создаётся или открывается рабочая БД;
3. работает логин;
4. открываются `Главная`, `ЭМЗ`, `Поиск и ЭМК`, `Лаборатория`, `Санитария`, `Аналитика`, `Форма 100`;
5. выполняется хотя бы один экспорт отчёта;
6. открывается `Администрирование` под ролью `admin`.

## 10. Частые проблемы

### 10.1 `PyInstaller` не найден

Причина:

- зависимости не установлены в активном интерпретаторе.

Что делать:

- активировать нужное окружение;
- выполнить `pip install -r requirements-dev.txt`.

### 10.2 `makensis.exe` не найден

Причина:

- `NSIS` не установлен или не добавлен в `PATH`.

Что делать:

- установить `NSIS`;
- либо добавить путь к `makensis.exe` в `PATH`.

### 10.3 `ISCC.exe` не найден

Причина:

- `Inno Setup` не установлен или не найден по стандартному пути.

Что делать:

- установить `Inno Setup 6`;
- добавить путь к `ISCC.exe` в `PATH`.

### 10.4 Не найден `dist\EpidControl.exe`

Причина:

- инсталлятор запускается до сборки основного `EXE`.

Что делать:

- сначала выполнить `scripts\build_exe.bat`.

### 10.5 Ошибки доступа при сборке

Причина:

- терминал не имеет прав на очистку `build/` и `dist/` или на запись в системные каталоги упаковщика.

Что делать:

- закрыть процессы, использующие `dist\EpidControl.exe`;
- при необходимости открыть терминал с повышенными правами;
- повторить сборку.

## 11. Что прикладывать к релизу

Минимальный комплект:

- собранный `EXE` или инсталлятор;
- `RELEASE_INFO.txt`;
- ссылка на коммит или тег релиза;
- отметка о прохождении quality gates;
- отметка о прохождении ручной регрессии.