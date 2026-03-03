# Epid Control - AI Assistant Rules & Project Guidelines

Это файл с базовыми правилами и инструкциями для AI-ассистента (и в частности для работы с проектом Epid Control).

## Основные правила (ОБЯЗАТЕЛЬНО К ВЫПОЛНЕНИЮ)

1. **Язык общения:** Мы общаемся ИСКЛЮЧИТЕЛЬНО на **русском языке**.
2. **Обязательное тестирование:** После каждого изменения в коде мы **должны протестировать код** локально (например, запуская `pytest`, `ruff`, `mypy`).
3. **Отчетность по результатам работы:** После каждого валидного и протестированного изменения мы **обязательно логируем** сделанное в файл `docs/progress_report.md`.

## Инструментарий и навыки (Skills)

В директории `.agents/skills/` находятся полезные инструменты, о которых стоит знать:

- **c4-architecture:** Генерация диаграмм архитектуры С4 (Mermaid).
- **codex:** Использование Codex CLI / GPT-5.2 для интеллектуального рефакторинга.
- **commit-work:** Помощь в создании качественных git-коммитов по спецификации Conventional Commits.
- **daily-meeting-update:** Генерация ежедневного отчета (standup) на основе истории и коммитов.
- **draw-io / excalidraw / mermaid-diagrams:** Создание и работа с диаграммами и архитектурными схемами.
- **gemini:** Использование Gemini CLI для код-ревью или задач с большим контекстом.
- **jira:** Взаимодействие с задачами из Jira.
- **qa-test-planner:** План тестирования и составление тест-кейсов для QA.
- И многие другие утилиты для анализа наименований (naming-analyzer), рефакторинга (agent-md-refactor), работы с БД (database-schema-designer).

Если возникает задача, для которой подходит один из навыков, я буду использовать его (через команду или чтение его `SKILL.md`).

## О проекте "Epid Control"

- **Стек:** Python 3.11+, PySide6 (UI), SQLAlchemy 2 (ORM), SQLite (БД), Alembic (миграции).
- **Архитектура:** Clean Architecture / DDD (UI -> Application -> Domain -> Infrastructure).
- **Платформа:** Создается под Windows (Windows-first), но код должен оставаться переносимым (cross-platform / Linux-ready).
- **Quality Gates:** Перед пушем нужно пройти проверки: `ruff check app tests`, `mypy app tests`, `pytest`, `compileall`.

## Основные команды проекта

- Запуск приложения: `python -m app.main`
- Запуск всех тестов: `pytest -q`
- Проверка линтером: `ruff check app tests`
- Проверка типов: `mypy app tests`
- Накат миграций БД: `alembic upgrade head`
- Скрипт полного quality gate (Windows): `powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1`

Я буду сверяться с этими правилами перед каждой задачей.
