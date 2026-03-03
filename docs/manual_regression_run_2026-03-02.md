# Ручной Регресс: Прогон 2026-03-02

## Контекст прогона
- Дата: 2026-03-02
- Цель: старт полного ручного прогона по чек-листу раздела 14.4 в `docs/context.md`.
- Режим: двухфазный
  - Фаза 1: автоматизированный precheck (выполнено)
  - Фаза 2: ручная UI-приемка (требует прогона в desktop UI)

## Фаза 1: Автоматизированный Precheck
- Команда:
  - `venv\Scripts\python.exe -m pytest -q tests/integration/test_auth_service.py tests/integration/test_reference_service.py tests/integration/test_reference_service_crud.py tests/integration/test_reference_service_catalogs.py tests/integration/test_reference_service_acl.py tests/integration/test_patient_service_core.py tests/integration/test_emz_service.py tests/integration/test_exchange_service_import_zip.py tests/integration/test_exchange_service_import_reports.py tests/integration/test_lab_service.py tests/integration/test_sanitary_service.py tests/integration/test_reporting_service_artifacts.py tests/integration/test_analytics_service_queries.py tests/unit/test_main_window_context_selection.py tests/unit/test_patient_widgets_error_handling.py tests/unit/test_emz_form_validators.py tests/unit/test_lab_sanitary_actions_layout.py tests/unit/test_startup_error_handling.py`
- Результат:
  - `49 passed in 21.40s`
- Вывод:
  - критических автодефектов в покрытых сценариях не обнаружено.

## Фаза 2: Ручная UI-приемка (чек-лист 14.4)

| Блок 14.4 | Статус | Авто-покрытие | Комментарий |
| --- | --- | --- | --- |
| Закрепление пациента/госпитализации | ⏳ Pending manual | `test_main_window_context_selection.py`, `test_patient_widgets_error_handling.py` | Нужна визуальная проверка связки вкладок и поведения кнопок в UI. |
| Поиск и ЭМК | ⏳ Pending manual | `test_patient_service_core.py` | Нужна ручная проверка передачи `patient_id/emr_case_id` при открытии из карточки. |
| ЭМЗ (создание/редактирование/валидации) | ⏳ Pending manual | `test_emz_service.py`, `test_emz_form_validators.py` | Нужен визуальный сценарий создания/редактирования формы в реальном окне. |
| Импорт/экспорт (ZIP/XLSX + безопасный отказ) | ⏳ Pending manual | `test_exchange_service_import_zip.py`, `test_exchange_service_import_reports.py` | Авто-проверки зеленые, руками проверить UX-сообщения и путь пользователя в мастере. |
| Лаборатория и санитария | ⏳ Pending manual | `test_lab_service.py`, `test_sanitary_service.py`, `test_lab_sanitary_actions_layout.py` | Нужна ручная проверка фильтров/пагинации/обновления списков на живом UI. |

## Дефекты по итогу старта прогона
- Автофаза: дефекты не обнаружены.
- Ручная фаза: не начата в UI (pending), дефекты будут добавляться по мере прохождения.

## Следующий шаг
- Выполнить ручной прогон блоков 14.4 на целевых разрешениях (1366x768, 1600x900, 1920x1080; scale 100/125/150) и зафиксировать результаты в этом файле.

