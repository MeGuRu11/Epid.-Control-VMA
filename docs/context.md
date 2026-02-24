# context.md — План проекта (Desktop-приложение на Python: ЭМЗ + микробиология + аналитика)

> Этот документ — единый «контекст» для AI agent Codex: архитектура, техстек, структура проекта, схема БД (ER), use-cases, карта UI (Qt), этапы разработки, правила качества.
> Цель: быстро и безопасно реализовать MVP под **Windows**, сохранив кроссплатформенность (Linux) без переделок.

---

## Статус работ (кратко)

Готово:

- Этапы I-IV из мастер-плана: backup, лабораторный QC/нумерация, ИСМП, аналитика.
- Этапы 1-5 основной дорожной карты: auth/users, EMR с версиями, лабораторный модуль, санитарные пробы, поиск/аналитика, импорт/экспорт (Excel/CSV/PDF/ZIP) и история пакетов.
- Блоки отчётности и производительности: артефакты + SHA256 + история отчётов, индексы, оптимизация тяжёлых запросов, кэш расчётов аналитики.
- Локализация основных UI на русский.
- Исправлены ключевые ошибки валидации и рекурсивного сброса контекста; добавлены сообщения об ошибках.
- Долгие операции переведены в фон (импорт/экспорт/отчеты/бэкапы, аналитика, поиск пациента).
- Локальные quality-gates: `ruff`, `mypy`, `pytest`, `compileall` — зелёные.

В процессе:

- P2: остаточная декомпозиция UI-файлов и ручной регрессионный прогон.
- Form100 V2: стабилизация и ручная приемка на целевых разрешениях/DPI.

Далее:

- Отложенный до финального этапа: UX-дефолты (Этап V).
- Завершить P2: декомпозиция остаточных UI-модулей.
- Ручной регрессионный UI прогон по чек-листу (см. раздел 14.4).

---

## 0) Краткое описание продукта

Desktop-приложение для:

- ведения **ЭМЗ (электронной медицинской записи)** пациента в стационаре;
- ведения **микробиологических лабораторных проб** пациента (микробиология, чувствительность к АМП, бактериофаги);
- ведения **санитарной микробиологии отделений**;
- **поиска**, **аналитики** и **визуализаций** (графики/гистограммы);
- **импорта/экспорта** данных и отчётов между этапами/подразделениями;
- соблюдения требований: история изменений, неизменяемость отчётных форм (через артефакты + хэш), аудит действий.

---

## 1) Основные принципы (Windows-first, Linux-ready)

### 1.1 Кроссплатформенность без боли

- Никаких win32-only зависимостей в core (pywin32 — только отдельным опциональным модулем, если понадобится).
- Пути — только `pathlib`, конфиги/данные — через `platformdirs`.
- Хранение данных — SQLite (локальный файл), не требующий сервера.
- Сборка: PyInstaller (Windows), затем PyInstaller для Linux (или AppImage при необходимости).

### 1.2 Безопасность и целостность

- Пароли — хэш (argon2/bcrypt).
- Аудит действий в `audit_log`.
- «Неизменяемость» форм отчётов: сохраняем файлы-артефакты + SHA256 (для верификации).
- История данных: версионирование записей ЭМЗ (и при необходимости иных сущностей).

---

## 2) Технический стек

### 2.1 Ядро

- Python: **3.11+**
- GUI: **PySide6 (Qt6)**
- БД: **SQLite**
- ORM: **SQLAlchemy 2.x**
- Миграции: **Alembic**
- Схемы/валидация: **pydantic** (для импорт/экспорт и входных DTO)

### 2.2 Отчёты/экспорт

- XLSX: `openpyxl`
- PDF: `reportlab` (если нужен печатный официальный вид)
- CSV/JSON: стандартная библиотека + pydantic

### 2.3 Графики

- `pyqtgraph` (быстро в Qt) **или** `matplotlib` (надёжно, но тяжелее)

### 2.4 Качество/инфраструктура

- Форматирование: `black`
- Линтинг: `ruff`
- Типы: `mypy` (по мере готовности)
- Тесты: `pytest`
- pre-commit: `pre-commit`
- CI (позже): GitHub Actions (Windows build + Linux smoke build)

### 2.5 Сборка/дистрибуция

- PyInstaller (Windows .exe)
- (опционально) Inno Setup / NSIS для установщика

---

## 3) Архитектура

### 3.1 Слои

- **UI (Qt)**: виджеты, модели таблиц, навигация.
- **Application**: use-cases (сервисы), транзакции, DTO.
- **Domain**: сущности, правила, вычисления показателей.
- **Infrastructure**: БД/репозитории, импорт/экспорт, отчёты, аудит, хэширование артефактов.

### 3.2 Стиль

Мини-Clean Architecture:

- UI → Application → Domain → Infrastructure
- Зависимости направлены внутрь (Domain не знает про Qt/SQLAlchemy).

### 3.3 Версионирование данных

Для ЭМЗ используем:

- `emr_case` (контейнер госпитализации)
- `emr_case_version` (версии формы, `is_current`, `valid_from`, `valid_to`)

Любое «редактирование» ЭМЗ = создание новой версии + закрытие предыдущей.

---

## 4) Структура репозитория

```text
app/
  main.py
  config.py
  ui/
    main_window.py
    login_dialog.py
    emr/
      emr_form.py
      emr_models.py
    lab/
      lab_samples_view.py
      lab_sample_detail.py
      lab_models.py
    sanitary/
      sanitary_dashboard.py
      sanitary_history.py
    analytics/
      analytics_view.py
      charts.py
    references/
      reference_editor.py
  application/
    dto/
      emr_dto.py
      lab_dto.py
      analytics_dto.py
      exchange_dto.py
    services/
      auth_service.py
      user_admin_service.py
      emr_service.py
      lab_service.py
      sanitary_service.py
      analytics_service.py
      reporting_service.py
      exchange_service.py
  domain/
    models/
      emr.py
      lab.py
      sanitary.py
      references.py
    calculations/
      incidence.py
      prevalence.py
      stratified.py
    rules/
      validation.py
  infrastructure/
    db/
      engine.py
      session.py
      models_sqlalchemy.py
      repositories/
        user_repo.py
        emr_repo.py
        lab_repo.py
        sanitary_repo.py
        reference_repo.py
        report_repo.py
        exchange_repo.py
      migrations/   # alembic
    export/
      export_json.py
      export_zip.py
    import/
      import_json.py
      import_zip.py
    reporting/
      report_xlsx.py
      report_pdf.py
    audit/
      audit_logger.py
    security/
      password_hash.py
      sha256.py
tests/
  unit/
  integration/
resources/
  icons/
  templates/
```

---

## 5) База данных — ER-модель (таблицы, поля, связи, индексы)

> Нотация: PK — первичный ключ, FK — внешний ключ. Типы SQLite: INTEGER, TEXT, REAL, DATE/DATETIME.

### 5.1 Пользователи и аудит

#### `users`

- `id` INTEGER PK
- `login` TEXT UNIQUE NOT NULL  (используется как ФИО ответственного лица)
- `password_hash` TEXT NOT NULL
- `role` TEXT NOT NULL CHECK IN ('admin','operator')
- `is_active` INTEGER NOT NULL DEFAULT 1
- `created_at` DATETIME NOT NULL

### Индексы: `users`

- `ux_users_login`(login)

#### `audit_log`

- `id` INTEGER PK
- `event_ts` DATETIME NOT NULL
- `user_id` INTEGER FK → users.id
- `entity_type` TEXT NOT NULL
- `entity_id` TEXT NOT NULL
- `action` TEXT NOT NULL
- `payload_json` TEXT

### Индексы: `audit_log`

- `(event_ts)`
- `(user_id, event_ts)`
- `(entity_type, entity_id)`

---

### 5.2 Справочники (references)

#### `departments`

- `id` INTEGER PK
- `name` TEXT UNIQUE NOT NULL

**Индексы**: `ux_departments_name`(name)

#### `ref_icd10`

- `code` TEXT PK
- `title` TEXT NOT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1

### Индексы: `ref_icd10`

- `(title)` (+ опционально FTS5)

#### `ref_microorganisms`

- `id` INTEGER PK
- `code` TEXT UNIQUE
- `name` TEXT NOT NULL
- `taxon_group` TEXT
- `is_active` INTEGER NOT NULL DEFAULT 1

### Индексы: `ref_microorganisms`

- `(code)`
- `(name)` (+ опционально FTS5)
- `(taxon_group)`

#### `ref_antibiotic_groups`

- `id` INTEGER PK
- `code` TEXT UNIQUE
- `name` TEXT NOT NULL

#### `ref_antibiotics`

- `id` INTEGER PK
- `code` TEXT UNIQUE
- `name` TEXT NOT NULL
- `group_id` INTEGER FK → ref_antibiotic_groups.id

### Индексы: `ref_antibiotics`

- `(name)`
- `(group_id)`

#### `ref_phages`

- `id` INTEGER PK
- `code` TEXT UNIQUE
- `name` TEXT NOT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1

#### `ref_material_types`

- `id` INTEGER PK
- `code` TEXT UNIQUE NOT NULL
- `name` TEXT NOT NULL

---

### 5.3 Пациенты и ЭМЗ (версионно)

#### `patients`

- `id` INTEGER PK
- `full_name` TEXT NOT NULL
- `dob` DATE
- `sex` TEXT CHECK IN ('M','F','U') DEFAULT 'U'
- `category` TEXT
- `military_unit` TEXT
- `military_district` TEXT
- `created_at` DATETIME NOT NULL

### Индексы: `patients`

- `(full_name)` (+ опционально FTS5)
- `(dob)`
- `(sex)`

#### `emr_case`  (контейнер госпитализации)

- `id` INTEGER PK
- `patient_id` INTEGER FK → patients.id NOT NULL
- `hospital_case_no` TEXT NOT NULL   (номер и/б)
- `department_id` INTEGER FK → departments.id
- `created_at` DATETIME NOT NULL
- `created_by` INTEGER FK → users.id

### Ограничения/Индексы: `emr_case`

- UNIQUE `(patient_id, hospital_case_no)`
- `(department_id)`
- `(hospital_case_no)`

#### `emr_case_version`  (версия ЭМЗ)

- `id` INTEGER PK
- `emr_case_id` INTEGER FK → emr_case.id NOT NULL
- `version_no` INTEGER NOT NULL
- `valid_from` DATETIME NOT NULL
- `valid_to` DATETIME NULL
- `is_current` INTEGER NOT NULL
- `entered_by` INTEGER FK → users.id

### Поля формы

- `admission_date` DATE
- `injury_date` DATE
- `outcome_date` DATE
- `outcome_type` TEXT
- `severity` TEXT
- `vph_sp_score` INTEGER
- `vph_p_or_score` INTEGER
- `sofa_score` INTEGER

### Авто-кэш (для скорости отчётов)

- `days_to_admission` INTEGER
- `length_of_stay_days` INTEGER

### Ограничения/Индексы: `emr_case_version`

- UNIQUE `(emr_case_id, version_no)`
- `(emr_case_id, is_current)`
- `(admission_date)`
- `(outcome_date)`
- `(severity)`
- `(sofa_score)`

#### `emr_diagnosis`

- `id` INTEGER PK
- `emr_case_version_id` INTEGER FK → emr_case_version.id NOT NULL
- `kind` TEXT CHECK IN ('admission','discharge','complication')
- `icd10_code` TEXT FK → ref_icd10.code
- `free_text` TEXT

### Индексы: `emr_diagnosis`

- `(emr_case_version_id)`
- `(icd10_code)`
- `(kind, icd10_code)`

#### `emr_intervention`

- `id` INTEGER PK
- `emr_case_version_id` INTEGER FK → emr_case_version.id NOT NULL
- `type` TEXT NOT NULL  (central_catheter / urinary_catheter / ventilation / surgery / …)
- `start_dt` DATETIME
- `end_dt` DATETIME
- `duration_minutes` INTEGER
- `performed_by` TEXT
- `notes` TEXT

### Индексы: `emr_intervention`

- `(emr_case_version_id, type)`
- `(type, start_dt)`

#### `emr_antibiotic_course`

- `id` INTEGER PK
- `emr_case_version_id` INTEGER FK → emr_case_version.id NOT NULL
- `start_dt` DATETIME
- `end_dt` DATETIME
- `antibiotic_id` INTEGER FK → ref_antibiotics.id
- `drug_name_free` TEXT
- `route` TEXT
- `dose` TEXT

### Индексы: `emr_antibiotic_course`

- `(emr_case_version_id)`
- `(antibiotic_id)`
- `(start_dt)`

---

### 5.4 Микробиологические пробы пациента

#### `lab_number_sequence`  (ежедневная нумерация по виду материала)

- `id` INTEGER PK
- `seq_date` DATE NOT NULL
- `material_type_id` INTEGER FK → ref_material_types.id NOT NULL
- `last_number` INTEGER NOT NULL
- UNIQUE `(seq_date, material_type_id)`

#### `lab_sample`

- `id` INTEGER PK
- `patient_id` INTEGER FK → patients.id NOT NULL
- `emr_case_id` INTEGER FK → emr_case.id
- `lab_no` TEXT NOT NULL UNIQUE
- `barcode` TEXT
- `material_type_id` INTEGER FK → ref_material_types.id NOT NULL
- `material_location` TEXT
- `medium` TEXT
- `study_kind` TEXT CHECK IN ('primary','repeat')
- `ordered_at` DATETIME
- `taken_at` DATETIME
- `delivered_at` DATETIME
- `growth_result_at` DATETIME
- `growth_flag` INTEGER CHECK IN (0,1)
- `colony_desc` TEXT
- `microscopy` TEXT
- `cfu` TEXT
- `created_at` DATETIME NOT NULL
- `created_by` INTEGER FK → users.id

### Индексы: `lab_sample`

- `(patient_id, taken_at)`
- `(material_type_id, taken_at)`
- `(growth_flag, growth_result_at)`
- `(emr_case_id)`

#### `lab_microbe_isolation`

- `id` INTEGER PK
- `lab_sample_id` INTEGER FK → lab_sample.id NOT NULL
- `microorganism_id` INTEGER FK → ref_microorganisms.id
- `microorganism_free` TEXT
- `notes` TEXT

### Индексы: `lab_microbe_isolation`

- `(lab_sample_id)`
- `(microorganism_id)`

#### `lab_abx_susceptibility`

- `id` INTEGER PK
- `lab_sample_id` INTEGER FK → lab_sample.id NOT NULL
- `antibiotic_id` INTEGER FK → ref_antibiotics.id NOT NULL
- `group_id` INTEGER FK → ref_antibiotic_groups.id
- `ris` TEXT CHECK IN ('R','I','S')
- `mic_mg_l` REAL
- `method` TEXT

### Индексы: `lab_abx_susceptibility`

- `(lab_sample_id)`
- `(antibiotic_id, ris)`
- `(group_id, ris)`

#### `lab_phage_panel_result`

- `id` INTEGER PK
- `lab_sample_id` INTEGER FK → lab_sample.id NOT NULL
- `phage_id` INTEGER FK → ref_phages.id
- `phage_free` TEXT
- `lysis_diameter_mm` REAL

### Индексы: `lab_phage_panel_result`

- `(lab_sample_id)`
- `(phage_id)`

---

### 5.5 Санитарная микробиология отделения

#### `sanitary_sample`

- `id` INTEGER PK
- `department_id` INTEGER FK → departments.id NOT NULL
- `room` TEXT
- `sampling_point` TEXT NOT NULL
- `lab_no` TEXT NOT NULL UNIQUE
- `barcode` TEXT
- `medium` TEXT
- `ordered_at` DATETIME
- `taken_at` DATETIME
- `delivered_at` DATETIME
- `growth_result_at` DATETIME
- `growth_flag` INTEGER CHECK IN (0,1)
- `colony_desc` TEXT
- `microscopy` TEXT
- `cfu` TEXT
- `created_at` DATETIME NOT NULL
- `created_by` INTEGER FK → users.id

### Индексы: `sanitary_sample`

- `(department_id, taken_at)`
- `(growth_flag, growth_result_at)`

Дочерние таблицы аналогичны lab_*:

- `san_microbe_isolation`
- `san_abx_susceptibility`
- `san_phage_panel_result`

---

### 5.6 Отчёты и пакеты обмена

#### `report_run`

- `id` INTEGER PK
- `created_at` DATETIME NOT NULL
- `created_by` INTEGER FK → users.id
- `report_type` TEXT NOT NULL
- `filters_json` TEXT NOT NULL
- `result_summary_json` TEXT NOT NULL
- `artifact_path` TEXT
- `artifact_sha256` TEXT

### Индексы: `report_run`

- `(created_at)`
- `(report_type, created_at)`

#### `data_exchange_package`

- `id` INTEGER PK
- `direction` TEXT CHECK IN ('export','import')
- `created_at` DATETIME NOT NULL
- `created_by` INTEGER FK → users.id
- `package_format` TEXT NOT NULL
- `file_path` TEXT NOT NULL
- `sha256` TEXT NOT NULL
- `notes` TEXT

### Индексы: `data_exchange_package`

- `(direction, created_at)`

---

## 6) Use-cases (Application layer)

> Формат: **Input → Checks → Changes → Output**

### 6.1 Auth / Users

#### UC-A1: Login

- Input: `login`, `password`
- Checks: user exists + active; password matches hash
- Changes: `audit_log` action='login'
- Output: session context (user_id, role, login)

#### UC-A2: Create user (admin)

- Input: admin session, login, password, role
- Checks: session.role == 'admin'; login unique; password policy
- Changes: insert users; audit
- Output: new user id

#### UC-A3: Deactivate / reset password (admin)

- Input: admin session, user_id, action
- Checks: admin privileges
- Changes: update users; audit
- Output: success

---

### 6.2 EMR (ЭМЗ)

#### UC-E1: Create patient + hospital case + initial EMR version

- Input: patient identity fields + hospital_case_no + department
- Checks: required fields (or 'н/д'); dates consistent
- Changes: upsert patients; insert emr_case; insert emr_case_version(version=1, current)
- Output: emr_case_id + emr_case_version_id

#### UC-E2: Update EMR (create new version)

- Input: emr_case_id + full form payload (including diagnoses/interventions/abx courses)
- Checks: required fields; date rules; compute:
  - days_to_admission = admission - injury (if both)
  - length_of_stay_days = outcome - admission (if both)
- Changes:
  - close previous version (is_current=0, valid_to=now)
  - insert new version (version_no+1, is_current=1)
  - replace child records under new version
  - audit
- Output: new version id + computed fields

#### UC-E3: Manage diagnoses (МКБ-10)

- Input: emr_case_version_id + list of diagnoses (kind, code, free_text)
- Checks: ICD code exists or free_text present
- Changes: replace emr_diagnosis for that version
- Output: stored list

#### UC-E4: Manage interventions (risk factors)

- Input: emr_case_version_id + list of interventions
- Checks: start<=end (if both); type allowed
- Changes: replace emr_intervention
- Output: stored list + aggregates per type (days/min)

#### UC-E5: Manage antibiotic courses

- Input: emr_case_version_id + list
- Checks: start<=end; antibiotic exists or free name provided
- Changes: replace emr_antibiotic_course
- Output: stored list

---

### 6.3 Patient microbiology

#### UC-L1: Create lab sample with daily auto-numbering

- Input: patient_id, material_type_id, optional fields (dates, barcode, medium, etc.)
- Checks: patient exists; material type exists
- Changes:
  - increment `lab_number_sequence` for (today, material_type)
  - generate `lab_no` (pattern: `{MATCODE}-{YYYYMMDD}-{####}`)
  - insert lab_sample; audit
- Output: lab_sample with lab_no

#### UC-L2: Update lab sample result + microbe isolation

- Input: lab_sample_id + growth/morphology/microscopy/CFU + microorganism (ref or free)
- Checks: if ref used, exists; if free, not empty
- Changes: update lab_sample; upsert lab_microbe_isolation; audit
- Output: updated detail model

#### UC-L3: Update antibiotic susceptibility panel (RIS/MIC)

- Input: lab_sample_id + list rows (antibiotic_id, ris, mic, method)
- Checks: ris in {R,I,S}; antibiotic exists
- Changes: replace lab_abx_susceptibility; audit
- Output: panel

#### UC-L4: Update phage panel results

- Input: lab_sample_id + list rows (phage_id/free, diameter)
- Checks: diameter>=0
- Changes: replace lab_phage_panel_result; audit
- Output: panel

---

### 6.4 Sanitary microbiology

#### UC-S1: Create sanitary sample

- Input: department_id, sampling_point, dates, medium, etc.
- Checks: department exists; required fields present
- Changes: insert sanitary_sample (own numbering strategy); audit
- Output: sanitary_sample

#### UC-S2: Update sanitary result/panels

- Same as UC-L2/L3/L4 but for san_* tables

---

### 6.5 Search / Analytics / Reports

#### UC-R1: Search cases/samples by filters

- Input: date interval + optional filters:
  - ICD-10 codes, severity/scores, hospital_case_no, lab_no, department, category, patient name, sex,

    unit/district, antibiotic, microorganism/group, material type, growth_flag, etc.

- Checks: from<=to
- Changes: none
- Output: list results + aggregates (counts)

#### UC-R2: Calculate epidemiological indicators

- Input: dataset + multiplier (e.g., 100/1000)
- Checks: denominator data available (bed-days, device-days etc.)
- Changes: optional cache to report_run
- Output:
  - cumulative incidence (n/N * 10^k)
  - incidence density (n/pT)
  - prevalence (P/N)
  - stratified incidence for device-associated infections

#### UC-R3: Generate charts/histograms

- Input: dataset + grouping period (day/week/month/year) + chart type
- Checks: dataset non-empty
- Changes: optional store image/summary
- Output: chart data models (for pyqtgraph/matplotlib)

#### UC-R4: Persist report run (artifact + hash)

- Input: report_type, filters, summary, artifact file (optional)
- Checks: file exists if provided
- Changes: insert report_run + sha256
- Output: report_run id

---

### 6.6 Import / Export

#### UC-X1: Export package

- Input: selected entities + format (json/zip)
- Checks: permissions; schema version
- Changes: write file; sha256; insert data_exchange_package(export); audit
- Output: file path + metadata

#### UC-X2: Import package

- Input: package file
- Checks: sha256; schema version; integrity
- Changes: upsert entities; insert data_exchange_package(import); audit
- Output: import summary (added/updated/skipped)

---

## 7) UI (PySide6) — карта экранов и виджетов

### 7.1 Навигационный каркас

- `MainWindow(QMainWindow)` + `QStackedWidget` — контейнер всех разделов.
- Верхнее меню (`QMenuBar`) содержит разделы:
  - `Главная`, `ЭМЗ`, `Форма 100`, `Поиск и ЭМК`, `Лаборатория`, `Санитария`, `Аналитика`, `Импорт/Экспорт`, `Справочники`, `Администрирование`.
- Контекстная панель (`ContextBar`) закрепляет пациента/госпитализацию и даёт быстрые переходы в рабочие разделы.
- Ролевое ограничение:
  - `Администрирование` доступно только роли `admin`;
  - роли в проекте: `admin`, `operator`.

### 7.2 Структура разделов приложения

| Раздел | Назначение | Ключевой функционал | Роли | Основной UI-файл |
| --- | --- | --- | --- | --- |
| Главная | Оперативная сводка системы | Счётчики по пациентам/ЭМЗ/пробам, топ-отделение, последний вход, часы | `admin`, `operator` | `app/ui/home/home_view.py` |
| ЭМЗ | Ведение госпитализации пациента | Создание/редактирование ЭМЗ, данные пациента, диагнозы, интервенции, антибиотики, ИСМП, валидации | `admin`, `operator` | `app/ui/emz/emz_form.py` |
| Форма 100 | Карточка медицинской эвакуации | Поиск карточек, create/update/sign (`DRAFT -> SIGNED`), этапы, bodymap, ZIP/PDF | `admin`, `operator` | `app/ui/form100/form100_view.py` |
| Поиск и ЭМК | Поиск пациента и история госпитализаций | Поиск по ФИО/ID, карточка пациента, фильтры госпитализаций, переход в ЭМЗ/Лаб, удаление | `admin`, `operator` | `app/ui/patient/patient_emk_view.py` |
| Лаборатория | Работа с лабораторными пробами | Фильтры, пагинация, карточка пробы, создание/редактирование, переход к пациенту | `admin`, `operator` | `app/ui/lab/lab_samples_view.py` |
| Санитария | Санитарная микробиология отделений | Сводка по отделениям, фильтры, история проб отделения | `admin`, `operator` | `app/ui/sanitary/sanitary_dashboard.py` |
| Аналитика | Поиск и аналитическая отчётность | Расширенные фильтры, агрегаты, тренды, ИСМП-метрики, история отчётов, экспорт XLSX/PDF | `admin`, `operator` | `app/ui/analytics/analytics_view.py` |
| Импорт/Экспорт | Обмен данными | Мастер импорта/экспорта (Excel/CSV/PDF/ZIP/Form100 ZIP), предпросмотр, история пакетов | `admin`, `operator` | `app/ui/import_export/import_export_view.py` |
| Справочники | Ведение НСИ | CRUD справочников (МКБ, микроорганизмы, антибиотики, материалы, отделения и др.) | чтение: `operator`, изменение: `admin` | `app/ui/references/reference_view.py` |
| Администрирование | Управление пользователями и обслуживанием | Пользователи, аудит, резервные копии (создать/восстановить) | только `admin` | `app/ui/admin/user_admin_view.py` |

### 7.3 Сквозные UI-сценарии

- Контекст пациента/госпитализации:
  - задаётся через `ContextBar`;
  - синхронизируется между `ЭМЗ`, `Поиск и ЭМК`, `Лаборатория`;
  - при logout выполняется очистка контекста.
- Обновление справочников:
  - изменение в `Справочники` инициирует обновление ссылочных данных в зависимых разделах.
- Обновление сводки на главной:
  - после изменения данных в рабочих модулях устанавливается флаг «грязной» сводки;
  - при возврате на `Главная` выполняется refresh.

### 7.4 Служебные окна авторизации

- `LoginDialog(QDialog)`:
  - вход по логину/паролю;
  - при успехе открывается `MainWindow`.
- `FirstRunDialog(QDialog)`:
  - показывается на «чистой» базе;
  - создаёт первого пользователя с ролью `admin`.

---

## 8) Индексы под поиск (минимальный набор)

> Реальный «ускоритель» для фильтров и отчётов.

- `patients(full_name)` (+ FTS5 по ФИО)
- `emr_case(hospital_case_no)`
- `emr_case(department_id)`
- `emr_case_version(admission_date)`, `emr_case_version(outcome_date)`, `emr_case_version(severity)`, `emr_case_version(sofa_score)`
- `emr_diagnosis(icd10_code)`, `emr_diagnosis(kind, icd10_code)`
- `lab_sample(lab_no) UNIQUE`, `lab_sample(patient_id, taken_at)`, `lab_sample(material_type_id, taken_at)`, `lab_sample(growth_flag, growth_result_at)`
- `lab_microbe_isolation(microorganism_id)`
- `lab_abx_susceptibility(antibiotic_id, ris)`
- `sanitary_sample(department_id, taken_at)`, `sanitary_sample(growth_flag, growth_result_at)`

Опционально:

- SQLite FTS5 таблицы для `patients.full_name`, `ref_microorganisms.name`, `ref_icd10.title`.

---

## 9) Этапы разработки (roadmap)

### Этап 0: Подготовка

- Репозиторий, pre-commit, black/ruff/pytest, базовая структура модулей.
- Alembic init, engine/session, конфиг через platformdirs.

### Этап 1: MVP-скелет

- Login (UC-A1), users (UC-A2/UC-A3).
- Базовые справочники (departments, ICD, microbes, antibiotics, phages, materials).
- EMR: patients/emr_case/emr_case_version + сохранение формы (UC-E1/UC-E2).

### Этап 2: Лабораторный модуль пациента

- Авто-нумерация (lab_number_sequence) + создание пробы (UC-L1).
- Карточка пробы, микроорганизм, панель RIS/MIC, панель фагов (UC-L2/L3/L4).

### Этап 3: Санитарная микробиология

- Dashboard отделений + история проб (UC-S1/S2).

### Этап 4: Поиск и аналитика

- Фильтры, таблица результатов (UC-R1).
- Расчёты показателей (UC-R2).
- Графики/гистограммы (UC-R3).
- Сохранение отчётов/артефактов (UC-R4).

### Этап 5: Импорт/экспорт

- Формат пакета (JSON/ZIP) + схемы pydantic.
- Экспорт/импорт с sha256 и журналом (UC-X1/UC-X2).

### Этап 6: Полировка и релиз

- Улучшение UX, обработка ошибок, локализация.
- PyInstaller build Windows, smoke build Linux.
- Документация пользователя + техдок.

---

## 10) Правила качества и соглашения

### 10.1 Правила кодстайла

- black, ruff — обязательно.
- типизация: новые сервисы и DTO стараться писать с typing.

### 10.2 Тестирование

- Domain calculations — unit tests (формулы/правила).
- Repositories — integration tests (SQLite in temp dir).
- Application services — unit/integration (transaction boundaries).

### 10.3 Транзакции

- Каждый use-case выполняется в одной транзакции (begin/commit/rollback).
- При ошибке — rollback + запись в audit_log (action='error' + payload).

### 10.4 Обработка «н/д»

- Для обязательных текстовых полей, если нет данных, UI предлагает/подставляет `н/д`.
- В БД хранить как TEXT 'н/д' (или NULL для необязательных), но единообразно в DTO/валидации.

### 10.5 Генерация номеров проб

- Реализовать атомарно:
  - read+update lab_number_sequence в транзакции,
  - затем insert lab_sample.
- Шаблон номера: `{material_code}-{YYYYMMDD}-{seq:04d}` (можно вынести в config).

### 10.6 Проверки после изменений

- После любых нововведений или изменений обязательно прогонять:
  - `python -m ruff check .`
  - `python -m pytest`

### 10.7 Обязательная самопроверка (консолидация из MASTER_TZ)

- Код запускается без синтаксических ошибок и без падений на старте.
- Импорты и типизация корректны (`ruff` + `mypy`).
- Логика соответствует текущим use-cases этого документа.
- Миграции добавлены и применимы, если менялась схема БД.
- UI-поведение проверено для затронутых сценариев.
- Аудит/безопасность не деградировали после изменений.

---

## 11) Формат обмена (черновик)

### 11.1 JSON schema versioning

- `schema_version`: "1.0"
- `exported_at`, `exported_by`
- `patients[]`, `emr_cases[]`, `emr_case_versions[]`, `lab_samples[]`, `lab_panels[]`, `sanitary_samples[]`, `reports[]`

### 11.2 ZIP пакет

- `manifest.json` (метаданные + sha256 каждого файла)
- `data.json`
- `artifacts/` (pdf/xlsx)

---

## 12) Что Codex должен сделать «в первую очередь» (порядок реализации)

> Раздел исторический (этапы запуска проекта); текущий актуальный план см. в разделе 14.

1) Инициализация проекта + база инфраструктуры БД и миграций.
2) Реализация users/auth + простая админка.
3) Реализация EMR form (сохранение версии).
4) Реализация lab module (авто-нумерация + карточка пробы + панели).
5) Санитарные пробы.
6) Поиск/аналитика/графики.
7) Отчёты/артефакты.
8) Импорт/экспорт.

---

## 13) TODO (вопросы на потом, не блокируют старт)

- Уточнить точный перечень вмешательств (enum) и формулы для “device-days” в отчётах.
- Уточнить состав отчётов (PDF/XLSX шаблоны) и обязательные поля на печати.
- Решить, нужно ли шифрование БД на диске (SQLCipher).
- Решить: FTS5 для ФИО/МКБ/микроорганизмов (скорость vs сложность).

---

## 14) Консолидированный план работ (актуально на 2026-02-13)

### 14.1 Статус консолидации

- Главный и единственный актуальный документ планирования: `docs/context.md`.
- Смысловые блоки из прежних файлов аудита и мастер-ТЗ интегрированы в этот раздел.
- При расхождении старых формулировок и текущего статуса ориентироваться только на этот файл.

### 14.2 Трекинг этапов мастер-плана (детализация)

- Этап I `Резервное копирование` — закрыт:
  - ручной backup;
  - автобэкап (>= 24h);
  - восстановление из admin;
  - аудит событий `backup_create/backup_restore`.
- Этап II `Лабораторный QC и нумерация` — закрыт:
  - QC-сроки: кровь 2h, прочие 6h;
  - QC-статусы: `valid/conditional/rejected`;
  - нумерация проб формата `TYPE-YEAR-COUNTER`.
- Этап III `ИСМП` — закрыт:
  - отдельная сущность ИСМП;
  - тип/дата начала/связь с госпитализацией;
  - корректный перечень типов в БД (`ВАП`, `КА-ИК`, `КА-ИМП`, `ИОХВ`, `ПАП`, `БАК`, `СЕПСИС`).
- Этап IV `Аналитика` — закрыт:
  - инцидентность;
  - плотность инцидентности;
  - метрики `ВАП/КА-ИК/КА-ИМП`;
  - превалентность.
- Этап V `UX` — частично закрыт:
  - [x] сворачиваемые секции;
  - [x] быстрые действия;
  - [ ] дефолты полей (не реализованы).
- Этап VI `Форма 100 МО РФ (v2.2)` — реализован (V2 под feature-flag):
  - [x] новая схема БД `form100` + `form100_data`, миграция `0019_form100_v2_schema.py`;
  - [x] перенос данных legacy `form100_card/form100_mark/form100_stage` в V2-схему;
  - [x] V2 domain/DTO/rules/repository/service с optimistic lock и статусом `DRAFT -> SIGNED`;
  - [x] аудит `form100.audit.v2` (create/update/sign/export/import с diff key-path);
  - [x] отдельный UI-пакет `app/ui/form100_v2/**`, интеграция в `MainWindow` через флаг;
  - [x] bodymap V2 без ручного JSON-ввода (4 силуэта, ограничение рисования по контуру);
  - [x] PDF/ZIP V2 (`form100.json + form100.pdf + manifest.json`) и интеграция в `ExchangeService`/`ReportingService`.

### 14.3 Результаты аудита (этапы 1-9)

- Этап 1 `Ядро/запуск` — закрыто:
  - безопасный показ критического `QMessageBox` только при наличии `QApplication`;
  - корректное закрытие stderr-лога через `atexit`.
- Этап 2 `Модели/DTO` — закрыто:
  - исправлены ограничения `ismp_type` и выпущена миграция для пересоздания constraint в SQLite;
  - исправлены поврежденные тексты ошибок.
- Этап 3 `Сервисы/репозитории` — закрыто:
  - восстановлено корректное распознавание кровяных материалов для QC;
  - нормализованы пользовательские строки в отчетности и исключениях.
- Этап 4 `UI` — закрыто:
  - после create/edit лабораторных проб выполняется полноценный `refresh()` списка;
  - долгие import/export операции вынесены из UI-потока;
  - preview Excel переведен в `read_only=True`.
- Этап 5 `Инфраструктура` — закрыто:
  - добавлено DEBUG-логирование падений FTS fallback вместо глухого `pass`.
- Этап 6 `Runtime и безопасность` — закрыто:
  - устранен Zip Slip (`_safe_extract_zip` + валидация путей);
  - импорт Excel переведен на потоковую обработку;
  - устранены типизационные и callback-дефекты в UI/tests.
- Этап 7 `Статконтроль и БД` — закрыто:
  - quality-gates: `mypy=0 ошибок`, `ruff=OK`, `pytest=green`, `compileall=OK`;
  - БД в целостном состоянии (`integrity_check=ok`, `foreign_key_check=0`), миграции на `head`.
- Этап 8 `Унификация FTS` — закрыто:
  - FTS-логика централизована в `FtsManager` для startup/runtime repair;
  - добавлены unit/integration тесты на ensure/repair.
- Этап 9 `P0 ZIP-импорт` — закрыто:
  - сообщения об ошибках импорта детализированы (`Небезопасный ZIP-архив: ...`);
  - добавлен устойчивый fallback временного каталога;
  - добавлены интеграционные тесты malicious/missing-files сценариев.
- Итог по приоритетам аудита:
  - P0 — закрыт;
  - P1 — покрытие сервисов расширено и зафиксировано тестами;
  - P2 — основная декомпозиция `EmzForm/main/analytics` выполнена.

### 14.4 Ручной UI чек-лист регрессии

- Закрепление пациента/госпитализации:
  - выбор пациента по ID и по ФИО;
  - проверка синхронизации контекста между ЭМЗ/ЭМК/Лаб;
  - очистка пациента/госпитализации и проверка сброса контекста во всех вкладках.
- Поиск и ЭМК:
  - поиск по ID и ФИО, сброс формы, фильтры госпитализаций;
  - открытие ЭМЗ/Лаб из карточки с корректной передачей `patient_id`/`emr_case_id`.
- ЭМЗ:
  - создание новой госпитализации, редактирование;
  - валидация дат и числовых полей.
- Импорт/экспорт:
  - импорт корректного ZIP/XLSX;
  - отказ импорта ZIP с `../...` и корректное сообщение об ошибке.
- Лаборатория и санитария:
  - фильтры/пагинация;
  - создание/редактирование записей;
  - корректность обновления списков.

### 14.5 Остаточный план (что осталось сделать)

#### P1 — Обязательные незакрытые пункты

- [ ] UX-дефолты (незакрытый пункт Этапа V):
  - согласовать перечень полей и стратегию заполнения;
  - внедрить дефолты в UI/DTO/валидации;
  - добавить unit/integration тесты на применение дефолтов.
- [x] Этап VI: `Форма 100 МО РФ (v2.2)`:
  - внедрен V2-контур под feature-flag;
  - legacy-модуль сохранен как fallback;
  - добавлены unit/integration тесты V2.
- [x] Подтверждённая UX-задача `PatientEditDialog`:
  - реализован отдельный диалог редактирования пациента (`PatientEditDialog`);
  - подключены точки входа из ЭМЗ и «Поиск и ЭМК»;
  - пациентский блок ЭМЗ переведен в read-only с кнопкой «Редактировать пациента»;
  - после сохранения обновляются карточка пациента в ЭМК, read-only поля в ЭМЗ и контекст-бар.
- [x] Hotfix-регрессия по рекурсивному сбросу контекста:
  - устранен цикл `EmzForm.clear_context() -> notify_case_selection() -> MainWindow._on_case_selected() -> EmzForm.clear_context()`;
  - в `MainWindow._on_case_selected` добавлена защита от re-entrant вызовов;
  - добавлен unit-тест `tests/unit/test_main_window_context_selection.py`.

#### P2 — Техдолг и сопровождение

- [ ] Декомпозиция оставшихся крупных UI-файлов без изменения поведения:
  - [x] `app/ui/analytics/analytics_view.py` (финальный проход: история отчетов вынесена в helper-слой, дубли форматирования/ширин колонок устранены, добавлены unit-тесты);
  - [x] `app/ui/sanitary/sanitary_history.py` (вынесены фильтрация/сортировка/пагинация/summary/форматирование карточек в helper-слой + unit-тесты);
  - [x] `app/ui/lab/lab_sample_detail.py` (вынесены сбор/валидация результатных payload и критерии наличия результатов в helper-слой + unit-тесты).
- [ ] Полный ручной регрессионный прогон по чек-листу раздела 14.4.
- [ ] Финальная актуализация пользовательской/технической документации после закрытия P1.

### 14.6 План выполнения по итерациям

1. Итерация A (закрыто): hotfix рекурсии сброса контекста.
2. Итерация B (закрыто): `PatientEditDialog` (UI + сервисная интеграция + обновление контекста).
3. Итерация C (текущая): декомпозиция остатка UI + ручной чек-лист + финальная документация P2.
4. Итерация D (отложено на финал): UX-дефолты (незакрытый пункт Этапа V).
5. Итерация E (закрыто): `Форма 100 V2` — модели/миграции/сервисы/UI/PDF/ZIP/аудит.
6. Итерация F (текущая): стабилизация V2 UI и расширенный ручной регрессионный прогон.

---

## 15) Релиз: сборка и документация

### Цель

Подготовить релизный билд приложения и пакет документов для распространения и установки.

### План (на потом)

1) Подготовить релизный билд Windows (PyInstaller) и проверить запуск.
2) Обновить пользовательскую и техническую документацию.
3) Подготовить установщик (NSIS/Inno Setup) и инструкции.
4) Провести финальный smoke‑тест на чистой машине.
5) Сформировать release‑note и версию.
6) Подготовить пакет релиза для передачи.

### Статус

- [x] Подготовлены скрипты сборки релиза.
- [x] Добавлен прогресс‑отчет в `docs/progress_report.md`.
- [x] Проведены локальные проверки ruff/pytest.
- [x] Сборка exe выполнена.
- [x] Сборка установщика выполнена.
- [x] Подготовлен план релизных действий.

---

## 16) Цветовая система UI (рекомендуемая палитра)

Цель раздела: зафиксировать единый набор цветов, чтобы новые экраны и доработки оставались визуально консистентными.

### 16.1 Core palette (базовые цвета интерфейса)

| Цвет | Где применяется | Для чего |
| --- | --- | --- |
| `#F7F2EC` | Основной фон окна приложения | Базовый нейтральный фон UI |
| `#FFF9F2` | Фон полей ввода, таблиц, карточек контента | Читаемая рабочая поверхность |
| `#FFFDF8` | Выделенные карточки (например, карточка пациента) | Визуально приподнятая поверхность |
| `#EFE6DA` | Menubar, вторичные подложки | Вторичный слой интерфейса |
| `#E3D9CF` | Границы виджетов, разделители, сетка таблиц | Единая контурная сетка и иерархия |
| `#3A3A38` | Основной текст и подписи | Базовый контрастный текст |
| `#7A7A78` | Вторичный текст, helper-подсказки | Приглушенная служебная информация |

### 16.2 Accent palette (акцент и интерактив)

| Цвет | Где применяется | Для чего |
| --- | --- | --- |
| `#A1E3D8` | Основные кнопки, highlight-состояния | Главный акцент бренда |
| `#8FDCCF` | Active/pressed состояния, primary-кнопки | Подчеркивание текущего действия |
| `#6FB9AD` | Рамка активного пункта меню/навигации | Акцентный контур активности |
| `#61C9B6` | Ссылки и динамический акцент (часы/таймеры) | Быстрый фокус внимания |

### 16.3 Status palette (системные статусы)

| Статус | Текст | Фон | Граница | Для чего |
| --- | --- | --- | --- | --- |
| `success` | `#9AD8A6` | `#E6F6EA` | `#9AD8A6` | Успешные действия и подтверждения |
| `warning` | `#F4D58D` | `#FFF4DB` | `#F4D58D` | Предупреждения и частично валидные состояния |
| `error` | `#E18A85` | `#FDE7E5` | `#E18A85` | Ошибки и блокирующие проблемы |
| `info` | `#7A7A78` | `#F2F1EF` | `#C9C6C1` | Нейтральная информационная обратная связь |

Примечания:

- `#D8746F` используется как pressed-состояние для danger-кнопок (например, выход).
- `#B00020` используется как усиленный error в отдельных формах.

### 16.4 Charts palette (аналитика)

| Цвет | Где применяется | Для чего |
| --- | --- | --- |
| `#4C78A8` | Столбцы и базовые линии графиков | Основной цвет аналитических серий |
| `#E18A85` | Линия положительных значений/рисков | Контрастная выделенная серия |

### 16.5 Bodymap palette (Форма 100, схема тела)

| Цвет | Где применяется | Для чего |
| --- | --- | --- |
| `#C0392B` | Метка `WOUND_X` | Обозначение раны |
| `#E67E22` | Метка `BURN_HATCH` | Обозначение ожога |
| `#943126` | Метка `AMPUTATION_FILL` | Обозначение ампутации |
| `#9C640C` | Метка `TOURNIQUET_LINE` | Обозначение линии жгута |
| `#1F77B4` / `#6AAEE6` | Контур/заливка `NOTE_PIN` | Точечная заметка врача |
| `#5F6A6A` | Preview-отрисовка фигуры | Предпросмотр рисования перед фиксацией |

### 16.6 Правила использования палитры

1. Новые экраны и виджеты должны использовать цвета из раздела 16.
2. Для статусов `success/warning/error/info` использовать централизованные стили из `app/ui/widgets/notifications.py`.
3. При добавлении нового цвета сначала обновить этот раздел и указать его назначение.
4. Для интерактивных элементов обеспечивать полный цикл состояний: `default -> hover -> pressed -> disabled`.

---

## 17) Premium UI архитектура (факт внедрения)

Цель: применить визуальные паттерны из `Test_UI` к боевому приложению без изменения бизнес-логики, сервисов, DTO и БД.

### 17.1 Feature flags UI

| Параметр | ENV | Значение по умолчанию | Назначение |
| --- | --- | --- | --- |
| `settings.ui_premium_enabled` | `EPIDCONTROL_UI_PREMIUM` | `1` | Глобальное включение premium UI-слоя |
| `settings.ui_animation_policy` | `EPIDCONTROL_UI_ANIMATION` | `adaptive` | Политика анимаций: `adaptive/full/minimal` |
| `settings.ui_density` | `EPIDCONTROL_UI_DENSITY` | `normal` | Плотность интерфейса: `normal/compact` |

### 17.2 Новые UI-модули

| Файл | Назначение |
| --- | --- |
| `app/ui/theme.py` | Единый источник цветов и глобального QSS |
| `app/ui/runtime_ui.py` | Расчёт `UiRuntimeConfig` по экрану/DPI и policy |
| `app/ui/widgets/transition_stack.py` | Безопасные fade-переходы между страницами |
| `app/ui/widgets/toast.py` | Неблокирующие toast-уведомления и менеджер позиционирования |
| `app/ui/widgets/animated_background.py` | Анимированный фон (`subtle/showcase`) |
| `app/ui/widgets/responsive_actions.py` | Адаптивная раскладка action-кнопок |

### 17.3 Интеграция в shell

1. В `app/main.py` тема подключается через `apply_theme(app, settings)`.
2. В `app/ui/main_window.py`:
   - сохранена top-menu навигация (без перехода на sidebar как primary-nav);
   - `QStackedWidget` заменён на `TransitionStack`;
   - добавлен слой `MedicalBackground` (включается по runtime policy);
   - добавлена адаптивная top-menu презентация (`full/compact/mini`) с короткими подписями на узких экранах;
   - сохранены текущие роли (`admin/operator`) и все callback-контракты контекста.

### 17.4 Политика уведомлений

1. `error` — modal (`QMessageBox`) + логирование.
2. `info/warning/success` — toast (`show_toast(...)`) без блокировки рабочего потока.
3. Публичные API сохранены: `show_error`, `show_warning`, `show_info`.

### 17.5 Адаптивность экранов (выполнено)

| Экран | Что адаптировано |
| --- | --- |
| `app/ui/widgets/context_bar.py` | Responsive reflow + адаптивные быстрые действия |
| `app/ui/form100/form100_view.py` | Адаптивный action toolbar через `ResponsiveActionsPanel` |
| `app/ui/analytics/analytics_view.py` | Адаптивные action-панели поиска и истории отчётов |
| `app/ui/patient/patient_emk_view.py` | Адаптивный quick actions toolbar |
| `app/ui/import_export/import_export_view.py` | Адаптивный quick actions toolbar |
| `app/ui/main_window.py` | Адаптивные подписи верхнего меню (`full/compact/mini`) |
| `app/ui/emz/emz_form.py` | Quick actions переведены на `ResponsiveActionsPanel` |
| `app/ui/lab/lab_samples_view.py` | Верхний action-row переведен на `ResponsiveActionsPanel` |
| `app/ui/sanitary/sanitary_dashboard.py` | Верхний action-row переведен на `ResponsiveActionsPanel` |
| `app/ui/sanitary/sanitary_history.py` | Блок действий переведен на `ResponsiveActionsPanel` |

### 17.6 Проверки качества

1. `ruff check app tests` — зелёный.
2. `pytest -q` — зелёный (`217 passed`).
3. Добавлены unit-тесты на новый UI-слой: theme/transition/toast/responsive/table-layout/shell.
4. Inline-стили в `app/ui` устранены; постоянные стили централизованы в `app/ui/theme.py`.
5. Добавлен guard-тест `tests/unit/test_ui_no_inline_styles.py` (запрещает возврат inline `setStyleSheet(...)` в `app/ui/**`).

### 17.7 Гайд По Стилю И `objectName`

1. Не использовать `setStyleSheet(...)` внутри экранов/виджетов для постоянных стилей.
2. Для постоянного оформления задавать `objectName`/динамические свойства и описывать стиль в `app/ui/theme.py`.
3. Для статусов использовать `app/ui/widgets/notifications.py` (`set_status`, `clear_status`) и селектор `QLabel#statusLabel[statusLevel=...]`.
4. Для карточек списков использовать единый набор:
   - `QWidget#listCard`;
   - `QLabel#cardStatusDot[tone=ok|warn|danger|unknown]`;
   - `QLabel#cardTitle`;
   - `QLabel#cardMeta`.
5. Для приглушённых подписей использовать `QLabel#muted`, для чипов — `QLabel#chipLabel`.
6. Допустимые исключения для локального `setStyleSheet(...)`:
   - временные прототипы, которые должны быть перенесены в `theme.py` до релиза.

### 17.8 Чеклист Для Нового UI-Экрана

1. Все кнопки действий собраны через адаптивный контейнер (`ResponsiveActionsPanel`), если есть риск перегрузки в одну строку.
2. Таблицы: отключён ручной resize колонок, ширины считаются кодом от viewport.
3. Сообщения об ошибках/успехе: `show_error`/`show_info`/`show_warning` и `set_status`.
4. Для новых цветов сначала обновляется раздел `16) Цветовая система UI`, потом `theme.py`.
5. Перед сдачей: `ruff check app tests`, `pytest -q`, `python -m compileall` по изменённым файлам.

---

## 18) Form100 V2 (новый контур)

### 18.1 Режим включения

| Параметр | ENV | Значение по умолчанию | Назначение |
| --- | --- | --- | --- |
| `settings.form100_v2_enabled` | `EPIDCONTROL_FORM100_V2_ENABLED` | `1` | Переключение между legacy Form100 и Form100 V2 в `MainWindow` |

### 18.2 Схема данных V2

| Таблица | Назначение | Ключевые поля |
| --- | --- | --- |
| `form100` | Карточка Form100 V2 (денормализованный листинг/поиск) | `id`, `status`, `version`, `main_full_name`, `main_unit`, `main_id_tag`, `main_diagnosis`, `legacy_card_id`, audit timestamps |
| `form100_data` | Подробные секции формы (1:1 к карточке) | `card_id`, JSON/TEXT секции: `stub_json`, `main_json`, `lesion_json`, `san_loss_json`, `medical_help_json`, `bodymap_json`, `flags_json`, `bottom_json` |

Примечания:

1. Миграция: `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`.
2. Откат удаляет только V2-таблицы, legacy-схема сохраняется.
3. В миграции выполнен перенос legacy-данных в V2 c трассировкой через `legacy_card_id`.

### 18.3 Сервисный контракт V2

`app/application/services/form100_service_v2.py`:

1. `list_cards(filters, limit, offset)`
2. `get_card(card_id)`
3. `create_card(request, actor_id)`
4. `update_card(card_id, request, actor_id, expected_version)`
5. `sign_card(card_id, actor_id, expected_version)`
6. `export_pdf(card_id, file_path, actor_id)`
7. `export_package_zip(card_id|filters, file_path, actor_id)`
8. `import_package_zip(file_path, actor_id, mode)`

Дополнительно:

1. workflow только `DRAFT -> SIGNED`;
2. optimistic lock по `version`;
3. роли: `admin/operator` для рабочих операций, admin-only для удаления.

### 18.4 UI и bodymap V2

| Файл | Назначение |
| --- | --- |
| `app/ui/form100_v2/form100_view.py` | Список карточек, фильтры, action-bar, интеграция редактора |
| `app/ui/form100_v2/form100_editor.py` | Блочная форма (штамп, клиника, флаги, помощь, подписи) |
| `app/ui/form100_v2/widgets/bodymap_editor_v2.py` | Графический bodymap-редактор без ручного JSON |

Правила bodymap V2:

1. 4 силуэта (м/ж, спереди/сзади), активные зависят от пола.
2. Рисование ограничено контуром силуэта (`QPainterPath.contains`).
3. Метки хранятся как структурированный JSON в `form100_data`.

### 18.5 Форматы обмена и отчётов

1. ZIP V2: `form100.json` + `form100.pdf` + `manifest.json`.
2. Валидация импорта: структура манифеста + SHA256 hash.
3. PDF V2: `app/infrastructure/reporting/form100_pdf_report_v2.py` (A5 landscape, кириллица).
4. Интеграция:
   - обмен: `app/application/services/exchange_service.py`;
   - отчётность и артефакты: `app/application/services/reporting_service.py`.

### 18.6 Тестовое покрытие V2

1. Unit: `tests/unit/test_form100_v2_rules.py`.
2. Integration: `tests/integration/test_form100_v2_service.py`.
3. Текущий контрольный прогон: `ruff check app tests`, `pytest -q` (`217 passed`).
