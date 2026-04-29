# Changelog

Все значимые изменения проекта фиксируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

---

## [Unreleased]

## [2026-04-27] — Model Update

- Обновлена модель Codex агента: GPT-5.5 (вышел 2026-04-23)
  заменяет GPT-5.4 для Stage 5–9 (frontend: Auth, Editor, Player, Dashboards, Admin)
- GPT-5.5 доступен в Codex для Plus/Pro/Business/Enterprise
- `gpt-5.4` оставлен только как временный fallback, если `gpt-5.5` ещё недоступен
  в конкретном аккаунте, Codex CLI, IDE extension или model picker

