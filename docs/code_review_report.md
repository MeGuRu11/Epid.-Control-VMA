# Код-ревью проекта Epid Control — 2026-04-06

## Статус после 4 этапов рефакторинга

### Что было исправлено
- Выполнен этап очистки проекта: удалены нерелевантные скиллы/артефакты, убран `pyright`, унифицирован контур на `mypy`.
- Устранены архитектурные нарушения `UI -> Infrastructure`: UI переведен на application-сервисы.
- Вынесена часть бизнес-логики/сборки payload из UI в application-слой (`setup`, `lab/sanitary payload`, `form100 payload`).
- Исправлен schema drift: `alembic check` приведен к стабильному `PASS`.
- Усилена SQL-безопасность в миграциях/FTS-менеджере, донастроены связи ORM (`back_populates`).
- Существенно улучшено качество типизации: убраны/обоснованы `type: ignore`, исправлены проблемные типы.
- Улучшены тесты: часть моков БД заменена на реальную SQLite, добавлены/усилены проверки в слабых тестах.
- Актуализированы ключевые документы (`README`, `context`, `progress/session handoff`) и выполнен поэтапный аудит (4 прохода).

### Текущее состояние quality gates
- ruff: PASS (`All checks passed!`)
- mypy: PASS (`Success: no issues found in 253 source files`)
- pytest: PASS (`236 passed, 2 warnings`)
- alembic: PASS (`No new upgrade operations detected`, `current=head`)

## Архитектура
- Критических нарушений зависимостей не найдено:
  - `UI -> Infrastructure`: 0.
  - `Domain -> external layers/libs (по заданным паттернам)`: 0.
  - `Application -> UI`: 0.
- Допустимые зависимости `Application -> Infrastructure` присутствуют.
- Зафиксирован архитектурный риск: UI в ряде мест импортирует `SQLAlchemyError` (утечка ORM-детали в presentation).
- SQL/DB-логика напрямую в UI по проверкам `execute/query/session_scope` не обнаружена.

## Типизация
- `mypy`: PASS (253 файла).
- Функций без аннотации возвращаемого типа: 1 (`app/application/dto/emz_dto.py`).
- `type: ignore`: 2, оба с обоснованием, без необоснованных — 0.
- `Any`: 249 вхождений; концентрация в `exchange_service`, `form100_service_v2`, `form100_rules_v2`, `reporting_service`, `form100_wizard`.
- Приоритет типизации: service-слой и Form100-контур (payload/manifest/JSON-структуры).

## Тесты
- Покрытие общее: 44%.
- По слоям:
  - domain: 86.1%
  - application: 71.1%
  - infrastructure: 84.6%
  - ui: 31.3%
- Единственный критичный модуль ниже 30%: `app/application/services/sanitary_sample_payload_service.py` (28%).
- Файлов тестов без assert/raises: 0.
- Низкий `assertions/tests` (<=1.0) у:
  - `tests/unit/test_responsive_actions.py`
  - `tests/unit/test_ui_theme_tokens.py`
  - `tests/unit/test_emz_form_case_selectors.py`
- Выявлен 1 случай нарушения правила «не мокать БД/ORM»:
  - `tests/unit/test_backup_service_error_handling.py` (мок `SQLAlchemy engine`).

## БД и миграции
- `alembic check`: PASS.
- `alembic heads`: `0019_form100_v2_schema (head)`.
- `alembic current`: `0019_form100_v2_schema (head)`.
- По базовым regex-проверкам SQL-инъекций (`f-string/.format/конкатенация` для SQL) критичных находок нет.
- Дополнительно найдены 6 DDL `f-string` в `app/infrastructure/db/fts_manager.py`; оценка — low risk (внутренние идентификаторы, не пользовательский ввод), но есть потенциал hardening.
- `relationship(...)` без `back_populates` в `models_sqlalchemy.py` не обнаружено.
- Утечек сессий через `session_scope` не найдено (использование через context manager).

## Документация
- Проверка ссылок в `docs/*.md` и `README.md`: битых локальных ссылок не найдено.
- `README.md`: в целом актуален, quality gates соответствуют фактическому скрипту (4 шага: ruff/mypy/pytest/compileall).
- `docs/context.md`: содержит актуальные рабочие метрики (236+ / 44%), но верхний штамп «Дата обновления» устарел и требует синхронизации.
- `docs/tech_guide.md`: архитектурно соответствует текущему контуру (слои, миграции, quality gates), критичных расхождений не выявлено.

## Приоритизированный план исправлений

### P0 — Критичные (исправить немедленно)
- Убрать мок SQLAlchemy engine в `tests/unit/test_backup_service_error_handling.py` и перевести тест на реальный SQLite test-engine/fixture.

### P1 — Важные (исправить на этой неделе)
- Довести покрытие `app/application/services/sanitary_sample_payload_service.py` выше 70%.
- Скрыть `SQLAlchemyError` за application-исключениями, чтобы UI не зависел от ORM-деталей.
- Укрепить тесты с низким `assertions/tests` (`test_responsive_actions`, `test_ui_theme_tokens`, `test_emz_form_case_selectors`).
- Снизить долю `Any` в ключевых сервисах (`exchange_service`, `form100_service_v2`, `reporting_service`).

### P2 — Рекомендации (при возможности)
- Добавить CI-чек на запрещенные импорты между слоями (архитектурный guardrail).
- Ввести типизированные JSON alias/TypedDict для Form100 payload/manifest.
- Для DDL f-string в `fts_manager` добавить централизованную валидацию/экранирование идентификаторов.
- Синхронизировать служебные даты в документах (`context/progress`) с фактической датой обновления.

## Метрики
| Метрика | До рефакторинга | После |
|---------|------------------|-------|
| Покрытие тестами | 43% | 44% |
| Ошибки ruff | 0 | 0 |
| Ошибки mypy | 0 | 0 |
| Тесты | 233 | 236 passed (2 warnings) |
| type: ignore без обоснования | 56 | 0 |
| Нарушения архитектуры UI→Infra | 5 | 0 |
| alembic check | FAIL | PASS |
