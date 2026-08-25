#!/usr/bin/env python3
"""Fail closed if the frozen detailed-600S configuration contract drifts."""

from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "assets/models/600s.configuration.json"
EXPECTED_ID = "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696"
EXPECTED_HITS = ["Chassis_Hit", "Turntable_Hit", "Boom_Hit", "Telescope_Hit", "Platform_Hit"]
EXPECTED_DIMENSIONS = {
    "stowed_envelope": [8.71, 2.48, 2.5],
    "wheelbase": 2.5,
    "ground_clearance": 0.29,
    "tailswing": 1.22,
    "platform": [0.91, 2.44],
}


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("Frozen configuration identity drift")
    if config.get("model") != "600S" or config.get("pvc") != "2607":
        raise RuntimeError("Model/PVC drift")
    if config.get("published_dimensions_m") != EXPECTED_DIMENSIONS:
        raise RuntimeError("Published dimensional contract drift")
    if config.get("interaction_volumes") != EXPECTED_HITS:
        raise RuntimeError("Interaction-volume contract drift")

    choices = config.get("choices") or {}
    expected_choices = {
        "drive": "4WD_HYDROSTATIC",
        "steer": "2WS_FRONT",
        "engine": "DEUTZ_D2_9L4_TIER4F_49HP",
        "tires": "355_55D625_FOAM_FILLED_STANDARD",
        "platform": "B3_RAPID_REPLACE_36X96_SWING_GATE",
        "hoods": "B3_DCPD",
        "options": [],
    }
    if choices != expected_choices:
        raise RuntimeError("Frozen option/configuration drift")

    edges = config.get("required_parent_edges") or {}
    if not edges or "600S_ROOT" in edges:
        raise RuntimeError("Invalid root/parent contract")
    for node in edges:
        visited = {node}
        parent = edges[node]
        while parent != "600S_ROOT":
            if parent in visited:
                raise RuntimeError(f"Hierarchy cycle at {parent}")
            visited.add(parent)
            if parent not in edges:
                raise RuntimeError(f"Hierarchy parent {parent} is not rooted")
            parent = edges[parent]

    required_by_section = {
        node
        for section in (config.get("sections") or {}).values()
        for node in section.get("required_nodes", [])
    }
    missing = sorted(node for node in required_by_section if node not in edges)
    if missing:
        raise RuntimeError(f"Section nodes missing from hierarchy: {missing}")

    for source in (config.get("source_publications") or {}).values():
        if not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
            raise RuntimeError(f"Invalid source checksum for {source.get('publication')}")

    authority = config.get("authority_policy") or {}
    if authority.get("manual_diagrams_are_fabrication_dimensions") is not False:
        raise RuntimeError("Manual diagrams must not be treated as fabrication dimensions")
    if authority.get("safety_or_service_simulation") is not False:
        raise RuntimeError("Safety/service simulation must remain out of scope")
    if authority.get("standalone_pvc2601_schematics_admitted") is not False:
        raise RuntimeError("Standalone PVC 2601 schematics must remain quarantined")

    print(json.dumps({
        "status": "PASS",
        "configuration_id": config["configuration_id"],
        "required_parent_edges": len(edges),
        "sections": sorted(config["sections"]),
        "source_publications": sorted(source["publication"] for source in config["source_publications"].values()),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
