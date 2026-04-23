---
name: Epid Control — дизайн-система интерфейса
description: >-
  Лёгкий дизайн-контракт для Codex при работе с PySide6-интерфейсом Epid Control.
  Фиксирует текущую визуальную систему проекта: тёплая светлая палитра, мягкий mint-акцент,
  desktop-first компоновку, единый QSS через app/ui/theme.py и runtime-флаги плотности и анимации.
---

# DESIGN.md

## Токены дизайна

```yaml
colors:
  primary:
    accent_fill: "#8FDCCF"
    accent_soft: "#A1E3D8"
    accent_border: "#6FB9AD"
    accent_pressed: "#76CABC"
    link: "#61C9B6"
  background:
    app: "#F7F2EC"
    menubar: "#EFE6DA"
    surface: "#FFF9F2"
    surface_raised: "#FFFDF8"
  border:
    default: "#E3D9CF"
    soft: "#EDE4D8"
  text:
    primary: "#2F3135"
    default: "#3A3A38"
    muted: "#707070"
    secondary: "#7A7A78"
  status:
    success:
      bg: "#E6F6EA"
      fg: "#2D5A40"
      border: "#9AD8A6"
    warning:
      bg: "#FFF4DB"
      fg: "#6E5525"
      border: "#F4D58D"
    error:
      bg: "#FDE7E5"
      fg: "#7F2F2A"
      border: "#E18A85"
    info:
      bg: "#F2F1EF"
      fg: "#7A7A78"
      border: "#C9C6C1"

typography:
  base:
    family: "Qt default sans-serif"
    size_normal: "12px"
    size_compact: "11px"
  headings:
    page_title:
      size: "22px"
      weight: 800
    section_title:
      size: "16px"
      weight: 700
  meta:
    caption:
      size: "10px"
      weight: 700
    helper:
      size: "11px"
      weight: 600
  table:
    body:
      size: "10px"
      weight: 400
    header:
      size: "10px"
      weight: 700
  display_exceptions:
    login_showcase_title:
      family: "Georgia"
      note: "Использовать только для логина/первого запуска"

spacing:
  values_px:
    xxs: 2
    xs: 4
    sm: 6
    md: 8
    lg: 10
    xl: 12
    "2xl": 14
    "3xl": 16
    "4xl": 18
    "5xl": 24
  common_usage:
    page_padding: [16, 24]
    card_padding: [18, 16]
    action_bar_padding: [12, 8]

radius:
  sm: 4
  md: 6
  lg: 8
  xl: 10
  "2xl": 12
  "3xl": 16
  pill: 9

density:
  env: "EPIDCONTROL_UI_DENSITY"
  default: "normal"
  modes:
    normal:
      base_font: "12px"
      control_padding: "7px 10px"
      button_padding: "6px 10px"
    compact:
      base_font: "11px"
      control_padding: "5px 8px"
      button_padding: "5px 10px"

motion:
  premium_env: "EPIDCONTROL_UI_PREMIUM"
  policy_env: "EPIDCONTROL_UI_ANIMATION"
  default_policy: "adaptive"
  modes:
    minimal:
      animations: false
      animated_background: false
    adaptive:
      animations: "включены, кроме очень маленьких экранов"
      animated_background: "отключается на small/high-DPI экранах"
    full:
      animations: true
      animated_background: true
  timings:
    page_transition_ms: 160
    toast_fade_ms: 180
```

## Правила компонентов

### Buttons

- Основной паттерн — стандартный `QPushButton` на accent-подложке; для вторичных действий используй `secondaryButton`.
- В action bar используй связку `sectionActionBar` + `sectionActionGroup`; если группа может не помещаться по ширине, применяй `update_action_bar_direction(...)` или `ResponsiveActionsPanel`.
- Для коротких рабочих действий используй `compact_button(...)`; типовой минимум в проекте — 96–112 px.
- `loginPrimaryButton`, `loginGhostButton`, `firstRunPrimaryButton`, `firstRunGhostButton` — витринные исключения только для логина и первого запуска.

### Input Fields

- Базовые поля — `QLineEdit`, `QComboBox`, `QDateEdit`, `QTextEdit`, `QSpinBox` под общей темой из `app/ui/theme.py`.
- Стандарт поля: тёплая светлая подложка, радиус 10 px, accent-border в фокусе.
- Не заменяй явную подпись полю одним placeholder: в проекте подпись и helper/meta-текст используются отдельно.
- Ошибки и валидацию показывай через `statusLabel` или `validationBanner`, а не через разовые inline-цвета.

### Dialogs

- Рабочие диалоги должны быть спокойными и системными: 16–24 px внешних отступов, 10–16 px вертикального ритма, локализованные кнопки через `dialog_utils`.
- Диалоги логина и первого запуска — отдельный showcase-паттерн с glass-card и animated background; не переноси его в CRUD-диалоги.
- Если диалог использует стандартные кнопки Qt, локализуй их через `localize_button_box(...)` или соседние helper-функции.

### Tables

- Для данных из БД предпочитай `QTableView + QAbstractTableModel`; `QTableWidget` оставляй для локальных/редактируемых таблиц.
- Таблицы в проекте плотные: тело и header держатся на 10 px, с мягкими границами и alternate-row фоном.
- Для ширины колонок и readonly-ячееек используй `app/ui/widgets/table_utils.py`, а не локальную логику в каждом экране.
- На крупных операционных экранах таблице или списку обычно задаётся явная `minimumHeight`, чтобы layout не "плавал".

### Status Indicators

- Используй уже существующие паттерны: `statusLabel[statusLevel]`, `toast[toastLevel]`, `*StateBadge`, `summaryBadge`, `form100ListBadge`.
- Базовая статусная подача в проекте мягкая: светлая подложка + рамка + тёмный текст, без кислотных плашек.
- Для `Лаборатории` и `Санитарии` сохраняй текущую доменную семантику: положительный результат может сознательно идти в danger/error-палитру, отрицательный — в success.

## Правила использования Codex

- Все новые UI-стили добавляй через `app/ui/theme.py`; `setStyleSheet()` вне `theme.py` запрещён и уже покрыт тестом.
- Сначала переиспользуй `COL`, существующие `objectName` и property-driven selector-ы. Новый `objectName` вводи только если существующий паттерн реально не подходит.
- Держись текущей шкалы отступов: `4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 24`. Не вводи произвольные `13`, `17`, `19`, если соседний шаг решает задачу.
- Для новых поверхностей используй текущую иерархию: app background → surface card → raised inner card → badge/status layer.
- Не вводи новый бренд-цвет, тёмную тему, холодную синюю аналитику или новую гарнитуру для обычных бизнес-экранов.
- Новая motion-логика обязана корректно деградировать при `EPIDCONTROL_UI_PREMIUM=0` и при `EPIDCONTROL_UI_ANIMATION=minimal`.
- Для desktop-layout сначала решай адаптацию через reflow, wrap, collapsible filter/action blocks и разумные `minimumHeight`, а не через fixed absolute geometry.
