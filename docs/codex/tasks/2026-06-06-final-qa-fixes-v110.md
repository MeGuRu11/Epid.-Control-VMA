# Задача: final qa fixes v110

## Метаданные
- Создано: 2026-06-06 15:14
- Слаг: `final-qa-fixes-v110`
- Ветка: `main`
- Статус: `завершено локально, готово к ревью`
- Источник запроса: `C:/Users/user/Downloads/CODEX_V110_FINAL_QA_FIXES.md`
- Владелец сессии: `Codex`

## Цель и границы
- Цель: закрыть финальные QA-дефекты перед `v1.1.0`: A1/A2 UI, B PDF enum-локализация, C читаемый Excel/CSV с безопасным round-trip.
- Почему это важно: дефекты найдены ручным Windows smoke-прогоном на чистом профиле и блокируют релизный тег.
- Что входит: тест-first фиксы `PatientEmkView`, combo-плейсхолдера `Исход`, единого источника enum-меток, PDF/Excel/CSV локализации и обратного импорта локализованных enum.
- Что не входит: push/tag, локализация `export_json`, локализация внутреннего `export.xlsx` в ZIP, изменение машинного поведения `export_excel`/`export_csv` по умолчанию, изменение полнословного пола в карточке пациента.
- Ограничения / риски: A1/A2 требуют живой GUI-проверки через `python -m app.main`; старые guard-тесты обмена не менять; `docs/QA_CHECKLIST_RELEASE_v1.1.0.md` уже был untracked и не относится к задаче.

## Контекст
- Ключевые файлы / модули: `app/ui/patient/patient_emk_view.py`, `app/ui/emz/form_widget_factories.py`, `app/ui/emz/emz_form.py`, `app/application/reporting/formatters.py`, `app/application/services/exchange_service.py`, `app/ui/import_export/import_export_wizard.py`, `app/ui/form100_v2/form100_list_panel.py`.
- Зависимые документы / скиллы: `AGENTS.md`, `docs/context.md`, `docs/codex_workflow.md`, `DESIGN.md`, `superpowers:test-driven-development`, `superpowers:systematic-debugging`, проектный skill `.agents/skills/epid-control`.
- Факты, которые уже подтверждены: `PatientEmkView.results_table` задаёт `Stretch` только для колонки `ФИО`, значит `ID`/`Дата рождения` остаются интерактивными; `create_outcome_type_combo()` добавляет `Не выбран` через `addItem(..., None)`; `_set_outcome_type(None)` выбирает индекс `0`; `exchange_service._ENUM_VALUE_LABELS` неполная и дублирует форматтеры; `form100_list_panel._STATUS_LABELS` дублирует статус Form100.
- Гипотезы / вопросы для проверки: seed-данные покрывают нужные enum для full export; локализованный импорт должен нормализовать значения до машинных до доменной/DB-валидации; `light/medium` severity являются legacy-алиасами и при локализованном импорте могут мапиться в канонические `mild/moderate`.

## План
1. [x] Уточнить критерии готовности и границы.
2. [x] Собрать только релевантный контекст и ссылки на файлы.
3. [x] Написать red-тесты для A1/A2/B/C и подтвердить падения.
4. [x] Исправить UI A1/A2 малыми изменениями.
5. [x] Централизовать enum-метки и подключить PDF/Excel/CSV локализацию с обратным импортом.
6. [x] Прогнать точечные проверки и полный quality gate.
7. [x] Проверить A1/A2 в живом GUI, обновить `docs/progress_report.md` и `docs/session_handoff.md`.

## Checkpoints
### 2026-06-06 15:14
- Создан task-файл.
- Стартовый снимок рабочей директории:
- `?? docs/QA_CHECKLIST_RELEASE_v1.1.0.md`

### 2026-06-06 15:20
- Прочитаны `AGENTS.md`, `docs/context.md`, хвост `docs/progress_report.md`, `docs/session_handoff.md`, `DESIGN.md`, `docs/codex_workflow.md`.
- Подтверждён фактический репозиторий: `C:/Users/user/Desktop/Program/Epid.-Control-VMA`.
- Подтверждены корневые причины A1/A2/B и точка включения C в мастере импорта/экспорта.

### 2026-06-06 16:10
- RED-тесты A1/A2/B/C подтвердили дефекты: интерактивный header, item-плейсхолдер `Не выбран`, отсутствующий formatter/export API, PDF `M/F`, wizard без `localized=True`.
- Реализованы A1/A2/B/C: header modes для EMK, placeholder `Исход`, центральные enum-метки и обратная нормализация, readable Excel/CSV, PDF enum labels, Form100 status delegation.
- Сохранены старые guard-тесты машинного обмена: поведение `export_excel`/`export_csv` по умолчанию не изменено.

### 2026-06-06 16:40
- Targeted GREEN: `102 passed`, затем `44 passed` + `60 passed`.
- Полный тестовый прогон: `python -m pytest -q --tb=short` — `946 passed`, `3 warnings`.
- Первичный полный gate прошёл; `ruff check .` потребовал исключить локальную `.agents` папку внешних skill-скриптов из проверки проекта.

### 2026-06-06 17:20
- Live GUI verifier: `python artifacts\live_gui_v110_final\verify_live_gui_v110_final.py --fresh` — `PASS`, `qt_platform=windows`.
- A1 live: drag widths unchanged, modes `ResizeToContents/Stretch/ResizeToContents`, sections movable/clickable disabled, name/ID filters and case loading passed.
- A2 live: `Исход` placeholder `Не выбран`, `currentIndex == -1`, dropdown without placeholder item, existing `discharge` preselected, save without outcome persisted `NULL`.
- Export verifier: `python artifacts\live_gui_v110_final\verify_exports_v110_final.py` — `PASS`; PDF/Excel/CSV artifacts created, readable Excel/CSV import `error_count == 0`, SQL machine-value checks all `0`.
- Финальный full gate после verifier-скриптов: `ruff`, `mypy`, `pytest`, architecture, compileall, alembic check, mojibake — pass.

## Validation Ledger
- RED targeted A1/A2/B/C before production fixes — failed for the expected reasons.
- Targeted GREEN suite — `102 passed`, `1 warning`.
- Focused follow-up suites — `44 passed`, `1 warning`; `60 passed`, `1 warning`.
- `python artifacts\live_gui_v110_final\verify_live_gui_v110_final.py --fresh` — pass; `qt_platform=windows`.
- `python artifacts\live_gui_v110_final\verify_exports_v110_final.py` — pass.
- `python -m ruff check .` — pass.
- `python -m mypy app tests` — pass (`404 source files`).
- `python -m pytest -q --tb=short` — `946 passed`, `3 warnings`.
- `python scripts\check_architecture.py` — pass.
- `python -m compileall app` — pass.
- `python -m alembic check` — pass (`No new upgrade operations detected.`).
- `python scripts\check_mojibake.py` — pass (`No mojibake detected.`).

## Prompt Patterns
### Планирование
`Сначала обнови этот task-файл: зафиксируй цель, границы, план и критерии готовности. Только потом переходи к правкам.`

### Checkpoint
`Перед следующим крупным шагом обнови Checkpoints и Validation Ledger, чтобы задача пережила паузу или смену сессии.`

### Resume
`Прочитай AGENTS.md, docs/context.md, хвост docs/progress_report.md, docs/session_handoff.md и этот task-файл. После этого продолжай с блока Resume Point.`

### Финальная сверка
`Перед завершением сверь фактические изменения с планом, закрой незавершённые пункты и зафиксируй quality gates.`

## Resume Point
- Следующее действие: ревью локального коммита и, если принято, push/tag владельцем; push/tag в этой сессии не выполнялись.
- Открытые вопросы / блокеры: нет.
- Что обязательно проверить вручную: по желанию владельца открыть сохранённые артефакты `artifacts/live_gui_v110_final/screenshots/*.png`, `exports/pdf_patients.pdf`, `exports/full_export_localized.xlsx`; automated live/export checks уже пройдены на native Windows Qt.
