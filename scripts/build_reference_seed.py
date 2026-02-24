from __future__ import annotations

import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
RESOURCES_DIR = ROOT_DIR / "resources"
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

ABX_SOURCE = DOCS_DIR / "extracted_1.txt"
MICRO_SOURCE = DOCS_DIR / "extracted_2.txt"
OUTPUT_PATH = RESOURCES_DIR / "reference_seed.json"


GROUP_HEADINGS = [
    "Пенициллины",
    "Цефалоспорины",
    "Ингибиторозащищенные цефалоспорины",
    "Карбапенемы",
    "Монобактамы",
    "Гликопептиды",
    "Липогликопептиды",
    "Липопептиды",
    "Макролиды",
    "Тетрациклины",
    "Амфениколы",
    "Аминогликозиды",
    "Оксазолидиноны",
    "Анзамицины",
    "Линкозамиды",
    "Глицилциклины",
    "Полимиксины",
    "Производные фосфоновой кислоты",
]

SKIP_ABX_LINES = {
    "Природные",
    "Полусинтетические",
    "Парентеральные",
    "Пероральные",
    "I поколение",
    "II поколение",
    "III поколение",
    "IV поколение",
    "V поколение",
}

JOIN_ABX_WORDS = {
    "Ингибиторозащищенные",
    "Производные",
    "фосфоновой",
    "р-",
    "лактамные",
}


def _normalize_line(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = value.replace("\t", " ")
    value = re.sub(r"[\x00-\x1f]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\b([A-Za-zА-Яа-я])\s+([a-zа-я])", r"\1\2", value)


def _strip_number_prefix(value: str) -> str:
    value = re.sub(r"^\d+\.?\s*", "", value).strip()
    return re.sub(r"^[IVXLC]+\.\s*", "", value).strip()


def _normalize_group_name(value: str) -> str:
    value = value.replace("ХП.", "").replace("ХП", "").strip()
    return value.replace("р-лактамные", "бета-лактамные")


def _parse_antibiotics(text: str) -> tuple[list[dict], list[dict]]:
    groups_by_name: dict[str, dict] = {}
    antibiotics: list[dict] = []
    group_lookup = {g.lower(): g for g in GROUP_HEADINGS}
    current_group: str | None = None

    raw_lines = text.splitlines()
    idx = 0
    merged_lines: list[str] = []
    while idx < len(raw_lines):
        line = _normalize_line(raw_lines[idx])
        idx += 1
        if not line:
            continue
        if not re.search(r"[A-Za-zА-Яа-я]", line):
            continue
        while idx < len(raw_lines):
            peek = _normalize_line(raw_lines[idx])
            if not peek:
                idx += 1
                continue
            if line.endswith("-"):
                line = f"{line[:-1]}{peek}".strip()
                idx += 1
                continue
            if line in JOIN_ABX_WORDS or peek[0].islower():
                line = f"{line} {peek}".strip()
                idx += 1
                continue
            break
        merged_lines.append(line)

    for raw in merged_lines:
        line = _normalize_line(raw)
        if not line:
            continue
        if line.endswith(":"):
            line = line[:-1].strip()
        line = _strip_number_prefix(line)
        if not line:
            continue
        line = _normalize_group_name(line)

        if line in SKIP_ABX_LINES:
            continue
        if not re.search(r"[A-Za-zА-Яа-я]", line):
            continue
        if re.fullmatch(r"[IVXLC]+", line):
            continue
        if "поколение" in line.lower() and re.search(r"\b[ivxlc]+\b", line.lower()):
            continue

        group_key = group_lookup.get(line.lower())
        if group_key:
            current_group = group_key
            if current_group not in groups_by_name:
                groups_by_name[current_group] = {"name": current_group}
            continue

        if current_group is None:
            continue

        for name in re.split(r"\s*,\s*", line):
            name = name.strip()
            if not name:
                continue
            if name in SKIP_ABX_LINES:
                continue
            if not re.search(r"[A-Za-zА-Яа-я]", name):
                continue
            antibiotics.append({"name": name, "group_name": current_group})

    groups = list(groups_by_name.values())
    return groups, antibiotics


def _extract_section_title(line: str) -> str:
    match = re.match(r"Раздел\s+\d+\.\s*(.+)", line)
    return match.group(1).strip() if match else line


def _expand_abbreviation(line: str, last_genus: dict[str, str]) -> str:
    match = re.match(r"^([A-Z])\.\s*(.+)$", line)
    if not match:
        return line
    initial, rest = match.groups()
    genus = last_genus.get(initial)
    if not genus:
        return line
    return f"{genus} {rest}"


def _parse_microorganisms(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    current_group: str | None = None
    last_genus: dict[str, str] = {}
    last_added_index: int | None = None

    raw_lines = text.splitlines()
    idx = 0
    merged_lines: list[str] = []
    while idx < len(raw_lines):
        line = _normalize_line(raw_lines[idx])
        idx += 1
        if not line:
            continue
        while idx < len(raw_lines):
            peek = _normalize_line(raw_lines[idx])
            if not peek:
                idx += 1
                continue
            if line.endswith("-"):
                line = f"{line[:-1]}{peek}".strip()
                idx += 1
                continue
            if line in {"Грамотрицательные", "Грамположительные"} and peek.lower().startswith("бактерии"):
                line = f"{line} {peek}".strip()
                idx += 1
                continue
            if line.lower().startswith("раздел") and not peek.lower().startswith("раздел"):
                line = f"{line} {peek}".strip()
                idx += 1
                break
            if re.fullmatch(r"[A-ZА-Я][a-zа-я]+", line) and peek[0].islower():
                line = f"{line} {peek}".strip()
                idx += 1
                continue
            break
        merged_lines.append(line)

    for raw in merged_lines:
        line = _normalize_line(raw)
        if not line:
            continue
        if line.lower().startswith("приложение"):
            continue
        if line.lower().startswith("перечень"):
            continue
        if line.lower().startswith("копировал"):
            continue
        if line.lower().startswith("плюс необходимо"):
            continue
        if line.lower().startswith("раздел"):
            current_group = _extract_section_title(line)
            continue
        if current_group is None:
            continue

        eskape = "eskape" in line.lower()
        line = re.sub(r"\(.*?eskape.*?\)", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\beskape\b", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\bпатоген(ы)?\b", "", line, flags=re.IGNORECASE)
        line = line.replace(" - ", " ").strip()
        line = line.replace("*", "").strip()
        line = re.sub(r"\(.*?\)", "", line)
        line = re.sub(r"\[.*?\]", "", line)
        line = line.replace('"', "").strip()
        line = _normalize_line(line)
        if not line or not re.search(r"[A-Za-zА-Яа-я]", line):
            if eskape and last_added_index is not None:
                label = results[last_added_index]["taxon_group"]
                if "ESKAPE" not in label:
                    results[last_added_index]["taxon_group"] = f"{label} / ESKAPE"
            continue

        if "Грамотрицательные бактерии" in line:
            current_group = "Грамотрицательные бактерии (ГОБ)"
            continue
        if "Грамположительные бактерии" in line:
            current_group = "Грамположительные бактерии (ГПБ)"
            continue
        if "Микромицеты" in line:
            current_group = "Микромицеты"
            continue

        if line.endswith(":"):
            line = line[:-1].strip()

        line = _expand_abbreviation(line, last_genus)
        line = _normalize_line(line)
        line = re.sub(r"\b([A-ZА-Я])\s+([a-zа-я])", r"\1\2", line)
        if not line:
            continue

        genus_match = re.match(r"^([A-Z][a-z]+)\s+(spp\.|ssp\.)$", line)
        if genus_match:
            genus = genus_match.group(1)
            last_genus[genus[0]] = genus
        else:
            genus_match = re.match(r"^([A-Z][a-z]+)\s+.+", line)
            if genus_match:
                genus = genus_match.group(1)
                last_genus[genus[0]] = genus

        group_label = current_group
        if eskape:
            group_label = f"{current_group} / ESKAPE"

        key = (line, group_label)
        if key in seen:
            continue
        seen.add(key)
        results.append({"name": line, "taxon_group": group_label})
        last_added_index = len(results) - 1

    return results


def _assign_codes(prefix: str, items: list[dict], field: str) -> None:
    for idx, item in enumerate(items, start=1):
        item[field] = f"{prefix}-{idx:04d}"


def main() -> int:
    if not ABX_SOURCE.exists() or not MICRO_SOURCE.exists():
        raise SystemExit("Source files not found. Use docs/extracted_1.txt and docs/extracted_2.txt.")

    abx_text = ABX_SOURCE.read_text(encoding="utf-8")
    micro_text = MICRO_SOURCE.read_text(encoding="utf-8")

    abx_groups, antibiotics = _parse_antibiotics(abx_text)
    microorganisms = _parse_microorganisms(micro_text)

    _assign_codes("ABG", abx_groups, "code")
    _assign_codes("ABX", antibiotics, "code")
    _assign_codes("MIC", microorganisms, "code")

    group_code_by_name = {g["name"]: g["code"] for g in abx_groups}
    for item in antibiotics:
        item["group_code"] = group_code_by_name.get(item["group_name"])
        item.pop("group_name", None)

    payload = {
        "antibiotic_groups": abx_groups,
        "antibiotics": antibiotics,
        "microorganisms": microorganisms,
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
