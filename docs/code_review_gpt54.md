# Код-ревью GPT-5.4 — 2026-04-09

## Сводка онбординга

Epid Control — desktop-приложение для ЭМЗ, микробиологии, санитарного контроля, аналитики и обмена данными. Стек проекта: Python 3.11+/3.12, PySide6 Widgets, SQLAlchemy 2, SQLite, Alembic, pydantic, reportlab/openpyxl, ruff, mypy, pytest, PyInstaller. Архитектура формально выдержана в стиле Clean Architecture / DDD: `UI -> Application -> Domain -> Infrastructure`, а `python scripts/check_architecture.py` сейчас проходит без нарушений. Текущее рабочее состояние по quality gates: `ruff`, `mypy`, `pytest --cov` и архитектурный чек зелёные, `256 passed`, общее покрытие `49.91%`, но дефолтный `python -m alembic check` всё ещё падает (`current=0019_form100_v2_schema`, `head=2daa0dea652d`). По `session_handoff` недавно закрыты основные security/P0/P1 задачи: role-gates на import/export, DB-lockout, idle-timeout, path validation, DI в integration tests, сокращение `Any`, архитектурный CI-check и hotfix для Form100 integration-теста. Незакрытые риски после онбординга: дефолтный Alembic state не self-contained, product-case записи артефактов Form100 всё ещё уязвим к `PermissionError`, в части mutating-сервисов сохраняется `actor_id: int | None`, а в коде и документации остались повреждённые строки. В `.agents/skills` сейчас доступно 20 скиллов; ключевые для этого проекта — `epid-control`, `security-review`, `architecture-patterns`, `python-testing`, `python-pro`, `managing-database-testing`, `SQLAlchemy ORM Expert`, `Backend Migration Standards`, `commit-work`, `session-handoff`.

Context7 MCP в этой сессии недоступен; для сверки паттернов использованы официальные документации SQLAlchemy 2, Alembic, mypy и pytest как fallback.

## Результаты ревью

### Критичные проблемы (P0)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `app/application/services/form100_service_v2.py:625` | `_store_imported_pdf()` делает fallback только вокруг `mkdir()`, но не вокруг самой записи файла. Если каталог артефактов уже существует, но не writable, `shutil.copy2()` на `app/application/services/form100_service_v2.py:634` всё ещё падает `PermissionError`; последний фикс закрыл только тестовый сценарий через monkeypatch. | Перенести fallback на весь блок копирования PDF или явно проверять write access перед `shutil.copy2()`, затем добавить регрессионный тест на существующий non-writable каталог артефактов. |
| 2 | `alembic.ini:3` | Дефолтный `python -m alembic check` в рабочем дереве по-прежнему fail: `current=0019_form100_v2_schema`, `head=2daa0dea652d`. Проект проходит Alembic только при ручном `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`, поэтому состояние не воспроизводится как release-ready из обычного checkout. | Привести default target DB к `head` или зафиксировать versioned bootstrap/automation: `upgrade head` перед `check` и единый writable data dir для локального CLI, CI и документации. |

### Важные проблемы (P1)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `app/application/services/emz_service.py:164` | `update_emr()` принимает `actor_id: int | None` и не делает `None`-guard до мутации. В результате новая версия ЭМЗ и audit могут быть записаны с пустым actor. | Сделать `actor_id` обязательным для всех интерактивных mutating-операций ЭМЗ и валидировать его в начале метода. |
| 2 | `app/application/services/emz_service.py:320` | `update_case_meta()` аналогично позволяет анонимное изменение метаданных госпитализации: `actor_id` nullable, audit пишется даже при `None`. | Ввести обязательный `actor_id` и отдельный guard/test на reject при пустом actor. |
| 3 | `app/application/services/form100_service_v2.py:160` | В интерактивных операциях Form100 (`create/update/sign/archive/export/import`) используется `_resolve_actor()` на `app/application/services/form100_service_v2.py:685`, который допускает synthetic actor вместо жёсткого требования аутентифицированного пользователя. Это ослабляет аудитный след и противоречит проектному правилу “каждая мутирующая операция логируется с actor_id”. | Развести interactive/system paths: для UI-сценариев сделать `actor_id` обязательным, а системные импорты/служебные операции оформить отдельным явным режимом. |
| 4 | `app/application/services/saved_filter_service.py:25` | `save_filter()` пишет в БД с `created_by: int | None`, без обязательного actor и без audit-события. Для mutating-сервиса это выбивается из общего security-контура проекта. | Сделать `actor_id` обязательным, записывать только trusted user id и добавить audit либо явно перевести сохранённые фильтры в неаудируемое client-side состояние. |
| 5 | `app/bootstrap/startup.py:89` | В коде сохранился mojibake в пользовательских сообщениях (`РџСЂРѕ...`). Аналогичные повреждённые строки есть в `app/application/services/reference_service.py:177`, `app/application/services/patient_service.py:188`, `app/ui/form100_v2/widgets/bodymap_editor_v2.py:217` и других местах. | Нормализовать повреждённые UTF-8 строки и добавить guard-check на типичные mojibake-паттерны (`Рџ`, `СЃ`, `Ð`, `Ã`) по `app/`. |
| 6 | `docs/session_handoff.md:391` | В документации остались крупные повреждённые секции: `docs/session_handoff.md`, `docs/progress_report.md:3397`, `docs/final_audit_report.md:1`. Это уже мешает онбордингу и делает часть предыдущих аудитов трудночитаемыми. | Переписать повреждённые блоки в UTF-8 и расширить encoding-check на mojibake, а не только на BOM/`U+FFFD`. |

### Рекомендации (P2)
| # | Файл:строка | Проблема | Фикс |
|---|-------------|----------|------|
| 1 | `README.md:27` | README больше не совпадает с реальным quality-gate контуром: перечислены только `ruff`, `mypy`, `pytest`, `compileall`, но пропущен `python scripts/check_architecture.py`, который уже встроен и в локальный скрипт, и в CI. | Синхронизировать README с фактической последовательностью quality gates. |
| 2 | `docs/final_audit_report.md:29` | В отчёте битая markdown-ссылка: `[app/ui/widgets/context_bar.py](app/ui/widgets/context_bar.py)` резолвится относительно `docs/` и не существует. | Использовать `../app/ui/widgets/context_bar.py` или заменить на текстовую ссылку без markdown-target. |
| 3 | `app/ui/analytics/analytics_view.py:1` | Крупные UI-модули остаются god objects: `analytics_view.py` (`1304` строк), `emz_form.py` (`1134`), `theme.py` (`1102`), `sanitary_history.py` (`811`). Архитектурных нарушений импорта нет, но сопровождение и review таких файлов уже дорогие. | Продолжить декомпозицию UI на helpers/presenters/view-model slices без возврата бизнес-логики в presentation. |
| 4 | `app/application/services/dashboard_service.py:1` | Низкое покрытие у важных модулей сохраняется: `dashboard_service` `40%`, `saved_filter_service` `37%`, `emz_service` `44%`, `main.py` `40%`. Это уже не случайные UI-хвосты, а сервисные/стартовые сценарии. | Поднять integration coverage для stateful service paths, startup/migration сценариев и персистентных пользовательских настроек. |
| 5 | `app/application/services/reporting_service.py:1` | Концентрация `Any` остаётся в нескольких ключевых модулях: `reporting_service` `18`, `form100_pdf_report_v2` `16`, `form100_wizard` `15`, `bodymap_editor_v2` `12`. | Продолжить сужение через `TypedDict`, `Protocol`, `JSONDict/JSONValue` там, где структуры уже стабильны. |

### Quality Gates
| Проверка | Результат |
|----------|-----------|
| `python scripts/check_architecture.py` | PASS |
| `ruff check app tests` | PASS |
| `mypy app tests` | PASS (`262 source files`) |
| `pytest --cov=app -q` | PASS (`256 passed, 2 warnings`, `TOTAL 49.91%`) |
| `python -m alembic check` | FAIL (`current=0019_form100_v2_schema`, `head=2daa0dea652d`) |
| `$env:EPIDCONTROL_DATA_DIR='tmp_run/epid-data'; python -m alembic check` | PASS (env-specific workaround) |

### Покрытие
| Слой | % |
|------|---|
| `domain` | `87.08%` |
| `application` | `74.63%` |
| `infrastructure` | `85.02%` |
| `ui` | `37.75%` |
| `TOTAL` | `49.91%` |

### Сравнение с предыдущими аудитами

- По сравнению с аудитами от `2026-04-06` и `2026-04-08`, архитектурный контур остался чистым: `UI -> Infrastructure = 0`, `sqlalchemy` в `app/ui = 0`, необоснованных `type: ignore = 0`.
- Security-фиксы из предыдущих задач в основном закреплены: `manage_exchange`, lockout в БД, idle-timeout, path validation, actor enforcement в `backup/reference/patient/lab/sanitary` действительно присутствуют в коде.
- Покрытие выросло до `49.91%`, а контрольный `pytest --cov=app -q` теперь полностью зелёный (`256 passed`), тогда как `docs/final_audit_report.md` всё ещё отражает более старое состояние с падающим тестом.
- При этом новый review подтвердил, что fix для `test_form100_v2_exchange_and_reporting` стабилизировал именно тест, но не устранил реальный product-case записи PDF в существующий non-writable каталог.
- В отличие от предыдущего финального аудита, кодировка не “чистая”: BOM и `U+FFFD` действительно убраны, но mojibake в коде и документации остаётся заметным и массовым.
- Дополнительно найден новый service-level gap, не зафиксированный в ранних отчётах: `SavedFilterService.save_filter()` всё ещё выпадает из общего правила mandatory actor + audit.

### Что я бы улучшил в первую очередь

1. Закрыть реальную причину `PermissionError` в `Form100ServiceV2`, а не только тестовый сценарий.
2. Привести default Alembic target DB к `head` или сделать env/bootstrap для CLI обязательным и зафиксированным в versioned automation.
3. Убрать `actor_id: int | None` из интерактивных mutating-операций `EmzService`, `Form100ServiceV2` и `SavedFilterService`.
4. Исправить mojibake в коде и документации и добавить автоматическую проверку на типичные повреждённые последовательности.
5. Поднять покрытие для `dashboard_service`, `saved_filter_service`, `emz_service` и startup/migration сценариев, прежде чем делать следующий релизный прогон.
