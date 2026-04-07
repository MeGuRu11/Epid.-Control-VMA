# Полный аудит безопасности — Epid Control (2026-04-07)

## Контекст и методика

- Проверены 7 направлений из чеклиста (`auth`, `authorization`, `SQL`, `PHI`, `secrets`, `DB integrity`, `desktop-specific`).
- Использованы статические проверки `rg` и ручной разбор критичных файлов (`app/application/services/*`, `app/ui/*`, `app/infrastructure/*`).
- Формат находок: уровень, категория, файл/строка, проблема, риск, фикс.

## Найденные проблемы

### 1) Уровень: КРИТИЧНО
Категория: Авторизация  
Файл: `app/ui/main_window.py:204`, `app/ui/import_export/import_export_wizard.py:108`, `app/application/services/exchange_service.py:347`  
Проблема: операции импорта/экспорта доступны всем авторизованным пользователям без проверки роли/права (нет gate по `session.role` и нет server-side permission check в `ExchangeService`).  
Риск: оператор с минимальными правами может массово экспортировать персональные и медицинские данные пациентов (CSV/XLSX/PDF/JSON/ZIP).  
Фикс: ввести отдельное permission (например, `manage_exchange`), проверять его и в UI, и в application-сервисе перед экспортом/импортом; все операции отклонять при отсутствии права.

### 2) Уровень: КРИТИЧНО
Категория: Данные  
Файл: `app/application/services/form100_service_v2.py:615`  
Проблема: в аудит (`_write_audit`) пишется `before/after` payload карточки Form100, включая персональные данные.  
Риск: аудит-таблица становится хранилищем избыточных ПДн/медданных; увеличивается поверхность утечки и нарушение принципа минимизации данных.  
Фикс: хранить в аудите только техничные метаданные изменений (список полей, идентификаторы, actor_id, timestamp, hash-отпечаток), без полных значений ПДн.

### 3) Уровень: ВАЖНО
Категория: Авторизация  
Файл: `app/application/services/reference_service.py:29`  
Проблема: `_require_admin_write` возвращает успех при `actor_id is None` (bypass проверки прав).  
Риск: внутренний/ошибочный вызов методов изменения справочников без `actor_id` проходит без авторизации.  
Фикс: запретить `None` для write-операций (`raise ValueError`), сделать `actor_id` обязательным в сигнатурах mutating методов.

### 4) Уровень: ВАЖНО
Категория: Авторизация  
Файл: `app/application/services/backup_service.py:38`  
Проблема: `_require_admin_access` пропускает проверку при `actor_id is None`.  
Риск: потенциальный обход контроля доступа для backup/restore при внутреннем вызове с `None`.  
Фикс: разделить системные автозадачи и пользовательские операции; для ручных backup/restore требовать обязательный `actor_id` и право `manage_backups`.

### 5) Уровень: ВАЖНО
Категория: Авторизация  
Файл: `app/application/services/patient_service.py:50`, `app/application/services/patient_service.py:206`, `app/application/services/patient_service.py:248`, `app/application/services/patient_service.py:465`  
Проблема: мутации пациента (`create_or_get`, `update_*`, `delete_patient`) не принимают `actor_id`, не проверяют права и не пишут аудит-события изменений.  
Риск: отсутствует трассируемость «кто изменил/удалил пациента», повышается риск несанкционированных правок без forensic-следа.  
Фикс: добавить `actor_id` во все mutating методы, внедрить permission check, писать аудит-события create/update/delete.

### 6) Уровень: ВАЖНО
Категория: Авторизация  
Файл: `app/application/services/lab_service.py:49`, `app/application/services/sanitary_service.py:34`  
Проблема: `create_sample` не принимает `actor_id` отдельно, а использует `request.created_by` (caller-controlled), без проверки прав.  
Риск: подмена автора операции в аудите и слабая доверенность к полю `created_by`.  
Фикс: убрать `created_by` из входного DTO, передавать `actor_id` как отдельный обязательный аргумент из trusted session context.

### 7) Уровень: ВАЖНО
Категория: Аутентификация  
Файл: `app/ui/login_dialog.py:30`, `app/ui/login_dialog.py:211`  
Проблема: lockout реализован только в состоянии диалога (память процесса), сбрасывается при перезапуске приложения.  
Риск: brute-force можно обходить рестартом приложения; нет устойчивого ограничения попыток.  
Фикс: хранить счётчик неуспешных попыток и время блокировки в БД/кэше по логину (или по пользователю), проверять в `AuthService`.

### 8) Уровень: ВАЖНО
Категория: Аутентификация  
Файл: `app/application/dto/auth_dto.py:15`, `app/ui/main_window.py:419`  
Проблема: нет сессионного TTL/idle-timeout; сессия действует до ручного logout/закрытия окна.  
Риск: оставленная без присмотра рабочая станция даёт длительный несанкционированный доступ.  
Фикс: ввести inactivity timeout с автоматическим logout и повторным запросом пароля.

### 9) Уровень: ВАЖНО
Категория: Аутентификация  
Файл: `app/ui/first_run_dialog.py:117`, `app/application/services/setup_service.py:23`  
Проблема: UI декларирует пароль «не менее 8 символов», но `SetupService` фактически проверяет только непустое значение.  
Риск: создание слабого админского пароля на первичном запуске.  
Фикс: enforce `MIN_PASSWORD_LENGTH` в `SetupService` (минимум 8+), по возможности добавить требования сложности.

### 10) Уровень: ВАЖНО
Категория: Данные  
Файл: `app/application/services/backup_service.py:91`, `app/application/services/backup_service.py:112`, `app/application/services/exchange_service.py:347`  
Проблема: backup и экспортные артефакты сохраняются в открытом виде (без шифрования).  
Риск: при компрометации файловой системы/копировании файлов утечка ПДн и медданных.  
Фикс: шифровать backup/экспорт (например, AES-GCM), хранить ключи вне репозитория (ENV/OS keystore), ограничить права доступа к директориям артефактов.

### 11) Уровень: ВАЖНО
Категория: Данные  
Файл: `app/application/services/reporting_service.py:409`  
Проблема: в `ReportRun.filters_json` сохраняются фильтры отчёта, включая потенциально чувствительные поля (`patient_name`, `lab_no`, `search_text`) в открытом виде.  
Риск: накопление чувствительных поисковых данных в служебной таблице отчётов.  
Фикс: маскировать/редактировать чувствительные фильтры перед сохранением или хранить только хэш/токенизированные значения.

### 12) Уровень: РЕКОМЕНДАЦИЯ
Категория: SQL  
Файл: `app/infrastructure/db/fts_manager.py:74`, `app/infrastructure/db/fts_manager.py:83`, `app/infrastructure/db/fts_manager.py:111`, `app/infrastructure/db/fts_manager.py:141`, `app/infrastructure/db/fts_manager.py:314`  
Проблема: используется DDL через f-string для имён таблиц/триггеров.  
Риск: сейчас значения в основном контролируются программно, но паттерн хрупкий и потенциально опасен при расширении/рефакторинге.  
Фикс: оставить только whitelist-идентификаторы и явную функцию безопасного quoting для имён объектов; исключить формирование SQL из внешних строк.

### 13) Уровень: РЕКОМЕНДАЦИЯ
Категория: БД  
Файл: `app/infrastructure/db/models_sqlalchemy.py:182`, `app/infrastructure/db/models_sqlalchemy.py:287`, `app/infrastructure/db/models_sqlalchemy.py:313`  
Проблема: часть FK задана без явной политики `ondelete` (используется default behavior).  
Риск: непредсказуемое поведение при удалении родительских сущностей и зависимость от ручной «каскадной» логики в сервисах.  
Фикс: формализовать стратегию `ON DELETE` для всех FK (CASCADE/SET NULL/RESTRICT) и закрепить в моделях + миграциях.

### 14) Уровень: РЕКОМЕНДАЦИЯ
Категория: Desktop  
Файл: `app/ui/import_export/import_export_view.py:230`, `app/ui/analytics/analytics_view.py:1081`  
Проблема: открытие артефактов происходит по пути из БД/таблицы без ограничений на доверенный каталог.  
Риск: при подмене записи БД пользователь может открыть нежелательный путь (например, внешний UNC-ресурс).  
Фикс: перед открытием проверять, что путь находится в разрешённых директориях артефактов (`DATA_DIR/artifacts`, `DATA_DIR/backups`) или требовать явное подтверждение.

## Проверки без критичных отклонений

- Хеширование паролей: используется `argon2`/`bcrypt`; `md5/sha1/plain` не найдены (`app/infrastructure/security/password_hash.py`).
- Критичных DML SQL-инъекций через f-string не обнаружено (SELECT/INSERT/UPDATE/DELETE в raw SQL).
- `subprocess/os.system/shell=True/eval()` в `app/` не выявлены.
- Транзакционный контур `session_scope()` корректно содержит `commit/rollback/close`.
- В `.gitignore` присутствуют `*.db`, `*.sqlite`, `data/`, `*.log`, кеши.

## Итог

- КРИТИЧНЫХ: 2
- ВАЖНЫХ: 9
- РЕКОМЕНДАЦИЙ: 3
