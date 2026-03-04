# Техническое руководство

## 1. Архитектура
- Стек: Python 3.11+, PySide6, SQLAlchemy 2.x, Alembic, SQLite.
- Слои:
  - `app/ui` — представление и UX-логика.
  - `app/application` — use-cases и сервисы.
  - `app/domain` — правила, модели предметной области.
  - `app/infrastructure` — БД, репозитории, импорт/экспорт, отчеты.

## 2. Запуск приложения
- Точка входа: `python -m app.main`.
- Последовательность старта:
  1. Логирование.
  2. Инициализация Qt и темы.
  3. Миграции БД (`initialize_database` в `app/bootstrap/startup.py`).
  4. Проверка пользователей и first-run сценарий.
  5. Авторизация и запуск `MainWindow`.

## 3. Конфигурация
Основные переменные окружения:
- `DATABASE_URL` — URL БД (переопределяет путь по умолчанию).
- `EPIDCONTROL_DATA_DIR` — корневой каталог данных.
- `EPIDCONTROL_DB_FILE` — путь к sqlite-файлу.
- `EPIDCONTROL_UI_PREMIUM` — premium UI слой (`1/0`).
- `EPIDCONTROL_UI_ANIMATION` — `adaptive|full|minimal`.
- `EPIDCONTROL_UI_DENSITY` — `normal|compact`.

## 4. База данных и миграции
- Миграции хранятся в `app/infrastructure/db/migrations`.
- Применение миграций:
  - `alembic upgrade head`
- Для диагностики:
  - `alembic current`
  - `alembic heads`

## 5. Quality Gates
Единый локальный прогон:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Что проверяется:
- `ruff check app tests`
- `mypy app tests`
- `pytest -q`
- `python -m compileall -q app tests scripts`

CI-пайплайн:
- `.github/workflows/quality-gates.yml`

## 6. Тестирование
- Unit tests: `tests/unit`
- Integration tests: `tests/integration`
- Рекомендуемый минимум перед merge:
  - полный quality-gates прогон;
  - ручная проверка критичных сценариев из `docs/manual_regression_scenarios.md`.

## 7. Логи и диагностика
- Логи приложения: каталог `LOG_DIR` из `app/config.py`.
- При ошибках миграций создается `migration_error.log`.
- Все критические ошибки должны иметь:
  - понятное сообщение пользователю;
  - запись в лог для диагностики.

## 8. Form100 V2: PDF и Bodymap
- Генератор PDF: `app/infrastructure/reporting/form100_pdf_report_v2.py`.
- Формат отчета: структурированный `A4` PDF с таблицами полей.
- Bodymap в PDF:
  - основной путь: шаблон `app/image/main/form_100_bd.png` + нанесение аннотаций;
  - fallback: векторная схема, если шаблон недоступен.
- Интеграция экспорта:
  - `app/application/services/form100_service_v2.py::export_pdf`;
  - `app/application/services/reporting_service.py::export_form100_pdf`.
- Тесты экспорта PDF:
  - `tests/unit/test_form100_pdf_report_v2.py`;
  - `tests/integration/test_form100_v2_service.py::test_form100_v2_exchange_and_reporting`.
