# Задача: компактный редизайн contextbar

## Метаданные
- Создано: 2026-04-27 08:26
- Слаг: `компактный-редизайн-contextbar`
- Ветка: `codex-compact-contextbar-redesign`
- Статус: `завершено`
- Источник запроса: пользовательский план compact contextbar redesign
- Владелец сессии: `Codex`

## Цель и границы
- Цель: сделать `ContextBar` компактной панелью закрепления одного пациента и одной госпитализации.
- Почему это важно: текущая панель занимает много вертикального места и дублирует навигацию верхнего меню.
- Что входит: UI-перестройка `ContextBar`, удаление quick-action контракта, QSS, unit-тесты, документация.
- Что не входит: БД, миграции, новые права, постоянное хранение нескольких закреплений.
- Ограничения / риски: сохранить существующую синхронизацию контекста с ЭМЗ, ЭМК и Лабораторией; не вернуть скрытые навигационные кнопки другим путём.

## Контекст
- Ключевые файлы / модули: `app/ui/widgets/context_bar.py`, `app/ui/main_window.py`, `app/ui/theme.py`, `tests/unit/test_dropdown_indicators.py`, `tests/unit/test_main_window_context_selection.py`.
- Зависимые документы / скиллы: `AGENTS.md`, `DESIGN.md`, `docs/context.md`, `epid-control`, `executing-plans`, `test-driven-development`.
- Факты, которые уже подтверждены: текущий `ContextBar` содержит search controls, chips и `ResponsiveActionsPanel` с быстрыми переходами; `MainWindow` передаёт `on_quick_action`.
- Гипотезы / вопросы для проверки: после удаления quick-actions не должны ломаться сценарии открытия Ф-100 из ЭМК.

## План
1. [x] Уточнить критерии готовности и границы.
2. [x] Собрать только релевантный контекст и ссылки на файлы.
3. [x] Выполнить изменения малыми шагами.
4. [x] Прогнать quality gates и зафиксировать результаты.
5. [x] Обновить `docs/progress_report.md` и `docs/session_handoff.md`.

## Checkpoints
### 2026-04-27 08:26
- Создан task-файл.
- Стартовый снимок рабочей директории:
- `?? .npm-cache/`

### 2026-04-27 08:30
- Создана спецификация `docs/specs/SPEC_contextbar_compact_redesign.md`.
- Рабочая ветка создана как `codex-compact-contextbar-redesign`, потому что запись refs для `codex/...` была заблокирована локальным состоянием Git/sandbox.
- Следующий шаг: добавить failing-тесты для нового compact-контракта панели.

### 2026-04-27 09:10
- Добавлены RED-тесты для compact-контракта `ContextBar`; первый targeted run ожидаемо упал на старом API и старых чипах.
- `ContextBar` переведён на compact-row с чипами пациента/госпитализации и раскрываемым блоком выбора.
- Из `MainWindow` удалён quick-action callback для contextbar.
- Обновлены QSS, пользовательская/техническая документация и manual regression сценарии.
- Quality gates по затронутой задаче пройдены.

## Validation Ledger
- `python -m pytest -q tests\unit\test_dropdown_indicators.py -k context_bar` — RED, `5 failed` на старом контракте.
- `python -m pytest -q tests\unit\test_dropdown_indicators.py -k context_bar` — pass (`5 passed, 1 deselected`).
- `python -m pytest -q tests\unit\test_dropdown_indicators.py tests\unit\test_main_window_context_selection.py` — pass (`14 passed`).
- `ruff check app tests` — pass.
- `python scripts\check_architecture.py` — pass.
- `python -m mypy app tests` — pass (`295 source files`).
- `pytest -q` — pass (`404 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m alembic upgrade head` — не запускалась, БД и миграции не менялись.
- `python -m alembic check` — не запускалась, БД и миграции не менялись.
- `python scripts\check_mojibake.py` — pass.
- `git diff --check` — pass, только CRLF warnings для `app/ui/main_window.py` и `tests/unit/test_dropdown_indicators.py`.

## Prompt Patterns
### Планирование
`Сначала обнови этот task-файл: зафиксируй цель, границы, план и критерии готовности. Только потом переходи к правкам.`

### Checkpoint
`Перед следующим крупным шагом обнови Checkpoints и Validation Ledger, чтобы задача пережила паузу или смену сессии.`

### Resume
`Прочитай AGENTS.md, docs/context.md, хвост docs/progress_report.md, docs/session_handoff.md и этот task-файл. После этого продолжай с блока Resume Point.`

### Финальная сверка
`Перед завершением сверь фактические изменения с планом, закрой незавершённые пункты и зафиксируй quality gates.`

## Resume Point
- Следующее действие: сделать коммит после финальной проверки `git diff`.
- Открытые вопросы / блокеры: нет.
- Что обязательно проверить вручную: визуально открыть приложение и убедиться, что contextbar не перекрывает первый экран, а раскрытый выбор помещается на широкой и узкой ширине.
