from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT_DIR = Path(__file__).resolve().parents[1]
CORRECTED_REFERENCE_MD = ROOT_DIR / "docs" / "reference_antibiotics_microorganisms_corrected.md"
SEED_JSON = ROOT_DIR / "resources" / "reference_seed.json"
REFERENCE_EXPORT_MD = ROOT_DIR / "docs" / "reference_antibiotics_microorganisms.md"

GROUP_ROW_RE: Final[re.Pattern[str]] = re.compile(
    r"^\| `(ABG-\d{4})` \| (.+?) \| (\d+) \|$"
)
ABX_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^### \d+\. (?P<name>.+) \(`(?P<code>ABG-\d{4})`\)$"
)
MICRO_HEADER_RE: Final[re.Pattern[str]] = re.compile(r"^### \d+\. (?P<name>.+)$")
AUTO_CODE_RE: Final[dict[str, re.Pattern[str]]] = {
    "ABX": re.compile(r"^ABX-\d{4}$"),
    "MIC": re.compile(r"^MIC-\d{4}$"),
}

MANUAL_ABX_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "Полимиксин В": ("Полимиксин",),
}
MANUAL_MICRO_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "Acinetobacter spp.": ("Acinetobacter ssp.",),
    "Acinetobacter pittii": ("Acinetobacter p",),
    "Viridans streptococci (Streptococcus anginosus group)": ("Viridans streptococci",),
}


@dataclass(frozen=True)
class AntibioticGroupDef:
    code: str
    name: str
    expected_count: int


@dataclass(frozen=True)
class AntibioticDef:
    code: str
    name: str
    group_code: str


@dataclass(frozen=True)
class MicroorganismDef:
    code: str
    name: str
    taxon_group: str


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _abbreviated_name(name: str) -> str | None:
    parts = name.split()
    if len(parts) < 2:
        return None
    genus = parts[0]
    if not genus or not genus[0].isalpha():
        return None
    return f"{genus[0]}. {' '.join(parts[1:])}"


def _variant_candidates(name: str, manual_aliases: dict[str, tuple[str, ...]]) -> list[str]:
    candidates = [name]
    candidates.extend(manual_aliases.get(name, ()))

    abbreviated = _abbreviated_name(name)
    if abbreviated is not None:
        candidates.append(abbreviated)

    if " spp." in name:
        candidates.append(name.replace(" spp.", " ssp."))
    if " ssp." in name:
        candidates.append(name.replace(" ssp.", " spp."))

    unique_candidates: list[str] = []
    for item in candidates:
        if item not in unique_candidates:
            unique_candidates.append(item)
    return unique_candidates


def _find_preserved_code(
    *,
    name: str,
    old_items_by_name: dict[str, dict[str, object]],
    used_codes: set[str],
    manual_aliases: dict[str, tuple[str, ...]],
) -> str | None:
    for candidate in _variant_candidates(name, manual_aliases):
        old_item = old_items_by_name.get(candidate)
        if old_item is None:
            continue
        old_code = str(old_item.get("code", ""))
        if old_code and old_code not in used_codes:
            return old_code
    return None


def _next_code(prefix: str, used_codes: set[str]) -> str:
    sequence = 1
    while True:
        code = f"{prefix}-{sequence:04d}"
        if code not in used_codes:
            return code
        sequence += 1


def parse_corrected_reference(path: Path) -> tuple[list[AntibioticGroupDef], list[tuple[str, str]], list[tuple[str, str]]]:
    lines = path.read_text(encoding="utf-8").splitlines()

    groups: list[AntibioticGroupDef] = []
    antibiotics: list[tuple[str, str]] = []
    microorganisms: list[tuple[str, str]] = []

    section = "groups"
    current_group_code: str | None = None
    current_taxon_group: str | None = None

    for line in lines:
        group_match = GROUP_ROW_RE.match(line)
        if group_match is not None:
            groups.append(
                AntibioticGroupDef(
                    code=group_match.group(1),
                    name=group_match.group(2).strip(),
                    expected_count=int(group_match.group(3)),
                )
            )
            continue

        abx_header_match = ABX_HEADER_RE.match(line)
        if abx_header_match is not None:
            section = "antibiotics"
            current_group_code = abx_header_match.group("code")
            continue

        micro_header_match = MICRO_HEADER_RE.match(line)
        if micro_header_match is not None:
            section = "microorganisms"
            current_taxon_group = micro_header_match.group("name").strip()
            continue

        if section == "microorganisms" and line.startswith("## "):
            break

        if line.startswith("- ") and section == "antibiotics" and current_group_code is not None:
            antibiotics.append((line[2:].strip(), current_group_code))
            continue

        if line.startswith("- ") and section == "microorganisms" and current_taxon_group is not None:
            microorganisms.append((line[2:].strip(), current_taxon_group))

    if len(groups) != 18:
        raise ValueError(f"Ожидалось 18 групп антибиотиков, получено {len(groups)}")

    actual_group_counts = {
        group.code: sum(1 for _, group_code in antibiotics if group_code == group.code)
        for group in groups
    }
    mismatched_groups = [
        f"{group.code}: expected={group.expected_count}, actual={actual_group_counts[group.code]}"
        for group in groups
        if actual_group_counts[group.code] != group.expected_count
    ]
    if mismatched_groups:
        raise ValueError(
            "Количество антибиотиков в markdown не совпадает с табличной сводкой: "
            + "; ".join(mismatched_groups)
        )

    return groups, antibiotics, microorganisms


def build_seed_payload() -> tuple[dict[str, object], list[AntibioticGroupDef], list[AntibioticDef], list[MicroorganismDef]]:
    previous_seed = _load_json(SEED_JSON)
    groups, antibiotics_from_md, microorganisms_from_md = parse_corrected_reference(CORRECTED_REFERENCE_MD)

    old_antibiotics = {
        str(item["name"]): item
        for item in previous_seed.get("antibiotics", [])
        if isinstance(item, dict)
    }
    old_microorganisms = {
        str(item["name"]): item
        for item in previous_seed.get("microorganisms", [])
        if isinstance(item, dict)
    }

    used_abx_codes: set[str] = set()
    antibiotics: list[AntibioticDef] = []
    for name, group_code in antibiotics_from_md:
        preserved_code = _find_preserved_code(
            name=name,
            old_items_by_name=old_antibiotics,
            used_codes=used_abx_codes,
            manual_aliases=MANUAL_ABX_ALIASES,
        )
        code = preserved_code or _next_code("ABX", used_abx_codes)
        used_abx_codes.add(code)
        antibiotics.append(AntibioticDef(code=code, name=name, group_code=group_code))

    used_micro_codes: set[str] = set()
    microorganisms: list[MicroorganismDef] = []
    for name, taxon_group in microorganisms_from_md:
        preserved_code = _find_preserved_code(
            name=name,
            old_items_by_name=old_microorganisms,
            used_codes=used_micro_codes,
            manual_aliases=MANUAL_MICRO_ALIASES,
        )
        code = preserved_code or _next_code("MIC", used_micro_codes)
        used_micro_codes.add(code)
        microorganisms.append(MicroorganismDef(code=code, name=name, taxon_group=taxon_group))

    payload = {
        "antibiotic_groups": [{"code": group.code, "name": group.name} for group in groups],
        "antibiotics": [
            {"code": item.code, "name": item.name, "group_code": item.group_code}
            for item in antibiotics
        ],
        "microorganisms": [
            {"code": item.code, "name": item.name, "taxon_group": item.taxon_group}
            for item in microorganisms
        ],
        "ismp_abbreviations": previous_seed.get("ismp_abbreviations", []),
    }
    return payload, groups, antibiotics, microorganisms


def render_reference_markdown(
    groups: list[AntibioticGroupDef],
    antibiotics: list[AntibioticDef],
    microorganisms: list[MicroorganismDef],
) -> str:
    antibiotics_by_group: dict[str, list[AntibioticDef]] = {group.code: [] for group in groups}
    for antibiotic in antibiotics:
        antibiotics_by_group.setdefault(antibiotic.group_code, []).append(antibiotic)

    taxon_order: list[str] = []
    microorganisms_by_taxon: dict[str, list[MicroorganismDef]] = {}
    for microorganism in microorganisms:
        if microorganism.taxon_group not in microorganisms_by_taxon:
            taxon_order.append(microorganism.taxon_group)
            microorganisms_by_taxon[microorganism.taxon_group] = []
        microorganisms_by_taxon[microorganism.taxon_group].append(microorganism)

    lines = [
        "# Справочник антибиотиков, групп антибиотиков и микроорганизмов",
        "",
        "Документ автоматически собран из файла [resources/reference_seed.json](../resources/reference_seed.json).",
        "",
        (
            "Содержимое seed-файла синхронизировано с "
            "[docs/reference_antibiotics_microorganisms_corrected.md]"
            "(./reference_antibiotics_microorganisms_corrected.md)."
        ),
        "",
        "## Сводка",
        "",
        f"- Группы антибиотиков: **{len(groups)}**",
        f"- Антибиотики: **{len(antibiotics)}**",
        f"- Микроорганизмы: **{len(microorganisms)}**",
        f"- Таксономические группы микроорганизмов: **{len(taxon_order)}**",
        "",
        "## Группы антибиотиков",
        "",
        "| Код группы | Название | Количество антибиотиков |",
        "| --- | --- | ---: |",
    ]

    for group in groups:
        lines.append(
            f"| `{group.code}` | {group.name} | {len(antibiotics_by_group.get(group.code, []))} |"
        )

    lines.extend(["", "## Антибиотики по группам", ""])
    for index, group in enumerate(groups, start=1):
        group_antibiotics = antibiotics_by_group.get(group.code, [])
        lines.extend(
            [
                f"### {index}. {group.name} (`{group.code}`)",
                "",
                f"Количество: **{len(group_antibiotics)}**",
                "",
            ]
        )
        for antibiotic in group_antibiotics:
            lines.append(f"- {antibiotic.name}")
        lines.append("")

    lines.extend(
        [
            "## Микроорганизмы",
            "",
            "Микроорганизмы сгруппированы по `taxon_group` в том виде, как они используются в программе.",
            "",
        ]
    )
    for index, taxon_group in enumerate(taxon_order, start=1):
        group_microorganisms = microorganisms_by_taxon[taxon_group]
        lines.extend(
            [
                f"### {index}. {taxon_group}",
                "",
                f"Количество: **{len(group_microorganisms)}**",
                "",
            ]
        )
        for microorganism in group_microorganisms:
            lines.append(f"- {microorganism.name}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    payload, groups, antibiotics, microorganisms = build_seed_payload()
    SEED_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    REFERENCE_EXPORT_MD.write_text(
        render_reference_markdown(groups, antibiotics, microorganisms),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
