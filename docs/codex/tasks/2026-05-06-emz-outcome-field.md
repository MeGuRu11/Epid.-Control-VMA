# Задача: emz outcome field

## Метаданные
- Создано: 2026-05-06 09:41
- Слаг: `emz-outcome-field`
- Ветка: `main`
- Статус: `завершено`
- Источник запроса: добавить поле `Исход` в форму ЭМЗ между датой/временем поступления и датой/временем исхода.
- Владелец сессии: `Codex`

## Цель и границы
- Цель: подключить существующий `outcome_type` к форме ЭМЗ через локальный QComboBox и сохранить optional-семантику для старых/черновых записей.
- Почему это важно: по ТТЗ ЭМЗ содержит дату поступления, исход и дату исхода; сейчас исход сохраняемым полем в форме не представлен.
- Что входит: UI ComboBox, mapping UI-label <-> stable code, payload/detail/read-path, unit/integration tests, документация.
- Что не входит: новая колонка БД, миграция, изменение смысла `outcome_date`, изменение бизнес-логики дат/времени.
- Ограничения / риски: не подставлять исход по умолчанию как медицинский факт; старые записи с `NULL outcome_type` должны открываться.

## Контекст
- Ключевые файлы / модули: `app/ui/emz/emz_form.py`, `app/ui/emz/form_widget_factories.py`, `app/ui/emz/form_utils.py`, `app/ui/emz/form_request_builders.py`, `app/application/dto/emz_dto.py`, `app/application/services/emz_service.py`.
- Зависимые документы / скиллы: `AGENTS.md`, `.agents/skills/epid-control/SKILL.md`, `docs/context.md`, `docs/progress_report.md`, `docs/session_handoff.md`.
- Факты, которые уже подтверждены:
  - `EmzVersionPayload.outcome_type` уже существует.
  - SQLAlchemy-модель `EmrCaseVersion.outcome_type` уже существует.
  - Alembic-миграции уже создают `outcome_type`, поэтому новая миграция не нужна.
  - Разрыв в текущей реализации: `EmzCaseDetail` и `EmzService.get_current()` не возвращают `outcome_type`, а форма не собирает и не применяет это поле.
- Гипотезы / вопросы для проверки:
  - Исход должен оставаться optional, так как текущая валидация не требует его до завершения госпитализации.

## План
1. [x] Уточнить критерии готовности и границы.
2. [x] Собрать только релевантный контекст и ссылки на файлы.
3. [x] Выполнить изменения малыми шагами.
4. [x] Прогнать quality gates и зафиксировать результаты.
5. [x] Обновить `docs/progress_report.md` и `docs/session_handoff.md`.

## Checkpoints
### 2026-05-06 09:41
- Создан task-файл.
- Стартовый снимок рабочей директории:
- Рабочее дерево чистое.

### 2026-05-06 09:55
- Root cause: поле исхода уже есть в payload/ORM/миграциях, но не было подключено к `EmzCaseDetail`, `EmzService.get_current()`, UI и `build_emz_version_payload()`.
- Решение: использовать существующую колонку `outcome_type`, добавить scoped UI-mapping `discharge`/`transfer`/`death` и не создавать миграцию.

### 2026-05-06 10:45
- Реализован ComboBox `Исход` между датой/временем поступления и датой/временем исхода.
- Добавлены stable codes `discharge` / `transfer` / `death`, optional placeholder `Не выбран`, apply/collect/reset и service read-path.
- Добавлены unit/integration тесты и offscreen smoke реальной `EmzForm`.

## Validation Ledger
- `ruff check app tests` — pass.
- `python scripts/check_architecture.py` — pass.
- `python -m mypy app tests` — pass (`301 source files`).
- `python -m pytest tests/unit/test_emz_form_widget_factories.py -q` — pass (`10 passed`).
- `python -m pytest tests/unit/test_emz_form_mappers.py -q` — pass (`6 passed`).
- `python -m pytest tests/unit/test_emz_form_request_builders.py -q` — pass (`4 passed`).
- `python -m pytest tests/unit/test_emz_form_validators.py -q` — pass (`6 passed`).
- PowerShell-expanded equivalent of `python -m pytest tests/unit/test_emz_form_* -q` — pass (`112 passed`).
- `python -m pytest tests/integration/test_emz_service.py -q` — pass (`6 passed`).
- `python -m pytest -q` — pass (`472 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m alembic upgrade head` — pass.
- `python -m alembic check` — pass (`No new upgrade operations detected`).
- `python scripts/check_mojibake.py` — pass.
- `git diff --check` — pass; только CRLF warnings Git, whitespace ошибок нет.
- Offscreen smoke `EmzForm` — pass (`offscreen smoke ok`).

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
- Следующее действие: сделать коммит `fix: добавлен исход в форму ЭМЗ`.
- Открытые вопросы / блокеры: нет.
- Что обязательно проверить вручную: при ближайшей видимой GUI-регрессии создать ЭМЗ, выбрать `Перевод`, сохранить, открыть снова и изменить на `Летальный исход`.
