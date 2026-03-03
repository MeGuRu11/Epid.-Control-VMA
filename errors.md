# Error Log

## Context
- This file was restored because it was missing on disk during the current session.
- It is used as a working tracker for static diagnostics and runtime errors.

## 2026-02-27

### Resolved
- `scripts/build_reference_seed.py`
  - Fixed Pylance-style typing gaps (`Unknown`, missing type arguments).
  - Added explicit row type alias and typed collections in parser functions.
  - Removed nullable assignment for `group_code` by guarding `None`.
  - Validation:
    - `ruff check scripts/build_reference_seed.py` -> passed
    - `mypy --no-incremental scripts/build_reference_seed.py` -> passed
    - Full `scripts/quality_gates.ps1` -> passed

### Current status
- No active diagnostics reproduced by local `mypy` for `scripts/`:
  - `mypy --no-incremental scripts` -> success (0 issues).

## Next updates format
- Date/time
- File/module
- Symptom
- Root cause
- Fix
- Verification command/result

## 2026-02-27 (update) - Test_UI services

### Resolved
- `Test_UI/app/application/services/*`
  - Symptom: `ruff` reported style violations (`E501`/`I001`/`B007`), while `mypy` was mostly clean.
  - Root cause: inconsistent formatting and one leftover loop-stub in analytics flow.
  - Fix: applied `ruff format` + `ruff check --fix`; removed loop-stub in `analytics_service.py`.
  - Verification:
    - `venv\Scripts\python.exe -m ruff check Test_UI/app/application/services` -> passed
    - `venv\Scripts\python.exe -m mypy --no-incremental Test_UI/app/application/services` -> passed

### Current status
- Active diagnostics for `Test_UI/app/application/services` are not reproduced on local checks.
## 2026-02-27 (update-2) - Form100 V2 wizard UI

### Resolved
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`
  - Symptom: review rows used inline RichText color styling; panel was overly rigid by width.
  - Root cause: HTML-based row rendering and high minimum width.
  - Fix: replaced with themed row widgets and reduced panel width constraints.
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py`
  - Symptom: extra fixed-width points reduced flexibility on compact layouts.
  - Fix: replaced fixed widths with min/max + size policies.
- `app/ui/theme.py`
  - Symptom: review badges had heavy outlines.
  - Fix: removed badge borders and added dedicated styles for review row label/value.

### Verification
- `venv\\Scripts\\python.exe -m ruff check app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` -> passed
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_ui_no_inline_styles.py tests/unit/test_notifications_status.py -p no:cacheprovider` -> 8 passed

## 2026-02-27 (update-3) - startup/logging + signal stability

### Resolved
- `app/main.py`
  - Symptom: possible crash path in migration/startup stage with `flush` on stream wrappers.
  - Root cause: stream wrapper exceptions could include `AttributeError` and were not handled.
  - Fix: added `AttributeError` handling in `_TeeStream.write/flush/isatty/fileno`.
- `app/ui/form100_v2/wizard_widgets/lesion_type_widget.py`
  - Symptom: runtime signal mismatch reported as `valuesChanged() only accepts 0 argument(s), 1 given`.
  - Root cause: toggled signal forwarding needed an explicit bool-accepting slot boundary.
  - Fix: routed toggled -> `_emit_values_changed(_checked: bool)` -> `valuesChanged.emit()`.

### Verification
- `venv\\Scripts\\python.exe -m ruff check app/main.py app/ui/form100_v2/wizard_widgets/lesion_type_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/main.py app/ui/form100_v2/wizard_widgets/lesion_type_widget.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py app/ui/form100_v2/wizard_widgets/wizard_steps/step_bodymap.py app/ui/theme.py` -> passed
- `venv\\Scripts\\python.exe -m pytest -q tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_list_panel_filters.py tests/unit/test_main_window_context_selection.py tests/unit/test_notifications_status.py tests/unit/test_ui_no_inline_styles.py -p no:cacheprovider` -> 12 passed
## 2026-02-27 (update-4) - Full Pylance cleanup (excluding Test_UI)

### Resolved
- `app/`, `scripts/`, `tests/`
  - Symptom: множественные Pylance/pyright ошибки (SQLAlchemy typed columns, nullable-access, unknown member/return types).
  - Root cause: неявные приведения типов и доступ к потенциально `None` значениям в сервисах, репозиториях, UI и тестах.
  - Fix: добавлены безопасные typed guards/casts, выровнены сигнатуры и проверки nullable полей, подключен `pyrightconfig.json` с исключением `Test_UI`.

### Verification
- `venv\\Scripts\\python.exe -m pyright` -> 0 errors
- `venv\\Scripts\\python.exe -m ruff check app scripts tests` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app scripts tests` -> success
## 2026-02-27 (update-5) - Packaging and repo-hygiene update

### Resolved
- `.gitignore`
  - Symptom: local artifacts (coverage/cache/tmp/sqlite/log files) polluted working tree.
  - Fix: expanded ignore patterns to common Python + project-specific runtime/build artifacts.
- `.pre-commit-config.yaml`
  - Symptom: outdated/limited hook set.
  - Fix: added base quality hooks, updated Ruff hooks, expanded mypy coverage, and added compileall hook.
- `scripts/build_windows.ps1`, `scripts/verify_exe.ps1`, `scripts/build_exe.bat`
  - Symptom: limited diagnostics and weak packaging feedback.
  - Fix: added prerequisite checks, cleaner logging, post-build verify, and release metadata output.
- `scripts/installer.nsi`, `scripts/build_installer_nsis.ps1`, `scripts/build_nsis.bat`
  - Symptom: installer flow had minimal metadata/UX and weak preflight checks.
  - Fix: added components, metadata/registry info, better shortcut handling, and robust build validation with version injection.
- `scripts/installer.iss`, `scripts/build_installer.ps1`
  - Symptom: weak feedback and static packaging metadata.
  - Fix: aligned with release metadata and robust parameterized build invocation.
- `docs/build_release.md`
  - Symptom: outdated/garbled guidance.
  - Fix: replaced with clean step-by-step release instructions.

### Verification
- `venv\\Scripts\\python.exe -m pre_commit validate-config` -> passed
- `venv\\Scripts\\python.exe -m ruff check app scripts tests` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app scripts tests` -> success
## 2026-02-27 (update-6) - main.py Pylance warning cleanup

### Resolved
- `app/main.py`
  - Symptom: `reportUnnecessaryIsInstance` on `isinstance(..., int)` in `_TeeStream.write` and `_TeeStream.fileno`.
  - Root cause: stream list is typed as `TextIOBase`, so return types are already `int` for these operations.
  - Fix: removed redundant runtime type checks and kept behavior unchanged.

### Verification
- `venv\\Scripts\\python.exe -m pyright app/main.py` -> 0 errors
- `venv\\Scripts\\python.exe -m ruff check app/main.py` -> passed

## 2026-02-27 (update-7) - pyright config hardening

### Resolved
- `pyrightconfig.json`
  - Symptom: `reportUnnecessaryIsInstance` was not explicitly enforced globally by config.
  - Fix: added `"reportUnnecessaryIsInstance": "error"` to make this class of issue fail-fast during static checks.

### Verification
- `venv\\Scripts\\python.exe -m pyright app tests` -> 0 errors

## 2026-02-27 (update-8) - pyright in pre-commit and CI

### Resolved
- `.pre-commit-config.yaml`
  - Symptom: pyright was not guaranteed in pre-commit flow, and initial system hook failed due missing module in hook runtime.
  - Fix: added dedicated `pyright` hook with `language: python` + `additional_dependencies: [pyright>=1.1.390]`.
- `.github/workflows/quality-gates.yml`
  - Symptom: CI did not run pyright explicitly.
  - Fix: added separate `Pyright` step.
- `scripts/quality_gates.ps1`
  - Symptom: local quality gate set differed from CI after pyright hardening.
  - Fix: added `-m pyright` invocation.
- `requirements-dev.txt`
  - Fix: added `pyright>=1.1.390`.

### Verification
- `venv\\Scripts\\python.exe -m pre_commit validate-config` -> passed
- `venv\\Scripts\\python.exe -m pre_commit run --files .pre-commit-config.yaml .github/workflows/quality-gates.yml` -> passed
- `venv\\Scripts\\python.exe -m pyright` -> 0 errors

## 2026-02-27 (update-9) - references action buttons layout

### Resolved
- `app/ui/references/reference_view.py`
  - Symptom: action buttons (`Добавить/Сохранить/Удалить`) looked visually mispositioned; action bar area could stretch and look oversized.
  - Fix: grouped actions into left (`Добавить/Сохранить`) and right (`Удалить/Очистить`) clusters, fixed vertical size policy for action bar, and anchored action zone with layout stretch.

### Verification
- `venv\\Scripts\\python.exe -m ruff check app/ui/references/reference_view.py` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/references/reference_view.py` -> success

## 2026-02-27 (update-10) - remove demo login controls

### Resolved
- `app/ui/login_dialog.py`
  - Symptom: presence of transferred demo controls (`Подставить demo`, test credentials hint) from Test_UI.
  - Fix: removed demo hint label, demo button, and `_fill_demo` helper.

### Verification
- `rg -n -i "demo|admin1234|подставить|для теста|fill_demo" app tests` -> no matches
- `venv\\Scripts\\python.exe -m ruff check app/ui/login_dialog.py` -> passed
- `venv\\Scripts\\python.exe -m mypy --no-incremental app/ui/login_dialog.py` -> success
- `venv\\Scripts\\python.exe -m pyright app/ui/login_dialog.py` -> 0 errors
