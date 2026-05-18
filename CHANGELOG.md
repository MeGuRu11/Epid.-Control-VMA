# Changelog

Все значимые изменения проекта фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

## [1.1.0] — 2026-05-18

### Added

- **Analytics v2**: полностью переработан раздел `Аналитика`.
  5 вкладок: `Обзор`, `Микробиология`, `ИСМП`, `Поиск`, `Отчёты`.
  KPI-карточки, sparklines, trend chart, heatmap, resistance grid,
  donut chart, bar отделений, inline empty states.
- **Exit Confirmation**: диалог подтверждения при закрытии окна
  (`✗` / `Alt+F4`). Авто-logout без подтверждения.
- **Formatters**: единый слой форматирования дат, булевых,
  enum-значений для PDF/XLSX/UI (`formatters.py`).
- **IdResolver**: резолвер FK→имя с кешем для CSV/PDF экспорта.
- **Bodymap**: маппинг координат на анатомические зоны Form100.
- **Seed-скрипт**: `scripts/seed_demo_data.py` для тестовых данных.

### Fixed

- Form100 PDF: экспорт больше не повышает `version` карточки.
- Form100 PDF: корректная верстка bodymap, KeepTogether секций,
  footer `Ревизия`, блок EMR-контекст.
- Form100: diff-баннер при расхождении данных с ЭМЗ.
- Analytics PDF/XLSX: блок ИСМП-показателей.
- CSV/PDF: локализованные заголовки колонок,
  резолвинг ID через IdResolver.
- JSON-экспорт: ISO-даты с timezone вместо naive datetime.
- Layout: главное окно открывается maximized без визуальных артефактов.
- TransitionStack: `sizeHint` только для текущей страницы.
- Sanitary: карточки отделений не пропадают.
- Диалоги Exit/Logout: центрируются относительно родительского окна.
- Analytics v2: `HomeView` и `AnalyticsViewV2` не растягиваются
  после первого maximized-показа и переключения вкладок.
- Analytics v2: KPI без sparkline не показывают лишний красный индикатор,
  inline placeholders не обрезают текст.
- Seed-скрипт: demo-данные распределяются по пациентам и отделениям,
  а `--clear` удаляет только demo-строки.

### Changed

- Analytics: v1 (`AnalyticsSearchView`) удалён; v2 является
  единственным интерфейсом.
- Окно по умолчанию открывается в развёрнутом (maximized) режиме.

## [2026-04-27] — Model Update

- Обновлена модель Codex агента: GPT-5.5 (вышел 2026-04-23)
  заменяет GPT-5.4 для Stage 5–9 (frontend: Auth, Editor, Player, Dashboards, Admin)
- GPT-5.5 доступен в Codex для Plus/Pro/Business/Enterprise
- `gpt-5.4` оставлен только как временный fallback, если `gpt-5.5` ещё недоступен
  в конкретном аккаунте, Codex CLI, IDE extension или model picker
