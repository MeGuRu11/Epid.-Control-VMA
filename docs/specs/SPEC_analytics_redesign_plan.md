# Финальный план: редизайн раздела «Аналитика»

**Дата утверждения:** 2026-05-09
**Статус:** Утверждено пользователем, готово к передаче Codex.

**Связанные документы:**
- `docs/specs/SPEC_analytics_redesign.md` — regression-сценарии (130+ чек-боксов).
- `docs/ANALYTICS_REDESIGN_PLAN.md` — расширенный план с анализом и обоснованиями.

---

## 1. Утверждённые решения

| № | Вопрос | Решение |
|---|--------|---------|
| 1 | Структура страницы | 5 вкладок + sticky filter-bar |
| 2 | Стартовая вкладка | «Обзор» |
| 3 | Стратегия миграции | Флаг фичи `use_analytics_v2` в UserPreferences (default = false на этапах 1–7, true на этапе 8) |
| 4 | Resistance pattern | Реализуем (клиническая ценность для микробиологии) |
| 5 | Heatmap «Отделения × Микро» | Реализуем |
| 6 | Sparklines в KPI | Реализуем (этап 3) |
| 7 | Дизайн KPI-карточки | Гибрид B+C, иконка 40×40 px (раздел 3) |
| 8 | Regression сценарии | Зафиксированы в `SPEC_analytics_redesign.md` |

---

## 2. Целевая структура страницы

```
┌──────────────────────────────────────────────────────────┐
│  Аналитика                              [Обновить]       │  ← Заголовок
├──────────────────────────────────────────────────────────┤
│  Период: [01.05 — 31.05]  [Месяц ▾]                      │  ← Sticky filter-bar
│  Пациенты: [Все ▾]    [Расширенный фильтр ▾]             │    (общий для всех вкладок)
├──────────────────────────────────────────────────────────┤
│  [Обзор] [Микробиология] [ИСМП] [Поиск] [Отчёты]         │  ← Tabs
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Содержимое выбранной вкладки                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Содержимое вкладок

| Вкладка | Состав |
|---------|--------|
| Обзор (default) | 4 KPI-карточки, главный TrendChart, топ-3 проблемных отделений |
| Микробиология | TopMicrobesChart, ResistanceGrid, Heatmap отделений × микро, Quick filter chips |
| ИСМП | 5 KPI-карточек, динамика инцидентности, DonutChart типов, Bar отделений |
| Поиск | Расширенные фильтры, сохранённые пресеты, таблица результатов, экспорт XLSX/PDF |
| Отчёты | История отчётов с фильтрами, действия (открыть, сохранить как, проверить хеш) |

---

## 3. Утверждённый дизайн KPI-карточки

### Параметры

| Параметр | Значение |
|----------|----------|
| Padding | `14px` |
| Фон | `rgba(255, 253, 248, 0.95)` |
| Граница | `1px solid #EDE4D8` |
| Скругление | `border-radius: 14px` |
| Hover-граница | `1px solid #6FB9AD` (намёк на drill-down) |
| Иконка-плашка | **40 × 40 px**, `border-radius: 10px` |
| Размер шрифта иконки | `20px` (Tabler Icons) |
| Шрифт значения | `22px`, `font-weight: 500`, `tabular-nums`, `letter-spacing: -0.3px` |
| Шрифт тренда | `12px`, `font-weight: 500` |
| Шрифт заголовка | `11px`, uppercase, `letter-spacing: 0.4px`, цвет `#888780` |
| Gap иконка ↔ body | `12px` |
| Gap внутри body | `6px` |

### Layout

```
┌──────────────────────────────────────┐
│  [40x40]   ЗАГОЛОВОК                 │
│            234         ▲ 12%         │
└──────────────────────────────────────┘
```

Иконка слева — цветная плашка категории. Body справа: заголовок сверху, ниже — значение слева и тренд справа в одной строке.

### Цветовая семантика плашек

| Категория | Background | Foreground |
|-----------|-----------|------------|
| Госпитализации, обследования (нейтральная статистика) | `#E1F5EE` | `#0F6E56` |
| ИСМП и негативные исходы | `#FCEBEB` | `#A32D2D` |
| Лабораторные пробы, материалы | `#FAEEDA` | `#854F0B` |
| Расчётные показатели (доля, превалентность) | `#EEEDFE` | `#3C3489` |

### Семантика тренда

- `▲` зелёный (`#2E7D32`) — рост позитивной или нейтральной метрики.
- `▼` красный (`#C62828`) — рост негативной метрики (ИСМП, превалентность).
- `—` серый (`#888780`) — без изменений или нет данных за прошлый период.

Цвет определяется в виджете `KpiCard` на основе параметра `metric_kind: "positive" | "negative" | "neutral"`. Не зашит в данные.

### Защита от длинных значений

- `min-width: 0` на `.body` и `.value` — без этого grid-cell распирается длинным значением.
- `white-space: nowrap` + `text-overflow: ellipsis` на значении.
- `tabular-nums` — цифры одинаковой ширины, столбец из карточек выровнен по вертикали.
- На пустых данных тренд деградирует до `—`, карточка не «прыгает» в высоту.

---

## 4. Архитектура файлов

### Целевая структура модуля

```
app/ui/analytics/
├── analytics_view.py                ← каркас, держит фильтры и табы (~250 строк)
├── filter_bar.py                    ← sticky-header с глобальными фильтрами
├── controller.py                    ← фасад между UI и сервисами
├── chart_data.py                    ← без изменений
├── charts.py                        ← TrendChart, TopMicrobesChart (общая база)
├── view_utils.py                    ← без изменений
├── report_history_helpers.py        ← без изменений
├── tabs/
│   ├── __init__.py
│   ├── overview_tab.py              ← KPI, главный тренд, топ-3 отделений
│   ├── microbiology_tab.py          ← топ-микро, resistance, heatmap, quick chips
│   ├── ismp_tab.py                  ← KPI ИСМП, графики, таблицы
│   ├── search_tab.py                ← фильтры, saved, результаты, экспорт
│   └── reports_tab.py               ← история отчётов
└── widgets/
    ├── __init__.py
    ├── kpi_card.py                  ← KpiCard(title, value, trend, metric_kind, sparkline?)
    ├── trend_indicator.py           ← ▲▼— с цветом по metric_kind
    ├── sparkline.py                 ← мини-trend (этап 3)
    ├── heatmap.py                   ← Heatmap-визуализация (этап 4)
    ├── donut_chart.py               ← DonutChart с легендой (этап 5)
    ├── resistance_grid.py           ← ResistanceGrid с RIS-цветовым кодом (этап 4)
    ├── quick_filter_chips.py        ← chips (этап 4)
    └── empty_state.py               ← плашка «нет данных» (этап 7)
```

### Принципы

- `controller.py` — единственная точка вызова сервисов. Вкладки получают данные через него.
- UI не импортирует `app.infrastructure.*`.
- `AnalyticsService`, `ReportingService`, DTO — без изменений. Все новые фичи строятся на существующих публичных методах.
- БД-схема не меняется.
- Старая страница (`AnalyticsSearchView`) работает до этапа 8 — переключение по флагу.

### Стили

В `theme.py` добавляются objectName-стили:
- `QFrame#kpiCard` (с hover-эффектом)
- `QLabel#kpiValue`, `QLabel#kpiTitle`
- `QLabel#kpiTrendUp`, `QLabel#kpiTrendDown`, `QLabel#kpiTrendFlat`
- `QFrame#filterBar` (sticky header)
- `QFrame#sectionFrame`, `QLabel#sectionTitle` (замена `QGroupBox`)
- `QTabBar::tab` и `QTabBar::tab:selected`
- `QFrame#emptyState`

Все `QGroupBox` в аналитике заменяются на `QFrame#sectionFrame` + `QLabel#sectionTitle`.

---

## 5. Этапы работ

> Принцип: каждый этап — самостоятельный коммит. После каждого — `ruff` + `mypy` + `pytest` зелёные. Старая страница работает параллельно до этапа 8.

### Этап 0 — Подготовка

| Шаг | Действие |
|-----|----------|
| 0.1 | Положить в `docs/specs/` файл `SPEC_analytics_redesign.md` (regression-сценарии) |
| 0.2 | Положить в `docs/specs/` файл `SPEC_analytics_redesign_design.md` (этот документ как часть 3) |
| 0.3 | Добавить `use_analytics_v2: bool = False` в `UserPreferences` DTO + миграция |
| 0.4 | Записать в `docs/progress_report.md` начало работ |

**Коммит:** `chore: add analytics v2 feature flag and design specs`

### Этап 1 — Foundation

| Шаг | Действие |
|-----|----------|
| 1.1 | Создать `analytics_view.py` v2 (новый класс `AnalyticsViewV2`) рядом со старым |
| 1.2 | Реализовать `filter_bar.py` — sticky-header с глобальными фильтрами |
| 1.3 | Реализовать `controller.py` — фасад над сервисами |
| 1.4 | Создать пустые `tabs/{overview,microbiology,ismp,search,reports}_tab.py` |
| 1.5 | Перенести существующий функционал в соответствующие вкладки **без визуальных изменений** |
| 1.6 | Подключить `AnalyticsViewV2` в `main_window` за флагом `use_analytics_v2` |
| 1.7 | Регрессионные тесты по чек-листу `SPEC_analytics_redesign.md` разделы 1, 3 |

**Коммит:** `refactor: extract analytics view into tabs (v2 behind feature flag)`

### Этап 2 — KPI-cards и Overview

| Шаг | Действие |
|-----|----------|
| 2.1 | Виджет `widgets/kpi_card.py` (без sparkline) |
| 2.2 | Виджет `widgets/trend_indicator.py` |
| 2.3 | Расчёт изменений в `controller.py` через `AnalyticsService.compare_periods` |
| 2.4 | Реализация вкладки `overview_tab.py`: 4 KPI-карточки, TrendChart, топ-3 отделений |
| 2.5 | Стили для `#kpiCard`, `#kpiValue`, `#kpiTitle`, `#kpiTrend*` в `theme.py` |
| 2.6 | Тесты: рендер KPI с разными значениями, hover, кликабельность |

**Коммит:** `feat: analytics overview tab with KPI cards and trend indicators`

### Этап 3 — Sparklines и drill-down

| Шаг | Действие |
|-----|----------|
| 3.1 | Виджет `widgets/sparkline.py` |
| 3.2 | Подключить sparkline к KPI-карточкам (опциональный параметр) |
| 3.3 | Drill-down: клик по KPI → переключение на соответствующую вкладку с сохранением фильтров |
| 3.4 | Тесты: drill-down переключает табы и сохраняет фильтр |

**Коммит:** `feat: KPI cards sparklines and drill-down navigation`

### Этап 4 — Микробиология

| Шаг | Действие |
|-----|----------|
| 4.1 | Виджет `widgets/heatmap.py` (отделения × микроорганизмы) |
| 4.2 | Виджет `widgets/resistance_grid.py` (RIS-цветовое кодирование) |
| 4.3 | Виджет `widgets/quick_filter_chips.py` |
| 4.4 | Реализация вкладки `microbiology_tab.py` |
| 4.5 | Тесты по `SPEC_analytics_redesign.md` раздел 2.5, 2.6, 3.3 |

**Коммит:** `feat: microbiology tab with heatmap, resistance pattern and quick filter chips`

### Этап 5 — ИСМП и графики

| Шаг | Действие |
|-----|----------|
| 5.1 | Виджет `widgets/donut_chart.py` |
| 5.2 | Реализация вкладки `ismp_tab.py`: 5 KPI, динамика, donut типов, bar отделений |
| 5.3 | Виджет `widgets/empty_state.py` (для пустого периода) |
| 5.4 | Тесты по `SPEC_analytics_redesign.md` раздел 2.4 |

**Коммит:** `feat: ismp tab redesign with donut and trend charts`

### Этап 6 — Поиск и отчёты

| Шаг | Действие |
|-----|----------|
| 6.1 | Реализация вкладки `search_tab.py`: расширенные фильтры, saved, результаты, экспорт |
| 6.2 | Реализация вкладки `reports_tab.py`: история отчётов, действия |
| 6.3 | Color-coded badges в результатах (положительные / отрицательные пробы) |
| 6.4 | Тесты по `SPEC_analytics_redesign.md` разделы 1.3, 3, 4, 5 |

**Коммит:** `feat: search and reports tabs with color-coded badges`

### Этап 7 — Стиль и полировка

| Шаг | Действие |
|-----|----------|
| 7.1 | Замена всех `QGroupBox` в аналитике на `QFrame#sectionFrame` |
| 7.2 | Применение всех стилей из раздела 4 этого документа в `theme.py` |
| 7.3 | Empty states на всех вкладках (вместо пустых таблиц) |
| 7.4 | Loading-индикаторы вместо модальных диалогов на ошибках |
| 7.5 | Адаптивность: KPI в 2 ряда на узких экранах, tabs со скроллом |
| 7.6 | Тесты по `SPEC_analytics_redesign.md` разделы 7, 8 |

**Коммит:** `feat: analytics v2 styling polish with empty states and adaptive layout`

### Этап 8 — Удаление v1 и финал

| Шаг | Действие |
|-----|----------|
| 8.1 | Прогон ручного регресс-теста по всем разделам `SPEC_analytics_redesign.md` |
| 8.2 | Перевести `use_analytics_v2 = True` в default UserPreferences |
| 8.3 | Удалить `AnalyticsSearchView` (старый класс) и связанные тесты |
| 8.4 | Удалить флаг `use_analytics_v2` |
| 8.5 | Обновить `docs/user_guide.md` — описание новых вкладок |

**Коммит:** `chore: remove analytics v1, make v2 default`

---

## 6. Жёсткие правила (для Codex)

```
Не удалять существующие тесты.
Не skip-ать тесты.
Не использовать # type: ignore без комментария-обоснования.
Не менять схему БД без Alembic-миграции.
Не переносить бизнес-логику в UI.
UI не импортирует app.infrastructure.*.
Не изменять публичные сигнатуры AnalyticsService и ReportingService.
Все вызовы сервисов из вкладок идут через controller.py.
QMessageBox используется только для критических ошибок и подтверждений.
Для нефатальных ошибок — inline-плашка в верху страницы.
Для каждой новой фичи — минимум 3 unit-теста.
Не использовать эмодзи в UI.
```

---

## 7. Quality gates после каждого этапа

```powershell
ruff check app tests
python -m mypy app tests
python -m pytest -q
python -m compileall -q app tests scripts
```

После миграционных изменений (этап 0):

```powershell
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
python -m alembic upgrade head
python -m alembic check
```

Запись в `docs/progress_report.md` после каждого закрытого этапа.

---

## 8. Готовность к выкатке (acceptance)

v2 признаётся готовым к выкатке как default, когда:

- Все чек-боксы в `SPEC_analytics_redesign.md` (разделы 1–11) выполнены.
- `pytest` проходит на 100%.
- `analytics_view.py` сократился с 1593 до ≤ 300 строк.
- Каждая вкладка ≤ 400 строк.
- Стиль соответствует системе (бежевая палитра, скругления, чипы, без `QGroupBox`).
- Минимум одна неделя в статусе «доступен через флаг» для опционального тестирования.

---

## 9. Что хранить в репозитории

После утверждения положить в репозиторий:

| Файл | Что |
|------|-----|
| `docs/specs/SPEC_analytics_redesign.md` | Regression-сценарии (130+ чек-боксов) |
| `docs/specs/SPEC_analytics_redesign_plan.md` | Этот документ |

Положить через коммит:
```
git add docs/specs/SPEC_analytics_redesign.md docs/specs/SPEC_analytics_redesign_plan.md
git commit -m "docs: analytics redesign — final plan and regression scenarios"
```

---

## Резюме

Текущий раздел аналитики — длинная вертикальная простыня с дублирующимися метриками и устаревшим стилем `QGroupBox`. Цель — разбить на 5 функциональных вкладок с глобальными sticky-фильтрами, добавить KPI-cards с тренд-индикаторами как главный экран, привести стили к системе, добавить три новые аналитические фичи (heatmap, resistance pattern, drill-down) и три UX-улучшения (sparklines, quick filter chips, color-coded badges).

Работа разбивается на 8 этапов общим объёмом ~5–6 спринтов с флагом фичи для безопасного перехода. Сервисы и БД не затрагиваются.

Готово к передаче Codex.
