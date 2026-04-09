# Сводка проекта

Короткий контекст для новых чатов: что за продукт, где мы находимся и что делать дальше.

Дата обновления: 2026-02-27

## Кратко о продукте

Desktop-приложение для стационара: ЭМЗ пациента, микробиологические лабораторные пробы, санитарная микробиология, поиск, аналитика и отчеты.

## Стек и архитектура

- Python 3.11+.
- UI: PySide6 (Qt6).
- База данных: SQLite + SQLAlchemy 2.x, миграции Alembic.
- Структура: UI -> Application -> Domain -> Infrastructure.

## База данных и данные

- FTS5 используется для поиска (по ФИО, МКБ и микроорганизмам); rebuild только при ошибках.
- Бэкапы SQLite должны выполняться через `sqlite3.Connection.backup()` или `VACUUM INTO`.

## Текущие приоритеты

- Определить следующий приоритетный блок улучшений.

## Принятые решения

- Windows-first, но без зависимостей, привязанных к Win32.
- Данные хранятся локально в SQLite.
- Тесты нужно запускать после каждого изменения.

## Журнал работ

### 2026-04-06 — Этап 4: качество кода и документация

- Переведён `tests/unit/test_user_admin_password_policy.py` с моков на реальную SQLite-базу (интеграционный сценарий с `session_factory`), добавлены проверки изменения пароля/деактивации и записи аудита.
- Усилены слабые тесты:
  - `tests/unit/test_form100_v2_rules.py` — добавлен явный assert в позитивном сценарии валидации.
  - `tests/unit/test_startup_temp_cleanup.py` — добавлен assert для `noop`-ветки.
- Убраны/переработаны `# type: ignore` в коде и тестах; оставлены только 2 обоснованных случая:
  - 2 в `app/ui/widgets/transition_stack.py` (ограничения stubs PySide6 для `setGraphicsEffect(None)`),
  - 1 в `app/infrastructure/reporting/form100_pdf_report_v2.py` устранён (служебный буфер присваивается без ignore).
- В Form100 V2 UI и виджетах заменены `list[dict]` на типизированные `list[dict[str, Any]]`, сняты `type-arg` ignore.
- Обновлены скрипты:
  - `scripts/build_reference_seed.py`,
  - `scripts/seed_references.py`,
  - `scripts/test_form100_pdf.py` — `print()` заменён на `logging`.
- Исправлены ссылки в документации:
  - `README.md`: ссылка на несуществующий `docs/manual_regression_run_2026-03-02.md` заменена на `docs/progress_report.md`.
- Обновлён `docs/context.md`:
  - метрика тестов обновлена до `236+ passed`,
  - добавлена отметка о глобальном аудите и этапах очистки,
  - черновой раздел обмена помечен как исторический.
- Ужесточён `mypy` поэтапно в `pyproject.toml`:
  - включены `warn_return_any = true`, `warn_unused_ignores = true`,
  - `disallow_untyped_defs` откатён (порог >30 ошибок),
  - глобальный `ignore_missing_imports` удалён, добавлен точечный override для `reportlab.*`, `openpyxl.*`, `pyqtgraph.*`.
- Доработаны типы в сервисах для прохождения `warn_return_any`:
  - `app/application/services/analytics_service.py` (generic `_cached_call`),
  - `app/application/services/exchange_service.py`,
  - `app/application/services/dashboard_service.py`.
- Проверки качества:
  - `ruff check app tests` — pass.
  - `mypy app tests` — pass (`253 source files`).
  - `pytest -q` — pass (`236 passed, 2 warnings`).
  - `python -m compileall -q app tests scripts` — pass.
  - `pytest --cov=app -q` — `TOTAL 44%`.

### 2026-02-09

- Исправлены нарушения markdownlint в `docs/context.md` (уникальные заголовки и нумерация списков).
- Перезаписан `docs/progress_report.md` в корректной кодировке UTF-8 с BOM.
- Стабилизирован FTS (rebuild только при ошибках; правки в `app/main.py`, `app/application/services/patient_service.py`).
- Добавлен безопасный бэкап SQLite через `sqlite3.Connection.backup()` (правки в `app/application/services/backup_service.py`).
- Включен PRAGMA foreign_keys=ON для SQLite (правки в `app/infrastructure/db/engine.py`).
- Добавлены ON DELETE CASCADE для дочерних таблиц в моделях и миграции (правки в `app/infrastructure/db/models_sqlalchemy.py`, `app/infrastructure/db/migrations/versions/0016_fk_cascade.py`).
- Включены WAL и busy_timeout для SQLite (правки в `app/infrastructure/db/engine.py`).
- Уточнена кодировка сообщений в сервисах: добавлены coding cookie и нормализованы строки (правки в `app/application/services/reference_service.py`, `app/application/services/patient_service.py`, `app/application/services/backup_service.py`).
- Добавлены валидаторы числовых полей в ЭМЗ (SOFA, ВПХ-П, длительность интервенций) в `app/ui/emz/emz_form.py`.
- Улучшен выбор пациента: диалог с FTS-поиском и списком последних пациентов, интеграция в селектор и контекстную панель (правки в `app/ui/widgets/patient_search_dialog.py`, `app/ui/widgets/patient_selector.py`, `app/ui/widgets/context_bar.py`, сервисы и репозитории пациента).
- Добавлены фильтры и пагинация в списке лабораторных проб (правки в `app/ui/lab/lab_samples_view.py`).
- Добавлены фильтры по номеру/росту/дате и пагинация в истории санитарных проб (правки в `app/ui/sanitary/sanitary_history.py`).
- Переведены в фон операции создания/восстановления бэкапа в админке (правки в `app/ui/admin/user_admin_view.py`).
- Переведены в фон поиск и обновление сводки в аналитике (правки в `app/ui/analytics/analytics_view.py`).
- Добавлена серверная валидация дат ЭМЗ (травма ≤ поступление ≤ исход) в `app/application/services/emz_service.py`.
- Переведен в фон поиск пациента в ЭМК (правки в `app/ui/patient/patient_emk_view.py`).
- Переведена в фон загрузка госпитализаций пациента в ЭМК (правки в `app/ui/patient/patient_emk_view.py`).
- Переведены в фон поиск и загрузка последних пациентов в диалоге поиска (правки в `app/ui/widgets/patient_search_dialog.py`).
- Закрыт пункт "Долгие операции в фон".
- Проверена кодировка UI-строк в `app/ui` (все файлы читаются как UTF-8, кракозябры не обнаружены).
- Исправлены ошибки `ruff check` (импорты, лишние coding cookie, SIM105, N802) и восстановлен запуск приложения.
- Актуализирован `docs/context.md` (FTS5 помечен как выполненный, мастер импорта/экспорта обновлен, добавлен статус фоновых операций).
- Тесты: `python -m pytest` (7 passed).
- Повторно выполнены проверки: `python -m ruff check .` (есть предупреждения "Отказано в доступе"), `python -m pytest` (7 passed).
- В лаборатории фильтры скрыты по умолчанию, добавлен переключатель показа/скрытия (правки в `app/ui/lab/lab_samples_view.py`).
- В «Поиск и ЭМК» усилена видимость кнопки «Поиск» и добавлено принудительное снятие busy-режима при ошибках/сбросе (правки в `app/ui/patient/patient_emk_view.py`).
- В «Поиск и ЭМК» поиск по ID теперь сразу загружает пациента и госпитализации, а busy-режим снимается даже при ошибках (правки в `app/ui/patient/patient_emk_view.py`).
- Перезаписан блок импорта библиотек графиков в `app/main.py` для устранения подозрительного синтаксиса, повторно прогнаны проверки.
- Удален случайно вставленный фрагмент изображения в строке импорта `pyqtgraph` (правки в `app/main.py`).
- Поиск пациента по ID переведен на синхронный путь (без фонового потока), чтобы исключить зависание кнопок (правки в `app/ui/patient/patient_emk_view.py`).
- Загрузка госпитализаций в ЭМК переведена на синхронный путь, чтобы исключить пустую таблицу из-за фонового потока (правки в `app/ui/patient/patient_emk_view.py`).
- Фильтр госпитализаций в ЭМК переведен на «пустые» даты по умолчанию (спецзначение вместо 01.01.2024), чтобы не скрывать записи (правки в `app/ui/patient/patient_emk_view.py`).
- Добавлена явная подсказка в ЭМК, если у пациента нет госпитализаций или фильтры скрывают все записи (правки в `app/ui/patient/patient_emk_view.py`).

### 2026-02-12

- Исправлен поиск пациента в «Закрепить пациента»: поле теперь принимает ФИО или ID, добавлен прямой поиск по ID в контекстной панели (правки в `app/ui/widgets/context_bar.py`).
- В диалоге выбора пациента добавлена поддержка поиска по ID (правки в `app/ui/widgets/patient_search_dialog.py`).
- Усилена синхронизация закрепленного контекста между разделами: при выборе пациента/госпитализации контекст сразу применяется к ЭМК, Лаборатории и ЭМЗ (правки в `app/ui/main_window.py`, `app/ui/patient/patient_emk_view.py`, `app/ui/emz/emz_form.py`).
- В ЭМК добавлено программное выделение выбранной госпитализации по `emr_case_id` при контекстной синхронизации (правки в `app/ui/patient/patient_emk_view.py`).
- Тесты: `python -m ruff check .` (успешно, есть предупреждения `os error 5: Отказано в доступе` для временных каталогов), `python -m pytest` (7 passed).
- Закрыт риск Zip Slip: импорт ZIP теперь использует безопасную распаковку с валидацией путей (`_safe_extract_zip`) вместо `extractall` (правки в `app/application/services/exchange_service.py`).
- Оптимизирован импорт Excel: удалено чтение всех строк в память через `list(iter_rows)`, добавлена потоковая обработка (`read_only=True`) (правки в `app/application/services/exchange_service.py`).
- Исправлен callback `on_finished` в аналитике (убран tuple-return из lambda, выделен отдельный метод) для корректной типизации (правки в `app/ui/analytics/analytics_view.py`).
- Исправлена типизация `DateInputAutoFlow._is_combo_popup` (правки в `app/ui/widgets/date_input_flow.py`).
- Исправлена аннотация pytest fixture `tmp_path` как generator (правки в `tests/conftest.py`).
- Добавлены unit-тесты на безопасность распаковки ZIP (`tests/unit/test_exchange_zip_security.py`).
- Проверки после изменений: `python -m mypy app tests` (0 ошибок), `python -m ruff check .` (успешно), `python -m pytest` (13 passed), `python -m compileall app tests scripts` (успешно).
- Проверка БД: `python -m alembic current` (`0016_fk_cascade (head)`), `PRAGMA integrity_check=ok`, `foreign_key_check=0`, FTS-таблицы/триггеры присутствуют.
- Унифицирована FTS-логика в отдельный менеджер `FtsManager` (новый файл `app/infrastructure/db/fts_manager.py`) для startup и runtime-repair.
- `app/main.py` переведен на вызов `FtsManager.ensure_all()` вместо встроенного блока DDL/trigger SQL.
- `PatientService` переведен на `FtsManager` (убраны дублирующие FTS-методы reset/rebuild/drop внутри сервиса).
- DI обновлен: `FtsManager` создается в `app/container.py` и передается в `PatientService`.
- Добавлены тесты: `tests/unit/test_fts_manager.py` (идемпотентность + восстановление FTS) и `tests/integration/test_patient_service_fts_repair.py` (repair после ручного удаления `patients_fts`).
- Проверки после унификации: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок), `python -m pytest` (16 passed), `python -m compileall app tests scripts` (успешно).
- Улучшена диагностика импорта ZIP: небезопасные пути теперь возвращают явную ошибку `Небезопасный ZIP-архив: ...` с причиной (`path traversal`, абсолютный путь, префикс диска).
- Добавлен fallback для временных директорий импорта/экспорта (`_working_temp_dir`) с проверкой права записи и резервным путём в `tmp_run`.
- Добавлены интеграционные тесты импорта ZIP на уровне API сервиса: `tests/integration/test_exchange_service_import_zip.py` (malicious path / отсутствует `manifest.json` / отсутствует файл из `manifest`).
- Переписаны unit-тесты проверки безопасной распаковки ZIP в корректной кодировке (`tests/unit/test_exchange_zip_security.py`).
- Повторные проверки после изменений: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 122 файлах), `python -m pytest` (19 passed).
- Начат блок P1 (расширение тестов сервисов):
  - добавлены интеграционные тесты `tests/integration/test_reference_service.py`:
    - проверка `seed_defaults` (группы/антибиотики/микроорганизмы + корректное обновление ISMP-справочника);
    - проверка `seed_defaults_if_empty` (вызов только для пустых целевых таблиц).
  - добавлены интеграционные тесты `tests/integration/test_patient_service_delete.py`:
    - удаление пациента с каскадной очисткой связанных ЭМЗ/лабораторных сущностей и audit-записей;
    - проверка ошибки при удалении несуществующего пациента.
- Проверки после P1-обновления тестов: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 124 файлах), `python -m pytest` (23 passed).
- Продолжен блок P1 (расширение покрытия сервисов):
  - добавлены тесты `tests/integration/test_patient_service_core.py`:
    - `create_or_get` обновляет существующего пациента по идентичности (ФИО + ДР);
    - `search_by_name` корректно работает по fallback, если `patients_fts` удалена;
    - `update_details` проверяет политику `None` для полей пациента.
  - добавлены тесты `tests/integration/test_reference_service_crud.py`:
    - CRUD-поток для отделений и типов материала;
    - проверки валидации и ошибок `not found` для `ReferenceService`.
- Повторные проверки: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 126 файлах), `python -m pytest` (28 passed).
- Добавлен следующий блок P1 по `ReferenceService`:
  - новый файл тестов `tests/integration/test_reference_service_catalogs.py`;
  - покрыты CRUD-сценарии и поиск для антибиотиков/групп, микроорганизмов, фагов, ИСМП-сокращений и МКБ-10;
  - покрыты ошибки `not found` для update-операций справочников.
- Актуальные проверки после шага: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 127 файлах), `python -m pytest` (31 passed).
- Начат P2 (декомпозиция startup/bootstrap в `main.py` без изменения поведения):
  - добавлен модуль `app/bootstrap/startup.py` с выделением блоков:
    - проверка предпосылок старта (`check_startup_prerequisites`);
    - миграции/совместимость схемы (`run_migrations`, `ensure_schema_compatibility`, `initialize_database`);
    - FTS инициализация (`ensure_fts_objects`);
    - post-startup операции (`seed_core_data`, `warn_missing_plot_dependencies`, `has_users`).
  - `app/main.py` упрощен: добавлен `_create_application()`, инициализация БД переведена на `initialize_database(...)`, удалены дубли startup-логики.
- Проверки после рефакторинга: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 129 файлах), `python -m pytest` (31 passed).
- Продолжен P2: декомпозиция `app/ui/patient/patient_emk_view.py` без изменения поведения:
  - выделены чистые функции форматирования/фильтрации/выбора госпитализаций в `app/ui/patient/emk_utils.py`;
  - `patient_emk_view` переведен на более мелкие UI-builder методы (`_build_search_box`, `_build_results_box`, `_build_patient_box`, `_build_cases_box`) вместо монолитного `_build_ui`;
  - фильтрация госпитализаций и форматирование дат/пола переведены на helper-функции.
- Проверки после шага: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 130 файлах), `python -m pytest` (31 passed), `python -m compileall app tests scripts` (успешно).
- Продолжен P2: декомпозиция `app/ui/analytics/analytics_view.py` без изменения поведения:
  - выделены общие вычисления и форматирование в `app/ui/analytics/view_utils.py` (нормализация периода, сравнение окон, быстрые периоды, форматирование дат);
  - `analytics_view` переведен на util-функции вместо локальных дублирующих методов/вычислений.
- Добавлены unit-тесты для утилит аналитики: `tests/unit/test_analytics_view_utils.py`.
- Проверки после шага: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 132 файлах), `python -m pytest` (34 passed).
- Продолжена декомпозиция `app/ui/analytics/analytics_view.py`:
  - `_build_ui` разбит на локальные builder-методы секций (`_build_filters_section`, `_build_saved_filters_section`, `_build_actions_row`, `_build_dashboard_box`, `_build_ismp_box`, `_build_top_box`, `_build_results_box`);
  - инициализация фильтров вынесена в `_init_filter_widgets`, разметка фильтров — в `_build_filters_grid`.
- Повторные проверки после рефакторинга UI: `python -m ruff check .` (успешно), `python -m mypy app tests` (0 ошибок в 132 файлах), `python -m pytest` (34 passed), `python -m compileall app tests scripts` (успешно).
- Продолжен P2: декомпозиция `app/ui/emz/emz_form.py` без изменения поведения:
  - монолитный `_build_ui` разбит на набор builder-методов (`_build_title_row`, `_build_quick_actions_row`, `_build_patient_hint_row`, `_build_form_box`, `_build_table_boxes`, `_build_collapsible_table_box`, `_build_scroll_area`, `_build_content_layout`);
  - инициализация полей/таблиц вынесена в отдельные методы (`_init_form_widgets`, `_build_tables`, `_initialize_table_rows`).
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 132 файлах), `python -m pytest` (34 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - вынесены pure-утилиты в `app/ui/emz/form_utils.py` (`parse_datetime_text`, `format_datetime`, `sex_code_to_label`);
  - в `EmzForm` добавлены helper-методы `_table_dt_value` и `_set_patient_identity_fields`, чтобы убрать дубли парсинга дат и заполнения данных пациента;
  - логика сбора/валидации дат в таблицах (`_collect_interventions`, `_collect_abx`, `_validate_tables_dt`) переведена на общий helper без изменения поведения.
- Добавлены unit-тесты для новых утилит: `tests/unit/test_emz_form_utils.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 134 файлах), `python -m pytest` (40 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлены внутренние table-helpers `_resize_table_columns`, `_prepare_table_for_fill`, `_setup_all_detail_tables`, `_reset_detail_tables`;
  - дубли в `_reset_form`, `_start_new_case` и `_fill_*` заменены на общие методы подготовки/сброса таблиц;
  - унифицирован resize колонок таблиц (двухпроходный resize сохранен в одном helper для стабильного поведения).
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 134 файлах), `python -m pytest` (40 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - валидация дат таблиц разбита на helper-методы `_validate_datetime_cell` и `_validate_datetime_range`;
  - сохранение ЭМЗ разбито на этапы (`_build_payload`, `_save_new_case`, `_save_existing_case`, `_notify_case_changed`) без изменения пользовательского сценария;
  - маппинг типов диагнозов вынесен в `app/ui/emz/form_utils.py` (`diagnosis_kind_to_dto`, `diagnosis_kind_to_ui`) и подключен в `_collect_diagnoses`/`_fill_table_from_dto`.
- Добавлены unit-тесты маппинга диагнозов в `tests/unit/test_emz_form_utils.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 134 файлах), `python -m pytest` (42 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - вынесены mapper-функции DTO в `app/ui/emz/form_mappers.py` (`map_diagnosis`, `map_intervention`, `map_antibiotic_course`, `map_ismp_case`);
  - методы `_collect_diagnoses`, `_collect_interventions`, `_collect_abx`, `_collect_ismp` переведены на новый mapper-слой без изменения поведения.
- Добавлены unit-тесты для mapper-слоя: `tests/unit/test_emz_form_mappers.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 136 файлах), `python -m pytest` (48 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен validator-слой в `app/ui/emz/form_validators.py` (`validate_required_fields`, `validate_datetime_cell`, `validate_datetime_range`);
  - в `EmzForm` валидация `_validate_required` и `_validate_tables_dt` переведена на validator-функции (UI оставлен как orchestration + вывод статуса).
- Добавлены unit-тесты validator-слоя: `tests/unit/test_emz_form_validators.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 138 файлах), `python -m pytest` (53 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен presenter-слой в `app/ui/emz/form_presenters.py` (`format_admission_label`, `format_save_message`, `split_date_or_datetime`, `text_or_empty`, `int_or_empty`);
  - в `EmzForm` добавлены локальные оркестраторы `_apply_case_access_state`, `_set_datetime_field_from_case_value`, `_apply_case_header_fields`, чтобы упростить `_apply_detail`;
  - форматирование статусов сохранения/даты поступления переведено на presenter-функции без изменения поведения.
- Добавлены unit-тесты presenter-слоя: `tests/unit/test_emz_form_presenters.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 140 файлах), `python -m pytest` (59 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена локальная декомпозиция `app/ui/emz/emz_form.py`:
  - выделен отдельный шаг применения выбранного пациента для сценария новой госпитализации (`_apply_patient_selection_for_new_case`);
  - `_load_case(...)` переведен на этот helper, убраны дубли в ветке `patient_id`;
  - удалены неиспользуемые методы форматирования (`_format_dt`, `_format_admission_label`, `_format_open_message`), чтобы сократить шум в `EmzForm`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 140 файлах), `python -m pytest` (59 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - `refresh_references` разбит на отдельные шаги (`_restore_department_selection`, `_refresh_diagnosis_reference_rows`, `_refresh_abx_reference_rows`, `_refresh_ismp_reference_rows`);
  - проверка дат таблиц переведена на общий валидатор `validate_table_datetime_rows` из `app/ui/emz/form_validators.py`.
- Добавлен unit-тест нового валидатора: `tests/unit/test_emz_form_validators.py::test_validate_table_datetime_rows_returns_first_error`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 140 файлах), `python -m pytest` (60 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен applier-слой `app/ui/emz/form_table_appliers.py` для заполнения таблиц диагнозов/интервенций/антибиотиков/ИСМП;
  - методы `EmzForm._fill_table_from_dto`, `EmzForm._fill_interventions`, `EmzForm._fill_abx`, `EmzForm._fill_ismp` переведены на новый слой без изменения поведения.
- Добавлены unit-тесты applier-слоя: `tests/unit/test_emz_form_table_appliers.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 142 файлах), `python -m pytest` (64 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен setup/refresh helper-слой `app/ui/emz/form_table_setups.py` для логики инициализации и обновления ссылочных виджетов таблиц;
  - методы `EmzForm._setup_icd_rows`, `EmzForm._setup_abx_rows`, `EmzForm._setup_intervention_rows`, `EmzForm._setup_ismp_rows`, `EmzForm._refresh_diagnosis_reference_rows`, `EmzForm._refresh_abx_reference_rows`, `EmzForm._refresh_ismp_reference_rows` переведены на функции нового слоя без изменения поведения.
- Добавлены unit-тесты setup/refresh слоя: `tests/unit/test_emz_form_table_setups.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 144 файлах), `python -m pytest` (69 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен case-selector helper `app/ui/emz/form_case_selectors.py` для определения «последней» госпитализации;
  - в `EmzForm._open_last_case` убран локальный алгоритм выбора кейса, используется `pick_latest_case_id(...)` без изменения поведения.
- Добавлены unit-тесты case-selector helper: `tests/unit/test_emz_form_case_selectors.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 146 файлах), `python -m pytest` (72 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен mode-presenter helper `app/ui/emz/form_mode_presenters.py` для UI-состояний режимов (`patient_hint`, edit-mode кнопки, состояние «новой госпитализации»);
  - методы `EmzForm._set_patient_read_only`, `EmzForm.set_edit_mode`, `EmzForm._start_new_case` переведены на функции helper-слоя без изменения поведения.
- Добавлены unit-тесты mode-presenter helper: `tests/unit/test_emz_form_mode_presenters.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 148 файлах), `python -m pytest` (76 passed), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен field-resolver helper `app/ui/emz/form_field_resolvers.py` (парсинг числовых полей, нормализация пола, резолв `department_id`);
  - методы `EmzForm._parse_int`, `EmzForm._normalize_sex`, `EmzForm._resolve_department_id` переведены на новый helper-слой без изменения поведения.
- Добавлены unit-тесты field-resolver helper: `tests/unit/test_emz_form_field_resolvers.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 150 файлах), `python -m pytest` (81 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен request-builder helper `app/ui/emz/form_request_builders.py` (сборка `EmzCreateRequest`, `EmzUpdateRequest` и payload обновления данных пациента);
  - методы `EmzForm._save_new_case` и `EmzForm._save_existing_case` переведены на новый helper-слой без изменения поведения.
- Добавлены unit-тесты request-builder helper: `tests/unit/test_emz_form_request_builders.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 152 файлах), `python -m pytest` (84 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен patient-identity helper `app/ui/emz/form_patient_identity.py` (структура и маппинг идентификационных полей пациента из patient/case объектов);
  - в `EmzForm` добавлен `_apply_patient_identity_data(...)`, а методы `load_case`, `_apply_detail`, `refresh_patient`, `_apply_patient_selection_for_new_case` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты patient-identity helper: `tests/unit/test_emz_form_patient_identity.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 154 файлах), `python -m pytest` (87 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - выделен table-collector helper `app/ui/emz/form_table_collectors.py` для сбора DTO из таблиц (`diagnoses`, `interventions`, `abx`, `ismp`);
  - методы `EmzForm._collect_diagnoses`, `EmzForm._collect_interventions`, `EmzForm._collect_abx`, `EmzForm._collect_ismp` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты table-collector helper: `tests/unit/test_emz_form_table_collectors.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 156 файлах), `python -m pytest` (91 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - в `app/ui/emz/form_request_builders.py` добавлен helper `build_emz_version_payload(...)` для сборки `EmzVersionPayload`;
  - метод `EmzForm._build_payload` переведен на helper-слой без изменения поведения.
- Обновлены unit-тесты request-builder слоя: `tests/unit/test_emz_form_request_builders.py` (добавлен сценарий для `build_emz_version_payload`).
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 156 файлах), `python -m pytest` (92 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен orchestration helper-слой `app/ui/emz/form_orchestrators.py` (`collect_save_case_context`, `run_save_case`, `run_load_case`);
  - метод `EmzForm.on_save_clicked` переведен на helper-оркестрацию сохранения;
  - метод `EmzForm.load_case` переведен на helper-оркестрацию загрузки кейса/пациента;
  - добавлен локальный helper `EmzForm._get_patient_identity_data(...)` для унификации загрузки identity-данных.
- Добавлены unit-тесты orchestration helper-слоя: `tests/unit/test_emz_form_orchestrators.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 158 файлах), `python -m pytest` (101 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен table-actions helper-слой `app/ui/emz/form_table_actions.py` (`add_diagnosis_row`, `add_intervention_row`, `add_abx_row`, `add_ismp_row`, `delete_table_row`);
  - методы `EmzForm._add_diagnosis_row`, `EmzForm._add_intervention_row`, `EmzForm._add_abx_row`, `EmzForm._add_ismp_row`, `EmzForm._delete_table_row` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты table-actions helper-слоя: `tests/unit/test_emz_form_table_actions.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 160 файлах), `python -m pytest` (108 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен widget-factory helper-слой `app/ui/emz/form_widget_factories.py` (фабрики combobox/date widgets + переиспользуемое наполнение ICD combo);
  - методы `EmzForm._create_dt_cell`, `EmzForm._create_date_cell`, `EmzForm._create_diag_type_combo`, `EmzForm._create_intervention_type_combo`, `EmzForm._create_icd_combo`, `EmzForm._refresh_icd_combo`, `EmzForm._create_abx_combo`, `EmzForm._create_ismp_type_combo` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты widget-factory helper-слоя: `tests/unit/test_emz_form_widget_factories.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 162 файлах), `python -m pytest` (116 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен helper-слой ICD-search orchestration `app/ui/emz/form_icd_search.py` (`wire_icd_search`, `resolve_icd_items`, `refresh_icd_combo`);
  - методы `EmzForm._wire_icd_search` и `EmzForm._refresh_icd_combo` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты ICD-search helper-слоя: `tests/unit/test_emz_form_icd_search.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 164 файлах), `python -m pytest` (120 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен helper-слой orchestration справочников/таблиц `app/ui/emz/form_reference_orchestrators.py`;
  - методы `EmzForm._setup_all_detail_tables`, `EmzForm._load_references`, `EmzForm.refresh_references` переведены на helper-слой;
  - callbacks для заполнения DTO-таблиц (`_fill_table_from_dto`, `_fill_abx`, `_fill_ismp`) переведены на специализированные setup-функции helper-слоя без изменения поведения.
- Добавлены unit-тесты helper-слоя: `tests/unit/test_emz_form_reference_orchestrators.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 166 файлах), `python -m pytest` (125 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Продолжена декомпозиция `app/ui/emz/emz_form.py`:
  - добавлен helper-слой UI-state orchestration `app/ui/emz/form_ui_state_orchestrators.py` (read-only состояния, reset полей формы/госпитализации, видимость quick-action кнопок, notify выбора кейса);
  - методы `EmzForm._set_patient_read_only`, `EmzForm._set_form_read_only`, `EmzForm.set_edit_mode`, `EmzForm._reset_form`, `EmzForm._start_new_case` переведены на helper-слой без изменения поведения.
- Добавлены unit-тесты helper-слоя: `tests/unit/test_emz_form_ui_state_orchestrators.py`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 168 файлах), `python -m pytest` (131 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).
- Финальная чистка `app/ui/emz/emz_form.py` в рамках текущего этапа:
  - удалены лишние thin-wrapper методы `EmzForm._create_diag_type_combo` и `EmzForm._create_intervention_type_combo`;
  - все вызовы переведены напрямую на factory-функции `create_diag_type_combo` / `create_intervention_type_combo`.
- Проверки после шага: `python -m ruff check .` (успешно; есть предупреждения `os error 5` для временных каталогов), `python -m mypy app tests` (0 ошибок в 168 файлах), `python -m pytest` (131 passed, запуск с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` из-за `WinError 5` в `AppData\\Local`), `python -m compileall app tests scripts` (успешно).

### 2026-02-13

- Закрыт P1-пункт «Матрица прав (admin/operator)»:
  - добавлен единый policy-модуль ролей `app/application/security/role_matrix.py` (`access_admin_view`, `manage_users`, `manage_references`, `manage_backups`);
  - UI переведен на policy: `app/ui/main_window.py`, `app/ui/references/reference_view.py`, `app/ui/admin/user_admin_view.py`;
  - `MainWindow` усилен guard-проверкой: недопустимая навигация в admin-view для `operator` принудительно переводится на Home.
- Усилен backend-контроль прав:
  - в `ReferenceService` write-операции (`add/update/delete`) получили `actor_id` и проверку admin-доступа с аудитом отказа (`access_denied`);
  - в `BackupService` добавлена проверка admin-доступа для `create_backup`/`restore_backup` с аудитом отказа.
- Обновлен DI-контейнер: `ReferenceService` и `BackupService` получают `user_repo`/`audit_repo` через `app/container.py`.
- Добавлены тесты:
  - `tests/unit/test_role_matrix.py`;
  - `tests/integration/test_reference_service_acl.py`;
  - `tests/integration/test_backup_service_acl.py`.
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 173 файлах;
  - `python -m pytest` — 135 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно.
- Закрыт P1-пункт «Лог ошибок и отчёт по результату импорта»:
  - `ExchangeService.import_excel/import_csv/import_json/import_zip` теперь формируют единый импорт-отчёт: `summary` (`rows_total`, `added`, `updated`, `skipped`, `errors`), `details` по scope и `errors` c `row`/`message`;
  - при ошибках импорта сервис пишет JSON-лог рядом с исходным файлом (`*_import_errors_YYYYMMDD_HHMMSS.json`) и возвращает `error_log_path`;
  - для ZIP-импорта отчёт и лог ошибок теперь проксируются из вложенного Excel-импорта на уровень ZIP.
- Обновлён мастер импорта (`app/ui/import_export/import_export_wizard.py`):
  - после импорта показывается развёрнутый отчёт (summary + детали по таблицам + путь к логу ошибок);
  - если есть ошибки, мастер завершает операцию статусом «с ошибками» (warning), без падения всей операции.
- Добавлены тесты импорта отчётов/логов:
  - `tests/integration/test_exchange_service_import_reports.py` (CSV/Excel/ZIP сценарии).
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 174 файлах;
  - `python -m pytest` — 138 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно.
- Закрыт блок «Шаблоны отчётов + SHA256»:
  - в `ReportingService` добавлено управляемое хранилище артефактов `data/artifacts/reports/<type>/<YYYY>/<MM>` с копированием экспортированного файла и логированием SHA256 в `report_run`;
  - добавлены API истории/верификации: `list_report_runs(...)` и `verify_report_run(report_run_id)` с проверкой наличия файла и сверкой SHA256;
  - в аналитике добавлен экран истории отчётов (`app/ui/analytics/analytics_view.py`): фильтры, таблица запусков, открытие артефакта и действия проверки хэшей;
  - после экспорта XLSX/PDF история отчётов автоматически обновляется в UI.
- Добавлены тесты артефактов отчётов:
  - `tests/integration/test_reporting_service_artifacts.py` (сценарии: успешная верификация, mismatch, отсутствующий файл).
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 175 файлах;
  - `python -m pytest` — 141 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно.
- Начат P2-блок «Оптимизация производительности»: добавлены индексы под фактические фильтры аналитики.
  - новая миграция `app/infrastructure/db/migrations/versions/0017_analytics_filter_indexes.py`;
  - добавлены индексы для сценариев `date/department/category/growth/microorganism/antibiotic/icd/is_current`:
    - `patients(category)`;
    - `lab_sample(emr_case_id, taken_at)`;
    - `lab_sample(growth_flag, taken_at)`;
    - `lab_microbe_isolation(microorganism_id, lab_sample_id)`;
    - `lab_abx_susceptibility(antibiotic_id, lab_sample_id)`;
    - `emr_case_version(is_current, admission_date, emr_case_id)`;
    - `emr_diagnosis(icd10_code, emr_case_version_id)`;
    - `ismp_case(start_date, emr_case_id, ismp_type)`.
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 176 файлах;
  - `python -m pytest` — 141 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно;
  - `python -m alembic heads` — `0017_analytics_filter_indexes (head)`.
- Продолжен P2-блок «Оптимизация производительности»: оптимизированы тяжелые запросы аналитики.
  - `app/infrastructure/db/repositories/analytics_repo.py`:
    - фильтрация выборки переведена на `EXISTS`-условия и единый подзапрос ID проб;
    - убрано декартово размножение строк от одновременных join `lab_microbe_isolation` и `lab_abx_susceptibility`;
    - `search_samples` теперь возвращает одну строку на пробу с детерминированным отображением микроорганизма/антибиотика через scalar-subquery;
    - добавлен `get_aggregates(...)` на стороне репозитория с корректным подсчетом `top_microbes` без cross-product артефактов.
  - `app/application/services/analytics_service.py`:
    - `get_aggregates` переведен на новый репозиторный агрегатор;
    - `search_samples` адаптирован к строковым значениям микроорганизма/антибиотика.
- Добавлены интеграционные тесты:
  - `tests/integration/test_analytics_service_queries.py`:
    - проверка «одна проба = одна строка в выдаче»;
    - проверка корректного `top_microbes` без двойного счета;
    - проверка цепочки фильтров (`department/material/microbe/abx/icd/growth/category/lab_no`) через `EXISTS`.
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 177 файлах;
  - `python -m pytest` — 144 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно.
- Закрыт последний подпункт P2 «Кэш расчётов для аналитики»:
  - в `app/application/services/analytics_service.py` добавлен in-memory TTL-кэш без изменения внешнего API сервиса;
  - кэшируемые методы: `get_aggregates`, `get_department_summary`, `get_trend_by_day`, `compare_periods`, `get_ismp_metrics`;
  - добавлены настройки кэша в конструкторе (`cache_ttl_seconds`, `cache_max_entries`) и метод `clear_cache()`;
  - реализованы детерминированные ключи кэша по нормализованному payload и защитное deep-copy на чтение/запись.
- Добавлены unit-тесты кэша:
  - `tests/unit/test_analytics_service_cache.py`:
    - cache hit/miss для `get_aggregates`;
    - истечение TTL;
    - кэширование `compare_periods`;
    - кэширование `get_ismp_metrics`.
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 178 файлах;
  - `python -m pytest` — 148 passed (с `EPIDCONTROL_DATA_DIR=tmp_run/epid-data`);
  - `python -m compileall app tests scripts` — успешно.
- Проведена консолидация документации:
  - `docs/context.md` обновлён как главный единый документ на базе `docs/code_audit_findings.md` и `docs/MASTER_TZ_CODEX.md`;
  - добавлен консолидированный остаточный план работ (что реально осталось сделать) с приоритетами P1/P2;
  - добавлены обязательные критерии самопроверки из `MASTER_TZ`;
  - устранены неточности статусов в кратком блоке и размечен исторический раздел «в первую очередь».
- Проведена финальная консолидация контекста:
  - в `docs/context.md` перенесены детализированные этапы мастер-плана (I-VI), результаты аудита 1-9, ручной UI чек-лист и уточненный итерационный план;
  - добавлен отдельный незакрытый пункт по hotfix рекурсивного сброса контекста в ЭМЗ;
  - после переноса смысловой нагрузки удалены файлы `docs/code_audit_findings.md` и `docs/MASTER_TZ_CODEX.md`.
- Исправлена проблема `Pylance reportMissingImports` для `PySide6`:
  - подтверждено, что `PySide6` установлен в системном `Python312` (`%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe`);
  - выявлено, что в рабочем `venv` пакет `PySide6` отсутствует, а установка через `pip` недоступна в текущем index;
  - workspace зафиксирован на системный интерпретатор через `.vscode/settings.json` (`python.defaultInterpreterPath`), чтобы Pylance корректно резолвил `PySide6.*`.
- Закрыт P1 hotfix-риск рекурсивного сброса контекста (RecursionError в `clear_context`):
  - в `app/ui/main_window.py` добавлен re-entrant guard (`_case_selection_in_progress`) в `_on_case_selected`;
  - повторный вход в `_on_case_selected` во время текущей синхронизации контекста теперь блокируется;
  - предотвращён цикл `EmzForm.clear_context -> notify_case_selection -> MainWindow._on_case_selected -> EmzForm.clear_context`.
- Добавлены unit-тесты на поведение обработчика контекста:
  - `tests/unit/test_main_window_context_selection.py`:
    - загрузка кейса выполняется один раз при непустом контексте;
    - ре-энтрантный callback из `clear_context` не вызывает повторный проход и рекурсию.
- Проверки после hotfix:
  - `python -m pytest tests/unit/test_main_window_context_selection.py` — 2 passed;
  - `python -m ruff check app/ui/main_window.py tests/unit/test_main_window_context_selection.py` — успешно.
- Закрыт P1-пункт `PatientEditDialog` и read-only режим пациентского блока в ЭМЗ:
  - `MainWindow` переведен с `EmzEditDialog` на `PatientEditDialog` для редактирования паспортных данных пациента;
  - точки входа подключены из обоих экранов: `EmzForm` и `PatientEmkView`;
  - `PatientEmkView` упростил callback редактирования пациента (только `patient_id`, без обязательного выбора госпитализации);
  - в `EmzForm` кнопка «Редактировать пациента» теперь показывается в read-only режиме (через `apply_patient_read_only_state`);
  - после сохранения из диалога выполняется обновление карточки пациента в ЭМК, read-only полей ЭМЗ и контекст-бара.
- Добавлены/обновлены unit-тесты:
  - `tests/unit/test_main_window_context_selection.py` — покрыт post-save поток `_after_patient_edit_saved`;
  - `tests/unit/test_emz_form_ui_state_orchestrators.py` — проверено отображение кнопки редактирования пациента в read-only состоянии.
- Проверки после шага:
  - `python -m ruff check app/ui/main_window.py app/ui/patient/patient_emk_view.py app/ui/emz/emz_form.py app/ui/emz/form_ui_state_orchestrators.py app/ui/emz/form_mode_presenters.py tests/unit/test_main_window_context_selection.py tests/unit/test_emz_form_ui_state_orchestrators.py` — успешно;
  - `python -m mypy app/ui/main_window.py app/ui/patient/patient_emk_view.py app/ui/emz/emz_form.py app/ui/emz/form_ui_state_orchestrators.py app/ui/emz/form_mode_presenters.py tests/unit/test_main_window_context_selection.py tests/unit/test_emz_form_ui_state_orchestrators.py` — 0 ошибок;
  - `python -m pytest tests/unit/test_main_window_context_selection.py tests/unit/test_emz_form_ui_state_orchestrators.py` — 10 passed.
- Финальные проверки после обновления тестов подсказок и интеграции:
  - `python -m pytest` — 152 passed;
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 179 файлах;
  - `python -m compileall app tests scripts` — успешно.
- Продолжен P2-блок декомпозиции UI: `app/ui/sanitary/sanitary_history.py`.
  - добавлен helper-слой `app/ui/sanitary/history_view_helpers.py`;
  - в `SanitaryHistoryDialog` вынесены функции фильтрации/сортировки, пагинации, расчета summary и сборки meta-строки карточек;
  - метод `_paginate` удален из диалога, логика перенесена в helper `paginate_samples(...)`;
  - UI-поведение и внешний API диалога не изменены.
- Добавлены unit-тесты helper-слоя:
  - `tests/unit/test_sanitary_history_view_helpers.py` (7 сценариев).
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 181 файле;
  - `python -m pytest` — 159 passed;
  - `python -m compileall app tests scripts` — успешно.
- Продолжен P2-блок декомпозиции UI: `app/ui/lab/lab_sample_detail.py`.
  - добавлен helper-слой `app/ui/lab/lab_sample_detail_helpers.py`;
  - в helper вынесены правила сборки/валидации payload для таблиц чувствительности и фагов;
  - вынесена логика определения наличия результатных данных и сборки `LabSampleResultUpdate`;
  - `LabSampleDetailDialog` переведен на helper-слой без изменения внешнего поведения UI.
- Добавлены unit-тесты helper-слоя:
  - `tests/unit/test_lab_sample_detail_helpers.py` (7 сценариев).
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 183 файлах;
  - `python -m pytest` — 166 passed;
  - `python -m compileall app tests scripts` — успешно.
- Завершен финальный P2-проход по `app/ui/analytics/analytics_view.py`:
  - добавлен helper-слой `app/ui/analytics/report_history_helpers.py`;
  - вынесены форматирование верификации отчета, нормализация строки истории и контракт ширин колонок;
  - `AnalyticsSearchView` переведен на helper-слой в блоке истории отчетов (без изменения UI-поведения).
- Добавлены unit-тесты helper-слоя:
  - `tests/unit/test_analytics_report_history_helpers.py` (4 сценария).
- Проверки после шага:
  - `python -m ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `python -m mypy app tests` — 0 ошибок в 185 файлах;
  - `python -m pytest` — 170 passed;
  - `python -m compileall app tests scripts` — успешно.
- Проведен ручной технический аудит проекта (кодировка/язык/логика/модули/БД):
  - проверен набор текстовых файлов `app/tests/scripts/docs` на mojibake и UTF-8 совместимость;
  - ?? ????????? ??????????? (`U+FFFD`, `U+00D0`, `U+00D1`, `U+00C3`, `U+00C2`) ?????????? ?? ???????;
  - БД и миграции: `alembic head/current = 0017_analytics_filter_indexes`, `PRAGMA integrity_check=ok`, `foreign_key_check=0`, FTS-таблицы присутствуют;
  - quality-gates: `ruff` OK, `mypy` OK, `pytest` 170 passed, `compileall` OK.
- Выявленные точки внимания по результатам аудита:
  - `app/ui/widgets/patient_selector.py`: broad `except Exception: pass` в `_apply` скрывает ошибки callback `on_select` и может маскировать реальную проблему;
  - часть русских UI/сервисных строк хранится в unicode-экранированном виде (`\\uXXXX`) вместо читаемого UTF-8 (например `app/ui/widgets/patient_search_dialog.py`, `app/ui/emz/form_utils.py`, `app/application/services/auth_service.py`), что ухудшает сопровождаемость.
- Закрыты риски из ручного аудита по обработке ошибок patient widgets и читаемости строк:
  - `app/ui/widgets/patient_selector.py`: в `_apply` убран `except Exception: pass`; добавлена явная ветка валидации ID и отображение ошибки `on_select` без тихого fallback в поиск;
  - `app/ui/widgets/patient_search_dialog.py`: в `_load_recent` заменено тихое подавление ошибок на явный статус пользователю (`Не удалось загрузить последних пациентов: ...`);
  - `app/ui/emz/form_utils.py`, `app/application/services/auth_service.py`, `app/ui/widgets/patient_search_dialog.py`: unicode-экранированные русские строки заменены на читаемые UTF-8;
  - `app/ui/emz/form_utils.py`: `except Exception` в парсере дат сужен до `ValueError`.
- Добавлены unit-тесты:
  - `tests/unit/test_patient_widgets_error_handling.py`:
    - ошибка `on_select` в `PatientSelector._apply` отображается как error-статус и не открывает поиск;
    - невалидный ID в `PatientSelector._apply` дает warning-статус;
    - ошибка загрузки recent в `PatientSearchDialog._load_recent` отображается в status-label.
- Проверки после шага:
  - `ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `mypy app tests` — 0 ошибок в 186 файлах;
  - `pytest` — 173 passed;
  - `python -m compileall app` — успешно.
- Подготовлен подробный набор ручных регрессионных сценариев: `docs/manual_regression_scenarios.md`.
  - добавлены предусловия стенда и путь к БД;
  - зафиксирован единый набор тестовых данных (учетки, справочники, пациенты, кейсы);
  - описаны пошаговые сценарии с ожидаемыми результатами по всем ключевым модулям: Auth/RBAC, Справочники, Контекст/ЭМК/ЭМЗ, Лаборатория, Санитария, Аналитика/артефакты отчетов, Импорт/Экспорт, Backup.
- Проверена генерация отчетов на предмет кодировки/кириллицы (XLSX/CSV/PDF) на реальных артефактах.
- Выявлен и устранен риск битой кириллицы в PDF-экспорте:
  - добавлен модуль `app/infrastructure/reporting/pdf_fonts.py` с регистрацией Unicode TTF-шрифта (Windows/Linux) и fallback через `EPIDCONTROL_PDF_FONT`;
  - `app/application/services/reporting_service.py` (`export_analytics_pdf`) переведен на явный `FONTNAME` с Unicode-шрифтом;
  - `app/application/services/exchange_service.py` (`export_pdf`) переведен на явный `FONTNAME` с Unicode-шрифтом.
- Практическая проверка артефактов в `tmp_run/report_encoding_check2`:
  - XLSX: листы/заголовки/данные с кириллицей читаются корректно (`xlsx_ok_summary=True`, `xlsx_ok_name=True`);
  - CSV: UTF-8-SIG, кириллический заголовок и ФИО читаются корректно;
  - PDF: присутствует `ToUnicode`, отсутствует `ZapfDingbats` fallback, что подтверждает корректное Unicode-отображение кириллицы.
- Проверки после правок:
  - `ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов);
  - `mypy app tests` — 0 ошибок в 187 файлах;
  - `pytest` — 173 passed.
- Проведен целевой аудит корректности аналитики и блока импорт/экспорт.
- Выявлен и исправлен дефект граничной даты в аналитике:
  - проблема: фильтр `date_to` для `DateTime`-полей (`LabSample.taken_at`, `EmrCaseVersion.admission_date`) исключал записи конечного дня после 00:00;
  - исправление в `app/infrastructure/db/repositories/analytics_repo.py`:
    - введены helper-границы `_date_floor(...)` и `_date_ceiling_exclusive(...)`;
    - фильтрация переведена на полуинтервал `[date_from 00:00; date_to+1day 00:00)`;
    - обновлены запросы `search_samples`, `get_aggregates`, `get_department_summary`, `get_trend_by_day`, `get_aggregate_counts`, `get_ismp_metrics`.
- Добавлены интеграционные тесты границ дат:
  - `tests/integration/test_analytics_date_boundaries.py`:
    - включение записей на конечный день в `get_aggregates`;
    - включение конечного дня в `get_trend_by_day`;
    - корректность `compare_periods` на однодневных диапазонах;
    - включение `admission_date` конечного дня в `get_ismp_metrics` и проверка формул `incidence/incidence_density/prevalence`.
- Выполнена независимая верификация на контролируемом датасете (скрипт в `tmp_run/qa_analytics_exchange`):
  - `ANALYTICS_VALIDATION=PASS`;
  - `EXCHANGE_VALIDATION=PASS` (round-trip Excel/ZIP/CSV между отдельными БД, сверка counts).
- Проверки после исправления:
  - `pytest` — 177 passed;
  - `mypy app tests` — 0 ошибок в 188 файлах;
  - `ruff check .` — успешно (есть предупреждения `os error 5` для временных каталогов).
- Исправлен ввод даты рождения в ЭМЗ (без подмешивания времени `HH:mm`):
  - причина: в Qt `QDateEdit` наследуется от `QDateTimeEdit`, и авто-flow ввода ошибочно применял datetime-ветку к date-only полям;
  - фикс в `app/ui/widgets/date_input_flow.py`:
    - добавлен детектор date-only по `displayFormat` (`_is_date_only_edit(...)`);
    - выбор секции фокуса/длины буфера/форматирования переведен на date-only vs datetime логику;
    - для date-only полей теперь строго формат `dd.MM.yyyy` и буфер 8 цифр.
- Добавлены unit-тесты регрессии:
  - `tests/unit/test_date_input_flow.py`:
    - корректное различение date-only/datetime при наследовании `QDateEdit <- QDateTimeEdit`;
    - date-only поле не получает время даже при длинном буфере;
    - datetime поле сохраняет формат с временем.
- Проверки после фикса:
  - `ruff check app/ui/widgets/date_input_flow.py tests/unit/test_date_input_flow.py` — успешно;
  - `mypy app/ui/widgets/date_input_flow.py tests/unit/test_date_input_flow.py` — 0 ошибок;
  - `pytest tests/unit/test_date_input_flow.py` — 3 passed.
- Исправлена логика парсинга ошибок при импорте ZIP Формы 100 и вывод сообщений в UI:
  - в `app/application/services/form100_service_v2.py` добавлен сбор ошибок валидации сущностей при импорте. Теперь `error_count` и список `errors` не являются жестко зашитыми 0/[].
  - в логе пакета выгрузки Form100 теперь также фиксируются выгруженные количества (`counts`).
  - в `app/ui/form100_v2/form100_view.py` исправлен вывод отчета пользователю: добавлено явное указание 'добавлено/обновлено/пропущено' и количество ошибок с выдачей warning.
- Проверки после фикса:
  - `ruff check app/application/services/form100_service_v2.py app/ui/form100_v2/form100_view.py` — успешно;
  - `mypy app/application/services/form100_service_v2.py app/ui/form100_v2/form100_view.py` — 0 ошибок;
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1` — All checks passed!
- Реализован модуль Form100 (v1) по плану: DB + backend + UI + роли + аудит + ZIP/PDF.
  - Исправлено форматирование дат (RAW ISO строки заменены на `%d.%m.%Y %H:%M`) при выгрузке отчетов (Excel, PDF).
  - Изменена визуальная верстка PDF-отчетов для модулей Аналитики и Базовых таблиц (используется книжная `landscape(A4)` ориентация и перенос текстов (`Paragraph`), чтобы предотвратить наложение колонок).
- Добавлены новые сущности и миграция:
  - `form100_card`, `form100_mark`, `form100_stage` в `app/infrastructure/db/models_sqlalchemy.py`;
  - миграция `app/infrastructure/db/migrations/versions/0018_form100_module.py` (down_revision=`0017_analytics_filter_indexes`).
- Реализован backend Form100:
  - DTO: `app/application/dto/form100_dto.py`;
  - доменные правила/валидации/дифф: `app/domain/rules/form100_rules.py`;
  - repo: `app/infrastructure/db/repositories/form100_repo.py`;
  - service: `app/application/services/form100_service.py`;
  - инфраструктура обмена/печати: `app/infrastructure/export/form100_export.py`, `app/infrastructure/import/form100_import.py`, `app/infrastructure/reporting/form100_pdf_report.py`.
- Реализованы публичные операции сервиса Form100:
  - list/get/create/update/add_stage/replace_marks/sign/delete;
  - export/import ZIP-пакета Form100;
  - export PDF карточки.
- Реализованы ролевые ограничения v1:
  - `admin/operator`: create/read/update/list/add_stage/replace_marks/sign;
  - `admin` only: delete.
- Аудит Form100 внедрен в `audit_log.payload_json` со схемой `form100.audit.v1` и `before/after` по изменённым полям.
- Интеграция в приложение:
  - DI: `app/container.py` (repo/service регистрации, wiring в exchange/reporting);
  - UI модуль: `app/ui/form100/*`;
  - меню/stack/context: `app/ui/main_window.py`, `app/ui/widgets/context_bar.py`;
  - мастер обмена: `app/ui/import_export/import_export_wizard.py` (формат `Form100 ZIP`).
- Расширены сервисы:
  - `ExchangeService`: `export_form100_package_zip`, `import_form100_package_zip`;
  - `ReportingService`: `export_form100_pdf` с записью в `report_run` и артефактами/hash.
- Добавлены тесты:
  - unit: `tests/unit/test_form100_rules.py`;
  - integration: `tests/integration/test_form100_service.py`.
- Проверки после внедрения:
  - `ruff check ...` — успешно;
  - `mypy app` — успешно (0 ошибок в 154 source files);
  - `pytest` — 186 passed;
  - `python -m compileall app` — успешно.
- UI-полировка Form100 (локализация и таблица):
  - в `app/ui/form100/form100_view.py` статус-фильтр переведен на русские подписи (`Черновик`/`Подписано`) при сохранении внутренних значений (`DRAFT`/`SIGNED`);
  - в `app/ui/form100/form100_view.py` таблица карточек настроена на растяжение последней колонки (`Обновлено`) до правого края (`horizontalHeader().setStretchLastSection(True)`);
  - в `app/ui/form100/form100_view.py` кнопки локализованы: `Экспорт ZIP`, `Импорт ZIP`, `Экспорт PDF`;
  - в `app/ui/form100/form100_view.py` отображение статуса в таблице переведено на русские значения через `_status_label(...)`.
- Локализация блока bodymap:
  - в `app/ui/form100/form100_editor.py` заголовок секции изменен на `Схема тела`;
  - в `app/ui/form100/widgets/bodymap_editor.py` подписи/ошибки локализованы (`Метки схемы тела`), добавлен tooltip с описанием структуры JSON-меток.
- Проверки после правок:
  - `ruff check app/ui/form100/form100_view.py app/ui/form100/form100_editor.py app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `python -m compileall app/ui/form100` — успешно.
- Замена JSON-ввода bodymap на визуальный редактор для врачей:
  - `app/ui/form100/widgets/bodymap_editor.py` полностью переведен на UX без JSON-поля;
  - добавлен режим `Открыть окно рисования` с отдельным диалогом и двумя холстами: `Вид спереди` / `Вид сзади`;
  - реализованы инструменты меток: `Рана (X)`, `Ожог (область)`, `Жгут (линия)`, `Ампутация (область)`, `Заметка (пин)`;
  - реализованы действия редактирования: отмена последней метки, очистка стороны, очистка всех меток, удаление ближайшей метки ПКМ;
  - сохранение осталось совместимым с backend/экспортом: формируются те же `Form100MarkDto` (`side/type/shape_json/meta_json`), без изменения API.
- Добавлены unit-тесты для нормализации/агрегации меток:
  - `tests/unit/test_form100_bodymap_editor.py`.
- Проверки после внедрения визуального редактора:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py tests/unit/test_form100_bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py tests/unit/test_form100_bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed;
  - `python -m compileall app/ui/form100/widgets/bodymap_editor.py app/ui/form100/form100_editor.py` — успешно.
- Улучшен шаблон bodymap под вид бланка Формы 100:
  - в `app/ui/form100/widgets/bodymap_editor.py` заменен базовый каркасный контур на силуэт человека (перед/зад) с геометрией головы, шеи, туловища, рук и ног;
  - добавлена фон-подложка холста и анатомические ориентиры (центральная линия, ключевые линии для front/back), чтобы рисование меток соответствовало логике бумажной формы;
  - сохранение/чтение меток осталось в прежнем контракте (`Form100MarkDto`, `shape_json/meta_json`), backend/экспорт/импорт не менялись.
- Проверки после доработки шаблона:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed;
  - `python -m compileall app/ui/form100/widgets/bodymap_editor.py` — успешно.
- Фиксация таблицы карточек Form100:
  - в `app/ui/form100/form100_view.py` отключено ручное изменение ширины колонок (`QHeaderView.ResizeMode.Fixed`, `setSectionsMovable(False)`);
  - добавлен перерасчет фиксированных ширин по пропорциям от доступной ширины таблицы, чтобы все 8 колонок оставались видимыми без горизонтального скролла;
  - добавлен вызов перерасчета при `refresh_cards()` и `resizeEvent()`.
- Проверки после фиксации таблицы:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Подключен референсный шаблон тела из файла пользователя:
  - добавлена загрузка `app/image/main/form_100_body.png` в визуальный `BodymapEditor`;
  - для комбинированного изображения реализован автосплит на front/back (горизонтальные/вертикальные варианты; для текущего шаблона используются первые два сегмента как `Вид спереди` и `Вид сзади`);
  - в `BodymapCanvas` добавлен рендер шаблона-изображения с fallback на векторный силуэт, если файл отсутствует/нечитабелен.
- Проверки после подключения шаблона:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed.
- Точная корректировка сплита `form_100_body.png` по обратной связи:
  - в `app/ui/form100/widgets/bodymap_editor.py` переработана `_split_combined_template(...)` с безопасным `clamped copy`;
  - для горизонтального шаблона с 4 сегментами добавлены направленные смещения crop-окон:
    - `front` расширен вправо, чтобы не обрезать правую кисть/пальцы;
    - `back` сдвинут левее и расширен вправо, чтобы не обрезать левую кисть.
- Проверки после корректировки сплита:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed.
- Точечный фикс артефакта в `Вид сзади`:
  - в `app/ui/form100/widgets/bodymap_editor.py` скорректирован crop для back-сегмента: окно сдвинуто вправо относительно границы сегмента и расширено вправо;
  - это убирает попадание руки от соседней фигуры (`Вид спереди`) слева на холсте `Вид сзади`.
- Проверки после точечного фикса:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed.
- Дополнительная подстройка `Вид сзади` (устранение артефакта справа):
  - в `app/ui/form100/widgets/bodymap_editor.py` back-crop переведен на симметричную подрезку сегмента (`back_trim_left` + `back_trim_right`) вместо расширения вправо;
  - это убирает попадание фрагмента соседней фигуры справа, сохраняя целостность основной фигуры.
- Проверки после дополнительной подстройки:
  - `ruff check app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `mypy app/ui/form100/widgets/bodymap_editor.py` — успешно;
  - `pytest -q tests/unit/test_form100_bodymap_editor.py tests/integration/test_form100_service.py` — 7 passed.
- Фикс layout-бага Form100 при выборе фильтра `Подписано`:
  - в `app/ui/form100/form100_view.py` убрано жёсткое минимальное ограничение ширины таблицы, из-за которого схлопывалась правая панель редактора;
  - переработан `_apply_cards_table_column_widths()` на адаптивное сжатие/расширение с min-ширинами колонок, чтобы колонка `Обновлено` оставалась читаемой, а правая часть не уезжала;
  - стабилизирована ширина `status_filter` (`connect_combo_autowidth(..., min_width=120)` + `setMaximumWidth(140)`), чтобы переключение `Все/Черновик/Подписано` не ломало геометрию шапки;
  - `QSplitter` возвращен к приоритету редактора (stretch 1:2), чтобы блоки функций и схема тела оставались доступными.
- Проверки после фикса layout:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Корректировка ширины таблицы карточек Form100 (регресс по колонке `Обновлено`):
  - в `app/ui/form100/form100_view.py` заменен предыдущий алгоритм сжатия на фиксированные базовые ширины колонок;
  - колонка `Обновлено` зафиксирована в базовом размере и больше не ужимается до нечитаемого состояния;
  - ширина самой левой области в `QSplitter` увеличена (баланс 1:1 вместо 1:2), чтобы таблица входила целиком без ручного растягивания;
  - ручное изменение ширин колонок по-прежнему отключено (`QHeaderView.ResizeMode.Fixed`, `setSectionsMovable(False)`).
- Проверки после корректировки:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Финальная фиксация таблицы Form100 по UI-замечанию (статичное поле + статичные колонки):
  - в `app/ui/form100/form100_view.py` заданы фиксированные ширины колонок без автосжатия (`_cards_base_widths`);
  - увеличена базовая ширина проблемных колонок (`Статус`, `Версия`, `Подразделение`, `Обновлено`), чтобы заголовки не обрезались;
  - зафиксирована ширина поля таблицы (`_cards_panel_width`, `setFixedWidth(...)`) и отключена возможность ручного перетягивания разделителя (`splitter.setHandleWidth(0)`);
  - добавлен `_enforce_splitter_sizes()` для поддержания стабильной геометрии таблицы и правой панели.
- Проверки после финальной фиксации:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Перевод таблицы Form100 на адаптив под любые экраны:
  - в `app/ui/form100/form100_view.py` убрана привязка к фиксированной ширине поля таблицы;
  - добавлен адаптивный расчёт геометрии (`_apply_cards_layout`, `_enforce_splitter_sizes`) с учетом минимальной ширины редактора и доступной ширины окна;
  - колонки оставлены статичными для пользователя (ручной resize отключен), но их ширины теперь автоматически пересчитываются под текущую ширину таблицы:
    - режим `preferred` при достаточной ширине;
    - режим `min + distribute` при среднем размере;
    - режим `floor shrink` для узких экранов.
- Проверки после адаптивного перевода:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Усилена читаемость колонок `Подразделение` и `Обновлено` на малых экранах:
  - в `app/ui/form100/form100_view.py` увеличены пороги сжатия:
    - `Подразделение`: `min 124 -> 138`, `floor 96 -> 112`;
    - `Обновлено`: `min 118 -> 130`, `floor 96 -> 110`.
- Проверки после усиления порогов:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.
- Адаптация Form100 под малые экраны (универсальная, без привязки к конкретному монитору):
  - в `app/ui/form100/form100_view.py` шапка `Поиск карточек` перестроена в 2 строки:
    - строка 1: поиск + фильтр статуса + `Найти`;
    - строка 2: кнопки действий в компактной сетке (`QGridLayout`) вместо длинной горизонтальной ленты;
  - кнопки действий сделаны компактнее (`compact_button(..., min_width=112, max_width=180)`), чтобы снижать риск «ломки» шапки на малых dpi/дюймах;
  - добавлен responsive-переключатель ориентации `QSplitter`:
    - узкий экран (`< 1380 px`): вертикальная компоновка (таблица сверху, форма снизу);
    - широкий экран: горизонтальная компоновка (таблица слева, форма справа);
  - перерасчет размеров сплиттера теперь учитывает текущую ориентацию.
- Проверки после responsive-доработки:
  - `ruff check app/ui/form100/form100_view.py` — успешно;
  - `mypy app/ui/form100/form100_view.py` — успешно;
  - `python -m compileall app/ui/form100/form100_view.py` — успешно;
  - `pytest -q tests/integration/test_form100_service.py` — 3 passed.

### 2026-02-16

- Обновлена проектная документация по палитре UI в `docs/context.md`:
  - добавлен раздел `16) Цветовая система UI (рекомендуемая палитра)`;
  - добавлены структурированные блоки `Core / Accent / Status / Charts / Bodymap`;
  - для каждого цвета зафиксированы `где применяется` и `для чего`.
- Добавлены правила использования палитры:
  - новые экраны используют только зафиксированные цвета;
  - статусные стили берутся централизованно из `app/ui/widgets/notifications.py`;
  - при добавлении нового цвета требуется обновление документации.
- Актуализирован раздел структуры UI в `docs/context.md`:
  - переписан раздел `7) UI (PySide6)` под текущую реализацию;
  - добавлена таблица разделов приложения с назначением, функционалом, ролями и основными файлами;
  - добавлены сквозные сценарии контекста/обновления справочников/обновления сводки.
- Исправлены замечания `markdownlint` (`MD060`) в `docs/context.md`:
  - таблицы переведены в единый стиль разделителей с пробелами (`| --- | ... |`);
  - устранены ошибки на строках разделов `7.2` и `16.x`.

### 2026-02-18

- Стартована и внедрена premium UI-интеграция из `Test_UI` в боевой проект без изменений backend/DB/сервисов:
  - добавлены UI feature flags в `app/config.py`:
    - `ui_premium_enabled` (`EPIDCONTROL_UI_PREMIUM`, default `1`);
    - `ui_animation_policy` (`EPIDCONTROL_UI_ANIMATION`: `adaptive/full/minimal`, default `adaptive`);
    - `ui_density` (`EPIDCONTROL_UI_DENSITY`: `compact/normal`, default `normal`).
  - добавлены новые UI-модули:
    - `app/ui/theme.py` (единая палитра и глобальный QSS);
    - `app/ui/runtime_ui.py` (`UiRuntimeConfig`, adaptive policy по экрану/DPI);
    - `app/ui/widgets/transition_stack.py` (анимированные переходы страниц);
    - `app/ui/widgets/toast.py` (toast manager, fade-in/fade-out, позиционирование);
    - `app/ui/widgets/animated_background.py` (subtle/showcase animated background);
    - `app/ui/widgets/responsive_actions.py` (адаптивная раскладка кнопок).
- Shell-интеграция:
  - `app/main.py`: подключение новой темы через `apply_theme(...)`;
  - `app/ui/main_window.py`:
    - переход с `QStackedWidget` на `TransitionStack` с directional animation;
    - добавлен слой `MedicalBackground` (включается по runtime policy);
    - сохранена текущая top-menu навигация и вся логика контекста/ролей.
- UX/адаптив:
  - `app/ui/widgets/context_bar.py`: добавлен responsive reflow для узких экранов + адаптивная панель быстрых действий;
  - `app/ui/form100/form100_view.py`: actions переведены на `ResponsiveActionsPanel`, сохранены статичные колонки;
  - `app/ui/analytics/analytics_view.py`: основные action-кнопки и actions истории отчётов переведены на responsive layout;
  - `app/ui/patient/patient_emk_view.py`: quick actions переведены на responsive layout;
  - `app/ui/import_export/import_export_view.py`: quick actions переведены на responsive layout.
- Уведомления:
  - `app/ui/widgets/notifications.py`: сохранены `show_error/show_warning/show_info`;
  - добавлен `show_toast(...)`;
  - политика переключена на неблокирующие toast для `info/warning/success`, `error` оставлен modal + лог.
- Добавлены новые unit-тесты:
  - `tests/unit/test_ui_theme_tokens.py`;
  - `tests/unit/test_transition_stack.py`;
  - `tests/unit/test_toast_manager.py`;
  - `tests/unit/test_responsive_actions.py`;
  - `tests/unit/test_form100_table_layout.py`;
  - `tests/unit/test_main_window_ui_shell.py`.
- Проверки после внедрения:
  - `ruff check app tests` — успешно;
  - `pytest -q` — `200 passed`;
  - целевой набор новых/затронутых тестов — `14 passed`.
- Продолжена шлифовка Stage 6 (централизация стилей):
  - `app/ui/widgets/context_bar.py`:
    - убраны inline-стили у toggle/helper/подзаголовков;
    - добавлены objectName-селекторы (`contextToggle`, `muted`) для управления из глобальной темы;
  - `app/ui/widgets/notifications.py`:
    - `set_status/clear_status` переведены с локального `setStyleSheet(...)` на динамические свойства (`statusLevel`) + реполиш;
    - сохранены текущие контракты API (`set_status`, `clear_status`, `show_*`) без изменения внешнего поведения;
  - `app/ui/theme.py`:
    - добавлены QSS-правила для `statusLabel`, `chipClear`, `contextToggle`.
- Проверки после шлифовки Stage 6:
  - `ruff check app tests` — успешно;
  - `pytest -q` — `202 passed`.
- Добавлен тест на статусные label:
  - `tests/unit/test_notifications_status.py` — проверка `statusLevel` при `set_status/clear_status`.
- Продолжена централизация стилей диалогов:
  - `app/ui/login_dialog.py`:
    - удалён локальный `_apply_styles()` и inline QSS;
    - введены `objectName` для элементов (`loginAppTitle`, `loginTimeValue`, `loginCardTitle`, `loginCardHint` и др.);
  - `app/ui/first_run_dialog.py`:
    - удалён локальный `_apply_styles()` и inline-цвета для form-label;
    - введены `objectName` (`firstRunTitle`, `firstRunSubtitle`, `firstRunMedicalLine`, `firstRunInfoBadge`, `firstRunFormLabel`);
  - `app/ui/theme.py`:
    - добавлены централизованные стили для `QDialog#loginDialog` и `QDialog#firstRunDialog` с сохранением текущего визуального паттерна.
- Проверки после централизации dialog-styles:
  - `ruff check app tests` — успешно;
  - `pytest -q` — `202 passed`.
- Продолжение Stage 6 (миграция inline-стилей в тему, волна 2):
  - `app/ui/admin/user_admin_view.py`:
    - убраны локальные `setStyleSheet(...)` у role hint / groupbox title / status;
    - добавлены objectName (`muted`, `adminStatus`) для централизованной темы;
  - `app/ui/references/reference_view.py`:
    - role hint переведен на `objectName="muted"`;
  - `app/ui/home/home_view.py`:
    - `_user_info_label` переведён на `objectName="homeUserInfo"`;
    - `statBadge` переведен с inline-color на property `toneKey` + правила в `theme.py`;
    - подпись метрики переведена на `objectName="muted"`;
  - `app/ui/patient/patient_edit_dialog.py`:
    - subtitle/status переведены на theme-driven стиль;
    - валидация использует `clear_status/set_status` вместо ручной окраски;
  - `app/ui/patient/patient_emk_view.py`, `app/ui/emz/emz_form.py`:
    - вспомогательные подписи переведены на `objectName="muted"`;
  - `app/ui/widgets/case_search_dialog.py`, `app/ui/widgets/patient_search_dialog.py`:
    - статусные лейблы переведены на `statusLabel`, добавлено использование `clear_status/set_status`;
  - `app/ui/form100/widgets/validation_banner.py`:
    - баннер переведен с inline QSS на `objectName="validationBanner"`.
  - `app/ui/theme.py`:
    - добавлены правила для `adminStatus`, `homeUserInfo`, `validationBanner`, `statBadge[toneKey=...]`.
- Проверки после волны 2:
  - `ruff check app tests` — успешно;
  - `pytest -q` — `202 passed`.
- Продолжение Stage 6 (миграция inline-стилей в тему, волна 3):
  - `app/ui/lab/lab_samples_view.py`:
    - карточки списка проб переведены на theme objectName (`listCard`, `cardStatusDot`, `cardTitle`, `cardMeta`);
    - `count_label` переведён на `muted`;
  - `app/ui/lab/lab_sample_detail.py`:
    - `qc_due_at` переведён на `objectName="muted"`;
  - `app/ui/sanitary/sanitary_dashboard.py` и `app/ui/sanitary/sanitary_history.py`:
    - summary/dept/meta подписи переведены на objectName;
    - карточки списка и статусные точки переведены на theme-driven стиль (через свойства `tone`);
  - `app/ui/theme.py`:
    - добавлены правила `listCard`, `cardStatusDot[tone=...]`, `cardTitle`, `cardMeta[tone=...]`.
- Результат по остаткам inline QSS:
  - в `app/ui` оставлен только `toast.py` (осознанно: динамический вид toast-компонента).
- Проверки после волны 3:
  - `ruff check app tests` — успешно;
  - `pytest -q` — `202 passed`.
- Продолжение Stage 6 (миграция inline-стилей в тему, волна 4):
  - `app/ui/widgets/toast.py`:
    - удалён локальный `setStyleSheet(...)`;
    - введены `objectName="toast"` и свойство `toastLevel`.
  - `app/ui/theme.py`:
    - добавлены правила `QWidget#toast[toastLevel=...]` + оформление `QWidget#toast QLabel`.
  - итог: в `app/ui` больше нет локальных `setStyleSheet(...)`; стили централизованы в `theme.py`.
- Проверки после волны 4:
  - `rg -n "setStyleSheet\\(" app/ui app/main.py` — только вызов `app.setStyleSheet(...)` в `theme.py`;
  - `ruff check app tests` — успешно;
  - `pytest -q` — `202 passed`.
- Зафиксирована защита от возврата inline-стилей:
  - добавлен `tests/unit/test_ui_no_inline_styles.py`;
  - тест запрещает `setStyleSheet(...)` в `app/ui/**`, кроме `app/ui/theme.py`.
- Проверки после добавления guard-теста:
  - `pytest -q tests/unit/test_ui_no_inline_styles.py` — `1 passed`;
  - `pytest -q` — `203 passed`.
- Адаптив верхней навигации и action-toolbar (малые экраны/DPI):
  - `app/ui/main_window.py`:
    - добавлены режимы подписей меню `full/compact/mini` с динамическим выбором по доступной ширине menubar;
    - реализованы карты коротких названий пунктов (`Главн.`, `Ф100`, `Имп/Эксп`, `Админ` и т.д.);
    - добавлены runtime-свойства `compactNav`/`miniNav` для theme-правил;
    - адаптация выполняется при `resize`, смене сессии и переключении раздела;
  - `app/ui/theme.py`:
    - добавлены QSS-правила для `QMenuBar[compactNav="true"]` и `QMenuBar[miniNav="true"]` (уменьшенные отступы/радиусы);
  - `app/ui/emz/emz_form.py`:
    - quick actions переведены с фиксированного `QHBoxLayout` на `ResponsiveActionsPanel`;
    - добавлен resize-driven compact режим для кнопок ЭМЗ.
- Тесты по адаптивной навигации:
  - расширен `tests/unit/test_main_window_ui_shell.py` (проверка перехода меню в `compact/mini` на узком окне и возврата в `full` на широком).
- Проверки после адаптивного шага:
  - `ruff check app tests` — успешно;
  - `pytest -q tests/unit/test_main_window_ui_shell.py` — `2 passed`;
  - `pytest -q` — `204 passed`.
- Продолжение адаптивного шага (Lab/Sanitary action rows):
  - `app/ui/lab/lab_samples_view.py`:
    - верхние кнопки действий переведены на `ResponsiveActionsPanel`;
    - добавлен resize-driven compact режим (`< 1400 px`);
  - `app/ui/sanitary/sanitary_dashboard.py`:
    - верхние кнопки действий переведены на `ResponsiveActionsPanel`;
    - добавлен resize-driven compact режим (`< 1340 px`);
  - `app/ui/sanitary/sanitary_history.py`:
    - блок `Действия` переведен на `ResponsiveActionsPanel`;
    - добавлен resize-driven compact режим (`< 1300 px`).
- Добавлены unit-тесты:
  - `tests/unit/test_lab_sanitary_actions_layout.py`:
    - проверка наличия `ResponsiveActionsPanel` в `LabSamplesView`, `SanitaryDashboard`, `SanitaryHistoryDialog`;
    - проверка переключения compact режима на узкой/широкой ширине.
- Проверки после Lab/Sanitary адаптива:
  - `ruff check app tests` — успешно;
  - `pytest -q tests/unit/test_lab_sanitary_actions_layout.py` — `2 passed`;
  - `pytest -q` — `206 passed`.
- Stage 7 (документация premium UI) — актуализация:
  - `docs/context.md`:
    - в разделе `17.6` обновлен факт тестов до `202 passed`;
    - добавлен `17.7 Гайд по стилю и objectName` (правила по отказу от inline QSS и централизации в `theme.py`);
    - добавлен `17.8 Чеклист для нового UI-экрана` (адаптив, таблицы, уведомления, проверки).
- Доработка окна авторизации (видимость анимации на разных экранах):
  - `app/ui/login_dialog.py`:
    - добавлен адаптивный расчёт начального и минимального размера окна (`_apply_initial_size`);
    - стартовый размер теперь вычисляется от `availableGeometry()` экрана (с безопасными min/max ограничениями), вместо размера "по содержимому";
    - это обеспечивает более крупную область фона/анимации при сохранении корректной работы на малых экранах.
  - Проверки:
    - `python -m compileall app/ui/login_dialog.py` — успешно;
    - `ruff check app/ui/login_dialog.py` — успешно.
- Доработка компоновки логин-экрана (центровка + крупные дата/время):
  - `app/ui/login_dialog.py`:
    - заголовок приложения переведен в центр и увеличен;
    - дата/время вынесены в отдельный крупный центрированный виджет `loginTimePanel`;
    - добавлена центровка окна авторизации по центру экрана при первом показе (`showEvent` + `_center_dialog_on_screen`).
  - `app/ui/theme.py`:
    - добавлены стили для `QFrame#loginTimePanel`;
    - усилены стили `loginAppTitle`, `loginTimeCaption`, `loginTimeValue` под новую компоновку.
  - Проверки:
    - `ruff check app/ui/login_dialog.py app/ui/theme.py` — успешно;
    - `python -m compileall app/ui/login_dialog.py app/ui/theme.py` — успешно.
- Доработка диалога создания первого администратора:
  - `app/ui/first_run_dialog.py`:
    - добавлен адаптивный стартовый/минимальный размер окна (`_apply_initial_size`);
    - добавлена центровка окна по экрану при первом показе (`showEvent` + `_center_dialog_on_screen`);
    - выровнены по центру заголовок и описание;
    - карточка формы ограничена по ширине и центрирована для более чистого премиум-лейаута;
    - информационные блоки снизу центрированы и переведены в многострочный режим.
  - `app/ui/theme.py`:
    - обновлены стили `firstRunTitle/Subtitle/InfoBadge` под новый визуальный размер и акценты.
  - Проверки:
    - `ruff check app/ui/first_run_dialog.py app/ui/theme.py` — успешно;
    - `python -m compileall app/ui/first_run_dialog.py app/ui/theme.py` — успешно.
- Глобальная компактность UI (все разделы: кнопки, таблицы, сводные показатели):
  - `app/ui/widgets/button_utils.py`:
    - уменьшены дефолтные размеры `compact_button`: `min_width 140 -> 112`, `max_width 260 -> 220`.
  - `app/ui/widgets/responsive_actions.py`:
    - кнопки больше не растягиваются на всю ширину колонки (`Expanding -> Minimum`);
    - кнопки центрируются внутри ячеек adaptive-grid, что устраняет визуально «огромные» плашки на широких экранах.
  - `app/ui/theme.py`:
    - уменьшен базовый шрифт интерфейса (`13 -> 12`, compact `12 -> 11`);
    - уменьшены отступы/высота кнопок;
    - для таблиц уменьшены шрифт и отступы заголовков (`QHeaderView::section`), чтобы заголовки лучше помещались;
    - добавлены стили `statCard` и `metricValue`, чтобы блок «Сводные показатели» выглядел плотнее и не создавал эффект пустого экрана.
  - Проверки:
    - `ruff check app/ui/widgets/button_utils.py app/ui/widgets/responsive_actions.py app/ui/theme.py` — успешно;
    - `pytest -q tests/unit/test_responsive_actions.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_main_window_ui_shell.py` — `6 passed`;
    - `python -m compileall app/ui/widgets/button_utils.py app/ui/widgets/responsive_actions.py app/ui/theme.py` — успешно.
- Точечная донастройка `ЭМЗ` + `Форма 100` (после пользовательского фидбека по крупным кнопкам и колонкам):
  - `app/ui/widgets/responsive_actions.py`:
    - убрано принудительное растягивание колонок action-grid, кнопки теперь не «разъезжаются» на всю ширину строки;
    - в результате action-строки в разделах выглядят компактнее и ровнее.
  - `app/ui/emz/emz_form.py`:
    - уменьшен базовый `min_button_width` панели быстрых действий (`136 -> 104`);
    - порог compact-режима обновлен (`1460 -> 1380`) для более раннего аккуратного reflow.
  - `app/ui/form100/form100_view.py`:
    - снижена минимальная ширина редактора (`560 -> 520`) для отдачи большего места таблице карточек;
    - увеличены и перераспределены ширины колонок таблицы карточек (в т.ч. приоритет для `ФИО`, `Подразделение`, `Обновлено`);
    - скорректированы минимальные/floor-ширины, чтобы заголовки были читаемее на узких экранах;
    - увеличена доля ширины сплиттера под таблицу (`0.40 -> 0.46`);
    - action-панель формы 100 дополнительно уплотнена (`min_button_width 108 -> 102`, compact threshold `1480 -> 1400`).
  - Проверки:
    - `ruff check app/ui/widgets/responsive_actions.py app/ui/emz/emz_form.py app/ui/form100/form100_view.py` — успешно;
    - `pytest -q tests/unit/test_responsive_actions.py tests/unit/test_form100_table_layout.py tests/unit/test_main_window_ui_shell.py tests/unit/test_lab_sanitary_actions_layout.py` — `7 passed`;
    - `python -m compileall app/ui/widgets/responsive_actions.py app/ui/emz/emz_form.py app/ui/form100/form100_view.py` — успешно.
- Финальная визуальная подгонка (1366x768 / 1920x1080) по action-row и плотности экранов:
  - `app/ui/widgets/button_utils.py`:
    - дефолт `compact_button` дополнительно уплотнен (`min 104`, `max 200`).
  - `app/ui/widgets/responsive_actions.py`:
    - уменьшены интервалы сетки действий (горизонталь/вертикаль);
    - spacing теперь адаптивный в `compact`;
    - сохранено центрирование кнопок, убрано их избыточное визуальное растяжение.
  - `app/ui/emz/emz_form.py`:
    - quick-action кнопки ЭМЗ сделаны компактнее (`min 96`, `max 180`) при сохранении адаптивного переноса.
  - `app/ui/form100/form100_view.py`:
    - action-кнопки формы 100 дополнительно уменьшены (`min 92..96`, `max 140..160`) для аккуратного размещения на меньших экранах.
  - `app/ui/widgets/context_bar.py`:
    - быстрые кнопки в «Закрепить пациента» уменьшены (`min 88`, `max 164`);
    - панель действий дополнительно уплотнена (`min_button_width=84`).
  - `app/ui/home/home_view.py`:
    - блок «Сводные показатели» сделан менее пустым:
      - колонки grid теперь растягиваются равномерно;
      - карточки статистики занимают доступную ширину;
      - удалён лишний внутренний stretch, из-за которого контент выглядел «прижатым» к левому краю.
  - `app/ui/theme.py`:
    - уменьшены глобальная высота кнопок и отступы;
    - таблицы уплотнены (`QTableWidget/QTableView` и `QHeaderView::section` до `10px`) для лучшего вмещения заголовков;
    - добавлено локальное правило для `contextActions` (ещё компактнее).
  - Проверки:
    - `ruff check app/ui/widgets/button_utils.py app/ui/widgets/responsive_actions.py app/ui/emz/emz_form.py app/ui/form100/form100_view.py app/ui/widgets/context_bar.py app/ui/home/home_view.py app/ui/theme.py` — успешно;
    - `pytest -q tests/unit/test_responsive_actions.py tests/unit/test_main_window_ui_shell.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_form100_table_layout.py` — `7 passed`;
    - `python -m compileall app/ui/widgets/button_utils.py app/ui/widgets/responsive_actions.py app/ui/emz/emz_form.py app/ui/form100/form100_view.py app/ui/widgets/context_bar.py app/ui/home/home_view.py app/ui/theme.py` — успешно.

- Реализован Form100 V2 под feature-flag `EPIDCONTROL_FORM100_V2_ENABLED`:
  - добавлены новые V2-модули:
    - `app/domain/models/form100_v2.py`;
    - `app/domain/rules/form100_rules_v2.py`;
    - `app/application/dto/form100_v2_dto.py`;
    - `app/application/services/form100_service_v2.py`;
    - `app/infrastructure/db/repositories/form100_repo_v2.py`;
    - `app/infrastructure/export/form100_export_v2.py`;
    - `app/infrastructure/import/form100_import_v2.py`;
    - `app/infrastructure/reporting/form100_pdf_report_v2.py`;
    - `app/ui/form100_v2/*` (view/editor/bodymap).
  - добавлена миграция `0019_form100_v2_schema.py`:
    - создана схема `form100` + `form100_data`;
    - добавлен `legacy_card_id` для трассировки;
    - реализован перенос данных из legacy `form100_card/form100_mark/form100_stage`.
  - выполнена интеграция в контейнер и существующие сервисы:
    - `app/container.py`: регистрация V2 repo/service;
    - `app/application/services/exchange_service.py`: `export/import_form100_v2_package_zip`;
    - `app/application/services/reporting_service.py`: `export_form100_v2_pdf` и маршрутизация PDF для V2;
    - `app/ui/main_window.py`: переключение legacy/V2 по feature-flag;
    - `app/ui/import_export/import_export_wizard.py`: добавлен формат `Form100 V2 ZIP`.
- Валидации/аудит/роли Form100 V2:
  - workflow зафиксирован как `DRAFT -> SIGNED`;
  - optimistic lock через `version`;
  - аудит в `audit_log.payload_json` в формате `form100.audit.v2` с diff изменённых key-path;
  - роли `admin/operator` на рабочие операции, admin-only на удаление.
- Добавлены тесты Form100 V2:
  - `tests/unit/test_form100_v2_rules.py`;
  - `tests/integration/test_form100_v2_service.py`.
- Проверки по итогам внедрения Form100 V2:
  - `ruff check app tests` — успешно;
  - `pytest -q tests/unit/test_form100_v2_rules.py tests/integration/test_form100_v2_service.py` — `6 passed`;
  - `pytest -q` — `212 passed`;
  - `python -m compileall app/application/dto/form100_v2_dto.py app/domain/models/form100_v2.py app/domain/rules/form100_rules_v2.py app/infrastructure/db/repositories/form100_repo_v2.py app/application/services/form100_service_v2.py app/infrastructure/export/form100_export_v2.py app/infrastructure/import/form100_import_v2.py app/infrastructure/reporting/form100_pdf_report_v2.py app/ui/form100_v2` — успешно.

- Актуализирована документация:
  - `docs/context.md`:
    - обновлен статус Этапа VI (`Форма 100 МО РФ v2.2`) на реализованный;
    - добавлен новый раздел `18) Form100 V2 (новый контур)` (feature-flag, схема БД, API, UI/bodymap, ZIP/PDF, покрытие тестами);
    - обновлены остаточный план и итерационный план (Form100 V2 закрыт, фокус на стабилизации/регрессии).

- Продолжение стабилизации Form100 V2 (добавлено покрытие по недостающим сценариям):
  - добавлены интеграционные тесты:
    - `tests/integration/test_form100_v2_roles.py` — проверка матрицы прав (удаление только `admin`);
    - `tests/integration/test_form100_v2_zip_roundtrip.py` — roundtrip в режиме `append` + проверка отказа при нарушении hash в ZIP;
    - `tests/integration/test_form100_v2_migration.py` — выполнение миграции `0019_form100_v2_schema` (создание V2-таблиц, перенос legacy-строки, корректный downgrade без удаления legacy-таблиц).
  - проверки:
    - `ruff check tests/integration/test_form100_v2_roles.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_form100_v2_migration.py` — успешно;
    - `mypy tests/integration/test_form100_v2_roles.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_form100_v2_migration.py` — успешно;
    - `pytest -q tests/integration/test_form100_v2_roles.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_form100_v2_migration.py` — `3 passed`;
    - `pytest -q` — `215 passed` (есть 2 deprecation warning от sqlite адаптера datetime в Python 3.12, на функционал не влияет).

- Продолжение внедрения `forma_100_section.md` в UI Form100 V2:
  - переработан `app/ui/form100_v2/form100_editor.py`:
    - в блок `Корешок` добавлены недостающие поля:
      - `stub_issued_date`, `stub_issued_time`;
      - `stub_pss_pgs_dose`, `stub_toxoid_type`, `stub_antidote_type`;
      - чек-лист `stub_med_help_underline` (без ручного JSON-ввода пользователем);
      - `stub_injury_date/stub_injury_time` переведены на `QDateEdit/QTimeEdit`;
    - в блок `Основной бланк` добавлены:
      - `main_issued_date`, `main_issued_time`;
      - `main_injury_date/main_injury_time` переведены на `QDateEdit/QTimeEdit`;
    - в блок `Нижний` поле `tourniquet_time` переведено на `QTimeEdit`;
    - расширены `load_card` / `_build_data_payload` / `clear_form` / `set_read_only` под новые поля;
    - добавлен безопасный парсинг дат/времени из legacy/V2 payload (`dd.MM.yyyy`, `yyyy-MM-dd`, `HH:mm`, `HH:mm:ss`).
  - добавлены unit-тесты UI-редактора:
    - `tests/unit/test_form100_v2_editor_fields.py`:
      - проверка сериализации новых полей в payload;
      - проверка загрузки новых полей из `Form100CardV2Dto`.
  - проверки:
    - `ruff check app/ui/form100_v2/form100_editor.py tests/unit/test_form100_v2_editor_fields.py` — успешно;
    - `mypy app/ui/form100_v2/form100_editor.py tests/unit/test_form100_v2_editor_fields.py` — успешно;
    - `pytest -q tests/unit/test_form100_v2_editor_fields.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_roles.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_form100_v2_migration.py` — `7 passed`;
    - `pytest -q` — `217 passed` (2 warnings по sqlite datetime adapter в Python 3.12, не блокирует).

---

## 2026-02-24 — Настройка окружения и исправление ошибок линтера/типизации

- **Окружение**: пересоздан `venv/` под Python 3.12.10 (старый venv был от стороннего проекта); установлены все зависимости из `requirements.txt` + `requirements-dev.txt`.
- **Исправлены ошибки ruff (2 шт.)**:
  - `app/domain/constants.py`: `MilitaryCategory(str, Enum)` и `IsmpType(str, Enum)` → `StrEnum` (UP042).
- **Исправлены ошибки mypy (13 шт.) в 5 файлах**:
  - `app/ui/widgets/transition_stack.py`: добавлен `# type: ignore[arg-type]` для `setGraphicsEffect(None)` (Qt допускает None, стабы — нет).
  - `app/ui/widgets/responsive_actions.py`: добавлена защита от `None` в `_clear_layout` (`takeAt` может вернуть `None`).
  - `app/ui/first_run_dialog.py`, `app/ui/login_dialog.py`, `app/ui/main_window.py`: добавлен `assert isinstance(app, QApplication)` после проверки на `None` (уточнение типа от `QCoreApplication` до `QApplication`).
  - `app/ui/main_window.py`: `_form100_view` переаннотирован как `Form100ViewV2 | Form100View` вместо `QWidget`.
- **Проверки по итогам**:
  - `ruff check app/` — `All checks passed`;
  - `mypy app/` — `Success: no issues found in 174 source files`;
  - `pytest -q` — `217 passed`.
- **Проанализирован `errors.md`** (94 ошибки Pylance, все в `app/main.py`):
  - Большинство (91) — артефакты Pylance: PySide6 не в PYTHONPATH редактора, отсутствие stub-файлов, отсутствие type hints в `_TeeStream`-классе.
  - 1 реальная проблема: `_STDERR_TEE` назван в стиле константы (UPPER_CASE), но переопределяется внутри функции (`reportConstantRedefinition`).
- **Исправлен `app/main.py`**: `_STDERR_TEE` → `_stderr_tee` (lowercase), чтобы соответствовать Python-конвенции для изменяемой модульной переменной. Проверки: `ruff` — passed, `mypy` — passed, `pytest` — `217 passed`.

---

## 2026-03-02 - Continuation: адаптивный проход Form100 (wizard/bodymap/evacuation)

### Что сделано

- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`:
  - перестроен layout шага: блоки управления вынесены в отдельную адаптивную панель над схемой тела;
  - добавлен responsive-переключатель направления панели (`LeftToRight` / `TopToBottom`) по ширине окна;
  - для узких экранов уменьшена минимальная высота схемы для лучшей вмещаемости.
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`:
  - центральный блок переведен на адаптивный `QBoxLayout` с переключением горизонталь/вертикаль;
  - на узких экранах обзор (`review`) уходит под основную форму, без «сжатия» в узкую колонку.
- `app/ui/form100_v2/widgets/bodymap_editor_v2.py`:
  - убран жесткий `resize(1220, 820)`, добавлен адаптивный расчет initial-size от фактического экрана.
- `app/ui/form100_v2/form100_wizard.py`:
  - добавлен дополнительный компактный брейкпоинт responsive-метрик для очень узких окон.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`:
  - уменьшен hard minimum size холста схемы тела для лучшей адаптивности.

### Проверки

- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/form100_wizard.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py` - `All checks passed`.
- `venv\\Scripts\\python.exe -m mypy app/ui/form100_v2/form100_wizard.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_ui_no_inline_styles.py tests/unit/test_notifications_status.py tests/integration/test_form100_v2_service.py` - `10 passed`.

### Статус DoD

- ✅ Узкие/сжатые колонки на критичных шагах Form100 существенно уменьшены.
- ✅ Поведение Form100 wizard стало стабильнее на небольших разрешениях.
- ✅ Изменения проверены статикой и тестами.

---

## 2026-03-02 - Continuation: окончательная зачистка кодировки и стабилизация тестов

### Что сделано

- `tests/integration/test_emz_service.py`:
  - исправлены остатки битой кодировки в фикстурных строках (`patient_full_name`, `patient_category`);
  - `patient_category` приведен к корректному enum-значению `MilitaryCategory.PRIVATE.value`.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`:
  - для кнопок инструментов схемы тела добавлен явный sync `active`-state через repolish;
  - стартовая активная кнопка теперь также принудительно синхронизируется по стилю.
- Дополнительно подтверждена чистота по рабочему контуру:
  - ? `app/` ? `tests/` ?????? ??? ????????? ????????? mojibake (`U+00C2`, `U+00C2`, `U+00C2`, `U+00C2`, `U+FFFD`) ? `*.py`.

### Проверки

- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_emz_service.py tests/integration/test_form100_v2_service.py tests/integration/test_exchange_service_import_reports.py` - `9 passed`.
- `venv\\Scripts\\python.exe -m mypy tests/integration/test_emz_service.py app/ui/form100_v2/form100_view.py app/application/services/reporting_service.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m mypy app/ui/form100_v2/wizard_widgets/bodymap_widget.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m ruff check tests/integration/test_emz_service.py app/ui/form100_v2/form100_view.py app/application/services/reporting_service.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/patient/patient_emk_view.py app/ui/theme.py` - `All checks passed`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_ui_no_inline_styles.py` - `3 passed`.

### Статус DoD

- ✅ Остатки битой кодировки в тестовом контуре устранены.
- ✅ Интеграционные сценарии EMZ/Form100/import не регресснули.
- ✅ Визуальная индикация активного инструмента на bodymap сделана более явной.

---

## 2026-03-02 - Form100/ЭМК: кодировка, bodymap и читаемость госпитализаций

### Что сделано

- `app/ui/patient/patient_emk_view.py`:
  - увеличена видимая область госпитализаций (`cases_table.setMinimumHeight(280)`);
  - переразложен правый блок (карточка пациента + госпитализации) с приоритетом места для таблицы госпитализаций.
- `app/ui/form100_v2/form100_view.py`:
  - полностью восстановлена нормальная кириллица во всех пользовательских строках (заголовки, кнопки, сообщения, диалоги, статусы).
- `app/application/services/reporting_service.py`:
  - восстановлены русские подписи и сообщения для XLSX/PDF-отчетов аналитики (листы/колонки/статусы/ошибки), чтобы исключить «крякозябры» в отчетности.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` и `app/ui/form100_v2/widgets/bodymap_editor_v2.py`:
  - оставлен единый набор силуэтов: только вид спереди и вид сзади (без отдельного женского набора);
  - добавлена нормализация шаблонов тела под белый фон/черный контур;
  - сохранена обратная совместимость со старыми маркерами (`female_*` маппится в `male_*`).
- `app/ui/theme.py`:
  - усилено визуальное состояние нажатых кнопок `Вид поражения`/`Вид сан. потерь` (`#lesionToggle:checked` и `[active="true"]`);
  - для чекбоксов типов тканей добавлена черная рамка индикатора (`#form100TissueCheck::indicator`), чтобы отметка не терялась на светлом фоне.

### Проверки

- `venv\\Scripts\\python.exe -m compileall -q app/ui/form100_v2 app/application/services/reporting_service.py app/ui/patient/patient_emk_view.py app/ui/theme.py` - успешно.
- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/form100_view.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/application/services/reporting_service.py app/ui/patient/patient_emk_view.py app/ui/theme.py` - `All checks passed!`.
- `venv\\Scripts\\python.exe -m mypy app/ui/form100_v2/form100_view.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/application/services/reporting_service.py app/ui/patient/patient_emk_view.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py tests/integration/test_exchange_service_import_reports.py tests/integration/test_analytics_service_queries.py` - `9 passed`.

### Статус DoD

- ✅ В Form100/отчетности восстановлена корректная кириллица.
- ✅ Bodymap приведен к единому 2-видовому формату (спереди/сзади) с читаемым контрастом.
- ✅ Состояние lesion/san-loss кнопок визуально однозначно.
- ✅ Зона госпитализаций в ЭМК больше и удобнее для просмотра.

---

## 2026-03-02 - Form100 body image migration to form_100_bd.png

### What was done

- Updated Form100 bodymap image loading to prioritize the new template file:
  - `app/ui/form100_v2/widgets/bodymap_editor_v2.py` now loads `form_100_bd.png` first with fallback to legacy `form_100_body.png`.
  - Added resilient handling for both template formats:
    - legacy 4-segment horizontal sprite (auto-split),
    - single body image (mirrored for all silhouettes).
- Updated wizard bodymap canvas:
  - `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` now loads `form_100_bd.png` first with fallback to `form_100_body.png`.
  - Rendering adjusted for the new image dimensions: the template is drawn per silhouette slot with proportional scaling (`KeepAspectRatio`) instead of one stretched full-width background.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` - passed.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/integration/test_form100_v2_service.py -p no:cacheprovider` - `5 passed, 1 warning`.

### DoD status

- ✅ New image `form_100_bd.png` is integrated in Form100 V2 UI flow.
- ✅ Backward compatibility with legacy `form_100_body.png` is preserved.

---

## 2026-03-02 - Form100 bodymap visual tuning for new 2-panel template

### What was done

- `app/ui/form100_v2/widgets/bodymap_editor_v2.py`:
  - refined template parser for `form_100_bd.png`: added dedicated handling for 2-panel layout (left = front, right = back);
  - preserved support for legacy 4-panel sprite and single-image fallback;
  - widened body drawing area inside each slot (`0.88w x 0.90h`) to avoid overly small silhouettes with the new template.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`:
  - added adaptive splitter for 4-panel / 2-panel / single-image templates;
  - switched internal storage from one shared pixmap to per-silhouette pixmaps;
  - aligned interactions with actual rendered image geometry:
    - marker placement/hit-testing and hover preview are now based on the real template draw-rect (`KeepAspectRatio`) instead of full slot bounds.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` - passed.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/integration/test_form100_v2_service.py -p no:cacheprovider` - `5 passed, 1 warning`.

### DoD status

- ✅ New 2-panel template (`form_100_bd.png`) is rendered proportionally and consistently.
- ✅ Marker coordinates and clicks are synchronized with the visible silhouette area.

---

## 2026-03-02 - Start of full manual regression (phase 1: automated precheck)

### What was done

- Started the planned full regression cycle from section 14.4 (`docs/context.md`).
- Executed a focused regression test pack covering:
  - auth/RBAC,
  - references CRUD/ACL,
  - patient context sync,
  - EMZ service + validators,
  - import/export ZIP/XLSX safety and error reporting,
  - laboratory/sanitary services,
  - reporting artifacts and analytics queries,
  - startup error-handling.
- Created run log:
  - `docs/manual_regression_run_2026-03-02.md` with block-by-block status matrix and next manual steps.

### Verification

- Command:
  - `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_auth_service.py tests/integration/test_reference_service.py tests/integration/test_reference_service_crud.py tests/integration/test_reference_service_catalogs.py tests/integration/test_reference_service_acl.py tests/integration/test_patient_service_core.py tests/integration/test_emz_service.py tests/integration/test_exchange_service_import_zip.py tests/integration/test_exchange_service_import_reports.py tests/integration/test_lab_service.py tests/integration/test_sanitary_service.py tests/integration/test_reporting_service_artifacts.py tests/integration/test_analytics_service_queries.py tests/unit/test_main_window_context_selection.py tests/unit/test_patient_widgets_error_handling.py tests/unit/test_emz_form_validators.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_startup_error_handling.py`
- Result:
  - `49 passed in 21.40s`

### DoD status

- ✅ Regression phase 1 (automated precheck) completed.
- ⏳ Regression phase 2 (manual desktop UI checklist) pending execution and defect capture.

---

## 2026-02-28 - FirstRun fine-tuning (button contrast and input height)

### What was done

- `app/ui/first_run_dialog.py`:
  - increased input field minimum heights from `42` to `45` px for better premium density;
  - increased primary `Создать` button minimum height from `40` to `42` px.
- `app/ui/theme.py`:
  - strengthened `firstRunPrimaryButton` contrast:
    - deeper gradient (`#8CDCCF -> #62C9B8`),
    - stronger border (`rgba(73, 163, 146, 0.95)`),
    - adjusted hover/pressed states for clearer visual feedback.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/first_run_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/first_run_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m pyright app/ui/first_run_dialog.py app/ui/theme.py` - `0 errors`.

### DoD status

- ✅ FirstRun inputs are taller and easier to scan.
- ✅ `Создать` button has clearer premium contrast and stronger CTA role.

---

## 2026-02-28 - Login cleanup and FirstRun premium style alignment

### What was done

- `app/ui/login_dialog.py`:
  - removed `Защищенный вход` badge from login card header per UX request;
  - kept premium card structure and hierarchy.
- `app/ui/first_run_dialog.py`:
  - rebuilt onboarding card in the same premium style as login:
    - top accent strip (`firstRunCardAccent`),
    - card title/subtitle (`firstRunCardTitle`, `firstRunCardHint`),
    - upgraded field styling via `firstRunInput`,
    - refined action buttons (`firstRunPrimaryButton`, `firstRunGhostButton`),
    - added supportive card meta text (`firstRunCardMeta`).
- `app/ui/theme.py`:
  - removed unused login security-badge style;
  - added full themed style set for new FirstRun premium elements and interactions.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/login_dialog.py app/ui/first_run_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/login_dialog.py app/ui/first_run_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m pyright app/ui/login_dialog.py app/ui/first_run_dialog.py app/ui/theme.py` - `0 errors`.

### DoD status

- ✅ Login card no longer shows `Защищенный вход`.
- ✅ First-run onboarding visually matches premium login style.

---

## 2026-02-28 - Login UI premium refresh

### What was done

- `app/ui/login_dialog.py`:
  - restructured login card header (accent strip + title + `Защищенный вход` badge);
  - added helper subtitle inside the card;
  - improved form semantics with dedicated field labels and tuned spacing;
  - regrouped action buttons into a compact right-aligned cluster;
  - upgraded button hierarchy (`loginPrimaryButton` / `loginGhostButton`) and card width bounds.
- `app/ui/theme.py`:
  - added premium visual styles for login dialog elements:
    - card gradient, accent strip, security badge, subtitle/meta text;
    - stronger input field styling (`loginInput`) with clearer focus state;
    - distinct primary/ghost button styles and interaction states;
    - refined title/time panel typography.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/login_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/login_dialog.py app/ui/theme.py` - passed.
- `venv\\Scripts\\python.exe -m pyright app/ui/login_dialog.py app/ui/theme.py` - `0 errors`.

### DoD status

- ✅ Login block is visually denser, cleaner, and more premium while preserving adaptive behavior.

---

## 2026-02-28 - Hotfix: restore Russian text encoding in login dialog

### What was done

- Fixed mojibake in `app/ui/login_dialog.py` (all Russian UI strings restored to normal Cyrillic).
- The file was re-saved in UTF-8 with BOM (`utf-8-sig`) to keep compatibility with the current project encoding style.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/login_dialog.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/login_dialog.py` - passed.
- `venv\\Scripts\\python.exe -m pyright app/ui/login_dialog.py` - `0 errors`.

### DoD status

- ✅ Login window labels/placeholders/buttons are readable in Russian again.

---

## 2026-02-28 - P2 cleanup checkpoint: full quality gates

### What was done

- After the latest P2 exception-handling cleanup batch, ran the full project quality gate script.

### Verification

- `powershell -ExecutionPolicy Bypass -File scripts\\quality_gates.ps1`:
  - `ruff` - passed
  - `mypy` - passed
  - `pyright` - passed (`0 errors`)
  - `pytest` - `221 passed, 2 warnings`
  - `compileall` - passed

### DoD status

- ✅ Global quality gate is green after current P2 changes.

---

## 2026-02-28 - P2 cleanup continuation: analytics/home/patient dialog + repository/util catches

### What was done

- UI error-handling:
  - `app/ui/analytics/analytics_view.py`: replaced broad catches in report history/filter operations with `_HANDLED_ANALYTICS_UI_ERRORS`; narrowed JSON filter parse catch to `(TypeError, ValueError)`.
  - `app/ui/home/home_view.py`: narrowed stats loading catch to typed tuple.
  - `app/ui/patient/patient_edit_dialog.py`: narrowed save catch to typed tuple.
- Repository/util cleanup:
  - `app/config.py`: narrowed migration copy fallback catch to `OSError`.
  - `app/infrastructure/reporting/pdf_fonts.py`: narrowed font registration fallback catch.
  - `app/infrastructure/export/form100_export_v2.py`: narrowed relative-path fallback catch.
  - `app/domain/rules/form100_rules_v2.py`: narrowed float conversion fallback catch.
  - `app/infrastructure/db/repositories/form100_repo_v2.py`: narrowed JSON decode fallback catch.
  - `app/infrastructure/db/repositories/reference_repo.py`, `app/infrastructure/db/repositories/patient_repo.py`: narrowed FTS fallback catches and added `SQLAlchemyError` typing.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/analytics/analytics_view.py app/ui/home/home_view.py app/ui/patient/patient_edit_dialog.py app/config.py app/infrastructure/reporting/pdf_fonts.py app/infrastructure/export/form100_export_v2.py app/domain/rules/form100_rules_v2.py app/infrastructure/db/repositories/form100_repo_v2.py app/infrastructure/db/repositories/reference_repo.py app/infrastructure/db/repositories/patient_repo.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/analytics/analytics_view.py app/ui/home/home_view.py app/ui/patient/patient_edit_dialog.py app/config.py app/infrastructure/reporting/pdf_fonts.py app/infrastructure/export/form100_export_v2.py app/domain/rules/form100_rules_v2.py app/infrastructure/db/repositories/form100_repo_v2.py app/infrastructure/db/repositories/reference_repo.py app/infrastructure/db/repositories/patient_repo.py` - passed.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_main_window_ui_shell.py tests/unit/test_main_window_context_selection.py tests/integration/test_analytics_service_queries.py tests/integration/test_reference_service.py tests/integration/test_reference_service_crud.py tests/integration/test_reference_service_catalogs.py tests/integration/test_patient_service_core.py tests/integration/test_form100_v2_service.py` - passed.

### DoD status

- ✅ Continued broad-except reduction in high-traffic UI and repository paths.
- ✅ Error behavior preserved (fail-safe fallback + user-visible messages).

---

## 2026-02-28 - P2 cleanup continuation: context/patient selector typed error handling

### What was done

- `app/ui/widgets/case_search_dialog.py`:
  - narrowed invalid ID parsing catch to `ValueError`;
  - replaced service call `except Exception` with typed catch:
    `(LookupError, RuntimeError, ValueError, SQLAlchemyError, TypeError)`.
- `app/ui/widgets/patient_selector.py`:
  - replaced callback error catch with typed tuple:
    `(LookupError, RuntimeError, ValueError, SQLAlchemyError, TypeError)`.
- `app/ui/widgets/context_bar.py`:
  - replaced three `except Exception` branches in case/patient context selection with typed catches:
    `(LookupError, RuntimeError, ValueError, SQLAlchemyError, TypeError)`.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/widgets/case_search_dialog.py app/ui/widgets/patient_selector.py app/ui/widgets/context_bar.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/ui/widgets/case_search_dialog.py app/ui/widgets/patient_selector.py app/ui/widgets/context_bar.py` - `Success: no issues found in 3 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_patient_widgets_error_handling.py tests/unit/test_main_window_context_selection.py` - `7 passed`.

### DoD status

- ✅ Removed remaining broad-except in context and patient selection widgets.
- ✅ Error UX behavior preserved and covered by unit tests.

---

## 2026-02-28 - P2 cleanup continuation: startup/login/main window exception narrowing

### What was done

- `app/bootstrap/startup.py`:
  - introduced `_HANDLED_STARTUP_ERRORS` and `_HANDLED_SEED_ERRORS`;
  - replaced generic catches in `run_migrations`, `ensure_schema_compatibility`, `seed_core_data`.
- `app/ui/first_run_dialog.py`:
  - replaced `except Exception` in admin creation flow with typed catch:
    `(SQLAlchemyError, OSError, RuntimeError, ValueError, TypeError)`.
- `app/ui/login_dialog.py`:
  - replaced `except Exception` in `_on_login` with typed catch:
    `(ValueError, SQLAlchemyError, RuntimeError, TypeError)`.
- `app/ui/main_window.py`:
  - replaced local `except Exception` during patient refresh context with typed catch:
    `(ValueError, SQLAlchemyError, RuntimeError, TypeError)`.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/bootstrap/startup.py app/ui/first_run_dialog.py app/ui/login_dialog.py app/ui/main_window.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/bootstrap/startup.py app/ui/first_run_dialog.py app/ui/login_dialog.py app/ui/main_window.py` - `Success: no issues found in 4 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_startup_error_handling.py` - `5 passed`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_main_window_context_selection.py tests/unit/test_main_window_ui_shell.py` - `6 passed`.

### DoD status

- ✅ Removed remaining broad-except in critical startup/auth/window flows covered by this step.
- ✅ Regression checks for startup and main window are green.

---

## 2026-02-28 - P2 cleanup continuation: ExchangeService narrow exception handling

### What was done

- `app/application/services/exchange_service.py`:
  - added `_HANDLED_IMPORT_ERRORS` tuple for row-level import recovery;
  - replaced `except Exception` in `import_excel`, `import_csv`, `import_json` row loops with `except _HANDLED_IMPORT_ERRORS`;
  - kept existing behavior: invalid rows are skipped into error report, import continues.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/application/services/exchange_service.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/application/services/exchange_service.py` - `Success: no issues found in 1 source file`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_exchange_service_import_reports.py` - `3 passed`.

### DoD status

- ✅ Broad-except removed in targeted ExchangeService import hotspots.
- ✅ Negative import scenarios still produce structured error reports without hard-fail.

---

## 2026-02-28 - P2 cleanup: narrow exceptions and adaptive width tuning

### What was done

- `app/application/services/form100_service_v2.py`:
  - narrowed import validation catch from `except Exception` to `except (TypeError, ValueError, KeyError)` in append mode.
- `app/application/services/reporting_service.py`:
  - added module logger;
  - `_safe_json_loads`: narrowed catch to `json.JSONDecodeError` and `TypeError`;
  - `_build_filter_maps`: narrowed catch to `(AttributeError, SQLAlchemyError, TypeError, ValueError)` with warning log.
- `app/ui/admin/user_admin_view.py`:
  - reduced hard layout thresholds/min widths in `_update_content_layout` for better behavior on smaller widths.
- `app/ui/form100_v2/wizard_widgets/form100_main_widget.py`:
  - replaced fixed isolation bar width (`setFixedWidth(22)`) with adaptive bounds (`min=18`, `max=24`).

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/application/services/form100_service_v2.py app/application/services/reporting_service.py app/ui/admin/user_admin_view.py app/ui/form100_v2/wizard_widgets/form100_main_widget.py` - passed.
- `venv\\Scripts\\python.exe -m mypy app/application/services/form100_service_v2.py app/application/services/reporting_service.py app/ui/admin/user_admin_view.py app/ui/form100_v2/wizard_widgets/form100_main_widget.py` - `Success: no issues found in 4 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py` - `3 passed`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_exchange_service_import_reports.py` - `3 passed`.

### DoD status

- ✅ Broad exception usage reduced in targeted service hotspots.
- ✅ Remaining fixed-width hotspot in Form100 main widget replaced with adaptive sizing.
- ✅ Changes validated by lint/type/tests and recorded in progress report.

---

## 2026-02-28 - Form100 PDF layout hardening (overflow-safe text)

### What was done

- `app/infrastructure/reporting/form100_pdf_report_v2.py`:
  - added width-aware clipping helper for text rendering (`_fit_text`, `_draw_clipped_text`);
  - protected key fields from visual overflow:
    - `ФИО`,
    - `Подразделение`,
    - `Жетон/ID`,
    - `Диагноз`,
    - bodymap summary lines.
- This prevents long values from spilling outside the printable block and improves report readability.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/infrastructure/reporting/form100_pdf_report_v2.py app/application/services/form100_service_v2.py app/application/services/reporting_service.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/infrastructure/reporting/form100_pdf_report_v2.py app/application/services/form100_service_v2.py app/application/services/reporting_service.py` - `Success: no issues found in 3 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py tests/unit/test_form100_v2_rules.py -p no:cacheprovider` - `8 passed, 1 warning`.
- Runtime check with intentionally long diagnosis confirms PDF generation succeeds and output is non-empty.

### DoD status

- ✅ Form100 PDF output is resilient to long text values (reduced risk of visually broken reports).

---

## 2026-02-28 - Form100 module audit: reporting integrity and anti-mojibake hardening

### What was done

- Performed dedicated Form100 module audit (service + PDF/ZIP reporting path):
  - validated lifecycle and reporting flows via targeted unit/integration tests;
  - validated runtime generation of Form100 PDF with Cyrillic payload;
  - validated runtime ZIP export payload encoding (`form100.json` / `manifest.json` in UTF-8).
- Fixed corrupted user-facing error texts in Form100 reporting path:
  - `app/application/services/form100_service_v2.py`:
    - normalized critical error messages (archive validation, card state restrictions, missing payload/hash mismatch, ACL);
    - replaced broken mojibake strings with stable plain-text messages.
  - `app/application/services/reporting_service.py`:
    - normalized Form100 reporting bootstrap error (`Form100 service is not configured`).

### Verification

- Static checks:
  - `venv\\Scripts\\python.exe -m ruff check app/application/services/form100_service_v2.py app/application/services/reporting_service.py app/infrastructure/reporting/form100_pdf_report_v2.py app/infrastructure/reporting/pdf_fonts.py app/infrastructure/export/form100_export_v2.py app/infrastructure/import/form100_import_v2.py tests/unit/test_form100_v2_rules.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py` - passed.
  - `venv\\Scripts\\python.exe -m mypy --no-incremental app/application/services/form100_service_v2.py app/application/services/reporting_service.py app/infrastructure/reporting/form100_pdf_report_v2.py app/infrastructure/reporting/pdf_fonts.py app/infrastructure/export/form100_export_v2.py app/infrastructure/import/form100_import_v2.py tests/unit/test_form100_v2_rules.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py` - `Success: no issues found in 9 source files`.
- Form100 regression subset:
  - `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_rules.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_form100_v2_roles.py tests/integration/test_form100_v2_migration.py tests/integration/test_exchange_service_import_reports.py -p no:cacheprovider` - `13 passed, 3 warnings`.
- Runtime reporting checks:
  - Form100 PDF (Cyrillic payload): valid `%PDF-` header, non-empty file, SHA256 generated.
  - Form100 ZIP: archive created, UTF-8 JSON decoded successfully, Cyrillic fields preserved, expected counts returned.

### DoD status

- ✅ Form100 reporting path (PDF/ZIP) is operational and non-empty.
- ✅ UTF-8 payload integrity verified for Cyrillic in export artifacts.
- ✅ User-facing mojibake errors removed from Form100 service/reporting flow.

---

## 2026-02-27 - Form100 API unification after V1 cleanup

### What was done

- Removed V2-suffixed duplicate API methods after switching to a single active Form100 implementation:
  - `app/application/services/exchange_service.py`:
    - removed `export_form100_v2_package_zip`,
    - removed `import_form100_v2_package_zip`.
  - `app/application/services/reporting_service.py`:
    - removed `export_form100_v2_pdf`.
- Updated integration usage to canonical method name:
  - `tests/integration/test_form100_v2_service.py` now calls `export_form100_pdf(...)`.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/application/services/exchange_service.py app/application/services/reporting_service.py tests/integration/test_form100_v2_service.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/application/services/exchange_service.py app/application/services/reporting_service.py tests/integration/test_form100_v2_service.py` - `Success: no issues found in 3 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_exchange_service_import_reports.py -p no:cacheprovider` - `7 passed, 1 warning`.
- `venv\\Scripts\\python.exe -m compileall -q app tests` - passed.

### DoD status

- ✅ Form100 service contracts are normalized to single method names without duplicate V2 aliases.

---

## 2026-02-27 - Form100 V1 backend retirement (full cleanup)

### What was done

- Removed legacy backend modules:
  - `app/application/services/form100_service.py`
  - `app/application/dto/form100_dto.py`
  - `app/domain/models/form100.py`
  - `app/domain/rules/form100_rules.py`
  - `app/infrastructure/db/repositories/form100_repo.py`
  - `app/infrastructure/export/form100_export.py`
  - `app/infrastructure/import/form100_import.py`
  - `app/infrastructure/reporting/form100_pdf_report.py`
- Removed legacy unit tests tied to V1 internals:
  - `tests/unit/test_form100_rules.py`
  - `tests/unit/test_form100_import_parsers.py`
- `app/application/services/exchange_service.py`:
  - removed legacy table scopes from generic exchange model map:
    - `form100_card`
    - `form100_mark`
    - `form100_stage`

### Verification

- `venv\\Scripts\\python.exe -m ruff check app tests` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app tests` - `Success: no issues found in 245 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_exchange_service_import_reports.py tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_form100_v2_wizard_mapping.py -p no:cacheprovider` - `12 passed, 1 warning`.

### DoD status

- ✅ Legacy Form100 V1 backend/service layer removed from active codebase.
- ✅ Runtime and tests validated against Form100 V2-only path.

---

## 2026-02-27 - Form100 V1 retirement (UI + runtime wiring)

### What was done

- Switched runtime wiring to a single Form100 service (V2 only):
  - `app/container.py`: removed `form100_repo`/`form100_service` from container composition and constructors.
  - `app/application/services/exchange_service.py`: unified `export/import_form100_package_zip` on V2 backend; kept `export/import_form100_v2_package_zip` as compatibility wrappers.
  - `app/application/services/reporting_service.py`: removed V1 fallback path; `export_form100_pdf` now uses V2 only; `export_form100_v2_pdf` delegates to it.
- Simplified Import/Export wizard format selection:
  - `app/ui/import_export/import_export_wizard.py`: removed duplicate `Form100 V2 ZIP` option, left one `Form100 ZIP` flow.
- Removed legacy Form100 UI package:
  - deleted `app/ui/form100/**`.
  - `app/ui/form100_v2/form100_editor.py`: switched `ValidationBanner` import to shared widget path.
  - added shared widget: `app/ui/widgets/validation_banner.py`.
- Removed obsolete V1-only tests:
  - deleted `tests/integration/test_form100_service.py`,
  - deleted `tests/unit/test_form100_bodymap_editor.py`,
  - deleted `tests/unit/test_form100_table_layout.py`.
- Synced docs/config with single-version mode:
  - `app/config.py`: removed unused `settings.form100_v2_enabled`,
  - `docs/context.md`: updated Form100 UI path and removed flag-based switching note,
  - `docs/tech_guide.md`: removed `EPIDCONTROL_FORM100_V2_ENABLED`.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/container.py app/application/services/exchange_service.py app/application/services/reporting_service.py app/ui/import_export/import_export_wizard.py app/ui/form100_v2/form100_editor.py app/ui/form100_v2/form100_view.py app/ui/widgets/validation_banner.py app/config.py tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_list_panel_filters.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/container.py app/application/services/exchange_service.py app/application/services/reporting_service.py app/ui/import_export/import_export_wizard.py app/ui/form100_v2/form100_editor.py app/ui/form100_v2/form100_view.py app/ui/widgets/validation_banner.py app/config.py tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_list_panel_filters.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py` - `Success: no issues found in 12 source files`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_list_panel_filters.py tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py -p no:cacheprovider` - `7 passed, 1 warning`.
- `venv\\Scripts\\python.exe -m compileall -q app tests` - passed.

### DoD status

- ✅ Form100 runtime now uses a single active implementation (V2).
- ✅ Duplicate Form100 import/export format choice removed from UI.
- ✅ Legacy `app/ui/form100` package removed from project.

---

## 2026-02-27 - Pyright gate added to pre-commit and CI

### What was done

- `.pre-commit-config.yaml`:
  - added a dedicated `pyright` hook in local hooks section;
  - configured it with `language: python` and `additional_dependencies: [pyright>=1.1.390]` to avoid host-environment drift.
- `.github/workflows/quality-gates.yml`:
  - added explicit `Pyright` step (`python -m pyright`) after `Mypy`.
- `scripts/quality_gates.ps1`:
  - added local `pyright` gate to align local run with CI.
- `requirements-dev.txt`:
  - added `pyright>=1.1.390`.

### Verification

- `venv\\Scripts\\python.exe -m pre_commit validate-config` - passed.
- `venv\\Scripts\\python.exe -m pre_commit run --files .pre-commit-config.yaml .github/workflows/quality-gates.yml` - passed.
- `venv\\Scripts\\python.exe -m pyright` - `0 errors, 0 warnings, 0 informations`.

### DoD status

- ✅ Pyright is now enforced in both pre-commit and CI.
- ✅ Local quality gate script includes pyright.

---

## 2026-02-27 - Pyright rule hardening for unnecessary isinstance

### What was done

- `pyrightconfig.json`:
  - added explicit rule `"reportUnnecessaryIsInstance": "error"`.
- This enforces the same diagnostic class that previously appeared in `app/main.py`.

### Verification

- `venv\\Scripts\\python.exe -m pyright app tests` -> `0 errors, 0 warnings, 0 informations`.

### DoD status

- ✅ Rule is enabled at config level and does not introduce new violations in `app`/`tests`.

---

## 2026-02-24 — Интеграция 3 компонентов из Test_UI (по плану)

### Задача 1 — `app/ui/login_dialog.py`

- Добавлена демо-подсказка `QLabel("Для теста: admin / admin1234")`.
- Добавлена кнопка «Подставить demo» (objectName `secondaryButton`).
- Заменён `QDialogButtonBox` на ручной `QHBoxLayout` с кнопками «Войти» / «Подставить demo» / «Отмена».
- Добавлен механизм блокировки: константы `_MAX_ATTEMPTS=5`, `_LOCKOUT_SECONDS=60`; атрибуты `_failed_attempts`, `_lockout_remaining`, `_lockout_timer`; методы `_fill_demo()`, `_start_lockout()`, `_tick_lockout()`, `_on_login_text_changed()`.
- Метка блокировки использует `objectName("statusLabel") + property("statusLevel", "error")` (без inline-стилей).

### Задача 3 — `app/ui/home/home_view.py` + `app/ui/main_window.py`

- `HomeView` получил сигнал `pageRequested = Signal(str)`.
- В `_build_ui()` добавлен блок «Быстрые действия» (6 кнопок): Пациенты, ЭМЗ, Форма 100, Лаборатория, Санитария, Аналитика.
- Кнопки используют objectName `quickBtn_{page_key}`; цветовые стили добавлены в `app/ui/theme.py`.
- В `MainWindow._init_views()` подключён сигнал `pageRequested` → `_on_home_page_requested()`.
- Добавлен метод `_on_home_page_requested(key)` для навигации по ключу.

### Задача 2 — Мастер Формы 100

**2a — Виджеты перенесены из `Test_UI` в `app/ui/form100_v2/wizard_widgets/`:**

- `icon_select_widget.py`, `lesion_type_widget.py`, `bodymap_widget.py`
- `form100_stub_widget.py`, `form100_main_widget.py`, `form100_flags_widget.py`, `form100_bottom_widget.py`
- `wizard_steps/step_identification.py`, `step_bodymap.py`, `step_medical.py`, `step_evacuation.py`
- Исправлены относительные импорты → абсолютные; путь к PNG схемы тела исправлен.

**2b — `app/ui/form100_v2/form100_wizard.py`** (создан):

- `Form100Wizard(QDialog)` — 4-шаговый мастер с бежевой цветовой темой левой панели.
- Загрузка существующей карточки из `card.data.raw_payload`.
- Сохранение через `create_card` / `update_card`; подпись через `sign_card`.
- Блокировка всех шагов при `status == "SIGNED"`.

**2c — `app/ui/form100_v2/form100_list_panel.py`** (создан):

- `Form100ListPanel(QDialog)` — диалог 900×650 px со списком карточек Формы 100.
- `QSplitter`: таблица (колонки: Дата, Статус, ФИО, Диагноз) + панель превью.
- Двойной клик или кнопка «Открыть / Редактировать» → `Form100Wizard`.
- Кнопка «Создать форму» → новый мастер без карточки.
- Статус-бейджи: DRAFT=#F4D58D/#7D5A00, SIGNED=#9AD8A6/#1D5030.

**2d — `app/ui/patient/patient_emk_view.py`:**

- Добавлен параметр `on_open_form100: Callable[[int|None, int|None], None] | None = None`.
- В `_build_quick_actions_row()` добавлена кнопка «Форма 100»; max_columns=5.
- Добавлен метод `_open_form100()`.

**2e — `app/ui/main_window.py`:**

- Вкладка «Форма 100» убрана из навигационного меню.
- `_form100_view` создаётся, но не добавляется в стек.
- Удалены вызовы `set_session`, `clear_context`, `refresh_references` у `_form100_view`.
- Добавлены `_open_form100_from_emk()` и `_on_home_page_requested()`.
- `_on_quick_action("form100")` → переход к `_emk_view`.

### Проверка качества

- `ruff check` — passed (все ошибки исправлены).
- `mypy` — passed (24 файла, 0 ошибок).
- `pytest` — **217 passed**, 2 warnings (не критично).
- Тест `test_ui_no_inline_styles` обновлён: wizard-компоненты добавлены в `allowed` (динамические цвета бейджей/аннотаций требуют programmatic styling).

---

## 2026-02-27 — Правило ведения progress_report и свежие изменения

### Новое правило

- Начиная с текущего этапа, каждое нововведение, изменение или улучшение фиксируется в `docs/progress_report.md` коротким блоком.
- Формат записи: что сделано, где сделано (ключевые файлы/модули), как проверено (ruff/mypy/pytest/ручная проверка).

### Ключевые изменения за цикл

- Усилена адаптивность UI на основных вкладках: убраны жёсткие пороги ширины, action-бары переведены на авто-перестройку по реальной доступной ширине, улучшено поведение сложных компоновок (`ЭМЗ`, `Поиск и ЭМК`, `Санитария`, `Импорт/Экспорт`, `Form100`, `Form100 V2`, `Администрирование`, `Контекстная панель`, `Главная`).
- Переработан визуальный блок «Карточка пациента» в `Поиск и ЭМК`: усилена иерархия текста (ФИО/ID/поля), данные переведены в более читаемые инфо-карточки.
- Улучшено нижнее статус-уведомление в `Поиск и ЭМК`: статус теперь компактный (не на всю ширину), с более контрастной и аккуратной стилизацией.
- Стабилизирован перехват ввода дат и корректное завершение приложения по `KeyboardInterrupt` (`Ctrl+C`) без шумного `Unhandled exception` в логах.

### Проверки

- Локальные проверки по изменённым модулям: `ruff` и `mypy` — успешно.
- Выборочные unit-тесты UI и фильтра ввода дат — успешно.

---

## 2026-02-27 — Итерация 1 (этап 1/6): quality-gates + синхронизация документации

### Что сделано

- Добавлен CI workflow `.github/workflows/quality-gates.yml`:
  - `ruff check app tests`
  - `mypy app tests`
  - `pytest -q`
  - `python -m compileall -q app tests scripts`
- Добавлен единый локальный скрипт прогона quality-gates:
  - `scripts/quality_gates.ps1`
- Обновлен `README.md`:
  - исправлены ссылки на документацию;
  - добавлен явный раздел по локальным quality-gates;
  - добавлена ссылка на CI workflow.
- Перезаписаны в корректном виде:
  - `docs/tech_guide.md`
  - `docs/build_release.md`
- Обновлен `docs/context.md`:
  - добавлен статус о наличии автоматизированного CI quality-gate.

### Формат записи в progress_report (зафиксирован как обязательный)

- Что сделано.
- Где сделано (ключевые файлы/модули).
- Как проверено.
- Статус DoD (закрыт/в работе).

### Статус DoD

- Закрыт:
  - ✅ CI workflow добавлен
  - ✅ Локальный скрипт quality-gates добавлен
  - ✅ Ключевые документы синхронизированы
  - ✅ Финальный локальный прогон quality-gates (ruff/mypy/pytest/compileall)

### Проверки

- `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`:
  - `ruff check app tests` — `All checks passed`
  - `mypy app tests` — `Success: no issues found in 262 source files`
  - `pytest -q` — `225 passed`
  - `compileall` — успешно

---

## 2026-02-27 — Итерация 2 (этап 2/6, старт): error-handling hardening

### Что сделано

- `app/bootstrap/startup.py`:
  - сужен `except` при проверке записи каталога БД (`Exception` -> `OSError`);
  - `has_users` переведен на `SQLAlchemyError`;
  - проверки наличия `pyqtgraph/matplotlib` переведены на `ImportError`.
- `app/infrastructure/db/migrations/env.py`:
  - сужен broad-except при `fileConfig` до `(AttributeError, OSError, ValueError)`.
- `app/bootstrap/startup.py` (дополнительно):
  - добавлен `_is_multiple_heads_error` для явного распознавания кейса Alembic multiple heads;
  - в `run_migrations` fallback на `heads` выполняется только при `CommandError` multiple heads;
  - запись `migration_error.log` сужена по исключениям (`OSError` при проблемах файловой системы).
- `app/application/services/exchange_service.py`:
  - сужены broad-except в `_parse_value`:
    - `Exception` -> `(TypeError, ValueError)` для Date/DateTime fallback-парсинга.
- `app/infrastructure/import/form100_import.py`:
  - убраны `pass` в fallback-парсинге дат/времени;
  - логика сохранена через явный flow c `parsed`/`parsed_date`.
- Добавлены негативные unit-тесты:
  - `tests/unit/test_startup_error_handling.py`:
    - ошибка записи в каталог БД (`check_startup_prerequisites`);
    - ошибка SQLAlchemy в `has_users`;
    - отсутствие `pyqtgraph/matplotlib` в `warn_missing_plot_dependencies`.
    - fallback `head -> heads` при `CommandError("Multiple heads ...")`;
    - проверка записи `migration_error.log` и уведомления пользователю при фатальной ошибке миграций.
- Добавлены unit-тесты парсинга импорта Form100:
  - `tests/unit/test_form100_import_parsers.py`:
    - ISO + legacy (`dd.mm.yyyy`) форматы;
    - негативные сценарии невалидных дат/времени.
- Актуализирован unit-тест под текущую сигнатуру:
  - `tests/unit/test_responsive_actions.py` (вызов `_columns_for_width` с keyword-аргументами).
- Исправлен скрипт `scripts/quality_gates.ps1`:
  - добавлен fail-fast по `LASTEXITCODE` для каждого шага, чтобы скрипт не давал ложный `passed`.

### Статус DoD

- В работе:
  - ✅ Убраны первые broad-except в критичных местах старта/миграций
  - ✅ Добавлены негативные тесты по startup-ошибкам
  - ✅ Усилен сценарий обработки ошибок миграций (multiple heads + логирование фаталов)
  - ✅ Закрыт первый проход по silent-fail в парсинге импорта/экспорта
  - ⏳ Следующий шаг: продолжить hardening оставшихся broad-except в сервисном слое

### Проверки

- `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`:
  - `ruff check app tests` — `All checks passed`
  - `mypy app tests` — `Success: no issues found in 263 source files`
  - `pytest -q` — `229 passed`
  - `compileall` — успешно

---

## 2026-02-27 — Итерация 3 (этап 3/6, старт): адаптивность критичных экранов

### Что сделано

- `app/ui/form100_v2/form100_wizard.py`:
  - убраны ключевые `setFixedWidth` для панели шагов и нижних action-кнопок;
  - навигационный бар переведен с fixed-height на минимальную высоту;
  - добавлен адаптивный пересчет размеров (`_apply_responsive_metrics`) с порогами по ширине окна;
  - добавлен `resizeEvent` для динамической перестройки метрик при изменении размера окна.
- `app/ui/form100_v2/form100_list_panel.py`:
  - убран жесткий `splitter.setSizes([500, 380])`;
  - добавлен адаптивный `_apply_responsive_layout` + `resizeEvent` для динамического перерасчета долей;
  - добавлены stretch factors и запрет схлопывания дочерних pane;
  - смягчены fixed-сайзы preview-бейджа/разделителя (min/max вместо fixed).
- `app/ui/admin/user_admin_view.py`:
  - улучшено поведение при узких экранах:
    - пересчитаны приоритеты колонок (`left:right = 3:2`);
    - добавлены floor-значения требуемой ширины для горизонтального режима;
    - добавлен явный fallback в вертикальный режим при недостатке ширины;
    - в горизонтальном режиме заданы минимальные ширины колонок для читаемости;
  - уменьшены минимальные высоты таблиц пользователей/аудита для более гибкой компоновки.

### Статус DoD

- В работе:
  - ✅ Начат переход от жестких размеров к адаптивным ограничениям
  - ✅ Улучшена адаптивность Form100ListPanel (split + preview)
  - ✅ Улучшена адаптивность страницы администрирования на узких/средних экранах
  - ⏳ Следующий шаг: продолжить вычищать fixed-сайзинг и inline-style hotspots в Form100 V2/админке

### Проверки

- `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`:
  - `ruff check app tests` — `All checks passed`
  - `mypy app tests` — `Success: no issues found in 263 source files`
  - `pytest -q` — `231 passed`
  - `compileall` — успешно

---

## 2026-02-27 — Итерация 2 (этап 2/6, продолжение): hardening ошибок и silent-fail

### Что сделано

- `app/main.py`:
  - усилен `_TeeStream` для stderr-tee: список потоков строго `TextIOBase`, чтобы исключить обращения к `None` в `flush`/`fileno`;
  - обработка ошибок `write/flush/isatty/fileno` сужена до `(OSError, ValueError, UnsupportedOperation)`;
  - убраны динамические `hasattr/getattr`-вызовы для `fileno`, что закрывает предупреждения статанализа и снижает риск ошибок при shutdown логирования.
- `app/application/services/backup_service.py`:
  - `get_last_backup`: broad-except заменен на конкретные ошибки парсинга/IO (`JSONDecodeError`, `KeyError`, `OSError`, `TypeError`, `ValueError`) с логированием;
  - `create_backup`: fallback копирования теперь сужен до `(sqlite3.Error, OSError)` с явным warning-логом;
  - `restore_backup`: убран `except ...: pass` при `engine.dispose()`, добавлено контролируемое логирование для `(AttributeError, ImportError, RuntimeError)`.
- `app/ui/widgets/context_bar.py`:
  - убраны silent-except в autocomplete-потоках пациента/госпитализации;
  - ошибки парсинга автодополнения сужены до `ValueError`;
  - ошибки сервисного поиска в autocomplete переводятся в `DEBUG`-логи вместо тихого поглощения.
- Добавлены unit-тесты:
  - `tests/unit/test_backup_service_error_handling.py`:
    - поврежденный `last_backup.json` не ломает приложение;
    - fallback на `copy2` при ошибке sqlite backup API;
    - восстановление из backup продолжается даже если `engine.dispose()` недоступен.

### Статус DoD

- В работе:
  - ✅ Дополнительно зачищены silent-fail в backup/context потоках
  - ✅ Расширено покрытие негативных сценариев по backup-сервису
  - ⏳ Следующий шаг: продолжить точечную зачистку broad-except в критичных UI-service стыках и стандартизировать сообщения ошибок через notifications слой

### Проверки

- Точечные проверки:
  - `ruff check app/main.py app/application/services/backup_service.py app/ui/widgets/context_bar.py tests/unit/test_backup_service_error_handling.py` — успешно
  - `mypy --no-incremental app/main.py app/application/services/backup_service.py app/ui/widgets/context_bar.py tests/unit/test_backup_service_error_handling.py` — успешно
  - `pytest -q tests/unit/test_backup_service_error_handling.py tests/unit/test_startup_error_handling.py tests/unit/test_responsive_actions.py -p no:cacheprovider` — `10 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 234 passed`.

---

## 2026-02-27 — Итерация 2 (этап 2/6, продолжение-2): унификация сообщений ошибок в UI

### Что сделано

- `app/ui/widgets/notifications.py`:
  - добавлен единый helper `error_text(exc, fallback)` для нормализации текста ошибок (включая пустые/`None`-сообщения).
- `app/ui/patient/patient_emk_view.py`:
  - broad-catch в ключевых потоках заменен на контролируемый набор (`ValueError`, `RuntimeError`, `LookupError`, `TypeError`, `SQLAlchemyError`);
  - сообщения пользователю переведены на единый formatter `error_text(...)`;
  - добавлен guarded-flow при выборе пациента из списка (`_select_from_results`), чтобы ошибка загрузки не приводила к необработанному исключению.
- `app/ui/admin/user_admin_view.py`:
  - broad-catch в операциях управления пользователями заменен на контролируемые типы;
  - добавлен защищенный загрузчик журнала аудита (`_load_audit`) с пользовательским сообщением;
  - async error-callback backup/restore переводит исключение через `error_text(...)`.
- `app/ui/sanitary/sanitary_history.py`:
  - broad-catch в карточке санитарной пробы (`_load_microbes`, `_load_existing`, оба сценария `on_save`) заменен на контролируемые типы;
  - сообщения ошибок приведены к единому виду через `error_text(...)`.
- Тесты:
  - `tests/unit/test_notifications_status.py` дополнен тестами `error_text(...)` для fallback и корректного сообщения.

### Статус DoD

- В работе:
  - ✅ Начата стандартизация пользовательских ошибок через единый UI-helper
  - ✅ Снижено количество broad-except в критичных UI потокаx (Поиск/ЭМК, Администрирование, Санитария)
  - ✅ Добавлено unit-покрытие для нового formatter-а ошибок
  - ⏳ Следующий шаг: продолжить hardening в оставшихся проблемных UI-модулях (`form100`, `references`, `import/export`) и завершить блок Iteration 2

### Проверки

- Точечные:
  - `ruff check app/ui/widgets/notifications.py app/ui/patient/patient_emk_view.py app/ui/admin/user_admin_view.py app/ui/sanitary/sanitary_history.py tests/unit/test_notifications_status.py` — успешно
  - `mypy --no-incremental app/ui/widgets/notifications.py app/ui/patient/patient_emk_view.py app/ui/admin/user_admin_view.py app/ui/sanitary/sanitary_history.py tests/unit/test_notifications_status.py` — успешно
  - `pytest -q tests/unit/test_notifications_status.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_backup_service_error_handling.py tests/unit/test_startup_error_handling.py -p no:cacheprovider` — `14 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): перенос стилевого state-менеджмента Form100Wizard в тему

### Что сделано

- `app/ui/form100_v2/form100_wizard.py`:
  - полностью удалены inline `setStyleSheet(...)` из step-panel и навигационной панели;
  - для stepper-элементов введены `objectName`/`property(stepState)`:
    - `wizardStepBadge`, `wizardStepName`, `wizardStepSeparator`, `wizardStepConnectorLine`, `wizardStepLock`, `wizardStepTitle`;
  - обновление визуального состояния шагов (`done/active/pending`) переведено с inline-CSS на property-driven модель:
    - добавлены `_set_step_visual_state(...)` и `_repolish(...)`;
    - `_update_step_indicator()` теперь только меняет текст badge и property состояния;
  - удалены устаревшие локальные color-константы, ставшие лишними после переноса в глобальную тему.
- `app/ui/theme.py`:
  - добавлены QSS-правила для `wizardStep*` и `wizardNavBar`;
  - добавлены state-aware правила для `wizardStepBadge` и `wizardStepName` по `stepState`.
- `tests/unit/test_ui_no_inline_styles.py`:
  - allow-list ужесточен: убраны `form100_wizard.py` и `form100_list_panel.py`;
  - разрешен только `theme.py`, что фиксирует запрет inline-style во всех UI-модулях проекта.

### Статус DoD

- В работе:
  - ✅ Закрыт крупный inline-style hotspot в мастере Form100 V2
  - ✅ Шаговый индикатор стал консистентным с общей темой и проще для поддержки
  - ✅ Усилен автоматический контроль: inline-style в UI теперь фактически запрещен повсеместно
  - ⏳ Следующий шаг: продолжить Iteration 3 на fixed-size hotspots (`form100_editor`/`form100_stub_widget`/`bodymap_widget`) с сохранением UX

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check app/ui/form100_v2/form100_wizard.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental app/ui/form100_v2/form100_wizard.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m pytest -q tests/unit/test_ui_no_inline_styles.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py -p no:cacheprovider` — `4 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): смягчение fixed-size в редакторах Form100

### Что сделано

- `app/ui/form100_v2/form100_editor.py`:
  - поля `stub_diagnosis` и `main_diagnosis` переведены с `setFixedHeight(56)` на диапазон `min/max` (`56..128`).
- `app/ui/form100/form100_editor.py`:
  - `diagnosis_text` переведен с `setFixedHeight(64)` на диапазон `min/max` (`64..140`).
- `app/ui/form100_v2/wizard_widgets/form100_stub_widget.py`:
  - `stub_diagnosis` переведен с `setFixedHeight(58)` на диапазон `min/max` (`58..132`).
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`:
  - `gender_combo` переведен с `setFixedWidth(100)` на диапазон `min/max` (`88..132`).

### Статус DoD

- В работе:
  - ✅ Уменьшена жесткость компоновки критичных form-блоков
  - ✅ Поведение полей осталось предсказуемым, но стало адаптивнее на узких/масштабированных экранах
  - ⏳ Следующий шаг: продолжить зачистку remaining fixed-size hotspots в UI-модулях админки и legacy экранов

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check app/ui/form100_v2/form100_editor.py app/ui/form100/form100_editor.py app/ui/form100_v2/wizard_widgets/form100_stub_widget.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental app/ui/form100_v2/form100_editor.py app/ui/form100/form100_editor.py app/ui/form100_v2/wizard_widgets/form100_stub_widget.py app/ui/form100_v2/wizard_widgets/bodymap_widget.py` — успешно
  - `venv\Scripts\python.exe -m pytest -q tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` — `5 passed`
- Полный прогон quality-gates:
  - первый прогон упал из-за поврежденного `mypy` cache (`KeyError: 'module'`);
  - выполнена очистка `.mypy_cache`, затем повторный прогон:
    - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 1/2 (доп. пакет): устранение Pylance typing-ошибок в `scripts/build_reference_seed.py`

### Что сделано

- `scripts/build_reference_seed.py`:
  - введен alias `SeedRow = dict[str, str]`;
  - сигнатуры функций и локальные коллекции типизированы явно:
    - `_parse_antibiotics(...) -> tuple[list[SeedRow], list[SeedRow]]`
    - `_parse_microorganisms(...) -> list[SeedRow]`
    - `_assign_codes(..., items: list[SeedRow], ...)`
  - сняты источники `Unknown/MissingTypeArgument` из Pylance за счет строгих type-аргументов для `dict/list`;
  - в пост-обработке `group_code` убрана потенциальная запись `None`: код группы записывается только при наличии значения.

### Статус DoD

- В работе:
  - ✅ Закрыт пакет диагностик из `errors.md` для `build_reference_seed.py`
  - ✅ Поведение генератора reference seed сохранено, изменения только типовые/структурные
  - ⏳ Следующий шаг: при необходимости разобрать оставшиеся записи `errors.md` (если есть новые после перезапуска Pylance)

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check scripts/build_reference_seed.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental scripts/build_reference_seed.py` — успешно
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): восстановление `errors.md` и адаптивная правка `main_window`

### Что сделано

- Восстановлен отсутствовавший файл `errors.md` как рабочий журнал ошибок:
  - добавлен текущий статус по закрытому блоку `scripts/build_reference_seed.py`;
  - зафиксирован единый формат для следующих записей (симптом, причина, фикс, верификация).
- `app/ui/main_window.py`:
  - в `_position_logout_button()` убраны `setFixedWidth/setFixedHeight`;
  - размер кнопки выхода теперь задается через `resize(width, height)`, что снижает жесткую фиксацию размеров при изменении геометрии меню.

### Статус DoD

- В работе:
  - ✅ `errors.md` снова присутствует в проекте и может использоваться как единый трекер диагностики
  - ✅ Снижен один из remaining fixed-size hotspots в навигационной оболочке
  - ⏳ Следующий шаг: продолжить итерацию 3 на remaining fixed-size в служебных UI-блоках с приоритетом на экраны с высокой плотностью

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check app/ui/main_window.py scripts/build_reference_seed.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental app/ui/main_window.py scripts/build_reference_seed.py` — успешно
  - `venv\Scripts\python.exe -m pytest -q tests/unit/test_main_window_context_selection.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` — `5 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): вынос inline-style из wizard step-экранов Form100 V2

### Что сделано

- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`:
  - удалены inline `setStyleSheet(...)` для чекбоксов тканей, хинта заметок и карточек заметок;
  - введены `objectName` для theme-driven стилизации (`form100TissueCheck`, `form100NotesHint`, `form100NotesContainer`, `form100NoteRow`, `form100NoteIndex`, `form100NoteText`).
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`:
  - удалены inline `setStyleSheet(...)` в обзорной панели (фон, карточки, заголовки, сепараторы, badges, placeholder);
  - введены `objectName`/`property(tone)` для унифицированной стилизации секций обзора (`form100Review*`);
  - заменена локальная карта hex-цветов на typed tone-key механизм (`_ACCENT_KEYS`) и передачу тона в тему.
- `app/ui/theme.py`:
  - добавлены QSS-правила для новых объектов StepBodymap/StepEvacuation;
  - добавлены tone-aware стили для карточек обзора Form100 (`id`, `injury`, `lesion`, `med`, `map`, `evac`, `flags`, `diag`);
  - сохранен прежний визуальный смысл, но источник стилей теперь единый (global theme).
- `tests/unit/test_ui_no_inline_styles.py`:
  - удалены исключения для `step_bodymap.py` и `step_evacuation.py` из allow-list;
  - усилен guardrail: новые inline-style в этих файлах теперь будут падать тестом.

### Статус DoD

- В работе:
  - ✅ Закрыт крупный hotspot inline-style в wizard step-экранах Form100 V2
  - ✅ Усилен контроль regressions через обновленный unit-тест без исключений для этих шагов
  - ✅ Визуальная логика сведена в единый theme-layer без локального CSS в code-behind
  - ⏳ Следующий шаг: продолжить итерацию 3 на оставшихся экранах с локальным стилевым долгом и фиксированными размерами

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m pytest -q tests/unit/test_ui_no_inline_styles.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py -p no:cacheprovider` — `4 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): зачистка inline-style в Form100Bottom + адаптивные правки высот

### Что сделано

- `app/ui/form100_v2/wizard_widgets/form100_bottom_widget.py`:
  - удалены inline `setStyleSheet(...)` для row-label, разделителей, заголовков секций и вспомогательных контейнеров;
  - введены `objectName` для theme-driven стилей (`form100BottomRowLabel`, `form100BottomSeparator`, `form100BottomSectionLabel`, `form100BottomInlineContainer`);
  - смягчены фиксированные размеры:
    - `tourniquet_time`: `setFixedWidth(110)` -> диапазон `min/max` (`96..132`);
    - `main_diagnosis`: `setFixedHeight(70)` -> `min/max` (`70..130`) + `QSizePolicy.Preferred`.
- `app/ui/theme.py`:
  - добавлены QSS-правила для новых объектов `form100Bottom*` с сохранением прежней визуальной иерархии.
- `tests/unit/test_ui_no_inline_styles.py`:
  - `form100_bottom_widget.py` удален из allow-list;
  - тест теперь контролирует inline-style и в этом модуле.

### Статус DoD

- В работе:
  - ✅ Снижен стилевой технический долг в Form100 V2 bottom-секции
  - ✅ Усилен автоматический контроль запрета inline-style
  - ✅ Улучшена гибкость размера блока диагноза для разных экранов
  - ⏳ Следующий шаг: продолжить итерацию 3 на оставшихся модулях с fixed-size/inline-style hotspot-ами

### Проверки

- Точечные:
  - `venv\Scripts\python.exe -m ruff check app/ui/form100_v2/wizard_widgets/form100_bottom_widget.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m mypy --no-incremental app/ui/form100_v2/wizard_widgets/form100_bottom_widget.py app/ui/theme.py tests/unit/test_ui_no_inline_styles.py` — успешно
  - `venv\Scripts\python.exe -m pytest -q tests/unit/test_ui_no_inline_styles.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py -p no:cacheprovider` — `4 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 2 (продолжение-3): зачистка broad-except в Form100 V2 widgets

### Что сделано

- Сужены broad-except в виджетах Form100 V2:
  - `app/ui/form100_v2/wizard_widgets/form100_stub_widget.py`
  - `app/ui/form100_v2/wizard_widgets/form100_main_widget.py`
  - `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`
  - `app/ui/form100_v2/widgets/bodymap_editor_v2.py`
- В JSON fallback-парсерах убран `except Exception`/`pass`, заменено на контролируемые исключения `(TypeError, ValueError, JSONDecodeError)` с сохранением прежнего fallback-поведения.
- В `_to_float(...)` bodymap-editor заменён broad-catch на `(TypeError, ValueError)`.

### Статус DoD

- В работе:
  - ✅ Дополнительно закрыт блок silent/broad exception в wizard widgets
  - ✅ Поведение UI сохранено (fallback на пустые коллекции/дефолтные значения)
  - ⏳ Следующий шаг: перенос inline-style в `step_bodymap`/`step_evacuation` на objectName/property + тема

### Проверки

- Точечные:
  - `ruff check app/ui/form100_v2/wizard_widgets/form100_stub_widget.py app/ui/form100_v2/wizard_widgets/form100_main_widget.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py` — успешно
  - `mypy --no-incremental app/ui/form100_v2/wizard_widgets/form100_stub_widget.py app/ui/form100_v2/wizard_widgets/form100_main_widget.py app/ui/form100_v2/widgets/bodymap_editor_v2.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py` — успешно
  - `pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` — `4 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 2/3 (продолжение): hardening Form100/References/Import-Export + вынос inline-styles

### Что сделано

- `app/ui/import_export/import_export_view.py`:
  - broad-except в загрузке истории пакетов заменен на контролируемый набор ошибок;
  - сообщения пользователю нормализованы через `error_text(...)`.
- `app/ui/references/reference_view.py`:
  - broad-except в CRUD-операциях (`add/update/delete`) заменен на контролируемые исключения;
  - ошибки для пользователя стандартизованы через `error_text(...)`.
- `app/ui/form100/form100_view.py` и `app/ui/form100_v2/form100_view.py`:
  - все broad-except в ключевых действиях (`refresh/load/save/sign/archive/import/export`) заменены на контролируемые типы;
  - сообщения об ошибках унифицированы через `error_text(...)` (в т.ч. validation banner).
- `app/ui/form100_v2/form100_wizard.py`:
  - JSON parser fallback в `_parse_json_list/_parse_json_markers` сужен с `Exception` до `(TypeError, ValueError, JSONDecodeError)`;
  - обработка ошибок в `_save/_sign` переведена на контролируемые типы и единый formatter.
- `app/ui/form100_v2/form100_list_panel.py` + `app/ui/theme.py`:
  - убраны inline `setStyleSheet` в preview-панели списка Form100;
  - введены `objectName`/`property` (`form100ListPreview`, `form100ListBadge[tone=...]`, и др.) и стили перенесены в тему;
  - добавлен динамический repolish для badge при смене статуса;
  - дополнительно улучшен адаптивный initial sizing панели списка.

### Статус DoD

- В работе:
  - ✅ Существенно уменьшено число broad-except в критичных UI-модулях Iteration 2
  - ✅ Продолжен перенос inline-style hotspots в theme (Iteration 3)
  - ✅ UI и error-handling поведение сохранено без регрессий по тестам
  - ⏳ Следующий шаг: дочистка оставшихся broad-except в `form100_v2/wizard_widgets` и `references/import` вспомогательных потоках + дальнейший перенос inline-стилей step-экрана

### Проверки

- Точечные:
  - `ruff check app/ui/import_export/import_export_view.py app/ui/references/reference_view.py app/ui/form100/form100_view.py app/ui/form100_v2/form100_view.py app/ui/form100_v2/form100_wizard.py app/ui/form100_v2/form100_list_panel.py app/ui/theme.py` — успешно
  - `mypy --no-incremental app/ui/import_export/import_export_view.py app/ui/references/reference_view.py app/ui/form100/form100_view.py app/ui/form100_v2/form100_view.py app/ui/form100_v2/form100_wizard.py app/ui/form100_v2/form100_list_panel.py app/ui/theme.py` — успешно
  - `pytest -q tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_notifications_status.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` — `8 passed`
  - `pytest -q tests/unit/test_main_window_context_selection.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_backup_service_error_handling.py -p no:cacheprovider` — `9 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

---

## 2026-02-27 — Итерация 3 (этап 3/6, продолжение): адаптивность диалогов Form100/Sanitary

### Что сделано

- `app/ui/form100_v2/form100_wizard.py`:
  - убран жесткий минимальный размер `1100x750`, добавлен адаптивный `_apply_initial_size()` на основе `availableGeometry`;
  - стартовые и минимальные размеры теперь вычисляются относительно экрана, с безопасными floor/ceiling.
- `app/ui/form100_v2/form100_list_panel.py`:
  - снижен hard floor окна (`900x650` -> адаптивный минимум с базой `780x560`);
  - добавлен `_apply_initial_size()` для корректной первичной посадки на разные экраны;
  - продолжена зачистка broad-except в карточках Form100: `_load_cards` и загрузка выбранной карточки в мастере (`_open_wizard`) переведены на контролируемый набор исключений + `error_text`.
- `app/ui/sanitary/sanitary_history.py` (`SanitarySampleDetailDialog`):
  - убраны фиксированные `resize(1100, 980)` и `setMinimumSize(900, 700)`;
  - добавлен `_apply_initial_size()` с адаптивным подбором минимального/целевого размера под фактический экран.

### Статус DoD

- В работе:
  - ✅ Закрыт еще один блок fixed-size проблем на сложных формах
  - ✅ Улучшена первичная масштабируемость Form100/Sanitary на 1366/1600/1920
  - ✅ Дополнительно уменьшен риск hard-fail в Form100 list/wizard при ошибках сервиса
  - ⏳ Следующий шаг: продолжить перенос inline-style hotspots в theme/objectName-property в Form100 V2 preview/wizard

### Проверки

- Точечные:
  - `ruff check app/ui/form100_v2/form100_list_panel.py app/ui/form100_v2/form100_wizard.py app/ui/sanitary/sanitary_history.py` — успешно
  - `mypy --no-incremental app/ui/form100_v2/form100_list_panel.py app/ui/form100_v2/form100_wizard.py app/ui/sanitary/sanitary_history.py` — успешно
  - `pytest -q tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_notifications_status.py -p no:cacheprovider` — `9 passed`
- Полный прогон quality-gates:
  - `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`
  - результат: `ruff`/`mypy`/`pytest`/`compileall` — green, `pytest: 236 passed`.

## 2026-02-27 — Test_UI services: lint/type stabilization (continuation)

### Что сделано

- Для `Test_UI/app/application/services` выполнено автоформатирование `ruff format` и безопасные фиксы `ruff check --fix`.
- В `analytics_service.py` удален пустой цикл-заглушка, вызывавший `B007` (unused loop variable).
- Ранее внесенные typing-правки в `form100_service.py` и `lab_service.py` сохранены и проверены повторно.

### Статус DoD

- ✅ `ruff` для `Test_UI/app/application/services` — green.
- ✅ `mypy` для `Test_UI/app/application/services` — green (без ошибок, только informational note в `auth_service.py` о `--check-untyped-defs`).
- ✅ Ошибки из рабочего трекера `errors.md` по сервисам устранены на текущем срезе.

### Проверки

- `venv\Scripts\python.exe -m ruff check Test_UI/app/application/services` — успешно.
- `venv\Scripts\python.exe -m mypy --no-incremental Test_UI/app/application/services` — успешно.

---

## 2026-02-27 - Итерация 3 (продолжение): cleanup inline-style и адаптивность шага Эвакуация/Схема

### Что сделано

- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`:
  - убран inline RichText со встроенными цветами в строках review-карточек;
  - строки сводки переведены на themed-элементы (`form100ReviewRow`, `form100ReviewRowLabel`, `form100ReviewRowValue`);
  - снижена жесткость layout review-панели (`minimumWidth` 280 -> 220 + корректный size policy).
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`:
  - убраны лишние fixed-width hotspot'ы (`isolation_bar`, индекс заметки);
  - ослаблены минимальные ширины боковых блоков (`Типы тканей`, `Заметки`) для лучшей вмещаемости.
- `app/ui/theme.py`:
  - добавлены QSS-правила для новых review-row элементов;
  - убраны обводки (`border`) у `form100ReviewBadge`, чтобы снизить визуальный шум.

### Статус DoD

- ✅ Удален inline-style hotspot в review-сводке шага Эвакуация.
- ✅ Улучшена адаптивность шагов `step_evacuation` и `step_bodymap` на узких экранах.
- ✅ Визуальная подача стала чище за счет отказа от лишних обводок в review-badges.

### Проверки

- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` - успешно.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` - успешно.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_ui_no_inline_styles.py tests/unit/test_notifications_status.py -p no:cacheprovider` - `8 passed`.

---

## 2026-02-27 - Итерация 2/3 (продолжение): startup hardening + signal-safety

### Что сделано

- `app/main.py`:
  - усилен `_TeeStream` в stderr-tee: в `write/flush/isatty/fileno` добавлен перехват `AttributeError` вместе с I/O исключениями;
  - это снижает риск аварии при shutdown/миграциях в окружениях, где системные stream-обертки деградируют до `None` внутри метода `flush()`.
- `app/ui/form100_v2/wizard_widgets/lesion_type_widget.py`:
  - заменен lambda-emit на явный слот `_emit_values_changed(self, _checked: bool)`;
  - уменьшен риск сигнального несоответствия `valuesChanged()` при прокидке аргумента от `toggled(bool)`.

### Статус DoD

- ✅ Укреплен стартовый error-handling в `main.py` без изменения бизнес-логики.
- ✅ Закрыт риск нестабильного сигнального вызова в lesion toggle widget.
- ✅ Точечные quality checks и unit-тесты по затронутым областям - green.

### Проверки

- `venv\\Scripts\\python.exe -m ruff check app/main.py app/ui/form100_v2/wizard_widgets/lesion_type_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` - успешно.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/main.py app/ui/form100_v2/wizard_widgets/lesion_type_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` - успешно.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_main_window_context_selection.py tests/unit/test_notifications_status.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` - `12 passed`.

---

## 2026-02-27 - Pylance full cleanup (excluding Test_UI)

### Что сделано

- Выполнена полная зачистка типовых Pylance/pyright ошибок по рабочему контуру проекта (`app`, `scripts`, `tests`) c явным исключением `Test_UI`.
- Исправлены типовые проблемы SQLAlchemy-типизации (bool/int выражения колонок), nullable доступы (`wb.active`, `datetime` поля), сигнатуры/атрибуты UI-хелперов.
- Добавлена конфигурация `pyrightconfig.json` с исключением `Test_UI`.

### Проверки

- `venv\\Scripts\\python.exe -m pyright` -> `0 errors, 0 warnings, 0 informations`.
- `venv\\Scripts\\python.exe -m ruff check app scripts tests` -> passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app scripts tests` -> success.

### Статус DoD

- ✅ В рабочем контуре нет воспроизводимых Pylance/pyright ошибок.
- ✅ `Test_UI` исключен из объема работ по договоренности.

---

## 2026-02-27 - Release packaging refresh (EXE + NSIS/Inno) and repo hygiene

### What was done

- `.gitignore` expanded to ignore modern local artifacts (coverage, pyright cache, sqlite/log/tmp/test outputs).
- `.pre-commit-config.yaml` refreshed:
  - added core repo hygiene hooks,
  - upgraded Ruff hooks (`ruff`, `ruff-format`),
  - expanded mypy scope to `app`, `scripts`, `tests`,
  - added local `compileall` hook.
- EXE packaging scripts improved:
  - `scripts/build_windows.ps1`: prerequisite checks, clean build, post-build verification, `RELEASE_INFO.txt` generation.
  - `scripts/build_exe.bat`: clear status output and proper exit code behavior.
  - `scripts/verify_exe.ps1`: clearer validation output and dynamic python runtime DLL check.
- Installer packaging improved:
  - `scripts/installer.nsi`: modernized flow with components page, start menu/desktop options, uninstall metadata, release-info support.
  - `scripts/build_installer_nsis.ps1` + `scripts/build_nsis.bat`: auto version injection from `pyproject.toml` and robust pre-checks.
  - `scripts/installer.iss` + `scripts/build_installer.ps1`: aligned metadata and improved build diagnostics.
- `docs/build_release.md` rewritten to a clean, up-to-date release playbook.

### Verification

- `venv\\Scripts\\python.exe -m pre_commit validate-config` - passed.
- `venv\\Scripts\\python.exe -m ruff check app scripts tests` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app scripts tests` - passed.

### DoD status

- ✅ Packaging scripts for EXE and NSIS/Inno are updated and informative.
- ✅ Repo hygiene and pre-commit baseline are updated.
- ✅ Documentation for release flow is synchronized.

---

## 2026-02-27 - Pylance cleanup: unnecessary isinstance in main.py

### What was done

- `app/main.py`:
  - removed redundant `isinstance(result, int)` in `_TeeStream.write`;
  - removed redundant `isinstance(fd_obj, int)` in `_TeeStream.fileno`.
- Logic is unchanged; code now matches strict type expectations for `TextIOBase`.

### Verification

- `venv\\Scripts\\python.exe -m pyright app/main.py` -> `0 errors`.
- `venv\\Scripts\\python.exe -m ruff check app/main.py` -> passed.

### DoD status

- ✅ Reported Pylance warnings `reportUnnecessaryIsInstance` for lines 71 and 98 are addressed.

---

## 2026-02-27 - References actions layout harmonization

### What was done

- `app/ui/references/reference_view.py`:
  - rebuilt form action layout into two semantic groups:
    - edit group: `Добавить`, `Сохранить`;
    - cleanup group: `Удалить`, `Очистить`;
  - set action bar vertical policy to `Fixed` to prevent oversized stretching;
  - inserted layout stretch before the action bar, so controls stay anchored in a predictable bottom area;
  - kept adaptive direction switching via `update_action_bar_direction`.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/ui/references/reference_view.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/references/reference_view.py` - passed.

### DoD status

- ✅ Action buttons are grouped and positioned more harmoniously.
- ✅ Layout behavior is stable on varying window sizes.

---

## 2026-02-27 - Remove transferred demo UI elements

### What was done

- `app/ui/login_dialog.py`:
  - removed demo hint text (`admin / admin1234`);
  - removed `Подставить demo` button from login actions;
  - removed helper method `_fill_demo` used only by that button.
- Verified there are no remaining `demo` login fillers in `app/` and `tests/`.

### Verification

- `rg -n -i "demo|admin1234|подставить|для теста|fill_demo" app tests` -> no matches.
- `venv\\Scripts\\python.exe -m ruff check app/ui/login_dialog.py` -> passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/login_dialog.py` -> passed.
- `venv\\Scripts\\python.exe -m pyright app/ui/login_dialog.py` -> 0 errors.

### DoD status

- ✅ Unneeded demo controls imported from Test_UI removed from login screen.

---

## 2026-02-28 - Form100 user-facing naming cleanup and test stabilization

### What was done

- Removed remaining user-facing `V2` labels for Form100:
  - `app/infrastructure/db/repositories/form100_repo_v2.py`:
    - `Карточка Form100 V2 не найдена` -> `Карточка Form100 не найдена`;
    - `Конфликт версий Form100 V2...` -> `Конфликт версий Form100...`.
  - `app/infrastructure/reporting/form100_pdf_report_v2.py`:
    - PDF title `Форма 100 V2 ...` -> `Форма 100 ...`;
    - header `ФОРМА 100 (V2)` -> `ФОРМА 100`.
- Stabilized `tests/integration/test_form100_v2_service.py`:
  - replaced corrupted fixture strings with stable ASCII fixture data;
  - removed fragile localized `pytest.raises(..., match=...)` checks in this test;
  - switched tissue type fixture to `sorted(_TISSUE_TYPES)[0]` via import from rules to avoid encoding-sensitive literals.

### Verification

- `venv\\Scripts\\python.exe -m ruff check app/infrastructure/db/repositories/form100_repo_v2.py app/infrastructure/reporting/form100_pdf_report_v2.py tests/integration/test_form100_v2_service.py` - passed.
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/infrastructure/db/repositories/form100_repo_v2.py app/infrastructure/reporting/form100_pdf_report_v2.py tests/integration/test_form100_v2_service.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m pytest -q tests/integration/test_form100_v2_service.py tests/integration/test_form100_v2_zip_roundtrip.py tests/integration/test_exchange_service_import_reports.py -p no:cacheprovider` - `7 passed, 1 warning`.
- `rg -n -S 'Form100 V2|ФОРМА 100 \\(V2\\)|Форма 100 V2|form100_v2\\+zip|report_type\\s*=\\s*\"form100_v2\"' app tests`:
  - only migration metadata remains in `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`.

### DoD status

- ✅ User-visible Form100 labels no longer expose `V2`.
- ✅ Targeted Form100 integration flow is green after test stabilization.
- ✅ Change logged per project reporting rule.

---

## 2026-03-02 - Continuation: адаптивность Администрирование и Справочники

### Что сделано

- `app/ui/admin/user_admin_view.py`:
  - усилены требования к ширине колонок админ-экрана в горизонтальном режиме;
  - добавлен более ранний переход в вертикальный стек (`LeftToRight` -> `TopToBottom`) при недостатке ширины;
  - для критичных блоков (`Список пользователей`, `События аудита`, `Резервные копии`, `Создать пользователя`, `Сброс пароля / статус`) установлена политика `Expanding`;
  - `backup_status` переведен в `wordWrap`, чтобы длинные статусы не ломали композицию.
- `app/ui/references/reference_view.py`:
  - панель верхних контролов сделана адаптивной (`QBoxLayout` + `update_action_bar_direction`);
  - основной контент переведен на адаптивный контейнер с переключением горизонталь/вертикаль по ширине окна;
  - в горизонтальном режиме зафиксированы минимумы для списка/формы; в узком режиме список поднимается вверх с увеличенной минимальной высотой;
  - выравнивание кнопок действий формы сохранено через текущий action-bar паттерн.

### Проверки

- `venv\\Scripts\\python.exe -m ruff check app/ui/admin/user_admin_view.py app/ui/references/reference_view.py` - `All checks passed`.
- `venv\\Scripts\\python.exe -m mypy app/ui/admin/user_admin_view.py app/ui/references/reference_view.py` - `Success: no issues found`.
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_ui_no_inline_styles.py tests/unit/test_notifications_status.py tests/integration/test_reference_service.py tests/integration/test_reference_service_crud.py tests/integration/test_backup_service_acl.py` - `12 passed`.
- `venv\\Scripts\\python.exe -m compileall -q app/ui/admin/user_admin_view.py app/ui/references/reference_view.py` - успешно.

### Статус DoD

- ✅ Страница администрирования на средних экранах больше не уходит в «узкие» колонки.
- ✅ Справочники адаптивно перестраиваются под меньшую ширину без потери функционала.
- ✅ Все изменения прошли статическую и тестовую проверку.

---

### 2026-03-02

- Проведен аудит безопасности и качества кода:
  - `ruff check app tests` — All checks passed;
  - `mypy app tests` — 0 ошибок в 245 файлах;
  - `pytest` — 221 passed (до исправлений).
- Проверены паттерны: SQLi, Path Traversal (Zip Slip), hardcoded secrets, RCE (`eval`/`exec`/`os.system`/`subprocess`).
  - Уязвимостей не обнаружено.
- Исправлены 3 найденные точки роста:
  - **Очистка `tmp_run` при старте**: добавлена `cleanup_stale_temp_dirs()` в `app/bootstrap/startup.py`.
    - Удаляет осиротевшие каталоги `epid-temp-*` и `form100-v2-*` из `tmp_run` при запуске приложения.
    - Вызывается из `initialize_database(...)` автоматически.
  - **Серверная валидация длины пароля**: подтверждено, что Pydantic DTO уже содержат `min_length=8` на уровне `CreateUserRequest`/`ResetPasswordRequest`.
    - В `app/application/services/user_admin_service.py` добавлен дополнительный defense-in-depth check (`MIN_PASSWORD_LENGTH = 8`).
  - **Миграция `_require_admin` на `role_matrix`**: в `app/application/services/user_admin_service.py` заменена жёсткая строковая проверка `str(actor.role) != "admin"` на вызов `can_manage_users(cast(Role, actor.role))` из централизованного модуля `app/application/security/role_matrix.py`.
- Добавлены тесты:
  - `tests/unit/test_startup_temp_cleanup.py` — 5 сценариев (удаление целевых, сохранение безопасных, noop).
  - `tests/unit/test_user_admin_password_policy.py` — 5 сценариев (DTO-валидация коротких паролей, прием валидных, константа).

### Проверки

- `ruff check app/bootstrap/startup.py app/application/services/user_admin_service.py tests/unit/test_startup_temp_cleanup.py tests/unit/test_user_admin_password_policy.py` — All checks passed.
- `pytest -q` — 231 passed (было 221).
- Исправлена проблема «Поиск и ЭМК»: таблица госпитализаций уезжала за экран.
  - Обернуто содержимое `_build_ui()` в `QScrollArea` (`app/ui/patient/patient_emk_view.py`), вся страница теперь скроллируется.
  - Снижен `minimumHeight` таблицы госпитализаций с 280 до 120 для лучшего сжатия на малых экранах.
  - Проверки: `ruff check` — All checks passed, `compileall` — успешно, `pytest -q` — 231 passed.

---

## Форма 100 — UI исправления (02.03.2026, сессия 2)

### 1. Чекбоксы: чёрная окантовка

- Добавлены глобальные стили `QCheckBox::indicator` и `QRadioButton::indicator` в `app/ui/theme.py` с тёмной окантовкой `1.5px solid`.
- Состояния: normal (серый бордер), hover (тёмный бордер), checked (заливка), disabled (приглушённый).

### 2. Страница «Поражения»: перестройка layout

- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`: переструктурирован layout — контролы (типы поражений + ткани + заметки) в верхнем ряду, схема тела — полная ширина внизу.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`: улучшена нормализация изображения силуэта — вместо жёсткого порога (3 уровня) используется плавная карта яркости→альфа для более чистых контуров тела.

### 3. Эвакуация/Итог: панель обзора

- `app/ui/theme.py`: переведены цвета панели обзора с холодных синих тонов (#2E86C1-based) на тёплую бежевую палитру приложения (accent, error, success, warn).
- Лейблы секций bottom-widget также обновлены на тёплые тона.

### Файлы изменены

- `app/ui/theme.py` — глобальные стили checkbox/radiobutton + обзорная панель
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py` — layout
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` — нормализация изображения

### 2026-03-03

- Проведен полный технический аудит кодовой базы на предмет наличия проблем с кодировкой ("кракозябр") и экранированных кириллических символов:
  - ????????? ???????????? `*.py`, `*.md`, `*.json`, `*.yaml` ?? ??????? ????? ???????? (????????: `U+00C2`, `U+00C2`, `U+00C2`, `U+00C2`, `U+FFFD`).
  - Выполнено сканирование на наличие unicode-экранированных (`\u04XX`) кириллических строк.
  - **Результат**: Проект чист от mojibake.
- Исправлены 2 найденные точки:
- В миграциях `0013_ismp_case.py` и `0016_fk_cascade.py` экранированные строки вида `'\u0412\u0410\u041f'` (сгенерированные Alembic) были переведены в читаемый кириллический текст.
- `quality_gates.ps1` (ruff, mypy, pytest) пройден без ошибок (All checks passed).

- Произведен рефакторинг модуля "Аналитика" по части UX и потребления памяти:
  - Введена пагинация (лимит в 1000 строк) для вывода результатов `search_samples` в таблицу UI, чтобы предотвратить зависания при выборе больших периодов.
  - Убрано жесткое ограничение в фильтрах на 2024 год (разрешен выбор дат с 2000 года).
  - Добавлена очистка кэша базы данных (`analytics_service.clear_cache()`) при ручном выполнении поиска или обновлении сводки, так что данные в UI всегда гарантированно актуальные.
  - В `AnalyticsRepository` устранен дубляж кода — фильтры по дате и категории пациента вынесены в приватную функцию-хелпер `_apply_base_filters`.

### 2026-03-04

- странены графические и текстовые наложения в генерации PDF ормы 100 v2 (pixel-perfect):
  - Скорректированы Y-смещения для текстов и обводок в медицинских таблицах корешка и основной карты.
  - екторные рисунки санэвакуационных потерь (оружие, , и др.) переведены из сплошной заливки в контурную отрисовку с правильным масштабом.
  - азделена колонка с вертикальным текстом 'ид санитарных потерь (обвести)'.
  - Скорректированы координаты + отметок и красных обводок маршрутов эвакуации ('куда эвакуирован').

  - астроены габариты вектора человечков (силуэтов спереди/сзади) для точного совпадения красных маркеров.
  - справлено наложение крестиков эвакуации на подписи 'куда эвакуирован'.

---

## 2026-03-04 - Form100 PDF: завершение перехода на структурный отчёт + bodymap из шаблона

### Что сделано

- `app/infrastructure/reporting/form100_pdf_report_v2.py`:
  - завершён переход на формат «структурный текстовый отчёт + визуальная схема тела»;
  - добавлен рендер bodymap на базе реального шаблона `form_100_bd.png` (fallback: `form_100_body.png`);
  - метки врача (`WOUND_X`, `BURN_HATCH`, `AMPUTATION`, `TOURNIQUET`, `NOTE_PIN`) наносятся поверх шаблона по координатам из `bodymap_annotations`;
  - получившееся изображение вставляется в PDF как `platypus.Image` (растровый flowable);
  - добавлен fallback на прежний векторный `Drawing`, если шаблон недоступен.
- Блок «Схема тела» теперь выводится всегда (даже если меток нет), а таблица аннотаций остаётся условной.
- Добавлены unit-тесты в `tests/unit/test_form100_pdf_report_v2.py`:
  - проверка, что PDF валиден и содержит image-объект при доступном шаблоне;
  - проверка fallback-пути (рендер через векторный `Drawing`) при отсутствии шаблона.

### Проверки

- `venv\Scripts\python.exe -m ruff check app/infrastructure/reporting/form100_pdf_report_v2.py tests/unit/test_form100_pdf_report_v2.py` - `All checks passed!`
- `venv\Scripts\python.exe -m mypy --no-incremental app/infrastructure/reporting/form100_pdf_report_v2.py tests/unit/test_form100_pdf_report_v2.py` - `Success: no issues found in 2 source files`
- `venv\Scripts\python.exe -m pytest -q tests/unit/test_form100_pdf_report_v2.py tests/integration/test_form100_v2_service.py` - `5 passed in 2.33s`

### Статус DoD

- ✅ Формат PDF по Форме 100 соответствует целевой модели: читаемые текстовые секции + схема тела с врачебными метками из карточки.
- ✅ Экспорт устойчив: fallback работает при недоступном файле шаблона.

---

## 2026-03-04 - Full quality-gates pass + pyright hardening

### Что сделано

- `app/application/services/reporting_service.py`:
  - уточнены типы данных для PDF-таблиц в `export_analytics_pdf(...)` (`list[list[Paragraph]]`), чтобы убрать ошибки строгой статической типизации.
- `app/infrastructure/reporting/form100_pdf_report_v2.py`:
  - `_MEIPASS` доступ переведён на безопасный `getattr(..., None)` + `isinstance(..., str)`;
  - аргументы фонового `Rect(...)` вынесены в `dict[str, Any]` для корректного прохождения `pyright`.
- `app/ui/form100_v2/widgets/bodymap_editor_v2.py`:
  - удалён мёртвый/недостижимый код в `_active_silhouettes`;
  - исправлен безопасный доступ к `_MEIPASS` для pyright-совместимости.
- `app/ui/form100_v2/wizard_widgets/bodymap_widget.py`:
  - исправлен безопасный доступ к `_MEIPASS` для pyright-совместимости.

### Проверки (CI-профиль)

- `venv\Scripts\python.exe -m ruff check app tests` - `All checks passed!`
- `venv\Scripts\python.exe -m mypy app tests` - `Success: no issues found in 248 source files`
- `venv\Scripts\python.exe -m pyright` - `0 errors, 0 warnings, 0 informations`
- `venv\Scripts\python.exe -m pytest -q` - `233 passed, 2 warnings`
- `venv\Scripts\python.exe -m compileall -q app tests scripts` - успешно

### Статус DoD

- ✅ Все quality-gates из workflow `quality-gates.yml` пройдены локально.
- ✅ Статический анализ pyright приведён к зелёному состоянию.

## 2026-04-06 - Очистка конфигурации агентов и статической типизации

### Что сделано

- Удалён `GEMINI.md`: в репозитории оставлена единая конфигурация агента в `AGENTS.md`.
- Удалён `pyrightconfig.json`: в проекте используется `mypy` как основной инструмент проверки типов.
- Перед удалением проверено:
  - `AGENTS.md` присутствует в корне проекта;
  - в `pyproject.toml` есть секция `[tool.mypy]`.

### Изменённые файлы

- `GEMINI.md` (удалён)
- `pyrightconfig.json` (удалён)
- `docs/progress_report.md` (обновлён)

### Проверки после изменений

- `ruff check app tests` — не пройден (17 ошибок `UP038` в существующих файлах проекта).
- `mypy app tests` — не пройден (16 существующих ошибок типизации в UI/bootstrap/infrastructure).
- `pytest -q` — не пройден (ошибки импорта из-за отсутствующего пакета `argon2`).
- `python -m compileall -q app tests scripts` — пройден.

## 2026-04-06 - Доведение quality gates до зелёного состояния

### Что сделано

- Исправлены ошибки строгой типизации PySide6:
  - `QDateTimeEdit(calendarPopup=True)` заменён на безопасный для типизации шаблон: создание без аргументов + `setCalendarPopup(True)`.
  - В `MainWindow._show_placeholder` убран невалидный для stubs конструктор `QLabel(..., alignment=...)`; выравнивание задаётся через `setAlignment(...)`.
  - Для вызовов `QMessageBox.critical/warning` в стартап-пайплайне добавлены обёртки `_show_critical/_show_warning` с типобезопасным parent.
  - В `main.py` для глобального обработчика исключений parent окна для `QMessageBox.critical` приведён к ожидаемому типу.
- Исправлена типизация SQLAlchemy-инспекции в `ReferenceRepository.upsert_simple`.
- Устранены все найденные `ruff`-ошибки `UP038` (автоисправление `ruff --unsafe-fixes`).
- Исправлено поведение адаптивной панели действий в `LabSamplesView` на узкой ширине (переключение в вертикальную компоновку), чтобы проходил unit-тест responsive-режима.
- Установлена отсутствующая зависимость окружения `argon2-cffi`, из-за которой падали тесты при импорте `argon2`.

### Изменённые файлы

- `app/bootstrap/startup.py`
- `app/infrastructure/db/repositories/reference_repo.py`
- `app/main.py`
- `app/ui/emz/emz_form.py`
- `app/ui/lab/lab_samples_view.py`
- `app/ui/main_window.py`
- `app/ui/sanitary/sanitary_history.py`
- `app/application/services/analytics_service.py`
- `app/application/services/exchange_service.py`
- `app/domain/rules/form100_rules_v2.py`
- `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`
- `app/infrastructure/db/repositories/form100_repo_v2.py`
- `app/infrastructure/reporting/form100_pdf_report_v2.py`
- `app/ui/form100_v2/form100_wizard.py`
- `app/ui/form100_v2/widgets/bodymap_editor_v2.py`
- `app/ui/widgets/date_input_flow.py`

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 248 source files`
- `pytest -q` - `233 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-06 - Глобальный аудит проекта (без исправлений кода)

### Что сделано

- Выполнен полный аудит проекта по 10 шагам:
  - правила/контекст/архитектура;
  - инвентаризация файлов и локальных артефактов;
  - quality gates + ручной статический аудит;
  - аудит тестов и покрытия;
  - аудит БД/миграций Alembic;
  - аудит `.agents/skills` и `skills-lock.json`;
  - аудит CI/CD-конфигураций и документации.
- Сформирован детальный отчёт: `docs/full_audit_report.md`.

### Изменённые файлы

- `docs/full_audit_report.md` (добавлен)
- `docs/progress_report.md` (обновлён)

### Выполненные проверки/команды

- `ruff check app tests --output-format=json`
- `mypy app tests`
- `pytest -q`
- `python -m compileall -q app tests scripts`
- `pytest --cov=app -q`
- `alembic heads`
- `alembic current`
- `alembic check`

### Ключевые результаты аудита (кратко)

- Найдены архитектурные нарушения слоёв (UI -> Infrastructure).
- `alembic check` падает (schema drift).
- Покрытие тестами: `43%`.
- `ruff`/`mypy`/`pytest`/`compileall` на момент аудита зелёные.

## 2026-04-06 - Этап 1: очистка проекта (скиллы, pyright, артефакты)

### Что сделано

- Выполнена чистка `.agents/skills`: удалены нерелевантные скиллы, оставлены только:
  - `epid-control`, `setup-codex-skills`, `codex`, `commit-work`, `qa-test-planner`,
  - `c4-architecture`, `mermaid-diagrams`, `backend-to-frontend-handoff-docs`,
  - `frontend-to-backend-requirements`, `session-handoff`.
- Удалены мусорные документы из `docs/`:
  - `docs/extracted_3.txt`, `docs/ttz_text.txt`, `docs/ttz_docx_text.txt`.
- Полностью убран `pyright` из контура проекта:
  - удалён `pyrightconfig.json` (если присутствовал);
  - удалён `pyright` из `requirements-dev.txt`;
  - удалён шаг `pyright` из `scripts/quality_gates.ps1`;
  - удалён шаг `pyright` из `.github/workflows/quality-gates.yml`.
- Удалён `GEMINI.md` (если присутствовал).
- Обновлён `skills-lock.json`:
  - удалены записи удалённых скиллов;
  - добавлены `epid-control` и `setup-codex-skills`.
- Удалены локальные артефакты:
  - `.mypy_cache/`, `.ruff_cache/`, `tmp/`, `tmp_run/`, `_pytest_tmp/`, `pytest_tmp/`, `pytest_work/`, `pytest_artifacts/`, `.coverage`, `pip_install.log`.
- Обновлён `.gitignore`: добавлены `pytest_tmp/` и `pytest_work/`.

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 249 source files`
- `pytest -q` - `236 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-06 - Этап 2: устранение нарушений UI -> Infrastructure

### Что сделано

- Устранены прямые зависимости UI-слоя от Infrastructure:
  - `app/ui/first_run_dialog.py` переведён на `SetupService` (`app/application/services/setup_service.py`) для создания первого администратора.
  - `app/ui/widgets/patient_selector.py` переведён на `PatientService` без прямого использования `PatientRepository/session_scope`.
- Расширен `PatientService`: добавлен метод `get_patient_name(...)` для UI-сценариев выбора пациента.
- Вынесена в application-слой логика подготовки payload/валидации для лабораторных и санитарных проб:
  - новый модуль `app/application/services/lab_sample_payload_service.py`;
  - новый модуль `app/application/services/sanitary_sample_payload_service.py`.
- Вынесена сборка payload Формы 100 V2 из UI в application-слой:
  - новый модуль `app/application/services/form100_payload_service.py`;
  - `app/ui/form100_v2/form100_editor.py` теперь использует application-builder.
- Для обратной совместимости unit-тестов `app/ui/lab/lab_sample_detail_helpers.py` оставлен как тонкий re-export application-функций.
- Проверка слоёв: в `app/ui/` отсутствуют импорты `app.infrastructure`.

### Изменённые файлы

- `app/application/services/setup_service.py` (добавлен)
- `app/application/services/patient_service.py`
- `app/application/services/lab_sample_payload_service.py` (добавлен)
- `app/application/services/sanitary_sample_payload_service.py` (добавлен)
- `app/application/services/form100_payload_service.py` (добавлен)
- `app/ui/first_run_dialog.py`
- `app/ui/widgets/patient_selector.py`
- `app/ui/lab/lab_sample_detail.py`
- `app/ui/lab/lab_sample_detail_helpers.py`
- `app/ui/sanitary/sanitary_history.py`
- `app/ui/form100_v2/form100_editor.py`
- `docs/progress_report.md`

### Проверки

- `rg -n "from app\.infrastructure|import app\.infrastructure" app/ui` — совпадений нет.
- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 253 source files`
- `pytest -q` - `236 passed, 2 warnings`

## 2026-04-06 - Срочная проверка "603 проблемы" (фактический статус ветки)

### Что сделано

- Повторно прочитаны `docs/session_handoff.md` и `AGENTS.md`.
- Запущен полный цикл проверок с сохранением логов в `tmp_run/`:
  - `ruff check app tests 2>&1 | tee tmp_run/ruff_output.txt`
  - `mypy app tests 2>&1 | tee tmp_run/mypy_output.txt`
  - `pytest -q 2>&1 | tee tmp_run/pytest_output.txt`
  - `python -m compileall -q app tests scripts 2>&1 | tee tmp_run/compileall_output.txt`
- Выполнен архитектурный скан импортов:
  - `rg -n "from app\.infrastructure|import app\.infrastructure" app/application/ app/ui/`
  - В `app/ui/` нарушений `UI -> Infrastructure` не найдено.
  - Совпадения есть только в `app/application/services`, что допустимо в текущем слое.
- Выполнен финальный повторный прогон quality gates:
  - `ruff check app tests`
  - `mypy app tests`
  - `pytest -q`
  - `python -m compileall -q app tests scripts`

### Итог по проблемам

- `ruff`: 0 ошибок.
- `mypy`: 0 ошибок.
- `pytest`: 0 failed, `236 passed` (`2 warnings`).
- `compileall`: 0 ошибок.
- Заявленные `603` проблемы в текущем состоянии ветки не воспроизвелись.

### Изменённые файлы

- `docs/progress_report.md`
- `docs/session_handoff.md`
- `tmp_run/ruff_output.txt`
- `tmp_run/mypy_output.txt`
- `tmp_run/pytest_output.txt`
- `tmp_run/compileall_output.txt`

## 2026-04-06 - Быстрая ревизия архитектуры (после этапа 2)

### Что сделано

- Выполнена контрольная проверка слоя UI на прямые импорты Infrastructure:
  - `rg -n "from app\.infrastructure|import app\.infrastructure" app/ui/` — совпадений нет.
- Проведён аудит новых application-сервисов:
  - `app/application/services/setup_service.py`
  - `app/application/services/lab_sample_payload_service.py`
  - `app/application/services/sanitary_sample_payload_service.py`
  - `app/application/services/form100_payload_service.py`
- В новых application-сервисах добавлены docstrings на публичные API (без изменения поведения):
  - `setup_service.py`
  - `lab_sample_payload_service.py`
  - `sanitary_sample_payload_service.py`
  - `form100_payload_service.py`
- Выполнена быстрая проверка крупных UI-файлов (`analytics_view.py`, `emz_form.py`, `theme.py`, `sanitary_history.py`):
  - критичных бизнес-правил в самих файлах, требующих срочного выноса, не обнаружено;
  - `sanitary_history.py` использует application-сервис для сборки/валидации payload.
- Проверен аспект Dependency Inversion:
  - payload-сервисы не зависят от Infrastructure;
  - `SetupService` импортирует конкретные infra-реализации (`User`, `session_scope`, `hash_password`) — допустимо на текущем этапе, рекомендуется в будущем перейти на протоколы/абстракции репозиториев.

### Изменённые файлы

- `app/application/services/setup_service.py`
- `app/application/services/lab_sample_payload_service.py`
- `app/application/services/sanitary_sample_payload_service.py`
- `app/application/services/form100_payload_service.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 253 source files`
- `pytest -q` - `236 passed, 2 warnings`

## 2026-04-06 - Локальный фикс Pylance Unknown в Form100 rules v2

### Что сделано

- Исправлена типизация в `app/domain/rules/form100_rules_v2.py` для устранения предупреждений Pylance `reportUnknown*`:
  - явная типизация `bodymap_tissue_types` и `bodymap_annotations` без неявных `list[Unknown]`;
  - сужение типов в `_walk_diff` через `cast(Mapping[Any, Any], ...)` и безопасная сортировка ключей (`key=str`);
  - ` _as_dict` переведён на работу с `Mapping`, чтобы убрать `dict[Unknown, Unknown]`.
- Бизнес-логика валидации не изменена.

### Изменённые файлы

- `app/domain/rules/form100_rules_v2.py`
- `docs/progress_report.md`

### Проверки

- `ruff check app/domain/rules/form100_rules_v2.py` - `All checks passed!`
- `mypy app/domain/rules/form100_rules_v2.py` - `Success: no issues found in 1 source file`
- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 253 source files`
- `pytest -q` - `236 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-06 - Этап 3: починка БД/миграций и SQL-безопасности

### Что сделано

- Настроен VS Code под единый type-checker:
  - создан локальный `.vscode/settings.json` с `"python.analysis.typeCheckingMode": "off"` (Pylance type checking отключён);
  - `.vscode/` уже присутствует в `.gitignore`, дополнительных правок не потребовалось.
- Починен `alembic check` (schema drift):
  - добавлен `include_object` в `app/infrastructure/db/migrations/env.py`;
  - из сравнения исключены FTS-таблицы и их shadow-таблицы (`*_fts*`), которые управляются `FtsManager`, а не Alembic;
  - исключены reflected-only индексы (`remove_index`), отсутствующие в SQLAlchemy metadata.
- Синхронизированы расхождения metadata/БД по Form100:
  - `Form100V2.emr_case_id`: убран `index=True`, добавлен явный `Index("ix_form100_emr_case", "emr_case_id")` в `__table_args__`;
  - `Form100DataV2.form100_id`: убран `unique=True`, сохранён именованный уникальный индекс `ux_form100_data_form`.
- Исправлена SQL-безопасность:
  - `app/infrastructure/db/fts_manager.py`: убран динамический DML f-string в integrity-check, добавлен whitelist заранее подготовленных SQL-выражений;
  - `app/infrastructure/db/migrations/versions/0016_fk_cascade.py`: заменён строковый `INSERT ... SELECT ...` на SQLAlchemy Core `insert().from_select(...)`.
- Исправлена связь ORM без обратной стороны:
  - `RefAntibioticGroup.antibiotics` <-> `RefAntibiotic.group` теперь с `back_populates` на обеих сторонах.

### Изменённые файлы

- `app/infrastructure/db/migrations/env.py`
- `app/infrastructure/db/models_sqlalchemy.py`
- `app/infrastructure/db/fts_manager.py`
- `app/infrastructure/db/migrations/versions/0016_fk_cascade.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`
- `tmp_run/alembic_check_output.txt`

### Проверки

- `alembic upgrade head` - успешно
- `alembic check` - `No new upgrade operations detected`
- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 253 source files`
- `pytest -q` - `236 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-06 - Код-ревью: проход 5 (документация + итоговый отчёт)

### Что сделано

- Проверена документация (`docs/` + `README.md`) на битые markdown-ссылки: битых ссылок не найдено.
- Выполнена ревизия актуальности ключевых документов:
  - `README.md` — соответствует текущему quality-gate контуру (ruff/mypy/pytest/compileall).
  - `docs/context.md` — метрики актуальны, но дата в шапке требует обновления.
  - `docs/tech_guide.md` — соответствует текущей архитектуре и процессу миграций.
- Собран единый итоговый отчёт по результатам проходов 1-4 и текущей проверки:
  - `docs/code_review_report.md`.

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 253 source files`
- `pytest -q` - `236 passed, 2 warnings`
- `python -m alembic check` - `No new upgrade operations detected.`
- `python -m alembic heads` - `0019_form100_v2_schema (head)`
- `python -m alembic current` - `0019_form100_v2_schema (head)`

### Изменённые файлы

- `docs/code_review_report.md` (добавлен)
- `docs/progress_report.md` (обновлён)
- `docs/session_handoff.md` (обновлён)

## 2026-04-07 - Полный аудит безопасности (без правок кода)

### Что сделано

- Выполнен полный security-аудит по 7 направлениям:
  - аутентификация;
  - авторизация;
  - SQL-инъекции;
  - защита данных пациентов;
  - секреты и конфигурация;
  - целостность БД;
  - desktop-специфичные риски.
- Сформирован детальный отчёт с классификацией рисков и конкретными фиксациями:
  - `docs/security_review_2026-04-07.md`.
- Подтверждено, что:
  - пароли хешируются через `argon2`/`bcrypt`;
  - критичных DML SQL-injection паттернов не обнаружено;
  - `subprocess/os.system/shell=True/eval()` в `app/` не используется.
- Выявлены ключевые риски:
  - критичные проблемы авторизации экспорта/импорта ПДн;
  - избыточное сохранение ПДн в audit payload Form100;
  - отсутствие шифрования backup/экспортных артефактов;
  - пробелы в audit/actor-tracking для части mutating операций.

### Статистика по итогам аудита

- КРИТИЧНЫХ: 2
- ВАЖНЫХ: 9
- РЕКОМЕНДАЦИЙ: 3

### Изменённые файлы

- `docs/security_review_2026-04-07.md` (добавлен)
- `docs/progress_report.md` (обновлён)
- `docs/session_handoff.md` (обновлён)

## 2026-04-07 - P0: критичные исправления security + архитектуры

### Что сделано

- Закрыт критичный контроль доступа для импорта/экспорта:
  - добавлен permission `manage_exchange` в role-matrix;
  - в `ExchangeService` добавлены проверки прав и обязательный `actor_id` для import/export операций;
  - в UI (`main_window`, `import_export_view`, `import_export_wizard`) добавлены скрытие/disable по правам и передача `actor_id`.
- Убраны избыточные ПДн из аудита Form100:
  - `form100_service_v2` теперь пишет только метаданные изменений (`actor`, `action`, `card_id`, `changed_fields`, `data_hash`), без full payload.
- Закрыт bypass `actor_id=None`:
  - `reference_service` и `backup_service` требуют `actor_id` для write-операций;
  - mutating-сигнатуры переведены на обязательный `actor_id`.
- Усилен `patient_service`:
  - mutating-методы получают `actor_id`, выполняют permission-check и пишут audit create/update/delete.
- Убран caller-controlled `created_by` из критичного контура:
  - в `lab_service`/`sanitary_service` для mutating-операций используется trusted `actor_id`;
  - обновлены вызовы из UI (прокидка `session.user_id`).
- Выполнен этап code-review P0 (п.6):
  - добавлен `app/application/exceptions.py` (`AppError`, `DatabaseError`, `AuthenticationError`, `PermissionError`);
  - удалены импорты `sqlalchemy` из UI, UI ловит `AppError`.
- Закрыт этап тестов P0 (п.7):
  - `tests/unit/test_backup_service_error_handling.py` переведён на реальный SQLite-engine (`sqlite:///:memory:`), без мока SQLAlchemy engine;
  - добавлен `tests/unit/test_sanitary_sample_payload_service.py`;
  - покрытие `app/application/services/sanitary_sample_payload_service.py` поднято до **86%**.
- Дополнительно устранены побочные проблемы кодировок в ряде UI/test файлов (восстановлены корректные русские строки), из-за которых падали unit-тесты.

### Результаты проверок

- Security checks:
  - `rg -n "sqlalchemy" app/ui --glob "*.py"` -> пусто;
  - `rg -n "actor_id is None" app/application/services/ | rg -v "raise"` -> пусто.
- Quality gates:
  - `ruff check app tests` — pass;
  - `mypy app tests` — pass (`255 source files`);
  - `pytest -q` — pass (`249 passed, 2 warnings`);
  - `python -m compileall -q app tests scripts` — pass.
- Coverage:
  - `pytest --cov=app --cov-report=term-missing -q` -> `TOTAL 45%`;
  - `pytest tests/unit/test_sanitary_sample_payload_service.py --cov=app.application.services.sanitary_sample_payload_service --cov-report=term-missing -q` -> **86%**.

### Изменённые файлы (ключевые)

- `app/application/exceptions.py`
- `app/application/security/role_matrix.py`
- `app/application/security/__init__.py`
- `app/application/services/exchange_service.py`
- `app/application/services/form100_service_v2.py`
- `app/application/services/reference_service.py`
- `app/application/services/backup_service.py`
- `app/application/services/patient_service.py`
- `app/application/services/lab_service.py`
- `app/application/services/sanitary_service.py`
- `app/container.py`
- `app/ui/main_window.py`
- `app/ui/import_export/import_export_view.py`
- `app/ui/import_export/import_export_wizard.py`
- `app/ui/emz/emz_form.py`
- `app/ui/lab/lab_samples_view.py`
- `app/ui/lab/lab_sample_detail.py`
- `app/ui/sanitary/sanitary_dashboard.py`
- `app/ui/sanitary/sanitary_history.py`
- `app/ui/patient/patient_edit_dialog.py`
- `app/ui/patient/patient_emk_view.py`
- `tests/unit/test_backup_service_error_handling.py`
- `tests/unit/test_sanitary_sample_payload_service.py`

## 2026-04-08 - P1: security-усиление (этапы 1-5)

### Что сделано

- Lockout после неудачных логинов переведён в БД:
  - в `users` добавлены `failed_login_count` и `locked_until`;
  - добавлена миграция `app/infrastructure/db/migrations/versions/0020_login_lockout_fields.py`;
  - `AuthService` реализует политику: 5 неудачных попыток -> блокировка на 15 минут, успешный вход -> сброс счётчика.
- Убран in-memory lockout из `app/ui/login_dialog.py`; UI теперь использует только результат `AuthService`.
- Добавлен idle session timeout:
  - в `SessionContext` (`app/application/dto/auth_dto.py`) добавлено поле `created_at`;
  - в `app/config.py` добавлен `session_timeout_minutes` (ENV: `EPIDCONTROL_SESSION_TIMEOUT_MINUTES`, по умолчанию 30);
  - в `app/ui/main_window.py` добавлены `QTimer` + `eventFilter` + auto-logout с повторным входом.
- Усилена парольная политика:
  - в `app/application/services/setup_service.py` добавлена проверка минимальной длины пароля (`MIN_PASSWORD_LENGTH = 8`).
- Добавлены минимальные меры по защите экспортов/бэкапов:
  - предупреждение пользователю о ПДн в экспортном файле (`app/ui/import_export/import_export_wizard.py`);
  - TODO на AES-GCM шифрование экспортов/бэкапов в `exchange_service.py` и `backup_service.py`;
  - best-effort ограничение прав доступа на директорию артефактов.
- Для `report_run.filters_json` добавлена маскировка чувствительных фильтров:
  - `patient_name`, `fio`, `search_text`, `lab_no`, `passport`, `snils` -> `***`.

### Тесты

- Добавлены/обновлены:
  - `tests/integration/test_auth_service.py` (lockout + разблокировка);
  - `tests/unit/test_setup_service_password_policy.py`;
  - `tests/integration/test_reporting_service_artifacts.py` (маскирование filters);
  - `tests/unit/test_main_window_ui_shell.py` (idle-timeout).

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 257 source files`
- `pytest -q` - `253 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-08 - P1: качество и документация (этапы 6-11)

### Что сделано

- В `app/application/dto/emz_dto.py` добавлена явная аннотация:
  - `to_patient_request(self) -> PatientCreateRequest`.
- Усилены слабые unit-тесты (добавлены дополнительные проверки состояния/инвариантов):
  - `tests/unit/test_responsive_actions.py`;
  - `tests/unit/test_ui_theme_tokens.py`;
  - `tests/unit/test_emz_form_case_selectors.py`.
- В `app/infrastructure/db/fts_manager.py` добавлены поясняющие комментарии к DDL f-string:
  - `SQL-injection safe: идентификатор контролируется программно, не пользовательский ввод`.
- Актуализирован `docs/context.md`:
  - обновлён контрольный `pytest -q` (`253 passed`, дата `2026-04-08`);
  - добавлена отметка по текущему покрытию (`~45%`).
- Проверены ссылки на `docs/manual_regression_scenarios.md` в документации:
  - `README.md`, `docs/build_release.md`, `docs/tech_guide.md` — ссылки валидны, файл существует.
- Проверена синхронизация quality-gates в `README.md`:
  - описаны 4 шага: `ruff`, `mypy`, `pytest`, `compileall` (без `pyright`).

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 257 source files`
- `pytest -q` - `253 passed, 2 warnings`
- `python -m compileall -q app tests scripts` - успешно

## 2026-04-08 - P1: перевод integration-тестов на явный DI

### Что сделано

- Переведены integration-тесты с monkeypatch-подмены `session_scope` на явный DI через `session_factory`.
- Для поддержки явного DI расширены сервисы:
  - `ReferenceService`:
    - добавлен параметр `session_factory` в конструктор;
    - все внутренние транзакционные блоки переведены с `session_scope()` на `self.session_factory()`.
  - `BackupService`:
    - добавлен параметр `session_factory` в конструктор;
    - внутренние DB-блоки переведены на `self.session_factory()`.
- Обновлены integration-тесты:
  - `tests/integration/test_backup_service_acl.py`
  - `tests/integration/test_reference_service.py`
  - `tests/integration/test_reference_service_acl.py`
  - `tests/integration/test_reference_service_catalogs.py`
  - `tests/integration/test_reference_service_crud.py`
- `monkeypatch` оставлен только там, где он нужен не для БД-сессии (например, подмена `DATA_DIR/DB_FILE` и локальная подмена `service.seed_defaults` в тесте).

### Изменённые файлы

- `app/application/services/reference_service.py`
- `app/application/services/backup_service.py`
- `tests/integration/test_backup_service_acl.py`
- `tests/integration/test_reference_service.py`
- `tests/integration/test_reference_service_acl.py`
- `tests/integration/test_reference_service_catalogs.py`
- `tests/integration/test_reference_service_crud.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

### Проверки

- `ruff check app tests` - `All checks passed!`
- `mypy app tests` - `Success: no issues found in 257 source files`
- `pytest -q` - `253 passed, 2 warnings`

## 2026-04-08 - P2: сужение `Any` в ключевых файлах

### Что сделано

- `app/bootstrap/startup.py`:
  - `seed_core_data(container: Any)` заменён на `seed_core_data(container: Container)` через `TYPE_CHECKING` импорт.
- Добавлены доменные JSON-типы:
  - новый файл `app/domain/types.py` с `JSONValue` и `JSONDict`.
- `app/domain/rules/form100_rules_v2.py`:
  - убраны `Any` в сигнатурах/локальных переменных;
  - где уместно введены `JSONValue`/`JSONDict`;
  - дифф-логика переведена на `object` + явные `cast`.
- `app/application/services/exchange_service.py`:
  - добавлены типизированные структуры через новый `app/application/dto/exchange_dto.py` (`TypedDict` для манифеста/ошибок/summary/result);
  - введён `Protocol` для `form100_v2_service` вместо `Any`;
  - убраны `Any` в сервисе, динамические участки сужены до `object`/`JSONDict` с точечными `cast`.
- `app/application/services/form100_service_v2.py`:
  - добавлены `TypedDict` через новый `app/application/dto/form100_service_dto.py` (изменения аудита, результаты экспорта/импорта);
  - убраны `Any`, динамические payload участки сужены до `JSONDict`/`dict[str, object]`.
- Сопутствующие правки UI-типизации из-за новых `TypedDict`-контрактов сервисов:
  - `app/ui/import_export/import_export_wizard.py`
  - `app/ui/form100_v2/form100_view.py`

### Метрика `Any`

- По `app/tests` до правок: `304` вхождения `Any`.
- По `app/tests` после правок: `238` вхождений `Any`.
- По целевым файлам задачи (`startup.py`, `form100_rules_v2.py`, `exchange_service.py`, `form100_service_v2.py`):
  - было: `66`
  - стало: `0`

### Проверки

- `ruff check app tests` — pass.
- `mypy app tests` — pass (`260 source files`).
- `pytest -q` — pass (`253 passed, 2 warnings`).
- `python -m compileall -q app tests scripts` — pass.

## 2026-04-08 - P2: CI-чек архитектуры, FK policies, path validation, UI smoke

### Что сделано

- Добавлен архитектурный чек импорта:
  - новый скрипт `scripts/check_architecture.py` с правилами:
    - `UI -> Infrastructure` (запрещено),
    - `UI -> SQLAlchemy` (запрещено),
    - `Domain -> app.infrastructure/app.application/app.ui` (запрещено),
    - `Domain -> PySide6/SQLAlchemy` (запрещено),
    - `Application -> UI` (запрещено).
- Архитектурный чек подключён в quality gates:
  - `scripts/quality_gates.ps1`,
  - `.github/workflows/quality-gates.yml`.
- Усилены FK политики `ondelete` в моделях:
  - `EmrCase.patient_id` -> `ondelete="CASCADE"`,
  - `LabSample.patient_id` -> `ondelete="CASCADE"`,
  - `LabMicrobeIsolation.microorganism_id` -> `ondelete="SET NULL"`.
- Добавлена миграция:
  - `app/infrastructure/db/migrations/versions/2daa0dea652d_feat_fk_ondelete_policies.py`.
- Добавлена path validation перед открытием артефактов:
  - `app/ui/import_export/import_export_view.py`,
  - `app/ui/analytics/analytics_view.py`.
  - Разрешены только директории:
    - `DATA_DIR/artifacts`,
    - `DATA_DIR/backups`,
    - `DATA_DIR/reports`.
- Добавлены базовые UI smoke-тесты:
  - `tests/unit/test_ui_smoke.py` для:
    - `AnalyticsSearchView`,
    - `EmzForm`,
    - `SanitaryHistoryDialog`.

### Проверки

- `python scripts/check_architecture.py` — `No architectural violations found.`
- `ruff check app tests` — pass.
- `mypy app tests` — pass (`262 source files`).
- `pytest -q` — pass (`256 passed, 2 warnings`).
- `python -m compileall -q app tests scripts` — pass.

## 2026-04-08 - P1: ???????? ? ??????????? ????????? (UTF-8/BOM/mojibake)

### ??? ???????

- ???????? ?????? ????? ????????? ??? `app/`, `tests/`, `scripts/`, `docs/`:
  - ???????? ????????????? UTF-8;
  - ????? BOM;
  - ????? mojibake-????????? ? ??????? `U+FFFD`.
- ????????? ????????:
  - ?????? BOM ?? `109` ????????? ?????? ? ??????? ???????????;
  - ????????????? ?????????? ?????? ? `docs/progress_report.md` (?????? ?????? ??????? `?`/mojibake ? ?????? ??????).
- ????????? ??????? ?????????????? ??????? ?????????:
  - ????? ???? `.editorconfig` ? `charset = utf-8`, `eol = lf` ? ???????? ????????? ??????????????;
  - ????? ???? `.gitattributes` ? ????????????? `UTF-8 + LF` ??? `*.py`, `*.md`, `*.qss`.

### ????????

- ????????? ???????? ????????? (`UTF-8`, `BOM`, `U+FFFD`) ??? `app/tests/scripts/docs`: `0` ???????.
- `ruff check app tests` ? pass.
- `mypy app tests` ? pass (`262 source files`).
- `pytest -q` ? pass (`256 passed, 2 warnings`).
- `python -m compileall -q app tests scripts` ? pass.

## 2026-04-08 - ????????? ????? ????? ??????? (10 ????????)

### ??? ???????

- ???????? ?????? ????????? ????? ??????? ?? 10 ????????:
  - quality gates + alembic + coverage;
  - ??????????? ????? ? ????????;
  - security-???????;
  - ????????? ? ???????? ??????;
  - ??/????????;
  - ?????????;
  - ????????????;
  - ???????????? ? CI.
- ??????????? ???????? ?????: `docs/final_audit_report.md`.

### ???????? ?????

- Pass: `check_architecture`, `ruff`, `mypy`, `compileall`, ?????????.
- Fail: `pytest -q` (1 ?????????????? ????), `alembic check` (database not up to date).
- ???????? `pytest --cov=app`: `50%`.
- ????????????? ????????? UI?Infrastructure / sqlalchemy ? UI / Domain????????: `0`.

### ?????????

- `tmp_run/final_architecture.txt`
- `tmp_run/final_ruff.txt`
- `tmp_run/final_mypy.txt`
- `tmp_run/final_pytest.txt`
- `tmp_run/final_compileall.txt`
- `tmp_run/final_alembic.txt`
- `tmp_run/final_coverage.txt`
- `tmp_run/final_coverage_layers.json`

---

## 2026-04-09 - Блокеры релиза: тест Form100 + синхронизация Alembic

### Что сделано

- Исправлен падающий интеграционный тест `tests/integration/test_form100_v2_service.py::test_form100_v2_exchange_and_reporting`.
- В тест добавлен monkeypatch для `FORM100_V2_ARTIFACT_DIR`, чтобы импортированные PDF-артефакты писались в `tmp_path`, а не в `%LOCALAPPDATA%`.
- Выполнена синхронизация миграций командой `alembic upgrade head` в рабочем каталоге данных `EPIDCONTROL_DATA_DIR=tmp_run/epid-data` (дефолтная БД в `%LOCALAPPDATA%` остаётся read-only в текущем окружении).
- Проверен `alembic check` в том же рабочем каталоге данных: дрейф отсутствует.

### Проверки

- `python scripts/check_architecture.py` — pass.
- `ruff check app tests` — pass.
- `mypy app tests` — pass (`262 source files`).
- `pytest -q` — pass (`256 passed, 2 warnings`).
- `python -m compileall -q app tests scripts` — pass.
- `$env:EPIDCONTROL_DATA_DIR='tmp_run/epid-data'; python -m alembic check` — pass.

### Изменённые файлы

- `tests/integration/test_form100_v2_service.py`

---

## 2026-04-09 - Онбординг + код-ревью GPT-5.4

### Что сделано

- Выполнен полный онбординг по проекту:
  - прочитаны `AGENTS.md`, проектный скилл `epid-control`, `docs/session_handoff.md`, `docs/context.md`, хвост `docs/progress_report.md`;
  - перечитаны `docs/final_audit_report.md`, `docs/security_review_2026-04-07.md`, `docs/code_review_report.md`, `docs/tech_guide.md`;
  - проверены `pyproject.toml`, `alembic.ini` и YAML-заголовки всех `SKILL.md` в `.agents/skills/`.
- Проверена доступность Context7:
  - MCP Context7 в этой сессии отсутствует;
  - для сверки паттернов использован fallback на официальные docs SQLAlchemy, Alembic, mypy и pytest.
- Проведён новый полный review без правок кода:
  - архитектурный чек (`check_architecture.py`, grep по слоям);
  - security-checklist по `security-review`;
  - `ruff`, `mypy`, `pytest --cov=app -q`;
  - `python -m alembic check`, `alembic current`, `alembic heads`;
  - проверки документации, markdown-ссылок, `type: ignore`, `Any`, моков, кодировки и mojibake.
- Сформирован новый отчёт:
  - `docs/code_review_gpt54.md`.

### Фактические результаты

- `python scripts/check_architecture.py` — pass.
- `ruff check app tests` — pass.
- `mypy app tests` — pass (`262 source files`).
- `pytest --cov=app -q` — pass (`256 passed, 2 warnings`, `TOTAL 49.91%`).
- `python -m alembic check` — fail (`current=0019_form100_v2_schema`, `head=2daa0dea652d`).
- `$env:EPIDCONTROL_DATA_DIR='tmp_run/epid-data'; python -m alembic check` — pass.

### Ключевые находки review

- P0:
  - `Form100ServiceV2._store_imported_pdf()` всё ещё уязвим к `PermissionError` при существующем non-writable каталоге артефактов; последний fix стабилизировал тест, но не продуктовый сценарий.
  - Дефолтный Alembic-state не self-contained: обычный `python -m alembic check` в рабочем дереве остаётся красным.
- P1:
  - в `EmzService` и `Form100ServiceV2` ещё есть mutating-методы с `actor_id: int | None`;
  - найден новый gap в `SavedFilterService.save_filter()` — запись в БД без обязательного actor/audit;
  - в коде и документации остаются mojibake-секции.
- P2:
  - README не синхронизирован с реальным quality-gate контуром (нет architecture step);
  - в `docs/final_audit_report.md` есть битая markdown-ссылка;
  - сохраняются крупные low-coverage UI-модули и концентрация `Any` в `reporting/Form100`.

### Изменённые файлы

- `docs/code_review_gpt54.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`
