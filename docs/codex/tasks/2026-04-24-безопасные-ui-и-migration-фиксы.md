# Задача: Безопасные UI и migration фиксы

## Метаданные
- Создано: 2026-04-24 03:13
- Слаг: `безопасные-ui-и-migration-фиксы`
- Ветка: `main`
- Статус: `выполнено`
- Источник запроса: безопасный техдолг-батч по UI-консистентности и SQLite warning
- Владелец сессии: `Codex`

## Цель и границы
- Цель: убрать точечные расхождения с `DESIGN.md` в custom-painted UI и закрыть `DeprecationWarning` по sqlite datetime adapter в миграции `0019_form100_v2_schema.py`.
- Что входит:
  - helper `theme_qcolor(...)` в `app/ui/theme.py`;
  - токенизация безопасных custom-painted зон: login, first run, `MedicalBackground`, `ClockCard`, highlight меню, `PatternOverlay`;
  - замена `#4C78A8` в analytics charts на theme token;
  - исправление `setObjectName("secondary")` -> `secondaryButton` в `StepEvacuation`;
  - нормализация bind-параметров `created_at`, `updated_at`, `birth_date`, `signed_at` в миграции;
  - узкие regression-тесты и полный quality gate.
- Что не входит:
  - redesign `theme.py` или новая paint-system;
  - правки bodymap-палитры, annotation colors и других domain-specific цветовых схем;
  - исправление `pytest_cache_local`, optional PyInstaller warnings и других нецелевых предупреждений окружения.

## Контекст
- Ключевые файлы:
  - `app/ui/theme.py`
  - `app/ui/analytics/charts.py`
  - `app/ui/login_dialog.py`
  - `app/ui/first_run_dialog.py`
  - `app/ui/widgets/animated_background.py`
  - `app/ui/widgets/pattern_overlay.py`
  - `app/ui/home/home_view.py`
  - `app/ui/main_window.py`
  - `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`
  - `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`
  - `tests/unit/test_analytics_charts.py`
  - `tests/unit/test_ui_theme_tokens.py`
  - `tests/unit/test_form100_v2_step_evacuation.py`
  - `tests/integration/test_form100_v2_migration.py`
- Зависящие документы:
  - `AGENTS.md`
  - `DESIGN.md`
  - `.agents/skills/epid-control/SKILL.md`
  - `docs/codex_workflow.md`

## План
1. [x] Уточнить критерии готовности и границы.
2. [x] Собрать релевантный контекст и зафиксировать список целевых файлов.
3. [x] Выполнить пакетный UI- и migration-патч малыми шагами.
4. [x] Прогнать targeted tests и полный quality gate.
5. [x] Обновить документацию сессии и task-файл.

## Checkpoints
### 2026-04-24 03:13
- Создан task-файл.
- Стартовый снимок рабочего дерева зафиксирован; сторонний `.npm-cache/` оставлен вне задачи.

### 2026-04-24 03:20
- Подтверждён рабочий объём: helper для theme token access, безопасная токенизация custom-painted UI, charts, `StepEvacuation`, migration warning.
- За пределами батча оставлены bodymap palette и прочие специализированные цветовые схемы.

### 2026-04-24 03:50
- Добавлен `theme_qcolor(...)` и переведены на токены login, first run, `MedicalBackground`, `ClockCard`, menu highlight и `PatternOverlay`.
- В analytics убран `#4C78A8`; столбцы переведены на `COL["accent2"]`.
- В `StepEvacuation` кнопка подписания переведена на `secondaryButton`.
- В миграции `0019` введена строковая нормализация `datetime`/`date` только для SQLite bind-параметров.

### 2026-04-24 04:00
- Добавлены regression-тесты на theme token brush в charts, `theme_qcolor`, `StepEvacuation` и отсутствие sqlite datetime `DeprecationWarning` в migration test.
- Targeted test batch прошёл успешно: `21 passed`.

### 2026-04-24 04:12
- Полный `scripts\quality_gates.ps1` завершился успешно.
- Результат: `359 passed`; все обязательные проверки зелёные.

## Validation Ledger
- `python -m pytest -q tests/unit/test_analytics_charts.py tests/unit/test_home_view.py tests/unit/test_ui_theme_tokens.py tests/unit/test_form100_v2_step_evacuation.py tests/integration/test_form100_v2_migration.py` — pass (`21 passed in 5.03s`)
- `ruff check app tests` — pass
- `python scripts/check_architecture.py` — pass
- `mypy app tests` — pass (`285 source files`)
- `pytest -q` — pass (`359 passed in 47.22s`)
- `python -m compileall -q app tests scripts` — pass
- `python -m alembic upgrade head` — pass
- `python -m alembic check` — pass
- `python scripts/check_mojibake.py` — pass

## Итог
- Задача выполнена в границах плана.
- Неавтоматизированные остатки:
  - желательно вручную проверить login/first-run showcase экраны;
  - желательно визуально проверить mint-highlight меню, часы на главной и analytics charts;
  - `.npm-cache/` остаётся сторонним untracked-каталогом и в рамках задачи не трогался.

## Resume Point
- Следующее действие: stage + commit текущего батча.
- Блокеров нет.
