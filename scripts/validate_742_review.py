#!/usr/bin/env python3
"""Validate gate-specific, artifact-backed local review evidence for the 742.

This validator does not perform a visual or browser review. It verifies that a
review manifest binds ten distinct, semantically parsed visual/raw-browser
artifacts to one exact candidate tree and one Git commit, plus the populated
post-capture browser allowlist as review-support evidence.
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
BROWSER_CAPTURE_ALLOWLIST_PATH = "docs/review/742/BROWSER_CAPTURE_ALLOWLIST.json"

# Every mechanically material owned render must prove one named observation.
# Keeping the semantic claim, canonical path, and allowlisted file identity in
# one record prevents an otherwise unused allowlist entry from satisfying this
# gate by count alone.
EXTENDED_VISUAL_RENDER_CONTRACT = (
    {
        "semantic_id": "maximum_lift_level_attachment",
        "path": "docs/review/742/maximum-lift-level-forks.png",
        "claim": "Level fork load surface is visible at the selected reconstructed maximum-lift pose.",
    },
    {
        "semantic_id": "maximum_lift_fork_closeup",
        "path": "docs/review/742/maximum-lift-forks-close.png",
        "claim": "Fork heels, blades, and the red validated posed-GLB fork-top/load-surface datum with exact contact markers are fully framed at maximum lift.",
    },
    {
        "semantic_id": "maximum_reach_load_center_pose",
        "path": "docs/review/742/maximum-reach-24in-load-center.png",
        "claim": "The selected 3 degree maximum-reach pose and 24 inch load-center reference are visible.",
    },
    {
        "semantic_id": "retract_chain_tangent_sheave_routing",
        "path": "docs/review/742/retract-chain-routing-cutaway.png",
        "claim": "Retract-chain tangent legs, sheave wrap, and moving termination are visible.",
    },
    {
        "semantic_id": "through_rod_two_tie_bars_four_pivots",
        "path": "docs/review/742/steering-linkage-cutaway.png",
        "claim": "One through-rod steering cylinder with two visible rod ends, two rigid tie bars, and four highlighted pivots is visible.",
    },
    {
        "semantic_id": "rear_through_rod_two_tie_bars_four_joints",
        "path": "docs/review/742/rear-steering-linkage.png",
        "claim": "The unobstructed REAR AXLE / FIXED THROUGH-ROD RACK caption identifies the rear state; the through-rod rack, two rigid tie bars, and all four highlighted joints are visible without label overlap.",
    },
    {
        "semantic_id": "circle_headings_two_actual_icrs_scrub",
        "path": "docs/review/742/circle-steering-plan.png",
        "claim": "The visible CIRCLE label reports reconstructed headings FL 55.000 / FR 54.914 / RL -55.000 / RR -54.914 deg, TWO ACTUAL ICR CONSTRUCTIONS, and SCRUB DIAGNOSTIC 93.466% — NOT FACTORY ACKERMANN; both ICR constructions are drawn.",
    },
    {
        "semantic_id": "crab_headings_toe_diagnostics",
        "path": "docs/review/742/crab-steering-plan.png",
        "claim": "The visible CRAB label reports reconstructed headings FL 55.000 / FR 54.914 / RL 54.914 / RR 55.000 deg, FULL-POSE TOE 0.086 deg, and DENSE MAX 0.753 deg.",
    },
    {
        "semantic_id": "front_headings_rear_aligned_actual_icrs_scrub",
        "path": "docs/review/742/front-steering-plan.png",
        "claim": "The visible FRONT label reports reconstructed headings FL 55.000 / FR 54.914 deg, REAR HELD ALIGNED, ACTUAL FRONT ICR CONSTRUCTIONS, and SCRUB DIAGNOSTIC 61.060% — NOT FACTORY ACKERMANN; the front ICR construction lines are drawn.",
    },
    {
        "semantic_id": "rigid_boom_angle_sensor_crank_and_link",
        "path": "docs/review/742/boom-pivot-angle-sensor.png",
        "claim": "Rigid boom-angle sensor crank, link, frame joint, and boom joint are visible.",
    },
    {
        "semantic_id": "rigid_boom_cab_clearance_datum",
        "path": "docs/review/742/boom-cab-clearance-datum.png",
        "claim": "The exact exported-GLB limiting boom-to-inner-cab-handrail clearance datum is visible and labeled 45.027 mm.",
    },
    {
        "semantic_id": "boom_hose_valve_bank_clearance_datum",
        "path": "docs/review/742/hose-valve-clearance-datum.png",
        "claim": "The exact exported-GLB boom-hose-to-main-valve-bank clearance datum is visible and labeled 34.000 mm.",
    },
)
FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS = {
    "docs/review/742/front-steering-limited-plan.png",
}
SEPARATE_VISUAL_GATE_PATHS = {
    "docs/review/742/stowed-front-left.png",
    "docs/review/742/cab-close.png",
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


def read_owned_render_allowlist_records() -> dict[str, dict]:
    allowlist = json.loads((ROOT / "docs/review/742/OWNED_RENDER_ALLOWLIST.json").read_text(encoding="utf-8"))
    if set(allowlist) != {"schema_version", "kind", "artifacts"}:
        raise RuntimeError("742 owned-render allowlist schema drift")
    if allowlist["schema_version"] != "1.0.0" or allowlist["kind"] != "owned-742-review-render-allowlist":
        raise RuntimeError("742 owned-render allowlist identity drift")
    records: dict[str, dict] = {}
    expected_fields = {"path", "sha256", "bytes", "width_px", "height_px", "provenance"}
    for record in allowlist.get("artifacts") or []:
        if not isinstance(record, dict) or set(record) != expected_fields:
            raise RuntimeError("742 owned-render allowlist artifact schema drift")
        render_path = record.get("path")
        if not isinstance(render_path, str) or render_path in records:
            raise RuntimeError("742 owned-render allowlist path identity drift")
        if render_path in FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS:
            raise RuntimeError(f"742 forbidden superseded render is allowlisted: {render_path}")
        records[render_path] = record
    return records


def validate_owned_render_semantic_coverage(allowed_png: dict[str, dict]) -> None:
    present_forbidden = sorted(FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS & set(allowed_png))
    existing_forbidden = sorted(
        path for path in FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS if (ROOT / path).exists()
    )
    if present_forbidden or existing_forbidden:
        raise RuntimeError(
            "742 superseded front-steering render is forbidden: "
            f"allowlisted={present_forbidden}, present={existing_forbidden}"
        )
    expected_paths = SEPARATE_VISUAL_GATE_PATHS | {
        contract["path"] for contract in EXTENDED_VISUAL_RENDER_CONTRACT
    }
    actual_paths = set(allowed_png)
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        unreferenced = sorted(actual_paths - expected_paths)
        raise RuntimeError(
            "742 owned-render semantic coverage drift: "
            f"missing={missing}, unreferenced={unreferenced}"
        )


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
        }
    receipt_path = ROOT / "assets/models/es1930m.asset-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return {
        "route": "/es1930m/",
        "configuration_id": receipt["configuration_id"],
        "release": receipt["release"],
        "asset_sha256": receipt["files"]["asset"]["sha256"],
        "runtime_sha256": receipt["runtime"]["sha256"],
    }


def _validate_extended_visual_semantics(
    artifact: dict, allowed_png: dict, *, expected_observed: bool = True
) -> None:
    fields = {
        "schema_version", "kind", "gate", "configuration_id", "candidate_tree_sha256",
        "reviewed_source_commit", "environment", "render_observations", "boundary",
    }
    if set(artifact) != fields or artifact["schema_version"] != "2.0.0" or artifact["kind"] != "742-visual-gate-observation":
        raise RuntimeError("742 extended visual observation schema drift")
    if artifact.get("gate") != "extended_visual_fidelity" or artifact.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 extended visual observation identity drift")
    environment = artifact.get("environment") or {}
    if set(environment) != {"renderer", "os"} or not isinstance(environment["renderer"], str) or "Blender" not in environment["renderer"]:
        raise RuntimeError("742 extended visual renderer environment drift")
    observations = artifact.get("render_observations")
    if not isinstance(observations, list) or len(observations) != len(EXTENDED_VISUAL_RENDER_CONTRACT):
        raise RuntimeError("742 extended visual observation does not cover the exact mechanical render set")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, (observation, expected) in enumerate(zip(observations, EXTENDED_VISUAL_RENDER_CONTRACT)):
        if not isinstance(observation, dict) or set(observation) != {"semantic_id", "claim", "observed", "artifact"}:
            raise RuntimeError(f"742 extended visual semantic record schema drift at index {index}")
        if observation["semantic_id"] != expected["semantic_id"] or observation["claim"] != expected["claim"]:
            raise RuntimeError(f"742 extended visual semantic claim drift: {expected['semantic_id']}")
        if observation["observed"] is not expected_observed:
            state = "observed" if expected_observed else "pending"
            raise RuntimeError(
                f"742 extended visual semantic claim has wrong {state} state: {expected['semantic_id']}"
            )
        render_path = expected["path"]
        if render_path in FORBIDDEN_EXTENDED_VISUAL_RENDER_PATHS:
            raise RuntimeError(f"742 superseded front-steering render is forbidden: {render_path}")
        if render_path in seen_paths or expected["semantic_id"] in seen_ids:
            raise RuntimeError("742 extended visual semantic records must use distinct IDs and artifacts")
        seen_ids.add(expected["semantic_id"])
        seen_paths.add(render_path)
        allowed = allowed_png.get(render_path)
        if not allowed:
            raise RuntimeError(f"742 extended visual render is not allowlisted: {render_path}")
        expected_artifact = {key: allowed[key] for key in ("path", "sha256", "bytes")}
        if observation["artifact"] != expected_artifact:
            raise RuntimeError(f"742 extended visual render hash/size binding drift: {render_path}")
    boundary = artifact.get("boundary")
    if (
        not isinstance(boundary, str)
        or "no manufacturer geometry" not in boundary
        or "not factory steering or crab calibration" not in boundary
    ):
        raise RuntimeError("742 extended visual evidence boundary is incomplete")


def _validate_extended_visual_observation(
    path: Path, candidate_tree_sha256: str, reviewed_commit: str, manifest_environment: dict, allowed_png: dict
) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    _validate_extended_visual_semantics(artifact, allowed_png)
    expected_identity = {
        "candidate_tree_sha256": candidate_tree_sha256,
        "reviewed_source_commit": reviewed_commit,
    }
    if any(artifact.get(key) != value for key, value in expected_identity.items()):
        raise RuntimeError("742 extended visual observation candidate binding drift")
    if artifact["environment"]["os"] != manifest_environment["os"]:
        raise RuntimeError("742 extended visual renderer OS identity drift")


def validate_pending_extended_visual_observation(path: Path, allowed_png: dict) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    _validate_extended_visual_semantics(artifact, allowed_png, expected_observed=False)
    if artifact.get("candidate_tree_sha256") != "PENDING" or artifact.get("reviewed_source_commit") != "PENDING":
        raise RuntimeError("742 pending extended-visual record is already bound")
    if artifact["environment"]["os"] is not None:
        raise RuntimeError("742 pending extended-visual record has a captured OS identity")


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
    canonical_relatives = {
        str(candidate.resolve().relative_to(ROOT.resolve())) for candidate in canonical_paths
    }
    if BROWSER_CAPTURE_ALLOWLIST_PATH in canonical_relatives:
        raise RuntimeError("742 browser-capture allowlist is post-candidate review evidence, not a canonical candidate path")
    _verify_commit_paths(commit, canonical_paths)

    reviewed: dict[str, dict] = {}
    seen_artifacts: set[str] = set()
    referenced_browser_captures: list[str] = []
    allowed_png = read_owned_render_allowlist_records()
    validate_owned_render_semantic_coverage(allowed_png)
    for gate in HUMAN_GATES:
        entry = manifest["gates"][gate]
        if set(entry) != {"status", "artifact", "notes"} or entry["status"] != "pass" or not isinstance(entry["notes"], str) or not entry["notes"].strip():
            raise RuntimeError(f"742 review gate is not explicitly passed: {gate}")
        if re.search(r"\b(?:pending|recapture-required|not reviewed|awaiting review)\b", entry["notes"], re.IGNORECASE):
            raise RuntimeError(f"742 passed review gate contains unresolved review language: {gate}")
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
            browser_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            capture_artifacts = browser_artifact["capture_artifacts"]
            referenced_browser_captures.extend(
                item["path"] for item in capture_artifacts["screenshots"]
            )
            referenced_browser_captures.append(capture_artifacts["automation_trace"]["path"])
            for group in ("browser", "os"):
                if artifact_environment[group] != environment[group]:
                    raise RuntimeError(f"742 {gate} capture environment disagrees with review manifest")
        else:
            raise RuntimeError(f"742 review gate has no semantic parser: {gate}")
        reviewed[gate] = {"status": "pass", "artifact": actual}
    browser_allowlist_path = ROOT / BROWSER_CAPTURE_ALLOWLIST_PATH
    browser_allowlist = json.loads(browser_allowlist_path.read_text(encoding="utf-8"))
    allowlisted_browser_captures = {
        item["path"] for item in browser_allowlist.get("artifacts") or []
    }
    referenced_browser_capture_set = set(referenced_browser_captures)
    duplicate_references = sorted({
        item for item in referenced_browser_captures if referenced_browser_captures.count(item) != 1
    })
    if duplicate_references or referenced_browser_capture_set != allowlisted_browser_captures:
        missing = sorted(allowlisted_browser_captures - referenced_browser_capture_set)
        unallowlisted = sorted(referenced_browser_capture_set - allowlisted_browser_captures)
        raise RuntimeError(
            "742 browser capture allowlist/gate coverage drift: "
            f"unused={missing}, unallowlisted={unallowlisted}, duplicates={duplicate_references}"
        )
    return reviewed, {
        "manifest": manifest_record,
        "browser_capture_allowlist": relative_record(browser_allowlist_path),
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
    allowed_png = read_owned_render_allowlist_records()
    validate_owned_render_semantic_coverage(allowed_png)
    validate_pending_extended_visual_observation(
        ROOT / EXPECTED_ARTIFACT_PATHS["extended_visual_fidelity"],
        allowed_png,
    )


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
