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

from validate_742_review import BROWSER_CAPTURE_ALLOWLIST_PATH, HUMAN_GATES, validate_review_manifest
from verify_pages_deployment import REQUIRED_742_PUBLIC_FILES
from validate_742_portable_posed_glb import EXPECTED_ASSET_PATH


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "assets/models/742.asset-receipt.json"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
CANONICAL_FILES = {
    "asset": "assets/models/742.glb",
    "source_blend": "source/blender/742-showcase-v1.0.blend",
    "builder": "scripts/build_742.py",
    "solver_bridge": "scripts/solve_742_pose.mjs",
    "solver_validator": "scripts/validate_742_solver.mjs",
    "portable_posed_glb_validator": "scripts/validate_742_portable_posed_glb.py",
    "blender_posed_glb_validator": "scripts/validate_742_posed_glb.py",
    "blender_posed_glb_runner": "scripts/run_742_posed_glb_gate.py",
    "receipt_writer": "scripts/write_742_receipt.py",
    "receipt_validator": "scripts/validate_742_receipt.py",
    "project_readme": "README.md",
    "package_manifest": "package.json",
    "package_lock": "package-lock.json",
    "pages_workflow": ".github/workflows/pages.yml",
    "pages_assembler": "scripts/assemble_pages.py",
    "pages_bundle_validator": "scripts/validate_pages_bundle.py",
    "pages_manifest_writer": "scripts/write_pages_attestation.py",
    "pages_deployment_verifier": "scripts/verify_pages_deployment.py",
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
    "review_validator": "scripts/validate_742_review.py",
    "review_binder": "scripts/bind_742_review.py",
    "browser_capture_validator": "scripts/validate_742_browser_evidence.py",
    "browser_capture_probe": "scripts/742_browser_capture_probe.js",
    "browser_capture_runner": "scripts/capture_742_browser_evidence.mjs",
    "browser_capture_parser_tests": "scripts/test_742_browser_evidence.py",
    "deterministic_rebuild_verifier": "scripts/verify_742_deterministic_rebuild.py",
    "owned_review_render_allowlist": "docs/review/742/OWNED_RENDER_ALLOWLIST.json",
    "browser_capture_requirements": "docs/review/742/CAPTURE_REQUIREMENTS.json",
}
CANONICAL_RUNTIME = [
    "favicon.ico",
    "742/index.html",
    "viewer.css",
    "viewer/742.css",
    "viewer/742-runtime.js",
    "machines/742/machine.js",
    "machines/742/articulation.js",
    "machines/742/inspector.js",
    "machines/742/cameras.js",
    "machines/742/version.js",
    "machines/742/solver.js",
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
    "actual_posed_glb": ("scripts/validate_742_portable_posed_glb.py", []),
    "route_contract": ("scripts/validate_742_route.py", []),
    "review_evidence_parser": ("scripts/test_742_browser_evidence.py", []),
    "review_visual_semantics_parser": ("scripts/test_742_review_semantics.py", []),
    "posed_glb_portability_parser": ("scripts/test_742_posed_glb_portability.py", []),
    "deployment_proof_parser": ("scripts/test_742_deployment_proof.py", []),
}
TOP_LEVEL_FIELDS = {
    "schema_version", "release", "release_status", "written", "configuration_id",
    "candidate_tree_sha256", "files", "runtime", "automated_checks",
    "mechanical_proof", "frozen_source_binary_verification", "human_review", "deployment_attestation", "boundary",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_record(record: dict, expected_path: str | None = None) -> Path:
    if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
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


def verify_browser_capture_allowlist_binding(record: dict) -> Path:
    """Verify the post-candidate browser allowlist bound by human review."""
    return verify_record(record, BROWSER_CAPTURE_ALLOWLIST_PATH)


def verify_deployment_rebuild_binding(
    record: dict, rebuild_path: Path, workflow_run_url: str, source_commit: str
) -> None:
    expected_fields = {"sha256", "bytes", "authority", "workflow_run_url", "source_commit"}
    if set(record or {}) != expected_fields:
        raise RuntimeError("742 deployment deterministic-rebuild record schema drift")
    if (
        record["authority"] != "generated_in_deployment_workflow"
        or record["workflow_run_url"] != workflow_run_url
        or record["source_commit"] != source_commit
        or not rebuild_path.is_file()
        or record["sha256"] != digest(rebuild_path)
        or record["bytes"] != rebuild_path.stat().st_size
    ):
        raise RuntimeError("742 deployment deterministic-rebuild current-run binding drift")


def aggregate_digest(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def solver_stroke_usage(result: dict) -> dict:
    ranges = result["cylinder_ranges"]
    return {
        "lift": ranges["lift"]["stroke_usage_m"],
        "telescope": ranges["telescope"]["stroke_usage_m"],
        "head_tilt_slave": ranges["carriageTilt"]["stroke_usage_m"],
        "compensation_master": ranges["compensation"]["stroke_usage_m"],
        "frame_sway": ranges["frameLevel"]["stroke_usage_m"],
        "rear_axle_stabilization_visible_subset": ranges["rearAxleStabilizer"]["stroke_usage_m"],
    }


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
    if name == "actual_posed_glb" and (
        result.get("asset") != EXPECTED_ASSET_PATH
        or record.get("result", {}).get("asset") != EXPECTED_ASSET_PATH
    ):
        raise RuntimeError("742 posed-GLB replay contains a checkout-specific asset path")
    if result.get("status") != "PASS" or result != record["result"] or hashlib.sha256(canonical).hexdigest() != record["result_sha256"]:
        raise RuntimeError(f"742 automated check result drift: {name}")
    return validator


def verify_human_review(
    review: dict, candidate_tree_sha256: str, require_review: bool, canonical_paths: list[Path]
) -> list[str]:
    if set(review) != {"status", "binding", "gates"} or set(review.get("gates") or {}) != set(HUMAN_GATES):
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
        if set(binding) != {
            "manifest", "browser_capture_allowlist", "candidate_tree_sha256",
            "reviewed_source_commit", "environment",
        }:
            raise RuntimeError("742 human review binding schema drift")
        verify_record(binding["manifest"])
        verify_browser_capture_allowlist_binding(binding["browser_capture_allowlist"])
        if not re.fullmatch(r"[0-9a-f]{64}", binding["candidate_tree_sha256"]):
            raise RuntimeError("742 human review candidate tree binding is malformed")
        if binding["candidate_tree_sha256"] != candidate_tree_sha256:
            raise RuntimeError("742 human review does not bind this candidate tree")
        if not re.fullmatch(r"[0-9a-f]{40}", binding["reviewed_source_commit"]):
            raise RuntimeError("742 reviewed source commit is malformed")
        environment = binding["environment"]
        if not isinstance(environment, dict) or not environment.get("browser") or not environment.get("os"):
            raise RuntimeError("742 human review environment is incomplete")
        reviewed, expected_binding = validate_review_manifest(
            ROOT / binding["manifest"]["path"], candidate_tree_sha256, canonical_paths
        )
        if reviewed != review["gates"] or expected_binding != binding:
            raise RuntimeError("742 semantically parsed review evidence disagrees with the receipt")
    if require_review and incomplete:
        raise RuntimeError(f"742 human review gates incomplete: {sorted(incomplete)}")
    return sorted(incomplete)


def verify_deployment_attestation(path: Path, receipt: dict, receipt_path: Path) -> None:
    attestation = json.loads(path.read_text(encoding="utf-8"))
    fields = {
        "schema_version", "kind", "configuration_id", "source_commit", "workflow_run_url", "base_url",
        "pages_build_manifest_url", "pages_build_manifest_http_status", "pages_build_manifest_sha256",
        "pages_build_manifest_bytes", "candidate_receipt_sha256", "frozen_source_replay",
        "deterministic_rebuild_attestation", "verified_files",
    }
    if set(attestation) != fields or attestation["schema_version"] != "3.0.0" or attestation["kind"] != "github-pages-http-attestation":
        raise RuntimeError("742 deployment attestation schema drift")
    if attestation["configuration_id"] != EXPECTED_ID:
        raise RuntimeError("742 deployment attestation identity drift")
    base_url = "https://exo-robotics.github.io/jlg-equipment-explorer/"
    if attestation["base_url"] != base_url or attestation["pages_build_manifest_url"] != f"{base_url}pages-build-manifest.json":
        raise RuntimeError("742 deployment attestation URL identity drift")
    if attestation["pages_build_manifest_http_status"] != 200:
        raise RuntimeError("742 deployment attestation did not retrieve the public build manifest")
    if not re.fullmatch(r"[0-9a-f]{40}", attestation["source_commit"]):
        raise RuntimeError("742 deployment attestation source commit is malformed")
    if not re.fullmatch(r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", attestation["workflow_run_url"]):
        raise RuntimeError("742 deployment attestation workflow run is malformed")
    replay = attestation["frozen_source_replay"]
    replay_fields = {
        "status", "configuration_id", "verified_count", "result_sha256", "result_bytes",
        "artifact_name", "artifact_run_url",
    }
    if set(replay or {}) != replay_fields or replay.get("status") != "verified_before_deployment":
        raise RuntimeError("742 deployment frozen-source replay schema/status drift")
    if replay["configuration_id"] != EXPECTED_ID or replay["verified_count"] != 11:
        raise RuntimeError("742 deployment frozen-source replay identity/count drift")
    artifact_run_url = replay["artifact_run_url"]
    if replay["artifact_name"] != "742-frozen-source-evidence" or not re.fullmatch(
        r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", artifact_run_url or ""
    ):
        raise RuntimeError("742 deployment frozen-source replay artifact identity drift")
    source_result_path = path.parent / "742-source-replay-result.json"
    if (
        not source_result_path.is_file()
        or replay["result_sha256"] != digest(source_result_path)
        or replay["result_bytes"] != source_result_path.stat().st_size
    ):
        raise RuntimeError("742 deployment frozen-source replay result record drift")
    source_result = json.loads(source_result_path.read_text(encoding="utf-8"))
    source_result_fields = {
        "admitted_source_binaries", "browser_captures_verified", "claims", "committed_source_binaries",
        "configuration_id", "frozen_source_binary_status", "local_binaries_missing",
        "local_binaries_verified", "local_binaries_verified_count", "owned_review_renders_verified",
        "primary_publications", "source_expressions_resolved", "status",
    }
    source_manifest = json.loads((ROOT / "docs/research/742/SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    browser_allowlist = json.loads((ROOT / "docs/review/742/BROWSER_CAPTURE_ALLOWLIST.json").read_text(encoding="utf-8"))
    owned_render_allowlist = json.loads((ROOT / "docs/review/742/OWNED_RENDER_ALLOWLIST.json").read_text(encoding="utf-8"))
    expected_source_names = sorted(
        source["local_filename"] for source in source_manifest["sources"]
        if source.get("local_filename") and source.get("sha256") and source.get("bytes")
    )
    if (
        set(source_result) != source_result_fields
        or source_result.get("status") != "PASS"
        or source_result.get("configuration_id") != EXPECTED_ID
        or source_result.get("frozen_source_binary_status") != "VERIFIED"
        or source_result.get("local_binaries_verified_count") != 11
        or source_result.get("admitted_source_binaries") != 11
        or source_result.get("browser_captures_verified") != len(browser_allowlist.get("artifacts") or [])
        or source_result.get("owned_review_renders_verified") != len(owned_render_allowlist.get("artifacts") or [])
        or source_result.get("local_binaries_verified") != expected_source_names
        or source_result.get("local_binaries_missing") != []
    ):
        raise RuntimeError("742 deployment frozen-source replay result did not verify all 11 sources")
    rebuild_record = attestation["deterministic_rebuild_attestation"]
    rebuild_path = path.parent / "742-deterministic-rebuild-attestation.json"
    verify_deployment_rebuild_binding(
        rebuild_record, rebuild_path, attestation["workflow_run_url"], attestation["source_commit"]
    )
    if attestation["candidate_receipt_sha256"] != digest(receipt_path):
        raise RuntimeError("742 deployment attestation does not bind the canonical candidate receipt")
    build_manifest_path = path.parent / "pages-build-manifest.json"
    if not build_manifest_path.is_file() or attestation["pages_build_manifest_sha256"] != digest(build_manifest_path) or attestation["pages_build_manifest_bytes"] != build_manifest_path.stat().st_size:
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
    for site_path, manifest_record in site_files.items():
        relative = Path(site_path)
        if relative.is_absolute() or ".." in relative.parts or "\\" in site_path or str(relative) != site_path:
            raise RuntimeError(f"742 Pages build manifest contains an unsafe path: {site_path}")
        if set(manifest_record or {}) != {"sha256", "bytes"}:
            raise RuntimeError(f"742 Pages build-manifest file record schema drift: {site_path}")
        local = ROOT / relative
        if not local.is_file() or manifest_record != {"sha256": digest(local), "bytes": local.stat().st_size}:
            raise RuntimeError(f"742 Pages build manifest does not match local bytes: {site_path}")
        committed = subprocess.run(
            ["git", "show", f"{attestation['source_commit']}:{site_path}"], cwd=ROOT,
            capture_output=True, check=False,
        )
        if committed.returncode or committed.stdout != local.read_bytes():
            raise RuntimeError(f"742 deployed source commit does not contain the attested public bytes: {site_path}")
    expected_site_files = {}
    for site_path in REQUIRED_742_PUBLIC_FILES:
        local = ROOT / site_path
        expected_site_files[site_path] = {"sha256": digest(local), "bytes": local.stat().st_size}
    for site_path, expected in expected_site_files.items():
        if site_files.get(site_path) != expected:
            raise RuntimeError(f"742 Pages build manifest drift: {site_path}")
    verified_files = attestation.get("verified_files") or {}
    if not REQUIRED_742_PUBLIC_FILES.issubset(site_files) or set(verified_files) != set(site_files):
        raise RuntimeError("742 deployment attestation did not verify the complete public build manifest")
    for site_path, expected in site_files.items():
        if set(expected or {}) != {"sha256", "bytes"}:
            raise RuntimeError(f"742 Pages build-manifest file record schema drift: {site_path}")
        observed = verified_files[site_path]
        if set(observed) != {"url", "http_status", "sha256", "bytes"}:
            raise RuntimeError(f"742 deployed-file attestation schema drift: {site_path}")
        if observed != {"url": f"{base_url}{site_path}", "http_status": 200, **expected}:
            raise RuntimeError(f"742 deployed-file attestation drift: {site_path}")
    binding = (receipt.get("human_review") or {}).get("binding")
    if binding:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", binding["reviewed_source_commit"], attestation["source_commit"]],
            cwd=ROOT, capture_output=True, check=False,
        )
        if ancestor.returncode:
            raise RuntimeError("742 deployed source commit does not descend from the reviewed candidate commit")


def verify_rebuild_attestation(path: Path, receipt: dict) -> None:
    attestation = json.loads(path.read_text(encoding="utf-8"))
    fields = {
        "schema_version", "kind", "configuration_id", "blender_version", "builder", "solver_bridge", "solver", "configuration",
        "run_1_glb", "run_2_glb", "committed_glb", "run_1_blend", "run_2_blend",
        "glb_byte_identical", "blend_byte_identity_claimed", "boundary",
    }
    if set(attestation) != fields or attestation["schema_version"] != "1.0.0" or attestation["kind"] != "742-deterministic-glb-rebuild-attestation":
        raise RuntimeError("742 deterministic rebuild attestation schema drift")
    if attestation["configuration_id"] != EXPECTED_ID or not re.fullmatch(r"Blender \d+\.\d+\.\d+.*", attestation["blender_version"]):
        raise RuntimeError("742 deterministic rebuild attestation identity drift")
    for label, expected_path in {
        "builder": "scripts/build_742.py", "solver_bridge": "scripts/solve_742_pose.mjs",
        "solver": "machines/742/solver.js", "configuration": "machines/742/742.configuration.json",
        "committed_glb": "assets/models/742.glb",
    }.items():
        record = attestation[label]
        if set(record) != {"path", "sha256", "bytes"} or record["path"] != expected_path:
            raise RuntimeError(f"742 deterministic rebuild {label} record drift")
        local = ROOT / expected_path
        if record["sha256"] != digest(local) or record["bytes"] != local.stat().st_size:
            raise RuntimeError(f"742 deterministic rebuild {label} no longer matches the candidate")
    for label in ("run_1_glb", "run_2_glb", "run_1_blend", "run_2_blend"):
        record = attestation[label]
        if set(record) != {"sha256", "bytes"} or not re.fullmatch(r"[0-9a-f]{64}", record.get("sha256", "")) or not isinstance(record.get("bytes"), int) or record["bytes"] <= 0:
            raise RuntimeError(f"742 deterministic rebuild output record drift: {label}")
    expected_asset = receipt["files"]["asset"]
    exact = {"sha256": expected_asset["sha256"], "bytes": expected_asset["bytes"]}
    if attestation["run_1_glb"] != exact or attestation["run_2_glb"] != exact or attestation["committed_glb"] != {"path": expected_asset["path"], **exact}:
        raise RuntimeError("742 deterministic rebuild GLBs are not byte-identical to the receipt asset")
    if attestation["glb_byte_identical"] is not True or not isinstance(attestation["blend_byte_identity_claimed"], bool):
        raise RuntimeError("742 deterministic rebuild result flags drift")
    if not isinstance(attestation["boundary"], str) or "Blend-file byte identity" not in attestation["boundary"]:
        raise RuntimeError("742 deterministic rebuild boundary is incomplete")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=RECEIPT)
    parser.add_argument("--sources-dir", type=Path)
    parser.add_argument("--require-source-binaries", action="store_true")
    parser.add_argument("--require-human-reviewed", action="store_true")
    parser.add_argument("--deployment-attestation", type=Path)
    parser.add_argument("--rebuild-attestation", type=Path)
    parser.add_argument("--require-deployed", action="store_true")
    parser.add_argument("--require-release", action="store_true", help="Require source-record, human-review, and external deployment gates together.")
    args = parser.parse_args()
    if args.require_source_binaries and not args.sources_dir:
        raise RuntimeError("--require-source-binaries requires --sources-dir")
    if args.require_deployed and not args.deployment_attestation:
        raise RuntimeError("--require-deployed requires --deployment-attestation")
    if args.require_deployed and not args.sources_dir:
        raise RuntimeError("--require-deployed requires --sources-dir for an independent frozen-binary replay")
    if args.require_release and not args.deployment_attestation:
        raise RuntimeError("--require-release requires --deployment-attestation")
    if args.require_release and not args.sources_dir:
        raise RuntimeError("--require-release requires --sources-dir for an independent frozen-binary replay")
    if args.require_release and not args.rebuild_attestation:
        raise RuntimeError("--require-release requires --rebuild-attestation for a byte-identical GLB rebuild")

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
    posed_glb_result = checks["actual_posed_glb"]["result"]
    mechanism = json.loads((ROOT / CANONICAL_FILES["mechanism"]).read_text(encoding="utf-8"))
    steering_linkage = kinematic_result["steering_linkage"]
    expected_mechanical_proof = {
        "asset_sha256": asset_result["sha256"],
        "source_blend_sha256": asset_result["source_blend_sha256"],
        "published_length_less_forks_m": configuration["published_dimensions_m"]["length_less_forks"],
        "posed_glb_length_less_forks_m": asset_result["length_less_forks_m"],
        "published_maximum_lift_height_m": configuration["published_performance"]["maximum_lift_height_m"],
        "posed_level_fork_surface_height_m": kinematic_result["maximum_level_fork_surface_y_m"],
        "published_maximum_forward_reach_m": configuration["published_performance"]["maximum_forward_reach_m"],
        "posed_24in_load_center_forward_reach_m": kinematic_result["maximum_reach_pose"]["forward_reach_m"],
        "posed_reach_fork_heel_world_x_m": kinematic_result["maximum_reach_pose"]["fork_heel_x_m"],
        "posed_reach_24in_load_center_world_x_m": kinematic_result["maximum_reach_pose"]["load_center_world_x_m"],
        "actual_glb_front_tire_tread_plane_x_m": kinematic_result["actual_glb_front_tire_tread_plane_x_m"],
        "evidence_steering_inner_limit_degrees": mechanism["steering"]["visual_inner_limit_degrees"],
        "solver_circle_maximum_inner_wheel_degrees": steering_linkage["maximum_inner_wheel_angle_degrees"],
        "solver_maximum_steering_bar_length_drift_m": steering_linkage["maximum_steering_bar_length_drift_m"],
        "solver_maximum_opposed_rod_joint_span_drift_m": steering_linkage["maximum_opposed_rod_joint_span_drift_m"],
        "solver_maximum_rod_bar_closure_error_m": steering_linkage["maximum_rod_bar_closure_error_m"],
        "solver_maximum_ackermann_fit_error_m": steering_linkage["maximum_ackermann_fit_error_m"],
        "solver_maximum_ackermann_relative_error": steering_linkage["maximum_ackermann_relative_error"],
        "solver_maximum_four_wheel_icr_relative_spread": steering_linkage["maximum_four_wheel_icr_relative_spread"],
        "solver_maximum_crab_heading_spread_degrees": steering_linkage["maximum_crab_heading_spread_degrees"],
        "solver_maximum_crab_corresponding_heading_error_degrees": steering_linkage["maximum_crab_corresponding_heading_error_degrees"],
        "solver_maximum_front_mode_icr_relative_spread": steering_linkage["maximum_front_mode_icr_relative_spread"],
        "solver_ackermann_authority": steering_linkage["ackermann_authority"],
        "solver_maximum_front_mode_wheel_angle_degrees": steering_linkage["maximum_front_mode_wheel_angle_degrees"],
        "solver_maximum_crab_mode_wheel_angle_degrees": steering_linkage["maximum_crab_mode_wheel_angle_degrees"],
        "solver_minimum_useful_mode_angle_degrees": steering_linkage["minimum_useful_mode_angle_degrees"],
        "solver_static_linkage_authority": steering_linkage["static_linkage_authority"],
        "solver_scrub_boundary": steering_linkage["scrub_boundary"],
        "solver_crab_parallelism_boundary": steering_linkage["crab_parallelism_boundary"],
        "solver_maximum_reconstructed_circle_center_spread_m": kinematic_result["maximum_reconstructed_circle_center_spread_m"],
        "solver_rigid_link_ranges_m": kinematic_result["rigid_link_ranges_m"],
        "solver_chain_paths": kinematic_result["chain_paths"],
        "solver_hose_paths": kinematic_result["hose_paths"],
        "continuous_hose_samples": kinematic_result["continuous_hose_samples"],
        "solver_maximum_chain_tangent_dot_error": kinematic_result["maximum_chain_tangent_dot_error"],
        "solver_minimum_chain_to_sheave_surface_clearance_m": kinematic_result["minimum_chain_to_sheave_surface_clearance_m"],
        "solver_minimum_boom_hose_to_rigid_tube_surface_clearance_m": kinematic_result["minimum_boom_hose_to_rigid_tube_surface_clearance_m"],
        "solver_maximum_boom_hose_adjacent_direction_change_degrees": kinematic_result["maximum_boom_hose_adjacent_direction_change_degrees"],
        "solver_boom_hose_nominal_centerline_length_m": kinematic_result["boom_hose_nominal_centerline_length_m"],
        "solver_service_line_chassis_clearance_sweep": kinematic_result["service_line_chassis_clearance_sweep"],
        "actual_glb_minimum_named_rigid_underbody_clearance_m": kinematic_result["actual_glb_minimum_named_rigid_underbody_clearance_m"],
        "actual_glb_stowed_boom_to_cab_clearance_m": asset_result["stowed_boom_clearance"]["cab"]["clearance_m"],
        "actual_glb_stowed_boom_to_engine_hood_clearance_m": asset_result["stowed_boom_clearance"]["engine_hood"]["clearance_m"],
        "actual_glb_stowed_service_line_to_cab_clearance_m": asset_result["stowed_service_line_clearance"]["cab"]["clearance_m"],
        "actual_glb_stowed_service_line_to_engine_clearance_m": asset_result["stowed_service_line_clearance"]["engine"]["clearance_m"],
        "actual_posed_glb_minimum_frame_level_clearance_m": posed_glb_result["minimum_frame_level_clearance"]["clearance_m"],
        "actual_posed_glb_minimum_frame_level_clearance_node": posed_glb_result["minimum_frame_level_clearance"]["limiting_node"],
        "actual_posed_glb_named_presets": posed_glb_result["named_presets_posed"],
        "actual_posed_glb_gate_kind": posed_glb_result["gate_kind"],
        "actual_posed_glb_asset_sha256": posed_glb_result["asset_sha256"],
        "actual_posed_glb_configuration_id": posed_glb_result["configuration_id"],
        "actual_posed_glb_parser": posed_glb_result["parser"],
        "actual_posed_glb_production_solver_bridge": posed_glb_result["production_solver_bridge"],
        "actual_posed_glb_neutral_binary_contract": posed_glb_result["neutral_binary_contract"],
        "actual_posed_glb_stowed_fork_bottom_m": posed_glb_result["stow"]["bottom_m"],
        "actual_posed_glb_maximum_lift_surface_m": posed_glb_result["maximum_lift"]["load_surface_m"],
        "actual_posed_glb_maximum_lift_fork_pitch_degrees": posed_glb_result["maximum_lift"]["pitch_degrees"],
        "actual_posed_glb_maximum_reach_m": posed_glb_result["maximum_reach"]["forward_reach_m"],
        "actual_posed_glb_maximum_reach_fork_pitch_degrees": posed_glb_result["maximum_reach"]["pitch_degrees"],
        "actual_posed_glb_maximum_circle_wheel_angle_degrees": posed_glb_result["maximum_circle_steer"]["inner_wheel_angle_degrees"],
        "actual_posed_glb_maximum_crab_wheel_angle_degrees": posed_glb_result["maximum_crab_steer"]["maximum_wheel_angle_degrees"],
        "actual_posed_glb_maximum_crab_heading_spread_degrees": posed_glb_result["maximum_crab_steer"]["maximum_heading_spread_degrees"],
        "actual_posed_glb_maximum_front_wheel_angle_degrees": posed_glb_result["maximum_front_steer"]["maximum_front_wheel_angle_degrees"],
        "actual_posed_glb_maximum_rear_wheel_angle_in_front_mode_degrees": posed_glb_result["maximum_front_steer"]["maximum_rear_wheel_angle_degrees"],
        "actual_posed_glb_maximum_beam_endpoint_error_m": max(
            pose["maximum_beam_endpoint_error_m"] for pose in posed_glb_result["pose_contracts"].values()
        ),
        "actual_posed_glb_maximum_point_position_error_m": max(
            pose["maximum_point_position_error_m"] for pose in posed_glb_result["pose_contracts"].values()
        ),
        "actual_posed_glb_minimum_boom_hose_to_rigid_tube_surface_clearance_m": min(
            pose["minimum_boom_hose_to_rigid_tube_surface_clearance_m"]
            for pose in posed_glb_result["pose_contracts"].values()
        ),
        "actual_posed_glb_maximum_boom_hose_adjacent_direction_change_degrees": max(
            pose["maximum_boom_hose_adjacent_direction_change_degrees"]
            for pose in posed_glb_result["pose_contracts"].values()
        ),
        "blender_posed_glb_companion": {
            "execution_status": "required_in_pinned_pages_ci_not_run_by_portable_receipt",
            "version": "5.1.1",
            "runner": posed_glb_result["blender_companion"],
            "validator": "scripts/validate_742_posed_glb.py",
            "included_in_standard_npm_check": False,
        },
        "approximate_published_rigid_underbody_clearance_m": mechanism["collision_proxies"]["minimum_rigid_underbody_clearance_m"],
        "published_hydraulic_cylinder_strokes_m": mechanism["hydraulic_cylinder_strokes_m"],
        "solver_evidence_stroke_usage_m": solver_stroke_usage(kinematic_result),
        "solver_fixed_barrel_length_ranges_m": {
            name: record["fixed_barrel_length_range_m"] for name, record in kinematic_result["cylinder_ranges"].items()
        },
        "rear_axle_stabilization_usage_boundary": kinematic_result["rear_axle_stabilization_usage_boundary"],
        "continuous_retract_chain_samples": kinematic_result["continuous_retract_chain_samples"],
        "continuous_all_chain_samples": kinematic_result["continuous_all_chain_samples"],
        "minimum_retract_chain_segment_m": kinematic_result["minimum_retract_chain_segment_m"],
        "stowed_fork_bottom_m": kinematic_result["stow"]["fork_bottom_m"],
        "canonical_solver": kinematic_result["canonical_solver"],
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
    if expected_mechanical_proof["evidence_steering_inner_limit_degrees"] != 55 or abs(expected_mechanical_proof["solver_circle_maximum_inner_wheel_degrees"] - 55.0) > 1e-9:
        raise RuntimeError("742 receipt 55-degree steering proof drift")
    if expected_mechanical_proof["solver_maximum_steering_bar_length_drift_m"] > 1e-12 or expected_mechanical_proof["solver_maximum_opposed_rod_joint_span_drift_m"] > 1e-12 or expected_mechanical_proof["solver_maximum_rod_bar_closure_error_m"] > 1e-12:
        raise RuntimeError("742 receipt rigid steering-linkage proof drift")
    if (
        expected_mechanical_proof["solver_maximum_front_mode_wheel_angle_degrees"] < 35
        or expected_mechanical_proof["solver_maximum_crab_mode_wheel_angle_degrees"] < 20
        or expected_mechanical_proof["solver_minimum_useful_mode_angle_degrees"] != 35
        or expected_mechanical_proof["solver_maximum_crab_heading_spread_degrees"] > 1
        or expected_mechanical_proof["solver_maximum_crab_corresponding_heading_error_degrees"] > 1
        or "one fixed axle-mounted double-rod cylinder" not in expected_mechanical_proof["solver_static_linkage_authority"]
        or "not Ackermann acceptance gates" not in expected_mechanical_proof["solver_scrub_boundary"]
        or "no mode-dependent toe" not in expected_mechanical_proof["solver_crab_parallelism_boundary"]
    ):
        raise RuntimeError("742 receipt source-correct static-linkage steering proof drift")
    if any(max(values) - min(values) > 1e-12 for values in expected_mechanical_proof["solver_rigid_link_ranges_m"].values()):
        raise RuntimeError("742 receipt rigid-link invariant proof drift")
    if any(path["maximum_total_length_drift_m"] > 1e-9 or path["minimum_segment_length_m"] < 0.04 or path["wrap_degrees"] != 180 for path in expected_mechanical_proof["solver_chain_paths"].values()):
        raise RuntimeError("742 receipt invariant chain-route proof drift")
    if expected_mechanical_proof["solver_maximum_chain_tangent_dot_error"] > 1e-12 or expected_mechanical_proof["solver_minimum_chain_to_sheave_surface_clearance_m"] <= 0 or expected_mechanical_proof["continuous_all_chain_samples"] < 2001:
        raise RuntimeError("742 receipt chain tangency/clearance/continuity proof drift")
    if expected_mechanical_proof["continuous_hose_samples"] < 2001 or any(path["maximum_total_length_drift_m"] > 1e-9 or path["minimum_segment_length_m"] < (0.05 if name.startswith("BoomHose") else 0.10) for name, path in expected_mechanical_proof["solver_hose_paths"].items()):
        raise RuntimeError("742 receipt invariant articulated-hose proof drift")
    if (
        expected_mechanical_proof["solver_minimum_boom_hose_to_rigid_tube_surface_clearance_m"] < 0.005
        or expected_mechanical_proof["solver_maximum_boom_hose_adjacent_direction_change_degrees"] > 22.500001
        or abs(expected_mechanical_proof["solver_boom_hose_nominal_centerline_length_m"] - 5.0) > 1e-12
    ):
        raise RuntimeError("742 receipt analytic boom-hose route proof drift")
    if expected_mechanical_proof["actual_glb_minimum_named_rigid_underbody_clearance_m"] + 1e-6 < expected_mechanical_proof["approximate_published_rigid_underbody_clearance_m"]:
        raise RuntimeError("742 receipt approximate rigid-underbody clearance proof drift")
    if (
        expected_mechanical_proof["actual_glb_stowed_boom_to_cab_clearance_m"] + 1e-6
        < mechanism["collision_proxies"]["minimum_stowed_boom_to_cab_clearance_m"]
        or expected_mechanical_proof["actual_glb_stowed_boom_to_engine_hood_clearance_m"] + 1e-6
        < mechanism["collision_proxies"]["minimum_stowed_boom_to_engine_hood_clearance_m"]
    ):
        raise RuntimeError("742 receipt stowed boom cab/hood clearance proof drift")
    if min(
        expected_mechanical_proof["actual_glb_stowed_service_line_to_cab_clearance_m"],
        expected_mechanical_proof["actual_glb_stowed_service_line_to_engine_clearance_m"],
    ) + 1e-6 < mechanism["collision_proxies"]["minimum_stowed_service_line_to_cab_or_engine_clearance_m"]:
        raise RuntimeError("742 receipt stowed service-line cab/engine clearance proof drift")
    service_sweep = expected_mechanical_proof["solver_service_line_chassis_clearance_sweep"]
    service_contract = mechanism["collision_proxies"]["service_line_clearance_sweep"]
    if (
        service_sweep["samples"] != service_contract["lift_samples"] * service_contract["telescope_samples"]
        or min(service_sweep["minimum_cab_surface_clearance_m"], service_sweep["minimum_engine_proxy_surface_clearance_m"])
        < service_contract["minimum_clearance_m"]
    ):
        raise RuntimeError("742 receipt dense service-line/chassis clearance sweep drift")
    neutral_binary = expected_mechanical_proof["actual_posed_glb_neutral_binary_contract"]
    expected_blender_companion = {
        "execution_status": "required_in_pinned_pages_ci_not_run_by_portable_receipt",
        "version": "5.1.1",
        "runner": "scripts/run_742_posed_glb_gate.py",
        "validator": "scripts/validate_742_posed_glb.py",
        "included_in_standard_npm_check": False,
    }
    if (
        expected_mechanical_proof["actual_posed_glb_gate_kind"] != "portable_committed_glb_production_solver"
        or expected_mechanical_proof["actual_posed_glb_asset_sha256"] != expected_mechanical_proof["asset_sha256"]
        or expected_mechanical_proof["actual_posed_glb_configuration_id"] != EXPECTED_ID
        or expected_mechanical_proof["actual_posed_glb_parser"] != "scripts/validate_742_portable_posed_glb.py"
        or expected_mechanical_proof["actual_posed_glb_production_solver_bridge"] != "scripts/solve_742_pose.mjs"
        or expected_mechanical_proof["blender_posed_glb_companion"] != expected_blender_companion
        or expected_mechanical_proof["actual_posed_glb_named_presets"] != [
            "stow_0deg", "maximum_lift_69deg", "maximum_reach_selected_3deg",
            "maximum_circle_steer", "maximum_crab_steer", "maximum_front_steer",
            "frame_level_dense_41",
        ]
        or neutral_binary["beams_checked"] <= 0
        or neutral_binary["points_checked"] <= 0
        or neutral_binary["maximum_neutral_beam_endpoint_error_m"] > 2e-6
        or neutral_binary["maximum_neutral_point_position_error_m"] > 2e-6
        or expected_mechanical_proof["actual_posed_glb_stowed_fork_bottom_m"] > 0.35
        or abs(expected_mechanical_proof["actual_posed_glb_maximum_lift_surface_m"] - expected_mechanical_proof["published_maximum_lift_height_m"]) > 0.02
        or abs(expected_mechanical_proof["actual_posed_glb_maximum_lift_fork_pitch_degrees"]) > 0.1
        or abs(expected_mechanical_proof["actual_posed_glb_maximum_reach_m"] - expected_mechanical_proof["published_maximum_forward_reach_m"]) > 0.02
        or abs(expected_mechanical_proof["actual_posed_glb_maximum_reach_fork_pitch_degrees"]) > 0.1
        or expected_mechanical_proof["actual_posed_glb_maximum_circle_wheel_angle_degrees"] < 35
        or expected_mechanical_proof["actual_posed_glb_maximum_circle_wheel_angle_degrees"] > 55.000001
        or expected_mechanical_proof["actual_posed_glb_maximum_crab_wheel_angle_degrees"] < 20
        or expected_mechanical_proof["actual_posed_glb_maximum_crab_heading_spread_degrees"] > 1
        or expected_mechanical_proof["actual_posed_glb_maximum_front_wheel_angle_degrees"] < 35
        or expected_mechanical_proof["actual_posed_glb_maximum_rear_wheel_angle_in_front_mode_degrees"] > 1e-9
        or expected_mechanical_proof["actual_posed_glb_minimum_frame_level_clearance_m"] + 1e-6 < expected_mechanical_proof["approximate_published_rigid_underbody_clearance_m"]
        or expected_mechanical_proof["actual_posed_glb_maximum_beam_endpoint_error_m"] > 2e-6
        or expected_mechanical_proof["actual_posed_glb_maximum_point_position_error_m"] > 1e-9
        or expected_mechanical_proof["actual_posed_glb_minimum_boom_hose_to_rigid_tube_surface_clearance_m"] < 0.005
        or expected_mechanical_proof["actual_posed_glb_maximum_boom_hose_adjacent_direction_change_degrees"] > 22.502
    ):
        raise RuntimeError("742 receipt actual posed-GLB mechanical proof drift")
    if any(max(values) - min(values) > 1e-12 for values in expected_mechanical_proof["solver_fixed_barrel_length_ranges_m"].values()):
        raise RuntimeError("742 receipt fixed-barrel proof drift")
    usage = expected_mechanical_proof["solver_evidence_stroke_usage_m"]
    published = expected_mechanical_proof["published_hydraulic_cylinder_strokes_m"]
    for name in ("lift", "telescope", "head_tilt_slave", "compensation_master", "frame_sway"):
        if abs(usage[name] - published[name]) > 2e-5:
            raise RuntimeError(f"742 receipt evidence-stroke proof drift: {name}")
    if not 0 < usage["rear_axle_stabilization_visible_subset"] <= published["rear_axle_stabilization"]:
        raise RuntimeError("742 receipt RAS visible-subset proof drift")
    if expected_mechanical_proof["minimum_retract_chain_segment_m"] < 0.04 or expected_mechanical_proof["continuous_retract_chain_samples"] < 2001:
        raise RuntimeError("742 receipt continuous retract-chain proof drift")
    if not 0.1 <= expected_mechanical_proof["stowed_fork_bottom_m"] <= 0.4:
        raise RuntimeError("742 receipt stowed-fork height proof drift")

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
    if (args.require_deployed or args.require_release) and source["status"] != "pass":
        raise RuntimeError("742 deployed/release gate requires a receipt written with frozen-source binary verification")

    incomplete = verify_human_review(
        receipt["human_review"], receipt["candidate_tree_sha256"],
        args.require_human_reviewed or args.require_deployed or args.require_release,
        file_paths + runtime_paths + validator_paths,
    )
    if (not incomplete) != (receipt["release_status"] == "reviewed_candidate_not_deployed"):
        raise RuntimeError("742 human review and release status disagree")
    deployed = False
    if args.deployment_attestation:
        verify_deployment_attestation(args.deployment_attestation, receipt, args.receipt)
        deployed = True
    rebuild_verified = False
    if args.rebuild_attestation:
        if args.deployment_attestation and args.rebuild_attestation.resolve() != (
            args.deployment_attestation.parent / "742-deterministic-rebuild-attestation.json"
        ).resolve():
            raise RuntimeError("742 release rebuild proof must be the deployment workflow's copied companion")
        verify_rebuild_attestation(args.rebuild_attestation, receipt)
        rebuild_verified = True
    if (args.require_deployed or args.require_release) and not source_replayed:
        raise RuntimeError("742 deployed/release gate requires a fresh frozen-source binary replay")

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
        "deterministic_rebuild_verified": rebuild_verified,
        "release_gate_complete": deployed and not incomplete and source["status"] == "pass" and source_replayed and rebuild_verified,
        "release_status": receipt["release_status"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
