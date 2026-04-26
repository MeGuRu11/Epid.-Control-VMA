# Сессия 2026-04-26 — исправление responsive-раскладки администрирования

## Что сделано

- Исправлен баг вкладки `Администрирование`: при первом широком запуске страница больше не должна оставаться в вертикальной раскладке, рассчитанной до появления реальной ширины `QScrollArea/QTabWidget`.
- Для `UserAdminView` добавлен отложенный responsive-пересчёт через `QTimer.singleShot(0, ...)` после построения UI, первого `showEvent`, resize самого виджета, resize вкладок и resize content-контейнера.
- Общий пересчёт action-bar и двухколоночной/вертикальной раскладки вынесен в `_update_responsive_layouts()`.
- Добавлены regression-тесты: широкий первый показ сразу включает `LeftToRight`, а переход из узкого окна в широкое пересчитывает раскладку обратно в две колонки.

## Что не закончено / в процессе

- Ручной GUI smoke пользователем ещё нужен: открыть приложение сразу в широком окне, перейти в `Администрирование`, затем уменьшить и снова развернуть окно.
- БД, миграции, сервисные контракты и бизнес-логика не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Проверить в реальном окне приложения, что вкладка `Администрирование` после нового запуска сразу отображает список пользователей слева и карточки справа.
2. Проверить resize-сценарий: уменьшить окно до вертикальной раскладки и снова развернуть, чтобы убедиться, что двухколоночная раскладка восстанавливается.

## Ключевые файлы, которые менялись

- `app/ui/admin/user_admin_view.py`
- `tests/unit/test_audit_ui_regressions.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_audit_ui_regressions.py -k "user_admin_view_uses_two_columns or user_admin_view_recalculates_layout or user_admin_view_creates_expected_tabs"` — pass (`3 passed`).
- `python -m pytest -q tests/unit/test_audit_ui_regressions.py -k user_admin_view` — pass (`11 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`295 source files`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m pytest -q` — pass (`401 passed`).

# Сессия 2026-04-25 — выравнивание кнопки выхода в строке навигации

## Что сделано

- Кнопка `Выйти` выровнена в один ряд с пунктами верхней навигационной панели: правый corner-контейнер теперь имеет высоту самой кнопки, а не всей панели.
- Убрано визуальное ощущение отдельного правого блока: `logoutCorner` сделан прозрачным и без собственной нижней границы.
- Для `logoutButton` добавлена постоянная тёмно-красная обводка через токен `danger_pressed`.
- Hover оставлен мягким красным фоном `error_bg`, при этом обводка остаётся темнее фона выделения.
- Обновлены regression-тесты геометрии `NavMenuBar` и QSS-тесты для logout-стиля.

## Что не закончено / в процессе

- Ручной GUI smoke пользователем ещё нужен: визуально проверить кнопку `Выйти` на фактическом окне приложения при текущем масштабе Windows.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Открыть приложение и проверить, что `Выйти` находится на одной линии с `Главная`, `ЭМЗ`, `Поиск и ЭМК` и не перекрывает блок ниже.
2. Навести курсор на `Выйти` и проверить, что фон становится мягко-красным, а обводка остаётся более тёмной.

## Ключевые файлы, которые менялись

- `app/ui/main_window.py`
- `app/ui/theme.py`
- `tests/unit/test_main_window_ui_shell.py`
- `tests/unit/test_ui_theme_tokens.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_main_window_ui_shell.py -k logout` — pass.
- `python -m pytest -q tests/unit/test_ui_theme_tokens.py -k logout` — pass.
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`295 source files`).
- `python -m pytest -q` — pass (`399 passed`).
- `python -m compileall -q app tests scripts` — pass.

# Сессия 2026-04-25 — детализация медпомощи Ф-100

## Что сделано

- В разделе 3 мастера Ф-100 `Мед. помощь` добавлены текстовые поля для пунктов, которые раньше были только чекбоксами: ПСС, ПГС, переливание крови, кровезаменители, иммобилизация и перевязка.
- Добавлен отдельный пункт `Оперативное вмешательство` с текстовым описанием.
- Синхронизированы мастер Ф-100, полный редактор, legacy `Form100MainWidget`, итоговый обзор, payload-сервис и PDF-экспорт.
- Старый ключ `mp_serum_dose` сохранён как fallback для обратной совместимости со старыми карточками.
- Добавлены regression-тесты для шага медпомощи, editor payload/load, wizard mapping и PDF-экспорта.
- БД, Alembic-миграции, domain-схема и бизнес-схема не менялись: новые данные сохраняются в существующий JSON payload карточки Ф-100.

## Что не закончено / в процессе

- Ручной GUI smoke пользователем ещё нужен: открыть мастер Ф-100, шаг 3 `Мед. помощь`, визуально проверить расположение новых текстовых строк и сохранение значений через обычный пользовательский сценарий.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Вручную создать или открыть карточку Ф-100 и проверить, что новые поля раздела `Мед. помощь` сохраняются, повторно загружаются и попадают в PDF.
2. Если визуальная плотность раздела 3 окажется неудобной, отдельной задачей уплотнить layout без изменения payload-ключей.

## Ключевые файлы, которые менялись

- `docs/specs/SPEC_form100_medical_help_details.md`
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_medical.py`
- `app/ui/form100_v2/form100_editor.py`
- `app/ui/form100_v2/wizard_widgets/form100_main_widget.py`
- `app/ui/form100_v2/form100_wizard.py`
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`
- `app/application/services/form100_payload_service.py`
- `app/infrastructure/reporting/form100_pdf_report_v2.py`
- `tests/unit/test_form100_v2_step_medical.py`
- `tests/unit/test_form100_v2_wizard_mapping.py`
- `tests/unit/test_form100_v2_editor_fields.py`
- `tests/unit/test_form100_pdf_report_v2.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_form100_v2_step_medical.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_pdf_report_v2.py tests/unit/test_form100_v2_rules.py tests/integration/test_form100_v2_service.py` — pass (`17 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`295 source files`).
- `python -m pytest -q` — pass (`399 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python scripts/check_mojibake.py` — pass.
- `python scripts/check_architecture.py` — pass.
- `git diff --check` — pass, только предупреждения Git о CRLF для уже затронутых файлов.

# Сессия 2026-04-25 — стабилизация logout-кнопки и popup антибиотиков

## Что сделано

- По повторной пользовательской проверке исправлена кнопка `Выйти`: ручное позиционирование заменено на `QMenuBar.setCornerWidget(...)` с отдельным контейнером.
- Кнопка `Выйти` больше не должна перекрывать нижний блок панели; её высота уменьшена до `28px`, а вертикальное выравнивание теперь выполняет Qt layout.
- Контейнер `logoutCorner` получил фон как у `QMenuBar`, а сама кнопка переведена в навигационный стиль без отдельной белой площадки.
- Hover кнопки `Выйти` теперь подсвечивается красным тоном, а не белым.
- Для антибиотиков в ЭМЗ прежний подход с принудительным изменением внешней геометрии нативного popup заменён на `LimitedPopupComboBox`.
- Новый popup антибиотиков использует `QFrame + QListView`, открывается от текущей ячейки, имеет высоту `216px` и сохраняет прокрутку через `QListView`.
- Wheel-события явно маршрутизируются в `AntibioticPopupListView`, чтобы колесо мыши прокручивало список, а не внешний экран ЭМЗ.
- На время открытого popup ставится глобальный event-filter, который ловит wheel-события даже если Qt отдаёт их внешнему скроллу формы.
- Для нового popup добавлены QSS-селекторы `abxComboPopup` и `abxComboPopupView`, чтобы сохранить проектный вид и цвет выбранной строки.
- Программная проверка геометрии показала popup `380x216`, позицию ровно под combo и активный scroll bar.

## Что не закончено / в процессе

- Ручной GUI smoke пользователем ещё нужен: визуально проверить кнопку `Выйти` и список антибиотиков в реальном окне приложения.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Открыть ЭМЗ, раскрыть антибиотик в таблице `Антибиотики`, проверить позицию popup и прокрутку колесом.
2. Проверить кнопку `Выйти` на широкой и средней ширине окна.

## Ключевые файлы, которые менялись

- `app/ui/main_window.py`
- `app/ui/emz/form_widget_factories.py`
- `app/ui/theme.py`
- `tests/unit/test_main_window_ui_shell.py`
- `tests/unit/test_emz_form_widget_factories.py`
- `tests/unit/test_ui_theme_tokens.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_emz_form_widget_factories.py tests/unit/test_main_window_ui_shell.py tests/unit/test_ui_theme_tokens.py -k "abx or real_popup or logout or antibiotic_popup"` — pass (`5 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`294 source files`).
- `python -m pytest -q` — pass (`396 passed`).
- `python -m compileall -q app tests scripts` — pass.

# Сессия 2026-04-25 — выравнивание выхода и popup антибиотиков

## Что сделано

- Завершена доработка logout-редизайна: оставшиеся literal-цвета в новых QSS-селекторах заменены на токен `error_fg`.
- Верхняя кнопка `Выйти` в `NavMenuBar` выровнена ровно по центру панели: фиксированная высота `30`, правый отступ `12`, корректная резервируемая ширина.
- Исправлена корневая причина большого popup антибиотиков в ЭМЗ: прежнее ограничение влияло на внутренний `view()`, но внешний popup-контейнер Qt оставался высоким.
- Добавлен `LimitedPopupComboBox`, который после `showPopup()` ограничивает внешний popup-контейнер и убирает большие пустые зоны.
- Добавлены regression-тесты на высоту реального popup-контейнера и позиционирование кнопки `Выйти`.

## Что не закончено / в процессе

- Ручной визуальный GUI smoke в запущенном приложении не выполнялся; поведение проверено unit/regression tests.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Вручную открыть ЭМЗ и проверить, что popup антибиотиков больше не рисует высокие пустые зоны.
2. Вручную проверить верхнюю кнопку `Выйти` в широком окне приложения и при изменении ширины окна.

## Ключевые файлы, которые менялись

- `app/ui/main_window.py`
- `app/ui/theme.py`
- `app/ui/emz/form_widget_factories.py`
- `tests/unit/test_main_window_ui_shell.py`
- `tests/unit/test_emz_form_widget_factories.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_emz_form_widget_factories.py -k "abx or real_popup"` — pass (`2 passed`).
- `python -m pytest -q tests/unit/test_main_window_ui_shell.py -k logout` — pass (`1 passed`).
- `python -m pytest -q tests/unit/test_emz_form_widget_factories.py tests/unit/test_main_window_ui_shell.py tests/unit/test_logout_dialog.py tests/unit/test_ui_theme_tokens.py -k "abx or logout or nav_menu"` — pass (`6 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`294 source files`).
- `python -m pytest -q` — pass (`395 passed`).
- `python -m compileall -q app tests scripts` — pass.

# Сессия 2026-04-25 — редизайн подтверждения выхода из системы

## Что сделано

- Подтверждение выхода из системы заменено с ручного `QMessageBox` на отдельный `LogoutConfirmDialog`.
- Диалог получил спокойную проектную композицию: заголовок `Завершить сеанс?`, пояснение, круглый индикатор, кнопки `Остаться` и `Выйти`.
- Кнопка `Остаться` сделана default, чтобы случайный Enter не завершал сессию.
- Верхняя кнопка `Выйти` в `MainWindow` получила более аккуратный pill-style через `logoutButton`.
- В `app/ui/theme.py` добавлены QSS-селекторы для `logoutConfirmDialog`, кнопок диалога и интерактивных состояний кнопки выхода.
- Добавлены unit-тесты для диалога, `_logout()` и QSS-селекторов темы.

## Что не закончено / в процессе

- Ручной визуальный GUI smoke в запущенном приложении не выполнялся; поведение и наличие QSS hooks проверены автотестами.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Вручную нажать `Выйти` в запущенном приложении и проверить внешний вид нового подтверждения.
2. Если визуально нужно сделать кнопку `Выйти` менее красной или более компактной, скорректировать только QSS-селекторы в `app/ui/theme.py`.

## Ключевые файлы, которые менялись

- `app/ui/widgets/logout_dialog.py`
- `app/ui/main_window.py`
- `app/ui/theme.py`
- `tests/unit/test_logout_dialog.py`
- `tests/unit/test_main_window_context_selection.py`
- `tests/unit/test_ui_theme_tokens.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_logout_dialog.py tests/unit/test_main_window_context_selection.py -k logout tests/unit/test_ui_theme_tokens.py -k logout` — pass (`4 passed`).
- `python -m pytest -q tests/unit/test_main_window_ui_shell.py tests/unit/test_ui_theme_tokens.py` — pass (`8 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`294 source files`).
- `python -m pytest -q` — pass (`393 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-25 — уменьшение выпадающего списка антибиотиков в ЭМЗ

## Что сделано

- В таблице `Антибиотики` на форме ЭМЗ ограничена высота выпадающего списка антибиотиков.
- `create_abx_combo()` теперь задаёт `setMaxVisibleItems(4)` и `view().setMaximumHeight(144)`, поэтому список раскрывается заметно компактнее и не занимает большую часть экрана.
- Добавлен regression-тест для фабрики combo антибиотиков.

## Что не закончено / в процессе

- Ручной GUI smoke в запущенном приложении не выполнялся; поведение проверено unit-тестами и общим quality gate.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Вручную открыть ЭМЗ, раскрыть список антибиотиков в таблице `Антибиотики` и проверить комфортную высоту popup.
2. Если визуально 4 строки всё ещё много или мало, скорректировать `ABX_COMBO_MAX_VISIBLE_ITEMS` и `ABX_COMBO_POPUP_MAX_HEIGHT`.

## Ключевые файлы, которые менялись

- `app/ui/emz/form_widget_factories.py`
- `tests/unit/test_emz_form_widget_factories.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_emz_form_widget_factories.py` — pass (`8 passed`).
- `python -m pytest -q tests/unit/test_emz_form_widget_factories.py tests/unit/test_emz_form_table_setups.py tests/unit/test_emz_form_table_appliers.py tests/unit/test_emz_form_table_actions.py` — pass (`24 passed`).
- `python -m pytest -q tests/unit/test_emz_form_orchestrators.py tests/unit/test_emz_form_reference_orchestrators.py tests/unit/test_emz_form_request_builders.py` — pass (`18 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`292 source files`).
- `python -m pytest -q` — pass (`389 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-25 — варианты эвакуации корешка Формы 100

## Что сделано

- В корешке Формы 100 оставлены два варианта эвакуации: `Самолётом` и `Сан. груз. авто.`.
- `Form100StubWidget` больше не показывает отдельные кнопки `Санг.` и `Грузавто`; старое сохранённое значение `truck` при загрузке выбирает `Сан. груз. авто.`.
- `Form100EditorV2` синхронизирован с тем же набором значений, чтобы мастер и редактор карточки не расходились.
- Добавлены regression-тесты на два варианта эвакуации и обратную совместимость старого значения `truck`.

## Что не закончено / в процессе

- Визуальный GUI smoke в запущенном приложении не выполнялся; поведение проверено unit-тестами виджетов.
- БД, миграции, domain, infrastructure и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущих задач и сторонний untracked каталог `.npm-cache/`; они не относятся к этой правке и не трогались.

## Следующие шаги

1. Вручную открыть мастер Формы 100 и проверить, что в блоке `Эвакуация (корешок)` отображаются только `Самолётом` и `Сан. груз. авто.`.
2. Если внешний вид подтверждён, можно сделать отдельный commit для этой правки.

## Ключевые файлы, которые менялись

- `app/ui/form100_v2/wizard_widgets/form100_stub_widget.py`
- `app/ui/form100_v2/form100_editor.py`
- `tests/unit/test_form100_v2_step_evacuation.py`
- `tests/unit/test_form100_v2_editor_fields.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_form100_v2_step_evacuation.py` — pass (`3 passed`).
- `python -m pytest -q tests/unit/test_form100_v2_editor_fields.py` — pass (`2 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`292 source files`).
- `python -m pytest -q` — pass (`389 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-25 — редизайн страницы «Администрирование»

## Что сделано

- Создана спецификация `docs/specs/SPEC_admin_view_redesign.md`.
- `UserAdminView` перестроен на вкладки `Пользователи`, `Аудит`, `Резервные копии`.
- Вкладка `Пользователи` реализована как master-detail: поиск и таблица пользователей слева, карточка выбранного пользователя и форма создания справа.
- Выбранный пользователь хранится в `Qt.UserRole`, а действия `Сбросить пароль`, `Активировать`, `Деактивировать` включаются только при валидном выборе.
- Добавлено подтверждение деактивации пользователя через `exec_message_box` с default `No`.
- Вкладка `Аудит` получила явный empty state, вкладка `Резервные копии` сохранила существующие create/restore действия и busy/role policy.
- Добавлены QSS-правила для admin hero/card/tab/badge элементов в `app/ui/theme.py`.
- Исправлен фон текстового блока в hero админки: `adminHeroTextBlock` сделан прозрачным, чтобы за заголовком не было отдельной подложки.
- Обновлено `docs/user_guide.md`.

## Что не закончено / в процессе

- Ручной GUI smoke новой админки на реальной тестовой БД не выполнялся в этой сессии.
- БД, Alembic migrations, роли, сервисные контракты и бизнес-схема не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаются незакоммиченные изменения предыдущей задачи по ЭМЗ/Form100 и сторонний untracked каталог `.npm-cache/`; они не относятся к редизайну админки и не трогались.
- Git продолжает выводить предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на проверки проекта это не влияло.

## Следующие шаги

1. Визуально проверить вкладки `Пользователи`, `Аудит`, `Резервные копии` в запущенном приложении на безопасной тестовой БД.
2. Если внешний вид master-detail устраивает, сделать отдельный commit для редизайна админки вместе с новой спецификацией и тестами.
3. Security/encryption задачи по backup/export не затрагивать до отдельного разрешения пользователя.

## Ключевые файлы, которые менялись

- `docs/specs/SPEC_admin_view_redesign.md`
- `app/ui/admin/user_admin_view.py`
- `app/ui/theme.py`
- `tests/unit/test_audit_ui_regressions.py`
- `docs/user_guide.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_audit_ui_regressions.py tests/unit/test_user_admin_password_policy.py` — pass (`21 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`292 source files`).
- `python -m pytest -q` — pass (`388 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-24 — редактирование ЭМЗ из ЭМК и экспорт PDF Формы 100

## Что сделано

- Спецификация заменена на `docs/specs/SPEC_patient_emk_emz_edit_and_form100_export.md`.
- Из диалога редактирования из `Поиск и ЭМК` убраны вкладки `Пациент` и `Форма 100`.
- `PatientFullEditDialog` теперь показывает только `EmzForm` в `edit_mode=True`; встроенная Форма 100 больше не открывается внутри этого диалога.
- Если ЭМЗ была сохранена, закрытие диалога через кнопку или крестик возвращает `Accepted`, чтобы `MainWindow` обновил контекст.
- Кнопка в карточке пациента переименована в `Редактировать ЭМЗ`.
- `PatientEmkView._open_edit_patient()` передаёт выбранную ЭМЗ, fallback на последнюю ЭМЗ, а если госпитализаций нет — показывает warning и не открывает диалог.
- `MainWindow._open_patient_edit_dialog(patient_id, emr_case_id=None)` защищён от открытия без ЭМЗ.
- В `Form100ListPanel` добавлена кнопка `Экспорт PDF` для выбранной карточки Формы 100; экспорт идёт через существующий `Form100ServiceV2.export_pdf(...)`.
- Добавлены/обновлены unit/regression tests для ЭМК callback, ЭМЗ-диалога, PDF-экспорта Формы 100 и вызова из `MainWindow`.

## Что не закончено / в процессе

- БД, Alembic migrations и бизнес-схема не менялись.
- Изменения по эвакуации не реализовывались: новые I/II/III кружочки, новые варианты транспорта и поля корешка не добавлялись.
- Security/encryption вопросы не затрагивались.

## Открытые проблемы / блокеры

- В рабочем дереве остаётся сторонний untracked каталог `.npm-cache/`; он не относится к задаче и не трогался.
- Git продолжает выводить предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на проверки проекта это не повлияло.

## Следующие шаги

1. Вручную проверить GUI на тестовой БД: выбрать пациента в `Поиск и ЭМК`, нажать `Редактировать ЭМЗ`, убедиться, что открыт только экран ЭМЗ.
2. В `Форма 100` из ЭМК создать карточку через мастер, выбрать её в списке и проверить `Экспорт PDF`.
3. После пользовательской проверки можно сделать commit с сообщением `fix: упрощено редактирование ЭМЗ и добавлен экспорт Формы 100`.

## Ключевые файлы, которые менялись

- `docs/specs/SPEC_patient_emk_emz_edit_and_form100_export.md`
- `app/ui/patient/patient_edit_dialog.py`
- `app/ui/patient/patient_full_edit_dialog.py`
- `app/ui/patient/patient_emk_view.py`
- `app/ui/main_window.py`
- `app/ui/form100_v2/form100_list_panel.py`
- `app/ui/form100_v2/form100_view.py`
- `tests/unit/test_patient_full_edit_dialog.py`
- `tests/unit/test_form100_view_fixed_context.py`
- `tests/unit/test_form100_v2_list_panel_filters.py`
- `tests/unit/test_audit_ui_regressions.py`
- `tests/unit/test_main_window_context_selection.py`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_patient_full_edit_dialog.py tests/unit/test_audit_ui_regressions.py tests/unit/test_main_window_context_selection.py tests/unit/test_form100_v2_list_panel_filters.py` — pass (`19 passed`).
- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`292 source files`).
- `python -m pytest -q tests/unit/test_form100_v2_editor_fields.py tests/unit/test_form100_v2_wizard_mapping.py tests/unit/test_form100_v2_step_evacuation.py tests/integration/test_form100_v2_service.py` — pass (`10 passed`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m pytest -q` — pass (`380 passed`).

# Сессия 2026-04-24 — очистка устаревших docs-файлов

## Что сделано

- По запросу пользователя выполнена локальная очистка Markdown-документации в `docs/` без изменений кода приложения, БД, миграций, UI и бизнес-логики.
- Удалены явные устаревшие кандидаты:
  - `docs/final_audit_report.md`;
  - `docs/full_audit_report.md`;
  - `docs/code_review_gpt54.md`;
  - `docs/code_review_report.md`;
  - `docs/code_audit_findings.md`;
  - `docs/MASTER_TZ_CODEX.md`.
- Создан каталог `docs/archive/`.
- В архив перенесены документы, которые лучше сохранить как исторический контекст:
  - `docs/archive/security_review_2026-04-07.md`;
  - `docs/archive/forma_100_section.md`;
  - `docs/archive/TTZ_Form100_Module_Adapted_v2_2.md`;
  - `docs/archive/full_system_audit.md`.
- `.npm-cache/` не трогался.

## Что не закончено / в процессе

- Решение по архивированию task-файлов в `docs/codex/tasks/` не принималось; они оставлены на месте.
- Security-тема и `AUD-001` по-прежнему отложены до отдельного разрешения пользователя.

## Открытые проблемы / блокеры

- В исторических записях `docs/progress_report.md` и старых handoff-блоках остаются ссылки на удалённые/перенесённые файлы как часть истории проекта. Они не переписывались.
- Git по-прежнему выводит предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на файловые операции это не повлияло.

## Следующие шаги

1. Проверить, нужно ли архивировать завершённые `docs/codex/tasks/*.md`.
2. При необходимости добавить короткий `README` в `docs/archive/`, если архив будет расти.
3. После подтверждения пользователя можно сделать отдельный docs-коммит.

## Ключевые файлы, которые менялись

- `docs/archive/security_review_2026-04-07.md`
- `docs/archive/forma_100_section.md`
- `docs/archive/TTZ_Form100_Module_Adapted_v2_2.md`
- `docs/archive/full_system_audit.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `rg --files docs -g "*.md"` — pass; архивные файлы видны в `docs/archive/`, удалённые файлы отсутствуют в корне `docs/`.
- `git status --short` — pass; показывает удаления, новый `docs/archive/` и сторонний `.npm-cache/`.
- `rg` по старым путям — pass; оставшиеся совпадения находятся в исторических записях или внутри архивного `full_system_audit.md`.

# Сессия 2026-04-24 — внедрение non-security исправлений после аудита

## Что сделано

- Реализован согласованный пакет исправлений по итогам `docs/full_system_audit.md` без блока безопасности: шифрование backup/export, защита от кражи данных и encrypted artifacts намеренно не затрагивались.
- Исправлен `ruff check app tests scripts`: `scripts/codex_task.py` переведён на `collections.abc.Sequence`, `scripts/test_form100_pdf.py` очищен от `E402`, лишних импортов и trailing whitespace.
- В `ImportExportView` исправлены повреждённые fallback-строки: история пакетов теперь показывает корректные русские сообщения и `Неизвестно` вместо mojibake.
- В `ReferenceView` добавлено подтверждение удаления справочников через `exec_message_box` с `Yes/No` и default `No`; при отказе delete-service и `refresh()` не вызываются.
- В `ExchangeService` экспорт CSV/Excel/PDF/legacy JSON переведён с `session.query(...).all()` на chunked-итерацию через `yield_per(500)` без изменения форматов файлов и import paths.
- Добавлены regression/UI tests для fallback labels import/export, подтверждения удаления справочников, first-run, admin user management, patient EMK destructive confirmation, lab sample validation и Form100 wizard smoke mapping.
- Документация синхронизирована с текущей архитектурной политикой: read-model/reporting query services во временном порядке могут использовать SQLAlchemy в application layer; новые write/use-case потоки вести через repositories/service boundaries. Также уточнены текущий не-strict mypy режим, `Column(...)` ORM-стиль и фактический путь миграций `app/infrastructure/db/migrations`.

## Что не закончено / в процессе

- Security finding `AUD-001` не реализовывался по решению пользователя; к шифрованию backup/export и отдельной модели защиты данных нужно вернуться позже отдельной задачей.
- Большой архитектурный рефакторинг Application -> Infrastructure не выполнялся: текущая политика зафиксирована документально, вынос query logic оставлен для отдельного этапа.
- Схема БД и Alembic migrations не менялись.

## Открытые проблемы / блокеры

- В рабочем дереве остаётся сторонний untracked каталог `.npm-cache/`; он не относится к этой задаче и не трогался.
- `docs/full_system_audit.md` остаётся audit-снимком на момент проверки: часть findings в нём исторически описывает проблемы, которые теперь частично закрыты этой итерацией.
- PowerShell/git продолжает выводить предупреждение `unable to access 'C:\Users\user/.config/git/ignore': Permission denied`; на проверки проекта это не повлияло.

## Следующие шаги

1. Отдельно решить, как фиксировать статус закрытых findings в `docs/full_system_audit.md`: оставить как исторический отчёт или добавить раздел статусов внедрения.
2. Вернуться к `AUD-001` только после отдельного разрешения пользователя на security/encryption работу.
3. Если потребуется, постепенно выносить read-model/query SQLAlchemy logic из application layer без массового рефакторинга.

## Ключевые файлы, которые менялись

- `app/application/services/exchange_service.py`
- `app/ui/import_export/import_export_view.py`
- `app/ui/references/reference_view.py`
- `scripts/codex_task.py`
- `scripts/test_form100_pdf.py`
- `tests/integration/test_exchange_service_import_reports.py`
- `tests/unit/test_audit_ui_regressions.py`
- `tests/unit/test_import_export_history_labels.py`
- `tests/unit/test_reference_view_delete_confirmation.py`
- `tests/unit/test_scripts_imports.py`
- `AGENTS.md`
- `docs/context.md`
- `docs/tech_guide.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `ruff check app tests scripts` — pass.
- `python -m mypy app tests` — pass (`289 source files`).
- `python -m pytest -q tests/unit/test_import_export_history_labels.py tests/unit/test_reference_view_delete_confirmation.py tests/unit/test_audit_ui_regressions.py tests/unit/test_scripts_imports.py` — pass (`10 passed`).
- `python -m pytest -q tests/integration/test_exchange_service_import_reports.py::test_exports_include_rows_beyond_single_batch` — pass.
- `python -m pytest -q tests/integration/test_exchange_service_import_reports.py tests/integration/test_exchange_service_import_zip.py` — pass (`12 passed`).
- `python -m pytest -q` — pass (`370 passed`).
- `python -m pytest --cov=app --cov-report=term-missing` — pass (`370 passed`, `TOTAL 65%`).
- `python -m compileall -q app tests scripts` — pass.
- `rg -n "mypy \(strict\)|Mapped\[\]|migrations/" AGENTS.md docs README.md` — pass для актуальных правок; оставшиеся совпадения относятся к историческим audit/report/spec записям или к уточнённой политике.

# Сессия 2026-04-24 — полный audit-only аудит системы

## Что сделано

- Выполнен полный локальный audit-only аудит Epid Control по архитектуре, доменной/медицинской логике, БД/миграциям, тестам, UI, security/privacy, зависимостям, запуску, производительности и документации.
- Создан отчёт: `docs/full_system_audit.md`.
- Работа велась только в локальной директории `C:\Users\user\Desktop\Program\Epid_System_Codex`; GitHub, remote/main и удалённые версии проекта не использовались как источник истины.
- Код приложения, БД, миграции, UI и бизнес-логика не менялись.

## Что не закончено / в процессе

- Интерактивный GUI smoke через `python -m app.main` не выполнялся: для него нужно отдельное разрешение и безопасная временная БД, чтобы не затронуть рабочие данные.
- Сборка `EXE`/инсталляторов не выполнялась: audit-only задача не должна менять `build/`/`dist/`.
- Исправления найденных рисков не применялись, только зафиксированы в отчёте.

## Открытые проблемы / блокеры

- High: backup/export артефакты не шифруются (`app/application/services/backup_service.py:96`, `app/application/services/exchange_service.py:677`).
- Medium: `ruff check app tests scripts` падает на scripts lint (`scripts/codex_task.py`, `scripts/test_form100_pdf.py`).
- Medium: низкое покрытие нескольких критичных UI-файлов при общем coverage `62%`.
- Medium: повреждённые user-facing строки с `?` в `app/ui/import_export/import_export_view.py`.
- Medium: удаление справочников в `ReferenceView` выполняется без подтверждения.

## Следующие шаги

1. Закрыть High-риск: шифрование backup/export и тесты на encrypted artifacts.
2. Исправить `ruff check app tests scripts`.
3. Исправить строки `?` в Import/Export UI и добавить regression check.
4. Добавить подтверждение удаления справочников.
5. Запланировать UI coverage для first-run/admin/patient/lab/Form100/reference flows.

## Ключевые файлы, которые менялись

- `docs/full_system_audit.md`
- `docs/session_handoff.md`
- `docs/progress_report.md`

## Проверки

- `python scripts/check_architecture.py` — pass.
- `python -m alembic current`, `heads`, `history`, `upgrade head`, `check` на `tmp_run\audit-data` — pass.
- `pytest -q` — pass (`359 passed`).
- `pytest -q -ra` — pass (`359 passed`).
- `pytest --collect-only -q` — pass (`359 tests collected`).
- `pytest --cov=app --cov-report=term-missing` — pass (`TOTAL 62%`).
- `ruff check app tests` — pass.
- `ruff check app tests scripts` — fail (`4` lint errors in scripts).
- `mypy app tests` — pass (`285 source files`).
- `python -m compileall -q app tests scripts` — pass.
- `python -m pip check` — pass.
- `python scripts/check_mojibake.py` — pass.

# Сессия 2026-04-24 — обновление Codex-скиллов под GPT-5.5

## Что сделано

- Проведён локальный аудит упоминаний GPT/Codex 5.x без использования GitHub или удалённых репозиториев как источника истины.
- `.agents/skills/codex/SKILL.md` переписан под актуальную политику: основная рекомендуемая модель для Codex-задач — `gpt-5.5`.
- В `codex` skill сохранены локальные operational-правила: sandbox, `--skip-git-repo-check`, resume через stdin, stderr handling через `2>/dev/null`, разрешения для high-impact flags.
- Устаревшие default-инструкции по старым GPT-5.x моделям и неподтверждённые benchmark/pricing-значения удалены; добавлена нейтральная формулировка про официальную документацию OpenAI/Codex.
- `.agents/skills/codex/README.md` обновлён с `gpt-5-codex` на `gpt-5.5` в CLI-примере.
- `.agents/skills/setup-codex-skills/SKILL.md` обновлён: `model = "gpt-5.5"`, CLI-примеры `codex -m gpt-5.5` и `codex exec -m gpt-5.5 ...`, fallback-логика через временный `gpt-5.4`.
- `skills-lock.json` обновлён для локального `setup-codex-skills` по воспроизводимому SHA256 от `SKILL.md`.
- `docs/progress_report.md` дополнен записью о docs/skills-only изменениях.

## Что не закончено / в процессе

- Код приложения, БД, миграции, UI и бизнес-логика не менялись.
- Полный quality gate не запускался, потому что задача была только про документацию и agent skills.

## Открытые проблемы / блокеры

- Для `.agents/skills/codex` запись в `skills-lock.json` имеет `sourceType: github`; текущий `computedHash` уже не совпадал с локальным `SKILL.md` до правок. Без обращения к удалённому источнику алгоритм hash неочевиден, поэтому hash для `codex` не подменялся догадкой и требует ручной проверки при следующей ревизии lock-файла.
- В рабочем дереве остаётся сторонний untracked-каталог `.npm-cache/`; в рамках этой docs/skills-задачи он не трогался.

## Следующие шаги

1. При следующей ревизии skill-lock политики решить, должен ли github-source `codex` skill фиксировать локально изменённый hash или hash upstream-источника.
2. Если `gpt-5.5` не отображается в конкретном окружении пользователя, обновить Codex CLI / приложение / IDE extension и временно использовать `gpt-5.4` только как fallback.
3. Перед следующими кодовыми изменениями вернуться к обычному quality gate циклу проекта.

## Ключевые файлы, которые менялись

- `.agents/skills/codex/SKILL.md`
- `.agents/skills/codex/README.md`
- `.agents/skills/setup-codex-skills/SKILL.md`
- `skills-lock.json`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `rg --hidden --glob "!.git/*" -n -e "gpt-5\\.2" -e "gpt-5\\.3-codex" -e "gpt-5\\.3" -e "gpt-5\\.4" -e "GPT-5\\.2" -e "GPT-5\\.3" -e "GPT-5\\.4" .` — pass; оставшиеся старые упоминания являются fallback или историческими.
- `rg --hidden --glob "!.git/*" -n -e "gpt-5\\.5" -e "GPT-5\\.5" .agents docs AGENTS.md README.md DESIGN.md` — pass.
- `python -m json.tool skills-lock.json` — pass.

# Сессия 2026-04-24 — safe UI token alignment и SQLite migration warning fix

## Что сделано

- В `app/ui/theme.py` добавлен минимальный helper `theme_qcolor(token, alpha=None)` для чтения цветовых токенов из `COL` без нового слоя дизайн-абстракций.
- На theme-токены переведены только безопасные зоны, которые уже дублировали существующую палитру:
  - showcase background у `LoginDialog`;
  - showcase background у `FirstRunDialog`;
  - mint-палитра в `MedicalBackground`;
  - `ClockCard` на главной;
  - highlight активного пункта меню в `MainWindow`;
  - `PatternOverlay`.
- В `app/ui/analytics/charts.py` убран жёстко заданный синий `#4C78A8`; обе диаграммы теперь используют `COL["accent2"]`.
- В `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py` `setObjectName("secondary")` заменён на `secondaryButton` без изменения поведения.
- В миграции `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py` добавлены локальные normalizer-helper’ы для SQLite bind-параметров:
  - `datetime` -> строка;
  - `date` -> ISO-строка;
  - `str` и `None` оставляются как есть.
- Нормализация применена только к `created_at`, `updated_at`, `birth_date`, `signed_at`; JSON-часть миграции не менялась.
- Добавлены и обновлены regression-тесты:
  - `tests/unit/test_analytics_charts.py` — проверка, что charts используют brush из theme token;
  - `tests/unit/test_ui_theme_tokens.py` — проверка `theme_qcolor`;
  - `tests/unit/test_form100_v2_step_evacuation.py` — `secondaryButton` и видимость кнопки подписи только для `DRAFT`;
  - `tests/integration/test_form100_v2_migration.py` — явная проверка отсутствия `DeprecationWarning` по sqlite datetime adapter.

## Что не закончено / в процессе

- Кодовая часть завершена.
- Ручной визуальный smoke новых token-aligned зон в этой сессии не выполнялся.

## Открытые проблемы / блокеры

- Блокеров по коду, тестам и quality gates нет.
- В рабочем дереве остаётся сторонний untracked-каталог `.npm-cache/`; в рамках этой задачи он не трогался.
- `PytestCacheWarning`, связанный с локальным cache-каталогом, остаётся внешней проблемой окружения, а не дефектом приложения.

## Следующие шаги

1. Визуально проверить `LoginDialog` и `FirstRunDialog`, чтобы убедиться, что showcase-фоны не потеряли характер после перевода на theme tokens.
2. Открыть главную и убедиться, что часы и highlight активного меню выглядят контрастно и в пределах текущего стиля.
3. Открыть аналитику и проверить, что mint-столбцы диаграмм визуально читаемы на текущем фоне.
4. При следующей релизной пересборке включить эти зоны в ручной smoke.

## Ключевые файлы, которые менялись

- `app/ui/theme.py`
- `app/ui/analytics/charts.py`
- `app/ui/login_dialog.py`
- `app/ui/first_run_dialog.py`
- `app/ui/home/home_view.py`
- `app/ui/main_window.py`
- `app/ui/widgets/animated_background.py`
- `app/ui/widgets/pattern_overlay.py`
- `app/ui/form100_v2/wizard_widgets/wizard_steps/step_evacuation.py`
- `app/infrastructure/db/migrations/versions/0019_form100_v2_schema.py`
- `tests/unit/test_analytics_charts.py`
- `tests/unit/test_ui_theme_tokens.py`
- `tests/unit/test_form100_v2_step_evacuation.py`
- `tests/integration/test_form100_v2_migration.py`
- `docs/codex/tasks/2026-04-24-безопасные-ui-и-migration-фиксы.md`
- `docs/progress_report.md`
- `docs/session_handoff.md`

## Проверки

- `python -m pytest -q tests/unit/test_analytics_charts.py tests/unit/test_home_view.py tests/unit/test_ui_theme_tokens.py tests/unit/test_form100_v2_step_evacuation.py tests/integration/test_form100_v2_migration.py` — pass (`21 passed in 5.03s`)
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\quality_gates.ps1` — pass
  - `ruff check app tests` — pass
  - `python scripts/check_architecture.py` — pass
  - `mypy app tests` — pass (`285 source files`)
  - `pytest -q` — pass (`359 passed in 47.22s`)
  - `python -m compileall -q app tests scripts` — pass
  - `python -m alembic upgrade head` — pass
  - `python -m alembic check` — pass
  - `python scripts/check_mojibake.py` — pass
