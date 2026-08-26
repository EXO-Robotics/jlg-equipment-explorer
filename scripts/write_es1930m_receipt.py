#!/usr/bin/env python3
"""Write a hash-bound ES1930M candidate receipt without overstating review gates."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb, visible_bounds
from es1930m_review_binding import PREDEPLOY_GATES, validate_review_binding


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "assets/models/es1930m.asset-receipt.json"
FILES = {
    "asset": ROOT / "assets/models/es1930m.glb",
    "source_blend": ROOT / "source/blender/es1930m-showcase-v1.0.blend",
    "configuration": ROOT / "machines/es1930m/es1930m.configuration.json",
    "mechanism": ROOT / "machines/es1930m/mechanism.json",
    "source_manifest": ROOT / "docs/research/es1930m/SOURCE_MANIFEST.json",
    "mechanism_evidence": ROOT / "docs/research/es1930m/MECHANISM_EVIDENCE.json",
    "visual_comparison": ROOT / "docs/research/es1930m/VISUAL_COMPARISON.md",
    "review_renderer": ROOT / "scripts/render_es1930m_preview.py",
    "review_evidence": ROOT / "docs/research/es1930m/REVIEW_EVIDENCE.json",
}
RUNTIME_FILES = [
    ROOT / "es1930m/index.html",
    ROOT / "viewer.css",
    ROOT / "viewer/multi-machine.css",
    ROOT / "viewer/machine-tabs.css",
    ROOT / "viewer/runtime.js",
    ROOT / "viewer/auto-override.mjs",
    ROOT / "viewer/pointer-gestures.mjs",
    ROOT / "viewer/presentation-route.mjs",
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
    kinematics = json.loads(subprocess.check_output(
        [sys.executable, "-B", str(ROOT / "scripts/validate_es1930m_kinematics.py")],
        cwd=ROOT,
        text=True,
    ))
    if kinematics.get("status") != "PASS":
        raise RuntimeError("ES1930M kinematic validator did not pass")
    reviews = json.loads(FILES["review_evidence"].read_text(encoding="utf-8"))
    current_runtime = runtime_digest()
    current_asset = digest(FILES["asset"])
    receipt_identity = {
        "configuration_id": "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
        "release": "1.0.5",
        "files": {"asset": {"sha256": current_asset}},
        "runtime": {"sha256": current_runtime},
    }
    receipt_600s = json.loads((ROOT / "assets/models/600s.asset-receipt.json").read_text(encoding="utf-8"))
    binding_error = None
    try:
        binding_report = validate_review_binding(reviews, receipt=receipt_identity, receipt_600s=receipt_600s)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        binding_report = None
        binding_error = str(error)
    review_flags = {}
    for gate, record in reviews.get("gates", {}).items():
        exact_record = bool(
            record.get("status") == "pass"
            and record.get("reviewed_runtime_sha256") == current_runtime
            and record.get("reviewed_asset_sha256") == current_asset
            and str(record.get("method", "")).strip()
            and str(record.get("evidence", "")).strip()
        )
        review_flags[gate] = exact_record and (gate == "deployed_pages_reviewed" or binding_report is not None)
    release_ready = bool(review_flags) and all(review_flags.values())
    receipt = {
        "schema_version": "1.0.0",
        # Artifact identity is stable across deployment review; release_status
        # alone records whether the exact public bytes have been approved.
        "release": "1.0.5",
        "release_status": "release" if release_ready else "candidate_not_deployable",
        "written": str(date.today()),
        "configuration_id": "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
        "files": {
            label: {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "bytes": path.stat().st_size}
            for label, path in FILES.items()
        },
        "runtime": {
            "files": [str(path.relative_to(ROOT)) for path in RUNTIME_FILES],
            "sha256": current_runtime,
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
            "sampled_lift_states": kinematics["samples"],
            "levels": kinematics["levels"],
            "maximum_link_length_error_m": kinematics["maximum_link_length_error_m"],
            "maximum_shared_pivot_error_m": kinematics["maximum_shared_pivot_error_m"],
            "maximum_rear_fixed_anchor_error_m": kinematics["maximum_rear_fixed_anchor_error_m"],
            "maximum_translation_per_0_01_sample_m": kinematics["maximum_translation_per_0_01_sample_m"],
            "cylinder_observed_stroke_m": kinematics["cylinder_observed_stroke_m"],
            "collision_proxy_assertions": kinematics["collision_proxy_assertions"],
            "collision_proxy_status": kinematics["collision_proxy_status"],
        },
        "review_flags": review_flags,
        "review_binding": {
            "status": "exact_executable_predeploy_evidence" if binding_report is not None else "pending_or_stale",
            "predeploy_gates": binding_report["predeploy_gates"] if binding_report is not None else 0,
            "error": binding_error,
        },
        "boundary": "Visual reconstruction only; not service, training, fabrication, load, stability, or safety authority."
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "receipt": str(RECEIPT.relative_to(ROOT)), "sha256": digest(RECEIPT)}, indent=2))


if __name__ == "__main__":
    main()
