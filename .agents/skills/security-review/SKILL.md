---
name: security-review
description: >-
  Аудит безопасности проекта Epid Control. Используй перед релизом,
  после крупных изменений в auth/БД/пользовательском вводе, или по запросу.
  Триггеры: "проверка безопасности", "security review", "аудит безопасности",
  "перед релизом", "проверь уязвимости".
  НЕ используй для обычных код-ревью без фокуса на безопасность.
---

# Security Review: Epid Control

## Контекст проекта

Epid Control — десктопное медицинское приложение (PySide6 + SQLAlchemy + SQLite).
Обрабатывает **персональные данные пациентов** и медицинскую информацию.
Это накладывает повышенные требования к безопасности.

## Когда проводить security review

- Перед каждым релизом / сборкой EXE
- После изменений в аутентификации / авторизации
- После добавления нового пользовательского ввода
- После изменений в модели данных (новые таблицы с персональными данными)
- По запросу пользователя

---

## Чеклист: 7 направлений проверки

### 1. Аутентификация

Проверь:
```bash
# Как хешируются пароли
rg -n "hash_password|verify_password|bcrypt|argon2|sha256|md5" app/

# Сессии и их время жизни
rg -n "session|Session|token|jwt|cookie" app/ --glob "*.py" | rg -v "sqlalchemy|db.session|SessionContext"

# Rate limiting на логин
rg -n "attempt|lockout|rate_limit|max_attempts|LOGIN_ATTEMPTS" app/
```

Что искать:
- [ ] Пароли хешируются через bcrypt или argon2 (НЕ md5/sha1/sha256)
- [ ] Есть ограничение попыток входа (lockout после N попыток)
- [ ] Сессия имеет срок жизни
- [ ] При логауте сессия полностью инвалидируется
- [ ] Пароль по умолчанию не хардкодится

### 2. Авторизация и разграничение доступа

Проверь:
```bash
# Проверки ролей
rg -n "role|can_access|can_manage|is_admin|permission" app/

# Операции без проверки прав
rg -n "def create_|def update_|def delete_" app/application/services/ | head -20
```

Что искать:
- [ ] Каждая операция CRUD проверяет роль пользователя
- [ ] actor_id передаётся в каждую мутирующую операцию
- [ ] Аудит-лог фиксирует кто, когда, что изменил
- [ ] Нет эндпоинтов, доступных без авторизации

### 3. Валидация ввода и SQL-инъекции

Проверь:
```bash
# f-string в SQL (потенциальные инъекции)
rg -n 'f".*SELECT|f".*INSERT|f".*UPDATE|f".*DELETE|f".*DROP|f".*CREATE' app/
rg -n 'text\(f"' app/

# Динамические SQL через .format()
rg -n '\.format\(.*SELECT|\.format\(.*INSERT' app/

# Конкатенация строк в SQL
rg -n '"\s*\+\s*.*SELECT|"\s*\+\s*.*INSERT' app/

# Пользовательский ввод без валидации
rg -n "text\(\)|toPlainText\(\)|currentText\(\)" app/ui/ | head -20
```

Что искать:
- [ ] Все SQL-запросы параметризованы (text() + bindparams, НЕ f-string)
- [ ] Пользовательский ввод из форм валидируется перед отправкой в сервис
- [ ] Числовые поля проверяются на тип (не принимают строки)
- [ ] Текстовые поля имеют ограничение длины
- [ ] DDL с f-string помечены комментарием SQL-injection safe

### 4. Защита данных пациентов

Проверь:
```bash
# Персональные данные
rg -n "patient|fio|name|birth|паспорт|snils|полис|адрес|address|phone|телефон" app/infrastructure/db/models_sqlalchemy.py

# Экспорт/импорт данных
rg -n "export|import|backup|dump|extract" app/ --glob "*.py" | head -20

# Логирование персональных данных
rg -n "log.*patient|log.*fio|log.*name|print.*patient" app/
```

Что искать:
- [ ] БД-файл не в общедоступном месте (AppData или указанный каталог)
- [ ] Бэкапы не содержат пароли в открытом виде
- [ ] При экспорте данные не логируются в консоль/файл
- [ ] Нет print() с персональными данными пациентов
- [ ] Аудит-лог не содержит полных ПД (только ID и действие)
- [ ] При удалении пациента каскадно удаляются связанные данные

### 5. Секреты и конфигурация

Проверь:
```bash
# Хардкод секретов
rg -n "password|secret|key|token" app/ --glob "*.py" | rg -v "hash_password|verify_password|api_key.*=.*os|getenv|environ|config\." | head -20

# .env / .gitignore
cat .gitignore | rg -i "env|secret|key|db|sqlite"

# Пароли по умолчанию
rg -n "default.*password|password.*default|admin.*123|123.*admin" app/
```

Что искать:
- [ ] Нет хардкоженных паролей/ключей в коде
- [ ] .db файлы в .gitignore
- [ ] Конфигурация через ENV-переменные или config.py
- [ ] Нет пароля по умолчанию при first run (пользователь создаёт сам)

### 6. Целостность БД

Проверь:
```bash
# FK constraints
rg -n "ForeignKey|foreign_key" app/infrastructure/db/models_sqlalchemy.py

# Каскадное удаление
rg -n "cascade|ondelete|on_delete" app/infrastructure/db/models_sqlalchemy.py

# Транзакции
rg -n "session.commit|session.rollback|session.flush" app/
```

Что искать:
- [ ] Все FK имеют ON DELETE CASCADE или SET NULL (не оставляют orphan records)
- [ ] Мутирующие операции в транзакции (with session_scope())
- [ ] При ошибке — rollback, а не partial commit
- [ ] Alembic-миграции обратимы (есть downgrade)

### 7. Desktop-специфичные риски

Проверь:
```bash
# Запуск внешних процессов
rg -n "subprocess|os.system|Popen|exec\(|eval\(" app/

# Работа с файловой системой
rg -n "open\(|Path\(|os.path|shutil" app/ --glob "*.py" | rg -v "test|__pycache__" | head -20

# Temp-файлы
rg -n "tmp|temp|NamedTemporaryFile|mkdtemp" app/
```

Что искать:
- [ ] subprocess не вызывается с shell=True
- [ ] Нет eval()/exec() с пользовательскими данными
- [ ] Temp-файлы очищаются после использования
- [ ] Пути к файлам не конструируются через конкатенацию строк с пользовательским вводом

---

## Формат отчёта

Для каждой найденной проблемы:

```
Уровень: КРИТИЧНО / ВАЖНО / РЕКОМЕНДАЦИЯ
Файл: app/путь/к/файлу.py:строка
Проблема: что не так
Риск: что может случиться
Фикс: конкретное исправление (код или описание)
```

## После аудита

1. Сохрани отчёт в `docs/security_review_[дата].md`
2. Критичные проблемы — исправить немедленно
3. Важные — добавить в план (P1)
4. Рекомендации — добавить в backlog (P2)
5. Обнови docs/progress_report.md и docs/session_handoff.md
