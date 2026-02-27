# Epid Control

Desktop-application for EMZ and microbiology workflows (PySide6 + SQLite).

## Quick Start
1. Use Python 3.11+ (3.12 recommended).
2. Create and activate a virtual environment:
   - Windows: `python -m venv venv` and `venv\Scripts\activate`
   - Linux/macOS: `python -m venv .venv` and `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements-dev.txt`

## Run
- Start app: `python -m app.main`
- DB path and runtime settings are configured via `app/config.py` and ENV variables:
  - `EPIDCONTROL_DATA_DIR`
  - `EPIDCONTROL_DB_FILE`
  - `DATABASE_URL`
- Manual DB migrations: `alembic upgrade head`

## Local Quality Gates
Run before merge:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\quality_gates.ps1
```

This script runs:
- `ruff check app tests`
- `mypy app tests`
- `pytest -q`
- `python -m compileall -q app tests scripts`

## CI
- Automatic quality checks are configured in `.github/workflows/quality-gates.yml`.

## Helpful Scripts
- Seed reference data: `python scripts/seed_references.py`
- Build EXE/installer: see `scripts/` and `docs/build_release.md`

## Documentation
- Context and roadmap: `docs/context.md`
- Progress log: `docs/progress_report.md`
- Manual regression scenarios: `docs/manual_regression_scenarios.md`
- User guide: `docs/user_guide.md`
- Technical guide: `docs/tech_guide.md`
- Build and release guide: `docs/build_release.md`
