# Codex Action Plan: системный аудит и исправление отчётности/экспортов Epid Control

**Версия:** 1.0
**Дата:** 2026-05-06
**Источники:**
- Аудит ChatGPT 5.5 (`reporting_artifacts_audit_prompt.md`) — продуктовая/визуальная сторона.
- Аудит Claude Opus 4.7 (`ANALYSIS_REPORT.md`) — техническая сторона (анализ байтов PDF, SHA256, БД, BOM, audit_log).
- Тестовый пакет артефактов `tmp_run/generated_app_outputs_20260506_101444` (29 файлов, синтетические данные, контрольные суммы 25/25 ✓).

**Адресат:** Codex GPT 5.5, работающий в репозитории **Epid.-Control-VMA**.

**Главная цель:** не «починить файлы», а привести систему отчётности к состоянию, в котором:
- подписанная медицинская карточка immutable;
- регенерация PDF детерминирована и не разрывает цепочку SHA256;
- человеко-ориентированные форматы (PDF/XLSX) имеют единое форматирование;
- машинно-ориентированные форматы (JSON/CSV/ZIP) имеют стабильные коды и ISO-даты;
- ошибки импорта структурированы и без утечки Python-исключений;
- покрытие аудита соответствует требованиям compliance (любой экспорт/импорт ПД оставляет след);
- регрессии ловятся тестами, а не пользователем.

---

## 0. Жёсткие ограничения

> Эти правила **не нарушаются** ни ради «быстрее закрыть», ни ради «уменьшить дифф».

- ✗ Не удалять существующие тесты. Если тест неправильный — изменить, объяснить в коммите.
- ✗ Не `skip`-ать тесты. Если падает — фиксим логику, не маскируем.
- ✗ Не использовать `# type: ignore` без комментария-обоснования.
- ✗ Не менять схему БД без Alembic-миграции (с `down_revision`, `upgrade()`, `downgrade()`).
- ✗ Не переносить бизнес-логику в UI (UI ← Application ← Domain).
- ✗ UI не должен импортировать `app.infrastructure.*` напрямую.
- ✗ Не логировать ФИО, ID пациентов и медицинские данные в открытом виде в `audit_log.payload_json` сверх необходимого. Использовать паттерны маскирования из существующего кода.
- ✗ **Не смешивать machine-exchange и human-readable форматы**. JSON/CSV — стабильные коды (`outcome_type: "transfer"`), PDF/XLSX — display labels (`Перевод`).
- ✗ **Экспорт, генерация PDF и упаковка ZIP — read-only операции**. Они не повышают `version`, не меняют `updated_at/updated_by/status/data` карточки. Допустимо только обновление `artifact_path/artifact_sha256` через отдельный механизм (см. P0.1).
- ✗ Не продолжать работу над следующим этапом, пока предыдущий не закрыт (зелёный CI + commit + запись в `progress_report.md`).

---

## 1. Подготовка — что читать перед началом

```text
AGENTS.md                             ← если есть
.agents/skills/epid-control/SKILL.md  ← если есть
docs/context.md                       ← роадмап и приоритеты
docs/session_handoff.md
docs/progress_report.md               ← последние записи
docs/tech_guide.md                    ← схема БД и сервисы
docs/specs/SPEC_*.md                  ← существующие спеки, особенно form100/exchange/analytics
```

Команда для быстрой ориентации:
```bash
git log --oneline -20
git status
python -m alembic heads
python scripts/check_architecture.py
```

После прочтения — **сначала составить root-cause-план в чате/PR-описании, и только потом править код**.

---

## 2. Subagent-роли

Если среда поддерживает субагентов — подключить. Иначе выполнить роли последовательно и зафиксировать выводы каждой в отчёте.

### 2.1. PDF Layout Auditor

Артефакты для проверки:
- `form100/form100_direct.pdf`
- `reports/form100_report_via_reporting.pdf`
- `reports/artifacts/form100/2026/05/form100_20260506_071446_*.pdf`
- `reports/analytics_report.pdf`
- `exchange/pdf/{patients,emr_case,lab_sample,sanitary_sample}.pdf`

Чек-лист:
- [ ] Word-wrap (а не char-wrap) в заголовках и значениях колонок (есть конкретные жертвы: `ID пациент\nа`, `Локализаци\nя материал\nа`, `офицер(прапор\nщик)`).
- [ ] Page-break не отрывает заголовок секции от контента (особенно `4. Схема тела`).
- [ ] ISO-даты и микросекунды отсутствуют в человеко-форматах (`1992-02-02`, `2026-05-06 07:14:44.623119`).
- [ ] Технические ID не висят в шапке (`ID пациента`, `ID типа материала` → имена + ID мелко при необходимости).
- [ ] `Создал: 1` заменён на login/ФИО.
- [ ] Поле `Сторона` в bodymap-таблице корректно семантически (см. P1.2).
- [ ] У PDF есть заголовок, период, автор, дата формирования (см. P1.3).
- [ ] PDF побайтово стабилен между двумя последовательными генерациями одного DTO (см. P0.2).

### 2.2. Exchange Schema Auditor

Артефакты:
- `exchange/full_export.json`
- `exchange/full_export.zip` + `manifest.json` внутри
- `form100/form100_cards.json`
- `form100/form100_package.zip` + manifest
- `exchange/form100_package_via_exchange.zip` + manifest
- `manifest.json` (корневой)

Чек-лист:
- [ ] Никаких мутаций исходных карточек/записей при экспорте (`form100.version` не растёт).
- [ ] Единый формат datetime во всех JSON-полях (ISO 8601 с TZ).
- [ ] `is_active`, growth-флаги — единый стандарт (boolean, не «Да»/«Нет», в machine-формате).
- [ ] Пути в манифестах — относительные, POSIX-разделители.
- [ ] `manifest.root` не содержит абсолютные пути с именем пользователя ОС.
- [ ] Обязательные поля версии: `schema_version`, `app_version`, `db_schema_revision`.
- [ ] SHA256 в `manifest.json` ZIP равен SHA256 файла, на который ссылается карточка (см. P0.3).
- [ ] `ismp_case` и Form100 присутствуют (или явно задокументировано отсутствие в манифесте).

### 2.3. XLSX/Reporting Auditor

Артефакты: `analytics_report.xlsx`, `full_export.xlsx`, `reports/artifacts/.../*.xlsx`.

Чек-лист:
- [ ] Все datetime — реальные `datetime` ячейки, не строки.
- [ ] Проценты — `0.0…1.0` + `number_format='0.0%'`, не `100` без формата и не строка `'100.0%'`.
- [ ] `freeze_panes`, `auto_filter`, bold header, column widths — на всех листах с данными.
- [ ] Локализованные заголовки колонок (включая `Срок QC`, `Статус QC`, не `qc_due_at`, `qc_status`).
- [ ] ID-колонки сопровождаются именованными колонками (`ID типа материала=1` + `Тип материала=Кровь`) — либо ID скрыт.
- [ ] Лист `Топ микроорганизмов` присутствует в analytics XLSX (P1.7).
- [ ] `None` не попадает в ячейки буквально; пустые поля — пустые ячейки.

### 2.4. Validation Auditor

Артефакты: `diagnostics/invalid_patients_import_errors_*.json`, тесты вокруг импорта и Form100.

Чек-лист:
- [ ] В пользовательских error-логах нет `list index out of range`, `KeyError: 'foo'`, `TypeError`.
- [ ] Есть структурированные поля: `row`, `field`, `value`, `error_code`, `message`, `hint`.
- [ ] Есть `summary`: `total`, `imported`, `skipped`, `errors`.
- [ ] CSV-парсер съедает BOM и принимает RU и EN заголовки.
- [ ] Подписание Form100 требует минимальный обязательный набор полей и сообщает пользователю список всех непрошедших валидаций (а не первой попавшейся).

### 2.5. Compliance/Audit Auditor

Чек-лист (новая роль, добавлена нами):
- [ ] Каждый экспорт ПД (Excel/CSV/PDF/JSON/ZIP) пишет событие в `audit_log` (не только в `data_exchange_package`).
- [ ] Каждый импорт (успех/ошибка) пишет событие в `audit_log`.
- [ ] Создание/восстановление бэкапа фиксируется в одной транзакции с операцией.
- [ ] Метаданные пакетов и резервных копий не утекают наружу абсолютные пути и имя ОС-пользователя.

### 2.6. Regression/Test Engineer

Сводный список тестов — см. раздел 8. Минимум на каждый исправленный пункт — золотой/инвариантный тест.

---

# ЭТАП 1 — P0: критические исправления

> Закрыть **до** перехода к P1. После каждого пункта — `pytest -q`, commit, запись в `progress_report.md`.

---

## P0.1. Form100: read-only export и version consistency

### Сводная проблема (две дополняющиеся стороны)

Из ChatGPT-аудита: версии в direct PDF / reporting PDF / artifact / JSON расходятся (видно «Версия: 2», «Версия: 3» на одной карточке).

Из Claude-аудита: причина расхождения — **PDF-генерация изменяет карточку**. По `audit_log`:
```
id=1 form100_create        new_version=1
id=2 form100_sign          new_version=2 (DRAFT→SIGNED)
id=3 form100_pdf_generate  new_version=3 (changed_fields: [artifact_path, artifact_sha256])
id=4 form100_export        (упаковка ZIP)
id=5 form100_pdf_generate  new_version=4 (changed_fields: [artifact_path, artifact_sha256])
id=6 form100_export        (упаковка ZIP)
```

Каждая регенерация PDF поднимает `version`, что ломает смысл подписи и optimistic-lock.

### Целевое поведение

Подписанная карточка — immutable snapshot. Любая регенерация PDF — побочная операция над **артефактами**, а не над карточкой:
1. Не повышает `card.version`.
2. Не меняет `updated_at`, `updated_by`, `status`, `data`.
3. Может создавать **новый** запись в реестре артефактов (`form100_artifact` или эквивалент), но не перезаписывать состояние карточки.
4. Работает с **зафиксированным** на момент подписи snapshot'ом данных.

### Что делать в коде

1. Добавить таблицу `form100_artifact` (миграция):
   ```
   id (uuid), form100_id (FK), version_at_generation (int),
   kind (enum: pdf|json|zip), path, sha256, generated_at, generated_by
   ```
   Каждая генерация PDF создаёт **новую** строку.

2. В `form100` оставить `artifact_path/artifact_sha256` как «последний primary artifact», но **обновлять только при подписи**, не при последующих регенерациях.

3. `Form100ServiceV2.export_pdf` и `ReportingService.export_form100_pdf`:
   - читают карточку с FOR UPDATE = NO;
   - генерируют PDF;
   - записывают строку в `form100_artifact`;
   - **НЕ изменяют поля карточки**;
   - аудит-событие `form100_pdf_generate` пишется без `changed_fields=[artifact_path, artifact_sha256]` для карточки — оно фиксирует факт генерации артефакта.

4. В печатном PDF поле «Версия» брать из `card.signed_version` (новое поле, фиксируемое при подписи), а не из текущего `card.version`. Если карточка ещё DRAFT — выводить `(черновик)`.

5. Проверить, не вызывает ли упаковка ZIP отдельную регенерацию PDF. Если да — переиспользовать существующий artifact файл, а не генерировать заново.

### Файлы

```
app/application/services/form100_service_v2.py
app/application/services/reporting_service.py
app/application/services/exchange_service.py
app/infrastructure/db/repositories/form100_repo_v2.py
app/infrastructure/reporting/form100_pdf_report_v2.py
app/infrastructure/export/form100_export_v2.py
app/infrastructure/db/migrations/versions/00XX_form100_artifact_table.py
app/domain/models/form100_v2.py        ← добавить signed_version
app/application/dto/form100_v2_dto.py  ← signed_version в Dto
```

### Тесты (P0.1)

```python
# tests/integration/test_form100_export_is_readonly.py

def test_export_pdf_does_not_increment_version(...)
def test_export_pdf_does_not_change_updated_at(...)
def test_zip_package_does_not_increment_version(...)
def test_signed_version_remains_after_three_regenerations(...)
def test_pdf_footer_uses_signed_version_not_current(...)
def test_artifact_table_records_each_generation(...)
def test_zip_reuses_existing_pdf_artifact_if_available(...)
```

### Acceptance criteria

- На карточке N: создание→sign→3×PDF→2×ZIP оставляет `card.version = signed_version` (т.е. 2 из примера).
- В таблице `form100_artifact` 3 строки от 3-х PDF-генераций.
- Все 3 PDF в footer показывают одну и ту же «Версия: 2».

---

## P0.2. PDF детерминизм (новый пункт, не было у ChatGPT)

### Проблема

Побайтовое сравнение `form100_direct.pdf` и `form100_report_via_reporting.pdf` (одинаковые данные, размер 510 280 байт):
- 74 байта различий в 7 регионах.
- Из них:
  - 2 байта на странице 3 — печатный номер «Версия» (это P0.1).
  - 72 байта — `/CreationDate`, `/ModDate`, `/ID` ReportLab (отличаются на 1 секунду, рандомный fingerprint).

После фикса P0.1 (одинаковая `signed_version`) останутся **только** 72 байта PDF-метаданных. Это всё ещё ломает SHA256 при любой регенерации.

### Что делать

1. В `app/infrastructure/reporting/form100_pdf_report_v2.py` и в `app/infrastructure/reporting/pdf_*` сделать единую обёртку над ReportLab:
   ```python
   doc = SimpleDocTemplate(buf, pagesize=A4, ...)
   doc.invariant = 1   # ReportLab option for reproducible builds
   # либо canvas.Canvas(buf, invariant=1)
   ```

2. Альтернативно/дополнительно в post-processing: после генерации PDF убирать `/CreationDate`, `/ModDate`, фиксировать `/ID` как HMAC от тела документа:
   ```python
   def _normalize_pdf_metadata(pdf_bytes: bytes, doc_id_seed: str) -> bytes:
       # remove /CreationDate, /ModDate, set deterministic /ID
   ```

3. Тест: сгенерировать **дважды** одну и ту же карточку → байты идентичны.

### Acceptance criteria

```python
def test_pdf_is_byte_identical_for_same_input(...):
    pdf_a = service.export_pdf(card_id)
    pdf_b = service.export_pdf(card_id)
    assert sha256(pdf_a) == sha256(pdf_b)
    assert pdf_a == pdf_b
```

Это **прямой регрессионный инвариант**: любая случайность в PDF — fail.

---

## P0.3. SHA256 целостность Form100 ZIP (новый пункт)

### Проблема

В `form100_package.zip`:
- `form100.json` пишет `"artifact_sha256": "d8258e25772b…"` — хэш «зарегистрированного в карточке» PDF.
- `manifest.json` того же ZIP пишет `"sha256": "e90b373cd595…"` — хэш PDF, фактически лежащего в архиве.

Два разных SHA256 для одного и того же физически файла в одном архиве. Получатель не может проверить: PDF в ZIP не тот, который был зафиксирован при подписи карточки.

### Что делать

После P0.1 (read-only export) и P0.2 (детерминизм) этот баг закрывается автоматически: PDF, генерируемый при упаковке ZIP, будет байт-в-байт совпадать с PDF, зафиксированным при подписи.

**Дополнительно** добавить инвариант:

```python
# tests/integration/test_form100_zip_integrity.py
def test_zip_pdf_sha256_matches_card_artifact_sha256(...):
    zip_bytes = service.export_zip(card_id)
    with ZipFile(BytesIO(zip_bytes)) as z:
        manifest = json.loads(z.read('manifest.json'))
        cards = json.loads(z.read('form100.json'))
        pdf_in_zip = z.read(f'form100/{card_id}.pdf')

    pdf_sha_actual = sha256(pdf_in_zip)
    pdf_sha_in_manifest = next(f['sha256'] for f in manifest['files'] if f['name'].endswith('.pdf'))
    pdf_sha_in_card = cards['cards'][0]['artifact_sha256']

    assert pdf_sha_actual == pdf_sha_in_manifest == pdf_sha_in_card
```

---

## P0.4. ИСМП и Form100 в полном экспорте (новый пункт)

### Проблема

`full_export.json` и `full_export.xlsx` содержат 21 таблицу. В БД при этом есть с непустыми данными:
- `ismp_case` (1 строка) — **отсутствует в экспорте**.
- `form100`, `form100_data` — отсутствуют (выгружаются отдельно через Form100 ZIP).
- `ref_ismp_abbreviations` (0 строк, но это справочник) — отсутствует.

Для пользователя «Экспорт всех данных» означает «всё». Сейчас это не так.

### Что делать

1. В `ExchangeService` добавить `ismp_case` и `ref_ismp_abbreviations` в карту таблиц (как для JSON, так и для XLSX-листов).

2. По Form100 — стратегическое решение:
   - **Вариант A (рекомендую):** включить Form100 в полный экспорт как отдельные секции (`form100`, `form100_data`), JSON-поля сериализовать как nested objects. PDF не включать (он остаётся в Form100 ZIP).
   - **Вариант B:** оставить Form100 отдельно, но в `manifest.json` полного экспорта явно писать `"not_included": ["form100"]` с указанием `"export_via": "form100_zip"`.

3. Регрессионный тест-инвариант:
   ```python
   def test_full_export_contains_all_clinical_tables(seeded_db):
       export = exchange_service.export_full_json()
       db_tables = clinical_tables_with_data(seeded_db)
       missing = db_tables - set(export['data'].keys())
       allowed_missing = {'form100', 'form100_data'}  # если выбран вариант B
       assert missing - allowed_missing == set()
   ```

4. Добавить лист «ИСМП-случаи» в `full_export.xlsx` с локализованными заголовками.

### Файлы

```
app/application/services/exchange_service.py
app/infrastructure/export/exchange_excel.py
app/infrastructure/export/exchange_json.py
tests/integration/test_exchange_full_export_completeness.py
```

---

## P0.5. Утечка PII в манифестах (новый пункт)

### Проблема

```json
// manifest.json
"root": "C:\\Users\\user\\Desktop\\PRo_CODER\\Epid.-Control-VMA\\..."
```

Везде в JSON-выгрузках:
- `last_backup.json/path`: `tmp_run\\generated_app_outputs_...\\backup\\backups\\app_*.db`
- `report_history.json/artifact_path`: `tmp_run\\...\\reports\\artifacts\\...`
- `data_exchange_package.file_path`: то же.
- `form100.artifact_path`: то же.

Утечка имени пользователя ОС, структуры файловой системы и абсолютных путей в файл, который ездит между организациями.

### Что делать

1. Все пути в выгружаемых JSON — **относительные от корня пакета**, POSIX-разделители (`form100/abc.pdf`, не `form100\\abc.pdf`).

2. `manifest.root` либо удалить, либо заменить на буквально `"."`.

3. Внутренний `data_exchange_package.file_path` в БД — допустимо абсолютным (это для локального использования), но при экспорте/выгрузке **не сериализовать** или нормализовать в относительный.

4. `form100.artifact_path` — лучше сразу хранить относительно `data_dir`, не абсолютно.

5. Тест:
   ```python
   def test_manifest_json_contains_no_absolute_paths(...):
       data = json.loads(manifest_path.read_text())
       for entry in data.get('generated', []):
           p = entry['path']
           assert not p.startswith('/') and ':\\' not in p
           assert '\\' not in p  # POSIX separators
       assert 'C:\\' not in json.dumps(data)
   ```

---

## P0.6. Валидация SIGNED Form100 (от ChatGPT, объединено)

### Проблема

В тестовом артефакте карточка `status='SIGNED'`, но в PDF пусто:
- Дата/время ранения/заболевания (`—`)
- Вид поражения (`—`)
- Вид санитарных потерь (`—`)
- Поля эвакуации (все 6 полей `—`)
- Звание (`—`)
- Выдана мед. пунктом (`—`)
- 11 строк блока «Медицинская помощь» все `— —`

В БД при этом у привязанной ЭМЗ есть `injury_date='2026-04-30 22:00'`. То есть некоторые данные в системе **уже есть**, но в Form100 не попали — это второй слой проблемы (см. P1.5).

### Что делать

1. В `app/domain/rules/form100_rules_v2.py` явно разделить два уровня валидации:
   - `validate_for_draft(dto)` — текущие минимальные проверки (ФИО, диагноз).
   - `validate_for_signing(dto)` — расширенный набор обязательных полей.

2. Минимальный набор для SIGNED (согласовать с заказчиком, спека → `docs/specs/SPEC_form100_signing_validation.md`):
   - ФИО
   - Звание (если применимо к категории пациента)
   - Воинская часть
   - Дата рождения (если поле уже есть)
   - Диагноз (основной)
   - Дата/время ранения или заболевания
   - Подпись (`signed_by`)
   - Вид поражения **или** Вид санитарных потерь (хотя бы один из двух)
   - Если флаг `flag_emergency=True` → требовать заполнение поля «Очерёдность эвакуации»
   - Если `mp_antibiotic=True` → требовать `mp_antibiotic_dose`
   - Если `mp_analgesic=True` → требовать `mp_analgesic_dose`

3. В `Form100ServiceV2.sign_card`:
   - вызвать `validate_for_signing`;
   - при ошибках — выбросить `Form100SigningError(errors: list[FieldError])`;
   - в UI (`form100_wizard.py` и `form100_view.py`) показать **список всех ошибок одним диалогом**, не первую попавшуюся.

4. Тесты:
   ```python
   def test_draft_with_empty_optional_fields_can_be_saved(...)
   def test_sign_with_missing_diagnosis_fails(...)
   def test_sign_with_missing_injury_date_fails(...)
   def test_sign_collects_all_errors_at_once(...)
   def test_sign_with_full_card_succeeds(...)
   def test_existing_signed_cards_remain_valid(...)  # backward compat
   ```

5. **Backward compatibility:** уже существующие подписанные карточки не валидировать «задним числом» при последующих экспортах — они остаются как есть. Жёсткая валидация — только для **новых** signing-операций.

---

## P0.7. Структурированные ошибки импорта (от ChatGPT, дополнено)

### Проблема

`invalid_patients_import_errors_*.json`:
```json
{ "scope": "patients", "row": 2, "message": "list index out of range" }
```

`list index out of range` — это `IndexError` Python, утёкший в пользовательский лог. Пользователь не понимает, что не так.

**Дополнение от Claude-аудита:** корневая причина почти наверняка в **BOM (`\ufeff`)** в начале CSV. Файл открывается как `utf-8`, заголовок первой колонки `id` парсится как `\ufeffid`, не находится в маппинге заголовков, маппер делает `headers[0]` → IndexError. Нужно открывать через `utf-8-sig` или явно стрипать BOM.

**Дополнение:** также проблема в несимметрии RU/EN заголовков — экспорт пишет `ID пациента, ФИО, ...`, импорт ждёт `id, full_name, ...`.

### Целевой формат ошибки

```json
{
  "summary": {
    "total_rows": 1,
    "imported": 0,
    "skipped": 1,
    "errors": 1,
    "started_at": "2026-05-06T07:14:47+00:00",
    "finished_at": "2026-05-06T07:14:47+00:00",
    "source_file": "invalid_patients.csv",
    "source_sha256": "07b3a80f..."
  },
  "errors": [
    {
      "row": 2,
      "field": "Дата рождения",
      "value": "bad-date",
      "error_code": "invalid_date_format",
      "message": "Строка 2, поле «Дата рождения»: некорректный формат «bad-date».",
      "hint": "Ожидается формат ДД.ММ.ГГГГ."
    }
  ]
}
```

### Что делать

1. В `app/infrastructure/import/csv_import.py` (или эквивалент):
   - открывать файл через `open(path, encoding='utf-8-sig')` — Python съедает BOM.
   - **до** обращения по индексам — валидировать длину и набор заголовков.
   - принимать **оба** набора заголовков: RU (как у экспорта) и EN (legacy).
   - использовать единый словарь маппинга `LOCALIZED_HEADERS` из formatter-модуля (см. P1.1).

2. Структурированный класс ошибок:
   ```python
   @dataclass
   class ImportFieldError:
       row: int
       field: str
       value: str | None
       error_code: str  # "invalid_date_format" | "missing_required" | "row_length_mismatch" | ...
       message: str    # localized
       hint: str | None = None
   ```

3. Аккумулировать **все** ошибки за один проход (не падать на первой), писать summary.

4. **Никакой `try/except Exception` без re-raise**, чтобы Python-исключения не утекали в лог.

5. Round-trip тест:
   ```python
   def test_csv_export_then_import_is_idempotent(seeded_db, tmp_path):
       export = exchange.export_patients_csv()
       errors = import_service.import_patients_csv(export)
       assert errors.errors == []
       # БД не должна измениться (или должна совпасть с исходным состоянием)
   ```

### Ошибки, которые должны корректно ловиться

| Сценарий CSV | error_code |
|--------------|-----------|
| Пустой `id` | `missing_required` |
| `dob = "bad-date"` | `invalid_date_format` |
| `sex = "Q"` | `invalid_enum_value` |
| Меньше колонок, чем заголовков | `row_length_mismatch` |
| Лишние колонки (warn) | `extra_columns` |
| Дубликат `id` в файле | `duplicate_row` |
| Незакрытая кавычка (CSV malformed) | `csv_parse_error` |

---

## P0.8. Audit покрытие (новый пункт)

### Проблема

В `data_exchange_package` 13 строк операций обмена. В `audit_log` про эти операции — только 2 события (form100_export). То есть:
- 1 Excel-экспорт
- 1 ZIP+Excel-экспорт
- 8 CSV/PDF экспортов (4 таблицы × 2 формата)
- 1 неудачный импорт CSV

— **10 операций над ПД не оставили следа в audit_log**.

Также: `backup_create` пишется **после** создания файла бэкапа — окно несогласованности.

### Что делать

1. Каждая операция в `ExchangeService`:
   ```python
   self._audit.record(
       entity_type='exchange',
       action='data_export',  # или 'data_import', 'data_import_failed'
       payload={
           'format': 'excel|csv|pdf|zip|json|form100_zip',
           'scope_tables': [...],   # какие таблицы вошли
           'file_sha256': '...',
           'rows_affected': N,
           'error_summary': None | {'errors_count': K, 'first_error_code': '...'},
       },
   )
   ```

2. `BackupService.create_backup`:
   - Записать `audit_log.action='backup_create'` **до** создания файла со статусом `started`.
   - После успешного `VACUUM INTO` — обновить запись (`status=ok`, `sha256=...`, `size=...`).
   - При ошибке — `status=failed` с error.

3. Тест:
   ```python
   def test_every_export_creates_audit_event(seeded_db):
       before = count_rows('audit_log')
       exchange.export_full_excel(...)
       exchange.export_full_zip(...)
       exchange.export_table_csv('patients', ...)
       exchange.export_table_pdf('patients', ...)
       after = count_rows('audit_log')
       assert after - before == 4
   ```

---

# ЭТАП 2 — P1: форматы, верстка, аналитика

> Закрывать только после полного зелёного P0.

---

## P1.1. Единый Formatting Layer

### Создать модуль `app/application/reporting/formatters.py`

```python
# Module is single source of truth for human-readable formatting.
# Used by: PDF reports, XLSX reports, CSV human variants.
# NOT used by: machine-exchange JSON (those use ISO/codes).

from datetime import date, datetime
from typing import Any

DASH = "—"

# ----- Dates / datetimes -----

def format_date(value: date | str | None) -> str:
    """ISO/date → 'DD.MM.YYYY'; None → '—'"""

def format_datetime(value: datetime | str | None, *, with_seconds: bool = False) -> str:
    """ISO/datetime → 'DD.MM.YYYY HH:MM' (without microseconds); None → '—'"""

# ----- Booleans / percents / missing -----

def format_bool(value: bool | int | None) -> str:
    """True/1 → 'Да'; False/0 → 'Нет'; None → '—'"""

def format_percent(value: float | None, *, digits: int = 1) -> str:
    """0.123 → '12.3%'; None → '—'"""

def format_missing(value: Any) -> str:
    """None/'' → '—'; иначе str(value)"""

# ----- Enums (codes → russian labels) -----

def format_sex(code: str | None) -> str:
    """'M' → 'Мужской'; 'F' → 'Женский'; None → '—'"""

def format_outcome(code: str | None) -> str:
    """'transfer' → 'Перевод'; 'recovered' → 'Выздоровление'; ..."""

def format_severity(code: str | None) -> str:
    """'mild' → 'Лёгкая'; 'moderate' → 'Средней тяжести'; 'severe' → 'Тяжёлая'"""

def format_study_kind(code: str | None) -> str:
    """'primary' → 'Первичное'; 'repeat' → 'Повторное'; ..."""

def format_route(code: str | None) -> str:
    """'iv' → 'В/в'; 'po' → 'Внутрь'; 'im' → 'В/м'; ..."""

def format_qc_status(code: str | None) -> str:
    """'valid' → 'Действителен'; 'expired' → 'Просрочен'; 'pending' → 'Ожидает'"""

def format_lesion_type(code: str | None) -> str: ...
def format_san_loss_type(code: str | None) -> str: ...
def format_annotation_type(code: str | None) -> str:
    """'WOUND_X' → 'Рана'; 'BURN_HATCH' → 'Ожог'; 'AMPUTATION' → 'Ампутация';
    'TOURNIQUET' → 'Жгут'; 'NOTE_PIN' → 'Заметка'."""

def format_silhouette(code: str | None) -> str:
    """'male_front' → 'Мужской, спереди'; 'female_back' → 'Женский, сзади'; ..."""

# ----- Headers (machine field name → display label) -----

LOCALIZED_HEADERS: dict[str, str] = {
    # patients
    'id': 'ID пациента',
    'full_name': 'ФИО',
    'dob': 'Дата рождения',
    'sex': 'Пол',
    # ...
    # lab_sample
    'qc_due_at': 'Срок QC',
    'qc_status': 'Статус QC',
    # ...
}

def localize_header(field: str) -> str:
    return LOCALIZED_HEADERS.get(field, field)

def localize_headers(fields: list[str]) -> list[str]:
    return [localize_header(f) for f in fields]
```

### Тесты `tests/unit/test_formatters.py`

```python
def test_format_date_iso_to_ddmmyyyy()
def test_format_date_none_returns_dash()
def test_format_datetime_strips_microseconds()
def test_format_bool_true_returns_da()
def test_format_percent_one_returns_100_0_percent()
def test_format_sex_m_returns_male_russian()
def test_format_outcome_unknown_returns_safe_fallback()
def test_localize_header_known_field()
def test_localize_header_unknown_field_returns_as_is()
def test_format_annotation_type_wound_x_returns_rana()
```

### Где применить

- `app/infrastructure/reporting/form100_pdf_report_v2.py` — все datetime, dates, enums.
- `app/infrastructure/reporting/analytics_pdf.py` — то же.
- `app/infrastructure/export/exchange_pdf.py` (raw table PDFs) — то же.
- `app/infrastructure/export/exchange_excel.py` — заголовки и значения enums.
- `app/infrastructure/export/exchange_csv.py` — для **человеко-читаемых CSV**, если такие будут (по умолчанию CSV машинный).

---

## P1.2. Form100 PDF: верстка и форматирование

### Список конкретных правок (объединение ChatGPT + Claude)

#### P1.2.1. Дата рождения

```text
Было:  Дата рождения 1992-02-02
Стало: Дата рождения 02.02.1992
```

#### P1.2.2. Дата подписания

```text
Было:  Дата подписания 2026-05-06 07:14:44.623119
Стало: Дата подписания 06.05.2026 07:14
```

(`format_datetime(card.signed_at)`)

#### P1.2.3. Тип аннотации в bodymap-таблице

```text
Было:  1  Рана (□)  Вид спереди  X=0.42, Y=0.36  Synthetic marker
Стало: 1  Рана      Спереди      Правая сторона груди, верхняя треть  Synthetic marker
```

- Убрать `(□)` — пустая иконка ничего не передаёт.
- Колонка `Сторона` сейчас содержит `Вид спереди` — это **проекция**, не сторона. Переименовать колонку в `Проекция` (значения: `Спереди` / `Сзади`), и **отдельно** добавить колонку `Сторона тела` (`Левая` / `Правая` / `По центру`) — определяется по `x ∈ [0, 0.5)`.
- Колонка `Координаты` — заменить на `Локализация`, генерировать human-readable из `(x, y)` через карту зон тела (`app/domain/services/bodymap_zones.py`):
  ```python
  def coordinates_to_zone(x: float, y: float, silhouette: str) -> str:
      # 'male_front', x=0.42, y=0.36 → "грудь, верхняя треть"
  ```
  Координаты оставить как опциональную служебную колонку, скрытую по умолчанию (или мелким шрифтом в footer).

#### P1.2.4. Page-break перед «4. Схема тела»

Заголовок секции «4. Схема тела (локализация повреждений)» сейчас попадает в конец стр.1, а сам PNG силуэта — на стр.2. Использовать `KeepTogether` ReportLab или `PageBreakBefore` для заголовка.

```python
from reportlab.platypus import KeepTogether
elements.append(KeepTogether([heading_4, bodymap_image]))
```

#### P1.2.5. Подпись и UUID

```text
Было:
8. Подпись врача
Врач (подпись) Synthetic signer
Статус карточки Подписано
Дата подписания 2026-05-06 07:14:44.623119
Карточка ID: 96e79a85-c246-4963-8282-02f5672777cf  Версия: 3
```

```text
Стало:
8. Подпись врача
Врач (подпись)        Synthetic signer
Статус карточки       Подписано
Дата подписания       06.05.2026 07:14

[мелким шрифтом в footer:]
Карточка №: F100-001/2026   Ревизия: 2   ID: 96e79a85-...
```

- Добавить отображаемый номер карточки (`card_no` или `display_id`) — короткий, последовательный.
- UUID — мелким шрифтом, в одну строку (или через QR-код).
- «Версия» переименовать в «Ревизия записи» (это техническая ревизия, а не версия документа).

#### P1.2.6. Раздел «Связанная ЭМЗ»

Если у карточки есть `emr_case_id`, добавить блок (после блока 1):
```text
Связанная госпитализация
№ ЭМЗ              CASE-T-001
Отделение          Test ICU
Дата поступления   01.05.2026 08:00
Дата травмы        30.04.2026 22:00     ← из emr_case_version
```

Это закрывает P1.5 (PDF не подтягивает данные из ЭМЗ).

#### P1.2.7. Различение пустых полей

- `None` (никогда не заполнялось) → курсивный серый «не указано».
- `False` или `0` (явный отрицательный ответ) → «не выполнено» / пустой кружок.
- Не одинаково отображать через `—`.

### Тесты P1.2

```python
def test_pdf_birth_date_is_dd_mm_yyyy()
def test_pdf_signed_date_no_microseconds()
def test_pdf_no_isoformat_dates_anywhere(extract_pdf_text)
def test_pdf_no_empty_parens_in_annotation_type()
def test_pdf_bodymap_table_has_projection_and_side_columns()
def test_pdf_bodymap_localization_human_readable()
def test_pdf_section_heading_not_orphaned_from_body()
def test_pdf_uses_signed_version_in_footer()
def test_pdf_includes_emr_case_block_when_available()
def test_pdf_card_display_number_present()
```

---

## P1.3. Analytics PDF — заголовок, summary, top microbes

### Что добавить

```text
[Заголовок страницы]
Аналитический отчёт
Эпидемиологический контроль и микробиология
Период: 01.05.2026 – 31.05.2026
Сформировал: artifact_admin
Дата формирования: 06.05.2026 07:14

[Блок «Сводка»]
Всего исследований                    1
Положительные                         1
Доля положительных                    100,0%
Выделений микроорганизмов (всего)    1

[Блок «Топ микроорганизмов»]   ← новый, был только в БД
№   Микроорганизм              Выделений    Доля
1   TMIC - Test microbe        1            100,0%

[Блок «Фильтры»]
Дата от                01.05.2026
Дата до                31.05.2026
Отделение              Test ICU
Рост                   Да

[Таблица данных, landscape]
ID  Лаб.№  ФИО пациента          Категория              Дата взятия       Отделение  ...
1   LAB-T  Synthetic Patient 001 Офицер (прапорщик)    01.05.2026 09:00  Test ICU   ...
```

### Конкретные изменения в коде

1. `app/infrastructure/reporting/analytics_pdf.py`:
   - Перейти на `landscape(A4)` для таблицы данных (а лучше — определять автоматически по числу колонок).
   - Все ячейки таблицы оборачивать в `Paragraph(escape(value), style)` для word-wrap.
   - Использовать `formatters.format_*` для всех значений.
   - Добавить блок Топ микроорганизмов (сейчас `top_microbes` есть в `agg`, но не выводится).
   - Добавить общий заголовок отчёта с логотипом ВМА (если есть) или просто текст.

2. Тесты:
   ```python
   def test_analytics_pdf_has_title()
   def test_analytics_pdf_has_top_microbes_block()
   def test_analytics_pdf_no_charwise_breaks_in_categories(fixture_long_category)
   def test_analytics_pdf_landscape_for_wide_tables()
   def test_analytics_pdf_includes_period_filters_author_date()
   ```

---

## P1.4. Analytics XLSX — оформление

### Что добавить (от ChatGPT + Claude)

#### Лист «Сводка»

- Bold header: A1:B1.
- Ширины: A=24, B=20.
- `B5` (доля) — `cell.value = 0.123` (число), `cell.number_format = '0.0%'`.
- `B2` (дата отчёта) — `cell.value = datetime(...)` + `number_format = 'DD.MM.YYYY HH:MM'`.

#### Лист «Фильтры»

- Bold header.
- Все enum-значения через `formatters.format_*`.

#### Лист «Данные»

- Bold header, freeze panes на `A2`.
- AutoFilter на всю область.
- Column widths по содержимому (минимум 12 для всех, до 40 для ФИО/диагнозов).
- Все datetime — настоящие datetime, не строки.
- ID-колонки сопровождаются именованной (`ID типа материала=1` + `Тип материала=Кровь`).

#### Новый лист «Топ микроорганизмов»

- Колонки: №, Код, Наименование, Выделений, Доля.

#### Новый лист «meta» (служебный, скрытый)

- `schema_version`, `app_version`, `db_revision`, `generated_at`, `generated_by`.

### Тесты P1.4 (через openpyxl)

```python
def test_xlsx_has_freeze_panes_on_data_sheet()
def test_xlsx_has_autofilter_on_data_sheet()
def test_xlsx_data_header_is_bold()
def test_xlsx_positive_share_cell_is_percent_format()
def test_xlsx_dates_are_datetime_not_string()
def test_xlsx_no_none_literal_in_cells()
def test_xlsx_has_top_microbes_sheet()
def test_xlsx_meta_sheet_has_schema_version()
def test_xlsx_column_widths_above_default()
```

---

## P1.5. Form100 ↔ ЭМЗ data integrity

### Проблема

В тестовом артефакте у пациента `id=1`:
- `patients.full_name = "Synthetic Patient 001"`
- `form100.main_full_name = "Synthetic Form100 Patient"` (другое!)
- `patients.dob = 1990-01-01`
- `form100.birth_date = 1992-02-02` (другое!)

Карточка привязана к `emr_case.id=1` → пациент `id=1`. Но ФИО/ДР в карточке **независимы** от пациента. Можно создать карточку с любыми ФИО/ДР на чужой ЭМЗ.

### Что делать

Это by-design в полевой Form100 (заполняется до известности пациента), но без сверки опасно.

1. В `form100_view.py` / `form100_wizard.py` при наличии `emr_case_id` показывать **diff-баннер**:
   - Если `main_full_name != patient.full_name` → жёлтое предупреждение «ФИО в карточке отличается от ФИО пациента в ЭМЗ. Проверьте корректность.»
   - Аналогично для ДР.

2. Опционально: при создании Form100 из ЭМК-карточки автозаполнять `main_full_name`, `birth_date` из `patients`.

3. В PDF Form100 в блоке «Связанная госпитализация» (см. P1.2.6) показать `patient.full_name` рядом с `main_full_name` если они отличаются.

4. Тест:
   ```python
   def test_form100_view_shows_diff_warning_when_names_differ(...)
   def test_form100_pdf_shows_both_names_when_differ(...)
   ```

---

## P1.6. ИСМП-показатели в аналитических отчётах

### Ситуация

В UI раздела «Аналитика» есть полноценный блок «ИСМП показатели» (скриншот предоставлен):

```
Госпитализаций: N   Случаев ИСМП: N   Инцидентность: X.X на 1000
Плотность: X.X на 1000 койко-дн.   Превалентность: X.X%

Тип ИСМП        Количество
ВАП             N
КА-ИК           N
...
```

Бэкенд для этого блока полностью реализован — `AnalyticsService.get_ismp_metrics()` считает все показатели:

```python
# analytics_service.py — get_ismp_metrics() возвращает:
{
    "total_cases": int,          # Всего госпитализаций
    "total_patient_days": int,   # Койко-дней
    "ismp_total": int,           # Всего случаев ИСМП (события)
    "ismp_cases": int,           # Госпитализаций с ИСМП
    "incidence": float,          # Инцидентность = ismp_cases / total_cases * 1000
    "incidence_density": float,  # Плотность = ismp_total / total_patient_days * 1000
    "prevalence": float,         # Превалентность = ismp_cases / total_cases * 100
    "by_type": [                 # Разбивка по типам
        {"type": "ВАП", "count": N},
        {"type": "КА-ИК", "count": N},
        # ВАП | КА-ИК | КА-ИМП | ИОХВ | ПАП | БАК | СЕПСИС
    ]
}
```

**Проблема:** `ReportingService.export_analytics_pdf()` и `export_analytics_xlsx()` не вызывают `get_ismp_metrics()`. Данные есть в системе — в отчёты не попадают.

### Что добавить

#### В analytics PDF (`app/infrastructure/reporting/analytics_pdf.py`)

Новый блок после «Топ микроорганизмов» (или сразу после «Сводки»):

```text
ИСМП — Инфекции, связанные с оказанием медицинской помощи
───────────────────────────────────────────────────────────
Показатель                           Значение
Всего госпитализаций                 N
Госпитализаций с ИСМП               N
Инцидентность (на 1000 госпит.)     X.X
Плотность (на 1000 койко-дн.)       X.X
Превалентность                       X.X%

Разбивка по типам ИСМП:
Тип ИСМП         Случаев    Доля от всех ИСМП
ВАП              N          X.X%
КА-ИК            N          X.X%
...
```

Если данных нет (пустой период) — показать: «Случаев ИСМП в выбранном периоде не зарегистрировано».

#### В analytics XLSX (`app/infrastructure/reporting/analytics_xlsx.py` или аналог)

Новый лист **«ИСМП»** со структурой:

| Показатель | Значение |
|-----------|---------|
| Всего госпитализаций | N |
| Госпитализаций с ИСМП | N |
| Инцидентность (на 1000 госп.) | X.X |
| Плотность (на 1000 койко-дн.) | X.X |
| Превалентность | X.X% |

И ниже — таблица разбивки по типам с колонками: Тип ИСМП / Случаев / Доля (%).

Все числа — реальные типы (`float`, `int`), не строки:
- Показатели с десятичными → `float` с `number_format='0.0'`
- Превалентность → `float` с `number_format='0.0%'`

#### В `ReportingService`

Добавить в `export_analytics_pdf()` и `export_analytics_xlsx()` получение метрик:

```python
ismp_data = self.analytics_service.get_ismp_metrics(
    date_from=request.date_from,
    date_to=request.date_to,
    department_id=request.department_id,
)
```

и передачу в генератор отчёта.

#### В `report_run.summary`

Добавить ИСМП-поля в summary, которые сохраняются в БД:

```python
summary = {
    "total": ...,
    "positives": ...,
    "positive_share": ...,
    "top_microbes": [...],
    "total_microbe_isolations": ...,
    # Новое:
    "ismp_cases": N,
    "ismp_incidence": X.X,
    "ismp_incidence_density": X.X,
    "ismp_prevalence": X.X,
    "ismp_by_type": [{"type": "ВАП", "count": N}, ...],
}
```

### Тесты P1.6 (ИСМП)

```python
# tests/unit/test_analytics_pdf_ismp.py
def test_analytics_pdf_contains_ismp_section(seeded_db_with_ismp)
def test_analytics_pdf_ismp_shows_incidence_density_prevalence()
def test_analytics_pdf_ismp_table_has_types_breakdown()
def test_analytics_pdf_ismp_empty_period_shows_placeholder()

# tests/unit/test_analytics_xlsx_ismp.py
def test_analytics_xlsx_has_ismp_sheet()
def test_analytics_xlsx_ismp_prevalence_cell_is_percent_format()
def test_analytics_xlsx_ismp_metrics_are_numeric_not_string()

# tests/integration/test_analytics_report_ismp.py
def test_export_analytics_calls_get_ismp_metrics(seeded_db_with_ismp)
def test_report_run_summary_includes_ismp_fields()
def test_ismp_metrics_match_ui_values(seeded_db_with_ismp)
    # Один и тот же вызов get_ismp_metrics → одни значения в UI и в отчёте
```

### Fixture `seeded_db_with_ismp`

```python
@pytest.fixture
def seeded_db_with_ismp(seeded_db):
    # Создать emr_case с known length_of_stay_days
    # Добавить 2–3 записи ismp_case разных типов (ВАП, КА-ИК, ИОХВ)
    # Вернуть БД с предсказуемыми значениями инцидентности/плотности
    ...
```

### Acceptance criteria

- `analytics_report.pdf` содержит блок «ИСМП» с числами, совпадающими с `get_ismp_metrics()`.
- `analytics_report.xlsx` содержит лист «ИСМП» с числовыми ячейками (не строками).
- `report_run.summary` в БД содержит `ismp_cases`, `ismp_incidence`, `ismp_prevalence`.
- При пустом периоде (0 случаев) — корректные нули, без деления на ноль.

---

## P1.7. Локализация заголовков и резолвинг ID в CSV/PDF

### Проблема

| Где | `qc_due_at` / `qc_status` | `material_type_id` | `created_by` |
|-----|:---:|:---:|:---:|
| Excel экспорт | ✅ `Срок QC` / `Статус QC` | `1` (int) | `1` (int) |
| CSV экспорт | ❌ `qc_due_at` / `qc_status` | `1` (int) | `1` (int) |
| PDF экспорт | ❌ `qc_due_at` / `qc_status` | `1` (int) | `1` (int) |
| Аналитика | — | ✅ `BLD - Blood` | — |

Три разных уровня локализации в трёх форматах. Нужен единый словарь (P1.1) и единый резолвер ID.

### Что делать

1. Использовать `formatters.localize_headers(...)` всюду в exchange-export.
2. Создать `IdResolver` (или расширить `_build_filter_maps` из ReportingService):
   ```python
   class IdResolver:
       def resolve_material_type(self, id_: int) -> str: ...
       def resolve_microorganism(self, id_: int) -> str: ...
       def resolve_antibiotic(self, id_: int) -> str: ...
       def resolve_department(self, id_: int) -> str: ...
       def resolve_user(self, id_: int) -> str: ...  # login or full name
   ```
3. В CSV/PDF добавлять резолвленные значения **рядом** с ID, не вместо (для машинной обработки ID нужен).

---

## P1.8. Единый формат datetime в JSON

### Проблема

В одной системе три разных формата datetime:

| Источник | Пример | Формат |
|----------|--------|--------|
| `manifest.json/exported_at` | `2026-05-06T07:14:46.206189+00:00` | ISO 8601 with TZ |
| `form100_cards.json/created_at` | `2026-05-06 07:14:44.606609` | без T, без TZ |
| `report_history.json/created_at` | `2026-05-06 07:14:46.193508` | без T, без TZ |

### Что делать

1. Единый сериализатор:
   ```python
   def to_iso(dt: datetime) -> str:
       if dt.tzinfo is None:
           dt = dt.replace(tzinfo=timezone.utc)
       return dt.isoformat()  # 2026-05-06T07:14:46.206189+00:00
   ```

2. Подключить в pydantic-модели через `field_serializer`/`Config`:
   ```python
   class Form100CardV2Dto(BaseModel):
       model_config = ConfigDict(json_encoders={datetime: to_iso})
   ```

3. В SQLAlchemy → DTO мапперах гарантировать наличие TZ (UTC по умолчанию).

4. Тест-инвариант:
   ```python
   def test_all_datetime_fields_in_exports_are_iso_with_tz():
       all_jsons = [export_full_json(), export_form100_cards_json(), get_report_history()]
       for blob in all_jsons:
           for path, value in walk_json(blob):
               if path.endswith('_at') and isinstance(value, str):
                   parsed = datetime.fromisoformat(value)
                   assert parsed.tzinfo is not None, f"naive datetime at {path}"
   ```

---

# ЭТАП 3 — P2: качество, exchange schema v2, backup

## P2.1. Raw table PDF/CSV — разделение

### Решение от ChatGPT (принимаем)

Разделить два сценария:
1. **Raw technical export** — машинный CSV/JSON для отладки и обмена.
2. **Human-readable PDF report** — печатный с заголовком, фильтрами, локализацией.

Что сделать минимум:
1. У каждого PDF добавить заголовок: `Технический отчёт: [Имя сущности]`, период, автор.
2. Использовать display labels (см. P1.1).
3. Lab/sanitary PDF: landscape, ограниченный набор колонок по умолчанию + опциональный «полный» режим.
4. `emr_case.pdf` сейчас — только dump таблицы без version/diagnoses/interventions/antibiotics. Это **вводит в заблуждение**, потому что называется «ЭМЗ». Решение:
   - **Вариант A:** переименовать в «Госпитализации» (текущее содержание — список госпитализаций без деталей).
   - **Вариант B:** реализовать настоящий «ЭМЗ PDF» с join'ом `emr_case + emr_case_version + emr_diagnosis + emr_intervention + emr_antibiotic_course + lab_sample + sanitary_sample[через department]`. Объёмнее, но логично.
5. Для CSV сохранить машинные заголовки (опционально с RU-вариантом через флаг `--human-readable`).

### Тесты P2.1

```python
def test_emr_case_pdf_renamed_or_has_full_emz_data()
def test_lab_sample_pdf_uses_landscape()
def test_lab_sample_pdf_no_charwise_header_breaks()
def test_pdf_report_has_title_period_author()
```

---

## P2.2. Exchange Schema v2

### От ChatGPT (принимаем)

Не ломая legacy v1, спроектировать схему v2:
- `schema_version: "2.0"`
- `exported_at` ISO UTC
- booleans `true`/`false` (не `"Да"`/`"Нет"`)
- dates `YYYY-MM-DD`, datetimes ISO 8601
- enum codes стабильные (`outcome_type: "transfer"`, не `"Перевод"`)
- `display_labels` отдельным sub-объектом (опционально, для UI без локализации)
- `app_version`, `db_schema_revision`

### Что добавлять в Claude-аудит

1. POSIX-разделители путей.
2. Все internal paths — относительные от корня пакета.
3. Манифест ZIP содержит:
   ```json
   {
     "schema_version": "2.0",
     "package_id": "<uuid>",
     "app_version": "0.X.Y",
     "db_schema_revision": "2daa0dea652d",
     "created_at": "ISO",
     "created_by": "<login>",
     "source_facility": "<from settings>",
     "entity_counts": {"patients": 1, "lab_sample": 1, ...},
     "files": [{"name": "...", "sha256": "...", "size": ...}],
     "package_sha256": "<hash of all file sha256 concat>"
   }
   ```

### Стратегия выпуска

1. Создать `docs/specs/SPEC_exchange_schema_v2.md` — ТЗ.
2. Реализовать v2 рядом с v1, выбираемое флагом `format_version` в API ExchangeService.
3. По умолчанию пользовательский UI экспорта = v2.
4. Импорт **должен поддерживать обе версии** (по `schema_version` в файле).
5. Через 1 релиз — пометить v1 deprecated, через 2 релиза — удалить.

---

## P2.3. Backup metadata

### Сейчас в `last_backup.json`

```json
{
  "path": "tmp_run\\...\\app_*.db",
  "created_at": "...",
  "reason": "..."
}
```

### Целевой формат

```json
{
  "schema_version": "1.0",
  "format_version": "sqlite-vacuum-v1",
  "path": "backups/app_20260506_071447.db",   ← относительный, POSIX
  "size": 360448,
  "sha256": "e463aa49aa9905...",
  "db_schema_revision": "2daa0dea652d",
  "app_version": "0.X.Y",
  "created_at": "2026-05-06T07:14:47.339210+00:00",
  "created_by": "artifact_admin",
  "reason": "manual",
  "encrypted": false,
  "compressed": false,
  "restore_checked": false,
  "restore_checked_at": null
}
```

Шифрование/сжатие — не делаем сейчас, но **вписываем флаги в контракт**, чтобы не ломать формат при добавлении.

### Тест восстановления

```python
def test_backup_restore_roundtrip(tmp_path, seeded_db):
    meta = backup_service.create_backup()
    sha_before = compute_db_sha(seeded_db)
    # уничтожаем БД
    delete_db()
    backup_service.restore_backup(meta.path)
    sha_after = compute_db_sha(seeded_db)
    assert sha_before == sha_after
```

---

## P2.4. Legacy V1 таблицы Form100

В backup БД присутствуют пустые `form100_card`, `form100_mark`, `form100_stage`. По логам они должны были быть удалены в феврале 2026, но миграция не пройдена.

### Что сделать

1. Убедиться, что в текущей БД эти таблицы **гарантированно пусты** (запрос).
2. Убедиться, что в `form100.legacy_card_id` все записи с непустым legacy_card_id имеют пары — то есть данные мигрированы.
3. Создать миграцию:
   ```
   alembic revision -m "drop_form100_v1_tables"
   # downgrade() должен уметь восстановить таблицы пустыми (без данных)
   ```
4. Тест: после `upgrade head` таблиц нет.

---

# ЭТАП 4 — Validator script и QA

## Скрипт `scripts/validate_generated_artifacts.py`

```python
"""
Usage: python scripts/validate_generated_artifacts.py <path_to_package_dir>

Exits 0 if all invariants hold, 1 otherwise.
Prints a structured report of findings.
"""
```

### Инварианты (полный список)

| # | Проверка | Источник |
|---|----------|---------|
| 1 | `manifest.failure_count == 0` | оба |
| 2 | Все файлы из `manifest.generated[]` существуют | оба |
| 3 | SHA256 каждого файла = SHA256 в manifest | Claude |
| 4 | Все ZIP проходят `testzip()` | оба |
| 5 | Все PDF имеют `%PDF-` header | ChatGPT |
| 6 | Все XLSX открываются `openpyxl.load_workbook()` | ChatGPT |
| 7 | `manifest.root` либо отсутствует, либо `"."` | Claude |
| 8 | В JSON нет абсолютных путей и backslash | Claude |
| 9 | Все datetime в JSON — ISO 8601 с TZ | Claude |
| 10 | `form100_cards.json/version` совпадает с `signed_version` карточки в БД | оба |
| 11 | `form100.artifact_sha256` = SHA256 PDF в ZIP | Claude |
| 12 | Form100 `signed` карточка проходит `validate_for_signing` | ChatGPT |
| 13 | В PDF нет `\nа`-подобных char-wrap'ов в фиксированных тестовых заголовках | ChatGPT |
| 14 | В analytics PDF есть «Топ микроорганизмов», «Период», «Автор» | оба |
| 15 | XLSX имеет `freeze_panes`, `auto_filter`, bold header на «Данные» | ChatGPT |
| 16 | `analytics_*.xlsx` percent-cell имеет `number_format='0.0%'` | оба |
| 17 | `import_errors.json` не содержит `list index out of range`, `Traceback`, `KeyError`, `TypeError` | оба |
| 18 | `import_errors.json` имеет `summary` и поля `row/field/value/error_code/message` | оба |
| 19 | `audit_log` содержит событие на каждый файл из `data_exchange_package` | Claude |
| 20 | Раунд-трип: экспорт CSV пациентов → импорт → diff = 0 | оба |
| 21 | Двойная регенерация PDF одной карточки → байты идентичны | Claude |
| 22 | Двойной экспорт ZIP одной карточки → SHA внутри manifest идентичны | Claude |

---

# ЭТАП 5 — Тесты (сводно)

## Структура

```
tests/
├── unit/
│   ├── test_formatters.py                        ← P1.1
│   ├── test_form100_pdf_layout.py                ← P1.2
│   ├── test_form100_signing_validation.py        ← P0.6
│   ├── test_analytics_pdf_layout.py              ← P1.3
│   ├── test_analytics_xlsx_styling.py            ← P1.4
│   ├── test_id_resolver.py                       ← P1.6
│   ├── test_csv_import_structured_errors.py      ← P0.7
│   ├── test_csv_import_bom_handling.py           ← P0.7
│   ├── test_csv_import_ru_en_headers.py          ← P0.7
│   └── test_audit_event_invariants.py            ← P0.8
├── integration/
│   ├── test_form100_export_is_readonly.py        ← P0.1
│   ├── test_form100_pdf_determinism.py           ← P0.2
│   ├── test_form100_zip_integrity.py             ← P0.3
│   ├── test_full_export_completeness.py          ← P0.4
│   ├── test_manifest_no_pii_paths.py             ← P0.5
│   ├── test_form100_signing_roundtrip.py         ← P0.6
│   ├── test_csv_export_import_roundtrip.py       ← P0.7
│   ├── test_audit_covers_all_exports.py          ← P0.8
│   ├── test_datetime_format_consistency.py       ← P1.7
│   ├── test_backup_restore_roundtrip.py          ← P2.3
│   └── test_legacy_v1_tables_dropped.py          ← P2.4
└── e2e/
    └── test_validate_generated_artifacts.py      ← validator script smoke
```

## Golden tests

Для PDF добавить **bytes-snapshot** теста: один и тот же фиксированный DTO → файл `tests/fixtures/golden/form100_card.pdf`. Любое изменение байтов — fail.

Для XLSX — snapshot структуры (sheet names, headers, freeze_panes, auto_filter ref, number_formats).

---

# ЭТАП 6 — Команды проверок

После КАЖДОГО этапа:

```bash
ruff check app tests
python -m mypy app tests
python -m pytest -q
python -m compileall -q app tests scripts
python scripts/check_architecture.py
```

После закрытия P0:

```bash
python -m alembic upgrade head
python -m alembic check
python scripts/check_mojibake.py
```

После закрытия P1/P2:

```bash
python scripts/generate_test_artifacts.py
python scripts/validate_generated_artifacts.py tmp_run/generated_app_outputs_<latest>
git diff --check
```

---

# ЭТАП 7 — Документация

## Обновить

- `docs/progress_report.md` — после каждого этапа короткий блок: что сделано, какие файлы, какие тесты.
- `docs/session_handoff.md` — снимок состояния для следующей сессии.

## Создать

- `docs/specs/SPEC_form100_export_consistency.md` — read-only export, version snapshot, deterministic PDF.
- `docs/specs/SPEC_form100_signing_validation.md` — обязательные поля для подписи, conditional rules.
- `docs/specs/SPEC_reporting_artifact_quality.md` — единые правила формата дат/процентов/booleans/enums; контракт между machine и human форматами.
- `docs/specs/SPEC_exchange_schema_v2.md` — JSON v2 схема и стратегия миграции.
- `docs/specs/SPEC_audit_coverage.md` — какие операции и какие поля пишутся в `audit_log`.

## Зафиксировать инварианты системы

- Export is read-only.
- Form100 signed_version is immutable across regenerations.
- PDF generation is deterministic for same input.
- Human-readable reports use display formatting.
- Machine exchange uses stable codes and ISO datetimes.
- Signed Form100 has stricter validation than draft.
- Import errors are structured and free of internal exceptions.
- Every export/import operation creates an audit event.

---

# ЭТАП 8 — Финальный отчёт Codex

После закрытия P0+P1 (минимум) дать отчёт:

1. **Root cause summary** — таблица «симптом → корневая причина → фикс».
2. **Form100** — что исправлено, какие новые инварианты введены.
3. **Analytics PDF/XLSX** — что добавлено в оформление и summary.
4. **Import validation** — структура ошибок, BOM handling, RU/EN headers.
5. **Exchange/ZIP/backup** — POSIX-пути, manifest schema, backup metadata.
6. **Audit coverage** — какие операции теперь покрыты.
7. **Изменённые/новые файлы** — список.
8. **Новые/обновлённые тесты** — список с количеством.
9. **Команды проверок** — какие запускались, статусы.
10. **Полный pytest** — кол-во прошедших / пропущенных / упавших.
11. **Открытые вопросы** — что отложено, почему.
12. **Был ли smoke** (offscreen или GUI).
13. **Коммиты** — список SHA + conventional commits messages.

---

# Сводный приоритезированный roadmap

## Спринт 1 — P0 целостность (блокирует всё)

| # | Задача | Сложность | Зависимости |
|---|--------|:---:|------|
| P0.2 | PDF детерминизм (`invariant=1` в ReportLab) | S | — |
| P0.1 | Form100 read-only export, signed_version, form100_artifact таблица | M | — |
| P0.3 | SHA256 целостность ZIP (закрывается P0.1+P0.2) | S | P0.1, P0.2 |
| P0.5 | POSIX-пути и удаление PII из манифестов | S | — |
| P0.4 | ИСМП в полном экспорте | S | — |
| P0.7 | Структурированные ошибки импорта + BOM + RU/EN | M | — |
| P0.6 | SIGNED-валидация Form100 (отдельная спека) | M | — |
| P0.8 | Audit покрытие всех экспортов/импортов | M | — |

## Спринт 2 — P1 формат и оформление

| # | Задача | Сложность |
|---|--------|:---:|
| P1.1 | Единый formatting layer (formatters.py) | M |
| P1.8 | Единый datetime сериализатор | S |
| P1.2 | Form100 PDF layout (даты, projection/side, page-break, EMR-блок) | M |
| P1.3 | Analytics PDF (заголовок, summary, top microbes, landscape) | M |
| P1.4 | Analytics XLSX (freeze, autofilter, percent format, top microbes sheet) | M |
| **P1.6** | **ИСМП-показатели в analytics PDF / XLSX / report_run.summary** | **M** |
| P1.5 | Form100 ↔ patient diff warning | S |
| P1.7 | Localized headers + IdResolver в CSV/PDF | M |

## Спринт 3 — P2 architecture & schema

| # | Задача | Сложность |
|---|--------|:---:|
| P2.2 | Exchange schema v2 (рядом с v1) | L |
| P2.1 | Raw table PDF/CSV полировка, EMR PDF | M |
| P2.3 | Backup metadata extension | S |
| P2.4 | Drop legacy V1 form100 tables | S |
| Validator | scripts/validate_generated_artifacts.py | M |

---

# Критерий завершения работы

Для каждого пункта P0/P1/P2:
- [ ] Спецификация в `docs/specs/SPEC_*.md` (если новая фича/контракт).
- [ ] Реализация по слоям (Domain → Infrastructure → Application → UI).
- [ ] Alembic миграция, если затронута БД.
- [ ] Юнит-тесты + интеграционные тесты + golden snapshot, если применимо.
- [ ] Quality gate: `ruff` + `mypy` + `pytest` + `compileall` + `check_architecture` — все зелёные.
- [ ] Запись в `docs/progress_report.md` и `docs/session_handoff.md`.
- [ ] Conventional commit (`feat:` / `fix:` / `refactor:` / `test:` / `docs:`).
- [ ] `validate_generated_artifacts.py` на свежем пакете → exit 0.

---

**Этот документ — единое ТЗ для Codex. Работа идёт по приоритету сверху вниз. P0 — блокирующий, без него P1/P2 не имеют смысла.**

---

# Спринт 4 — UI и Редизайн (добавлено 2026-05-09)

Задачи появились в ходе работы и не вошли в исходный план. Каждая имеет отдельный документ-спецификацию.

## S4.1. Подтверждение закрытия приложения через системные кнопки

**Спецификация:** `docs/EXIT_CONFIRM_PLAN.md`

**Суть:** при нажатии ✗ окна / Alt+F4 / Cmd+Q приложение закрывается без подтверждения. Кнопка «Выйти» в шапке показывает диалог, а системное закрытие — нет. Нужно добавить `ExitConfirmDialog` и вызывать его в `closeEvent`.

**Ключевые файлы:**
- `app/ui/widgets/logout_dialog.py` — добавить `ExitConfirmDialog` и `confirm_exit`
- `app/ui/main_window.py` — `closeEvent` с `confirm_exit` + флаг `_close_confirmed`
- `app/ui/theme.py` — стили `#exitConfirmDialog`

**Сложность:** S (один коммит).

**Conventional commit:**
```
feat: confirm exit on system close (✗ button, Alt+F4)
```

---

## S4.2. Редизайн раздела «Аналитика» (v2)

**Спецификации:**
- `docs/specs/SPEC_analytics_redesign_plan.md` — финальный утверждённый план (8 этапов)
- `docs/specs/SPEC_analytics_redesign.md` — regression-сценарии (130+ чек-боксов)

**Суть:** текущий раздел — длинная вертикальная простыня из 9 секций без визуальной иерархии, в устаревшем QGroupBox-стиле. Редизайн без потери функционала: 5 вкладок (Обзор / Микробиология / ИСМП / Поиск / Отчёты), KPI-cards с тренд-индикаторами, новые фичи (heatmap, resistance pattern, drill-down, sparklines, quick filter chips), стиль системы.

**Этапы:**

| Этап | Что | Коммит |
|------|-----|--------|
| 0 | Флаг `use_analytics_v2` в UserPreferences + миграция | `chore: add analytics v2 feature flag` |
| 1 | Каркас: tabs + sticky filter-bar + controller.py | `refactor: extract analytics view into tabs (v2 behind feature flag)` |
| 2 | KPI-cards (40×40px иконка, гибрид B+C) + Overview tab | `feat: analytics overview tab with KPI cards and trend indicators` |
| 3 | Sparklines + drill-down | `feat: KPI cards sparklines and drill-down navigation` |
| 4 | Microbiology tab: heatmap + resistance pattern + quick chips | `feat: microbiology tab with heatmap, resistance pattern and quick filter chips` |
| 5 | ISMP tab: donut + bar + KPI | `feat: ismp tab redesign with donut and trend charts` |
| 6 | Search tab + Reports tab + color-coded badges | `feat: search and reports tabs with color-coded badges` |
| 7 | Стиль: QGroupBox → sectionFrame, empty states, loading | `feat: analytics v2 styling polish` |
| 8 | Удаление v1, v2 как default | `chore: remove analytics v1, make v2 default` |

**Ключевые архитектурные решения:**
- `AnalyticsService`, `ReportingService`, DTO — без изменений.
- БД-схема не меняется.
- Все вызовы сервисов через `controller.py` (новый файл-фасад).
- UI не импортирует `app.infrastructure.*`.
- Старая страница работает до этапа 8 — переключение по флагу в UserPreferences.
- P1.3 и P1.4 (полировка analytics PDF/XLSX) делаются после этапа 5 v2, не раньше.

**Утверждённый дизайн KPI-карточки:**
- Размер иконки: 40×40px, border-radius 10px.
- Цветные плашки по категории: мятный (нейтральная статистика), красный (ИСМП), амбер (лаборатория), фиолетовый (расчётные показатели).
- Значение: 22px, tabular-nums, letter-spacing -0.3px.
- Тренд в одной строке со значением.
- Hover: border-color меняется на акцентный (намёк на drill-down).

**Сложность:** L (5–6 спринтов, 8 коммитов).


---

## S4.3. Обновление документации

**Приоритет:** выполняется последним, после закрытия P1, S4.1, S4.2.

**Суть:** в ходе работы накопились изменения в поведении, интерфейсе и форматах, которые не отражены в пользовательской и технической документации. Нужен финальный проход по всем doc-файлам.

### Что обновить

| Файл | Что |
|------|-----|
| `docs/user_guide.md` | Новое название раздела «Первичные медицинские карточки (ф. 100)»; дата рождения в карточке; новая структура Analytics v2 (5 вкладок); блок ИСМП в отчётах; подтверждение закрытия приложения |
| `docs/manual_regression_scenarios.md` | Добавить сценарии из `docs/specs/SPEC_analytics_redesign.md` (разделы 1–11); сценарии exit confirmation; round-trip импорта/экспорта CSV |
| `docs/tech_guide.md` | Новые модули: `formatters.py`, `id_resolver.py`, `bodymap_zones.py`, `bodymap_geometry.py`, `controller.py` (Analytics v2); новые сервисные методы и их сигнатуры |
| `CHANGELOG.md` | Записи по версии 1.1.0: все закрытые P0/P1/S4 задачи с коммитами |
| `README.md` | Если есть — обновить описание ключевых возможностей |

### Что НЕ трогать

- `docs/specs/SPEC_*.md` — спеки актуальны, не менять.
- `docs/CODEX_ACTION_PLAN.md` — живой документ, Codex обновляет сам через `progress_report`.
- `docs/progress_report.md` и `docs/session_handoff.md` — Codex ведёт сам.

### Conventional commit

```
docs: update user guide, tech guide, regression scenarios and CHANGELOG for v1.1.0
```

**Сложность:** M (один коммит, только текст).

