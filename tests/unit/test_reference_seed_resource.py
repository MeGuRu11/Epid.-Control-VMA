from __future__ import annotations

import json
from pathlib import Path


def test_reference_seed_matches_corrected_reference_lists() -> None:
    seed = json.loads(Path("resources/reference_seed.json").read_text(encoding="utf-8"))

    antibiotic_names = {item["name"] for item in seed["antibiotics"]}
    microorganism_names = {item["name"] for item in seed["microorganisms"]}
    taxon_groups = {item["taxon_group"] for item in seed["microorganisms"]}

    assert len(seed["antibiotic_groups"]) == 18
    assert len(seed["antibiotics"]) == 47
    assert len(seed["microorganisms"]) == 840
    assert len(taxon_groups) == 5

    assert "Полимиксин В" in antibiotic_names
    assert "Полимиксин" not in antibiotic_names
    assert "В" not in antibiotic_names

    assert "Acinetobacter spp." in microorganism_names
    assert "Acinetobacter ssp." not in microorganism_names
    assert "Acinetobacter pittii" in microorganism_names
    assert "ittii" not in microorganism_names
