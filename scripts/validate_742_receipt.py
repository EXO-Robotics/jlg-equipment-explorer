#!/usr/bin/env python3
"""Verify the canonical 742 receipt and independently replay automated checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "assets/models/742.asset-receipt.json"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
CANONICAL_FILES = {
    "asset": "assets/models/742.glb",
    "source_blend": "source/blender/742-showcase-v1.0.blend",
    "builder": "scripts/build_742.py",
    "receipt_writer": "scripts/write_742_receipt.py",
    "receipt_validator": "scripts/validate_742_receipt.py",
    "project_readme": "README.md",
    "package_manifest": "package.json",
    "pages_workflow": ".github/workflows/pages.yml",
    "configuration": "machines/742/742.configuration.json",
    "mechanism": "machines/742/mechanism.json",
    "source_manifest": "docs/research/742/SOURCE_MANIFEST.json",
    "mechanism_evidence": "docs/research/742/MECHANISM_EVIDENCE.json",
    "research_readme": "docs/research/742/README.md",
    "references": "docs/research/742/REFERENCES.md",
    "configuration_notes": "docs/research/742/CONFIGURATION.md",
    "dimensions_notes": "docs/research/742/DIMENSIONS.md",
    "articulation_notes": "docs/research/742/ARTICULATION.md",
    "source_reconciliation": "docs/research/742/SOURCE_RECONCILIATION.md",
    "detailed_reconstruction": "docs/research/742/DETAILED_RECONSTRUCTION.md",
    "comparison_matrix": "docs/research/742/COMPARISON_MATRIX.md",
    "rights_boundary": "docs/research/742/RIGHTS_AND_BIM_BOUNDARY.md",
    "reference_board_boundary": "docs/research/742/reference-board/README.md",
    "review_renderer": "scripts/render_742_preview.py",
}
CANONICAL_RUNTIME = [
    "742/index.html",
    "viewer.css",
    "viewer/742.css",
    "viewer/742-runtime.js",
    "machines/742/machine.js",
    "machines/742/articulation.js",
    "machines/742/inspector.js",
    "machines/742/cameras.js",
    "machines/742/version.js",
]
AUTOMATED_CHECKS = {
    "600s_viewer_contract": ("scripts/validate_viewer_contract.py", []),
    "600s_configuration_contract": ("scripts/validate_600s_configuration.py", []),
    "600s_asset_contract": ("scripts/validate_600s_glb.py", []),
    "es1930m_release_receipt": ("scripts/validate_es1930m_receipt.py", []),
    "es1930m_kinematics_contract": ("scripts/validate_es1930m_kinematics.py", []),
    "es1930m_asset_contract": ("scripts/validate_es1930m_glb.py", []),
    "evidence_ledger": ("scripts/validate_742_evidence.py", ["--manifest-only"]),
    "asset_contract": ("scripts/validate_742_glb.py", []),
    "mechanical_kinematics": ("scripts/validate_742_kinematics.py", []),
    "route_contract": ("scripts/validate_742_route.py", []),
}
HUMAN_GATES = {
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
}
TOP_LEVEL_FIELDS = {
    "schema_version", "release", "release_status", "written", "configuration_id",
    "candidate_tree_sha256", "files", "runtime", "automated_checks",
    "mechanical_proof", "frozen_source_binary_verification", "human_review", "deployment_attestation", "boundary",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_record(record: dict, expected_path: str | None = None) -> Path:
    if set(record) != {"path", "sha256", "bytes"}:
        raise RuntimeError("742 receipt file record schema drift")
    if expected_path is not None and record["path"] != expected_path:
        raise RuntimeError(f"742 receipt path drift: expected {expected_path}, found {record['path']}")
    candidate = Path(record["path"])
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError(f"742 receipt path escapes repository: {candidate}")
    path = ROOT / candidate
    if not path.is_file() or digest(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
        raise RuntimeError(f"742 receipt file drift: {candidate}")
    return path


def aggregate_digest(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def replay_check(name: str, record: dict) -> Path:
    expected_script, expected_args = AUTOMATED_CHECKS[name]
    expected_fields = {"status", "validator", "arguments", "result_sha256", "result"}
    if set(record) != expected_fields or record["status"] != "pass" or record["arguments"] != expected_args:
        raise RuntimeError(f"742 automated check schema/status drift: {name}")
    validator = verify_record(record["validator"], expected_script)
    completed = subprocess.run(
        [sys.executable, "-B", str(validator), *expected_args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"742 automated check replay failed: {name}\n{completed.stdout}{completed.stderr}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"742 automated check replay emitted invalid JSON: {name}") from error
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    if result.get("status") != "PASS" or result != record["result"] or hashlib.sha256(canonical).hexdigest() != record["result_sha256"]:
        raise RuntimeError(f"742 automated check result drift: {name}")
    return validator


def verify_human_review(review: dict, candidate_tree_sha256: str, require_review: bool) -> list[str]:
    if set(review) != {"status", "binding", "gates"} or set(review.get("gates") or {}) != HUMAN_GATES:
        raise RuntimeError("742 human review schema drift")
    incomplete = []
    for name, gate in review["gates"].items():
        if set(gate) != {"status", "artifact"} or gate["status"] not in {"pending", "pass"}:
            raise RuntimeError(f"742 human gate schema drift: {name}")
        if gate["status"] == "pending":
            if gate["artifact"] is not None:
                raise RuntimeError(f"742 pending human gate has an artifact: {name}")
            incomplete.append(name)
        else:
            verify_record(gate["artifact"])
    if incomplete:
        if review["status"] != "pending" or review["binding"] is not None:
            raise RuntimeError("742 pending human review has an invalid aggregate state")
    else:
        if review["status"] != "pass" or not isinstance(review["binding"], dict):
            raise RuntimeError("742 completed human review lacks a binding")
        binding = review["binding"]
        if set(binding) != {"manifest", "candidate_tree_sha256", "reviewed_source_commit", "environment"}:
            raise RuntimeError("742 human review binding schema drift")
        verify_record(binding["manifest"])
        if not re.fullmatch(r"[0-9a-f]{64}", binding["candidate_tree_sha256"]):
            raise RuntimeError("742 human review candidate tree binding is malformed")
        if binding["candidate_tree_sha256"] != candidate_tree_sha256:
            raise RuntimeError("742 human review does not bind this candidate tree")
        if not re.fullmatch(r"[0-9a-f]{40}", binding["reviewed_source_commit"]):
            raise RuntimeError("742 reviewed source commit is malformed")
        environment = binding["environment"]
        if not isinstance(environment, dict) or not environment.get("browser") or not environment.get("os"):
            raise RuntimeError("742 human review environment is incomplete")
    if require_review and incomplete:
        raise RuntimeError(f"742 human review gates incomplete: {sorted(incomplete)}")
    return sorted(incomplete)


def verify_deployment_attestation(path: Path, receipt: dict, receipt_path: Path) -> None:
    attestation = json.loads(path.read_text(encoding="utf-8"))
    fields = {
        "schema_version", "kind", "configuration_id", "source_commit", "workflow_run_url",
        "route_url", "route_http_status", "route_sha256", "asset_url", "asset_http_status",
        "asset_sha256", "asset_bytes", "pages_build_manifest_sha256", "candidate_receipt_sha256",
    }
    if set(attestation) != fields or attestation["schema_version"] != "1.0.0" or attestation["kind"] != "github-pages-http-attestation":
        raise RuntimeError("742 deployment attestation schema drift")
    if attestation["configuration_id"] != EXPECTED_ID:
        raise RuntimeError("742 deployment attestation identity drift")
    if attestation["route_url"] != "https://exo-robotics.github.io/jlg-equipment-explorer/742/":
        raise RuntimeError("742 deployment attestation route is not canonical")
    if attestation["asset_url"] != "https://exo-robotics.github.io/jlg-equipment-explorer/assets/models/742.glb":
        raise RuntimeError("742 deployment attestation asset URL is not canonical")
    if attestation["route_http_status"] != 200 or attestation["asset_http_status"] != 200:
        raise RuntimeError("742 deployment attestation did not observe HTTP 200")
    if attestation["route_sha256"] != digest(ROOT / "742/index.html"):
        raise RuntimeError("742 deployed route HTML does not match the candidate route")
    if not re.fullmatch(r"[0-9a-f]{40}", attestation["source_commit"]):
        raise RuntimeError("742 deployment attestation source commit is malformed")
    if not re.fullmatch(r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", attestation["workflow_run_url"]):
        raise RuntimeError("742 deployment attestation workflow run is malformed")
    asset = receipt["files"]["asset"]
    if attestation["asset_sha256"] != asset["sha256"] or attestation["asset_bytes"] != asset["bytes"]:
        raise RuntimeError("742 deployed asset does not match the candidate receipt")
    if attestation["candidate_receipt_sha256"] != digest(receipt_path):
        raise RuntimeError("742 deployment attestation does not bind the canonical candidate receipt")
    build_manifest_path = path.parent / "pages-build-manifest.json"
    if not build_manifest_path.is_file() or attestation["pages_build_manifest_sha256"] != digest(build_manifest_path):
        raise RuntimeError("742 deployment attestation does not bind the Pages build manifest")
    build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
    if set(build_manifest) != {"schema_version", "kind", "source_commit", "files"}:
        raise RuntimeError("742 Pages build manifest schema drift")
    if build_manifest["schema_version"] != "1.0.0" or build_manifest["kind"] != "github-pages-build-manifest":
        raise RuntimeError("742 Pages build manifest identity drift")
    if build_manifest["source_commit"] != attestation["source_commit"]:
        raise RuntimeError("742 Pages build manifest source commit mismatch")
    site_files = build_manifest.get("files") or {}
    if "assets/models/742.asset-receipt.json" in site_files:
        raise RuntimeError("Non-release 742 receipt was packaged into Pages")
    expected_site_files = {"assets/models/742.glb": {"sha256": asset["sha256"], "bytes": asset["bytes"]}}
    for runtime_path in CANONICAL_RUNTIME:
        local = ROOT / runtime_path
        expected_site_files[runtime_path] = {"sha256": digest(local), "bytes": local.stat().st_size}
    public_docs = {
        "research_readme", "references", "configuration_notes", "dimensions_notes", "articulation_notes",
        "source_reconciliation", "detailed_reconstruction", "comparison_matrix", "rights_boundary",
        "source_manifest", "mechanism_evidence", "reference_board_boundary",
    }
    for label in public_docs:
        record = receipt["files"][label]
        expected_site_files[record["path"]] = {"sha256": record["sha256"], "bytes": record["bytes"]}
    for site_path, expected in expected_site_files.items():
        if site_files.get(site_path) != expected:
            raise RuntimeError(f"742 Pages build manifest drift: {site_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--sources-dir", type=Path)
    parser.add_argument("--require-source-binaries", action="store_true")
    parser.add_argument("--require-human-reviewed", action="store_true")
    parser.add_argument("--deployment-attestation", type=Path)
    parser.add_argument("--require-deployed", action="store_true")
    parser.add_argument("--require-release", action="store_true", help="Require source-record, human-review, and external deployment gates together.")
    args = parser.parse_args()
    if args.require_source_binaries and not args.sources_dir:
        raise RuntimeError("--require-source-binaries requires --sources-dir")
    if args.require_deployed and not args.deployment_attestation:
        raise RuntimeError("--require-deployed requires --deployment-attestation")
    if args.require_release and not args.deployment_attestation:
        raise RuntimeError("--require-release requires --deployment-attestation")
    if args.require_release and not args.sources_dir:
        raise RuntimeError("--require-release requires --sources-dir for an independent frozen-binary replay")

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if set(receipt) != TOP_LEVEL_FIELDS or receipt.get("schema_version") != "2.0.0":
        raise RuntimeError("742 receipt top-level schema drift")
    if receipt.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 receipt identity drift")
    configuration = json.loads((ROOT / CANONICAL_FILES["configuration"]).read_text(encoding="utf-8"))
    target_release = configuration.get("target_release", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", target_release):
        raise RuntimeError("742 configuration target release is missing or malformed")
    if receipt.get("release") != f"{target_release}-candidate" or receipt.get("release_status") not in {
        "candidate_review_pending", "reviewed_candidate_not_deployed"
    }:
        raise RuntimeError("742 receipt overstates or misstates release status")
    if receipt.get("deployment_attestation") != {"status": "not_attested", "artifact": None}:
        raise RuntimeError("Deployment proof must remain external to the candidate receipt")

    if set(receipt.get("files") or {}) != set(CANONICAL_FILES):
        raise RuntimeError("742 receipt canonical file set drift")
    file_paths = [verify_record(receipt["files"][label], path) for label, path in CANONICAL_FILES.items()]
    runtime = receipt.get("runtime") or {}
    if set(runtime) != {"files", "sha256"} or runtime["files"] != CANONICAL_RUNTIME:
        raise RuntimeError("742 receipt canonical runtime set drift")
    runtime_paths = [ROOT / path for path in CANONICAL_RUNTIME]
    if any(not path.is_file() for path in runtime_paths) or aggregate_digest(runtime_paths) != runtime["sha256"]:
        raise RuntimeError("742 receipt runtime drift")

    checks = receipt.get("automated_checks") or {}
    if set(checks) != set(AUTOMATED_CHECKS):
        raise RuntimeError("742 receipt automated check set drift")
    validator_paths = [replay_check(name, checks[name]) for name in AUTOMATED_CHECKS]
    if aggregate_digest(file_paths + runtime_paths + validator_paths) != receipt["candidate_tree_sha256"]:
        raise RuntimeError("742 receipt candidate tree drift")

    asset_result = checks["asset_contract"]["result"]
    kinematic_result = checks["mechanical_kinematics"]["result"]
    mechanism = json.loads((ROOT / CANONICAL_FILES["mechanism"]).read_text(encoding="utf-8"))
    circle_angles = kinematic_result["positive_circle_max_wheel_angles_degrees"]
    expected_mechanical_proof = {
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
    if receipt.get("mechanical_proof") != expected_mechanical_proof:
        raise RuntimeError("742 receipt mechanical proof summary drift")
    if abs(expected_mechanical_proof["posed_glb_length_less_forks_m"] - expected_mechanical_proof["published_length_less_forks_m"]) > 0.015:
        raise RuntimeError("742 receipt length-less-forks proof misses the published envelope")
    if abs(expected_mechanical_proof["posed_level_fork_surface_height_m"] - expected_mechanical_proof["published_maximum_lift_height_m"]) > 0.02:
        raise RuntimeError("742 receipt maximum-height pose proof drift")
    if abs(expected_mechanical_proof["posed_24in_load_center_forward_reach_m"] - expected_mechanical_proof["published_maximum_forward_reach_m"]) > 0.02:
        raise RuntimeError("742 receipt maximum-reach pose proof drift")
    if expected_mechanical_proof["evidence_steering_inner_limit_degrees"] != 55 or expected_mechanical_proof["posed_circle_maximum_wheel_degrees"] != 55.0:
        raise RuntimeError("742 receipt 55-degree steering proof drift")

    source = receipt.get("frozen_source_binary_verification") or {}
    if set(source) != {"status", "result_sha256", "verified_count"} or source["status"] not in {"not_run", "pass"}:
        raise RuntimeError("742 frozen-source verification schema drift")
    if source["status"] == "not_run" and source != {"status": "not_run", "result_sha256": None, "verified_count": 0}:
        raise RuntimeError("742 unrun frozen-source verification overstates evidence")
    if source["status"] == "pass" and (
        source["verified_count"] != 11 or not re.fullmatch(r"[0-9a-f]{64}", source.get("result_sha256") or "")
    ):
        raise RuntimeError("742 frozen-source verification pass record is incomplete")
    source_replayed = False
    if args.sources_dir:
        evidence_script = ROOT / "scripts/validate_742_evidence.py"
        completed = subprocess.run(
            [sys.executable, "-B", str(evidence_script), "--sources-dir", str(args.sources_dir), "--require-source-binaries"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        if completed.returncode:
            raise RuntimeError(f"742 source-binary verification failed\n{completed.stdout}{completed.stderr}")
        result = json.loads(completed.stdout)
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
        if source["status"] == "pass" and (
            source["verified_count"] != result["local_binaries_verified_count"]
            or source["result_sha256"] != hashlib.sha256(canonical).hexdigest()
        ):
            raise RuntimeError("742 receipt source-binary result drift")
        source_replayed = True
    if args.require_source_binaries and source["status"] != "pass":
        raise RuntimeError("742 receipt was not written with frozen-source binary verification")
    if args.require_release and source["status"] != "pass":
        raise RuntimeError("742 release requires a receipt written with frozen-source binary verification")

    incomplete = verify_human_review(
        receipt["human_review"], receipt["candidate_tree_sha256"], args.require_human_reviewed or args.require_release
    )
    if (not incomplete) != (receipt["release_status"] == "reviewed_candidate_not_deployed"):
        raise RuntimeError("742 human review and release status disagree")
    deployed = False
    if args.deployment_attestation:
        verify_deployment_attestation(args.deployment_attestation, receipt, args.receipt)
        deployed = True

    print(json.dumps({
        "status": "PASS",
        "configuration_id": EXPECTED_ID,
        "verified_files": sorted(CANONICAL_FILES.values()),
        "automated_checks_replayed": sorted(AUTOMATED_CHECKS),
        "frozen_source_binary_receipt_status": source["status"],
        "frozen_source_binary_replay_status": "VERIFIED" if source_replayed else "NOT_REPLAYED",
        "human_review_status": receipt["human_review"]["status"],
        "incomplete_human_gates": incomplete,
        "deployed_attestation_verified": deployed,
        "release_gate_complete": deployed and not incomplete and source["status"] == "pass",
        "release_status": receipt["release_status"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
