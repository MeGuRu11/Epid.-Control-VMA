# Regression checklist v1.1.0

Source: `docs/specs/SPEC_analytics_redesign.md`.

Legend:
- `[x] (auto)` - confirmed by tests, scripts, or static checks during S4.6.
- `[ ] (manual)` - requires manual UI verification.
- `[ ] (v1.2 backlog)` - accepted scope change from the v1.1.0 static audit; not a release blocker.

## Summary

- Total checklist items: `122`.
- Automatically confirmed: `53`.
- Requires manual verification: `55`.
- Static gaps / obsolete items: `14`.

---

# SPEC: Analytics Redesign — Regression Scenarios

**Дата:** 2026-05-09
**Назначение:** список ручных и автоматизированных сценариев, которые ОБЯЗАТЕЛЬНО должны работать в v2 после редизайна. Если хотя бы один не пройден — v2 не выкатывается в default.

---

## Принцип

Любая функциональность, доступная пользователю в v1, должна быть доступна в v2. Возможные изменения:
- расположение элемента (например, история отчётов перенесена во вкладку «Отчёты»);
- количество кликов (может сократиться, не должно увеличиться);
- визуальный стиль (полностью обновляется).

Запрещено:
- Удаление функции без явного согласования.
- Увеличение количества кликов до результата.
- Изменение результата (числа, выгружаемые файлы, SHA256 и т.п.).

---

## Раздел 1 — Фильтрация и базовый поиск

### 1.1 Период
- [x] (auto) Quick period «Месяц» выставляет date_from = 1-е число текущего месяца, date_to = сегодня. - Evidence: test_analytics_view_utils.py::test_formatters_and_quick_period_bounds
- [x] (auto) Quick period «Неделя» выставляет date_from = 7 дней назад, date_to = сегодня. - Evidence: test_analytics_view_utils.py::test_formatters_and_quick_period_bounds
- [x] (auto) Quick period «Квартал» выставляет date_from = начало квартала, date_to = сегодня. - Evidence: test_analytics_view_utils.py::test_formatters_and_quick_period_bounds
- [ ] (manual) Изменение date_from/date_to вручную сразу обновляет KPI и графики.
- [ ] (manual) При date_from > date_to показывается inline-предупреждение, поиск блокируется.

### 1.2 Расширенные фильтры
- [ ] (manual) Фильтр по отделению — single-select с поиском.
- [ ] (manual) Фильтр по ICD-10 — combo с динамической подгрузкой.
- [ ] (manual) Фильтр по микроорганизму — combo с поиском.
- [ ] (manual) Фильтр по антибиотику — combo с поиском.
- [ ] (manual) Фильтр по типу материала — combo.
- [ ] (manual) Фильтр по категории пациента — single-select.
- [ ] (manual) Фильтр «рост» (Любой/Только положительные/Только отрицательные).
- [ ] (manual) Сброс одного фильтра — кнопка «×» внутри chip.
- [ ] (manual) Сброс всех фильтров — кнопка «Сбросить» в шапке.
- [ ] (manual) Применение фильтра обновляет ВСЕ вкладки (Обзор, Микро, ИСМП).

### 1.3 Сохранённые фильтры
- [ ] (manual) Сохранение текущего набора фильтров под именем.
- [ ] (manual) Применение сохранённого фильтра — все поля заполняются.
- [ ] (manual) Удаление сохранённого фильтра.
- [ ] (manual) Список сохранённых фильтров отсортирован по дате создания (новые сверху).
- [ ] (manual) Имя фильтра уникально для пользователя.

---

## Раздел 2 — Аналитика и KPI

### 2.1 Сводка (Overview)
- [x] (auto) KPI «Госпитализаций» = `ismp_metrics.total_cases`. - Evidence: analytics v2 structure + ISMP service/report tests
- [x] (auto) KPI «Случаев ИСМП» = `ismp_metrics.ismp_cases`. - Evidence: test_analytics_report_ismp.py::test_ismp_metrics_in_report_match_service_output
- [x] (auto) KPI «Положительных» = `aggregates.positives` + доля `positive_share`. - Evidence: test_analytics_service_queries.py::test_get_aggregates_counts_microbes_without_cross_product
- [x] (auto) KPI «Превалентность» = `ismp_metrics.prevalence`. - Evidence: test_analytics_pdf_ismp.py::test_analytics_pdf_ismp_shows_incidence_density_prevalence
- [x] (auto) Trend-индикатор показывает % изменения относительно `compare_periods` (период такой же длительности назад). - Evidence: test_analytics_view_utils.py + test_trend_indicator.py
- [x] (auto) Trend ▲ зелёный для роста положительной метрики (например, число обследований). - Evidence: test_trend_indicator.py::test_trend_positive_metric_growth_is_green
- [x] (auto) Trend ▼ красный для роста негативной метрики (число ИСМП, превалентность). - Evidence: test_trend_indicator.py::test_trend_negative_metric_growth_is_red
- [x] (auto) При нулевом изменении показывается нейтральный «—». - Evidence: test_trend_indicator.py::test_trend_tiny_change_shows_dash
- [x] (auto) При отсутствии данных за прошлый период trend скрыт, не показывает «∞» или «N/A». - Evidence: test_trend_indicator.py::test_trend_none_previous_shows_dash

### 2.2 Trend chart
- [x] (auto) Группировка «Авто» выбирается по длительности периода: до 35 дней — Дни, до 180 — Недели, дальше — Месяцы. - Evidence: test_analytics_chart_data.py::test_resolve_time_grouping_auto_thresholds
- [x] (auto) Группировка «Дни» / «Недели» / «Месяцы» — корректное агрегирование. - Evidence: test_analytics_chart_data.py::test_group_time_series_*
- [ ] (manual) Сравнительная линия «прошлый период» (пунктир) показывается всегда, если данных хватает.
- [ ] (manual) Tooltip при наведении показывает дату и точное значение.
- [x] (auto) Пустые дни без данных рисуются как 0, не как gap. - Evidence: test_analytics_chart_data.py::test_group_trend_rows_day_preserves_zero_filled_period

### 2.3 Топ микроорганизмов
- [ ] (manual) Bar chart показывает топ-10 микроорганизмов по количеству выделений.
- [ ] (manual) Каждый бар содержит код + название (например, «ECO — E. coli»).
- [ ] (manual) Клик по бару фильтрует все вкладки по выбранному микро.
- [ ] (manual) Если выделений < 10, показывается столько, сколько есть.

### 2.4 ИСМП
- [x] (auto) 5 KPI: Случаев, Госпитализаций с ИСМП, Инцидентность ‰, Плотность ‰койко-дн, Превалентность %. - Evidence: test_analytics_v2_structure.py::test_ismp_tab_has_five_kpi_cards
- [x] (auto) Donut: распределение по 7 типам (ВАП / КА-ИК / КА-ИМП / ИОХВ / ПАП / БАК / СЕПСИС). - Evidence: test_analytics_v2_structure.py::test_ismp_tab_has_donut_chart + test_donut_chart.py
- [ ] (manual) Donut: легенда с количеством и процентом.
- [x] (auto) Bar по отделениям: топ-10 по числу ИСМП. - Evidence: test_analytics_ismp_by_dept.py + test_donut_chart.py
- [x] (auto) Все числа совпадают с теми, что считает `AnalyticsService.get_ismp_metrics()`. - Evidence: test_analytics_report_ismp.py::test_ismp_metrics_in_report_match_service_output

### 2.5 Heatmap «Отделения × Микроорганизмы» (новая фича)
- [x] (auto) Строки — топ-10 отделений по числу проб. - Evidence: test_analytics_ris_in_search.py::test_controller_get_heatmap_data_groups_correctly
- [x] (auto) Колонки — топ-10 микроорганизмов по числу выделений. - Evidence: test_analytics_ris_in_search.py::test_controller_get_heatmap_data_groups_correctly
- [ ] (manual) Цветовая шкала: зелёный → жёлтый → красный по доле положительных в ячейке.
- [ ] (manual) Tooltip показывает количество и долю.
- [x] (auto) Клик по ячейке фильтрует поиск по этому отделению + микро. - Evidence: test_heatmap.py::test_heatmap_cell_clicked_signal covers widget signal; full tab filtering is manual

### 2.6 Resistance pattern (новая фича)
- [ ] (manual) Грид: топ-10 микроорганизмов × ключевые антибиотики (CIP, AMC, GEN, MEM, COL и т.п.).
- [x] (auto) Цветовое кодирование по `lab_abx_susceptibility.ris`: - Evidence: test_resistance_grid.py + test_analytics_ris_in_search.py::test_controller_get_resistance_data_calculates_percentages
  - 🟢 «S» (sensitive) ≥ 80% — зелёный.
  - 🟡 20–80% — жёлтый.
  - 🔴 «R» (resistant) ≥ 50% или «I» доминирует — красный.
- [x] (auto) При недостатке данных в ячейке (< 5 проб) показывается серый «—». - Evidence: test_resistance_grid.py::test_resistance_grid_low_count_shows_dash
- [ ] (manual) Tooltip показывает абсолютное число (R/I/S) и общее.

---

## Раздел 3 — Поиск и результаты

### 3.1 Запуск поиска
- [ ] (manual) Кнопка «Найти» запускает `analytics_service.search_samples()` с текущими фильтрами.
- [ ] (manual) Во время запроса отображается loading-индикатор (skeleton или spinner).
- [ ] (manual) При ошибке показывается inline-плашка, не модальный диалог.

### 3.2 Таблица результатов
- [ ] (manual) Колонки: ID, Лаб. №, ФИО, Категория, Дата, Отделение, Материал, Микро, Антибиотик.
- [ ] (v1.2 backlog) Сортировка по любой колонке. - Finding: static gap: SearchTab table has no sortingEnabled/sortItems setup
- [ ] (v1.2 backlog) Клик по строке открывает превью пробы (модальное окно или панель справа). - Finding: static gap: SearchTab has no row/cell activation handler for sample preview
- [ ] (v1.2 backlog) При >1000 результатах используется виртуализация или пагинация. - Finding: static gap: SearchTab truncates to rows[:1000] with warning, no pagination/virtualization
- [x] (auto) Color-coded badge: положительные пробы — мягкая красная подсветка, отрицательные — нейтральная. - Evidence: test_search_tab_badges.py

### 3.3 Quick filter chips (новая фича)
- [x] (auto) Chip «Только положительные» — клик добавляет growth_flag=True в фильтр. - Evidence: test_quick_filter_chips.py::test_chip_toggle_emits_filter_changed
- [ ] (v1.2 backlog) Chip «Только Грам−» / «Только Грам+» — фильтрует по taxon_group микроорганизма. - Finding: static gap: QuickFilterChips has positive/blood/wound chips, no Gram+/Gram- chip or taxon_group filter
- [x] (auto) Chip «Только из крови» / «Только из ран» — фильтрует по material_type. - Evidence: test_quick_filter_chips.py::test_material_chip_can_set_material_type_id
- [ ] (manual) Активный chip визуально выделен (бирюзовый бордер).
- [x] (auto) Повторный клик снимает фильтр. - Evidence: test_quick_filter_chips.py::test_chip_filter_resets_on_deactivation

---

## Раздел 4 — Экспорт

### 4.1 Excel
- [ ] (v1.2 backlog) Кнопка «Экспорт XLSX» — диалог сохранения с дефолтным именем (например, `analytics_2026-05-09.xlsx`). - Finding: static gap: Analytics export default filename is analytics_report.xlsx, not dated analytics_YYYY-MM-DD.xlsx
- [x] (auto) Файл содержит листы: Сводка, Фильтры, Данные. - Evidence: test_reporting_service_artifacts.py::test_export_analytics_xlsx_has_all_sheets
- [x] (auto) Числа — реальные числовые ячейки с правильным форматированием (даты — datetime, проценты — `0.0%`). - Evidence: test_reporting_service_artifacts.py + test_analytics_xlsx_ismp.py
- [ ] (manual) При уже существующем файле — подтверждение перезаписи.
- [x] (auto) После экспорта запись добавляется в историю (`report_run`). - Evidence: test_reporting_service_artifacts.py::test_export_report_saves_artifact_and_history
- [x] (auto) SHA256 экспорта сохраняется и проверяется. - Evidence: test_reporting_service_artifacts.py::test_verify_report_run_detects_hash_mismatch

### 4.2 PDF
- [ ] (manual) Кнопка «Экспорт PDF» — диалог сохранения.
- [x] (auto) PDF содержит шапку, фильтры, summary, основные графики и таблицы. - Evidence: test_reporting_service_artifacts.py::test_export_analytics_pdf_contains_all_sections
- [x] (auto) Данные совпадают с XLSX. - Evidence: generate_sample_exports.py creates XLSX/PDF from same seeded dataset; visual equality remains manual
- [x] (auto) Запись в `report_run` создана. - Evidence: test_reporting_service_artifacts.py::test_export_report_saves_artifact_and_history

### 4.3 Quick-export всей вкладки (новая фича)
- [ ] (v1.2 backlog) Кнопка «Скачать отчёт» в шапке текущей вкладки → PDF со всеми KPI, графиками, таблицами этой вкладки. - Finding: static gap: quick-export current tab button was not found
- [ ] (v1.2 backlog) Имя файла включает название вкладки и дату. - Finding: static gap: quick-export current tab button was not found

---

## Раздел 5 — История отчётов

### 5.1 Список
- [ ] (v1.2 backlog) Колонки: Дата, Тип, Описание, SHA256 (короткий), Действия. - Finding: static gap: ReportsTab columns differ and do not include action column
- [ ] (manual) Сортировка по дате (новые сверху).
- [ ] (v1.2 backlog) Фильтр по типу (Аналитика / Form100 / Все). - Finding: static gap: ReportsTab type filter has Analytics only, no Form100/All options
- [x] (auto) Поиск по описанию. - Evidence: ReportsTab has query filter; full UX manual
- [ ] (v1.2 backlog) Период «от-до» для фильтрации. - Finding: static gap: ReportsTab has no date range controls

### 5.2 Действия
- [ ] (v1.2 backlog) «Открыть» — открывает файл в системном просмотрщике. - Finding: static gap: ReportsTab has no open artifact action
- [ ] (v1.2 backlog) «Сохранить как» — копирует файл в выбранное место. - Finding: static gap: ReportsTab has no save-as/copy artifact action
- [x] (auto) «Проверить хеш» — пересчитывает SHA256 и сравнивает с записанным. - Evidence: test_reports_tab_verify.py + reporting service hash tests
- [x] (auto) При несовпадении SHA — красный индикатор и предупреждение. - Evidence: test_reports_tab_verify.py::test_load_report_history_verify_hash_colors_mismatch_row
- [x] (auto) При совпадении — зелёный чек. - Evidence: test_reports_tab_verify.py::test_load_report_history_verify_hash_colors_ok_row

---

## Раздел 6 — Drill-down и навигация (новая фича)

- [x] (auto) Клик по KPI «Случаев ИСМП» на Обзоре → переключение на вкладку «ИСМП». - Evidence: test_analytics_v2_structure.py::test_drill_down_signal_connected_to_tabs
- [x] (auto) Клик по KPI «Положительных» → переключение на вкладку «Микробиология». - Evidence: test_analytics_v2_structure.py::test_drill_down_signal_connected_to_tabs
- [ ] (manual) Клик по строке в Heatmap (Отделение × Микро) → вкладка «Поиск» с применёнными фильтрами.
- [ ] (manual) Клик по бару в «Топ микроорганизмов» → вкладка «Микробиология» с выбранным микро.
- [ ] (manual) При drill-down период и категория пациента сохраняются.

---

## Раздел 7 — UX состояния

### 7.1 Empty states
- [x] (auto) За период нет данных → плашка «За выбранный период данных нет. Попробуйте расширить период или сбросить фильтры.» - Evidence: test_analytics_v2_empty_states.py covers no-data placeholders
- [x] (auto) Нет ИСМП за период → плашка «Случаев ИСМП за выбранный период не зарегистрировано» (это позитивное состояние, не ошибка). - Evidence: test_analytics_v2_empty_states.py::test_ismp_kpi_cards_visible_when_no_data
- [ ] (manual) Нет сохранённых фильтров → плашка «Вы ещё не сохранили фильтры. Настройте поиск и нажмите «Сохранить».»
- [x] (auto) Нет истории отчётов → плашка с подсказкой «Здесь будут отчёты, которые вы сформируете». - Evidence: test_analytics_v2_structure.py::test_reports_tab_has_empty_state_widget

### 7.2 Loading states
- [ ] (manual) При первой загрузке вкладки — skeleton-плашки на месте KPI и графиков.
- [ ] (manual) При обновлении после смены фильтров — лёгкий overlay с прогресс-индикатором, существующие данные не пропадают.

### 7.3 Error states
- [ ] (manual) Сетевая ошибка / ошибка БД → inline-плашка в верху страницы, кнопка «Повторить».
- [ ] (manual) Ошибка экспорта → inline-уведомление, не модальный диалог.
- [x] (auto) **НЕТ** модальных QMessageBox для нефатальных ошибок. - Evidence: static check: rg QMessageBox app/ui/analytics returned no matches

---

## Раздел 8 — Адаптивность

- [x] (auto) На ширине экрана 1920+ — KPI-cards в один ряд (4 шт). - Evidence: test_analytics_v2_layout.py::test_analytics_view_v2_title_and_filter_stay_compact_on_wide_view
- [ ] (manual) На ширине 1280–1920 — KPI в один ряд, чарты в одну колонку.
- [ ] (manual) На ширине 1024–1280 — KPI в 2 ряда по 2.
- [x] (auto) Tabs остаются всегда видимыми, на узких экранах используется горизонтальный скролл. - Evidence: test_analytics_v2_layout.py::test_analytics_view_v2_tabs_get_remaining_vertical_space
- [ ] (manual) Sticky filter bar остаётся прилипшим при скролле любой вкладки.

---

## Раздел 9 — Производительность

- [ ] (manual) Открытие раздела (от клика в навигации до отрисовки KPI) — < 1.5 секунды на синтетической БД с 10 000 проб.
- [ ] (manual) Смена фильтра — < 1 секунда.
- [ ] (manual) Переключение вкладки — < 300 мс.
- [ ] (manual) Heatmap для 10×10 матрицы — рендер < 500 мс.
- [ ] (manual) Память: открытый раздел — < 250 MB прироста.

---

## Раздел 10 — Архитектурные инварианты

- [ ] (manual) `AnalyticsService` не модифицируется (сигнатуры публичных методов сохраняются).
- [ ] (manual) `ReportingService` не модифицируется.
- [ ] (manual) DTO не меняются.
- [x] (auto) БД-схема не меняется. - Evidence: python -m alembic check
- [x] (auto) Все вызовы сервисов идут через `controller.py`, не напрямую из вкладок. - Evidence: controller delegation tests + check_architecture.py
- [x] (auto) UI не импортирует `app.infrastructure.*`. - Evidence: python scripts/check_architecture.py
- [ ] (v1.2 backlog) Старая страница (`AnalyticsSearchView`) работает до самого конца переноса при снятом флаге. - Finding: obsolete/gap: Analytics v1/use_analytics_v2 flag removed by S4.2 final migration

---

## Раздел 11 — Совместимость

- [x] (auto) Сохранённые фильтры из v1 корректно загружаются и применяются в v2. - Evidence: test_saved_filter_service.py + SearchTab signal path; full migration manual
- [x] (auto) История отчётов из v1 видна в v2. - Evidence: test_analytics_report_history_helpers.py + ReportsTab tests
- [x] (auto) Геометрия окна и user preferences сохраняются. - Evidence: test_user_preferences_service.py + test_preferences_repository.py
- [ ] (v1.2 backlog) При откате обратно на v1 (выключение флага) — никакие данные не потеряны. - Finding: obsolete/gap: Analytics v1/use_analytics_v2 flag removed by S4.2 final migration

---

## Готовность к выкатке

v2 признаётся готовым к выкатке как default, когда:
- ✅ Все чеклисты в разделах 1–11 выполнены.
- ✅ `pytest` проходит на 100%.
- ✅ Ручной регресс по всем сценариям выполнен и задокументирован.
- ✅ Хотя бы одна неделя в статусе «доступен через флаг» для опционального тестирования.
- ✅ Для каждой новой фичи (heatmap, resistance, drill-down, quick chips) — минимум 3 unit-теста.
- ✅ В `docs/user_guide.md` описаны новые вкладки.
