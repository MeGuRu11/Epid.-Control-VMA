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

from app.application.dto.form100_v2_dto import (
    Form100CardV2Dto,
    Form100CardV2ListItemDto,
    Form100CreateV2Request,
    Form100SignV2Request,
    Form100UpdateV2Request,
    Form100V2Filters,
)
from app.config import DATA_DIR
from app.domain.models.form100_v2 import FORM100_V2_STATUS_DRAFT, FORM100_V2_STATUS_SIGNED
from app.domain.rules.form100_rules_v2 import (
    build_changed_paths_v2,
    validate_card_payload_v2,
    validate_status_transition_v2,
)
from app.infrastructure.db import models_sqlalchemy as models
from app.infrastructure.db.repositories.audit_repo import AuditLogRepository
from app.infrastructure.db.repositories.form100_repo_v2 import Form100RepositoryV2
from app.infrastructure.db.repositories.user_repo import UserRepository
from app.infrastructure.db.session import session_scope
from app.infrastructure.export.form100_export_v2 import build_manifest_v2, export_form100_json
from app.infrastructure.reporting.form100_pdf_report_v2 import export_form100_pdf_v2
from app.infrastructure.security.sha256 import sha256_file

FORM100_V2_ARTIFACT_DIR = DATA_DIR / "artifacts" / "form100_v2"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@contextmanager
def _working_temp_dir() -> Iterator[Path]:
    roots = [Path(tempfile.gettempdir()), Path.cwd() / "tmp_run"]
    last_error: OSError | None = None
    for root in roots:
        temp_dir = root / f"form100-v2-{uuid4().hex}"
        try:
            root.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            last_error = exc
            shutil.rmtree(temp_dir, ignore_errors=True)
            continue
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return
    raise OSError("Не удалось создать временный каталог Form100 V2") from last_error


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


class Form100ServiceV2:
    def __init__(
        self,
        repo: Form100RepositoryV2 | None = None,
        user_repo: UserRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        session_factory: Callable = session_scope,
    ) -> None:
        self.repo = repo or Form100RepositoryV2()
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditLogRepository()
        self.session_factory = session_factory

    def list_cards(
        self,
        filters: Form100V2Filters | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Form100CardV2ListItemDto]:
        filter_payload = filters.model_dump(exclude_none=True) if filters else {}
        with self.session_factory() as session:
            rows = self.repo.list_cards(session, filters=filter_payload, limit=limit, offset=offset)
            return [
                Form100CardV2ListItemDto(
                    id=str(item.id),
                    status=str(item.status),
                    version=int(item.version),
                    main_full_name=str(item.main_full_name),
                    birth_date=cast(date | None, item.birth_date),
                    main_unit=cast(str | None, item.main_unit),
                    main_id_tag=cast(str | None, item.main_id_tag),
                    main_diagnosis=cast(str | None, item.main_diagnosis),
                    updated_at=cast(datetime, item.updated_at),
                    is_archived=bool(item.is_archived),
                )
                for item in rows
            ]

    def get_card(self, card_id: str) -> Form100CardV2Dto:
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 V2 не найдена")
            data_row = self.repo.get_data(session, card_id)
            payload = self.repo.to_card_dict(row, data_row)
            return Form100CardV2Dto.model_validate(payload)

    def create_card(self, request: Form100CreateV2Request, actor_id: int | None) -> Form100CardV2Dto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        data_payload = request.data.model_dump()
        _inject_denormalized_fields(
            data_payload,
            main_full_name=request.main_full_name,
            main_unit=request.main_unit,
            main_id_tag=request.main_id_tag,
            main_diagnosis=request.main_diagnosis,
        )
        validate_card_payload_v2(
            {
                "main_full_name": request.main_full_name,
                "main_unit": request.main_unit,
                "main_diagnosis": request.main_diagnosis,
                **data_payload,
            }
        )
        with self.session_factory() as session:
            row, data_row = self.repo.create_card(
                session,
                payload={
                    "emr_case_id": request.emr_case_id,
                    "main_full_name": request.main_full_name,
                    "main_unit": request.main_unit,
                    "main_id_tag": request.main_id_tag,
                    "main_diagnosis": request.main_diagnosis,
                    "birth_date": request.birth_date,
                    "status": FORM100_V2_STATUS_DRAFT,
                },
                data_payload=data_payload,
                actor_login=actor_login,
            )
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=str(row.id),
                action="create",
                status_from=None,
                status_to=FORM100_V2_STATUS_DRAFT,
                expected_version=None,
                new_version=int(row.version),
                changes={"before": {}, "after": self.repo.to_card_dict(row, data_row)},
            )
            return Form100CardV2Dto.model_validate(self.repo.to_card_dict(row, data_row))

    def update_card(
        self,
        card_id: str,
        request: Form100UpdateV2Request,
        actor_id: int | None,
        expected_version: int,
    ) -> Form100CardV2Dto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 V2 не найдена")
            if bool(row.is_archived):
                raise ValueError("Архивированная карточка Form100 V2 недоступна для редактирования")
            if str(row.status) != FORM100_V2_STATUS_DRAFT:
                raise ValueError("Редактирование подписанной карточки Form100 V2 запрещено")

            before_data_row = self.repo.get_data(session, card_id)
            before_payload = self.repo.to_card_dict(row, before_data_row)

            merged_card_payload: dict[str, object] = {
                "emr_case_id": request.emr_case_id if request.emr_case_id is not None else row.emr_case_id,
                "main_full_name": request.main_full_name or str(row.main_full_name),
                "main_unit": request.main_unit if request.main_unit is not None else row.main_unit,
                "main_id_tag": request.main_id_tag if request.main_id_tag is not None else row.main_id_tag,
                "main_diagnosis": request.main_diagnosis if request.main_diagnosis is not None else row.main_diagnosis,
                "birth_date": request.birth_date if request.birth_date is not None else row.birth_date,
            }
            merged_data_payload = (
                request.data.model_dump()
                if request.data is not None
                else cast(dict[str, Any], before_payload.get("data") or {})
            )
            _inject_denormalized_fields(
                merged_data_payload,
                main_full_name=str(merged_card_payload["main_full_name"]),
                main_unit=str(merged_card_payload["main_unit"] or ""),
                main_id_tag=cast(str | None, merged_card_payload.get("main_id_tag")),
                main_diagnosis=str(merged_card_payload["main_diagnosis"] or ""),
            )
            validate_card_payload_v2({**merged_card_payload, **merged_data_payload})

            row, data_row = self.repo.update_card(
                session,
                card_id=card_id,
                payload=merged_card_payload,
                data_payload=merged_data_payload,
                expected_version=expected_version,
                actor_login=actor_login,
            )
            after_payload = self.repo.to_card_dict(row, data_row)
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="update",
                status_from=str(before_payload.get("status") or FORM100_V2_STATUS_DRAFT),
                status_to=str(after_payload.get("status") or FORM100_V2_STATUS_DRAFT),
                expected_version=expected_version,
                new_version=int(row.version),
                changes=build_changed_paths_v2(
                    cast(dict[str, Any], before_payload),
                    cast(dict[str, Any], after_payload),
                ),
            )
            return Form100CardV2Dto.model_validate(after_payload)

    def sign_card(
        self,
        card_id: str,
        request: Form100SignV2Request,
        actor_id: int | None,
        expected_version: int,
    ) -> Form100CardV2Dto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 V2 не найдена")
            if bool(row.is_archived):
                raise ValueError("Архивированная карточка Form100 V2 недоступна для подписания")
            validate_status_transition_v2(str(row.status), FORM100_V2_STATUS_SIGNED)

            before_data_row = self.repo.get_data(session, card_id)
            before_payload = self.repo.to_card_dict(row, before_data_row)
            row, data_row = self.repo.update_card(
                session,
                card_id=card_id,
                payload={
                    "status": FORM100_V2_STATUS_SIGNED,
                    "signed_by": request.signed_by or actor_login,
                    "signed_at": _utc_now(),
                },
                data_payload=None,
                expected_version=expected_version,
                actor_login=actor_login,
            )
            after_payload = self.repo.to_card_dict(row, data_row)
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="sign",
                status_from=FORM100_V2_STATUS_DRAFT,
                status_to=FORM100_V2_STATUS_SIGNED,
                expected_version=expected_version,
                new_version=int(row.version),
                changes=build_changed_paths_v2(
                    cast(dict[str, Any], before_payload),
                    cast(dict[str, Any], after_payload),
                ),
            )
            return Form100CardV2Dto.model_validate(after_payload)

    def archive_card(self, card_id: str, actor_id: int | None, expected_version: int) -> Form100CardV2Dto:
        actor_login, actor_role = self._resolve_actor(actor_id)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 V2 не найдена")
            before_data_row = self.repo.get_data(session, card_id)
            before_payload = self.repo.to_card_dict(row, before_data_row)
            row = self.repo.archive_card(
                session,
                card_id=card_id,
                expected_version=expected_version,
                actor_login=actor_login,
            )
            after_payload = self.repo.to_card_dict(row, before_data_row)
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="archive",
                status_from=str(before_payload.get("status")),
                status_to=str(after_payload.get("status")),
                expected_version=expected_version,
                new_version=int(row.version),
                changes=build_changed_paths_v2(
                    cast(dict[str, Any], before_payload),
                    cast(dict[str, Any], after_payload),
                ),
            )
            return Form100CardV2Dto.model_validate(after_payload)

    def delete_card(self, card_id: str, actor_id: int | None) -> None:
        with self.session_factory() as session:
            self._require_admin(session, actor_id)
            deleted = self.repo.delete_card(session, card_id)
            if not deleted:
                raise ValueError("Карточка Form100 V2 не найдена")
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="form100",
                entity_id=card_id,
                action="form100_delete",
                payload_json=json.dumps({"schema": "form100.audit.v2"}, ensure_ascii=False),
            )

    def export_pdf(self, card_id: str, file_path: str | Path, actor_id: int | None) -> dict[str, Any]:
        actor_login, actor_role = self._resolve_actor(actor_id)
        file_path = Path(file_path)
        with self.session_factory() as session:
            row = self.repo.get_card(session, card_id)
            if row is None:
                raise ValueError("Карточка Form100 V2 не найдена")
            data_row = self.repo.get_data(session, card_id)
            payload = self.repo.to_card_dict(row, data_row)

        export_form100_pdf_v2(card=payload, file_path=file_path)
        artifact_hash = sha256_file(file_path)
        with self.session_factory() as session:
            row = self.repo.set_pdf_artifact(
                session,
                card_id=card_id,
                artifact_path=str(file_path),
                artifact_sha256=artifact_hash,
                actor_login=actor_login,
            )
            self._write_audit(
                session=session,
                actor_id=actor_id,
                actor_role=actor_role,
                card_id=card_id,
                action="pdf_generate",
                status_from=str(row.status),
                status_to=str(row.status),
                expected_version=int(row.version) - 1,
                new_version=int(row.version),
                changes={
                    "before": {},
                    "after": {"artifact_path": str(file_path), "artifact_sha256": artifact_hash},
                },
            )
        return {"path": str(file_path), "card_id": card_id, "sha256": artifact_hash}

    def export_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int | None,
        card_id: str | None = None,
        filters: Form100V2Filters | None = None,
        exported_by: str | None = None,
    ) -> dict[str, Any]:
        filter_payload = filters.model_dump(exclude_none=True) if filters else {}
        with self.session_factory() as session:
            rows = self.repo.find_cards_for_export(session, card_id=card_id, filters=filter_payload)
            cards_payload = [self.repo.to_card_dict(item, self.repo.get_data(session, str(item.id))) for item in rows]

        with _working_temp_dir() as tmp_dir:
            json_path = tmp_dir / "form100.json"
            counts = export_form100_json(cards_payload, json_path)

            form_dir = tmp_dir / "form100"
            form_dir.mkdir(parents=True, exist_ok=True)
            files = [json_path]
            for card in cards_payload:
                card_pdf_path = form_dir / f"{card['id']}.pdf"
                export_form100_pdf_v2(card=card, file_path=card_pdf_path)
                files.append(card_pdf_path)

            manifest = build_manifest_v2(files=files, exported_by=exported_by, base_dir=tmp_dir)
            manifest_path = tmp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(manifest_path)

            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(json_path, arcname="form100.json")
                zf.write(manifest_path, arcname="manifest.json")
                for card in cards_payload:
                    card_pdf_path = form_dir / f"{card['id']}.pdf"
                    zf.write(card_pdf_path, arcname=f"form100/{card['id']}.pdf")

        package_hash = sha256_file(file_path)
        with self.session_factory() as session:
            session.add(
                models.DataExchangePackage(
                    direction="export",
                    package_format="form100_v2+zip",
                    file_path=str(file_path),
                    sha256=package_hash,
                    created_by=actor_id,
                    notes=json.dumps({"card_id": card_id, "filters": filter_payload}, ensure_ascii=False),
                )
            )
            self.audit_repo.add_event(
                session,
                user_id=actor_id,
                entity_type="form100",
                entity_id=card_id or "-",
                action="form100_export",
                payload_json=json.dumps(
                    {"schema": "form100.audit.v2", "count": len(cards_payload), "path": str(file_path)},
                    ensure_ascii=False,
                ),
            )
        return {"path": str(file_path), "counts": counts, "sha256": package_hash}

    def import_package_zip(
        self,
        *,
        file_path: str | Path,
        actor_id: int | None,
        mode: str = "merge",
    ) -> dict[str, Any]:
        actor_login, actor_role = self._resolve_actor(actor_id)
        file_path = Path(file_path)
        with _working_temp_dir() as tmp_dir:
            with zipfile.ZipFile(file_path, "r") as zf:
                _safe_extract_zip(zf, tmp_dir)

            manifest_path = tmp_dir / "manifest.json"
            if not manifest_path.exists():
                raise ValueError("В архиве отсутствует manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = cast(list[dict[str, Any]], manifest.get("files") or [])
            for entry in files:
                payload_path = (tmp_dir / str(entry.get("name"))).resolve()
                if not payload_path.exists():
                    raise ValueError(f"Файл отсутствует: {entry.get('name')}")
                if sha256_file(payload_path) != str(entry.get("sha256")):
                    raise ValueError(f"Хэш не совпадает: {entry.get('name')}")

            json_path = tmp_dir / "form100.json"
            if not json_path.exists():
                raise ValueError("В архиве отсутствует form100.json")
            import_module = importlib.import_module("app.infrastructure.import.form100_import_v2")
            load_form100_json = cast(Callable[[Path], list[dict[str, Any]]], import_module.load_form100_json)
            cards = load_form100_json(json_path)

            added = 0
            updated = 0
            skipped = 0
            with self.session_factory() as session:
                for item in cards:
                    incoming_id = str(item.get("id") or "").strip() or str(uuid4())
                    existing = self.repo.get_card(session, incoming_id)
                    incoming_data = cast(dict[str, Any], item.get("data") or {})
                    card_payload = {
                        "emr_case_id": item.get("emr_case_id"),
                        "main_full_name": item.get("main_full_name") or "",
                        "main_unit": item.get("main_unit") or "",
                        "main_id_tag": item.get("main_id_tag"),
                        "main_diagnosis": item.get("main_diagnosis"),
                        "birth_date": item.get("birth_date"),
                        "status": item.get("status") or FORM100_V2_STATUS_DRAFT,
                        "signed_by": item.get("signed_by"),
                        "signed_at": item.get("signed_at"),
                        "legacy_card_id": item.get("legacy_card_id"),
                        "is_archived": bool(item.get("is_archived")),
                    }
                    try:
                        validate_card_payload_v2({**card_payload, **incoming_data})
                    except Exception:  # noqa: BLE001
                        if mode == "append":
                            skipped += 1
                            continue
                    if existing is None:
                        added += 1
                        self.repo.create_card(
                            session,
                            card_id=incoming_id,
                            payload=card_payload,
                            data_payload=incoming_data,
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
                            payload=card_payload,
                            data_payload=incoming_data,
                            expected_version=int(existing.version),
                            actor_login=actor_login,
                        )

                    pdf_path = tmp_dir / "form100" / f"{incoming_id}.pdf"
                    if pdf_path.exists():
                        artifact_path = self._store_imported_pdf(card_id=incoming_id, source_pdf=pdf_path)
                        artifact_hash = sha256_file(artifact_path)
                        self.repo.set_pdf_artifact(
                            session,
                            card_id=incoming_id,
                            artifact_path=str(artifact_path),
                            artifact_sha256=artifact_hash,
                            actor_login=actor_login,
                        )

                package_hash = sha256_file(file_path)
                session.add(
                    models.DataExchangePackage(
                        direction="import",
                        package_format="form100_v2+zip",
                        file_path=str(file_path),
                        sha256=package_hash,
                        created_by=actor_id,
                        notes=json.dumps({"mode": mode}, ensure_ascii=False),
                    )
                )
                self.audit_repo.add_event(
                    session,
                    user_id=actor_id,
                    entity_type="form100",
                    entity_id="-",
                    action="form100_import",
                    payload_json=json.dumps(
                        {
                            "schema": "form100.audit.v2",
                            "summary": {"rows_total": len(cards), "added": added, "updated": updated, "skipped": skipped},
                            "actor_role": actor_role,
                        },
                        ensure_ascii=False,
                    ),
                )

        return {
            "path": str(file_path),
            "counts": {"form100": len(cards)},
            "summary": {"rows_total": len(cards), "added": added, "updated": updated, "skipped": skipped, "errors": 0},
            "error_count": 0,
            "errors": [],
        }

    def _store_imported_pdf(self, *, card_id: str, source_pdf: Path) -> Path:
        now = _utc_now()
        target_dir = FORM100_V2_ARTIFACT_DIR / now.strftime("%Y") / now.strftime("%m")
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            target_dir = Path.cwd() / "tmp_run" / "form100_v2_artifacts" / now.strftime("%Y") / now.strftime("%m")
            target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{card_id}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}.pdf"
        shutil.copy2(source_pdf, target_path)
        return target_path

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
                "schema": "form100.audit.v2",
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
            action=f"form100_{action}",
            payload_json=payload_json,
        )

    def _resolve_actor(self, actor_id: int | None) -> tuple[str, str]:
        if actor_id is None:
            return "system", "system"
        with self.session_factory() as session:
            actor = self.user_repo.get_by_id(session, actor_id)
            if actor is None:
                return f"user_{actor_id}", "unknown"
            return str(actor.login), str(actor.role)

    def _require_admin(self, session, actor_id: int | None) -> None:
        if actor_id is None:
            return
        actor = self.user_repo.get_by_id(session, actor_id)
        if actor and actor.role == "admin":
            return
        raise ValueError("Операция доступна только администратору")


def _inject_denormalized_fields(
    data_payload: dict[str, Any],
    *,
    main_full_name: str,
    main_unit: str,
    main_id_tag: str | None,
    main_diagnosis: str,
) -> None:
    main = data_payload.setdefault("main", {})
    if not isinstance(main, dict):
        main = {}
        data_payload["main"] = main
    main.setdefault("main_full_name", main_full_name)
    main.setdefault("main_unit", main_unit)
    if main_id_tag:
        main.setdefault("main_id_tag", main_id_tag)

    bottom = data_payload.setdefault("bottom", {})
    if not isinstance(bottom, dict):
        bottom = {}
        data_payload["bottom"] = bottom
    bottom.setdefault("main_diagnosis", main_diagnosis)
