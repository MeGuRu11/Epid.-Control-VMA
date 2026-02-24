from __future__ import annotations

import importlib
import json
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast
from uuid import uuid4

from app.application.dto.form100_dto import (
    Form100CardDto,
    Form100CardListItemDto,
    Form100CreateRequest,
    Form100Filters,
    Form100MarkDto,
    Form100SignRequest,
    Form100StageCreateRequest,
    Form100StageDto,
    Form100UpdateRequest,
)
from app.domain.models.form100 import FORM100_STATUS_DRAFT, FORM100_STATUS_SIGNED
from app.domain.rules.form100_rules import (
    build_changed_paths,
    validate_card_payload,
    validate_status_transition,
)
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.form100_repo import Form100Repository
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope
from app.infrastructure.export.form100_export import build_manifest, export_form100_excel
from app.infrastructure.reporting.form100_pdf_report import export_form100_pdf
from app.infrastructure.security.sha256 import sha256_file


def _utc_now() -> datetime:
    return datetime.now(UTC)


@contextmanager
def _working_temp_dir() -> Iterator[Path]:
    roots = [Path(tempfile.gettempdir()), Path.cwd() / "tmp_run"]
    last_error: OSError | None = None
    for root in roots:
        temp_dir = root / f"form100-{uuid4().hex}"
        try:
            root.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=False)
            yield temp_dir
            return
        except OSError as exc:
            last_error = exc
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    raise OSError("Не удалось создать временный каталог Form100") from last_error


def _safe_extract_zip(zip_file: zipfile.ZipFile, destination: Path) -> list[Path]:
    destination = destination.resolve()
    extracted: list[Path] = []
    for member in zip_file.infolist():
        if member.is_dir():
            continue
        raw_name = member.filename.replace("\\", "/")
        pure_path = PurePosixPath(raw_name)
        if not raw_name:
            raise ValueError(f"Недопустимый путь в архиве: {member.filename}")
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise ValueError(f"Недопустимый путь в архиве: {member.filename}")
        if pure_path.parts and ":" in pure_path.parts[0]:
            raise ValueError(f"Недопустимый путь в архиве: {member.filename}")
        target_path = (destination / Path(*pure_path.parts)).resolve()
        try:
            target_path.relative_to(destination)
        except ValueError as exc:
            raise ValueError(f"Недопустимый путь в архиве: {member.filename}") from exc
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(member, "r") as src, target_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
        extracted.append(target_path)
    return extracted


class Form100Service:
    def __init__(
        self,
        repo: Form100Repository | None = None,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.repo = repo or Form100Repository()
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def list_cards(
        self,
        filters: Form100Filters | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Form100CardListItemDto]:
        filter_payload = filters.model_dump(exclude_none=True) if filters else {}
        with self.session_factory() as session:
            rows = self.repo.list_cards(session, filters=filter_payload, limit=limit, offset=offset)
            return [self._to_list_item_dto(row) for row in rows]

    def get_card(self, card_id: str) -> Form100CardDto:
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 не найдена")
            marks = self.repo.list_marks(session, card_id)
            stages = self.repo.list_stages(session, card_id)
            return self._to_card_dto(row=row, marks=marks, stages=stages)

    def create_card(self, request: Form100CreateRequest, actor_id: int | None) -> Form100CardDto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        payload = request.model_dump(exclude={"marks", "stages"})
        payload["status"] = FORM100_STATUS_DRAFT
        validate_card_payload(payload)
        with self.session_factory() as session:
            row = self.repo.create_card(
                session,
                card_id=None,
                payload=payload,
                actor_login=actor_login,
            )
            marks = self.repo.replace_marks(
                session,
                card_id=str(row.id),
                marks=[item.model_dump() for item in request.marks],
                actor_login=actor_login,
            )
            stages = []
            for stage_request in request.stages:
                stage = self.repo.add_stage(
                    session,
                    card_id=str(row.id),
                    payload=stage_request.model_dump(),
                )
                stages.append(stage)

            payload_json = json.dumps(
                {
                    "schema": "form100.audit.v1",
                    "actor": {"user_id": actor_id, "role": actor_role},
                    "event": {
                        "ts": _utc_now().isoformat(),
                        "action": "create",
                        "status_from": None,
                        "status_to": FORM100_STATUS_DRAFT,
                    },
                    "entity": {"type": "form100", "id": str(row.id)},
                    "changes": {
                        "format": "before_after",
                        "before": {},
                        "after": {"id": str(row.id), "status": FORM100_STATUS_DRAFT},
                    },
                    "meta": {"expected_version": None, "new_version": int(row.version)},
                },
                ensure_ascii=False,
            )
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="form100",
                entity_id=str(row.id),
                action="create_form100",
                payload_json=payload_json,
            )
            return self._to_card_dto(row=row, marks=marks, stages=stages)

    def update_card(
        self,
        card_id: str,
        request: Form100UpdateRequest,
        actor_id: int | None,
        expected_version: int,
    ) -> Form100CardDto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        update_payload = request.model_dump(exclude_unset=True, exclude={"marks"})
        if "status" in update_payload:
            raise ValueError("Изменение статуса через update_card запрещено")

        with self.session_factory() as session:
            before_row = self.repo.get_card(session, card_id)
            if before_row is None:
                raise ValueError("Карточка Form100 не найдена")
            if str(before_row.status) != FORM100_STATUS_DRAFT:
                raise ValueError("Редактирование подписанной карточки запрещено")

            before_data = self.repo.to_card_dict(before_row)
            merged_payload = dict(before_data)
            merged_payload.update(update_payload)
            validate_card_payload(merged_payload)

            if update_payload:
                row = self.repo.update_card(
                    session,
                    card_id=card_id,
                    payload=update_payload,
                    expected_version=expected_version,
                    actor_login=actor_login,
                )
            else:
                row = self.repo.touch_card(
                    session,
                    card_id=card_id,
                    expected_version=expected_version,
                    actor_login=actor_login,
                )

            before_marks = self.repo.list_marks(session, card_id) if request.marks is not None else []
            if request.marks is not None:
                marks = self.repo.replace_marks(
                    session,
                    card_id=card_id,
                    marks=[item.model_dump() for item in request.marks],
                    actor_login=actor_login,
                )
            else:
                marks = self.repo.list_marks(session, card_id)
            stages = self.repo.list_stages(session, card_id)

            after_data = self.repo.to_card_dict(row)
            changes = build_changed_paths(before_data, after_data)
            if request.marks is not None:
                changes["before"]["marks"] = [self.repo.to_mark_dict(item) for item in before_marks]
                changes["after"]["marks"] = [self.repo.to_mark_dict(item) for item in marks]
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="update",
                status_from=str(before_row.status),
                status_to=str(row.status),
                expected_version=expected_version,
                new_version=int(row.version),
                changes=changes,
            )
            return self._to_card_dto(row=row, marks=marks, stages=stages)

    def add_stage(
        self,
        card_id: str,
        request: Form100StageCreateRequest,
        actor_id: int | None,
    ) -> Form100StageDto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 не найдена")
            if str(row.status) != FORM100_STATUS_DRAFT:
                raise ValueError("Нельзя добавлять этап в подписанную карточку")
            stage = self.repo.add_stage(session, card_id=card_id, payload=request.model_dump())
            row = self.repo.touch_card(
                session,
                card_id=card_id,
                expected_version=int(row.version),
                actor_login=actor_login,
            )
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="add_stage",
                status_from=str(row.status),
                status_to=str(row.status),
                expected_version=int(row.version) - 1,
                new_version=int(row.version),
                changes={
                    "before": {},
                    "after": {"stage": self.repo.to_stage_dict(stage)},
                },
            )
            return Form100StageDto.model_validate(self.repo.to_stage_dict(stage))

    def replace_marks(
        self,
        card_id: str,
        marks: list[Form100MarkDto],
        actor_id: int | None,
        expected_version: int,
    ) -> list[Form100MarkDto]:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 не найдена")
            if str(row.status) != FORM100_STATUS_DRAFT:
                raise ValueError("Нельзя изменять отметки в подписанной карточке")
            before_marks = self.repo.list_marks(session, card_id)
            touched = self.repo.touch_card(
                session,
                card_id=card_id,
                expected_version=expected_version,
                actor_login=actor_login,
            )
            new_marks = self.repo.replace_marks(
                session,
                card_id=card_id,
                marks=[item.model_dump() for item in marks],
                actor_login=actor_login,
            )
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="replace_marks",
                status_from=str(touched.status),
                status_to=str(touched.status),
                expected_version=expected_version,
                new_version=int(touched.version),
                changes={
                    "before": {"marks": [self.repo.to_mark_dict(item) for item in before_marks]},
                    "after": {"marks": [self.repo.to_mark_dict(item) for item in new_marks]},
                },
            )
            return [Form100MarkDto.model_validate(self.repo.to_mark_dict(item)) for item in new_marks]

    def sign_card(
        self,
        card_id: str,
        request: Form100SignRequest,
        actor_id: int | None,
        expected_version: int,
    ) -> Form100CardDto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 не найдена")
            if str(row.status) != FORM100_STATUS_DRAFT:
                raise ValueError("Карточка уже подписана")
            validate_status_transition(str(row.status), FORM100_STATUS_SIGNED)
            before_data = self.repo.to_card_dict(row)
            update_payload = {
                "status": FORM100_STATUS_SIGNED,
                "signed_by": request.signed_by or actor_login,
                "signed_at": _utc_now(),
                "seal_applied": request.seal_applied,
            }
            row = self.repo.update_card(
                session,
                card_id=card_id,
                payload=update_payload,
                expected_version=expected_version,
                actor_login=actor_login,
            )
            marks = self.repo.list_marks(session, card_id)
            stages = self.repo.list_stages(session, card_id)
            after_data = self.repo.to_card_dict(row)
            changes = build_changed_paths(before_data, after_data)
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="sign",
                status_from=FORM100_STATUS_DRAFT,
                status_to=FORM100_STATUS_SIGNED,
                expected_version=expected_version,
                new_version=int(row.version),
                changes=changes,
            )
            return self._to_card_dto(row=row, marks=marks, stages=stages)

    def delete_card(self, card_id: str, actor_id: int | None) -> None:
        with self.session_factory() as session:
            self._require_admin(session, actor_id)
            deleted = self.repo.delete_card(session, card_id)
            if not deleted:
                raise ValueError("Карточка Form100 не найдена")
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="form100",
                entity_id=card_id,
                action="delete_form100",
                payload_json=json.dumps({"schema": "form100.audit.v1"}, ensure_ascii=False),
            )

    def export_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int | None,
        card_id: str | None = None,
        filters: Form100Filters | None = None,
        exported_by: str | None = None,
    ) -> dict[str, Any]:
        file_path = Path(file_path)
        filter_payload = filters.model_dump(exclude_none=True) if filters else {}
        with self.session_factory() as session:
            cards = self.repo.find_cards_for_export(session, card_id=card_id, filters=filter_payload)
            card_rows = [self.repo.to_card_dict(item) for item in cards]
            marks: list[dict[str, object]] = []
            stages: list[dict[str, object]] = []
            for card in cards:
                marks.extend(self.repo.to_mark_dict(item) for item in self.repo.list_marks(session, str(card.id)))
                stages.extend(self.repo.to_stage_dict(item) for item in self.repo.list_stages(session, str(card.id)))

        with _working_temp_dir() as tmp_dir:
            excel_path = tmp_dir / "export.xlsx"
            counts = export_form100_excel(
                cards=cast(list[dict[str, Any]], card_rows),
                marks=cast(list[dict[str, Any]], marks),
                stages=cast(list[dict[str, Any]], stages),
                file_path=excel_path,
            )
            manifest = build_manifest(files=[excel_path], exported_by=exported_by)
            manifest_path = tmp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            file_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.write(excel_path, arcname=excel_path.name)
                zip_file.write(manifest_path, arcname=manifest_path.name)

        package_hash = sha256_file(file_path)
        with self.session_factory() as session:
            session.add(
                models.DataExchangePackage(
                    direction="export",
                    package_format="form100+zip",
                    file_path=str(file_path),
                    sha256=package_hash,
                    created_by=actor_id,
                    notes=json.dumps({"card_id": card_id, "filters": filter_payload}, ensure_ascii=False),
                )
            )
        return {"path": str(file_path), "counts": counts, "sha256": package_hash}

    def import_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int | None,
        mode: str = "merge",
    ) -> dict[str, Any]:
        file_path = Path(file_path)
        actor_login, _actor_role = self._resolve_actor(actor_id)
        with _working_temp_dir() as tmp_dir:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                _safe_extract_zip(zip_file, tmp_dir)

            manifest_path = tmp_dir / "manifest.json"
            if not manifest_path.exists():
                raise ValueError("В архиве отсутствует manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = cast(list[dict[str, Any]], manifest.get("files") or [])
            for entry in files:
                payload_path = tmp_dir / str(entry.get("name"))
                if not payload_path.exists():
                    raise ValueError(f"Файл отсутствует: {entry.get('name')}")
                if sha256_file(payload_path) != str(entry.get("sha256")):
                    raise ValueError(f"Хэш не совпадает: {entry.get('name')}")
            excel_path = tmp_dir / "export.xlsx"
            if not excel_path.exists():
                raise ValueError("В архиве отсутствует export.xlsx")

            import_module = importlib.import_module("app.infrastructure.import.form100_import")
            load_form100_excel = cast(Callable[[Path], dict[str, list[dict[str, Any]]]], import_module.load_form100_excel)
            payload = load_form100_excel(excel_path)

        cards = payload.get("cards", [])
        marks = payload.get("marks", [])
        stages = payload.get("stages", [])
        marks_by_card: dict[str, list[dict[str, Any]]] = {}
        for mark in marks:
            card_key = str(mark.get("card_id") or "")
            marks_by_card.setdefault(card_key, []).append(mark)
        stages_by_card: dict[str, list[dict[str, Any]]] = {}
        for stage in stages:
            card_key = str(stage.get("card_id") or "")
            stages_by_card.setdefault(card_key, []).append(stage)

        added = 0
        updated = 0
        skipped = 0
        with self.session_factory() as session:
            for card_payload in cards:
                incoming_id = str(card_payload.get("id") or "")
                if not incoming_id:
                    continue
                existing = self.repo.get_card(session, incoming_id)
                row_payload = dict(card_payload)
                row_payload.pop("id", None)
                row_payload.setdefault("status", FORM100_STATUS_DRAFT)
                row_payload.setdefault("version", 1)
                if existing is None:
                    added += 1
                    self.repo.create_card(
                        session,
                        card_id=incoming_id,
                        payload=row_payload,
                        actor_login=actor_login,
                    )
                elif mode == "append":
                    skipped += 1
                    continue
                else:
                    updated += 1
                    self.repo.update_card(
                        session,
                        card_id=incoming_id,
                        payload=row_payload,
                        expected_version=int(existing.version),
                        actor_login=actor_login,
                    )
                self.repo.replace_marks(
                    session,
                    card_id=incoming_id,
                    marks=marks_by_card.get(incoming_id, []),
                    actor_login=actor_login,
                )
                self.repo.replace_stages(
                    session,
                    card_id=incoming_id,
                    stages=stages_by_card.get(incoming_id, []),
                )

            package_hash = sha256_file(file_path)
            session.add(
                models.DataExchangePackage(
                    direction="import",
                    package_format="form100+zip",
                    file_path=str(file_path),
                    sha256=package_hash,
                    created_by=actor_id,
                    notes=json.dumps({"mode": mode}, ensure_ascii=False),
                )
            )

        return {
            "path": str(file_path),
            "counts": {"form100_card": len(cards), "form100_mark": len(marks), "form100_stage": len(stages)},
            "summary": {
                "rows_total": len(cards),
                "added": added,
                "updated": updated,
                "skipped": skipped,
                "errors": 0,
            },
            "error_count": 0,
            "errors": [],
        }

    def export_pdf(self, card_id: str, file_path: str | Path, actor_id: int | None) -> dict[str, Any]:
        file_path = Path(file_path)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 не найдена")
            marks = self.repo.list_marks(session, card_id)
            stages = self.repo.list_stages(session, card_id)
            card_payload = self.repo.to_card_dict(row)
            marks_payload = [self.repo.to_mark_dict(item) for item in marks]
            stages_payload = [self.repo.to_stage_dict(item) for item in stages]

        export_form100_pdf(
            card=cast(dict[str, Any], card_payload),
            marks=cast(list[dict[str, Any]], marks_payload),
            stages=cast(list[dict[str, Any]], stages_payload),
            file_path=file_path,
        )
        self._log_pdf_export(actor_id=actor_id, card_id=card_id, file_path=file_path)
        return {"path": str(file_path), "card_id": card_id}

    def _log_pdf_export(self, *, actor_id: int | None, card_id: str, file_path: Path) -> None:
        with self.session_factory() as session:
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="form100",
                entity_id=card_id,
                action="export_pdf",
                payload_json=json.dumps({"path": str(file_path)}, ensure_ascii=False),
            )

    def _write_audit(
        self,
        *,
        session,
        actor_id: int | None,
        actor_role: str,
        card_id: str,
        action: str,
        status_from: str | None,
        status_to: str | None,
        expected_version: int | None,
        new_version: int,
        changes: dict[str, Any],
    ) -> None:
        payload_json = json.dumps(
            {
                "schema": "form100.audit.v1",
                "actor": {"user_id": actor_id, "role": actor_role},
                "event": {
                    "ts": _utc_now().isoformat(),
                    "action": action,
                    "status_from": status_from,
                    "status_to": status_to,
                },
                "entity": {"type": "form100", "id": card_id},
                "changes": {
                    "format": "before_after",
                    "before": changes.get("before", {}),
                    "after": changes.get("after", {}),
                },
                "meta": {"expected_version": expected_version, "new_version": new_version},
            },
            ensure_ascii=False,
            default=str,
        )
        self.audit_repo.add_event(
            session,
            user_id=actor_id,
            entity_type="form100",
            entity_id=card_id,
            action=f"{action}_form100",
            payload_json=payload_json,
        )

    def _require_admin(self, session, actor_id: int | None) -> None:
        if actor_id is None:
            return
        actor = self.user_repo.get_by_id(session, actor_id)
        if actor and actor.role == "admin":
            return
        raise ValueError("Операция доступна только администратору")

    def _resolve_actor(self, actor_id: int | None) -> tuple[str, str]:
        if actor_id is None:
            return "system", "system"
        with self.session_factory() as session:
            actor = self.user_repo.get_by_id(session, actor_id)
            if actor is None:
                return f"user_{actor_id}", "unknown"
            return str(actor.login), str(actor.role)

    def _to_list_item_dto(self, row: models.Form100Card) -> Form100CardListItemDto:
        birth_date = cast(date, row.birth_date)
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        return Form100CardListItemDto(
            id=str(row.id),
            status=str(row.status),
            version=int(row.version),
            last_name=str(row.last_name),
            first_name=str(row.first_name),
            middle_name=cast(str | None, row.middle_name),
            birth_date=birth_date,
            unit=str(row.unit),
            dog_tag_number=cast(str | None, row.dog_tag_number),
            diagnosis_text=str(row.diagnosis_text),
            created_at=cast(datetime, row.created_at),
            updated_at=cast(datetime, row.updated_at),
        )

    def _to_card_dto(
        self,
        *,
        row: models.Form100Card,
        marks: list[models.Form100Mark],
        stages: list[models.Form100Stage],
    ) -> Form100CardDto:
        card_payload = self.repo.to_card_dict(row)
        card_payload["marks"] = [self.repo.to_mark_dict(item) for item in marks]
        card_payload["stages"] = [self.repo.to_stage_dict(item) for item in stages]
        return Form100CardDto.model_validate(card_payload)
