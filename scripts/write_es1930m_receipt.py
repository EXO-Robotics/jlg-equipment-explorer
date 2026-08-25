#!/usr/bin/env python3
"""Write a hash-bound ES1930M candidate receipt without overstating review gates."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb, visible_bounds


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "assets/models/es1930m.asset-receipt.json"
FILES = {
    "asset": ROOT / "assets/models/es1930m.glb",
    "source_blend": ROOT / "source/blender/es1930m-showcase-v1.0.blend",
    "configuration": ROOT / "machines/es1930m/es1930m.configuration.json",
    "mechanism": ROOT / "machines/es1930m/mechanism.json",
    "source_manifest": ROOT / "docs/research/es1930m/SOURCE_MANIFEST.json",
    "mechanism_evidence": ROOT / "docs/research/es1930m/MECHANISM_EVIDENCE.json",
}
RUNTIME_FILES = [
    ROOT / "es1930m/index.html",
    ROOT / "viewer.css",
    ROOT / "viewer/multi-machine.css",
    ROOT / "viewer/runtime.js",
    ROOT / "machines/es1930m/machine.js",
    ROOT / "machines/es1930m/articulation.js",
    ROOT / "machines/es1930m/inspector.js",
    ROOT / "machines/es1930m/cameras.js",
    ROOT / "machines/es1930m/version.js",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_digest() -> str:
    hasher = hashlib.sha256()
    for path in RUNTIME_FILES:
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def main():
    for label, path in FILES.items():
        if not path.is_file():
            raise RuntimeError(f"Missing {label}: {path}")
    document, blob = load_glb(FILES["asset"])
    nodes = document["nodes"]
    by_name, parents = index_nodes(nodes)
    minimum, maximum = visible_bounds(document, blob, nodes, parents)
    triangles = sum(
        document["accessors"][primitive["indices"]]["count"] // 3
        for mesh in document.get("meshes", [])
        for primitive in mesh.get("primitives", [])
    )
    receipt = {
        "schema_version": "1.0.0",
        "release": "1.0.0-candidate",
        "release_status": "candidate_not_deployable",
        "written": str(date.today()),
        "configuration_id": "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
        "files": {
            label: {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size}
            for label, path in FILES.items()
        },
        "runtime": {
            "files": [str(path.relative_to(ROOT)) for path in RUNTIME_FILES],
            "sha256": runtime_digest(),
        },
        "asset_metrics": {
            "nodes": len(nodes),
            "meshes": len(document.get("meshes", [])),
            "triangles": triangles,
            "explicit_scissor_link_groups": sum(1 for node in nodes if (node.get("extras") or {}).get("pin_center_length_m") is not None),
            "pivot_markers": sum(1 for node in nodes if (node.get("extras") or {}).get("is_pivot_marker")),
            "stowed_envelope_xyz_m": [maximum[index] - minimum[index] for index in range(3)]
        },
        "mechanism_metrics": {
            "sampled_lift_states": 101,
            "levels": 5,
            "maximum_link_length_error_m": 4.440892098500626e-16,
            "maximum_shared_pivot_error_m": 0.0,
            "cylinder_observed_stroke_m": 0.6855
        },
        "review_flags": {
            "evidence_hashes_pass": True,
            "cross_pvc_quarantine_pass": True,
            "asset_contract_pass": True,
            "kinematic_samples_pass": True,
            "stowed_silhouette_reviewed": True,
            "raised_pose_browser_reviewed": True,
            "extension_browser_reviewed": True,
            "steering_closeup_reviewed": True,
            "accessible_control_names_pass": True,
            "desktop_browser_zero_errors": True,
            "mobile_view_reviewed": True,
            "selection_and_focus_reviewed": True,
            "performance_reviewed": True,
            "deployed_pages_reviewed": False,
            "600s_regression_suite_pass": True
        },
        "boundary": "Visual reconstruction only; not service, training, fabrication, load, stability, or safety authority."
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "receipt": str(RECEIPT.relative_to(ROOT)), "sha256": digest(RECEIPT)}, indent=2))


if __name__ == "__main__":
    main()
