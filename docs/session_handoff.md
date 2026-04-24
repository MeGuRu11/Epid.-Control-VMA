# Сессия 2026-04-24 — очистка устаревших docs-файлов

## Что сделано

- По запросу пользователя выполнена локальная очистка Markdown-документации в `docs/` без изменений кода приложения, БД, миграций, UI и бизнес-логики.
- Удалены явные устаревшие кандидаты:
  - `docs/final_audit_report.md`;
  - `docs/full_audit_report.md`;
  - `docs/code_review_gpt54.md`;
  - `docs/code_review_report.md`;
  - `docs/code_audit_findings.md`;
  - `docs/MASTER_TZ_CODEX.md`.
- Создан каталог `docs/archive/`.
- В архив перенесены документы, которые лучше сохранить как исторический контекст:
  - `docs/archive/security_review_2026-04-07.md`;
  - `docs/archive/forma_100_section.md`;
  - `docs/archive/TTZ_Form100_Module_Adapted_v2_2.md`;
  - `docs/archive/full_system_audit.md`.
- `.npm-cache/` не трогался.

## Что не закончено / в процессе

- Решение по архивированию task-файлов в `docs/codex/tasks/` не принималось; они оставлены на месте.
- Security-тема и `AUD-001` по-прежнему отложены до отдельного разрешения пользователя.

## Открытые проблемы / блокеры

- В исторических записях `docs/progress_report.md` и старых handoff-блоках остаются ссылки на удалённые/перенесённые файлы как часть истории проекта. Они не переписывались.
- Git по-прежнему выводит предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на файловые операции это не повлияло.

## Следующие шаги

1. Проверить, нужно ли архивировать завершённые `docs/codex/tasks/*.md`.
2. При необходимости добавить короткий `README` в `docs/archive/`, если архив будет расти.
3. После подтверждения пользователя можно сделать отдельный docs-коммит.

## Ключевые файлы, которые менялись

- `docs/archive/security_review_2026-04-07.md`
- `docs/archive/forma_100_section.md`
- `docs/archive/TTZ_Form100_Module_Adapted_v2_2.md`
- `docs/archive/full_system_audit.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `rg --files docs -g "*.md"` — pass; архивные файлы видны в `docs/archive/`, удалённые файлы отсутствуют в корне `docs/`.
- `git status --short` — pass; показывает удаления, новый `docs/archive/` и сторонний `.npm-cache/`.
- `rg` по старым путям — pass; оставшиеся совпадения находятся в исторических записях или внутри архивного `full_system_audit.md`.

# Сессия 2026-04-24 — внедрение non-security исправлений после аудита

## Что сделано

- Реализован согласованный пакет исправлений по итогам `docs/full_system_audit.md` без блока безопасности: шифрование backup/export, защита от кражи данных и encrypted artifacts намеренно не затрагивались.
- Исправлен `ruff check app tests scripts`: `scripts/codex_task.py` переведён на `collections.abc.Sequence`, `scripts/test_form100_pdf.py` очищен от `E402`, лишних импортов и trailing whitespace.
- В `ImportExportView` исправлены повреждённые fallback-строки: история пакетов теперь показывает корректные русские сообщения и `Неизвестно` вместо mojibake.
- В `ReferenceView` добавлено подтверждение удаления справочников через `exec_message_box` с `Yes/No` и default `No`; при отказе delete-service и `refresh()` не вызываются.
- В `ExchangeService` экспорт CSV/Excel/PDF/legacy JSON переведён с `session.query(...).all()` на chunked-итерацию через `yield_per(500)` без изменения форматов файлов и import paths.
- Добавлены regression/UI tests для fallback labels import/export, подтверждения удаления справочников, first-run, admin user management, patient EMK destructive confirmation, lab sample validation и Form100 wizard smoke mapping.
- Документация синхронизирована с текущей архитектурной политикой: read-model/reporting query services во временном порядке могут использовать SQLAlchemy в application layer; новые write/use-case потоки вести через repositories/service boundaries. Также уточнены текущий не-strict mypy режим, `Column(...)` ORM-стиль и фактический путь миграций `app/infrastructure/db/migrations`.

## Что не закончено / в процессе

- Security finding `AUD-001` не реализовывался по решению пользователя; к шифрованию backup/export и отдельной модели защиты данных нужно вернуться позже отдельной задачей.
- Большой архитектурный рефакторинг Application -> Infrastructure не выполнялся: текущая политика зафиксирована документально, вынос query logic оставлен для отдельного этапа.
- Схема БД и Alembic migrations не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаётся сторонний untracked каталог `.npm-cache/`; он не относится к этой задаче и не трогался.
- `docs/full_system_audit.md` остаётся audit-снимком на момент проверки: часть findings в нём исторически описывает проблемы, которые теперь частично закрыты этой итерацией.
- PowerShell/git продолжает выводить предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на проверки проекта это не повлияло.

## Следующие шаги

1. Отдельно решить, как фиксировать статус закрытых findings в `docs/full_system_audit.md`: оставить как исторический отчёт или добавить раздел статусов внедрения.
2. Вернуться к `AUD-001` только после отдельного разрешения пользователя на security/encryption работу.
3. Если потребуется, постепенно выносить read-model/query SQLAlchemy logic из application layer без массового рефакторинга.

## Ключевые файлы, которые менялись

- `app/application/services/exchange_service.py`
- `app/ui/import_export/import_export_view.py`
- `app/ui/references/reference_view.py`
- `scripts/codex_task.py`
- `scripts/test_form100_pdf.py`
- `tests/integration/test_exchange_service_import_reports.py`
- `tests/unit/test_audit_ui_regressions.py`
- `tests/unit/test_import_export_history_labels.py`
- `tests/unit/test_reference_view_delete_confirmation.py`
- `tests/unit/test_scripts_imports.py`
- `AGENTS.md`
- `docs/context.md`
- `docs/tech_guide.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`289 source files`).
- `python -m pytest -q tests/unit/test_import_export_history_labels.py tests/unit/test_reference_view_delete_confirmation.py tests/unit/test_audit_ui_regressions.py tests/unit/test_scripts_imports.py` — pass (`10 passed`).
- `python -m pytest -q tests/integration/test_exchange_service_import_reports.py::test_exports_include_rows_beyond_single_batch` — pass.
- `python -m pytest -q tests/integration/test_exchange_service_import_reports.py tests/integration/test_exchange_service_import_zip.py` — pass (`12 passed`).
- `python -m pytest -q` — pass (`370 passed`).
- `python -m pytest --cov=app --cov-report=term-missing` — pass (`370 passed`, `TOTAL 65%`).
- `python -m compileall -q app tests scripts` — pass.
- `rg -n "mypy \(strict\)|Mapped\[\]|migrations/" AGENTS.md docs README.md` — pass для актуальных правок; оставшиеся совпадения относятся к историческим audit/report/spec записям или к уточнённой политике.

# Сессия 2026-04-24 — полный audit-only аудит системы

## Что сделано

- Выполнен полный локальный audit-only аудит Epid Control по архитектуре, доменной/медицинской логике, БД/миграциям, тестам, UI, security/privacy, зависимостям, запуску, производительности и документации.
- Создан отчёт: `docs/full_system_audit.md`.
- Работа велась только в локальной директории `C:\Users\user\Desktop\Program\Epid_System_Codex`; GitHub, remote/main и удалённые версии проекта не использовались как источник истины.
- Код приложения, БД, миграции, UI и бизнес-логика не менялись.

## Что не закончено / в процессе

- Интерактивный GUI smoke через `python -m app.main` не выполнялся: для него нужно отдельное разрешение и безопасная временная БД, чтобы не затронуть рабочие данные.
- Сборка `EXE`/инсталляторов не выполнялась: audit-only задача не должна менять `build/`/`dist/`.
- Исправления найденных рисков не применялись, только зафиксированы в отчёте.

## Открытые проблемы / блокеры

- High: backup/export артефакты не шифруются (`app/application/services/backup_service.py:96`, `app/application/services/exchange_service.py:677`).
- Medium: `ruff check app tests scripts` падает на scripts lint (`scripts/codex_task.py`, `scripts/test_form100_pdf.py`).
- Medium: низкое покрытие нескольких критичных UI-файлов при общем coverage `62%`.
- Medium: повреждённые user-facing строки с `?` в `app/ui/import_export/import_export_view.py`.
- Medium: удаление справочников в `ReferenceView` выполняется без подтверждения.

## Следующие шаги

1. Закрыть High-риск: шифрование backup/export и тесты на encrypted artifacts.
2. Исправить `ruff check app tests scripts`.
3. Исправить строки `?` в Import/Export UI и добавить regression check.
4. Добавить подтверждение удаления справочников.
5. Запланировать UI coverage для first-run/admin/patient/lab/Form100/reference flows.

## Ключевые файлы, которые менялись

- `docs/full_system_audit.md`
- `docs/session_handoff.md`
- `docs/progress_report.md`

## Проверки

- `python scripts/check_architecture.py` — pass.
- `python -m alembic current`, `heads`, `history`, `upgrade head`, `check` на `tmp_run\audit-data` — pass.
- `pytest -q` — pass (`359 passed`).
- `pytest -q -ra` — pass (`359 passed`).
- `pytest --collect-only -q` — pass (`359 tests collected`).
- `pytest --cov=app --cov-report=term-missing` — pass (`TOTAL 62%`).
- `ruff check app tests` — pass.
- `ruff check app tests scripts` — fail (`4` lint errors in scripts).
- `mypy app tests` — pass (`285 source files`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m pip check` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-24 — обновление Codex-скиллов под GPT-5.5

## Что сделано

- Проведён локальный аудит упоминаний GPT/Codex 5.x без использования GitHub или удалённых репозиториев как источника истины.
- `.agents/skills/codex/SKILL.md` переписан под актуальную политику: основная рекомендуемая модель для Codex-задач — `gpt-5.5`.
- В `codex` skill сохранены локальные operational-правила: sandbox, `--skip-git-repo-check`, resume через stdin, stderr handling через `2>/dev/null`, разрешения для high-impact flags.
- Устаревшие default-инструкции по старым GPT-5.x моделям и неподтверждённые benchmark/pricing-значения удалены; добавлена нейтральная формулировка про официальную документацию OpenAI/Codex.
- `.agents/skills/codex/README.md` обновлён с `gpt-5-codex` на `gpt-5.5` в CLI-примере.
- `.agents/skills/setup-codex-skills/SKILL.md` обновлён: `model = "gpt-5.5"`, CLI-примеры `codex -m gpt-5.5` и `codex exec -m gpt-5.5 ...`, fallback-логика через временный `gpt-5.4`.
- `skills-lock.json` обновлён для локального `setup-codex-skills` по воспроизводимому SHA256 от `SKILL.md`.
- `docs/progress_report.md` дополнен записью о docs/skills-only изменениях.

## Что не закончено / в процессе

- Код приложения, БД, миграции, UI и бизнес-логика не менялись.
- Полный quality gate не запускался, потому что задача была только про документацию и agent skills.

## Открытые проблемы / блокеры

- Для `.agents/skills/codex` запись в `skills-lock.json` имеет `sourceType: github`; текущий `computedHash` уже не совпадал с локальным `SKILL.md` до правок. Без обращения к удалённому источнику алгоритм hash неочевиден, поэтому hash для `codex` не подменялся догадкой и требует ручной проверки при следующей ревизии lock-файла.
- В рабочем дереве остаётся сторонний untracked-каталог `.npm-cache/`; в рамках этой docs/skills-задачи он не трогался.

## Следующие шаги

1. При следующей ревизии skill-lock политики решить, должен ли github-source `codex` skill фиксировать локально изменённый hash или hash upstream-источника.
2. Если `gpt-5.5` не отображается в конкретном окружении пользователя, обновить Codex CLI / приложение / IDE extension и временно использовать `gpt-5.4` только как fallback.
3. Перед следующими кодовыми изменениями вернуться к обычному quality gate циклу проекта.

## Ключевые файлы, которые менялись

- `.agents/skills/codex/SKILL.md`
- `.agents/skills/codex/README.md`
- `.agents/skills/setup-codex-skills/SKILL.md`
- `skills-lock.json`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `rg --hidden --glob "!.git/*" -n -e "gpt-5\\.2" -e "gpt-5\\.3-codex" -e "gpt-5\\.3" -e "gpt-5\\.4" -e "GPT-5\\.2" -e "GPT-5\\.3" -e "GPT-5\\.4" .` — pass; оставшиеся старые упоминания являются fallback или историческими.
- `rg --hidden --glob "!.git/*" -n -e "gpt-5\\.5" -e "GPT-5\\.5" .agents docs AGENTS.md README.md DESIGN.md` — pass.
- `python -m json.tool skills-lock.json` — pass.

# Сессия 2026-04-24 — safe UI token alignment и SQLite migration warning fix

## Что сделано

- В `app/ui/theme.py` добавлен минимальный helper `theme_qcolor(token, alpha=None)` для чтения цветовых токенов из `COL` без нового слоя дизайн-абстракций.
- На theme-токены переведены только безопасные зоны, которые уже дублировали существующую палитру:
  - showcase background у `LoginDialog`;
  - showcase background у `FirstRunDialog`;
  - mint-палитра в `MedicalBackground`;
  - `ClockCard` на главной;
  - highlight активного пункта меню в `MainWindow`;
  - `PatternOverlay`.
- В `app/ui/analytics/charts.py` убран жёстко заданный синий `#4C78A8`; обе диаграммы теперь используют `COL["accent2"]`.
- В `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py` `setObjectName("secondary")` заменён на `secondaryButton` без изменения поведения.
- В миграции `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py` добавлены локальные normalizer-helper’ы для SQLite bind-параметров:
  - `datetime` -> строка;
  - `date` -> ISO-строка;
  - `str` и `None` оставляются как есть.
- Нормализация применена только к `created_at`, `updated_at`, `birth_date`, `signed_at`; JSON-часть миграции не менялась.
- Добавлены и обновлены regression-тесты:
  - `tests/unit/test_analytics_charts.py` — проверка, что charts используют brush из theme token;
  - `tests/unit/test_ui_theme_tokens.py` — проверка `theme_qcolor`;
  - `tests/unit/test_form100_v2_step_evacuation.py` — `secondaryButton` и видимость кнопки подписи только для `DRAFT`;
  - `tests/integration/test_form100_v2_migration.py` — явная проверка отсутствия `DeprecationWarning` по sqlite datetime adapter.

## Что не закончено / в процессе

- Кодовая часть завершена.
- Ручной визуальный smoke новых token-aligned зон в этой сессии не выполнялся.

## Открытые проблемы / блокеры

- Блокеров по коду, тестам и quality gates нет.
- В рабочем дереве остаётся сторонний untracked-каталог `.npm-cache/`; в рамках этой задачи он не трогался.
- `PytestCacheWarning`, связанный с локальным cache-каталогом, остаётся внешней проблемой окружения, а не дефектом приложения.

## Следующие шаги

1. Визуально проверить `LoginDialog` и `FirstRunDialog`, чтобы убедиться, что showcase-фоны не потеряли характер после перевода на theme tokens.
2. Открыть главную и убедиться, что часы и highlight активного меню выглядят контрастно и в пределах текущего стиля.
3. Открыть аналитику и проверить, что mint-столбцы диаграмм визуально читаемы на текущем фоне.
4. При следующей релизной пересборке включить эти зоны в ручной smoke.

## Ключевые файлы, которые менялись

- `app/ui/theme.py`
- `app/ui/analytics/charts.py`
- `app/ui/login_dialog.py`
- `app/ui/first_run_dialog.py`
- `app/ui/home/home_view.py`
- `app/ui/main_window.py`
- `app/ui/widgets/animated_background.py`
- `app/ui/widgets/pattern_overlay.py`
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`
- `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`
- `tests/unit/test_analytics_charts.py`
- `tests/unit/test_ui_theme_tokens.py`
- `tests/unit/test_form100_v2_step_evacuation.py`
- `tests/integration/test_form100_v2_migration.py`
- `docs/codex/tasks/2026-04-24-безопасные-ui-и-migration-фиксы.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_analytics_charts.py tests/unit/test_home_view.py tests/unit/test_ui_theme_tokens.py tests/unit/test_form100_v2_step_evacuation.py tests/integration/test_form100_v2_migration.py` — pass (`21 passed in 5.03s`)
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\quality_gates.ps1` — pass
  - `ruff check app tests` — pass
  - `python scripts/check_architecture.py` — pass
  - `mypy app tests` — pass (`285 source files`)
  - `pytest -q` — pass (`359 passed in 47.22s`)
  - `python -m compileall -q app tests scripts` — pass
  - `python -m alembic upgrade head` — pass
  - `python -m alembic check` — pass
  - `python scripts/check_mojibake.py` — pass
