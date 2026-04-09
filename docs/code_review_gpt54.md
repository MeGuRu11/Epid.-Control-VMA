# Код-ревью GPT-5.4 — 2026-04-09

## Сводка онбординга

Epid Control — desktop-приложение для ЭМЗ, микробиологии, санитарного контроля, аналитики и обмена данными. Стек проекта: Python 3.11+/3.12, PySide6 Widgets, SQLAlchemy 2, SQLite, Alembic, pydantic, reportlab/openpyxl, ruff, mypy, pytest, PyInstaller. Архитектура выдержана в стиле Clean Architecture / DDD: `UI -> Application -> Domain -> Infrastructure`, а `python scripts/check_architecture.py` проходит без нарушений. На момент ревью `ruff`, `mypy`, `pytest --cov` и архитектурный чек были зелёными; `256 passed`, общее покрытие составляло `49.91%`. Недавние сессии закрыли основные security/P0/P1-задачи: role-gates на import/export, lockout в БД, idle-timeout, path validation, DI в integration-тестах и hotfix для Form100 integration-теста. Незакрытые риски на тот момент: default `alembic check` без выделенного data-dir, реальный `PermissionError` при записи PDF-артефактов Form100, nullable `actor_id` в части mutating-сервисов и повреждённые строки mojibake в коде и документации.

## Результаты ревью

### Критичные проблемы (P0)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `app/application/services/form100_service_v2.py:625` | `_store_imported_pdf()` обрабатывал fallback только частично: каталог мог существовать, но быть недоступным для записи, после чего `shutil.copy2()` всё ещё падал `PermissionError`. | Обернуть весь блок копирования в graceful fallback, проверять write access до копирования и добавить регрессионный тест на non-writable каталог. |
| 2 | `alembic.ini:3` / `scripts/quality_gates.ps1` | Дефолтный `python -m alembic check` зависел от окружения и не был самодостаточным в обычном checkout. | Перед `check` всегда выполнять `upgrade head` в контролируемом `EPIDCONTROL_DATA_DIR`, синхронизировать это с CI и README. |

### Важные проблемы (P1)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `app/application/services/emz_service.py:164` | `update_emr()` допускал nullable `actor_id` в mutating-операции. | Сделать `actor_id` обязательным и валидировать в начале метода. |
| 2 | `app/application/services/emz_service.py:320` | `update_case_meta()` имел ту же проблему с `actor_id`. | Ввести жёсткий guard и тест на отказ при пустом actor. |
| 3 | `app/application/services/form100_service_v2.py:160` | В interactive-операциях Form100 использовался путь с synthetic actor через `_resolve_actor()`. | Развести interactive и system paths: для UI-операций `actor_id` обязателен, для системных сценариев нужен явный `system=True`. |
| 4 | `app/application/services/saved_filter_service.py:25` | `save_filter()` сохранял запись без обязательного actor и без audit-события. | Сделать `actor_id` обязательным и записывать audit-событие при сохранении фильтра. |
| 5 | `app/bootstrap/startup.py:89` и смежные файлы | В коде и документации оставались строки mojibake. | Нормализовать повреждённые UTF-8 строки и добавить автоматическую проверку на типичные паттерны mojibake. |

### Рекомендации (P2)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `README.md:27` | README не был синхронизирован с реальным quality-gate контуром. | Явно перечислить `check_architecture`, `alembic upgrade/check` и проверку mojibake. |
| 2 | `docs/final_audit_report.md:29` | В документации была битая markdown-ссылка на файл UI. | Исправить относительный путь или убрать markdown-target. |
| 3 | `app/ui/analytics/analytics_view.py:1` и др. | В проекте остались крупные UI god objects. | Продолжить декомпозицию UI на меньшие presentation-компоненты без возврата бизнес-логики в UI. |
| 4 | `app/application/services/dashboard_service.py:1` и др. | У ряда важных модулей оставалось низкое покрытие. | Поднять integration coverage для stateful service paths и startup/migration сценариев. |
| 5 | `app/application/services/reporting_service.py:1` и др. | В нескольких ключевых модулях сохранялась концентрация `Any`. | Продолжить сужение через `TypedDict`, `Protocol`, `JSONDict/JSONValue`. |

### Quality Gates
| Проверка | Результат |
|----------|-----------|
| `python scripts/check_architecture.py` | PASS |
| `ruff check app tests` | PASS |
| `mypy app tests` | PASS (`262 source files`) |
| `pytest --cov=app -q` | PASS (`256 passed`, `TOTAL 49.91%`) |
| `python -m alembic check` | FAIL без выделенного `EPIDCONTROL_DATA_DIR` |
| `EPIDCONTROL_DATA_DIR=tmp_run/epid-data; python -m alembic check` | PASS |

### Покрытие
| Слой | % |
|------|---|
| `domain` | `87.08%` |
| `application` | `74.63%` |
| `infrastructure` | `85.02%` |
| `ui` | `37.75%` |
| `TOTAL` | `49.91%` |

### Сравнение с предыдущими аудитами

- Архитектурный контур остался чистым: `UI -> Infrastructure = 0`, `sqlalchemy` в `app/ui = 0`, необоснованных `type: ignore = 0`.
- Security-фиксы предыдущих этапов закрепились: `manage_exchange`, lockout в БД, idle-timeout, path validation и actor enforcement для основных mutating-сервисов.
- Покрытие выросло примерно до `49.91%`, а контрольный `pytest --cov=app -q` стал полностью зелёным.
- При этом ревью подтвердило, что часть фиксов была точечной: тестовый workaround по Form100 не закрывал продуктовый сценарий записи в non-writable каталог.
- Дополнительно был найден service-level gap в `SavedFilterService`, который не был явно зафиксирован в ранних аудитах.

### Что я бы улучшил в первую очередь

1. Закрыть реальную причину `PermissionError` в `Form100ServiceV2`, а не только тестовый сценарий.
2. Сделать Alembic bootstrap воспроизводимым по умолчанию для локального запуска и CI.
3. Убрать nullable `actor_id` из всех interactive mutating-операций.
4. Дочистить mojibake в коде и документации и зафиксировать это автоматической проверкой.
5. Поднять покрытие для `dashboard_service`, `saved_filter_service`, `emz_service` и startup/migration-сценариев.
