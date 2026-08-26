#!/usr/bin/env python3
"""Validate gate-specific, artifact-backed local review evidence for the 742.

This validator does not perform a visual or browser review. It verifies that a
review manifest binds ten distinct, semantically parsed visual/raw-browser
artifacts to one exact candidate tree and one Git commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from validate_742_browser_evidence import BROWSER_GATES, validate_complete_browser_artifact, validate_pending_template


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
HUMAN_GATES = (
    "stowed_visual_fidelity",
    "extended_visual_fidelity",
    "cab_closeup_fidelity",
    "desktop_browser_interaction",
    "mobile_browser_interaction",
    "accessibility_semantics_and_keyboard",
    "semantic_selection",
    "performance_profile",
    "600s_browser_regression",
    "es1930m_browser_regression",
)
EXPECTED_ARTIFACT_PATHS = {
    "stowed_visual_fidelity": "docs/review/742/stowed-front-left.png",
    "extended_visual_fidelity": "docs/review/742/extended-visual-fidelity.json",
    "cab_closeup_fidelity": "docs/review/742/cab-close.png",
    "desktop_browser_interaction": "docs/review/742/desktop-browser-interaction.json",
    "mobile_browser_interaction": "docs/review/742/mobile-browser-interaction.json",
    "accessibility_semantics_and_keyboard": "docs/review/742/accessibility-semantics-keyboard.json",
    "semantic_selection": "docs/review/742/semantic-selection.json",
    "performance_profile": "docs/review/742/performance-profile.json",
    "600s_browser_regression": "docs/review/742/600s-browser-regression.json",
    "es1930m_browser_regression": "docs/review/742/es1930m-browser-regression.json",
}
def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_record(path: Path) -> dict:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise RuntimeError(f"742 review artifact escapes repository: {path}") from error
    if not resolved.is_file():
        raise RuntimeError(f"Missing 742 review artifact: {relative}")
    return {"path": str(relative), "sha256": digest(resolved), "bytes": resolved.stat().st_size}


def _require_exact_true(record: dict, names: set[str], gate: str) -> None:
    if set(record) != names or any(record[name] is not True for name in names):
        raise RuntimeError(f"742 {gate} observation fields/status drift")


def _expected_upstream_identity(model: str) -> dict:
    if model == "600s":
        route = "/"
        receipt_path = ROOT / "assets/models/600s.asset-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        return {
            "route": route,
            "configuration_id": receipt["configuration_id"],
            "release": receipt["release"],
            "asset_sha256": receipt["sha256"],
            "runtime_sha256": receipt["runtime_sha256"],
            "receipt_sha256": digest(receipt_path),
            "receipt_bytes": receipt_path.stat().st_size,
        }
    receipt_path = ROOT / "assets/models/es1930m.asset-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "route": "/es1930m/",
        "configuration_id": receipt["configuration_id"],
        "release": receipt["release"],
        "asset_sha256": receipt["files"]["asset"]["sha256"],
        "runtime_sha256": receipt["runtime"]["sha256"],
        "receipt_sha256": digest(receipt_path),
        "receipt_bytes": receipt_path.stat().st_size,
    }


def _validate_extended_visual_observation(
    path: Path, candidate_tree_sha256: str, reviewed_commit: str, manifest_environment: dict, allowed_png: dict
) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    fields = {
        "schema_version", "kind", "gate", "configuration_id", "candidate_tree_sha256",
        "reviewed_source_commit", "environment", "render_artifacts", "observations", "boundary",
    }
    if set(artifact) != fields or artifact["schema_version"] != "1.0.0" or artifact["kind"] != "742-visual-gate-observation":
        raise RuntimeError("742 extended visual observation schema drift")
    expected_identity = {
        "gate": "extended_visual_fidelity", "configuration_id": EXPECTED_ID,
        "candidate_tree_sha256": candidate_tree_sha256, "reviewed_source_commit": reviewed_commit,
    }
    if any(artifact.get(key) != value for key, value in expected_identity.items()):
        raise RuntimeError("742 extended visual observation candidate binding drift")
    environment = artifact.get("environment") or {}
    if set(environment) != {"renderer", "os"} or environment["os"] != manifest_environment["os"] or "Blender" not in environment["renderer"]:
        raise RuntimeError("742 extended visual renderer environment drift")
    expected_renders = [
        "docs/review/742/maximum-lift-level-forks.png",
        "docs/review/742/maximum-lift-forks-close.png",
        "docs/review/742/maximum-reach-24in-load-center.png",
        "docs/review/742/retract-chain-routing-cutaway.png",
        "docs/review/742/steering-linkage-cutaway.png",
        "docs/review/742/boom-pivot-angle-sensor.png",
    ]
    if artifact.get("render_artifacts") != expected_renders or any(path not in allowed_png for path in expected_renders):
        raise RuntimeError("742 extended visual observation does not bind the required owned render set")
    expected_observations = {
        "maximum_lift_level_attachment_visible", "maximum_lift_fork_closeup_visible",
        "maximum_reach_load_center_pose_visible", "retract_chain_tangent_sheave_routing_visible",
        "rigid_double_ended_steering_rack_and_bars_visible",
        "rigid_boom_angle_sensor_crank_and_link_visible",
    }
    _require_exact_true(artifact.get("observations") or {}, expected_observations, "extended visual")
    if not isinstance(artifact.get("boundary"), str) or "no manufacturer geometry" not in artifact["boundary"]:
        raise RuntimeError("742 extended visual evidence boundary is incomplete")


def _verify_commit_paths(commit: str, paths: list[Path]) -> None:
    for path in paths:
        relative = str(path.resolve().relative_to(ROOT.resolve()))
        completed = subprocess.run(
            ["git", "show", f"{commit}:{relative}"], cwd=ROOT, capture_output=True, check=False,
        )
        if completed.returncode or completed.stdout != path.read_bytes():
            raise RuntimeError(f"742 reviewed commit does not contain the reviewed candidate bytes: {relative}")
    for relative in ("assets/models/600s.asset-receipt.json", "assets/models/600s.glb", "assets/models/es1930m.asset-receipt.json", "assets/models/es1930m.glb"):
        path = ROOT / relative
        completed = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT, capture_output=True, check=False)
        if completed.returncode or completed.stdout != path.read_bytes():
            raise RuntimeError(f"742 reviewed commit does not contain exact upstream regression bytes: {relative}")


def validate_review_manifest(path: Path, candidate_tree_sha256: str, canonical_paths: list[Path]) -> tuple[dict, dict]:
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_tree_sha256):
        raise RuntimeError("742 candidate tree hash is malformed")
    manifest_record = relative_record(path)
    if manifest_record["path"] != "docs/review/742/review-manifest.json":
        raise RuntimeError("742 review manifest must use its canonical repository path")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {"schema_version", "configuration_id", "candidate_tree_sha256", "reviewed_source_commit", "environment", "gates"}
    if set(manifest) != expected or manifest.get("schema_version") != "3.0.0" or manifest.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 review manifest schema/identity drift")
    if manifest.get("candidate_tree_sha256") != candidate_tree_sha256:
        raise RuntimeError("742 review manifest does not bind the current candidate tree")
    commit = manifest.get("reviewed_source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("742 review manifest requires an exact reviewed source commit")
    environment = manifest.get("environment")
    if set(environment or {}) != {"browser", "os"}:
        raise RuntimeError("742 review manifest environment schema drift")
    if set(environment["browser"] or {}) != {"name", "version", "user_agent"} or set(environment["os"] or {}) != {"name", "version", "build"}:
        raise RuntimeError("742 review manifest exact browser/OS identity drift")
    if not all(isinstance(value, str) and value.strip() for group in environment.values() for value in group.values()):
        raise RuntimeError("742 review manifest browser/OS identity is incomplete")
    if set(manifest.get("gates") or {}) != set(HUMAN_GATES):
        raise RuntimeError("742 review manifest must address every canonical review gate")
    _verify_commit_paths(commit, canonical_paths)

    reviewed: dict[str, dict] = {}
    seen_artifacts: set[str] = set()
    allowlist = json.loads((ROOT / "docs/review/742/OWNED_RENDER_ALLOWLIST.json").read_text(encoding="utf-8"))
    allowed_png = {item["path"]: item for item in allowlist["artifacts"]}
    for gate in HUMAN_GATES:
        entry = manifest["gates"][gate]
        if set(entry) != {"status", "artifact", "notes"} or entry["status"] != "pass" or not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise RuntimeError(f"742 review gate is not explicitly passed: {gate}")
        expected_path = EXPECTED_ARTIFACT_PATHS[gate]
        if entry.get("artifact", {}).get("path") != expected_path or expected_path in seen_artifacts:
            raise RuntimeError(f"742 review gate must use its distinct canonical artifact: {gate}")
        seen_artifacts.add(expected_path)
        artifact_path = ROOT / expected_path
        actual = relative_record(artifact_path)
        if actual != entry["artifact"]:
            raise RuntimeError(f"742 review artifact hash/size drift: {gate}")
        if artifact_path.suffix.lower() == ".png":
            allowed = allowed_png.get(expected_path)
            if not allowed or actual != {key: allowed[key] for key in ("path", "sha256", "bytes")}:
                raise RuntimeError(f"742 visual review artifact is not in the owned-render allowlist: {gate}")
            data = artifact_path.read_bytes()
            if data[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", data[16:24]) != (allowed["width_px"], allowed["height_px"]):
                raise RuntimeError(f"742 visual review PNG structure drift: {gate}")
        elif gate == "extended_visual_fidelity":
            _validate_extended_visual_observation(
                artifact_path, candidate_tree_sha256, commit, environment, allowed_png
            )
        elif gate in BROWSER_GATES:
            upstream = None
            if gate in {"600s_browser_regression", "es1930m_browser_regression"}:
                upstream = _expected_upstream_identity("600s" if gate.startswith("600s") else "es1930m")
            artifact_environment = validate_complete_browser_artifact(
                artifact_path, gate, candidate_tree_sha256, commit, upstream
            )
            for group in ("browser", "os"):
                if artifact_environment[group] != environment[group]:
                    raise RuntimeError(f"742 {gate} capture environment disagrees with review manifest")
        else:
            raise RuntimeError(f"742 review gate has no semantic parser: {gate}")
        reviewed[gate] = {"status": "pass", "artifact": actual}
    return reviewed, {
        "manifest": manifest_record,
        "candidate_tree_sha256": candidate_tree_sha256,
        "reviewed_source_commit": commit,
        "environment": environment,
    }


def validate_pending_review_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {"schema_version", "configuration_id", "candidate_tree_sha256", "reviewed_source_commit", "environment", "gates"}
    if set(manifest) != expected or manifest.get("schema_version") != "3.0.0" or manifest.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 pending review manifest schema/identity drift")
    if manifest.get("candidate_tree_sha256") != "PENDING" or manifest.get("reviewed_source_commit") != "PENDING" or manifest.get("environment") is not None:
        raise RuntimeError("742 pending review manifest has a candidate binding")
    if set(manifest.get("gates") or {}) != set(HUMAN_GATES):
        raise RuntimeError("742 pending review manifest gate set drift")
    for gate, entry in manifest["gates"].items():
        if set(entry or {}) != {"status", "artifact", "notes"} or entry["status"] != "pending" or entry["artifact"] is not None or not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise RuntimeError(f"742 pending review gate state drift: {gate}")
    for gate in BROWSER_GATES:
        validate_pending_template(ROOT / EXPECTED_ARTIFACT_PATHS[gate], gate)
    extended = json.loads((ROOT / EXPECTED_ARTIFACT_PATHS["extended_visual_fidelity"]).read_text(encoding="utf-8"))
    if extended.get("candidate_tree_sha256") != "PENDING" or extended.get("reviewed_source_commit") != "PENDING":
        raise RuntimeError("742 pending extended-visual record is already bound")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/review/742/review-manifest.json")
    parser.add_argument("--candidate-tree-sha256")
    parser.add_argument("--canonical-path", action="append", default=[])
    parser.add_argument("--allow-pending-manifest", action="store_true")
    args = parser.parse_args()
    if args.allow_pending_manifest:
        if args.candidate_tree_sha256 or args.canonical_path:
            raise RuntimeError("Pending review validation cannot accept candidate bindings")
        validate_pending_review_manifest(args.manifest)
        print(json.dumps({"status": "PASS", "pending_gates": list(HUMAN_GATES)}, indent=2, sort_keys=True))
        return
    if not args.candidate_tree_sha256:
        raise RuntimeError("Completed review validation requires --candidate-tree-sha256")
    paths = [ROOT / value for value in args.canonical_path]
    reviewed, binding = validate_review_manifest(args.manifest, args.candidate_tree_sha256, paths)
    print(json.dumps({
        "status": "PASS",
        "configuration_id": EXPECTED_ID,
        "reviewed_source_commit": binding["reviewed_source_commit"],
        "gates_verified": sorted(reviewed),
        "distinct_artifacts": len({gate["artifact"]["path"] for gate in reviewed.values()}),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
