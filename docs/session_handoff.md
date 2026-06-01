# CURRENT: 2026-05-30 - sanitary date filters apply on Enter only

The current handoff is the first `2026-05-30` section below. Older `2026-05-30` and `2026-05-29` notes are retained for context.

# Session 2026-05-30 - sanitary date filters apply on Enter only

## Current State

- Repository: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Task: make Enter in sanitary date filter `date_to` apply the filter exactly like `date_from`, with reset only through the reset button.
- Commit and push were not performed.
- Required shared helpers were not touched: `app/ui/widgets/date_input_flow.py` and `app/ui/widgets/datetime_inputs.py`.

## Done

- Found that `SanitaryHistoryDialog` and `SanitaryDashboard` still refreshed date filters through `QDateEdit.dateChanged`, so date edits could apply before Enter.
- Removed date-filter application from `dateChanged` for both `date_from` and `date_to`.
- Added explicit Return/Enter event handling for both date fields in both sanitary views.
- The Enter handler commits pending text with `interpretText()` and then applies the existing filter refresh logic.
- Reset remains button-only; default/auto-default button behavior was not restored.
- Added regression coverage proving that changing `date_from` or `date_to` does not refresh filters until Enter is pressed.

## Checks

- RED before the fix: targeted new sanitary Enter-only tests - `2 failed`.
- GREEN targeted: targeted new sanitary Enter-only tests - `2 passed`.
- `python -m pytest tests/unit/test_sanitary_history_dialog.py tests/unit/test_sanitary_dashboard.py -q --tb=short` - `18 passed`.
- `python -m app.main` - started in offscreen mode and was stopped after 8 seconds at expected GUI/login wait; no startup crash.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`398 source files`).
- `python scripts/check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `912 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

# Сессия 2026-06-01 - UX fixes v1.1.0

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Задача: внедрить UX-исправления из `CODEX_UX_FIXES_V110.md`.
- Реализация завершена; full quality gate пройден.
- Push не выполнялся.

## Что сделано

- `PatientEmkView` получил встроенный табличный patient picker по аналогии с Lab: полный список при открытии, локальная фильтрация по ФИО/ID/дате рождения, выбор строки грузит карточку пациента и госпитализации.
- Введён общий helper `set_combo_placeholder()` и переведены combo со служебным `Выбрать`/`Выберите...` на placeholder + `currentIndex(-1)`.
- Обновлены reset/restore-ветки и тесты, где старый selectable-placeholder был частью индексации.
- Для Form100 добавлен `form100_required_label()` на базе `FORM100_SIGNING_FIELD_LABELS`; обязательные для подписи поля помечены `*` в editor и wizard.
- `EmptyState` Analytics увеличен по минимальной высоте до 132px для корректного отображения пустой истории отчётов.
- Добавлены/обновлены regression-тесты для всех четырёх пунктов.

## Проверки

- `python -m app.main` - стартовал в offscreen-режиме и остановлен через 8 секунд на ожидаемом GUI/login wait.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`404 source files`).
- `python scripts/check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `929 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

## Следующие шаги

1. Просмотреть атомарные коммиты по четырём UX-пунктам.
2. При необходимости пройти ручной smoke в реальном GUI по ЭМК, Analytics Reports и Form100 signing flow.

## Open Notes

- Working tree still contains the implemented code/test/doc changes and an existing untracked `docs/QA_CHECKLIST_DATETIME_WIDGET.md`.

# Сессия 2026-05-29 - cleanup docs перед v1.1.0

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Ветка: `main`.
- Задача: инвентаризация и уборка документации перед v1.1.0.
- Коммит и push не выполнялись.
- В рабочей копии до начала cleanup уже были незакоммиченные изменения кода и тестов по date/datetime-вводу; они не трогались.

## Что сделано

- Проведена инвентаризация `docs/` и корневых `README.md` / `CHANGELOG.md`.
- Через `git mv` в `docs/archive/` перенесены исторические планы, S4.6 audit-файлы, закрытые Codex task-файлы и реализованные промежуточные spec-планы.
- Создано оглавление архива: `docs/archive/README.md`.
- Обновлены живые документы:
  - `CHANGELOG.md`;
  - `README.md`;
  - `docs/context.md`;
  - `docs/specs/SPEC_analytics_redesign.md`;
  - `docs/progress_report.md`;
  - `docs/session_handoff.md`.
- Untracked/ignored файлы не перемещались и не добавлялись в git:
  - `docs/QA_CHECKLIST_DATETIME_WIDGET.md`;
  - `docs/sample_exports/*`.

## Проверки

- `python scripts\check_mojibake.py` - pass.
- `git diff --stat` - проверен.
- `git status --short` - проверен; кодовые `.py`-изменения в статусе остались только прежними пользовательскими изменениями.

## Открытые вопросы

- Ручной smoke полей 3/4/S, date/datetime-ввода, сборка `EXE` и инсталлятор остаются следующими release-шагами.
- `docs/QA_CHECKLIST_DATETIME_WIDGET.md` остаётся untracked по явному правилу cleanup-промпта.

## Следующие шаги

1. Пользователю проверить таблицу решений по файлам.
2. После принятия cleanup-решений выполнить commit самостоятельно.
3. Перед тегом v1.1.0 пройти ручной smoke и сборочные проверки.
# Сессия 2026-05-30 - sanitary filters and optional date NULL persistence

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Задача: исправить сброс санитарных фильтров по Enter и проверить/исправить сохранение пустых optional-дат как SQL `NULL`, а не `1900-01-01`.
- Коммит и push не выполнялись.
- До начала работы в репозитории уже были незакоммиченные изменения документации и date/datetime-виджетов; они оставлены без отката.

## Что сделано

- Найдена причина бага Enter: в `SanitaryHistoryDialog` кнопка `Сбросить` становилась default/auto-default кнопкой `QDialog`, поэтому Enter в `QDateEdit` вызывал `_clear_filters()`.
- В `SanitaryHistoryDialog` и `SanitaryDashboard` отключен default/auto-default режим у `QPushButton`-действий, чтобы Enter в фильтрах не запускал кнопки.
- В `Form100EditorV2` и wizard-компонентах пустые optional-даты больше не сериализуются как `01.01.1900`; наружу уходит `""`/`None`.
- В `Form100ServiceV2.update_card()` явное `birth_date=None` теперь очищает дату до SQL `NULL`, а отсутствие поля продолжает сохранять прежнее значение.
- Добавлены регрессионные тесты для санитарного Enter, Form100 editor/wizard, очистки `birth_date`, а также SQL `NULL` для optional-дат EMZ/Lab/Sanitary.

## Проверки

- `python -m app.main` - стартовал в offscreen-режиме и был остановлен через 8 секунд на ожидаемом GUI/login wait; startup crash не обнаружен.
- `python -m pytest tests/integration -q --tb=short` - `162 passed`, `1 warning`.
- `python -m pytest tests/unit/test_sanitary_history_dialog.py tests/unit/test_sanitary_dashboard.py -q --tb=short` - `16 passed`.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`398 source files`).
- `python scripts\check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `910 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

## Открытые вопросы

- Ручной smoke в реальном GUI после запуска приложения остается полезным для UX-подтверждения Enter-сценария, но автоматические регрессии покрывают сброс фильтров и SQL `NULL`.
- Следующий шаг перед релизом: собрать/проверить `EXE` и пройти ручные сценарии из release checklist.

---
