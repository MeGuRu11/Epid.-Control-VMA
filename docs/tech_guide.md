# Техническое руководство Epid Control

## 1. Назначение документа

Этот документ нужен разработчику, тестировщику и сопровождающему инженеру. Он описывает текущую архитектуру, модули, конфигурацию, БД, ключевые сервисы и правила сопровождения.

## 2. Технологический стек

| Область | Технология |
|---------|------------|
| Язык | Python 3.11+ |
| UI | PySide6 (виджеты) |
| Архитектура | Clean Architecture / DDD |
| ORM | SQLAlchemy 2 |
| База данных | SQLite |
| Миграции | Alembic |
| Линтер | ruff |
| Типизация | mypy |
| Тесты | pytest |
| Сборка | PyInstaller |

## 3. Архитектура и зависимости слоёв

Приложение организовано по слоям:

- `app/ui` — PySide6-виджеты, окна, диалоги, модели представления;
- `app/application` — сервисы приложения, DTO, проверки прав, оркестрация use-case;
- `app/domain` — предметные модели, правила, перечисления, типы;
- `app/infrastructure` — SQLAlchemy-модели, миграции, репозитории, экспорт, отчёты, файловые операции.

Разрешённые зависимости:

- `UI -> Application`
- `Application -> Domain`
- `Application -> Infrastructure`
- `Infrastructure -> Domain`

Запрещённые зависимости:

- `UI -> Infrastructure`
- `UI -> SQLAlchemy`
- `Domain -> UI / Application / Infrastructure`
- `Domain -> PySide6 / SQLAlchemy`
- `Application -> UI`

Эти ограничения дополнительно проверяются скриптом `scripts/check_architecture.py`.

## 4. Точка входа и последовательность запуска

Основная точка входа:

```powershell
python -m app.main
```

Типовая последовательность старта:

1. загрузка конфигурации из `app/config.py`;
2. подготовка каталогов данных, логов и артефактов;
3. инициализация БД и применение миграций;
4. seed базовых справочников и системных сущностей;
5. запуск `QApplication` и темы интерфейса;
6. окно первого запуска при пустой БД;
7. окно логина;
8. создание `MainWindow` после успешной аутентификации.

Дополнительно при старте:

- начальная геометрия `MainWindow` применяется отложенно после `show()`, а не до показа окна;
- экран для стартовой геометрии выбирается через `windowHandle().screen()` с fallback на экран под курсором и `primaryScreen()`;
- размер стартового окна ограничивается рамками `availableGeometry()`, чтобы избежать предупреждений `QWindowsWindow::setGeometry` на multi-monitor Windows-конфигурациях.

## 5. Конфигурация и каталоги данных

Ключевые переменные окружения:

- `EPIDCONTROL_DATA_DIR` — корневой каталог данных;
- `EPIDCONTROL_DB_FILE` — имя SQLite-файла;
- `DATABASE_URL` — override строки подключения;
- `EPIDCONTROL_UI_PREMIUM` — режим визуального слоя;
- `EPIDCONTROL_UI_ANIMATION` — режим анимаций;
- `EPIDCONTROL_UI_DENSITY` — плотность интерфейса.

Структура каталогов данных обычно включает:

- каталог базы данных;
- каталог логов;
- каталог артефактов отчётов;
- каталог импортов и экспортов;
- каталог резервных копий.

Все пути должны формироваться через `app/config.py`, а не хардкодиться в UI или сервисах.

## 6. Карта UI-модулей

### 6.1 Главное окно

`app/ui/main_window.py`

Отвечает за:

- верхнюю навигацию между разделами;
- инициализацию разделов;
- общий контекст пользователя;
- выход из системы;
- контроль session timeout;
- передачу текущей сессии в дочерние представления.

### 6.2 Контекстная панель пациента

`app/ui/widgets/context_bar.py`

Функции:

- поиск пациента по ФИО или ID;
- выбор госпитализации;
- хранение текущего patient/case context;
- быстрые переходы в `ЭМЗ`, `Лаб`, `Ф100`, `Санитарию`, `Аналитику`.

### 6.3 Основные представления

- `app/ui/home/home_view.py` — главная сводка.
- `app/ui/patient/patient_emk_view.py` — поиск и карточка пациента.
- `app/ui/emz/emz_form.py` — форма ЭМЗ и госпитализации.
- `app/ui/lab/lab_samples_view.py` — основной экран лаборатории: hero-контекст пациента/госпитализации, KPI-сводка, selector-card, filter-card и карточная рабочая лента проб.
- `app/ui/lab/lab_sample_detail.py` — карточка лабораторной пробы.
- `app/ui/sanitary/sanitary_dashboard.py` — основной экран санитарии: hero-контекст по отделениям, KPI по текущей выборке, filter-card и карточный список отделений.
- `app/ui/sanitary/sanitary_history.py` — диалог истории санитарных проб с summary-блоком, responsive-фильтрами, карточным списком и доступом к карточке санитарной пробы.
- `app/ui/analytics/analytics_view.py` — поиск, графики, отчёты, история артефактов.
- `app/ui/form100_v2/form100_view.py` — список карточек `Form100 V2`.
- `app/ui/form100_v2/form100_editor.py` — редактор карточки `Form100 V2`.
- `app/ui/import_export/import_export_view.py` — история обмена.
- `app/ui/import_export/import_export_wizard.py` — мастер импорта/экспорта.
- `app/ui/references/reference_view.py` — справочники.
- `app/ui/admin/user_admin_view.py` — пользователи, аудит, резервные копии.

### 6.4 Вспомогательные диалоги

- `app/ui/login_dialog.py` — аутентификация пользователя;
- `app/ui/first_run_dialog.py` — создание первого администратора;
- `app/ui/patient/patient_edit_dialog.py` — редактирование пациента;
- `app/ui/widgets/case_search_dialog.py` — выбор случая/госпитализации.

## 7. Карта application-сервисов

Ключевые сервисы приложения:

- `AuthService` — вход, блокировки, сброс счётчиков неудачных попыток, контекст сессии;
- `SetupService` — создание первого пользователя и первичная инициализация;
- `UserAdminService` — создание пользователей, смена статуса, сброс пароля;
- `PatientService` — создание, поиск, обновление и удаление пациентов;
- `EmzService` — госпитализации и ЭМЗ;
- `LabService` — лабораторные пробы;
- `SanitaryService` — санитарные пробы;
- `Form100ServiceV2` — жизненный цикл карточки `Form100 V2`;
- `AnalyticsService` — аналитические выборки и агрегаты;
- `DashboardService` — данные для главной панели и summary-экранов;
- `ReferenceService` — CRUD справочников;
- `ExchangeService` — импорт и экспорт данных;
- `BackupService` — резервные копии;
- `ReportingService` — генерация XLSX/PDF и история запусков;
- `SavedFilterService` — пользовательские сохранённые фильтры.

Общее правило: UI вызывает только application-сервис. Любая запись в БД проходит через сервис, проверку прав и аудит.

## 8. Безопасность и права доступа

Обязательные проектные правила:

- пароли только через `argon2`/`bcrypt`;
- каждая мутирующая операция должна знать `actor_id`;
- каждая мутирующая операция должна проверять права;
- аудит не должен хранить лишние персональные данные;
- DML-запросы не должны использовать string interpolation;
- UI не должен напрямую ловить инфраструктурные исключения SQLAlchemy, только application-исключения;
- файловые артефакты должны открываться только после проверки допустимого пути.

Роли минимум:

- `admin` — полный доступ;
- `operator` — рабочие разделы без административных прав.

## 9. База данных и Alembic

### 9.1 Миграции

Миграции находятся в `app/infrastructure/db/migrations`.

Полезные команды:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
python -m alembic check
```

Для локального `alembic check` нужно задавать каталог данных, например:

```powershell
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
python -m alembic upgrade head
python -m alembic check
```

### 9.2 Модели и ORM

Текущие требования проекта:

- SQLAlchemy 2-стиль;
- явные `relationship(..., back_populates=...)`;
- `ForeignKey(..., ondelete=...)` на важных связях;
- доступ к БД через `session_scope()` или внедрённую session factory;
- `SQLite` остаётся основной рабочей базой и средой тестов.

### 9.3 FTS

Полнотекстовый поиск обслуживается FTS-менеджером. FTS-таблицы исключаются из normal `alembic check`, так как создаются отдельно и не должны восприниматься как schema drift.

## 10. Отчёты, импорт/экспорт и артефакты

Основные инфраструктурные направления:

- `reporting` — генерация `XLSX`, `PDF`, `Form100 PDF`;
- `exchange` — экспорт и импорт пакетов;
- `backup` — создание резервных копий;
- `artifacts` — история артефактов, контроль `SHA256`, повторное открытие файла.

Замечания:

- экспортные и backup-файлы содержат чувствительные данные;
- в интерфейсе должны показываться предупреждения о безопасном хранении;
- пути к артефактам проходят валидацию перед открытием.

## 11. Тестовая стратегия

Структура тестов:

- `tests/unit` — юнит- и компонентные тесты;
- `tests/integration` — интеграционные сценарии на реальной SQLite;
- `tests/conftest.py` — общие фикстуры;
- `tests/integration/test_full_system.py` — сквозные функциональные сценарии сервисов.

Проектные правила тестирования:

- не мокать SQLAlchemy, если можно использовать реальную SQLite;
- каждый тест изолирован;
- файловые сценарии писать через `tmp_path`;
- UI-тесты по возможности запускать на реальных виджетах, а не на моках.

## 12. Quality gates и CI

Локальный единый прогон:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Что проверяется:

1. `ruff check app tests`
2. `python scripts/check_architecture.py`
3. `mypy app tests`
4. `pytest -q`
5. `python -m compileall -q app tests scripts`
6. `python -m alembic upgrade head`
7. `python -m alembic check`
8. поиск mojibake по проекту

CI-файл:

- `.github/workflows/quality-gates.yml`

Важно: локальный сценарий и CI должны оставаться синхронизированными.

## 13. Сборка

Сборка приложения выполняется через `PyInstaller`. Основной файл конфигурации:

- `EpidControl.spec`

Перед сборкой нужно:

- прогнать quality gates;
- убедиться, что миграции синхронизированы;
- проверить сценарии из `docs/manual_regression_scenarios.md`;
- убедиться, что ресурсы, шаблоны и изображения bodymap включены в сборку.

## 14. Документация проекта

Ключевые документы:

- `README.md` — быстрый вход и карта проекта;
- `docs/user_guide.md` — подробная инструкция для конечного пользователя;
- `docs/context.md` — состояние проекта и roadmap;
- `docs/progress_report.md` — журнал изменений;
- `docs/session_handoff.md` — передача контекста между сессиями;
- `docs/build_release.md` — сборка и релиз;
- `docs/manual_regression_scenarios.md` — ручная регрессия.

## 15. Чек-лист после изменений UI или документации

После любого значимого изменения:

1. проверьте, что новый экран или кнопка отражены в `docs/user_guide.md`;
2. проверьте, что `README.md` не противоречит текущей навигации и quality gates;
3. при изменении архитектурного поведения обновите `docs/tech_guide.md`;
4. добавьте запись в `docs/progress_report.md`;
5. обновите `docs/session_handoff.md` перед завершением сессии.
