# ТЗ v2.2: Модуль «Форма 100 МО РФ» — “железобетонная” спецификация с шаблонами кода (под ваш проект)

Дата: 2026-01-21  
Основано на фактах вашего кода: `audit_log.payload_json`, роли `admin/operator`, `QStackedWidget` навигация, ZIP-пакеты `export.xlsx + manifest.json`, reportlab A4, поиск LIKE/ILIKE.

> Это ТЗ предназначено **для Codex**: содержит конкретные шаги, готовые каркасы классов/функций/моделей и точки интеграции в существующую архитектуру.

---

## 0) Решения v2.2 (зафиксировано)

1) **Аудит**: не меняем `audit_log` (нет миграций для аудита). Diff хранится внутри `payload_json` по схеме `form100.audit.v1`.
2) **Роли**: права проверяются в сервисе `Form100Service` простыми сравнениями `actor.role == "admin"`.
3) **Справочники**: всё, что пользователь выбирает из списков (причины, типы травм и т.д.) — **через ReferenceService** (если справочника нет — добавить seed/таблицу по вашему паттерну).
4) **Поиск**: LIKE/ILIKE, FTS5 не подключаем.
5) **Подпись**: v1 — только `signed_by/signed_at/seal_applied`. Рисованной подписи нет.
6) **Обмен**: основной формат — ZIP с `export.xlsx + manifest.json`, плюс запись в `data_exchange_package` (по вашему существующему механизму).
7) **PDF**: reportlab, A4.

---

## 1) Файлы: что создать и что изменить

### 1.1 Создать (новые)
- `app/domain/models/form100.py`
- `app/domain/rules/form100_rules.py`
- `app/application/dto/form100_dto.py`
- `app/application/services/form100_service.py`
- `app/infrastructure/db/repositories/form100_repo.py`
- `app/infrastructure/export/form100_export.py`
- `app/infrastructure/import/form100_import.py`
- `app/infrastructure/reporting/form100_pdf_report.py`
- `app/ui/form100/__init__.py`
- `app/ui/form100/form100_view.py`
- `app/ui/form100/form100_editor.py`
- `app/ui/form100/widgets/flags_strip.py`
- `app/ui/form100/widgets/bodymap_editor.py`
- `app/ui/form100/widgets/validation_banner.py`
- `tests/unit/test_form100_rules.py`
- `tests/integration/test_form100_service.py`

### 1.2 Изменить (существующие)
- `app/infrastructure/db/models_sqlalchemy.py` — добавить `Form100Card`, `Form100Mark`, `Form100Stage`
- `app/infrastructure/db/migrations/versions/0012_form100_module.py` — миграция
- `app/container.py` — DI регистрация repo/service/pdf/export/import
- `app/ui/main_window.py` — пункт меню + view в QStackedWidget + ContextBar
- `app/ui/import_export/import_export_wizard.py` — добавить “Form100 package zip”
- `app/application/services/exchange_service.py` — добавить экспорт/импорт пакета Form100 (если обмен централизован там)
- `app/application/services/reporting_service.py` — добавить печать Form100 (если печать централизована)

---

## 2) DB: готовый шаблон моделей (SQLAlchemy)

**Файл:** `app/infrastructure/db/models_sqlalchemy.py`  
**Требование:** использовать ваш `Base` и паттерны других моделей.

### 2.1 Вставить модели (шаблон)

```python
# --- Form100 ---------------------------------------------------------------

from sqlalchemy import (
    Column, String, Integer, DateTime, Date, Boolean, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship

class Form100Card(Base):
    __tablename__ = "form100_card"

    id = Column(String(36), primary_key=True)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=False)

    status = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)

    qr_payload = Column(Text, nullable=True)
    print_number = Column(String, nullable=True)

    corrects_id = Column(String(36), nullable=True)
    corrected_by_new_id = Column(String(36), nullable=True)

    # person
    last_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    birth_date = Column(Date, nullable=False)
    rank = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    dog_tag_number = Column(String, nullable=True)
    id_doc_type = Column(String, nullable=True)
    id_doc_number = Column(String, nullable=True)

    # event
    injury_dt = Column(DateTime, nullable=True)
    arrival_dt = Column(DateTime, nullable=False)
    first_aid_before = Column(Boolean, nullable=False, default=False)
    cause_category = Column(String, nullable=False)
    is_combat = Column(Boolean, nullable=True)

    # injury/diagnosis
    trauma_types_json = Column(Text, nullable=False, default="[]")
    thermal_degree = Column(String, nullable=True)
    wound_types_json = Column(Text, nullable=False, default="[]")
    features_json = Column(Text, nullable=False, default="[]")
    other_text = Column(Text, nullable=True)
    diagnosis_text = Column(Text, nullable=False)
    diagnosis_code = Column(String, nullable=True)
    triage = Column(String, nullable=True)

    # flags
    flag_urgent = Column(Boolean, nullable=False, default=False)
    flag_sanitation = Column(Boolean, nullable=False, default=False)
    flag_isolation = Column(Boolean, nullable=False, default=False)
    flag_radiation = Column(Boolean, nullable=False, default=False)

    # care
    care_bleeding_control = Column(String, nullable=True)
    care_dressing = Column(String, nullable=True)
    care_immobilization = Column(String, nullable=True)
    care_airway = Column(String, nullable=True)

    care_analgesia_given = Column(Boolean, nullable=False, default=False)
    care_analgesia_details = Column(Text, nullable=True)

    care_antibiotic_given = Column(Boolean, nullable=False, default=False)
    care_antibiotic_details = Column(Text, nullable=True)

    care_antidote_given = Column(Boolean, nullable=False, default=False)
    care_antidote_details = Column(Text, nullable=True)

    care_tetanus = Column(String, nullable=True)
    care_other = Column(Text, nullable=True)

    infusion_performed = Column(Boolean, nullable=False, default=False)
    infusion_volume_ml = Column(Integer, nullable=True)
    infusion_details = Column(Text, nullable=True)

    transfusion_performed = Column(Boolean, nullable=False, default=False)
    transfusion_volume_ml = Column(Integer, nullable=True)
    transfusion_details = Column(Text, nullable=True)

    sanitation_performed = Column(Boolean, nullable=False, default=False)
    sanitation_type = Column(String, nullable=True)
    sanitation_details = Column(Text, nullable=True)

    # evac
    evac_destination = Column(Text, nullable=True)
    evac_transport = Column(String, nullable=True)
    evac_position = Column(String, nullable=True)
    evac_require_escort = Column(Boolean, nullable=True)
    evac_oxygen_needed = Column(Boolean, nullable=True)
    evac_notes = Column(Text, nullable=True)

    # sign
    signed_by = Column(String, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    seal_applied = Column(Boolean, nullable=False, default=False)

    marks = relationship("Form100Mark", back_populates="card", cascade="all, delete-orphan")
    stages = relationship("Form100Stage", back_populates="card", cascade="all, delete-orphan")


Index("idx_form100_status", Form100Card.status)
Index("idx_form100_injury_dt", Form100Card.injury_dt)
Index("idx_form100_arrival_dt", Form100Card.arrival_dt)
Index("idx_form100_dog_tag", Form100Card.dog_tag_number)
Index("idx_form100_unit", Form100Card.unit)
Index("idx_form100_name", Form100Card.last_name, Form100Card.first_name)


class Form100Mark(Base):
    __tablename__ = "form100_mark"

    id = Column(String(36), primary_key=True)
    card_id = Column(String(36), ForeignKey("form100_card.id"), nullable=False, index=True)

    side = Column(String, nullable=False)  # FRONT/BACK
    type = Column(String, nullable=False)  # WOUND_X/BURN_HATCH/TOURNIQUET_LINE/AMPUTATION_FILL/NOTE_PIN
    shape_json = Column(Text, nullable=False)
    meta_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime, nullable=False)
    created_by = Column(String, nullable=True)

    card = relationship("Form100Card", back_populates="marks")


class Form100Stage(Base):
    __tablename__ = "form100_stage"

    id = Column(String(36), primary_key=True)
    card_id = Column(String(36), ForeignKey("form100_card.id"), nullable=False, index=True)

    stage_name = Column(String, nullable=False)
    received_at = Column(DateTime, nullable=True)

    updated_diagnosis_text = Column(Text, nullable=True)
    updated_diagnosis_code = Column(String, nullable=True)
    procedures_text = Column(Text, nullable=True)

    evac_next_destination = Column(Text, nullable=True)
    evac_next_dt = Column(DateTime, nullable=True)

    condition_at_transfer = Column(Text, nullable=True)
    outcome = Column(String, nullable=True)
    outcome_date = Column(Date, nullable=True)
    burial_place = Column(Text, nullable=True)

    signed_by = Column(String, nullable=True)
    signed_at = Column(DateTime, nullable=True)

    card = relationship("Form100Card", back_populates="stages")
```

---

## 3) Alembic миграция (шаблон)

**Файл:** `app/infrastructure/db/migrations/versions/0012_form100_module.py`

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # NOTE: Codex обязан корректно выставить revision/down_revision под актуальный head
    op.create_table(
        "form100_card",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),

        sa.Column("qr_payload", sa.Text(), nullable=True),
        sa.Column("print_number", sa.String(), nullable=True),
        sa.Column("corrects_id", sa.String(length=36), nullable=True),
        sa.Column("corrected_by_new_id", sa.String(length=36), nullable=True),

        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("middle_name", sa.String(), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("rank", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=False),
        sa.Column("dog_tag_number", sa.String(), nullable=True),
        sa.Column("id_doc_type", sa.String(), nullable=True),
        sa.Column("id_doc_number", sa.String(), nullable=True),

        sa.Column("injury_dt", sa.DateTime(), nullable=True),
        sa.Column("arrival_dt", sa.DateTime(), nullable=False),
        sa.Column("first_aid_before", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cause_category", sa.String(), nullable=False),
        sa.Column("is_combat", sa.Boolean(), nullable=True),

        sa.Column("trauma_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("thermal_degree", sa.String(), nullable=True),
        sa.Column("wound_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("features_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("other_text", sa.Text(), nullable=True),
        sa.Column("diagnosis_text", sa.Text(), nullable=False),
        sa.Column("diagnosis_code", sa.String(), nullable=True),
        sa.Column("triage", sa.String(), nullable=True),

        sa.Column("flag_urgent", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_sanitation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_isolation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("flag_radiation", sa.Boolean(), nullable=False, server_default=sa.text("0")),

        sa.Column("care_bleeding_control", sa.String(), nullable=True),
        sa.Column("care_dressing", sa.String(), nullable=True),
        sa.Column("care_immobilization", sa.String(), nullable=True),
        sa.Column("care_airway", sa.String(), nullable=True),

        sa.Column("care_analgesia_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_analgesia_details", sa.Text(), nullable=True),

        sa.Column("care_antibiotic_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_antibiotic_details", sa.Text(), nullable=True),

        sa.Column("care_antidote_given", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("care_antidote_details", sa.Text(), nullable=True),

        sa.Column("care_tetanus", sa.String(), nullable=True),
        sa.Column("care_other", sa.Text(), nullable=True),

        sa.Column("infusion_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("infusion_volume_ml", sa.Integer(), nullable=True),
        sa.Column("infusion_details", sa.Text(), nullable=True),

        sa.Column("transfusion_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("transfusion_volume_ml", sa.Integer(), nullable=True),
        sa.Column("transfusion_details", sa.Text(), nullable=True),

        sa.Column("sanitation_performed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("sanitation_type", sa.String(), nullable=True),
        sa.Column("sanitation_details", sa.Text(), nullable=True),

        sa.Column("evac_destination", sa.Text(), nullable=True),
        sa.Column("evac_transport", sa.String(), nullable=True),
        sa.Column("evac_position", sa.String(), nullable=True),
        sa.Column("evac_require_escort", sa.Boolean(), nullable=True),
        sa.Column("evac_oxygen_needed", sa.Boolean(), nullable=True),
        sa.Column("evac_notes", sa.Text(), nullable=True),

        sa.Column("signed_by", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("seal_applied", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "form100_mark",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("card_id", sa.String(length=36), sa.ForeignKey("form100_card.id"), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("shape_json", sa.Text(), nullable=False),
        sa.Column("meta_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
    )
    op.create_index("ix_form100_mark_card_id", "form100_mark", ["card_id"])

    op.create_table(
        "form100_stage",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("card_id", sa.String(length=36), sa.ForeignKey("form100_card.id"), nullable=False),
        sa.Column("stage_name", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("updated_diagnosis_text", sa.Text(), nullable=True),
        sa.Column("updated_diagnosis_code", sa.String(), nullable=True),
        sa.Column("procedures_text", sa.Text(), nullable=True),
        sa.Column("evac_next_destination", sa.Text(), nullable=True),
        sa.Column("evac_next_dt", sa.DateTime(), nullable=True),
        sa.Column("condition_at_transfer", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("outcome_date", sa.Date(), nullable=True),
        sa.Column("burial_place", sa.Text(), nullable=True),
        sa.Column("signed_by", sa.String(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_form100_stage_card_id", "form100_stage", ["card_id"])

    op.create_index("idx_form100_status", "form100_card", ["status"])
    op.create_index("idx_form100_injury_dt", "form100_card", ["injury_dt"])
    op.create_index("idx_form100_arrival_dt", "form100_card", ["arrival_dt"])
    op.create_index("idx_form100_dog_tag", "form100_card", ["dog_tag_number"])
    op.create_index("idx_form100_unit", "form100_card", ["unit"])
    op.create_index("idx_form100_name", "form100_card", ["last_name", "first_name"])

def downgrade():
    op.drop_index("idx_form100_name", table_name="form100_card")
    op.drop_index("idx_form100_unit", table_name="form100_card")
    op.drop_index("idx_form100_dog_tag", table_name="form100_card")
    op.drop_index("idx_form100_arrival_dt", table_name="form100_card")
    op.drop_index("idx_form100_injury_dt", table_name="form100_card")
    op.drop_index("idx_form100_status", table_name="form100_card")

    op.drop_index("ix_form100_stage_card_id", table_name="form100_stage")
    op.drop_table("form100_stage")

    op.drop_index("ix_form100_mark_card_id", table_name="form100_mark")
    op.drop_table("form100_mark")

    op.drop_table("form100_card")
```

---

## 4) DTO: шаблоны

**Файл:** `app/application/dto/form100_dto.py` — см. полный шаблон в документе v2.2 (включён выше).

---

## 5) Аудит: payload_json (финальный формат)

Так как diff-колонок нет, всегда писать в `payload_json`:

```json
{
  "schema":"form100.audit.v1",
  "actor":{"user_id":"...","role":"operator"},
  "event":{"ts":"ISO8601","action":"update","status_from":"DRAFT","status_to":"DRAFT"},
  "entity":{"type":"form100","id":"<card_id>"},
  "changes":{"format":"before_after","before":{"path":"old"},"after":{"path":"new"}},
  "meta":{"expected_version":3,"new_version":4}
}
```

**Правило:** `before/after` содержат только изменённые key-path.

---

## 6) UI и интеграция: QStackedWidget

Codex должен реализовать `Form100View` и `Form100Editor` и встроить в `MainWindow` по паттерну других модулей:
- QAction → `_set_active_view("form100")`
- добавить view в `QStackedWidget`
- обновить `ContextBar`

---

## 7) ZIP exchange и PDF
- ZIP: `export.xlsx + manifest.json` по вашему текущему механизму; история — `data_exchange_package`.
- PDF: reportlab A4; 1–2 страницы.

---

## 8) Чеклист готовности
См. раздел Deliverables: миграция, UI, workflow, аудит, zip, pdf.

---
