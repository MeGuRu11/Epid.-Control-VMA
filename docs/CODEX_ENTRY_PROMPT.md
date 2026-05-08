# Prompt: Epid Control — Аудит и исправление отчётности

Ты работаешь в репозитории **Epid.-Control-VMA**.

Тебе предстоит системное исправление качества отчётности, экспортов и диагностических артефактов приложения. Главный документ с планом уже готов — он лежит в корне репозитория как `CODEX_ACTION_PLAN.md`. Он включает исчерпывающий аудит, root-cause анализ по каждой проблеме и полный план работ по этапам P0→P1→P2.

**Не начинай кодить, пока не выполнишь шаги ниже полностью.**

---

## Шаг 1. Онбординг — что прочитать обязательно

Читай строго в этом порядке. Каждый файл важен:

```
AGENTS.md
docs/context.md
docs/session_handoff.md
docs/progress_report.md            ← последние 3–4 записи
CODEX_ACTION_PLAN.md               ← главный документ задачи
```

Дополнительно, если задача затрагивает конкретный модуль:

```
docs/tech_guide.md                 ← схема БД, сервисы, архитектура слоёв
docs/specs/SPEC_*.md               ← существующие спецификации form100/exchange/analytics
app/application/services/form100_service_v2.py
app/application/services/reporting_service.py
app/application/services/exchange_service.py
app/infrastructure/reporting/form100_pdf_report_v2.py
app/infrastructure/export/form100_export_v2.py
app/domain/rules/form100_rules_v2.py
```

---

## Шаг 2. Ориентация в состоянии репозитория

Выполни эти команды и зафиксируй результаты:

```powershell
git log --oneline -10
git status
git branch --show-current

ruff check app tests
python scripts/check_architecture.py
python -m mypy app tests

$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
python -m alembic current
python -m alembic heads
python -m alembic check

python -m pytest -q --tb=no -q
```

Ожидаемое исходное состояние (если не было изменений после последнего коммита):
- `ruff` — 0 ошибок
- `mypy` — 0 ошибок, 285 source files
- `pytest` — 359 passed
- `alembic current` — `2daa0dea652d (head)`

Если что-то не совпадает — зафикси расхождение и **не начинай задачу до выяснения причины**.

---

## Шаг 3. Составь root-cause-план в чате

После прочтения `CODEX_ACTION_PLAN.md` напиши **в своём ответе** (до первого изменения кода):

1. Список файлов, которые будут затронуты в рамках **P0 (текущий приоритет)**.
2. Порядок, в котором будешь делать P0-пункты, с обоснованием.
3. Список Alembic-миграций, которые потребуются.
4. Список новых тестов-инвариантов.
5. Всё, что непонятно или требует уточнения у пользователя, — **отдельным блоком** в конце.

Только после того, как пользователь подтвердит план, — приступай к коду.

---

## Шаг 4. Жёсткие правила работы

Соблюдай всегда, без исключений:

```
✗ Не удалять существующие тесты
✗ Не skip-ать тесты
✗ Не использовать # type: ignore без комментария-обоснования
✗ Не менять схему БД без Alembic-миграции (с upgrade + downgrade)
✗ Не переносить бизнес-логику в UI
✗ UI не импортирует app.infrastructure.*
✗ Не логировать ФИО, ID пациентов в открытом виде сверх необходимого
✗ Не смешивать machine-exchange и human-readable форматы в одном сериализаторе
✗ Экспорт/PDF-генерация/упаковка ZIP — read-only операции.
  Они НЕ повышают card.version, НЕ меняют updated_at/updated_by/status/data
```

---

## Шаг 5. Цикл после КАЖДОГО изменения

```powershell
ruff check app tests
python -m mypy app tests
python -m pytest -q
python -m compileall -q app tests scripts
```

После миграционных изменений:

```powershell
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
python -m alembic upgrade head
python -m alembic check
```

После закрытия каждого P0-пункта — добавь запись в `docs/progress_report.md`.

---

## Шаг 6. Первый пункт для входа в работу — P0.2

Начни с **P0.2** («PDF детерминизм») — это самый изолированный фикс с минимумом зависимостей. Он не требует Alembic-миграции, не трогает схему данных, изолирован в `infrastructure/reporting`, и сразу даёт работающий инвариант: один и тот же DTO → байт-в-байт идентичный PDF.

Критерий принятия P0.2:

```python
# tests/integration/test_form100_pdf_determinism.py

def test_form100_pdf_is_byte_identical_for_same_input(seeded_db):
    """Два последовательных вызова export_pdf на одних данных дают одинаковые байты."""
    pdf_a = reporting_service.export_form100_pdf(card_id=..., file_path=tmp_a, actor_id=1)
    pdf_b = reporting_service.export_form100_pdf(card_id=..., file_path=tmp_b, actor_id=1)
    assert Path(tmp_a).read_bytes() == Path(tmp_b).read_bytes()

def test_analytics_pdf_is_byte_identical_for_same_request(seeded_db):
    """Аналогично для analytics PDF."""
    ...
```

Как фиксить: в `SimpleDocTemplate` или `canvas.Canvas` включить `invariant=1` — это стандартная опция ReportLab для детерминистичной генерации (убирает `/CreationDate`, `/ModDate`, фиксирует `/ID` от содержимого). Проверь все точки создания `SimpleDocTemplate`/`canvas.Canvas` в `app/infrastructure/reporting/`.

После закрытия P0.2 — переходи к P0.1 (Form100 read-only export + signed_version), затем последовательно по плану.

---

## Контекст задачи (кратко)

Анализ реальных артефактов приложения на синтетической БД выявил 6 критических и 15+ серьёзных проблем. Ключевые:

- `form100.version` растёт при каждой генерации PDF (видно по `audit_log`: create→1, sign→2, pdf_generate→3, pdf_generate→4). Подписанная карточка не immutable.
- PDF недетерминирован: `/CreationDate`, `/ModDate`, `/ID` меняются от генерации к генерации → SHA256 пересчитывается → цепочка целостности подписи рвётся.
- SHA256 в `form100.json` и в `manifest.json` одного ZIP-пакета не совпадают для одного PDF.
- `ismp_case` (внутрибольничные инфекции) отсутствует в «полном» экспорте.
- В `manifest.json` утечка абсолютного пути: `C:\Users\user\Desktop\PRo_CODER\...` с именем пользователя ОС.
- Ошибки импорта CSV: `"message": "list index out of range"` — Python IndexError напрямую в пользовательский лог. Корень — BOM в CSV + парсер ждёт EN-заголовки, экспорт пишет RU.
- **ИСМП-показатели (P1.6) — важный отдельный пункт.** В UI аналитики есть блок «ИСМП показатели» с инцидентностью, плотностью, превалентностью и разбивкой по типам (ВАП / КА-ИК / КА-ИМП / ИОХВ / ПАП / БАК / СЕПСИС). `AnalyticsService.get_ismp_metrics()` полностью реализован. Но `ReportingService.export_analytics_pdf/xlsx()` метод не вызывает — данные до отчётов не доходят. Нужно добавить блок «ИСМП» в analytics PDF и лист «ИСМП» в XLSX, а также расширить `report_run.summary` соответствующими полями.

Полный детальный разбор с root-cause и предлагаемыми фиксами — в `CODEX_ACTION_PLAN.md`.

---

## Что писать в коммитах

Conventional Commits:

```
fix: make Form100 PDF generation read-only (no card version bump)
fix: enable ReportLab invariant mode for deterministic PDF output
feat: add form100_artifact table for pdf generation history
fix: include ismp_case in full exchange export
fix: use relative POSIX paths in all export manifests
fix: structured CSV import errors with row/field/error_code/hint
feat: add ISMP metrics block to analytics PDF report
feat: add ИСМП sheet to analytics XLSX with numeric formatting
feat: include ismp_* fields in report_run summary
feat: add audit_log events for all exchange exports and imports
test: Form100 export read-only invariant tests
test: PDF byte-identical determinism tests
```

---

Вопросы перед стартом — задавай. Молча не начинай.
