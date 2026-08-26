#!/usr/bin/env python3
"""Write a hash-bound 742 candidate receipt from independently run validators.

The writer records automated facts only. Human/browser review can be attached with
an explicit, artifact-backed review manifest; deployment is attested separately by
the Pages workflow after it probes the public URL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "assets/models/742.asset-receipt.json"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"

FILES = {
    "asset": ROOT / "assets/models/742.glb",
    "source_blend": ROOT / "source/blender/742-showcase-v1.0.blend",
    "builder": ROOT / "scripts/build_742.py",
    "receipt_writer": ROOT / "scripts/write_742_receipt.py",
    "receipt_validator": ROOT / "scripts/validate_742_receipt.py",
    "project_readme": ROOT / "README.md",
    "package_manifest": ROOT / "package.json",
    "pages_workflow": ROOT / ".github/workflows/pages.yml",
    "configuration": ROOT / "machines/742/742.configuration.json",
    "mechanism": ROOT / "machines/742/mechanism.json",
    "source_manifest": ROOT / "docs/research/742/SOURCE_MANIFEST.json",
    "mechanism_evidence": ROOT / "docs/research/742/MECHANISM_EVIDENCE.json",
    "research_readme": ROOT / "docs/research/742/README.md",
    "references": ROOT / "docs/research/742/REFERENCES.md",
    "configuration_notes": ROOT / "docs/research/742/CONFIGURATION.md",
    "dimensions_notes": ROOT / "docs/research/742/DIMENSIONS.md",
    "articulation_notes": ROOT / "docs/research/742/ARTICULATION.md",
    "source_reconciliation": ROOT / "docs/research/742/SOURCE_RECONCILIATION.md",
    "detailed_reconstruction": ROOT / "docs/research/742/DETAILED_RECONSTRUCTION.md",
    "comparison_matrix": ROOT / "docs/research/742/COMPARISON_MATRIX.md",
    "rights_boundary": ROOT / "docs/research/742/RIGHTS_AND_BIM_BOUNDARY.md",
    "reference_board_boundary": ROOT / "docs/research/742/reference-board/README.md",
    "review_renderer": ROOT / "scripts/render_742_preview.py",
}
RUNTIME_FILES = [
    ROOT / "742/index.html",
    ROOT / "viewer.css",
    ROOT / "viewer/742.css",
    ROOT / "viewer/742-runtime.js",
    ROOT / "machines/742/machine.js",
    ROOT / "machines/742/articulation.js",
    ROOT / "machines/742/inspector.js",
    ROOT / "machines/742/cameras.js",
    ROOT / "machines/742/version.js",
]
AUTOMATED_CHECKS = {
    "600s_viewer_contract": ("validate_viewer_contract.py", []),
    "600s_configuration_contract": ("validate_600s_configuration.py", []),
    "600s_asset_contract": ("validate_600s_glb.py", []),
    "es1930m_release_receipt": ("validate_es1930m_receipt.py", []),
    "es1930m_kinematics_contract": ("validate_es1930m_kinematics.py", []),
    "es1930m_asset_contract": ("validate_es1930m_glb.py", []),
    "evidence_ledger": ("validate_742_evidence.py", ["--manifest-only"]),
    "asset_contract": ("validate_742_glb.py", []),
    "mechanical_kinematics": ("validate_742_kinematics.py", []),
    "route_contract": ("validate_742_route.py", []),
}
HUMAN_GATES = (
    "stowed_visual_fidelity",
    "extended_visual_fidelity",
    "cab_closeup_fidelity",
    "desktop_browser_interaction",
    "mobile_browser_interaction",
    "accessibility_assistive_technology",
    "semantic_selection",
    "performance_profile",
    "600s_browser_regression",
    "es1930m_browser_regression",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_file_record(path: Path) -> dict:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise RuntimeError(f"Receipt artifacts must be inside the repository: {path}") from error
    if not resolved.is_file():
        raise RuntimeError(f"Missing receipt artifact: {relative}")
    return {"path": str(relative), "sha256": digest(resolved), "bytes": resolved.stat().st_size}


def aggregate_digest(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def run_check(script: str, extra_args: list[str]) -> dict:
    path = ROOT / "scripts" / script
    command = [sys.executable, "-B", str(path), *extra_args]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"Automated check failed: {script} {' '.join(extra_args)}\n{completed.stdout}{completed.stderr}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Automated check did not emit one JSON result: {script}") from error
    if result.get("status") != "PASS":
        raise RuntimeError(f"Automated check did not pass: {script}")
    canonical_result = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    return {
        "status": "pass",
        "validator": relative_file_record(path),
        "arguments": extra_args,
        "result_sha256": hashlib.sha256(canonical_result).hexdigest(),
        "result": result,
    }


def read_review_manifest(path: Path | None, candidate_tree_sha256: str) -> tuple[dict, dict | None]:
    pending = {name: {"status": "pending", "artifact": None} for name in HUMAN_GATES}
    if path is None:
        return pending, None
    record = relative_file_record(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version", "configuration_id", "candidate_tree_sha256",
        "reviewed_source_commit", "environment", "gates",
    }
    if set(manifest) != expected:
        raise RuntimeError("742 review manifest has non-canonical top-level fields")
    if manifest["schema_version"] != "1.0.0" or manifest["configuration_id"] != EXPECTED_ID:
        raise RuntimeError("742 review manifest identity/schema drift")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("reviewed_source_commit", "")):
        raise RuntimeError("742 review manifest requires an exact reviewed source commit")
    if manifest["candidate_tree_sha256"] != candidate_tree_sha256:
        raise RuntimeError("742 review manifest does not bind the current candidate tree")
    commit_check = subprocess.run(
        ["git", "cat-file", "-e", f"{manifest['reviewed_source_commit']}^{{commit}}"],
        cwd=ROOT, capture_output=True, check=False,
    )
    if commit_check.returncode:
        raise RuntimeError("742 reviewed source commit does not resolve in this repository")
    environment = manifest.get("environment")
    if not isinstance(environment, dict) or not environment.get("browser") or not environment.get("os"):
        raise RuntimeError("742 review manifest requires browser and OS environment identity")
    if set(manifest.get("gates") or {}) != set(HUMAN_GATES):
        raise RuntimeError("742 review manifest must address every canonical human gate")
    reviewed = {}
    for name in HUMAN_GATES:
        gate = manifest["gates"][name]
        if set(gate) != {"status", "artifact", "notes"} or gate["status"] != "pass":
            raise RuntimeError(f"742 human gate is not explicitly passed: {name}")
        artifact_path = ROOT / gate["artifact"]["path"]
        actual = relative_file_record(artifact_path)
        if actual != gate["artifact"]:
            raise RuntimeError(f"742 human gate artifact drift: {name}")
        reviewed[name] = {"status": "pass", "artifact": actual}
    return reviewed, {
        "manifest": record,
        "candidate_tree_sha256": candidate_tree_sha256,
        "reviewed_source_commit": manifest["reviewed_source_commit"],
        "environment": environment,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-dir", type=Path, help="Verify every admitted frozen source binary when writing.")
    parser.add_argument("--review-manifest", type=Path, help="Attach a canonical artifact-backed human review manifest.")
    parser.add_argument("--output", type=Path, default=RECEIPT, help="Receipt output path (defaults to the canonical asset receipt).")
    args = parser.parse_args()

    missing = [label for label, path in FILES.items() if not path.is_file()]
    missing.extend(str(path.relative_to(ROOT)) for path in RUNTIME_FILES if not path.is_file())
    if missing:
        raise RuntimeError(f"Missing canonical 742 receipt inputs: {missing}")
    configuration = json.loads(FILES["configuration"].read_text(encoding="utf-8"))
    target_release = configuration.get("target_release", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", target_release):
        raise RuntimeError("742 configuration target release is missing or malformed")

    checks = {name: run_check(script, extra) for name, (script, extra) in AUTOMATED_CHECKS.items()}
    asset_result = checks["asset_contract"]["result"]
    kinematic_result = checks["mechanical_kinematics"]["result"]
    mechanism = json.loads(FILES["mechanism"].read_text(encoding="utf-8"))
    circle_angles = kinematic_result["positive_circle_max_wheel_angles_degrees"]
    mechanical_proof = {
        "asset_sha256": asset_result["sha256"],
        "source_blend_sha256": asset_result["source_blend_sha256"],
        "published_length_less_forks_m": configuration["published_dimensions_m"]["length_less_forks"],
        "posed_glb_length_less_forks_m": asset_result["length_less_forks_m"],
        "published_maximum_lift_height_m": configuration["published_performance"]["maximum_lift_height_m"],
        "posed_level_fork_surface_height_m": kinematic_result["maximum_level_fork_surface_y_m"],
        "published_maximum_forward_reach_m": configuration["published_performance"]["maximum_forward_reach_m"],
        "posed_24in_load_center_forward_reach_m": kinematic_result["maximum_reach_pose"]["forward_reach_m"],
        "evidence_steering_inner_limit_degrees": mechanism["steering"]["visual_inner_limit_degrees"],
        "posed_circle_maximum_wheel_degrees": max(abs(value) for value in circle_angles.values()),
        "published_hydraulic_cylinder_strokes_m": mechanism["hydraulic_cylinder_strokes_m"],
        "posed_evidence_stroke_usage_m": kinematic_result["evidence_stroke_usage_m"],
        "unique_multidimensional_state_samples": kinematic_result["unique_multidimensional_state_samples"],
    }
    if abs(mechanical_proof["posed_glb_length_less_forks_m"] - mechanical_proof["published_length_less_forks_m"]) > 0.015:
        raise RuntimeError("742 receipt length-less-forks proof misses the published 5.76 m envelope")
    if abs(mechanical_proof["posed_level_fork_surface_height_m"] - mechanical_proof["published_maximum_lift_height_m"]) > 0.02:
        raise RuntimeError("742 receipt maximum-height pose proof drift")
    if abs(mechanical_proof["posed_24in_load_center_forward_reach_m"] - mechanical_proof["published_maximum_forward_reach_m"]) > 0.02:
        raise RuntimeError("742 receipt maximum-reach pose proof drift")
    if mechanical_proof["evidence_steering_inner_limit_degrees"] != 55 or mechanical_proof["posed_circle_maximum_wheel_degrees"] != 55.0:
        raise RuntimeError("742 receipt 55-degree steering proof drift")
    if args.sources_dir:
        source_check = run_check(
            "validate_742_evidence.py",
            ["--sources-dir", str(args.sources_dir), "--require-source-binaries"],
        )
        source_verification = {
            "status": "pass",
            "result_sha256": source_check["result_sha256"],
            "verified_count": source_check["result"]["local_binaries_verified_count"],
        }
    else:
        source_verification = {"status": "not_run", "result_sha256": None, "verified_count": 0}

    validator_paths = [ROOT / "scripts" / value[0] for value in AUTOMATED_CHECKS.values()]
    receipt_inputs = list(FILES.values()) + RUNTIME_FILES + validator_paths
    candidate_tree_sha256 = aggregate_digest(receipt_inputs)
    human_gates, review_binding = read_review_manifest(args.review_manifest, candidate_tree_sha256)
    human_complete = all(gate["status"] == "pass" for gate in human_gates.values())
    receipt = {
        "schema_version": "2.0.0",
        "release": f"{target_release}-candidate",
        "release_status": "reviewed_candidate_not_deployed" if human_complete else "candidate_review_pending",
        "written": str(date.today()),
        "configuration_id": EXPECTED_ID,
        "candidate_tree_sha256": candidate_tree_sha256,
        "files": {label: relative_file_record(path) for label, path in FILES.items()},
        "runtime": {
            "files": [str(path.relative_to(ROOT)) for path in RUNTIME_FILES],
            "sha256": aggregate_digest(RUNTIME_FILES),
        },
        "automated_checks": checks,
        "mechanical_proof": mechanical_proof,
        "frozen_source_binary_verification": source_verification,
        "human_review": {
            "status": "pass" if human_complete else "pending",
            "binding": review_binding,
            "gates": human_gates,
        },
        "deployment_attestation": {"status": "not_attested", "artifact": None},
        "boundary": "Visual reconstruction only; not load, stability, service, training, fabrication, or safety authority.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        output_label = str(args.output.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        output_label = str(args.output.resolve())
    print(json.dumps({
        "status": "PASS",
        "receipt": output_label,
        "sha256": digest(args.output),
        "release_status": receipt["release_status"],
        "human_review": receipt["human_review"]["status"],
        "frozen_source_binary_verification": source_verification["status"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
