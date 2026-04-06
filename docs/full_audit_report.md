# Полный аудит проекта Epid Control

Дата аудита: 2026-04-06

## Шаг 1. Правила проекта
Прочитаны и проверены:
- `AGENTS.md`
- `.agents/skills/epid-control/SKILL.md`
- `docs/context.md`
- `docs/tech_guide.md`
- `docs/progress_report.md`

Итог шага: **Правила изучены, начинаю аудит.**

---

## Шаг 2. Инвентаризация файлов

Проверены корень проекта, отслеживаемые git-файлы (`513`) и локальные неотслеживаемые артефакты.

### 2.А Файлы/папки, которые точно лишние

| Файл/папка | Статус | Причина |
|---|---|---|
| `.mypy_cache/` | удалить | Локальный кэш анализатора, не нужен в репозитории |
| `.ruff_cache/` | удалить | Локальный кэш линтера |
| `venv/` | удалить | Локальное окружение разработки |
| `build/` | удалить | Локальные build-артефакты |
| `tmp/`, `tmp_run/`, `_pytest_tmp/`, `pytest_tmp/`, `pytest_work/` | удалить | Временные каталоги runtime/тестов |
| `pytest_artifacts/`, `pytest-cache-files-*`, `pytest_cache_local/` | удалить | Локальные каталоги кэша/артефактов тестов |
| `.coverage` | удалить | Локальный coverage-файл |
| `pip_install.log` | удалить | Временный лог установки пакетов |

### 2.Б Файлы под вопросом

| Файл | Статус | Причина |
|---|---|---|
| `docs/extracted_3.txt` | под вопросом | Не найдено ссылок/использования в коде; выглядит как промежуточный артефакт |
| `docs/ttz_text.txt` | под вопросом | Большой текстовый дамп из DOCX/XML, прямого использования в коде нет |
| `docs/ttz_docx_text.txt` | под вопросом | Аналогично, технический дамп без явного runtime-назначения |
| `docs/TTZ_Form100_Module_Adapted_v2_2.md` | под вопросом | Похоже на историческое ТЗ; много ссылок на старые пути Form100 |
| `docs/ТТЗ 16.07.2025.docx` | под вопросом | Исходный документ ТЗ; полезность зависит от политики хранения артефактов |
| `docs/Группы антибиотиков.docx` | под вопросом | Сырьевой справочник; в runtime не используется напрямую |
| `docs/Микробные патогены.docx` | под вопросом | Сырьевой справочник; в runtime не используется напрямую |
| `scripts/clear_patients.py` | под вопросом | Утилита админ-очистки, без явных ссылок из CI/доков |
| `scripts/ui_mockups.py` | под вопросом | Демо/макеты UI, не участвует в сборке/тестах |
| `scripts/test_form100_pdf.py` | под вопросом | Ручная утилита; упомянута в документации, но не в CI |

### 2.В Явно нужные файлы

| Файл | Статус | Причина |
|---|---|---|
| `AGENTS.md` | оставить | Главный регламент проекта |
| `.agents/skills/epid-control/SKILL.md` | оставить | Проектный скилл с процедурами |
| `pyproject.toml` | оставить | Центр конфигурации зависимостей/линтера/типов/pytest |
| `scripts/quality_gates.ps1` | оставить | Основной локальный quality-gate пайплайн |
| `.github/workflows/quality-gates.yml` | оставить | CI quality-gates |

---

## Шаг 3. Аудит архитектуры

### 3.1 Нарушения зависимостей слоёв

**UI -> Infrastructure (прямое нарушение):**
- `app/ui/first_run_dialog.py:25` (`from app.infrastructure.db.models_sqlalchemy import User`)
- `app/ui/first_run_dialog.py:26` (`from app.infrastructure.db.session import session_scope`)
- `app/ui/first_run_dialog.py:27` (`from app.infrastructure.security.password_hash import hash_password`)
- `app/ui/widgets/patient_selector.py:16` (`from app.infrastructure.db.repositories.patient_repo import PatientRepository`)
- `app/ui/widgets/patient_selector.py:17` (`from app.infrastructure.db.session import session_scope`)

**UI -> Domain (по правилам AGENTS также нежелательно):**
- `app/ui/analytics/analytics_view.py:34` (`MilitaryCategory`)
- `app/ui/emz/emz_form.py:37` (`MilitaryCategory`)
- `app/ui/patient/patient_edit_dialog.py:23` (`MilitaryCategory`)

### 3.2 Проверка Domain-изоляции

В `app/domain/**` не найдено импортов `PySide6`, `sqlalchemy`, `app.ui`, `app.infrastructure`, `app.application`.

### 3.3 Циклические импорты

Проверка графа импортов по `app/**/*.py`: **циклы не обнаружены** (`CYCLE_COUNT=0`).

### 3.4 Разделение ответственности

Файлы с признаками смешения обязанностей:
- `app/ui/first_run_dialog.py:321-334` — UI напрямую пишет в БД.
- `app/ui/widgets/patient_selector.py:30-31,108-110` — UI создаёт инфраструктурный репозиторий и работает с `session_scope`.
- `app/ui/sanitary/sanitary_history.py:737-792,827-898` — массивная бизнес-валидация и сборка payload в UI.
- `app/ui/form100_v2/form100_editor.py:587-664` — заметная доменная сборка данных в UI.
- `app/ui/lab/lab_sample_detail.py:550-640` — значительная валидация/нормализация данных в UI.

Крупные UI-файлы (риск «god object»):
- `app/ui/analytics/analytics_view.py` (~1439 строк)
- `app/ui/emz/emz_form.py` (~1208 строк)
- `app/ui/theme.py` (~1109 строк)
- `app/ui/sanitary/sanitary_history.py` (~925 строк)
- `app/ui/patient/patient_emk_view.py` (~830 строк)

---

## Шаг 4. Качество кода

Выполнены команды:
- `ruff check app tests --output-format=json` -> `[]` (0 ошибок)
- `mypy app tests` -> `Success: no issues found in 248 source files`
- `pytest -q` -> `233 passed, 2 warnings`
- `python -m compileall -q app tests scripts` -> успешно

### 4.1 Аннотации типов

Найдено функций/методов без полных аннотаций: **86**.

Примеры:
- `app/infrastructure/db/repositories/analytics_repo.py:310` (`search_samples`)
- `app/application/services/patient_service.py:320` (`_repair_database_raw`)
- `app/ui/references/reference_view.py:188` (`resizeEvent`)
- `app/ui/widgets/animated_background.py:79` (`resizeEvent`)
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py:354` (`mousePressEvent`)

### 4.2 Docstring на публичных классах/методах

Найдено пропусков docstring: **916**.

Файлы-лидеры по числу пропусков:
- `app/application/services/reference_service.py` (40)
- `app/infrastructure/db/models_sqlalchemy.py` (37)
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` (20)
- `app/ui/emz/form_widget_factories.py` (19)

Примеры:
- `app/application/dto/auth_dto.py:8` (`class LoginRequest`)
- `app/application/services/analytics_service.py:22` (`class AnalyticsService`)
- `app/application/services/auth_service.py:25` (`login`)
- `app/application/services/reference_service.py:118` (`list_material_types`)

### 4.3 Хардкод путей/URL/секретов

- В runtime-коде критичного хардкода секретов не найдено.
- Обнаружены URL в инсталляторных скриптах:
  - `scripts/installer.iss:15`
  - `scripts/installer.nsi:23`
- В тестах есть тестовый путь-строка `C:/tmp/report.xlsx`:
  - `tests/unit/test_analytics_report_history_helpers.py:29`
  - `tests/unit/test_analytics_report_history_helpers.py:40`

### 4.4 print() вместо logging

`print()` найден в скриптах:
- `scripts/build_reference_seed.py:322`
- `scripts/test_form100_pdf.py:90`
- `scripts/seed_references.py:41`

### 4.5 `# type: ignore` без обоснования

Всего `type: ignore`: **56**, без комментария-обоснования: **56**.

Примеры:
- `app/infrastructure/reporting/form100_pdf_report_v2.py:18`
- `app/infrastructure/db/repositories/form100_repo_v2.py:194`
- `app/ui/emz/emz_form.py:145`
- `app/ui/form100_v2/form100_wizard.py:594`
- `tests/unit/test_user_admin_password_policy.py:32`

### 4.6 TODO/FIXME/HACK

- В `app/tests/scripts` не обнаружено.
- Есть `TODO`-раздел в документации: `docs/context.md:964`.

---

## Шаг 5. Аудит тестов

### 5.1 Покрытие

`pytest --cov=app -q` -> **TOTAL 43%**.

Ключевые зоны недопокрытия:
- `app/main.py` -> `0%`
- `app/ui/first_run_dialog.py` -> `0%`
- `app/ui/emz/emz_edit_dialog.py` -> `0%`
- `app/ui/analytics/analytics_view.py` -> `9%`
- `app/ui/login_dialog.py` -> `11%`
- `app/ui/patient/patient_emk_view.py` -> `10%`

### 5.2 Тесты со слабой проверкой результата

Потенциально «пустые» (нет явного `assert`/проверки состояния):
- `tests/unit/test_form100_v2_rules.py:36` (`test_validate_card_payload_v2_checks_annotations`)
- `tests/unit/test_startup_temp_cleanup.py:54` (`test_noop_when_no_tmp_run`)
- `tests/unit/test_user_admin_password_policy.py:56` (`test_reset_password_accepts_valid_password`)

### 5.3 Изоляция

Явных order-dependent тестов не обнаружено. Найден тест с тестовым «абсолютным» путём в данных:
- `tests/unit/test_analytics_report_history_helpers.py:29,40` (`C:/tmp/report.xlsx`)

### 5.4 Моки vs реальная БД

Нарушение проектного правила про минимизацию моков SQLAlchemy:
- `tests/unit/test_user_admin_password_policy.py` — мокируются `session_factory` и репозитории вместо SQLite in-memory.

### 5.5 Именование тестов

Нарушений формата `test_<что>_<сценарий>` не найдено.

Рекомендации:
- увеличить покрытие сервисов и критичного UI-shell;
- усилить тесты без явной проверки результата;
- заменить моки БД в `test_user_admin_password_policy.py` на интеграционный сценарий с SQLite.

---

## Шаг 6. Аудит БД и миграций

### 6.1 SQLAlchemy-модели

- В `app/infrastructure/db/models_sqlalchemy.py` используется старый стиль `Column(...)`.
- `Mapped[]/mapped_column()` не применяются (несоответствие текущему стандарту AGENTS).
- Модели без `__tablename__` не обнаружены.
- Найден `relationship()` без `back_populates`:
  - `app/infrastructure/db/models_sqlalchemy.py:134`

### 6.2 Alembic

- `alembic heads` -> `0019_form100_v2_schema (head)`
- `alembic current` -> `0019_form100_v2_schema (head)`
- `alembic check` -> **FAILED**

Причина: зафиксирован существенный schema drift (FTS-таблицы, индексы, ограничения, различия имени индекса `ix_form100_emr_case` vs `ix_form100_emr_case_id` и др.).

### 6.3 Raw SQL и параметризация

Потенциально небезопасные f-string в SQL:
- `app/infrastructure/db/fts_manager.py:107`
- `app/infrastructure/db/migrations/versions/0016_fk_cascade.py:25`

Комментарий: сейчас значения выглядят внутренними/контролируемыми, но технически паттерн небезопасный.

---

## Шаг 7. Аудит скиллов `.agents/skills/`

### 7.1 Структурная валидность

- Каталогов скиллов: **45**
- `SKILL.md` отсутствует: **0**
- Битый frontmatter: **0**

### 7.2 Дубли/перекрытия

Перекрывающиеся по назначению пары:
- `difficult-workplace-conversations` и `feedback-mastery`
- `crafting-effective-readmes` и `writing-clearly-and-concisely` (частичное перекрытие)

### 7.3 Релевантность проекту и рекомендация

Рекомендовано **оставить**:
- `epid-control`
- `setup-codex-skills`
- `codex`
- `commit-work`
- `qa-test-planner`
- `c4-architecture`
- `mermaid-diagrams`
- `backend-to-frontend-handoff-docs`
- `frontend-to-backend-requirements`
- `session-handoff`

Рекомендовано **удалить** (непроектные/низкая практическая ценность для данного репозитория):
- `agent-md-refactor`
- `command-creator`
- `crafting-effective-readmes`
- `daily-meeting-update`
- `database-schema-designer`
- `datadog-cli`
- `dependency-updater`
- `design-system-starter`
- `difficult-workplace-conversations`
- `domain-name-brainstormer`
- `draw-io`
- `excalidraw`
- `feedback-mastery`
- `game-changing-features`
- `gemini`
- `gepetto`
- `humanizer`
- `jira`
- `lesson-learned`
- `marp-slide`
- `meme-factory`
- `mui`
- `naming-analyzer`
- `openapi-to-typescript`
- `perplexity`
- `plugin-forge`
- `professional-communication`
- `react-dev`
- `react-useeffect`
- `reducing-entropy`
- `requirements-clarity`
- `ship-learn-next`
- `skill-judge`
- `web-to-markdown`
- `writing-clearly-and-concisely`

### 7.4 `skills-lock.json`

- Файл `skills-lock.json` в корне найден и валиден.
- Несоответствие lock-файла текущему каталогу скиллов:
  - отсутствуют в lock: `epid-control`, `setup-codex-skills`.

---

## Шаг 8. Аудит CI/CD и конфигурации

### 8.1 CI workflow vs локальные quality gates

- `.github/workflows/quality-gates.yml` и `scripts/quality_gates.ps1` в целом синхронизированы по шагам.
- Оба включают `pyright`.

Проблема: это конфликтует с текущим курсом проекта «mypy как единый типизатор».

### 8.2 `pyproject.toml`

Обнаружено:
- `[tool.mypy] strict = false` (конфликт с требованием strict-подхода из AGENTS).
- `ignore_missing_imports = true` снижает строгость типовой проверки.

### 8.3 `requirements.txt` vs `requirements-dev.txt`

- `requirements.txt` согласован с runtime-зависимостями `pyproject.toml`.
- В `requirements-dev.txt` есть extra-пакеты не отражённые в `[project.optional-dependencies.dev]`:
  - `pyright`
  - `pyinstaller`

### 8.4 `.gitignore`

- Настроен корректно: покрыты `venv`, кэши, `*.db`, `build`, `dist`, временные артефакты.

---

## Шаг 9. Аудит документации

### 9.1 Актуальность файлов docs

Проблемы:
- Битые ссылки на отсутствующий файл:
  - `README.md:43` -> `docs/manual_regression_scenarios.md` (файл отсутствует)
  - `docs/build_release.md:67` -> `docs/manual_regression_scenarios.md` (файл отсутствует)
  - `docs/tech_guide.md:58` -> `docs/manual_regression_scenarios.md` (файл отсутствует)
- `docs/context.md` содержит устаревшие тестовые метрики (`217 passed`) и черновые секции.
- `README.md` описывает quality-gates как 4 шага, фактически `quality_gates.ps1` содержит 5 шагов (включая `pyright`).

### 9.2 README

`README.md` в целом релевантен, но содержит:
- битую ссылку на manual regression сценарии;
- рассинхрон описания quality-gates с фактическим скриптом.

### 9.3 Ссылки

Найдено много исторических ссылок в `docs/progress_report.md` на старые Form100-модули (это ожидаемо для журнала, но усложняет навигацию).

---

## Шаг 10. Итоговый отчёт

### КРИТИЧЕСКИЕ ПРОБЛЕМЫ (исправить немедленно)

1. Нарушения архитектуры слоёв (UI -> Infrastructure):
- `app/ui/first_run_dialog.py:25,26,27`
- `app/ui/widgets/patient_selector.py:16,17`

2. Drift схемы БД (`alembic check` падает):
- Несогласованность metadata vs миграции/состояние схемы (FTS/индексы/constraints).

3. Неполное соблюдение стандарта SQLAlchemy 2 в моделях:
- `app/infrastructure/db/models_sqlalchemy.py` не использует `Mapped[]/mapped_column()`.

### ВАЖНЫЕ ПРОБЛЕМЫ (исправить в ближайшее время)

1. Низкое покрытие тестами: `TOTAL 43%`, слабое покрытие критичного UI-shell.
2. Много пропусков качества API кода:
- 86 мест без полных аннотаций.
- 916 пропусков docstring в публичных сущностях.
3. `type: ignore` без обоснования: 56 случаев.
4. Конфликт политики типизации:
- проект декларирует переход на `mypy`, но CI и локальный gate всё ещё гоняют `pyright`.
5. Документация частично устарела:
- битые ссылки,
- устаревшие контрольные цифры,
- рассинхрон README/скриптов.

### РЕКОМЕНДАЦИИ (улучшения)

1. Сначала закрыть архитектурные нарушения UI -> Application/Infrastructure через сервисный фасад.
2. Починить `alembic check` и согласовать модель/миграции (особенно FTS-объекты и индексы).
3. Утвердить единую политику типизации: либо убрать `pyright` из CI/локального gate, либо зафиксировать dual-run официально.
4. Ввести поэтапный план покрытия: приоритет `app/main.py`, auth/startup, ключевые UI-потоки.
5. Ввести обязательное обоснование для каждого `type: ignore`.
6. Очистить документацию: восстановить/заменить отсутствующие ссылки, синхронизировать README и `quality_gates.ps1`.
7. Сократить нерелевантные скиллы в `.agents/skills/` и актуализировать `skills-lock.json`.

### ФАЙЛЫ НА УДАЛЕНИЕ

#### A. Локальные артефакты (вне git)
- `.mypy_cache/`, `.ruff_cache/`, `venv/`, `build/`, `tmp*/`, `pytest*`, `.coverage`, `pip_install.log`

#### B. Кандидаты на удаление из репозитория (после подтверждения владельца)
```bash
git rm docs/extracted_3.txt docs/ttz_text.txt docs/ttz_docx_text.txt
```

Опционально (если решено не хранить исходники ТЗ в репозитории):
```bash
git rm "docs/ТТЗ 16.07.2025.docx" "docs/Группы антибиотиков.docx" "docs/Микробные патогены.docx"
```

### СТАТИСТИКА

- Всего отслеживаемых файлов: **513**
- Всего файлов Python: **263**
- Покрытие тестами: **43%**
- Ошибок ruff: **0**
- Ошибок mypy: **0**
- Тестов всего / прошло / упало: **233 / 233 / 0**

---

## Приложение (сырой аудит)

Для воспроизводимости сохранены артефакты сканирования:
- `tmp_run/audit/missing_annotations.tsv`
- `tmp_run/audit/missing_docstrings.tsv`
- `tmp_run/audit/type_ignore.tsv`
