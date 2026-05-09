# План работ: Form 100 — три исправления

**Дата:** 2026-05-08
**Статус:** Утверждён пользователем. Готов к исполнению.
**Приоритет:** Три независимых коммита, в порядке возрастания сложности.

---

## Обзор

| # | Проблема | Сложность | Коммит |
|---|----------|:---------:|--------|
| 1 | Переименование раздела и subtitle | XS | `fix: rename Form100 section title` |
| 2 | Дата рождения в визарде создания | S | `feat: add birth_date field to Form100 wizard` |
| 3 | Метки bodymap съезжают в PDF | M | `fix: align bodymap markers in PDF to match UI geometry` |

---

## Quality gate после каждого коммита

```powershell
ruff check app tests
python -m mypy app tests
python -m pytest -q
python -m compileall -q app tests
```

CI запускается на каждый push — все шаги должны быть зелёными.

---

## Коммит 1 — Переименование

### Что менять

Не везде одно и то же название. Ниже точная карта.

#### Группа A — заменить на «Первичные медицинские карточки (ф. 100)»

Это заголовки, видимые пользователю как название раздела/документа:

| Файл | Строка | Было | Стало |
|------|:------:|------|-------|
| `app/ui/form100_v2/form100_list_panel.py` | 174 | `QLabel("Карточки Формы 100")` | `QLabel("Первичные медицинские карточки (ф. 100)")` |
| `app/ui/form100_v2/form100_view.py` | 90 | `QLabel("Форма 100")` | `QLabel("Первичные медицинские карточки (ф. 100)")` |
| `app/ui/form100_v2/form100_wizard.py` | 324 | `QLabel("Форма 100")` | `QLabel("Первичные медицинские карточки (ф. 100)")` |

#### Группа B — subtitle на главном экране

| Файл | Строка | Было | Стало |
|------|:------:|------|-------|
| `app/ui/main_window.py` | 400 | `"Форма 100": "Карточка медицинской эвакуации"` | `"Форма 100": "Учёт первичных карточек ф. 100"` |

#### Группа C — НЕ менять (короткие подписи, внутренние ключи, системные window title)

| Файл | Причина |
|------|---------|
| `app/ui/main_window.py:153` — `"Форма 100": "Ф100"` | Ключ мэппинга |
| `app/ui/main_window.py:166` — `"Форма 100": "100"` | Ключ мэппинга |
| `app/ui/form100_v2/form100_list_panel.py:163` — `setWindowTitle("Форма 100")` | Системный заголовок окна |
| `app/ui/form100_v2/form100_wizard.py:304` — `setWindowTitle(f"Форма 100 — {…}")` | Системный заголовок окна |
| `app/ui/patient/patient_emk_view.py:156` — `QPushButton("Форма 100")` | Короткая кнопка quick-action |
| `app/ui/settings/settings_dialog.py:279` — упоминание Form 100 | Техническая подпись настроек |
| `app/infrastructure/reporting/form100_pdf_report_v2.py:441` — `Paragraph("Форма 100", s_subtitle)` | В PDF уже стоит «ПЕРВИЧНАЯ МЕДИЦИНСКАЯ КАРТОЧКА», подзаголовок «Форма 100» уместен |

### Тест

```python
# tests/unit/test_form100_titles.py

def test_form100_list_panel_label_renamed():
    panel = Form100ListPanel(...)
    assert panel._title_label.text() == "Первичные медицинские карточки (ф. 100)"

def test_form100_view_title_renamed():
    view = Form100View(...)
    assert view._title_label.text() == "Первичные медицинские карточки (ф. 100)"

def test_form100_wizard_header_renamed():
    wizard = Form100Wizard(...)
    assert wizard._header_title_label.text() == "Первичные медицинские карточки (ф. 100)"
```

### Acceptance criteria

- Три заголовка (list_panel, view, wizard header) отображают новое название.
- Subtitle на главном экране: «Учёт первичных карточек ф. 100».
- Все window title, кнопки, внутренние ключи — без изменений.
- `ruff` + `mypy` + `pytest` — зелёные.

---

## Коммит 2 — Дата рождения в визарде

### Анализ текущего состояния

- В DTO (`form100_v2_dto.py`): поле `birth_date: date | None` — **есть**.
- В модели (`form100_v2.py`): поле `birth_date: date | None` — **есть**.
- В редакторе (`form100_editor.py:184–208`): `QDateEdit` с `dd.MM.yyyy` — **есть**.
- В визарде (`form100_wizard.py`) и шаге идентификации (`step_identification.py`): поля нет — **отсутствует**.

При создании карточки через визард `Form100CreateV2Request` строится без `birth_date` (строки 629–637 в wizard.py), поле остаётся `None`.

### Что добавить

#### 1. `step_identification.py` — новый виджет

Добавить после строки с `main_id_tag` (`self.main_id_tag.setPlaceholderText(…)`):

```python
self.birth_date = QDateEdit()
self.birth_date.setDisplayFormat("dd.MM.yyyy")
self.birth_date.setCalendarPopup(True)
self.birth_date.setSpecialValueText("Не указана")
self.birth_date.setMinimumDate(QDate(1900, 1, 1))
self.birth_date.setMaximumDate(QDate.currentDate())
self.birth_date.setDate(self.birth_date.minimumDate())  # по умолчанию = специальное "пустое" значение
```

Добавить в layout после строки `ident_lay.addRow("Жетон №:", self.main_id_tag)`:

```python
ident_lay.addRow("Дата рождения:", self.birth_date)
```

Логика «пустого» значения: специальное значение (`minimumDate = 01.01.1900`) отображается как «Не указана». При сохранении проверять:

```python
def _get_birth_date(self) -> date | None:
    d = self.birth_date.date()
    if d == self.birth_date.minimumDate():
        return None
    return date(d.year(), d.month(), d.day())
```

#### 2. `step_identification.py` — `load_payload()`

Добавить загрузку при открытии существующей карточки:

```python
birth_date_iso = payload.get("birth_date_iso")
if birth_date_iso:
    try:
        d = date.fromisoformat(birth_date_iso)
        self.birth_date.setDate(QDate(d.year, d.month, d.day))
    except ValueError:
        self.birth_date.setDate(self.birth_date.minimumDate())
else:
    self.birth_date.setDate(self.birth_date.minimumDate())
```

#### 3. `step_identification.py` — `collect_payload()`

Добавить в возвращаемый dict:

```python
out["birth_date_iso"] = (
    _get_birth_date().isoformat() if _get_birth_date() else None
)
```

#### 4. `form100_wizard.py` — проброс в request

В функции, строящей `Form100CreateV2Request` и `Form100UpdateV2Request` (строки ~629/642):

```python
# Получить birth_date из payload
birth_date_iso = payload.get("birth_date_iso")
birth_date: date | None = None
if birth_date_iso:
    try:
        birth_date = date.fromisoformat(birth_date_iso)
    except ValueError:
        birth_date = None

request = Form100CreateV2Request(
    ...
    birth_date=birth_date,      # ← добавить
)
```

То же для `Form100UpdateV2Request`.

#### 5. `form100_pdf_report_v2.py` — формат даты рождения

Найти место, где `birth_date` попадает в PDF. Сейчас скорее всего:
```python
card.birth_date.isoformat()   # → "1992-02-02"
```

Заменить на:
```python
card.birth_date.strftime("%d.%m.%Y") if card.birth_date else "—"  # → "02.02.1992"
```

До появления общего `formatters.py` — допустимо использовать `strftime`. Оставить `TODO: заменить на formatters.format_date()` когда formatters будет готов.

#### 6. Добавить `birth_date` в список полей-виджетов для focus chain

В `step_identification.py` где-то строится список виджетов в tab-order (строки ~140-143):
```python
self.main_rank,
self.main_unit,
self.main_full_name,
self.main_id_tag,
self.birth_date,  # ← добавить в конец
```

### Файлы

```
app/ui/form100_v2/wizard_widgets/wizard_steps/step_identification.py   ← основные правки
app/ui/form100_v2/form100_wizard.py                                     ← проброс birth_date в request
app/infrastructure/reporting/form100_pdf_report_v2.py                  ← формат даты
tests/integration/test_form100_wizard_birth_date.py                    ← новый тест
```

### Тесты

```python
# tests/integration/test_form100_wizard_birth_date.py

def test_birth_date_widget_exists_in_wizard(wizard_fixture):
    """Поле QDateEdit видимо в шаге идентификации."""
    step = wizard_fixture._step1  # StepIdentification
    assert hasattr(step, "birth_date")
    assert isinstance(step.birth_date, QDateEdit)

def test_birth_date_empty_by_default(wizard_fixture):
    """По умолчанию дата рождения — «Не указана» (specialValue)."""
    step = wizard_fixture._step1
    assert step._get_birth_date() is None

def test_birth_date_saved_to_card(wizard_fixture, db_session):
    """Введённая дата рождения сохраняется в карточку Form100."""
    step = wizard_fixture._step1
    step.birth_date.setDate(QDate(1985, 6, 15))
    wizard_fixture._save_draft()
    card = db_session.get(Form100, wizard_fixture._card.id)
    assert card.birth_date == date(1985, 6, 15)

def test_birth_date_loaded_from_existing_card(wizard_fixture, card_with_birth_date):
    """При открытии карточки с birth_date поле QDateEdit корректно заполнено."""
    wizard_fixture.load_card(card_with_birth_date)
    step = wizard_fixture._step1
    assert step._get_birth_date() == card_with_birth_date.birth_date

def test_pdf_birth_date_format_is_ddmmyyyy(card_with_birth_date, tmp_path):
    """В PDF дата рождения отображается как 'ДД.ММ.ГГГГ', не ISO."""
    pdf_bytes = generate_form100_pdf(card_with_birth_date)
    text = extract_text_from_pdf(pdf_bytes)
    assert "15.06.1985" in text
    assert "1985-06-15" not in text
```

### Acceptance criteria

- Поле «Дата рождения» видно в мастере, шаг 1 («Идентификация»), после «Жетон №».
- По умолчанию — «Не указана» (не текущая дата).
- При сохранении черновика дата попадает в `form100.birth_date`.
- При повторном открытии карточки дата корректно восстанавливается.
- В PDF: `02.02.1992`, не `1992-02-02`.

---

## Коммит 3 — Bodymap: съезд меток в PDF

### Root cause

**Разные системы координат в UI и PDF.**

**В UI** (`bodymap_widget.py:128–131`) рендеринг изображения идёт в `target_rect` — прямоугольник с отступами внутри слота:

```python
target_rect = QRectF(
    slot.x() + slot.width() * 0.06,   # left: +6% от слота
    slot.y() + slot.height() * 0.03,  # top:  +3% от слота
    slot.width() * 0.88,              # ширина: 88% слота
    slot.height() * 0.94,             # высота: 94% слота
)
```

Нормализованные координаты клика (`nx`, `ny`) записываются **относительно `target_rect`** (строки 168–169). При рисовке маркера они раскрываются обратно относительно `target_rect` (строки 354–355).

**В PDF** (`_build_bodymap_image_flowable`, строки ~239–246) те же `x_norm, y_norm` умножаются на **полный** `panel_width` и `canvas_height`:

```python
x = panel_offset + x_norm * panel_width    # ← полная ширина панели
y = y_norm * canvas_height                  # ← полная высота PNG, отступы не учтены
```

Итог: метка, поставленная в UI на стопе (y_norm ≈ 0.95), в PDF оказывается **ниже силуэта** — в нижнем поле PNG.

### Решение — единый модуль `bodymap_geometry.py`

Выносим ратио в одно место и используем **и в UI, и в PDF**.

#### Шаг 1. Создать `app/domain/services/bodymap_geometry.py`

```python
"""
Единая геометрия bodymap.

Нормализованные координаты (x_norm, y_norm ∈ [0, 1]) задаются относительно
target_rect — рабочей области внутри слота силуэта с фиксированными отступами.

Эти константы должны совпадать с теми, что используются в bodymap_widget.py.
Изменение только здесь — оба места адаптируются автоматически.
"""
from __future__ import annotations

# Отступы target_rect внутри слота (совпадают с bodymap_widget.py)
SLOT_PAD_LEFT   = 0.06   # 6% слева
SLOT_PAD_TOP    = 0.03   # 3% сверху
SLOT_EFFECTIVE_W = 0.88  # 88% ширины слота
SLOT_EFFECTIVE_H = 0.94  # 94% высоты слота


def denormalize_for_pil(
    x_norm: float,
    y_norm: float,
    *,
    panel_width_px: float,
    canvas_height_px: float,
    is_back: bool,
) -> tuple[float, float]:
    """
    Конвертирует нормализованные координаты (из UI) в пиксельные для PIL-рендера.

    x_norm, y_norm — координаты, записанные bodymap_widget.py относительно target_rect.
    Возвращает (x_px, y_px) — пиксельные координаты в системе PIL-canvas.
    """
    panel_offset = panel_width_px if is_back else 0.0

    # Рабочая область target_rect внутри панели в пикселях
    left_px   = panel_offset + panel_width_px * SLOT_PAD_LEFT
    top_px    = canvas_height_px * SLOT_PAD_TOP
    width_px  = panel_width_px  * SLOT_EFFECTIVE_W
    height_px = canvas_height_px * SLOT_EFFECTIVE_H

    x = left_px + x_norm * width_px
    y = top_px  + y_norm * height_px
    return x, y


def denormalize_for_drawing(
    x_norm: float,
    y_norm: float,
    *,
    panel_width_pt: float,
    total_height_pt: float,
    is_back: bool,
) -> tuple[float, float]:
    """
    То же, но для ReportLab Drawing (coordinate origin = bottom-left, Y растёт вверх).
    """
    panel_offset = panel_width_pt if is_back else 0.0

    left_pt   = panel_offset + panel_width_pt * SLOT_PAD_LEFT
    top_pt    = total_height_pt * SLOT_PAD_TOP
    width_pt  = panel_width_pt  * SLOT_EFFECTIVE_W
    height_pt = total_height_pt * SLOT_EFFECTIVE_H

    x = left_pt + x_norm * width_pt
    # ReportLab: Y = 0 снизу, поэтому инвертируем
    y = total_height_pt - (top_pt + y_norm * height_pt)
    return x, y
```

> **Почему не auto-detect по alpha?**
> Auto-detect по alpha возможен, но требует загрузки PIL при инициализации и усложняет
> логику при замене шаблона. Поскольку константы UI (`0.06 / 0.03 / 0.88 / 0.94`) уже
> зафиксированы в `bodymap_widget.py` и полностью соответствуют реальному положению
> силуэта в PNG, достаточно вынести их в общий модуль. Auto-detect оставляем как TODO
> для будущей замены шаблона.

#### Шаг 2. Обновить `bodymap_widget.py` — заменить магические числа на константы

```python
from app.domain.services.bodymap_geometry import (
    SLOT_PAD_LEFT, SLOT_PAD_TOP, SLOT_EFFECTIVE_W, SLOT_EFFECTIVE_H,
)

# Строки 128–131: было hardcode, стало:
target_rect = QRectF(
    slot.x() + slot.width() * SLOT_PAD_LEFT,
    slot.y() + slot.height() * SLOT_PAD_TOP,
    slot.width() * SLOT_EFFECTIVE_W,
    slot.height() * SLOT_EFFECTIVE_H,
)
```

Логика нормализации при клике и рисовки маркеров — без изменений, они уже правильные.

#### Шаг 3. Исправить `form100_pdf_report_v2.py` — PIL путь

Функция `_build_bodymap_image_flowable`, строки ~234–248:

```python
from app.domain.services.bodymap_geometry import denormalize_for_pil

# ... внутри цикла по аннотациям:
is_back = silhouette.endswith("back")
x, y = denormalize_for_pil(
    x_norm, y_norm,
    panel_width_px=panel_width,
    canvas_height_px=canvas_height,
    is_back=is_back,
)
_draw_annotation_marker(draw, annotation_type=ann_type, x=x, y=y, note=…)
```

#### Шаг 4. Исправить `form100_pdf_report_v2.py` — ReportLab Drawing путь

Функция `_render_bodymap_drawing`, строки ~326+:

```python
from app.domain.services.bodymap_geometry import denormalize_for_drawing

# ... внутри цикла по аннотациям:
is_back = "back" in sil
x, y = denormalize_for_drawing(
    x_norm, y_norm,
    panel_width_pt=mid,        # mid = ширина Drawing / 2
    total_height_pt=height_pt,
    is_back=is_back,
)
# далее рисовать маркер через (x, y)
```

#### Шаг 5. Убедиться в согласованности

Написать интеграционный тест, который:
1. Ставит маркер в UI на известные (x_norm, y_norm).
2. Генерирует PDF.
3. Извлекает PNG-рендер страницы bodymap (через pdf2image или pypdfium2).
4. Проверяет, что красный пиксель крестика находится в ожидаемой области.

### Файлы

```
app/domain/services/bodymap_geometry.py                                ← НОВЫЙ
app/ui/form100_v2/wizard_widgets/bodymap_widget.py                    ← заменить magic numbers
app/infrastructure/reporting/form100_pdf_report_v2.py                 ← PIL path + Drawing path
tests/unit/test_bodymap_geometry.py                                    ← НОВЫЙ
tests/integration/test_form100_pdf_bodymap_alignment.py               ← НОВЫЙ
```

### Тесты

```python
# tests/unit/test_bodymap_geometry.py

def test_denormalize_center_front():
    """Центральная точка попадает в середину рабочей области панели."""
    x, y = denormalize_for_pil(0.5, 0.5, panel_width_px=400, canvas_height_px=800, is_back=False)
    # Ожидаемый x: 0 + 400*0.06 + 0.5*(400*0.88) = 24 + 176 = 200
    assert abs(x - 200.0) < 0.5
    # Ожидаемый y: 800*0.03 + 0.5*(800*0.94) = 24 + 376 = 400
    assert abs(y - 400.0) < 0.5

def test_denormalize_top_left_front():
    """(0, 0) → левый верхний угол рабочей области."""
    x, y = denormalize_for_pil(0.0, 0.0, panel_width_px=400, canvas_height_px=800, is_back=False)
    assert abs(x - 400 * 0.06) < 0.5
    assert abs(y - 800 * 0.03) < 0.5

def test_denormalize_bottom_right_back():
    """(1, 1) → нижний правый угол рабочей области задней панели."""
    x, y = denormalize_for_pil(1.0, 1.0, panel_width_px=400, canvas_height_px=800, is_back=True)
    # x: 400 (offset) + 400*0.06 + 1*(400*0.88) = 400 + 24 + 352 = 776
    assert abs(x - 776.0) < 0.5
    # y: 800*0.03 + 1*(800*0.94) = 24 + 752 = 776
    assert abs(y - 776.0) < 0.5

def test_drawing_y_is_inverted_vs_pil():
    """ReportLab Y растёт снизу вверх — должен инвертировать."""
    _, y_pil = denormalize_for_pil(0.5, 0.9, panel_width_px=400, canvas_height_px=800, is_back=False)
    _, y_rl = denormalize_for_drawing(0.5, 0.9, panel_width_pt=400, total_height_pt=800, is_back=False)
    assert y_rl < 800 * 0.5  # нижняя точка → малое Y в ReportLab

def test_constants_match_bodymap_widget():
    """Константы geometry совпадают с тем, что использует bodymap_widget."""
    from app.ui.form100_v2.wizard_widgets.bodymap_widget import (
        SLOT_PAD_LEFT as W_LEFT, SLOT_PAD_TOP as W_TOP,
        SLOT_EFFECTIVE_W as W_W, SLOT_EFFECTIVE_H as W_H,
    )
    assert SLOT_PAD_LEFT   == W_LEFT
    assert SLOT_PAD_TOP    == W_TOP
    assert SLOT_EFFECTIVE_W == W_W
    assert SLOT_EFFECTIVE_H == W_H
```

```python
# tests/integration/test_form100_pdf_bodymap_alignment.py

def test_marker_position_front_foot_in_correct_area(signed_card_with_foot_marker, tmp_path):
    """
    Маркер на стопе (y_norm≈0.95) в PDF должен быть в нижней трети изображения,
    но НЕ ниже boundary 97% высоты.
    """
    pdf_bytes = export_pdf(signed_card_with_foot_marker)
    page_img = rasterize_bodymap_page(pdf_bytes)  # PIL Image
    red_pixels = find_red_pixels(page_img)
    assert len(red_pixels) > 0, "маркер не найден"
    y_max = max(py for _, py in red_pixels)
    assert y_max < page_img.height * 0.97, "маркер ниже силуэта"
    assert y_max > page_img.height * 0.80, "маркер не в нижней зоне"

def test_marker_position_consistent_ui_and_pdf(marker_at_known_coords):
    """
    Нормализованные координаты дают одинаковое положение в UI и PDF.
    Используем denormalize_for_pil напрямую, без рендеринга GUI.
    """
    x_norm, y_norm = 0.5, 0.5
    x_pdf, y_pdf = denormalize_for_pil(
        x_norm, y_norm,
        panel_width_px=400, canvas_height_px=800, is_back=False,
    )
    x_ui_expected = 400 * SLOT_PAD_LEFT + x_norm * 400 * SLOT_EFFECTIVE_W
    y_ui_expected = 800 * SLOT_PAD_TOP  + y_norm * 800 * SLOT_EFFECTIVE_H
    assert abs(x_pdf - x_ui_expected) < 1.0
    assert abs(y_pdf - y_ui_expected) < 1.0
```

### Acceptance criteria

- Маркер на стопе в UI → маркер на стопе силуэта в PDF (не ниже ступней).
- Маркер в центре груди в UI → маркер в центре груди в PDF.
- `bodymap_widget.py` использует константы из `bodymap_geometry.py`, не хардкод.
- `_build_bodymap_image_flowable` и `_render_bodymap_drawing` используют `denormalize_for_*`.
- Все тесты `test_bodymap_geometry.py` проходят.

---

## Итоговый список файлов

```
Изменяются:
  app/ui/form100_v2/form100_list_panel.py               (1: title)
  app/ui/form100_v2/form100_view.py                      (1: title)
  app/ui/form100_v2/form100_wizard.py                    (1: title + 2: birth_date request)
  app/ui/main_window.py                                  (1: subtitle)
  app/ui/form100_v2/wizard_widgets/wizard_steps/step_identification.py  (2: birth_date widget)
  app/ui/form100_v2/wizard_widgets/bodymap_widget.py    (3: magic → constants)
  app/infrastructure/reporting/form100_pdf_report_v2.py (2: date format + 3: bodymap)

Создаются:
  app/domain/services/bodymap_geometry.py               (3: единая геометрия)
  tests/unit/test_form100_titles.py                     (1)
  tests/integration/test_form100_wizard_birth_date.py   (2)
  tests/unit/test_bodymap_geometry.py                   (3)
  tests/integration/test_form100_pdf_bodymap_alignment.py (3)
```

---

## Порядок коммитов и conventional commits

```
Коммит 1:
  git commit -m "fix: rename Form100 section title to Первичные медицинские карточки (ф. 100)"

Коммит 2:
  git commit -m "feat: add birth_date field to Form100 wizard step-identification"

Коммит 3:
  git commit -m "fix: align Form100 PDF bodymap markers to match UI coordinate geometry"
```

---

## Открытые вопросы (решены)

| Вопрос | Решение |
|--------|---------|
| Subtitle на главной | `"Учёт первичных карточек ф. 100"` ✓ |
| Дата рождения: автозаполнение из patient.dob? | Нет, только ручной ввод ✓ |
| Bodymap: auto-detect bbox или константы? | Константы из модуля (auto-detect = TODO) ✓ |
| Документация user_guide/manual_regression | Отдельный проход позже ✓ |
