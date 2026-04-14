# Epid Control

`Epid Control` — настольное приложение для эпидемиологического контроля, ведения ЭМЗ, лабораторных и санитарных проб, аналитики, отчётности и безопасного обмена данными.

## Что делает система

- запускается в режиме первого старта и создаёт первого администратора;
- аутентифицирует пользователей по ролям `admin` и `operator`;
- ведёт карточки пациентов и госпитализаций в ЭМЗ;
- хранит лабораторные пробы с ростом, идентификацией, антибиотикограммой и фагами;
- ведёт санитарные пробы по отделениям;
- строит аналитику, отчёты, графики и историю запусков отчётов;
- поддерживает `Form100 V2`: создание, сохранение, подписание, архивирование, экспорт `PDF/ZIP`, импорт `ZIP`;
- выполняет импорт и экспорт данных через мастер обмена;
- управляет справочниками, пользователями, аудитом и резервными копиями.

## Стек

- `Python 3.11+` (`3.12` рекомендуется)
- `PySide6` (виджеты, без `QML`)
- `SQLAlchemy 2`
- `SQLite`
- `Alembic`
- `ruff`
- `mypy`
- `pytest`
- `PyInstaller`

## Быстрый старт

### 1. Подготовка окружения

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Настройка путей данных

Основные переменные окружения:

- `EPIDCONTROL_DATA_DIR` — корневой каталог данных приложения;
- `EPIDCONTROL_DB_FILE` — имя файла SQLite внутри каталога данных;
- `DATABASE_URL` — полный URL подключения, если нужен явный override;
- `EPIDCONTROL_UI_PREMIUM` — расширенный UI (`1` или `0`);
- `EPIDCONTROL_UI_ANIMATION` — режим анимаций: `adaptive`, `full`, `minimal`;
- `EPIDCONTROL_UI_DENSITY` — плотность интерфейса: `normal`, `compact`.

Пример:

```powershell
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
$env:EPIDCONTROL_DB_FILE = "epid-control.db"
```

### 3. Запуск приложения

```powershell
python -m app.main
```

Если это чистая база, приложение откроет окно первого запуска и предложит создать администратора.

## Разделы интерфейса

Основные разделы верхней навигации:

- `Главная` — сводные показатели и состояние системы.
- `ЭМЗ` — создание и ведение госпитализаций, диагнозов, антибиотиков, ИСМП.
- `Поиск и ЭМК` — поиск пациентов, просмотр карточки и госпитализаций.
- `Лаборатория` — список лабораторных проб пациента и карточка пробы.
- `Санитария` — отделения, санитарные пробы и история по отделению.
- `Аналитика` — фильтры, сводка, графики, история отчётов, экспорт отчётов.
- `Импорт/Экспорт` — история обмена и мастер импорта/экспорта.
- `Справочники` — управление отделениями, материалами, антибиотиками, микроорганизмами и другими каталогами.
- `Администрирование` — пользователи, аудит, резервные копии.

Под верхней навигацией находится контекстная панель пациента. Она позволяет:

- закрепить пациента по ФИО или ID;
- выбрать госпитализацию по номеру истории болезни или ID;
- быстро перейти в `ЭМЗ`, `Лаб`, `Ф100`, `Санитарию`, `Аналитику` для текущего контекста;
- сбросить текущий контекст.

## Роли и доступ

- `admin` — полный доступ ко всем разделам, включая справочники, администрирование, импорт/экспорт, резервные копии.
- `operator` — рабочие разделы без административных функций. Недоступные разделы скрываются или блокируются.

## Документация

- [Подробное руководство пользователя](docs/user_guide.md)
- [Техническое руководство](docs/tech_guide.md)
- [Контекст проекта и roadmap](docs/context.md)
- [Журнал прогресса](docs/progress_report.md)
- [Контекст последней сессии](docs/session_handoff.md)
- [Сценарии ручной регрессии](docs/manual_regression_scenarios.md)
- [Сборка и релиз](docs/build_release.md)

## Локальные quality gates

Полный локальный прогон:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

Скрипт проверяет:

1. `ruff check app tests`
2. `python scripts/check_architecture.py`
3. `mypy app tests`
4. `pytest -q`
5. `python -m compileall -q app tests scripts`
6. `python -m alembic upgrade head`
7. `python -m alembic check`
8. проверку на mojibake в `app/`, `docs/`, `scripts/`, `tests/`

Если нужен ручной запуск по шагам:

```powershell
ruff check app tests
python scripts/check_architecture.py
mypy app tests
pytest -q
python -m compileall -q app tests scripts
$env:EPIDCONTROL_DATA_DIR = "$PWD\tmp_run\epid-data"
python -m alembic upgrade head
python -m alembic check
```

## Полезные команды

```powershell
python -m app.main
pytest -q
pytest --cov=app -q
ruff check app tests
ruff check --fix app tests
mypy app tests
python -m compileall -q app tests scripts
python scripts/check_architecture.py
python scripts/seed_references.py
python -m alembic upgrade head
python -m alembic current
python -m alembic heads
```

## Структура репозитория

```text
app/
  application/      Сервисы приложения, DTO, безопасность, use-cases
  domain/           Бизнес-правила, модели предметной области, типы
  infrastructure/   SQLAlchemy, миграции, отчёты, импорт/экспорт, FTS
  ui/               PySide6-виджеты, окна, диалоги, модели представления
  main.py           Точка входа приложения

docs/
  context.md                Контекст проекта и roadmap
  progress_report.md        Журнал изменений
  session_handoff.md        Контекст между сессиями
  user_guide.md             Руководство пользователя
  tech_guide.md             Техническое руководство
  manual_regression_*.md    Сценарии ручной проверки
  build_release.md          Сборка и релиз

scripts/
  quality_gates.ps1         Единый quality gate
  check_architecture.py     Проверка архитектурных ограничений
  seed_references.py        Инициализация справочников
```

## Что читать дальше

- Для повседневной работы в системе — `docs/user_guide.md`.
- Для доработок, отладки и сопровождения — `docs/tech_guide.md`.
- Для понимания текущего статуса проекта — `docs/context.md` и `docs/progress_report.md`.
