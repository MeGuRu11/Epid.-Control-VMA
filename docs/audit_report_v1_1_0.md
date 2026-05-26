# Аудит системы Epid.-Control-VMA v1.1.0

**Дата:** 2026-05-26
**Аудируемый коммит:** `191c560` (`chore: comprehensive system audit and regression check for v1.1.0`)
**Исполнитель:** Codex (автоматизированные) + Пользователь (ручные)

---

## 1. Автоматизированные проверки

| Проверка | Результат | Детали |
|----------|-----------|--------|
| Python | pass | `Python: 3.12.10 (MSC v.1943 64 bit)` |
| git log | pass | `191c560 chore: comprehensive system audit and regression check for v1.1.0` |
| git status | pass | Рабочая копия была чистой на старте аудита |
| ruff check | pass | `python -m ruff check app tests scripts` → `All checks passed!` |
| mypy | pass | `397 source files`, `0 errors` |
| check_architecture.py | pass | `No architectural violations found.` |
| compileall | pass | `python -m compileall -q app tests scripts` |
| pytest | pass | `861 passed`, `3 warnings`, `194.31s` |
| pytest --cov | warning | `861 passed`, `3 warnings`, coverage `78%`; HTML: `htmlcov/index.html` |
| alembic check | pass | `No new upgrade operations detected.` |
| alembic heads | pass | `0021_form100_artifacts (head)` |
| check_mojibake.py | pass | `No mojibake detected.` |
| seed_demo_data.py --clear | pass | Demo DB cleaned: `C:\Users\user\AppData\Local\epid-control\epid-control\app.db` |
| seed_demo_data.py | pass | 5 patients, 15 EMZ cases, 58 lab samples, 8 sanitary samples, 1 Form100 card |
| generate_sample_exports.py --skip-seed | pass | `15 OK / 0 SKIP / 0 ERROR`, `docs/sample_exports` |
| test_import_roundtrip.py | pass | `7 PASS / 0 FAIL` |

**Итог автоматизированных:** все команды завершились с exit code `0`. Найдены не падения команд, а release-gate issues по регрессионному чеклисту и ручной приёмке.

Предупреждения pytest:

- `reportlab`: `ast.NameConstant is deprecated and will be removed in Python 3.14`.
- `pytest-qt`: два `RuntimeWarning: Failed to disconnect ... timeout()`.
- `pytest-asyncio`: в начале запуска выводится предупреждение о unset `asyncio_default_fixture_loop_scope`.

Отдельное наблюдение: вывод `generate_sample_exports.py` и `test_import_roundtrip.py` в текущем PowerShell отображает кириллицу как mojibake, но файловая проверка `python scripts\check_mojibake.py` прошла. Это выглядит как проблема кодировки консольного вывода, не как порча файлов репозитория.

---

## 2. Покрытие тестами

**Общее покрытие:** `78%`
**HTML-отчёт:** `htmlcov/index.html`

**Модули с покрытием < 40%:**

| Модуль | Покрытие | Тип | Действие |
|--------|----------|-----|----------|
| `app/ui/form100_v2/wizard_widgets/form100_main_widget.py` | `0%` | GUI / legacy candidate | Проверить, используется ли старый wizard widget; если нет — удалить после релиза, если да — добавить smoke-тест |
| `app/ui/patient/patient_edit_dialog.py` | `0%` | GUI | Добавить focused smoke-тест редактирования пациента |
| `app/ui/patient/patient_emk_view.py` | `12%` | GUI | Добавить smoke/regression на поиск, карточку, переход к ЭМЗ |
| `app/ui/form100_v2/widgets/bodymap_editor_v2.py` | `17%` | GUI | Приемлемо для релиза только при ручной проверке bodymap; затем поднять покрытие |
| `app/ui/patient/emk_utils.py` | `20%` | UI helpers | Добавить unit-тесты форматирования/сборки строк |
| `app/ui/widgets/patient_search_dialog.py` | `27%` | GUI | Добавить smoke-тест выбора пациента |
| `app/ui/widgets/patient_selector.py` | `36%` | GUI | Добавить smoke-тест состояния selector |
| `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` | `37%` | GUI | Есть частичное покрытие geometry constants; нужен smoke интерактива |

Top-5 самых слабых модулей: `form100_main_widget.py`, `patient_edit_dialog.py`, `patient_emk_view.py`, `bodymap_editor_v2.py`, `emk_utils.py`.

---

## 3. Регрессионный чеклист

Файл детализации: `docs/audit_v1_1_0/regression_checklist.md`.

- Всего пунктов: `122`.
- Пройдено автоматически: `53/122`.
- Требует ручной проверки: `55/122`.
- Static gap / obsolete: `14/122`.

Ключевые gap-пункты, найденные статическим аудитом:

- `QuickFilterChips` не содержит chip `Только Грам−` / `Только Грам+`; в коде есть только `Только положительные`, `Только из крови`, `Только из ран`.
- `SearchTab` не включает сортировку таблицы по колонкам.
- `SearchTab` не содержит обработчика клика по строке для preview пробы.
- При `>1000` результатов `SearchTab` обрезает список до `rows[:1000]` с warning, но не имеет pagination/virtualization.
- Analytics export default filename сейчас `analytics_report.xlsx`, а не датированный `analytics_YYYY-MM-DD.xlsx`.
- Quick-export текущей вкладки (`Скачать отчёт`) не найден.
- `ReportsTab` не содержит action-column, open/save-as действий и фильтра периода `от-до`.
- `ReportsTab` type filter содержит `Аналитика`, но не содержит явные `Form100` / `Все`.
- Пункты про откат на Analytics v1 / `use_analytics_v2` устарели: v1 и feature flag удалены в S4.2 финальной миграции.

---

## 4. Ручной аудит (требует действия пользователя)

Следующие области требуют ручной проверки в UI перед релизом:

### 4.1. Form100 V2

- [ ] Создать карточку (черновик), убедиться что dirty-banner появляется.
- [ ] Подписать карточку — статус DRAFT → SIGNED.
- [ ] Экспорт PDF — открыть, проверить что bodymap метки видны.
- [ ] Архивирование карточки.
- [ ] Снять подпись (если роль admin).

### 4.2. Analytics v2

- [ ] Открыть все 5 вкладок текущей реализации: `Обзор`, `Микробиология`, `ИСМП`, `Поиск`, `Отчёты`.
- [ ] KPI отображаются корректно на seeded data.
- [ ] Drill-down по KPI и heatmap не теряет фильтры.
- [ ] Heatmap 10×10 визуально читаема и не ломает layout.
- [ ] Resistance grid визуально показывает S/I/R состояния.
- [ ] Проверить gap-пункты из раздела 3 и решить: исправить до релиза или явно принять как scope change.

### 4.3. Импорт/Экспорт (P0.x)

- [x] Сгенерировать `docs/sample_exports/` через скрипт — автоматизировано, `15 OK`.
- [x] Импортировать `full_export.xlsx` обратно — автоматизировано, `0 errors`.
- [x] Импортировать `full_export.zip` — автоматизировано, `0 errors`.
- [x] CSV-импорт для 4 таблиц — автоматизировано, `patients`, `lab_sample`, `sanitary_sample`, `emr_case`.
- [ ] Открыть `analytics.pdf` — 7 страниц, цифры не слипаются.

### 4.4. ЭМЗ (новый редизайн)

- [ ] Открыть `ЭМЗ` — chip-навигация работает.
- [ ] Заполнить все обязательные поля — footer-кнопка становится enabled.
- [ ] Добавить/удалить строки в 4 таблицах.
- [ ] Сохранить → переключиться на `Поиск и ЭМК` → найти запись.
- [ ] Кликнуть `Редактировать ЭМЗ` — переключается вкладка с breadcrumb.
- [ ] Сохранить изменения → ЭМК обновляется.

### 4.5. Прочее

- [ ] Закрытие приложения через `X` показывает диалог подтверждения.
- [ ] `Alt+F4` показывает диалог.
- [ ] История отчётов — открыть, проверить SHA256.
- [ ] Backup — создать через меню, проверить файл `.db` и `audit_log`.

---

## 5. Найденные проблемы

| Приоритет | Описание | Действие |
|-----------|----------|----------|
| Critical | Ручной QA выявил, что date/date-time поля не принимают нормальный keyboard/paste ввод | Исправлено в follow-up: общий date-input слой поддерживает цифры и paste; нужен повторный ручной smoke |
| High | В диалогах лабораторной и санитарной пробы отсутствовали видимые идентификаторы (`Лаб. номер`, `Штрихкод`) и часть контекстных полей | Исправлено в follow-up: поля добавлены в UI/DTO/service/repository; нужен повторный ручной smoke |
| Medium | Form100 sidebar обрезал длинный заголовок; Analytics показывала ISO-week labels вида `2026-W05` | Исправлено в follow-up: sidebar расширен/переносится, week labels заменены на диапазоны дат |
| Low | Ручной regression-pass остаётся обязательным релизным шагом: `55/122` пунктов Analytics checklist и общие UI-сценарии требуют действий пользователя | Выполнить после follow-up исправлений |
| Low | `14/122` пунктов Analytics regression checklist имеют static gap/obsolete статус | Принято как scope change: перенесено в `v1.2 backlog`, не блокирует v1.1.0 |
| Medium | Покрытие ниже `40%` в 8 UI-модулях, включая Patient/EMK и Form100 bodymap | Добавить smoke/unit тесты после релизного решения по High-пунктам |
| Medium | `form100_main_widget.py` имеет `0%` coverage и выглядит как legacy/dead-code candidate | Проверить использование и удалить/покрыть после релиза |
| Low | Предупреждения pytest от `reportlab`, `pytest-qt`, `pytest-asyncio` | Занести в backlog |
| Low | PowerShell отображает кириллический stdout export/roundtrip скриптов как mojibake | Настроить UTF-8 output encoding для CLI scripts/консоли |

**Если Critical/High найдены — релиз НЕ выпускается без решения этих пунктов.**

---

## 6. Соответствие плану CODEX_ACTION_PLAN.md

| Пункт | Статус аудита |
|-------|---------------|
| P0.x — экспорты human-readable + safe round-trip | Закрыто автоматикой: sample exports `15 OK`, round-trip `7 PASS / 0 FAIL` |
| P1.3 — Analytics PDF v2 | Автотесты и sample export проходят; ручной PDF-view остаётся нужен |
| P1.4 — Analytics XLSX v2 | Автотесты и sample export проходят |
| P1.5 — Import/Export wizard UX | Автотесты проходят |
| S4.1 — Confirm dialog on close | Нужен ручной smoke `X` / `Alt+F4` |
| S4.2 — Analytics v2 | Автотесты проходят; `14` gap/obsolete пунктов приняты как `v1.2 backlog` |
| S4.5 — Lab/sanitary sample dialogs redesign | Follow-up добавил недостающие поля; нужен повторный ручной smoke диалогов |
| EMZ redesign | Follow-up исправил общий date input; нужен повторный ручной smoke сценария редактирования |
| S4.6 — этот аудит | Автоматизированная часть выполнена; ручная часть не выполнена |

---

## 7. Версионирование

- Текущая версия в `pyproject.toml`: `1.1.0`.
- `app/__init__.py`: `__version__` отсутствует.
- `CHANGELOG.md`: запись `[1.1.0] — 2026-05-18` уже существует.
- Git tag `v1.1.0`: не найден.

Версионный bump/tag/push не выполнялись, потому что ручная проверка и High release-gates ещё не закрыты.

---

## 8. Рекомендации после релиза

- Поднять coverage критических UI-модулей до `60%`, начиная с Patient/EMK и Form100 bodymap.
- Сделать профилирование Analytics v2 на `10k` проб.
- Настроить UTF-8 stdout для Windows CLI scripts.
- Добавить Pyright/Pylance config для подавления типовых Qt optional-warning noise, если команда использует Pyright.
- Выполнить повторный ручной smoke по date input, Lab/San dialogs, Form100 sidebar и Analytics weekly labels.
- Перенести `v1.2 backlog` пункты из regression checklist в отдельный roadmap после релиза.

---

## Готовность к релизу

**Вердикт:** ⚠️ Готовность зависит от повторного ручного smoke после follow-up исправлений.

Автоматизированные quality gates повторно пройдены после follow-up исправлений: ruff, mypy, architecture, compileall, полный pytest, Alembic, mojibake и sample export round-trip зелёные. Остался ручной smoke пользователем. Static gaps Analytics приняты как scope change для `v1.2.0`.
