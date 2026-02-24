# Codex EMZ/Lab

Desktop EMZ + microbiology app (PySide6 + SQLite).

## Setup
- Python 3.11+
- `python -m venv .venv && .venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (Linux)
- `pip install -r requirements-dev.txt`
- `pre-commit install` (optional)

## Database
- Paths in `app/config.py` (platformdirs, default SQLite `app.db` in user data dir).
- Run migrations: `alembic upgrade head` (URL can be overridden with `DATABASE_URL`).

## Run
- `python -m app.main`
- Ensure there is at least one user in `users` table (create manually or via `UserAdminService`).

## Tests
- `pytest`
- Unit: `tests/unit/test_password_hash.py`
- Integration: `tests/integration/test_auth_service.py`
- Integration EMZ: `tests/integration/test_emz_service.py`
- Integration lab/sanitary: `tests/integration/test_lab_service.py`, `tests/integration/test_sanitary_service.py`

## References seed
- Optional helper to prefill departments/material types: `python scripts/seed_references.py`

## Docs
- Регрессионный тест: `docs/manual_test.md`
- Руководство пользователя: `docs/user_guide.md`
- Техническое руководство: `docs/tech_guide.md`
- Сборка/релиз: `docs/build_release.md`
