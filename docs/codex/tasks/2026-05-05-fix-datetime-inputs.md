# Задача: fix datetime inputs

## Метаданные

- Создано: 2026-05-05 10:03
- Закрыто: 2026-05-06
- Слаг: `fix-datetime-inputs`
- Ветка: `main`
- Статус: `закрыто`
- Источник запроса: пользовательская задача Codex
- Владелец сессии: `Codex`

## Цель и границы

- Цель: исключить скрытую автоподстановку текущего времени в date-time полях ЭМЗ, лаборатории и санитарии.
- Почему это важно: время медицинского события не должно сохраняться как текущее системное без явного ввода пользователя.
- Что вошло: общий helper для опциональных date/date-time widgets, ЭМЗ reset/table widgets, лабораторные и санитарные detail dialogs, payload builder санитарных результатов, регрессионные тесты.
- Что не вошло: миграции БД, изменение доменных моделей, замена всех date-only фильтров на datetime.
- Ограничения: не добавлять `datetime.now()` как default для медицинских событий, не ломать date-only поля и сохранение уже заданного времени.

## Root cause

- `QDateTimeEdit()` в Qt по умолчанию содержит текущую дату/время.
- Лабораторные и санитарные detail dialogs создавали date-time widgets без empty sentinel, а collectors читали любой valid `dateTime()` как заполненный.
- ЭМЗ инициализировал верхние date-time поля empty sentinel, но `_reset_form` передавал `QDateTime.currentDateTime()`.
- `DateInputAutoFlow` при вводе только даты сохраняет имеющуюся time-часть widget; это становилось багом, когда time-часть была скрытым текущим временем.
- `build_sanitary_result_update` подставлял `datetime.now(UTC)` для `growth_result_at`, когда были результаты, но не было явной даты/времени результата.

## Карта полей

- Date-only:
  - ЭМЗ: дата рождения, дата ИСМП;
  - лаборатория/санитария: фильтры периодов;
  - ЭМК/аналитика: date-фильтры;
  - Form100 V2: даты и время представлены раздельными `QDateEdit`/`QTimeEdit`.
- Date-time:
  - ЭМЗ: дата/время травмы, поступления, исхода;
  - ЭМЗ таблицы: начало/окончание вмешательств, начало/окончание антибиотикотерапии;
  - лаборатория: дата назначения, время взятия, дата доставки, результат роста;
  - санитария: время взятия, дата доставки, результат роста.

## Выполнено

1. [x] Проведён аудит `QDateEdit`/`QDateTimeEdit`/`QTimeEdit`, `currentDateTime()`, `datetime.now()`, collectors/appliers.
2. [x] Добавлен `app/ui/widgets/datetime_inputs.py`.
3. [x] ЭМЗ переведён на общий helper и empty reset.
4. [x] Лабораторная и санитарная карточки переведены на optional date-time widgets.
5. [x] Санитарный result payload больше не подставляет текущее время.
6. [x] Добавлены/обновлены регрессионные тесты.
7. [x] Пройден полный quality gate.
8. [x] Обновлены `docs/progress_report.md` и `docs/session_handoff.md`.

## Checkpoints

### 2026-05-05 10:03

- Создан task-файл.
- Стартовый снимок рабочей директории: рабочее дерево было чистым.

### 2026-05-05 10:20

- Аудит `QDateTimeEdit`/`currentDateTime()`/collectors показал: корень бага в неявных defaults `QDateTimeEdit()` и в явном reset на current datetime, а не в одном поле ЭМЗ.
- Карта полей: date-only поля/фильтры используют `QDateEdit` или `QDateTimeEdit` с format `dd.MM.yyyy`; date-time поля ЭМЗ/лаборатории/санитарии должны иметь format `dd.MM.yyyy HH:mm` и empty sentinel.

### 2026-05-06

- Реализован helper optional date/date-time widgets.
- Подключены ЭМЗ, лаборатория, санитария.
- Добавлены offscreen GUI-регрессии и smoke.
- Команды quality gate прошли.

## Validation Ledger

- `ruff check app tests` — pass.
- `python scripts/check_architecture.py` — pass.
- `python -m mypy app tests` — pass (`301 source files`).
- `python -m pytest tests/unit/test_date_input_flow.py -q` — pass (`7 passed`).
- `python -m pytest tests/unit/test_emz_form_table_setups.py -q` — pass (`7 passed`).
- `python -m pytest tests/unit/test_emz_form_table_appliers.py -q` — pass (`5 passed`).
- `python -m pytest tests/unit/test_emz_form_table_collectors.py -q` — pass (`4 passed`).
- `python -m pytest tests/unit/test_emz_form_request_builders.py -q` — pass (`4 passed`).
- `python -m pytest tests/unit/test_lab_sample_detail_helpers.py -q` — pass (`8 passed`).
- `python -m pytest tests/unit/test_lab_samples_view.py -q` — pass (`4 passed`).
- `python -m pytest tests/unit/test_sanitary_dashboard.py -q` — pass (`7 passed`).
- `python -m pytest tests/unit/test_form100_v2_editor_fields.py -q` — pass (`3 passed`).
- `python -m pytest tests/unit -q` — pass (`388 passed`).
- `python -m pytest -q` — pass (`464 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m alembic check` — pass.
- `python scripts/check_mojibake.py` — pass.
- `git diff --check` — pass; только CRLF warnings Git, whitespace ошибок нет.
- Offscreen smoke лабораторной и санитарной карточек — pass (`offscreen smoke passed`).

## Resume Point

- Следующее действие: нет, задача закрыта.
- Открытые вопросы / блокеры: нет.
- Что проверить вручную при ближайшем доступе к видимому GUI: открыть ЭМЗ, лабораторную и санитарную карточки; вручную задать дату+время; сохранить и повторно открыть; убедиться, что выбранные часы/минуты сохранились.
