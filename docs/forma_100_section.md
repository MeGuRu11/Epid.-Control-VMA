# Этап VI — Форма 100 МО РФ (v2.2)
# Раздел для context.md | Задание для AI-агента

> **Статус**: не начат → реализовать полностью.
> **Приоритет**: P1 (обязательный).
> **Стек**: PySide6 (Qt6), SQLAlchemy 2.x, Alembic, ReportLab, SQLite.
> **Цветовая палитра**: строго из раздела 16 context.md (bodymap — раздел 16.5).
> **Архитектура**: UI → Application → Domain → Infrastructure (мини-Clean Architecture).

---

## VI.1 Контекст и требования

Форма 100 («Первичная медицинская карточка», Форма 100 МО РФ) — официальный документ
первичной медицинской документации при боевых потерях. Приложение должно:

- воспроизводить **структуру Формы 100 один в один** (все секции, все поля, все символы);
- позволять **рисовать и отмечать повреждения на схеме тела** (интерактивная bodymap);
- сохранять данные в БД, генерировать PDF-артефакт с SHA256, включать в ZIP-обмен;
- логировать все действия в `audit_log`.

Форма состоит из **трёх физических частей** (корешок + основной бланк + боковые полосы):

| Часть | Цвет полосы на оригинале | Назначение |
|---|---|---|
| Корешок (левый блок) | — | Остаётся в подразделении |
| Основной бланк (центр) | — | Сопровождает раненого |
| Полоса «Неотложная помощь» | Красная | Флаг экстренной помощи |
| Полоса «Радиационное поражение» | Синяя (бирюза) | Флаг радиационного поражения |
| Полоса «Санитарная обработка» | Жёлтая | Флаг санитарной обработки |

---

## VI.2 Полный перечень полей формы

### VI.2.1 Корешок первичной медицинской карточки (левая часть)

| ID поля | Название | Тип виджета | Значения / формат |
|---|---|---|---|
| `stub_issued_time` | Выдана — часы, мин | `QTimeEdit` | ЧЧ:ММ |
| `stub_issued_date` | Выдана — дата | `QDateEdit` | ДД.ММ.ГГГГ |
| `stub_rank` | В/звание | `QLineEdit` | текст |
| `stub_unit` | В/часть | `QLineEdit` | текст |
| `stub_full_name` | Фамилия, имя, отчество | `QLineEdit` | текст |
| `stub_id_tag` | Удостоверение личности, жетон № | `QLineEdit` | текст |
| `stub_injury_time` | Ранен/заболел — час | `QTimeEdit` | ЧЧ:ММ |
| `stub_injury_date` | Ранен/заболел — дата | `QDateEdit` | ДД.ММ.ГГГГ |
| `stub_evacuation_method` | Эвакуирован (подчеркнуть) | `QButtonGroup` (radio) | самолётом / санг. / грузавто |
| `stub_evacuation_dest` | Куда эвакуирован (обвести) | `IconSelectWidget` (3 иконки) | + лежа / ⊕ сидя / ✉ носилки |
| `stub_med_help_underline` | Мед. помощь — подчеркнуть | `QListWidget` (multi-check) | см. список ниже |
| `stub_antibiotic_dose` | Введено антибиотик — доза | `QLineEdit` | текст |
| `stub_pss_pgs_dose` | Сыворотка ПСС, ПГС — доза | `QLineEdit` | текст |
| `stub_toxoid_type` | Анатоксин (какой) | `QLineEdit` | текст |
| `stub_antidote_type` | Антидот (какой) | `QLineEdit` | текст |
| `stub_analgesic_dose` | Обезболивающее средство | `QLineEdit` | текст |
| `stub_transfusion` | Переливание крови / кровезаменителей | `QCheckBox` | да/нет |
| `stub_immobilization` | Иммобилизация, перевязка | `QCheckBox` | да/нет |
| `stub_tourniquet` | Наложен жгут, санобработка | `QCheckBox` | да/нет |
| `stub_diagnosis` | Диагноз | `QTextEdit` (1 строка) | текст |

**Список «подчеркнуть» (мед. помощь) для корешка:**
`Введено: антибиотик`, `Сыворотка ПСС/ПГС`, `Анатоксин`, `Антидот`,
`Обезболивающее средство`, `Произведено: переливание крови, кровезаменителей`,
`Иммобилизация, перевязка`, `Наложен жгут, санобработка`

---

### VI.2.2 Основной бланк — верхний блок (идентификация)

| ID поля | Название | Тип виджета | Значения / формат |
|---|---|---|---|
| `main_issued_place` | Выдана (наименование мед. пункта/учреждения) | `QLineEdit` | текст |
| `main_issued_time` | Выдана — часы, мин | `QTimeEdit` | ЧЧ:ММ |
| `main_issued_date` | Выдана — дата | `QDateEdit` | ДД.ММ.ГГГГ |
| `main_rank` | В/звание | `QLineEdit` | текст |
| `main_unit` | В/часть | `QLineEdit` | текст |
| `main_full_name` | Фамилия, имя, отчество | `QLineEdit` | текст |
| `main_id_tag` | Удостоверение личности, жетон № | `QLineEdit` | текст |
| `main_injury_time` | Ранен/заболел — час | `QTimeEdit` | ЧЧ:ММ |
| `main_injury_date` | Ранен/заболел — дата | `QDateEdit` | ДД.ММ.ГГГГ |

---

### VI.2.3 Основной бланк — секция «Вид поражения» (пиктограммы, вертикальный блок слева)

Реализуется как вертикальный список строк. Каждая строка = пиктограмма + буква + метка.
Пользователь **обводит/отмечает** нужные строки.

| Буква | Метка | ID поля |
|---|---|---|
| О | Огнестрельное (пиктограмма: пистолет) | `lesion_gunshot` |
| Я | Ядерное (пиктограмма: ядерный гриб) | `lesion_nuclear` |
| Х | Химическое (пиктограмма: противогаз/колба) | `lesion_chemical` |
| Бак. | Бактериологическое (пиктограмма: микроб) | `lesion_biological` |
| Другие | Другие поражения (пиктограмма: нож/осколок) | `lesion_other` |
| Отм. | Отморожение (пиктограмма: снежинка) | `lesion_frostbite` |
| Б | Ожог (пиктограмма: огонь/кровать) | `lesion_burn` |
| И | Иное (пиктограмма: человек+знак) | `lesion_misc` |

Тип виджета: `LesionTypeWidget` — кастомный виджет (список кнопок-тоглов с SVG-пиктограммами).
При активации строка визуально «обводится» (рамка акцентным цветом).

---

### VI.2.4 Основной бланк — секция «Вид санитарных потерь» (вертикальный блок)

| Буква | Метка | ID поля |
|---|---|---|
| О | Огнестрельное | `san_loss_gunshot` |
| Я | Ядерное | `san_loss_nuclear` |
| Х | Химическое | `san_loss_chemical` |
| Бак. | Бактериологическое | `san_loss_biological` |
| Другие | Другие | `san_loss_other` |
| Отм. | Отморожение | `san_loss_frostbite` |
| Б | Ожог | `san_loss_burn` |
| И | Иное | `san_loss_misc` |

Аналогичный `LesionTypeWidget`.

---

### VI.2.5 Основной бланк — секция «Изоляция» (вертикальная полоса)

Вертикальный флаг-переключатель. Активируется если требуется изоляция.

| ID поля | Название | Тип виджета |
|---|---|---|
| `isolation_required` | ИЗОЛЯЦИЯ | `QCheckBox` / кнопка-флаг |

---

### VI.2.6 Основной бланк — Схема тела (BodyMap, центральный блок)

**Это ключевой интерактивный элемент. Реализуется как `BodyMapWidget(QWidget)`.**

Схема тела — **4 силуэта человека**:
- Мужчина: спереди + сзади
- Женщина: спереди + сзади

На схеме врач:
- отмечает **локализацию повреждения** (подчеркнуть на форме);
- выбирает **тип ткани** (мягкие ткани / кости / сосуды / полостные раны / ожоги).

**КРИТИЧНО**: Рисование возможно **только внутри контуров силуэтов**. Клики вне тела игнорируются (используется клиппинг-маска по контуру SVG).

#### Метки типов повреждений (подчеркнуть):
`мягкие ткани`, `кости`, `сосуды`, `полостные раны`, `ожоги`

| ID поля | Название | Тип |
|---|---|---|
| `bodymap_annotations_json` | JSON с координатами и типами меток | TEXT (JSON) |
| `bodymap_tissue_types` | Отмеченные типы тканей | `QCheckBox` × 5 |
| `bodymap_gender` | Пол для отображения | TEXT ('M' / 'F') |

#### Спецификация `BodyMapWidget`:

```
BodyMapWidget(QWidget)
│
├── QComboBox «Пол» (вверху)
│   ├── Мужчина (M)
│   └── Женщина (F)
│
├── QGraphicsScene  (1280×720 px рабочая область, 4 силуэта)
│   │
│   ├── Слой силуэтов (всегда видны все 4, но активны только 2 в зависимости от пола)
│   │   ├── male_front.svg     (x: 0–320,    y: 0–720)
│   │   ├── male_back.svg      (x: 320–640,  y: 0–720)
│   │   ├── female_front.svg   (x: 640–960,  y: 0–720)
│   │   └── female_back.svg    (x: 960–1280, y: 0–720)
│   │
│   ├── Клиппинг-маски (QPainterPath, извлечённые из SVG контуров)
│   │   └── Проверка: клик внутри контура → размещает аннотацию, иначе → игнорируется
│   │
│   └── Слой аннотаций   (QGraphicsItemGroup)
│       ├── AnnotationItem: WOUND_X       цвет #C0392B, символ ✕ (12×12 px)
│       ├── AnnotationItem: BURN_HATCH    цвет #E67E22, штриховка (круг Ø16px)
│       ├── AnnotationItem: AMPUTATION    цвет #943126, заливка (треугольник 14px)
│       ├── AnnotationItem: TOURNIQUET    цвет #9C640C, линия (20px горизонтальная)
│       └── AnnotationItem: NOTE_PIN      цвет #1F77B4, булавка (кружок+хвостик)
│
├── ToolBar (QToolBar горизонтальная, над виджетом)
│   ├── RadioButton: WOUND_X      (рана)
│   ├── RadioButton: BURN_HATCH   (ожог)
│   ├── RadioButton: AMPUTATION   (ампутация)
│   ├── RadioButton: TOURNIQUET   (жгут)
│   ├── RadioButton: NOTE_PIN     (заметка)
│   └── Button: Очистить всё
│
└── Сигналы:
    annotations_changed(list[AnnotationData])
    gender_changed(str)  # 'M' | 'F'
```

#### Структура `AnnotationData` (dataclass):
```python
@dataclass
class AnnotationData:
    annotation_type: str   # 'WOUND_X' | 'BURN_HATCH' | 'AMPUTATION' | 'TOURNIQUET' | 'NOTE_PIN'
    x: float               # 0.0–1.0, нормализованные координаты внутри силуэта
    y: float               # 0.0–1.0
    silhouette: str        # 'male_front' | 'male_back' | 'female_front' | 'female_back'
    note: str = ""         # текстовая заметка (для NOTE_PIN)
```

#### Поведение:
- **Отображение**: все 4 силуэта всегда видны, расположены горизонтально.
- **Активные силуэты**: зависят от выбранного пола в QComboBox:
  - Если пол = 'M' → можно рисовать **только на `male_front` и `male_back`**. Клики по женским силуэтам игнорируются.
  - Если пол = 'F' → можно рисовать **только на `female_front` и `female_back`**. Клики по мужским силуэтам игнорируются.
- **Визуальная обратная связь**: неактивные силуэты затемнены (opacity 0.3).
- **Клик** внутри контура активного силуэта → размещает аннотацию текущего типа.
- **Клик вне** контура тела или на неактивном силуэте → игнорируется (нет действия).
- **ПКМ** (правая кнопка) внутри контура активного силуэта → удаляет ближайшую аннотацию в радиусе 15px.
- **Preview**: при наведении курсора над активным силуэтом — полупрозрачный предпросмотр метки (`#5F6A6A`, opacity 0.4).
- **Клиппинг**: используется `QPainterPath.contains(point)` для проверки попадания в контур тела.
- Сохранение: все аннотации сериализуются в JSON и хранятся в поле `bodymap_annotations_json`.
- Масштабирование: виджет адаптируется при изменении размера окна (координаты нормализованы).

#### Алгоритм клиппинга:
```python
def is_inside_body(self, silhouette: str, x: float, y: float) -> bool:
    """Проверяет, находится ли точка (x, y) внутри контура силуэта."""
    path = self.silhouette_paths[silhouette]  # QPainterPath из SVG
    point = QPointF(x * self.scene_width, y * self.scene_height)
    return path.contains(point)
```

#### Извлечение контуров из SVG:
При инициализации виджета:
1. Загружается SVG-файл силуэта (например, `male_front.svg`).
2. Парсится XML, извлекается атрибут `d` элемента `<path>`.
3. Конвертируется в `QPainterPath` через `QPainterPath.addPath()`.
4. Сохраняется в `self.silhouette_paths[silhouette_name]`.

**Требование к SVG**: каждый силуэт должен быть **замкнутым контуром** (один `<path>` элемент).

#### Подготовка SVG из PNG (для разработчика):
1. Открыть `form_100_body.png` в Inkscape / Adobe Illustrator.
2. Вырезать 4 силуэта: мужчина спереди/сзади, женщина спереди/сзади.
3. Выполнить трассировку (Image Trace / Vectorize Bitmap) с порогом 128.
4. Упростить контур (Path → Simplify), оставить один замкнутый `<path>`.
5. Сохранить каждый силуэт в отдельный SVG-файл с viewport 320×720 px.
6. Убрать лишние атрибуты, оставить только `<svg>` и `<path d="..."/>`.

**Результат**: 4 чистых SVG-файла без фона, только белый контур тела.

---

### VI.2.7 Основной бланк — правый блок «Медицинская помощь»

| ID поля | Название | Тип виджета | Примечание |
|---|---|---|---|
| `mp_antibiotic` | Введено: антибиотик | `QCheckBox` | подчеркнуть |
| `mp_antibiotic_dose` | Доза антибиотика | `QLineEdit` | вписать |
| `mp_serum_pss` | Сыворотка ПСС | `QCheckBox` | |
| `mp_serum_pgs` | Сыворотка ПГС | `QCheckBox` | |
| `mp_serum_dose` | Доза сыворотки | `QLineEdit` | |
| `mp_toxoid` | Анатоксин (какой) | `QLineEdit` | |
| `mp_antidote` | Антидот (какой) | `QLineEdit` | |
| `mp_analgesic` | Обезболивающее средство | `QCheckBox` + `QLineEdit` | |
| `mp_transfusion_blood` | Переливание крови | `QCheckBox` | |
| `mp_transfusion_substitute` | Переливание кровезаменителей | `QCheckBox` | |
| `mp_immobilization` | Иммобилизация | `QCheckBox` | |
| `mp_bandage` | Перевязка | `QCheckBox` | |

---

### VI.2.8 Основной бланк — правый нижний блок

| ID поля | Название | Тип виджета | Значения / формат |
|---|---|---|---|
| `tourniquet_time` | Жгут наложен — час, мин | `QTimeEdit` | ЧЧ:ММ |
| `sanitation_type` | Санитарная обработка (подчеркнуть) | `QButtonGroup` | полная / частичная / не проводилась |
| `evacuation_dest` | Эвакуировать (нужное обвести) | `IconSelectWidget` | лёжа / сидя / носилки |
| `evacuation_priority` | Очерёдность эвакуации | `QButtonGroup` | I / II / III |
| `transport_type` | Вид транспорта (обвести) | `IconSelectWidget` | авто / сан. / корабль / вертолёт / самолёт |
| `doctor_signature` | Врач (подпись разборчиво) | `QLineEdit` | текст |
| `main_diagnosis` | Диагноз | `QTextEdit` | текст |

---

### VI.2.9 Боковые флаг-полосы

| ID поля | Полоса | Цвет | Тип виджета |
|---|---|---|---|
| `flag_emergency` | НЕОТЛОЖНАЯ ПОМОЩЬ | Красный (#C0392B) | `QCheckBox`-флаг |
| `flag_radiation` | РАДИАЦИОННОЕ ПОРАЖЕНИЕ | Синий (#1F77B4) | `QCheckBox`-флаг |
| `flag_sanitation` | САНИТАРНАЯ ОБРАБОТКА | Жёлтый (#F4D58D) | `QCheckBox`-флаг |

Флаги отображаются как **цветные вертикальные полосы** по краям бланка.
Активная полоса — яркая, неактивная — полупрозрачная (opacity 0.25).

---

## VI.3 Схема БД — новые таблицы

### `form100`

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | |
| `emr_case_id` | INTEGER FK → emr_case.id NOT NULL | Привязка к госпитализации |
| `created_at` | DATETIME NOT NULL | |
| `created_by` | INTEGER FK → users.id | |
| `updated_at` | DATETIME | |
| `updated_by` | INTEGER FK → users.id | |
| `is_archived` | INTEGER DEFAULT 0 | Архивирован (неизменяемый) |
| `artifact_path` | TEXT | Путь к PDF-артефакту |
| `artifact_sha256` | TEXT | SHA256 PDF-файла |

### `form100_data`

| Поле | Тип | Описание |
|---|---|---|
| `id` | INTEGER PK | |
| `form100_id` | INTEGER FK → form100.id NOT NULL | |
| — **Корешок** — | | |
| `stub_issued_time` | TEXT | ЧЧ:ММ |
| `stub_issued_date` | TEXT | ДД.ММ.ГГГГ |
| `stub_rank` | TEXT | |
| `stub_unit` | TEXT | |
| `stub_full_name` | TEXT | |
| `stub_id_tag` | TEXT | |
| `stub_injury_time` | TEXT | |
| `stub_injury_date` | TEXT | |
| `stub_evacuation_method` | TEXT | 'airplane'\|'ambu'\|'truck' |
| `stub_evacuation_dest` | TEXT | 'lying'\|'sitting'\|'stretcher' |
| `stub_med_help_json` | TEXT | JSON список отмеченных пунктов |
| `stub_antibiotic_dose` | TEXT | |
| `stub_pss_pgs_dose` | TEXT | |
| `stub_toxoid_type` | TEXT | |
| `stub_antidote_type` | TEXT | |
| `stub_analgesic_dose` | TEXT | |
| `stub_transfusion` | INTEGER | 0/1 |
| `stub_immobilization` | INTEGER | 0/1 |
| `stub_tourniquet` | INTEGER | 0/1 |
| `stub_diagnosis` | TEXT | |
| — **Основной бланк — идентификация** — | | |
| `main_issued_place` | TEXT | |
| `main_issued_time` | TEXT | |
| `main_issued_date` | TEXT | |
| `main_rank` | TEXT | |
| `main_unit` | TEXT | |
| `main_full_name` | TEXT | |
| `main_id_tag` | TEXT | |
| `main_injury_time` | TEXT | |
| `main_injury_date` | TEXT | |
| — **Вид поражения** — | | |
| `lesion_json` | TEXT | JSON {gunshot, nuclear, chemical, …} |
| `san_loss_json` | TEXT | JSON вид санитарных потерь |
| `isolation_required` | INTEGER | 0/1 |
| — **Bodymap** — | | |
| `bodymap_gender` | TEXT | 'M' / 'F' |
| `bodymap_annotations_json` | TEXT | JSON список AnnotationData |
| `bodymap_tissue_types_json` | TEXT | JSON список отмеченных типов ткани |
| — **Медицинская помощь** — | | |
| `mp_json` | TEXT | JSON всех полей мед. помощи |
| — **Нижний блок** — | | |
| `tourniquet_time` | TEXT | |
| `sanitation_type` | TEXT | 'full'\|'partial'\|'none' |
| `evacuation_dest` | TEXT | 'lying'\|'sitting'\|'stretcher' |
| `evacuation_priority` | TEXT | 'I'\|'II'\|'III' |
| `transport_type` | TEXT | 'car'\|'ambu'\|'ship'\|'heli'\|'plane' |
| `doctor_signature` | TEXT | |
| `main_diagnosis` | TEXT | |
| — **Флаги** — | | |
| `flag_emergency` | INTEGER | 0/1 |
| `flag_radiation` | INTEGER | 0/1 |
| `flag_sanitation` | INTEGER | 0/1 |

### Индексы:

```sql
CREATE INDEX ix_form100_emr_case ON form100(emr_case_id);
CREATE INDEX ix_form100_created_at ON form100(created_at);
CREATE UNIQUE INDEX ux_form100_data_form ON form100_data(form100_id);
```

---

## VI.4 Структура файлов (новые файлы)

```
app/
  ui/
    form100/
      __init__.py
      form100_view.py          # Главный экран формы 100 (вкладка)
      form100_stub_widget.py   # Виджет корешка (левая часть)
      form100_main_widget.py   # Виджет основного бланка (центр + правая часть)
      form100_flags_widget.py  # Виджет цветных флаг-полос
      bodymap_widget.py        # BodyMapWidget + AnnotationData
      lesion_type_widget.py    # LesionTypeWidget (пиктограммы)
      icon_select_widget.py    # IconSelectWidget (иконки обводки)
  application/
    dto/
      form100_dto.py           # Form100DTO, Form100DataDTO
    services/
      form100_service.py       # create / update / archive / get_by_case
  domain/
    models/
      form100.py               # доменные модели Form100, Form100Data, AnnotationData
  infrastructure/
    db/
      repositories/
        form100_repo.py        # CRUD репозиторий
      migrations/
        xxxx_add_form100.py    # Alembic migration
    reporting/
      form100_pdf.py           # Генерация PDF (ReportLab) — точная копия бланка
resources/
  svg/
    male_front.svg               # Силуэт мужчины спереди (из form_100_body.png)
    male_back.svg                # Силуэт мужчины сзади
    female_front.svg             # Силуэт женщины спереди
    female_back.svg              # Силуэт женщины сзади
    lesion_gunshot.svg           # Пиктограммы видов поражений
    lesion_nuclear.svg
    lesion_chemical.svg
    lesion_biological.svg
    lesion_other.svg
    lesion_frostbite.svg
    lesion_burn.svg
    lesion_misc.svg
    evac_lying.svg
    evac_sitting.svg
    evac_stretcher.svg
    transport_car.svg
    transport_ambu.svg
    transport_ship.svg
    transport_heli.svg
    transport_plane.svg
tests/
  unit/
    test_form100_service.py
    test_bodymap_widget.py
    test_form100_pdf.py
  integration/
    test_form100_repo.py
```

---

## VI.5 UI — компоновка экрана

### Структура `Form100View` (вкладка в главном окне):

```
Form100View (QWidget)
│
├── QSplitter (горизонтальный, resizable)
│   │
│   ├── LEFT PANEL (фиксированная ширина ~300px)
│   │   └── Form100StubWidget       ← корешок
│   │
│   └── RIGHT PANEL
│       ├── QScrollArea
│       │   └── QVBoxLayout
│       │       ├── Form100FlagsWidget (горизонтальные флаги наверху)
│       │       ├── Form100MainWidget  (идентификация + поражения + bodymap + мед.помощь)
│       │       └── Form100BottomWidget (эвакуация, диагноз, подпись врача)
│       │
│       └── QHBoxLayout (кнопки действий внизу)
│           ├── QPushButton «Сохранить»
│           ├── QPushButton «Сгенерировать PDF»
│           ├── QPushButton «Архивировать» (деактивирует редактирование)
│           └── QPushButton «Очистить форму»
│
└── StatusBar hint (подсказки по текущему полю)
```

### Компоновка `Form100MainWidget`:

```
Form100MainWidget (QWidget)
│
├── QHBoxLayout (верхний ряд)
│   ├── LesionTypeWidget       «Вид поражения» (левый столбец, ~100px)
│   ├── QFrame (изоляция)      ИЗОЛЯЦИЯ (вертикальная полоса, 80px)
│   ├── BodyMapWidget          схема тела — 4 силуэта (центр, растягивается)
│   │   └── QComboBox (пол) вверху: Мужчина / Женщина
│   └── QGroupBox              «Медицинская помощь» (правый столбец, ~220px)
│
└── QGroupBox «Идентификация»  (под верхним рядом, все поля ФИО/жетон/дата)
```

**Примечание**: BodyMapWidget занимает центральную область, 4 силуэта расположены горизонтально. Каждый силуэт масштабируется пропорционально при изменении размера окна.

---

## VI.6 PDF-генерация (`form100_pdf.py`)

**Цель**: воспроизвести бланк Формы 100 пиксель-в-пиксель средствами ReportLab.

### Принципы:

1. Использовать `reportlab.platypus` (Paragraph, Table, Image).
2. Размер страницы: **A5 альбомная** (`landscape(A5)`) — соответствует оригиналу.
3. Воспроизводить все три части: корешок (левый блок) + основной бланк (центр) + полосы (правый край).
4. Цветные полосы «Неотложная помощь» / «Радиационное поражение» / «Санитарная обработка» — закрашенные прямоугольники.
5. Схема тела: экспортировать `BodyMapWidget` в PNG через `QPixmap.grabWidget()` → вставить в PDF как `Image`. **Важно**: экспортировать только те силуэты, которые соответствуют выбранному полу (`bodymap_gender`). Если пол 'M' — отрисовать мужчину спереди/сзади, если 'F' — женщину спереди/сзади.
6. Пиктограммы: вставить как PNG-иконки из `resources/svg/` (pre-rasterized при сборке).
7. Финальный файл сохраняется в `{data_dir}/form100_artifacts/{form100_id}_{timestamp}.pdf`.
8. SHA256 файла записывается в `form100.artifact_sha256`.

---

## VI.7 ZIP-обмен

Файл `form100_pdf.py` уже генерирует PDF. В ZIP-экспорт добавить:

```python
# в export_zip.py / exchange_service.py
zip.write(f"form100/{form100_id}.pdf")
zip.write(f"form100/{form100_id}.json")   # сырые данные form100_data
```

В ZIP-импорте: восстанавливать `form100` + `form100_data` из JSON, пересчитывать SHA256 PDF.

---

## VI.8 Аудит

Все события логировать в `audit_log` с `entity_type = 'form100'`:

| Событие (`action`) | Когда |
|---|---|
| `form100_create` | Создание новой формы |
| `form100_update` | Сохранение изменений |
| `form100_archive` | Архивирование (блокировка редактирования) |
| `form100_pdf_generate` | Генерация PDF |
| `form100_export` | Включение в ZIP |
| `form100_import` | Восстановление из ZIP |

---

## VI.9 Доменные модели (`domain/models/form100.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class AnnotationData:
    annotation_type: str   # 'WOUND_X' | 'BURN_HATCH' | 'AMPUTATION' | 'TOURNIQUET' | 'NOTE_PIN'
    x: float               # нормализованные 0.0–1.0
    y: float
    silhouette: str        # 'male_front' | 'male_back' | 'female_front' | 'female_back'
    note: str = ""

@dataclass
class Form100Data:
    # Корешок
    stub_issued_time: Optional[str] = None
    stub_issued_date: Optional[str] = None
    stub_rank: Optional[str] = None
    stub_unit: Optional[str] = None
    stub_full_name: Optional[str] = None
    stub_id_tag: Optional[str] = None
    stub_injury_time: Optional[str] = None
    stub_injury_date: Optional[str] = None
    stub_evacuation_method: Optional[str] = None
    stub_evacuation_dest: Optional[str] = None
    stub_med_help: list[str] = field(default_factory=list)
    stub_antibiotic_dose: Optional[str] = None
    stub_pss_pgs_dose: Optional[str] = None
    stub_toxoid_type: Optional[str] = None
    stub_antidote_type: Optional[str] = None
    stub_analgesic_dose: Optional[str] = None
    stub_transfusion: bool = False
    stub_immobilization: bool = False
    stub_tourniquet: bool = False
    stub_diagnosis: Optional[str] = None
    # Основной бланк
    main_issued_place: Optional[str] = None
    main_issued_time: Optional[str] = None
    main_issued_date: Optional[str] = None
    main_rank: Optional[str] = None
    main_unit: Optional[str] = None
    main_full_name: Optional[str] = None
    main_id_tag: Optional[str] = None
    main_injury_time: Optional[str] = None
    main_injury_date: Optional[str] = None
    # Поражения
    lesion_types: list[str] = field(default_factory=list)
    san_loss_types: list[str] = field(default_factory=list)
    isolation_required: bool = False
    # Bodymap
    bodymap_gender: str = 'M'  # 'M' | 'F'
    bodymap_annotations: list[AnnotationData] = field(default_factory=list)
    bodymap_tissue_types: list[str] = field(default_factory=list)
    # Мед. помощь
    mp_antibiotic: bool = False
    mp_antibiotic_dose: Optional[str] = None
    mp_serum_pss: bool = False
    mp_serum_pgs: bool = False
    mp_serum_dose: Optional[str] = None
    mp_toxoid: Optional[str] = None
    mp_antidote: Optional[str] = None
    mp_analgesic: bool = False
    mp_analgesic_dose: Optional[str] = None
    mp_transfusion_blood: bool = False
    mp_transfusion_substitute: bool = False
    mp_immobilization: bool = False
    mp_bandage: bool = False
    # Нижний блок
    tourniquet_time: Optional[str] = None
    sanitation_type: Optional[str] = None   # 'full'|'partial'|'none'
    evacuation_dest: Optional[str] = None
    evacuation_priority: Optional[str] = None  # 'I'|'II'|'III'
    transport_type: Optional[str] = None
    doctor_signature: Optional[str] = None
    main_diagnosis: Optional[str] = None
    # Флаги
    flag_emergency: bool = False
    flag_radiation: bool = False
    flag_sanitation: bool = False

@dataclass
class Form100:
    id: Optional[int]
    emr_case_id: int
    created_at: datetime
    created_by: int
    is_archived: bool
    data: Form100Data
    artifact_path: Optional[str] = None
    artifact_sha256: Optional[str] = None
```

---

## VI.10 Use-cases / сервис (`form100_service.py`)

```python
class Form100Service:
    def create(self, emr_case_id: int, data: Form100DataDTO, user_id: int) -> Form100DTO: ...
    def update(self, form100_id: int, data: Form100DataDTO, user_id: int) -> Form100DTO: ...
    def get_by_case(self, emr_case_id: int) -> list[Form100DTO]: ...
    def get_by_id(self, form100_id: int) -> Form100DTO: ...
    def archive(self, form100_id: int, user_id: int) -> None: ...
    def generate_pdf(self, form100_id: int, user_id: int) -> str: ...  # → путь к PDF
```

**Правила:**
- `update` запрещён если `is_archived = True` → выбросить `Form100ArchivedError`.
- `generate_pdf` всегда сохраняет SHA256 в БД.
- Все методы пишут в `audit_log`.

---

## VI.11 Миграция Alembic

```python
# migrations/xxxx_add_form100.py

def upgrade():
    op.create_table(
        'form100',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('emr_case_id', sa.Integer, sa.ForeignKey('emr_case.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('created_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('updated_at', sa.DateTime),
        sa.Column('updated_by', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('is_archived', sa.Integer, default=0),
        sa.Column('artifact_path', sa.Text),
        sa.Column('artifact_sha256', sa.Text),
    )
    op.create_table(
        'form100_data',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('form100_id', sa.Integer, sa.ForeignKey('form100.id'), nullable=False),
        # ... все поля из VI.3
    )
    op.create_index('ix_form100_emr_case', 'form100', ['emr_case_id'])
    op.create_index('ix_form100_created_at', 'form100', ['created_at'])
    op.create_unique_constraint('ux_form100_data_form', 'form100_data', ['form100_id'])

def downgrade():
    op.drop_table('form100_data')
    op.drop_table('form100')
```

---

## VI.12 Тесты

### Unit-тесты:

| Файл | Что тестирует |
|---|---|
| `test_form100_service.py` | create/update/archive/get_by_case; Form100ArchivedError на update архивированной |
| `test_bodymap_widget.py` | AnnotationData serialization/deserialization; нормализация координат; сброс |
| `test_form100_pdf.py` | PDF генерируется без ошибок; SHA256 непустой; файл существует |

### Integration-тесты:

| Файл | Что тестирует |
|---|---|
| `test_form100_repo.py` | CRUD через SQLite in-memory; FK к emr_case; UNIQUE ux_form100_data_form |

---

## VI.13 Чек-лист интеграции в главное окно

- [ ] Добавить вкладку «Форма 100» в `MainWindow` (рядом с ЭМЗ, Лаб, Санитария).
- [ ] Вкладка активируется только при выбранном пациенте/госпитализации (аналогично ЭМЗ).
- [ ] При смене пациента — очищать форму (`Form100View.clear_context()`).
- [ ] При открытии вкладки — загружать последнюю незаархивированную форму для текущей госпитализации.
- [ ] Кнопка «Форма 100» в контекстной панели пациента (quick-action).

---

## VI.14 Критерии готовности (Definition of Done)

- [ ] Все поля формы отображаются и сохраняются в БД.
- [ ] BodyMapWidget: клик размещает аннотацию, ПКМ удаляет, координаты нормализованы.
- [ ] PDF генерируется, содержит схему тела с аннотациями, SHA256 записан.
- [ ] Цветные флаг-полосы (красная/синяя/жёлтая) визуально корректны.
- [ ] Архивирование блокирует редактирование.
- [ ] Все audit-события записываются.
- [ ] Alembic-миграция применяется без ошибок (`alembic upgrade head`).
- [ ] ZIP-экспорт включает PDF + JSON формы.
- [ ] `ruff`, `mypy`, `pytest` — зелёные.
- [ ] Ручной прогон: открыть форму, заполнить все секции, нарисовать метки на теле, сгенерировать PDF.
