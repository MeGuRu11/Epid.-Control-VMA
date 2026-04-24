---
name: codex
description: >-
  Используй, когда пользователь просит запустить Codex CLI (`codex`, `codex exec`,
  `codex resume`) или поручить Codex локальный анализ, рефакторинг либо правки.
  Основная рекомендуемая модель для Codex-задач: GPT-5.5.
---

# Codex Skill Guide

## Основная политика моделей

- По умолчанию используй `gpt-5.5` для Codex-задач.
- `gpt-5.5` считается основным рекомендуемым вариантом для анализа кода, рефакторинга, локальных правок и длинных agentic coding workflows.
- `gpt-5.4` допускается только как временный fallback, если `gpt-5.5` ещё не доступен в аккаунте, Codex CLI, IDE extension или model picker.
- Если `gpt-5.5` не отображается, сначала предложи обновить Codex CLI / приложение / IDE extension, затем временно используй `gpt-5.4`.
- Не указывай неподтверждённые benchmark, pricing, лимиты или capabilities моделей; актуальные значения см. в официальной документации OpenAI/Codex.

## Running a Task

1. Выбери модель:
   - default: `gpt-5.5`;
   - fallback: `gpt-5.4`, только если `gpt-5.5` недоступен.
2. Уточни или выбери `reasoning_effort` по сложности задачи:
   - `xhigh` — особо сложная архитектура, безопасность, глубокое расследование;
   - `high` — сложный рефакторинг, диагностика, performance/security analysis;
   - `medium` — обычные фичи, багфиксы, организация кода;
   - `low` — простые точечные правки, форматирование, документация.
3. Выбери sandbox:
   - по умолчанию `--sandbox read-only`;
   - для локальных правок `--sandbox workspace-write`;
   - для сетевого или широкого доступа только после явного разрешения пользователя.
4. Собери команду с нужными флагами:
   - `-m, --model <MODEL>`
   - `--config model_reasoning_effort="<xhigh|high|medium|low>"`
   - `--sandbox <read-only|workspace-write|danger-full-access>`
   - `--full-auto`
   - `-C, --cd <DIR>`
   - `--skip-git-repo-check`
5. Всегда используй `--skip-git-repo-check`.
6. По умолчанию добавляй `2>/dev/null` ко всем `codex exec` командам, чтобы скрыть thinking tokens из stderr. Показывай stderr только если пользователь явно просит или если идёт отладка.
7. После завершения Codex кратко перескажи результат и сообщи пользователю: `Эту Codex-сессию можно продолжить позже через codex resume или отдельную просьбу продолжить анализ/правки.`

## Примеры команд

Интерактивный запуск с актуальной моделью:

```bash
codex -m gpt-5.5
```

Локальный read-only анализ:

```bash
codex exec -m gpt-5.5 \
  --config model_reasoning_effort="high" \
  --sandbox read-only \
  --skip-git-repo-check \
  "Проанализируй локальный проект и найди риски" 2>/dev/null
```

Локальные правки в рабочей директории:

```bash
codex exec -m gpt-5.5 \
  --config model_reasoning_effort="medium" \
  --sandbox workspace-write \
  --full-auto \
  --skip-git-repo-check \
  "Внеси локальную правку и проверь diff" 2>/dev/null
```

Fallback, если `gpt-5.5` недоступен:

```bash
codex exec -m gpt-5.4 \
  --config model_reasoning_effort="high" \
  --sandbox read-only \
  --skip-git-repo-check \
  "Выполни анализ с временным fallback на gpt-5.4" 2>/dev/null
```

## Resume

- Продолжай предыдущую сессию через stdin:

```bash
echo "Продолжи с учётом новых вводных" | codex exec --skip-git-repo-check resume --last 2>/dev/null
```

- При resume не добавляй model/sandbox/reasoning flags, если пользователь явно не попросил изменить модель или `reasoning_effort`.
- Если flags всё же нужны, вставляй их между `exec` и `resume`.

Пример с явной сменой модели при resume:

```bash
echo "Продолжи с GPT-5.5" | codex exec -m gpt-5.5 --skip-git-repo-check resume --last 2>/dev/null
```

## Quick Reference

| Use case | Sandbox mode | Key flags |
| --- | --- | --- |
| Read-only review or analysis | `read-only` | `-m gpt-5.5 --sandbox read-only --skip-git-repo-check 2>/dev/null` |
| Apply local edits | `workspace-write` | `-m gpt-5.5 --sandbox workspace-write --full-auto --skip-git-repo-check 2>/dev/null` |
| Permit network or broad access | `danger-full-access` | Только после явного разрешения пользователя |
| Resume recent session | Inherited from original | `echo "prompt" \| codex exec --skip-git-repo-check resume --last 2>/dev/null` |
| Run from another directory | Match task needs | `-C <DIR>` плюс остальные нужные flags |

## Error Handling

- Если `codex --version` или `codex exec` завершается с non-zero exit code, остановись, перескажи ошибку и запроси направление перед повтором.
- Перед high-impact flags (`--full-auto`, `--sandbox danger-full-access`, `--skip-git-repo-check`) получи разрешение пользователя, если оно ещё не было дано правилами проекта или текущей задачей.
- Если `gpt-5.5` не найден в CLI/model picker, не подменяй silently: сообщи, что нужен update Codex CLI / приложения / IDE extension, и только затем используй `gpt-5.4` как временный fallback.
- Когда вывод содержит предупреждения или частичные результаты, кратко суммируй их и предложи следующий безопасный шаг.

## CLI Version

Используй версию Codex CLI / приложения / IDE extension, которая поддерживает `gpt-5.5`. Актуальные требования по версиям, лимитам и доступности моделей см. в официальной документации OpenAI/Codex.

Для проверки:

```bash
codex --version
```

Модель можно переключить через slash-command `/model` внутри Codex-сессии или задать default в `~/.codex/config.toml`:

```toml
model = "gpt-5.5"
```
