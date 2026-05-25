# Аудит системы v1.1.0

Дата: 2026-05-26
Режим: автоматизированный аудит S4.6 + фиксация ограничений ручной части.

## Автоматизированные проверки

| Проверка | Команда | Результат |
|----------|---------|-----------|
| Ruff | `python -m ruff check app tests` | pass, `All checks passed!` |
| Mypy | `python -m mypy app tests` | pass, `397 source files`, `0 errors` |
| Архитектура слоёв | `python scripts/check_architecture.py` | pass, `No architectural violations found.` |
| Все тесты | `python -m pytest -q` | pass, `861 passed`, `3 warnings`, `197.47s` |
| Компиляция | `python -m compileall -q app tests scripts` | pass |
| Alembic | `python -m alembic check` | pass, `No new upgrade operations detected.` |
| Mojibake | `python scripts/check_mojibake.py` | pass, `No mojibake detected.` |
| Coverage | `python -m pytest --cov=app --cov-report=term-missing -q` | pass, `861 passed`, `3 warnings`, coverage `78%` |

Пункт S4.6 `python scripts/validate_generated_artifacts.py tmp_run/generated_app_outputs_<latest>` не выполнен: в репозитории нет `scripts/validate_generated_artifacts.py`, а в `tmp_run` нет каталога `generated_app_outputs_*`.

## Регрессионный чеклист

- `docs/specs/SPEC_analytics_redesign.md`: найдено `122` markdown-checkbox.
- Отмечено как выполнено в документе: `0/122`.
- Ручной проход по всем пунктам S4.6 в этой сессии не выполнялся.

Ручные проверки, которые остаются обязательными перед релизной приёмкой:

- Form100: создание, редактирование, подписание, экспорт PDF/ZIP.
- Analytics v2: вкладки, KPI, sparklines, drill-down, heatmap, resistance, donut, color badges.
- Импорт/экспорт: round-trip CSV/XLSX/JSON/ZIP и PDF/XLSX с ИСМП-блоком.
- Диалоги лабораторной и санитарной проб: вкладки, sticky header/footer, inline-валидация, сохранение после переключения вкладок.
- Отчёты: история, SHA256, открыть/скачать.
- Exit confirmation: системная кнопка закрытия и Alt+F4.
- Backup: создание, метаданные, audit_log.

## Покрытие тестами

- Общее покрытие: `78%`.
- Модули ниже `40%`, требующие отдельного решения по UI-тестам или smoke-покрытию:
  - `app/ui/form100_v2/widgets/bodymap_editor_v2.py` — `17%`.
  - `app/ui/form100_v2/wizard_widgets/bodymap_widget.py` — `37%`.
  - `app/ui/form100_v2/wizard_widgets/form100_main_widget.py` — `0%`.
  - `app/ui/patient/emk_utils.py` — `20%`.
  - `app/ui/patient/patient_edit_dialog.py` — `0%`.
  - `app/ui/patient/patient_emk_view.py` — `12%`.
  - `app/ui/widgets/patient_search_dialog.py` — `27%`.
  - `app/ui/widgets/patient_selector.py` — `36%`.

## Найденные проблемы

### High

- S4.6 нельзя считать полностью закрытым без ручного regression-pass: чеклист Analytics в `docs/specs/SPEC_analytics_redesign.md` не отмечен, UI-сценарии из плана не пройдены в этой сессии.

### Medium

- Artifact validation из плана S4.6 не воспроизводится как команда: отсутствует `scripts/validate_generated_artifacts.py` и нет актуального `tmp_run/generated_app_outputs_*`.
- Несколько пользовательских UI-модулей имеют покрытие ниже `40%`, особенно `Patient/EMK` и `Form100 bodymap`.

### Low

- Pytest стабильно проходит, но остаются предупреждения сторонних компонентов:
  - `reportlab`: `ast.NameConstant is deprecated`.
  - `pytest-qt`: `Failed to disconnect ... timeout()`.
  - `pytest-asyncio`: unset `asyncio_default_fixture_loop_scope` выводится в начале запуска.

## Рекомендации

1. Перед релизом выполнить ручной S4.6 regression-pass и отметить результат в `docs/specs/SPEC_analytics_redesign.md` или отдельном manual regression report.
2. Вернуть воспроизводимую artifact validation-команду: либо добавить `scripts/validate_generated_artifacts.py`, либо обновить S4.6 план под текущий `scripts/generate_sample_exports.py` и `docs/sample_exports`.
3. Добавить focused UI/smoke-тесты для модулей ниже `40%`, начиная с patient search/selector и Form100 bodymap.
4. Зафиксировать предупреждение `pytest-asyncio` настройкой `asyncio_default_fixture_loop_scope`, если проект продолжит использовать `pytest-asyncio`.
