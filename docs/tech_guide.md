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
- `EPIDCONTROL_FORM100_V2_ENABLED` — переключение Form100 V2.

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
