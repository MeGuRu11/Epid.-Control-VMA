# CURRENT: 2026-06-04 - v1.1.0 native verification reconciliation

The current handoff is the first `2026-06-04` section below. Older notes are retained for context.

# Session 2026-06-04 - v1.1.0 native verification reconciliation

## Current State

- Repository: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Task: execute `CODEX_V110_NATIVE_VERIFY.md` final native/non-offscreen verification and artifact reconciliation.
- Production code was not changed in this pass.
- Push/tag were not performed.
- Verification outputs remain intentionally untracked: root `VERIFY_V110_REPORT.md` and `artifacts/verify_v110/`.
- CHANGELOG was not touched.

## Done

- Recreated `artifacts/verify_v110/verify_v110_offscreen.py` with Reports anti-clip assertions and no manual `SearchTab.saved_filter_select.setCurrentIndex(-1)`.
- Added `artifacts/verify_v110/verify_v110_native.py` for native Windows Qt `QWidget.grab()` checks at default scale and `QT_SCALE_FACTOR=1.5`, with blank/monochrome guards.
- Regenerated current verification outputs: 2 verifier scripts, 2 JSON summaries, and 14 PNG screenshots under `artifacts/verify_v110/`.
- Added deterministic Form100 coverage for `ФИО *` bound to `stub_full_name` in `Form100EditorV2`, `Form100StubWidget`, and `StepIdentification`.
- Added B1 regression proving `validate_for_signing` still accepts a previously valid payload without `stub.stub_full_name`; the stub `ФИО *` mark is UI-only.
- Replaced `VERIFY_V110_REPORT.md` so it matches the current artifacts and removes stale claims about old EMK/combo 54 PNGs and `minimumHeight == 132`.

## Checks

- Focused Form100 regression: `python -m pytest tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_signing_error_text.py -q --tb=short` - `15 passed`, `1 warning`.
- `python -m mypy app tests` - pass (`404 source files`).
- `python -m pytest -q --tb=short` - `938 passed`, `3 warnings`.
- `python -m ruff check app tests scripts` - pass.
- `python scripts/check_architecture.py` - pass.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.
- `python artifacts/verify_v110/verify_v110_offscreen.py` - `PASS`; Reports anti-clip wide/narrow and SearchTab `currentIndex=-1`.
- `python artifacts/verify_v110/verify_v110_native.py` - `PASS`; `qt_platform=windows`; Reports wide/narrow nonblank; Form100 StepIdentification nonblank with `ФИО *`.
- `python artifacts/verify_v110/verify_v110_native.py --scale 1.5` - `PASS`; Reports scale 1.5 nonblank and anti-clip.

## Notes

- Native Qt `QWidget.grab()` on platform `windows` is stronger evidence than offscreen rendering, but it is not the user's full manual desktop/DPI workflow. Final visual sign-off remains manual.
- Expected working tree after commits: tracked changes clean, with untracked `VERIFY_V110_REPORT.md` and `artifacts/`.

# Session 2026-06-02 - v1.1.0 final UX fixes добивка

## Current State

- Repository: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Task: execute `CODEX_V110_FINAL_FIXES.md` final v1.1.0 cleanup.
- Implemented and verified locally; push/tag were not performed.
- Verification artifacts remain intentionally untracked: `artifacts/verify_v110/` and root `VERIFY_V110_REPORT.md`.
- CHANGELOG was not touched.

## Done

- Fixed Analytics Reports empty-state clipping root cause: `EmptyState` now recalculates wrapped `QLabel` minimum heights from `heightForWidth()` and updates frame/widget minimum heights from layout `sizeHint()`.
- Added a RED/GREEN anti-clip regression for themed wrapped labels and a ReportsTab wide/narrow anti-clip check.
- Updated `artifacts/verify_v110/verify_v110_offscreen.py` with the same anti-clip assertions, real theme application, no manual `SearchTab.saved_filter_select` reset, and a Form100 stub `ФИО *` check.
- Added `FORM100_SIGNING_REQUIRED_FIELDS` in domain validation, derived UI required marks from it, and guarded signing errors against unknown signing keys.
- Marked Form100 stub `ФИО` as `ФИО *` in both editor and wizard stub widget.
- Added `SearchTab.saved_filter_select` placeholder regression proving `currentIndex() == -1` without manual reset.
- Reviewed B2/B3/B5: no Form100 inline styles; EMK picker extraction deferred as tech debt; QC placeholder remains `Выберите статус QC`.

## Checks

- RED empty-state anti-clip test before fix - failed with `emptyStateText: height=29, needed=88, width=252`.
- RED Form100 source test before fix - failed because `FORM100_SIGNING_REQUIRED_FIELDS` did not exist.
- GREEN targeted: `python -m pytest tests/unit/test_empty_state.py tests/unit/test_form100_signing_error_text.py tests/unit/test_form100_v2_editor_fields.py tests/unit/test_combo_placeholders.py -q --tb=short` - `24 passed`, `1 warning`.
- B2/B3 focused: `python -m pytest tests/unit/test_ui_no_inline_styles.py tests/unit/test_patient_emk_enter_filters.py tests/unit/test_patient_widgets_error_handling.py -q --tb=short` - `9 passed`.
- Native startup: `python -m app.main` without offscreen - process stayed alive after 8 seconds and was stopped; startup crash not detected.
- `python -m mypy app tests` - pass (`404 source files`).
- `python -m pytest -q --tb=short` - `936 passed`, `3 warnings`.
- `python -m ruff check app tests scripts` - pass.
- `python scripts/check_architecture.py` - pass.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.
- `python artifacts/verify_v110/verify_v110_offscreen.py` - `PASS`.

## Notes

- Native Reports tab visual sign-off is still a manual Windows-GUI step. Automation confirmed native app startup and offscreen/themed anti-clip geometry, but did not interactively navigate through the live GUI.
- Full pytest count is now `936 passed`, `3 warnings`.

# Session 2026-06-02 - verify UX fixes v1.1.0 / Form100 required hint

## Current State

- Repository: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Task: verify the four UX fixes from v1.1.0 with programmatic checks and offscreen screenshots from `CODEX_VERIFY_V110.md`.
- A Form100 DoD defect was found and fixed: required `*` marks now have the explanatory hint `Обязательные поля отмечены *.`.
- Verification artifacts are intentionally untracked: `artifacts/verify_v110/` and root `VERIFY_V110_REPORT.md`.
- Push was not performed.

## Done

- Added shared `FORM100_REQUIRED_HINT_TEXT` / `form100_required_hint_label()` in Form100 v2 UI.
- Added the hint to `Form100EditorV2`, Form100 wizard blocks and steps.
- Avoided duplicate hint in `StepIdentification` by making `Form100StubWidget(show_required_hint=False)` when embedded.
- Added regression coverage that checks the hint is present exactly once where required marks are visible.
- Created offscreen verification artifacts under `artifacts/verify_v110/`: verification script, JSON summary and 54 PNG screenshots.

## Checks

- RED targeted hint test before the fix - failed.
- RED targeted exact-one-hint test before duplicate cleanup - failed.
- GREEN targeted: `python -m pytest tests/unit/test_form100_v2_editor_fields.py::test_form100_v2_required_hint_is_shown_where_required_marks_are_visible -q` - `1 passed`.
- Focused Form100 regression: `python -m pytest tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_step_medical.py tests/unit/test_form100_v2_step_evacuation.py tests/integration/test_form100_wizard_birth_date.py -q` - `20 passed`, `1 warning`.
- Offscreen verification: `python artifacts/verify_v110/verify_v110_offscreen.py` - `PASS`.
- `python -m app.main` - started in offscreen mode and was stopped after 8 seconds at expected GUI/login wait; no startup crash.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`404 source files`).
- `python scripts/check_architecture.py` - pass.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.
- `python -m pytest -q --tb=short` - `930 passed`, `3 warnings`.

## Notes

- Offscreen screenshots are useful for layout/text sanity checks, but they are not a native Windows GUI run. Manual Windows-GUI verification remains required for final visual sign-off.
- The final verification report must stay untracked and should be read from `VERIFY_V110_REPORT.md`.

# Session 2026-05-30 - sanitary date filters apply on Enter only

## Current State

- Repository: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Task: make Enter in sanitary date filter `date_to` apply the filter exactly like `date_from`, with reset only through the reset button.
- Commit and push were not performed.
- Required shared helpers were not touched: `app/ui/widgets/date_input_flow.py` and `app/ui/widgets/datetime_inputs.py`.

## Done

- Found that `SanitaryHistoryDialog` and `SanitaryDashboard` still refreshed date filters through `QDateEdit.dateChanged`, so date edits could apply before Enter.
- Removed date-filter application from `dateChanged` for both `date_from` and `date_to`.
- Added explicit Return/Enter event handling for both date fields in both sanitary views.
- The Enter handler commits pending text with `interpretText()` and then applies the existing filter refresh logic.
- Reset remains button-only; default/auto-default button behavior was not restored.
- Added regression coverage proving that changing `date_from` or `date_to` does not refresh filters until Enter is pressed.

## Checks

- RED before the fix: targeted new sanitary Enter-only tests - `2 failed`.
- GREEN targeted: targeted new sanitary Enter-only tests - `2 passed`.
- `python -m pytest tests/unit/test_sanitary_history_dialog.py tests/unit/test_sanitary_dashboard.py -q --tb=short` - `18 passed`.
- `python -m app.main` - started in offscreen mode and was stopped after 8 seconds at expected GUI/login wait; no startup crash.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`398 source files`).
- `python scripts/check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `912 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

# Сессия 2026-06-01 - UX fixes v1.1.0

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Задача: внедрить UX-исправления из `CODEX_UX_FIXES_V110.md`.
- Реализация завершена; full quality gate пройден.
- Push не выполнялся.

## Что сделано

- `PatientEmkView` получил встроенный табличный patient picker по аналогии с Lab: полный список при открытии, локальная фильтрация по ФИО/ID/дате рождения, выбор строки грузит карточку пациента и госпитализации.
- Введён общий helper `set_combo_placeholder()` и переведены combo со служебным `Выбрать`/`Выберите...` на placeholder + `currentIndex(-1)`.
- Обновлены reset/restore-ветки и тесты, где старый selectable-placeholder был частью индексации.
- Для Form100 добавлен `form100_required_label()` на базе `FORM100_SIGNING_FIELD_LABELS`; обязательные для подписи поля помечены `*` в editor и wizard.
- `EmptyState` Analytics увеличен по минимальной высоте до 132px для корректного отображения пустой истории отчётов.
- Добавлены/обновлены regression-тесты для всех четырёх пунктов.

## Проверки

- `python -m app.main` - стартовал в offscreen-режиме и остановлен через 8 секунд на ожидаемом GUI/login wait.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`404 source files`).
- `python scripts/check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `929 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

## Следующие шаги

1. Просмотреть атомарные коммиты по четырём UX-пунктам.
2. При необходимости пройти ручной smoke в реальном GUI по ЭМК, Analytics Reports и Form100 signing flow.

## Open Notes

- Working tree still contains the implemented code/test/doc changes and an existing untracked `docs/QA_CHECKLIST_DATETIME_WIDGET.md`.

# Сессия 2026-05-29 - cleanup docs перед v1.1.0

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Ветка: `main`.
- Задача: инвентаризация и уборка документации перед v1.1.0.
- Коммит и push не выполнялись.
- В рабочей копии до начала cleanup уже были незакоммиченные изменения кода и тестов по date/datetime-вводу; они не трогались.

## Что сделано

- Проведена инвентаризация `docs/` и корневых `README.md` / `CHANGELOG.md`.
- Через `git mv` в `docs/archive/` перенесены исторические планы, S4.6 audit-файлы, закрытые Codex task-файлы и реализованные промежуточные spec-планы.
- Создано оглавление архива: `docs/archive/README.md`.
- Обновлены живые документы:
  - `CHANGELOG.md`;
  - `README.md`;
  - `docs/context.md`;
  - `docs/specs/SPEC_analytics_redesign.md`;
  - `docs/progress_report.md`;
  - `docs/session_handoff.md`.
- Untracked/ignored файлы не перемещались и не добавлялись в git:
  - `docs/QA_CHECKLIST_DATETIME_WIDGET.md`;
  - `docs/sample_exports/*`.

## Проверки

- `python scripts\check_mojibake.py` - pass.
- `git diff --stat` - проверен.
- `git status --short` - проверен; кодовые `.py`-изменения в статусе остались только прежними пользовательскими изменениями.

## Открытые вопросы

- Ручной smoke полей 3/4/S, date/datetime-ввода, сборка `EXE` и инсталлятор остаются следующими release-шагами.
- `docs/QA_CHECKLIST_DATETIME_WIDGET.md` остаётся untracked по явному правилу cleanup-промпта.

## Следующие шаги

1. Пользователю проверить таблицу решений по файлам.
2. После принятия cleanup-решений выполнить commit самостоятельно.
3. Перед тегом v1.1.0 пройти ручной smoke и сборочные проверки.
# Сессия 2026-05-30 - sanitary filters and optional date NULL persistence

## Текущее состояние

- Репозиторий: `C:\Users\user\Desktop\Program\Epid.-Control-VMA`.
- Задача: исправить сброс санитарных фильтров по Enter и проверить/исправить сохранение пустых optional-дат как SQL `NULL`, а не `1900-01-01`.
- Коммит и push не выполнялись.
- До начала работы в репозитории уже были незакоммиченные изменения документации и date/datetime-виджетов; они оставлены без отката.

## Что сделано

- Найдена причина бага Enter: в `SanitaryHistoryDialog` кнопка `Сбросить` становилась default/auto-default кнопкой `QDialog`, поэтому Enter в `QDateEdit` вызывал `_clear_filters()`.
- В `SanitaryHistoryDialog` и `SanitaryDashboard` отключен default/auto-default режим у `QPushButton`-действий, чтобы Enter в фильтрах не запускал кнопки.
- В `Form100EditorV2` и wizard-компонентах пустые optional-даты больше не сериализуются как `01.01.1900`; наружу уходит `""`/`None`.
- В `Form100ServiceV2.update_card()` явное `birth_date=None` теперь очищает дату до SQL `NULL`, а отсутствие поля продолжает сохранять прежнее значение.
- Добавлены регрессионные тесты для санитарного Enter, Form100 editor/wizard, очистки `birth_date`, а также SQL `NULL` для optional-дат EMZ/Lab/Sanitary.

## Проверки

- `python -m app.main` - стартовал в offscreen-режиме и был остановлен через 8 секунд на ожидаемом GUI/login wait; startup crash не обнаружен.
- `python -m pytest tests/integration -q --tb=short` - `162 passed`, `1 warning`.
- `python -m pytest tests/unit/test_sanitary_history_dialog.py tests/unit/test_sanitary_dashboard.py -q --tb=short` - `16 passed`.
- `python -m ruff check app tests scripts` - pass.
- `python -m mypy app tests` - pass (`398 source files`).
- `python scripts\check_architecture.py` - pass.
- `python -m pytest -q --tb=short` - `910 passed`, `3 warnings`.
- `python -m compileall -q app tests scripts` - pass.
- `python scripts\check_mojibake.py` - pass.

## Открытые вопросы

- Ручной smoke в реальном GUI после запуска приложения остается полезным для UX-подтверждения Enter-сценария, но автоматические регрессии покрывают сброс фильтров и SQL `NULL`.
- Следующий шаг перед релизом: собрать/проверить `EXE` и пройти ручные сценарии из release checklist.

---
