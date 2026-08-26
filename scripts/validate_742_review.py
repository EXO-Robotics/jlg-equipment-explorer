#!/usr/bin/env python3
"""Validate gate-specific, artifact-backed local review evidence for the 742.

This validator does not perform a visual or browser review. It verifies that a
human-authored manifest binds ten distinct, semantically parseable observations
to one exact candidate tree and one Git commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


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
COMMON_OBSERVATION_FIELDS = {
    "schema_version", "kind", "gate", "configuration_id", "candidate_tree_sha256",
    "reviewed_source_commit", "environment", "observations", "boundary",
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


def _validate_json_observation(
    gate: str, path: Path, candidate_tree_sha256: str, reviewed_commit: str, manifest_environment: dict
) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if set(artifact) != COMMON_OBSERVATION_FIELDS:
        raise RuntimeError(f"742 review observation schema drift: {gate}")
    if artifact["schema_version"] != "1.0.0" or artifact["kind"] != "742-gate-observation":
        raise RuntimeError(f"742 review observation identity drift: {gate}")
    if artifact["gate"] != gate or artifact["configuration_id"] != EXPECTED_ID:
        raise RuntimeError(f"742 review observation gate/configuration drift: {gate}")
    if artifact["candidate_tree_sha256"] != candidate_tree_sha256 or artifact["reviewed_source_commit"] != reviewed_commit:
        raise RuntimeError(f"742 review observation candidate binding drift: {gate}")
    environment = artifact["environment"]
    if not isinstance(environment, dict) or any(environment.get(key) != value for key, value in manifest_environment.items()):
        raise RuntimeError(f"742 review observation environment drift: {gate}")
    if not isinstance(artifact["boundary"], str) or not artifact["boundary"].strip():
        raise RuntimeError(f"742 review observation boundary missing: {gate}")
    observations = artifact["observations"]
    if not isinstance(observations, dict):
        raise RuntimeError(f"742 review observations malformed: {gate}")

    if gate == "desktop_browser_interaction":
        if environment.get("viewport_css_px") != [1280, 720]:
            raise RuntimeError("742 desktop interaction viewport identity drift")
        if set(observations) != {"dom_dataset", "interaction_transcript"}:
            raise RuntimeError("742 desktop interaction transcript schema drift")
        dataset = observations["dom_dataset"]
        expected_dataset = {
            "machine_source": "glb-validated", "render_profile": "desktop", "pixel_ratio": 1.0,
            "shadow_profile": "1024px-14m", "frame_sample_count": 180, "frame_p95_ms": 17.6,
            "frame_worst_ms": 33.3, "visible_stall_count": 0, "selection_overlap_rays": 15,
            "selection_priority_rays": 15, "runtime_error_count": 0,
        }
        if dataset != expected_dataset:
            raise RuntimeError("742 desktop raw DOM dataset drift")
        transcript = observations["interaction_transcript"]
        if not isinstance(transcript, list) or len(transcript) != 4 or any(set(item) != {"action", "observed"} for item in transcript):
            raise RuntimeError("742 desktop interaction transcript is incomplete")
        required_terms = ("load /742/", "five mechanism sliders", "maximum pose", "select Boom")
        if any(term not in transcript[index]["action"] for index, term in enumerate(required_terms)):
            raise RuntimeError("742 desktop interaction transcript action drift")
    elif gate == "mobile_browser_interaction":
        if environment.get("viewports_css_px") != [[390, 844], [844, 390]]:
            raise RuntimeError("742 mobile interaction viewport identity drift")
        if set(observations) != {"dom_datasets", "interaction_transcript"}:
            raise RuntimeError("742 mobile interaction transcript schema drift")
        datasets = observations["dom_datasets"]
        expected_profiles = {
            "portrait": ("portrait", "512px-16m", 17.7, 49.1),
            "short_landscape": ("short-landscape", "512px-14m", 17.8, 33.4),
        }
        if set(datasets) != set(expected_profiles):
            raise RuntimeError("742 mobile DOM dataset profile set drift")
        fields = {"source", "render_profile", "pixel_ratio", "shadow_profile", "sample_count", "p95_ms", "worst_ms", "visible_stalls", "runtime_errors"}
        for name, (profile, shadow, p95, worst) in expected_profiles.items():
            dataset = datasets[name]
            if set(dataset) != fields or dataset != {
                "source": "glb-validated", "render_profile": profile, "pixel_ratio": 1.0,
                "shadow_profile": shadow, "sample_count": 180, "p95_ms": p95, "worst_ms": worst,
                "visible_stalls": 0, "runtime_errors": 0,
            }:
                raise RuntimeError(f"742 {name} raw DOM dataset drift")
        transcript = observations["interaction_transcript"]
        if not isinstance(transcript, list) or len(transcript) != 4 or any(set(item) != {"viewport_css_px", "action", "observed"} for item in transcript):
            raise RuntimeError("742 mobile interaction transcript is incomplete")
        if transcript[0]["viewport_css_px"] != [390, 844] or transcript[2]["viewport_css_px"] != [844, 390] or "five sliders" not in transcript[2]["observed"] or "component selection" not in transcript[3]["observed"]:
            raise RuntimeError("742 mobile interaction transcript observation drift")
    elif gate == "accessibility_semantics_and_keyboard":
        if set(observations) != {"semantic_snapshot", "keyboard_transcript"}:
            raise RuntimeError("742 accessibility observation schema drift")
        snapshot = observations["semantic_snapshot"]
        if snapshot != {
            "application_instructions_exposed": True,
            "slider_aria_valuetext": ["0°", "0.00 m visual", "0°", "Center", "Level"],
            "dialog_background_inert": True,
            "physical_screen_reader_session_claimed": False,
        }:
            raise RuntimeError("742 accessibility semantic snapshot drift")
        transcript = observations["keyboard_transcript"]
        if not isinstance(transcript, list) or len(transcript) != 4 or any(set(item) != {"action", "observed"} for item in transcript):
            raise RuntimeError("742 accessibility keyboard transcript is incomplete")
        if "focus remained trapped" not in transcript[0]["observed"] or "focus returned" not in transcript[1]["observed"] or "Showcase disabled" not in transcript[3]["observed"]:
            raise RuntimeError("742 accessibility keyboard transcript did not pass")
        if snapshot["physical_screen_reader_session_claimed"] is not False or not any(
            token in artifact["boundary"] for token in ("VoiceOver", "NVDA")
        ):
            raise RuntimeError("742 accessibility gate must not imply a physical screen-reader review")
    elif gate == "semantic_selection":
        if set(observations) != {"dom_dataset", "selection_transcript"}:
            raise RuntimeError("742 semantic-selection observation schema drift")
        if observations["dom_dataset"] != {
            "semantic_volume_count": 6, "semantic_volume_ready_count": 6, "selection_overlap_rays": 15,
            "selection_priority_rays": 15, "selection_self_test": "pass", "proxy_volume_shadows": "disabled",
        }:
            raise RuntimeError("742 semantic-selection raw DOM dataset drift")
        transcript = observations["selection_transcript"]
        if not isinstance(transcript, list) or len(transcript) != 4 or any(set(item) != {"action", "observed"} for item in transcript):
            raise RuntimeError("742 semantic-selection transcript is incomplete")
        if "15 of 15" not in transcript[0]["observed"] or "aria-pressed" not in transcript[1]["observed"] or "no component" not in transcript[3]["observed"]:
            raise RuntimeError("742 semantic-selection transcript did not pass")
    elif gate == "performance_profile":
        if environment.get("viewports_css_px") != [[1280, 720], [390, 844], [844, 390]]:
            raise RuntimeError("742 performance viewport identity drift")
        expected = {
            "desktop", "portrait", "short_landscape", "background_samples_excluded", "visible_stalls_included",
            "artifact_safe_sample_metadata_exposed", "physical_low_end_mobile_gpu_claimed",
        }
        if set(observations) != expected:
            raise RuntimeError("742 performance observation schema drift")
        profile_fields = {
            "viewport_css_px", "render_profile", "pixel_ratio", "shadow_profile", "sample_count", "p95_frame_time_ms",
            "worst_frame_time_ms", "visible_stall_count_gte_250ms", "runtime_error_count", "machine_source",
        }
        expected_profiles = {
            "desktop": ([1280, 720], "desktop", "1024px-14m"),
            "portrait": ([390, 844], "portrait", "512px-16m"),
            "short_landscape": ([844, 390], "short-landscape", "512px-14m"),
        }
        for name, (viewport, render_profile, shadow_profile) in expected_profiles.items():
            profile = observations[name]
            if set(profile) != profile_fields or profile["viewport_css_px"] != viewport or profile["render_profile"] != render_profile or profile["pixel_ratio"] != 1.0 or profile["shadow_profile"] != shadow_profile:
                raise RuntimeError(f"742 {name} performance profile identity drift")
            if profile["sample_count"] < 60 or not 0 < profile["p95_frame_time_ms"] <= 50 or not 0 < profile["worst_frame_time_ms"] < 250:
                raise RuntimeError(f"742 {name} frame-time samples are incomplete or outside the local gate")
            if profile["visible_stall_count_gte_250ms"] != 0 or profile["runtime_error_count"] != 0 or profile["machine_source"] != "glb-validated":
                raise RuntimeError(f"742 {name} performance observation did not pass")
        if observations["background_samples_excluded"] is not True or observations["visible_stalls_included"] is not True or observations["artifact_safe_sample_metadata_exposed"] is not True:
            raise RuntimeError("742 performance sampling-boundary observation did not pass")
        if observations["physical_low_end_mobile_gpu_claimed"] is not False:
            raise RuntimeError("742 local performance gate cannot claim physical low-end mobile GPU proof")


def _validate_regression_observation(
    gate: str, path: Path, candidate_tree_sha256: str, reviewed_commit: str, manifest_environment: dict
) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected_fields = COMMON_OBSERVATION_FIELDS | {"upstream_identity"}
    if set(artifact) != expected_fields or artifact.get("kind") != "742-upstream-regression-observation":
        raise RuntimeError(f"742 upstream regression schema drift: {gate}")
    # Validate common identity/environment without trying to apply the ordinary gate parser.
    for field, expected in {
        "schema_version": "1.0.0", "gate": gate, "configuration_id": EXPECTED_ID,
        "candidate_tree_sha256": candidate_tree_sha256, "reviewed_source_commit": reviewed_commit,
    }.items():
        if artifact.get(field) != expected:
            raise RuntimeError(f"742 upstream regression binding drift: {gate}:{field}")
    if any((artifact.get("environment") or {}).get(key) != value for key, value in manifest_environment.items()):
        raise RuntimeError(f"742 upstream regression environment drift: {gate}")
    model = "600s" if gate.startswith("600s") else "es1930m"
    if artifact["upstream_identity"] != _expected_upstream_identity(model):
        raise RuntimeError(f"742 {model} regression does not bind the exact current upstream release")
    observations = artifact.get("observations") or {}
    if set(observations) != {"title", "status_text", "parsed_status", "interaction_transcript"}:
        raise RuntimeError(f"742 {model} regression observation schema drift")
    transcript = observations["interaction_transcript"]
    if not isinstance(transcript, list) or len(transcript) != 1 or set(transcript[0]) != {"action", "observed"} or "errors 0" not in transcript[0]["observed"]:
        raise RuntimeError(f"742 {model} regression transcript is incomplete")
    if model == "600s":
        expected_status = {"source": "blender-showcase-v1.1.0", "meshes": 92, "selection": "5/5 pass", "errors": 0, "load_ms": 106, "render_profile": "desktop", "fps": 60, "p95_ms": 17.8, "reduced_motion": "off"}
        if observations["title"] != "600S Interactive Equipment Study" or observations["parsed_status"] != expected_status or "selection 5/5 pass" not in observations["status_text"]:
            raise RuntimeError("742 600S regression title/status DOM drift")
    else:
        expected_status = {"machine": "es1930m", "configuration_id": "ES1930M-PVC2404-US-STD-FR-FLA130-NM", "source": "glb", "selection": "self-test-pass", "errors": 0, "load_ms": 26, "fps": 61, "p95_ms": 17.1}
        if observations["title"] != "ES1930M Interactive Equipment Study" or observations["parsed_status"] != expected_status or "selection self-test-pass" not in observations["status_text"]:
            raise RuntimeError("742 ES1930M regression title/status DOM drift")
    if not isinstance(artifact.get("boundary"), str) or "no new" not in artifact["boundary"].lower():
        raise RuntimeError(f"742 {model} regression boundary is incomplete")


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
        "docs/review/742/maximum-reach-24in-load-center.png",
        "docs/review/742/retract-chain-routing-cutaway.png",
        "docs/review/742/steering-linkage-cutaway.png",
    ]
    if artifact.get("render_artifacts") != expected_renders or any(path not in allowed_png for path in expected_renders):
        raise RuntimeError("742 extended visual observation does not bind the required owned render set")
    expected_observations = {
        "maximum_lift_level_attachment_visible", "maximum_reach_load_center_pose_visible",
        "retract_chain_sheave_routing_visible",
        "double_ended_steering_ram_and_bars_visible",
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
    if set(manifest) != expected or manifest.get("schema_version") != "2.0.0" or manifest.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 review manifest schema/identity drift")
    if manifest.get("candidate_tree_sha256") != candidate_tree_sha256:
        raise RuntimeError("742 review manifest does not bind the current candidate tree")
    commit = manifest.get("reviewed_source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("742 review manifest requires an exact reviewed source commit")
    environment = manifest.get("environment")
    if set(environment or {}) != {"browser", "os"} or not all(isinstance(environment[key], str) and environment[key] for key in environment):
        raise RuntimeError("742 review manifest environment schema drift")
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
        elif gate in {"600s_browser_regression", "es1930m_browser_regression"}:
            _validate_regression_observation(gate, artifact_path, candidate_tree_sha256, commit, environment)
        else:
            _validate_json_observation(gate, artifact_path, candidate_tree_sha256, commit, environment)
        reviewed[gate] = {"status": "pass", "artifact": actual}
    return reviewed, {
        "manifest": manifest_record,
        "candidate_tree_sha256": candidate_tree_sha256,
        "reviewed_source_commit": commit,
        "environment": environment,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidate-tree-sha256", required=True)
    parser.add_argument("--canonical-path", action="append", default=[])
    args = parser.parse_args()
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
