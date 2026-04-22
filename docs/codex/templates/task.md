# Задача: {{title}}

## Метаданные
- Создано: {{created_at}}
- Слаг: `{{slug}}`
- Ветка: `{{branch}}`
- Статус: `в планировании`
- Источник запроса:
- Владелец сессии: `Codex`

## Цель и границы
- Цель:
- Почему это важно:
- Что входит:
- Что не входит:
- Ограничения / риски:

## Контекст
- Ключевые файлы / модули:
- Зависимые документы / скиллы:
- Факты, которые уже подтверждены:
- Гипотезы / вопросы для проверки:

## План
1. [ ] Уточнить критерии готовности и границы.
2. [ ] Собрать только релевантный контекст и ссылки на файлы.
3. [ ] Выполнить изменения малыми шагами.
4. [ ] Прогнать quality gates и зафиксировать результаты.
5. [ ] Обновить `docs/progress_report.md` и `docs/session_handoff.md`.

## Checkpoints
### {{created_at}}
- Создан task-файл.
- Стартовый снимок рабочей директории:
{{modified_files}}

## Validation Ledger
- `ruff check app tests` —
- `python scripts/check_architecture.py` —
- `mypy app tests` —
- `pytest -q` —
- `python -m compileall -q app tests scripts` —
- `python -m alembic upgrade head` —
- `python -m alembic check` —
- `python scripts/check_mojibake.py` —

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
- Следующее действие:
- Открытые вопросы / блокеры:
- Что обязательно проверить вручную:
