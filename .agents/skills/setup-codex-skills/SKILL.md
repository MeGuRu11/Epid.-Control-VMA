---
name: setup-codex-skills
description: >-
  Установка и настройка скиллов для Codex в проекте Epid Control.
  Используй когда пользователь просит: "настрой codex", "установи скиллы",
  "прокачай агента", "setup skills". НЕ используй для обычной разработки.
---

# Установка скиллов для Codex — Epid Control

Этот скилл выполняется ОДИН РАЗ для настройки окружения.
Выполняй шаги по порядку. После каждого шага сообщай пользователю результат.

---

## ШАГ 1: Установка курируемых скиллов из openai/skills

Выполни эти команды внутри Codex (каждую отдельно, дождись завершения):

```
$skill-installer doc
```
```
$skill-installer sentry
```
```
$skill-installer install the create-plan skill from the .experimental folder
```

**Проверка:** после каждой команды убедись, что скилл появился в `~/.codex/skills/` или `.agents/skills/`.

Если `$skill-installer` не работает, установи вручную:
```bash
# Создай папку и скачай через GitHub API
mkdir -p ~/.codex/skills/doc
curl -sL "https://raw.githubusercontent.com/openai/skills/main/skills/.curated/doc/SKILL.md" \
  -o ~/.codex/skills/doc/SKILL.md
```

---

## ШАГ 2: Установка скиллов из LobeHub Marketplace

Выполни каждую команду. Если curl не работает (sandbox блокирует домен) — 
**СООБЩИ ПОЛЬЗОВАТЕЛЮ** и выведи команду, чтобы он выполнил её вручную в терминале.

### 2.1 PySide6 Architecture
```bash
mkdir -p ~/.codex/skills/pyside6-architecture
curl -sL "https://lobehub.com/skills/ds-codi-project-memory-mcp-pyside6-qml-architecture/skill.md" \
  -o ~/.codex/skills/pyside6-architecture/SKILL.md
echo "✅ pyside6-architecture установлен"
```

### 2.2 Python Testing Patterns
```bash
mkdir -p ~/.codex/skills/python-testing-patterns
curl -sL "https://lobehub.com/skills/juanjosegongi-skills-python-testing-patterns/skill.md" \
  -o ~/.codex/skills/python-testing-patterns/SKILL.md
echo "✅ python-testing-patterns установлен"
```

### 2.3 Integration Testing (без моков)
```bash
mkdir -p ~/.codex/skills/integration-testing
curl -sL "https://lobehub.com/skills/simonheimlicher-spx-claude-testing/skill.md" \
  -o ~/.codex/skills/integration-testing/SKILL.md
echo "✅ integration-testing установлен"
```

### 2.4 Codex Agent Skill
```bash
mkdir -p ~/.codex/skills/codex-agent
curl -sL "https://lobehub.com/skills/openclaw-skills-codex-skill/skill.md" \
  -o ~/.codex/skills/codex-agent/SKILL.md
echo "✅ codex-agent установлен"
```

### 2.5 Codex Plugin CC (кросс-ревью)
```bash
mkdir -p ~/.codex/skills/codex-plugin-cc
curl -sL "https://lobehub.com/skills/aradotso-trending-skills-codex-plugin-cc/skill.md" \
  -o ~/.codex/skills/codex-plugin-cc/SKILL.md
echo "✅ codex-plugin-cc установлен"
```

### 2.6 Oh-My-Codex (мульти-агент)
```bash
mkdir -p ~/.codex/skills/oh-my-codex
curl -sL "https://lobehub.com/skills/neversight-learn-skills.dev-oh-my-codex/skill.md" \
  -o ~/.codex/skills/oh-my-codex/SKILL.md
echo "✅ oh-my-codex установлен"
```

### 2.7 LobeHub Skill Installer (расширенный)
```bash
mkdir -p ~/.codex/skills/lobehub-installer
curl -sL "https://lobehub.com/skills/openai-codex-skill-installer/skill.md" \
  -o ~/.codex/skills/lobehub-installer/SKILL.md
echo "✅ lobehub-installer установлен"
```

**После каждого curl проверь:**
```bash
# Файл должен содержать YAML frontmatter (---) в начале
head -5 ~/.codex/skills/<имя>/SKILL.md
```
Если файл содержит HTML или ошибку — сообщи пользователю.

---

## ШАГ 3: Установка Superpowers

### Windows:
```powershell
git clone https://github.com/obra/superpowers "$env:USERPROFILE\.codex\superpowers"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\superpowers" "$env:USERPROFILE\.codex\superpowers\skills"
```

### Linux/macOS:
```bash
git clone https://github.com/obra/superpowers ~/.codex/superpowers
mkdir -p ~/.agents/skills
ln -sf ~/.codex/superpowers/skills ~/.agents/skills/superpowers
```

**Если git clone не работает** (sandbox) — сообщи пользователю:
> ⚠️ Я не могу клонировать репозиторий из sandbox.
> Выполни в своём терминале:
> `git clone https://github.com/obra/superpowers ~/.codex/superpowers`
> Затем скажи мне, и я продолжу настройку.

---

## ШАГ 4: Настройка config.toml

Проверь, существует ли файл:
```bash
cat ~/.codex/config.toml 2>/dev/null || echo "ФАЙЛ НЕ СУЩЕСТВУЕТ"
```

Если файл существует — **НЕ перезаписывай целиком**. Проверь текущие значения:
- если `model = "..."`
  уже есть, замени значение на `model = "gpt-5.5"`;
- если `model` отсутствует, добавь `model = "gpt-5.5"` в корень TOML;
- если `[model_config]` уже есть, выставь `reasoning_effort = "high"`;
- если `[experimental]` уже есть, выставь `collab = true`;
- отсутствующие секции добавь в конец.

Целевый фрагмент:
```toml
model = "gpt-5.5"

[model_config]
reasoning_effort = "high"

[experimental]
collab = true
```

Если файла нет — создай:
```bash
mkdir -p ~/.codex
cat > ~/.codex/config.toml << 'EOF'
model = "gpt-5.5"

[model_config]
reasoning_effort = "high"

[experimental]
collab = true
EOF
```

### Fallback по модели

- Основной default для Codex-задач: `gpt-5.5`.
- Если `gpt-5.5` не отображается в аккаунте, Codex CLI, приложении, IDE extension или model picker, сначала обнови Codex CLI / приложение / IDE extension.
- До обновления можно временно использовать `gpt-5.4` как fallback.
- Не фиксируй benchmark, pricing, лимиты или capabilities моделей в проектной документации; актуальные значения см. в официальной документации OpenAI/Codex.

CLI-примеры:

```bash
codex -m gpt-5.5
```

```bash
codex exec -m gpt-5.5 \
  --config model_reasoning_effort="high" \
  --sandbox read-only \
  --skip-git-repo-check \
  "Проверь локальный проект" 2>/dev/null
```

---

## ШАГ 5: Проверка кастомных файлов проекта

Убедись, что в репозитории есть:

### 5.1 AGENTS.md в корне
```bash
if [ -f "AGENTS.md" ]; then
  echo "✅ AGENTS.md найден"
else
  echo "❌ AGENTS.md НЕ НАЙДЕН — нужно добавить!"
fi
```

### 5.2 Скилл epid-control
```bash
if [ -f ".agents/skills/epid-control/SKILL.md" ]; then
  echo "✅ epid-control скилл найден"
else
  echo "❌ epid-control скилл НЕ НАЙДЕН — нужно добавить!"
fi
```

Если файлы отсутствуют — попроси пользователя добавить их (они были созданы ранее).

---

## ШАГ 6: Финальная проверка

```bash
echo "=== Проверка установленных скиллов ==="
echo ""
echo "--- Пользовательские скиллы (~/.codex/skills/) ---"
ls -d ~/.codex/skills/*/ 2>/dev/null || echo "(пусто)"
echo ""
echo "--- Проектные скиллы (.agents/skills/) ---"
ls -d .agents/skills/*/ 2>/dev/null || echo "(пусто)"
echo ""
echo "--- Superpowers ---"
ls ~/.agents/skills/superpowers/ 2>/dev/null || echo "(не установлен)"
echo ""
echo "--- Config ---"
cat ~/.codex/config.toml 2>/dev/null || echo "(не найден)"
echo ""
echo "=== Готово! ==="
echo "⚠️ ПЕРЕЗАПУСТИ CODEX чтобы подхватить новые скиллы."
echo "После перезапуска набери /skills для проверки."
```

---

## ВАЖНО: что Codex НЕ МОЖЕТ сделать сам

Эти шаги требуют действий пользователя:

1. **Перезапуск Codex** — скажи пользователю: "Перезапусти Codex (Ctrl+C и запусти заново)".
2. **git clone в sandbox** — если заблокирован, выведи команду для ручного выполнения.
3. **curl на заблокированные домены** — выведи команду для ручного выполнения.
4. **git push** — после добавления AGENTS.md и скилла, пользователь должен запушить.

Для каждого такого случая — **чётко скажи пользователю что сделать и какую команду выполнить**.
