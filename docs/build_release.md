# Сборка и релиз (Windows)

## 1. Предусловия
- Python 3.11+ (рекомендуется 3.12).
- Установлены зависимости проекта:
  - `pip install -r requirements-dev.txt`
- Для инсталлятора:
  - NSIS (для `build_nsis.bat`) и/или
  - Inno Setup (для `build_installer.ps1`).

## 2. Обязательный pre-release quality gate

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Релиз допускается только при полностью зеленом прогоне.

## 3. Сборка EXE

```powershell
scripts\build_exe.bat
```

Ожидаемый артефакт:
- `dist\EpidControl.exe`

Проверка:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_exe.ps1
```

## 4. Сборка установщика

### NSIS

```powershell
scripts\build_nsis.bat
```

### Inno Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

## 5. Smoke-тест на чистой машине
1. Установить приложение из собранного инсталлятора/EXE.
2. Запустить приложение.
3. Убедиться, что БД создается и миграции применяются.
4. Проверить логин и открытие ключевых вкладок.
5. Выполнить короткий сценарий из `docs/manual_regression_scenarios.md`.

## 6. Release checklist
- [ ] Quality-gates пройдены (ruff/mypy/pytest/compileall).
- [ ] EXE собирается без ошибок.
- [ ] Инсталлятор собирается без ошибок.
- [ ] Smoke-тест на чистой машине пройден.
- [ ] `docs/user_guide.md` и `docs/tech_guide.md` актуализированы.
- [ ] Обновлен `docs/progress_report.md`.

## 7. Частые проблемы
- `python312.dll not found`:
  - проверить тип сборки и содержимое `dist\_internal` (для onedir).
- NSIS/ISCC не найдены:
  - установить NSIS/Inno Setup и добавить в `PATH`.
- Ошибки доступа к директории данных:
  - запустить с `EPIDCONTROL_DATA_DIR` в доступный путь.
