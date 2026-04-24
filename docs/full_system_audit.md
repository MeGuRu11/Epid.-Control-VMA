# Полный аудит системы Epid Control

Дата аудита: 2026-04-24
Режим: audit-only, без изменения кода приложения, БД, миграций, UI и бизнес-логики.
Источник истины: только локальная директория `C:\Users\user\Desktop\Program\Epid_System_Codex`; GitHub, remote/main и удалённые версии проекта не использовались.

## 1. Краткое резюме

Система находится в рабочем состоянии для дальнейшей разработки с ограничениями. Основные автоматические проверки проходят: архитектурный скрипт, `mypy`, `pytest`, `compileall`, Alembic на отдельной audit-БД, `pip check`, `ruff check app tests` и проверка mojibake. Полный набор тестов собран и выполнен: `359 passed`.

Главные риски:

- незашифрованные backup/export артефакты с персональными и медицинскими данными;
- расширенный lint-контур `ruff check app tests scripts` падает на файлах в `scripts`;
- низкое покрытие ряда критичных UI-потоков при общем покрытии `62%`;
- часть application-сервисов напрямую завязана на SQLAlchemy/infra-модели, хотя документация описывает зависимость через интерфейсы;
- в Import/Export UI остались пользовательские строки с `?` вместо русского текста.

Срочного исправления перед продуктивной эксплуатацией требует шифрование резервных копий и экспортов. Перед активной разработкой также стоит закрыть lint scripts, user-facing mojibake, подтверждения удаления справочников и план декомпозиции крупных UI/сервисных файлов.

## 2. Область аудита

Проверенный локальный путь:

- `C:\Users\user\Desktop\Program\Epid_System_Codex`

Проверенные директории и файлы:

- `app/` — application, domain, infrastructure, UI, startup/bootstrap;
- `tests/` — unit/integration/UI-smoke тесты;
- `app/infrastructure/db/migrations/` — Alembic migrations;
- `scripts/` — quality gates, architecture check, build/support scripts;
- `docs/` — context, tech/user/build docs, historical audit reports, handoff/progress;
- корневые файлы `AGENTS.md`, `README.md`, `DESIGN.md`, `pyproject.toml`, `alembic.ini`, `requirements*.txt`, `EpidControl.spec`.

Не найден top-level каталог `migrations/`; миграции фактически расположены в `app/infrastructure/db/migrations`, что соответствует текущему `alembic.ini`.

Проверки не через локальный проект не выполнялись. GitHub, удалённый `main` и публичные репозитории не использовались.

## 3. Карта системы

Основные entry points:

- `app/main.py` — запуск GUI через `python -m app.main`;
- `app/bootstrap/startup.py` — startup prerequisites, миграции, post-startup операции;
- `app/container.py` — сборка сервисов и контейнера зависимостей;
- `scripts/quality_gates.ps1` — локальный quality gate.

Архитектурные слои:

- `app/ui` — PySide6 Widgets, окна, диалоги, виджеты, presentation orchestration;
- `app/application` — DTO, сервисы, role matrix, use-case логика;
- `app/domain` — доменные модели, constants, rules, type aliases;
- `app/infrastructure` — SQLAlchemy модели, репозитории, Alembic, FTS, reporting, hashing;
- `tests/unit` и `tests/integration` — unit, integration, UI smoke и regression coverage;
- `docs/` — контекст, workflow, user/tech/build guides, исторические отчёты;
- `scripts/` — проверки, build scripts, seed/reference utilities.

Основные функциональные зоны:

- auth/user admin/roles/audit;
- patient + EMR context;
- laboratory samples;
- sanitary samples;
- analytics/reporting;
- Form100 V2;
- import/export packages;
- backups/restore;
- reference catalogs.

## 4. Таблица найденных проблем

| ID | Severity | Область | Файл/строка | Проблема | Риск | Рекомендация |
|----|----------|---------|-------------|----------|------|--------------|
| AUD-001 | High | security/privacy | `app/application/services/backup_service.py:96`, `app/application/services/exchange_service.py:677` | Backup/export создаются без шифрования; в коде есть `TODO SECURITY` про AES-GCM. | Утечка персональных и медицинских данных через `.db`, `.xlsx`, `.zip`, `.csv`, `.pdf` артефакты. | До продуктивной эксплуатации добавить шифрование экспортов/backup, key management, UX предупреждения и tests на encrypted artifacts. |
| AUD-002 | Medium | architecture | `app/application/services/dashboard_service.py:7`, `:9`; `patient_service.py:9`, `:14`; `reference_service.py:10`, `:13` | Application-сервисы напрямую используют SQLAlchemy и infra-модели, хотя docs/AGENTS описывают работу через интерфейсы/протоколы. | Слой application жёстко связан со схемой БД, усложняется тестирование и замена persistence. | Либо обновить архитектурный контракт как сознательное решение, либо постепенно вынести запросы в repositories/query services. |
| AUD-003 | Medium | tooling | `scripts/codex_task.py:8`, `scripts/test_form100_pdf.py:8`, `:91` | `ruff check app tests scripts` падает на `UP035`, `E402`, `I001`, `W293`. | Расширенный quality gate из плана аудита не зелёный; scripts могут деградировать вне основного `ruff check app tests`. | Исправить lint в scripts или явно сузить официальный lint-контур. |
| AUD-004 | Medium | tests/ui | coverage output | Общее покрытие `62%`, но несколько важных UI-файлов имеют 0-17% покрытия. | Регрессии в data-entry и admin/UI потоках могут пройти незамеченными. | Добавить focused UI/service tests для first-run, admin, patient EMK, lab detail, Form100 wizard. |
| AUD-005 | Medium | ui/docs | `app/ui/import_export/import_export_view.py:234`, `:242`, `:245` | В пользовательских строках Import/Export остались `?? ???????...` и `??????????`. | Пользователь видит повреждённый текст ошибок/unknown-state; это снижает эксплуатационную надёжность. | Заменить строки на корректные русские сообщения и добавить regression test на отсутствие `?`-mojibake в UI text. |
| AUD-006 | Medium | ui/reliability | `app/ui/references/reference_view.py:582-606` | Удаление справочников выполняется сразу после нажатия `Удалить`, без `QMessageBox` подтверждения. | Администратор может случайно удалить значимый справочник; последствия зависят от связей и FK policy. | Добавить confirmation dialog с default `No`, названием записи и предупреждением о влиянии на данные. |
| AUD-007 | Medium | performance | `app/application/services/exchange_service.py:668`, `:924`, `:1017`, `:1078` | Экспорт Excel/CSV/PDF/legacy JSON грузит все строки таблиц через `.all()`. | На больших БД возможны долгие синхронные операции, рост памяти и freeze/задержки UI при экспорте. | Ввести chunked export/streaming, progress, лимиты или background worker для больших выгрузок. |
| AUD-008 | Medium | maintainability | line-count audit | В проекте много файлов больше 500 строк: `analytics_view.py` 1519, `theme.py` 1494, `emz_form.py` 1241, `exchange_service.py` 1146 и др. | Рост стоимости ревью, повышенный риск конфликтов и локальных регрессий. | Планово декомпозировать крупные UI и сервисные файлы по уже существующим локальным helper patterns. |
| AUD-009 | Low | docs/tooling | `AGENTS.md:113`, `pyproject.toml:69`; `AGENTS.md:109`, `models_sqlalchemy.py:69+` | Документация говорит `mypy (strict)` и SQLAlchemy `Mapped[]`, но `pyproject.toml` содержит `strict = false`, а модели используют классический `Column(...)`. | Новый разработчик получит неверные ожидания по typing/ORM policy. | Синхронизировать docs с текущей политикой или запланировать отдельную миграцию на strict/Mapped style. |
| AUD-010 | Low | tooling | `git status --short` | Git выводит warning: `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`. | Шум в диагностике git; может мешать автоматизации, но не ломает проект. | Исправить локальные права/путь global git ignore вне проекта. |
| AUD-011 | Info | reliability/ui | проверка не запускалась | Реальный GUI smoke через `python -m app.main` не выполнялся в audit-only режиме. | Автотесты покрывают UI smoke частично, но не заменяют ручной старт/логин/first-run на рабочем desktop. | Выполнить отдельный ручной smoke на безопасной БД после разрешения на интерактивный запуск. |
| AUD-012 | Info | docs/database | структура проекта | Top-level `migrations/` отсутствует; Alembic использует `app/infrastructure/db/migrations`. | Это не дефект, но команды аудита с `migrations` как путём надо адаптировать к фактической структуре. | В документации/чеклистах указывать фактический путь миграций. |

## 5. Архитектура

Проверка `python scripts/check_architecture.py` прошла: `No architectural violations found.`

Подтверждённые сильные стороны:

- `app/ui` не импортирует `app.infrastructure` и не работает напрямую с SQLAlchemy;
- `app/domain` не импортирует PySide6, SQLAlchemy, UI или infrastructure;
- `app/application`, `app/domain`, `app/infrastructure` не импортируют `app.ui`;
- основной UI работает через application-сервисы и DTO.

Ограничение текущей архитектуры: проверочный скрипт не запрещает application -> infrastructure. Фактический код использует concrete SQLAlchemy/infra imports в ряде application-сервисов (`dashboard_service.py`, `patient_service.py`, `reference_service.py`, `exchange_service.py`). Это рабочая архитектура текущего проекта, но она строже связана с persistence, чем описано в AGENTS/tech docs.

Рекомендация: либо явно документировать текущую практику как допустимую, либо постепенно вынести SQLAlchemy query logic из application в repositories/query services.

## 6. Доменная и медицинская логика

Проверенные наблюдения:

- `app/domain/rules/form100_rules_v2.py` валидирует обязательные поля Form100: ФИО, подразделение, диагноз, статусы, bodymap annotations, детали антибиотика/анальгетика.
- DTO для EMR, patient, lab, sanitary используют Pydantic `Field`, `pattern`, `field_validator` и проверяют категории, даты, sex/status-like поля.
- Тесты покрывают негативные сценарии: короткие пароли, actor_id, права, Form100 transitions, payload validation, ZIP hash/path validation, patient delete cascade.
- В ходе аудита не найдено автоматических медицинских заключений или рекомендаций без явной пользовательской записи. Система в основном хранит и валидирует структурированные данные.

Риски:

- пользовательские медицинские данные экспортируются в открытые файлы без шифрования;
- часть UI-валидации и workflow safety зависит от тестового покрытия, которое по критичным UI-файлам остаётся низким;
- без ручного smoke нельзя подтвердить, что все error states и empty states корректны в реальном desktop запуске.

## 7. База данных и миграции

Alembic проверялся только на безопасном локальном data-dir:

```powershell
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\audit-data"
$env:EPIDCONTROL_DB_FILE = "epid-control-audit.db"
```

Результаты:

- `python -m alembic current` — pass;
- `python -m alembic heads` — pass, head `2daa0dea652d`;
- `python -m alembic history` — pass;
- `python -m alembic upgrade head` — pass на audit-БД;
- `python -m alembic check` — pass, `No new upgrade operations detected.`

Модели содержат FK, constraints, `ondelete` и индексы для ключевых таблиц. Важные наблюдения:

- `patients`, `emr_case`, `lab_sample`, `sanitary_sample`, Form100 и дочерние таблицы имеют FK/cascade policies;
- FTS управляется отдельно через `FtsManager` и исключён из обычного `alembic check`;
- top-level `migrations/` отсутствует, фактический путь миграций — `app/infrastructure/db/migrations`.

Рабочая production-like БД не удалялась и не менялась.

## 8. Тесты

Результаты:

- `pytest --collect-only -q` — pass, собрано `359` тестов;
- `pytest -q` — pass, `359 passed`;
- `pytest -q -ra` — pass, `359 passed`;
- `pytest --cov=app --cov-report=term-missing` — pass, `TOTAL 62%`.

Покрытие есть по auth, role matrix, backup ACL, exchange ZIP/import/export, Form100, EMR, patient, lab, sanitary, analytics, startup, UI smoke/helpers.

Основной пробел: низкое покрытие ряда больших UI/data-entry файлов:

- `app/ui/form100_v2/wizard_widgets/form100_main_widget.py` — `0%`;
- `app/ui/admin/user_admin_view.py` — `9%`;
- `app/ui/lab/lab_sample_detail.py` — `9%`;
- `app/ui/patient/patient_emk_view.py` — `10%`;
- `app/ui/first_run_dialog.py` — `10%`;
- `app/ui/references/reference_view.py` — `10%`;
- часть Form100 wizard/bodymap модулей — около `10-17%`.

Skipped/xfail без причины по итогам поиска не выявлены как системная проблема.

## 9. Качество кода

Результаты:

- `ruff check app tests` — pass;
- `ruff check app tests scripts` — fail;
- `mypy app tests` — pass, `Success: no issues found in 285 source files`;
- `python -m compileall -q app tests scripts` — pass;
- `python scripts/check_mojibake.py` — pass.

Подтверждённый lint debt в `scripts`:

- `scripts/codex_task.py:8` — `UP035`;
- `scripts/test_form100_pdf.py:8` — `E402`, `I001`;
- `scripts/test_form100_pdf.py:91` — `W293`.

Крупные файлы требуют плановой декомпозиции. Самые большие:

- `app/ui/analytics/analytics_view.py` — 1519 строк;
- `app/ui/theme.py` — 1494 строки;
- `app/ui/emz/emz_form.py` — 1241 строка;
- `app/ui/sanitary/sanitary_history.py` — 1149 строк;
- `app/application/services/exchange_service.py` — 1146 строк;
- `app/ui/lab/lab_samples_view.py` — 1065 строк;
- `app/ui/sanitary/sanitary_dashboard.py` — 910 строк.

## 10. UI/UX

Сильные стороны:

- UI не обращается напрямую к SQLAlchemy/infrastructure;
- опасные удаления пациента и ЭМЗ имеют `QMessageBox` с default `No`;
- есть empty states и status/error messages во многих views;
- часть долгих операций вынесена в async helper (`run_async`) в patient search/import-export workflows.

Риски:

- `app/ui/import_export/import_export_view.py:234`, `:242`, `:245` содержит повреждённые user-facing строки с `?`;
- удаление справочников в `reference_view.py:582-606` не подтверждается dialog-ом;
- реальные first-run/login/main-window сценарии не запускались вручную в рамках audit-only задачи;
- крупные UI-модули усложняют визуальное ревью и поддержку.

## 11. Безопасность и приватность

Проверки:

- hardcoded production secrets не обнаружены;
- пароли хешируются через `argon2`/`bcrypt` (`app/infrastructure/security/password_hash.py`);
- role/permission checks покрыты тестами для admin/operator flows;
- ZIP import защищён от path traversal и проверяет sha256 manifest;
- DML SQL через пользовательский ввод как f-string не найден; DDL f-string в FTS ограничен внутренними whitelist-identifiers и документирован комментариями.

Главный риск: backup/export артефакты не шифруются. В проекте явно есть `TODO SECURITY` на это место, а экспорт включает поля пациентов (`full_name`, дата рождения и медицинские данные). Это High до продуктивной эксплуатации или передачи файлов вне контролируемого контура.

Дополнительный privacy-риск: `backup_service.py:151-164` пишет путь backup-файла в audit payload. Это не ФИО/паспорт/СНИЛС, но путь может раскрывать структуру локального окружения; риск ниже, чем отсутствие шифрования.

## 12. Надёжность и эксплуатация

Что работает:

- startup/bootstrap имеет проверки prerequisite, миграции и error logging;
- quality gate script выставляет `EPIDCONTROL_DATA_DIR` в `tmp_run\epid-data`;
- Alembic upgrade/check проходит на отдельной audit-БД;
- `pip check` не нашёл конфликтов зависимостей;
- `compileall` проходит.

Что не проверялось:

- интерактивный GUI запуск `python -m app.main`;
- сборка `EXE`/инсталляторов;
- backup/restore руками на production-like БД.

Причина: задача audit-only, без изменения рабочей БД и без интерактивного desktop smoke. Для GUI smoke нужен отдельный разрешённый запуск на временной БД.

## 13. Производительность

Найденные bottlenecks:

- `exchange_service.py` использует `.all()` для полных выгрузок таблиц в Excel/CSV/PDF/JSON;
- ряд UI views заполняет `QTableWidget` через `setRowCount(len(rows))` и item-by-item population;
- большие views и synchronous refresh paths могут стать заметными на крупной SQLite БД.

Сдерживающие факторы:

- repository methods для обычных поисков часто имеют `limit`;
- Form100 list использует `offset/limit`;
- analytics repositories применяют aggregate queries, cache и `limit` для top rows.

Рекомендация: сначала ограничить/chunk export paths, затем добавить progress/background execution для больших пакетов обмена.

## 14. Документация

Актуальные части:

- `README.md` описывает текущий запуск, env-переменные, quality gates, структуру и основные команды;
- `docs/tech_guide.md` фиксирует архитектуру, Alembic data-dir и FTS policy;
- `docs/context.md` описывает состояние продукта и приоритеты;
- `docs/build_release.md` и `docs/manual_regression_scenarios.md` покрывают release/manual regression.

Расхождения:

- `docs/context.md` содержит старые счётчики (`340 passed`, `281 source files`) против текущих `359 passed`, `285 source files`;
- `AGENTS.md` говорит `mypy (strict)`, а `pyproject.toml` содержит `strict = false`;
- `AGENTS.md` описывает SQLAlchemy `Mapped[]`, а текущие модели используют `Column(...)`;
- исторические отчёты в `docs/final_audit_report.md`, `docs/full_audit_report.md`, `docs/code_review_gpt54.md` отражают прошлое состояние и местами содержат уже закрытые проблемы. Они не переписывались.

## 15. Приоритетный план исправлений

### Срочно

1. Добавить шифрование backup/export артефактов и тесты на encrypted outputs.
2. Исправить user-facing `?`-mojibake в `app/ui/import_export/import_export_view.py`.
3. Добавить подтверждение удаления справочников в `ReferenceView`.

### Следующий спринт

1. Исправить `ruff check app tests scripts`.
2. Поднять UI coverage для first-run, admin, patient EMK, lab detail, reference view, Form100 wizard/bodymap.
3. Уточнить архитектурный контракт application -> infrastructure или вынести SQLAlchemy query logic в repositories/query services.
4. Добавить chunked export/progress для больших выгрузок.

### Позже

1. Планово декомпозировать самые крупные UI и service files.
2. Синхронизировать docs с фактическими typing/ORM policies или запланировать переход на strict/Mapped.
3. Провести ручной GUI smoke и packaged smoke на чистом Windows окружении.

## 16. Выполненные команды

| Команда | Результат |
|---------|-----------|
| `pwd` | passed: `C:\Users\user\Desktop\Program\Epid_System_Codex` |
| `python --version` | passed: `Python 3.12.10` |
| `pip --version` | passed: `pip 26.0.1` |
| `Test-Path .venv`, `Test-Path venv` | passed: `.venv=False`, `venv=True` |
| `git status --short` | passed with warning: untracked `.npm-cache/`; warning на global git ignore permission |
| `git branch --show-current` | passed: `main` |
| `Get-ChildItem -Force` | passed |
| `rg ... entry points / PySide6 / SQLAlchemy / Alembic` | passed |
| `python scripts/check_architecture.py` | passed: `No architectural violations found.` |
| `rg ... architecture boundaries` | passed: UI/domain/application leak checks выполнены |
| `rg ... TODO/FIXME/security/domain/db/ui/performance` | passed |
| `python -m alembic current` | passed on audit data-dir |
| `python -m alembic heads` | passed: `2daa0dea652d (head)` |
| `python -m alembic history` | passed |
| `python -m alembic upgrade head` | passed on `tmp_run\audit-data` |
| `python -m alembic check` | passed: no new upgrade operations |
| `pytest -q` | passed: `359 passed` |
| `pytest -q -ra` | passed: `359 passed` |
| `pytest --collect-only -q` | passed: `359 tests collected` |
| `python -c "import pytest_cov; ..."` | passed: `pytest-cov available` |
| `pytest --cov=app --cov-report=term-missing` | passed: `TOTAL 62%` |
| `ruff check app tests` | passed |
| `ruff check app tests scripts` | failed: 4 lint errors in scripts |
| `mypy app tests` | passed: no issues in 285 source files |
| `python -m compileall -q app tests scripts` | passed |
| `python -m pip check` | passed: no broken requirements |
| `python -m pip list` | passed |
| `python -m pip freeze` | passed |
| `python scripts/check_mojibake.py` | passed: `No mojibake detected.` |
| `rg ... requirements*.txt setup.cfg setup.py tox.ini .` | failed: Windows path/glob issue and absent optional files; repeated with explicit `requirements.txt requirements-dev.txt` |
| `rg ... pyproject.toml requirements.txt requirements-dev.txt` | passed |
| `git diff --name-only` перед записью отчёта | passed: tracked changes отсутствовали |

## 17. Невыполненные проверки

- GUI smoke `python -m app.main` — skipped: интерактивный запуск мог открыть first-run/login и создать/изменить audit-БД; для него нужно отдельное разрешение и временный data-dir.
- Packaged build smoke (`scripts\build_exe.bat`, installer scripts) — skipped: задача audit-only, сборка меняет `build/`/`dist/` и требует отдельного времени/среды.
- Ручные backup/restore/import/export операции на production-like SQLite — skipped: нельзя трогать рабочую БД без отдельного разрешения.
- Real-world performance profiling на большой БД — skipped: тестовой large dataset в рамках аудита не создавалось.

## 18. Итоговая оценка готовности

Оценка: готово к дальнейшей разработке условно, с ограничениями.

Основание:

- автоматический базовый контур проекта стабилен: architecture, mypy, pytest, compileall, Alembic, pip check проходят;
- миграции актуальны на безопасной audit-БД;
- критичных сбоев запуска тестов или schema drift не найдено;
- есть High security/privacy риск по незашифрованным backup/export, который нужно закрыть до продуктивной эксплуатации;
- есть Medium technical debt по scripts lint, UI coverage, user-facing mojibake, deletion confirmation, performance export и крупным файлам.

Код приложения в рамках аудита не изменялся.
