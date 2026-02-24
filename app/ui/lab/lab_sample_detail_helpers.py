from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.dto.lab_dto import LabSampleResultUpdate


@dataclass(frozen=True)
class SusceptibilityInput:
    row_number: int
    antibiotic_id: int | None
    ris: str | None
    mic_text: str | None
    method: str | None


@dataclass(frozen=True)
class PhageInput:
    row_number: int
    phage_id: int | None
    phage_free: str
    diameter_text: str | None


def build_susceptibility_payload(rows: list[SusceptibilityInput]) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        ris_text = row.ris.strip() if row.ris else ""
        mic_text = row.mic_text.strip() if row.mic_text else ""
        method_text = row.method.strip() if row.method else ""
        has_any = bool(ris_text or mic_text or method_text)
        if has_any and not row.antibiotic_id:
            raise ValueError(f"Выберите антибиотик в строке {row.row_number}")
        if row.antibiotic_id:
            ris_val = ris_text.upper() or None
            if ris_val and ris_val not in ("R", "I", "S"):
                raise ValueError("RIS должен быть R/I/S")
            items.append(
                {
                    "antibiotic_id": row.antibiotic_id,
                    "ris": ris_val,
                    "mic_mg_l": float(mic_text) if mic_text else None,
                    "method": row.method,
                }
            )
    return items


def build_phage_payload(rows: list[PhageInput]) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        free_text = row.phage_free.strip()
        diameter_text = row.diameter_text.strip() if row.diameter_text else ""
        has_any = bool(free_text or diameter_text)
        if has_any and not row.phage_id and not free_text:
            raise ValueError(f"Укажите фаг или свободное имя в строке {row.row_number}")
        if row.phage_id or free_text:
            diameter = float(diameter_text) if diameter_text else None
            if diameter is not None and diameter < 0:
                raise ValueError("Диаметр должен быть >= 0")
            items.append(
                {
                    "phage_id": row.phage_id,
                    "phage_free": free_text or None,
                    "lysis_diameter_mm": diameter,
                }
            )
    return items


def has_lab_result_data(
    *,
    growth_flag: int | None,
    colony_desc: str,
    microscopy: str,
    cfu: str,
    microorganism_id: int | None,
    microorganism_free: str,
    susceptibility_rows: list[SusceptibilityInput],
    phage_rows: list[PhageInput],
) -> bool:
    if growth_flag is not None:
        return True
    if any([colony_desc.strip(), microscopy.strip(), cfu.strip(), microorganism_id is not None, microorganism_free.strip()]):
        return True
    for susc_row in susceptibility_rows:
        if susc_row.antibiotic_id is not None:
            return True
        if susc_row.ris and susc_row.ris.strip():
            return True
        if susc_row.mic_text and susc_row.mic_text.strip():
            return True
        if susc_row.method and susc_row.method.strip():
            return True
    for phage_row in phage_rows:
        if phage_row.phage_id is not None:
            return True
        if phage_row.phage_free.strip():
            return True
        if phage_row.diameter_text and phage_row.diameter_text.strip():
            return True
    return False


def compose_lab_result_update(
    *,
    has_results: bool,
    growth_flag: int | None,
    growth_result_at: datetime | None,
    colony_desc: str,
    microscopy: str,
    cfu: str,
    qc_status: str | None,
    microorganism_id: int | None,
    microorganism_free: str,
    susceptibility: list[dict],
    phages: list[dict],
) -> LabSampleResultUpdate:
    return LabSampleResultUpdate(
        growth_flag=growth_flag if has_results else None,
        growth_result_at=growth_result_at if has_results else None,
        colony_desc=colony_desc or None if has_results else None,
        microscopy=microscopy or None if has_results else None,
        cfu=cfu or None if has_results else None,
        qc_status=qc_status,
        microorganism_id=microorganism_id if has_results else None,
        microorganism_free=microorganism_free or None if has_results else None,
        susceptibility=susceptibility if has_results else [],
        phages=phages if has_results else [],
    )
