#!/usr/bin/env python3
"""Validate exact, executable upstream browser evidence before ES predeploy binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from validate_742_browser_evidence import (
    EXPECTED_600S_AX_SLIDER_VALUES,
    EXPECTED_ES_AX_SLIDER_VALUES,
    _validate_accessibility_tree,
    _validate_browser_bundle,
    _validate_fatal_failures,
    _validate_live_reduced_motion,
    _validate_upstream_screenshot_framing,
)


ROOT = Path(__file__).resolve().parents[1]
ES_ARTIFACT = ROOT / "docs/review/742/es1930m-browser-regression.json"
UPSTREAM_600S_ARTIFACT = ROOT / "docs/review/742/600s-browser-regression.json"
PREDEPLOY_GATES = (
    "stowed_silhouette_reviewed", "platform_controls_visual_reviewed",
    "raised_pose_browser_reviewed", "extension_browser_reviewed",
    "steering_boundary_reviewed", "figure_eight_presentation_reviewed",
    "mobile_drag_direction_reviewed", "accessibility_reviewed",
    "desktop_browser_zero_errors", "mobile_and_pinch_reviewed",
    "selection_and_focus_reviewed", "performance_reviewed",
    "600s_regression_suite_pass",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outcome_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def normalized_browser_evidence(artifact: dict) -> dict:
    """Return captured evidence without the later 742 review-binding envelope."""
    excluded = {"candidate_tree_sha256", "reviewed_source_commit"}
    return {key: value for key, value in artifact.items() if key not in excluded}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _validate_record(record: dict, label: str) -> Path:
    path = ROOT / str(record.get("path", ""))
    _require(path.is_file(), f"{label} is missing: {path}")
    _require(digest(path) == record.get("sha256"), f"{label} hash drift")
    _require(path.stat().st_size == record.get("bytes"), f"{label} byte-count drift")
    return path


def _passed(assertions: dict, name: str) -> dict:
    record = assertions.get(name)
    _require(isinstance(record, dict) and record.get("outcome") == "pass", f"Browser assertion incomplete: {name}")
    return record


def validate_artifact(path: Path, *, receipt: dict, model: str) -> dict:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    gate = f"{model}_browser_regression" if model == "600s" else "es1930m_browser_regression"
    _require(artifact.get("schema_version") == "2.0.0", f"{model} browser schema drift")
    _require(artifact.get("gate") == gate and artifact.get("capture_status") == "complete", f"{model} browser capture is incomplete")
    _require(artifact.get("kind") == "742-upstream-regression-capture", f"{model} browser capture kind drift")
    _require(artifact.get("boundary") == "Exact current upstream release regression in local headless Chromium only; no deployment, physical-device, or manufacturer-equivalence claim.", f"{model} browser evidence boundary drift")
    environment = artifact.get("environment") or {}
    _require(environment.get("physical_device_session") is False and environment.get("assistive_technology_session") is False, f"{model} browser environment overclaims physical or AT review")

    runner = artifact.get("capture_runner") or {}
    _validate_record(runner, f"{model} capture runner")
    _require(runner.get("path") == "scripts/capture_742_browser_evidence.mjs", f"{model} capture runner path drift")
    capture_artifacts = artifact.get("capture_artifacts") or {}
    trace_record = capture_artifacts.get("automation_trace") or {}
    trace_path = _validate_record(trace_record, f"{model} raw automation trace")
    screenshot_records = capture_artifacts.get("screenshots") or []
    expected_screenshot_count = 3 if model == "es1930m" else 2
    _require(len(screenshot_records) == expected_screenshot_count, f"{model} screenshot set drift")
    for index, record in enumerate(screenshot_records):
        _validate_record(record, f"{model} screenshot {index + 1}")
        _require(
            isinstance(record.get("width_px"), int) and record["width_px"] > 0
            and isinstance(record.get("height_px"), int) and record["height_px"] > 0,
            f"{model} screenshot dimensions are invalid",
        )
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assertions = (artifact.get("observations") or {}).get("assertions") or {}
    _require(trace.get("schema_version") == "2.0.0" and trace.get("gate") == gate, f"{model} trace identity drift")
    _require(trace.get("runner") == runner, f"{model} trace runner drift")
    toolchain = environment.get("automation") or {}
    _require(trace.get("toolchain") == toolchain, f"{model} trace/toolchain binding drift")
    _require(toolchain.get("source") == "repo-locked-default", f"{model} browser toolchain is not repository-owned")
    _validate_record(toolchain.get("lockfile") or {}, f"{model} browser lockfile")
    browser_executable = toolchain.get("browser_executable") or {}
    _require(
        browser_executable.get("product") == "chromium"
        and isinstance(browser_executable.get("revision"), str) and browser_executable["revision"]
        and isinstance(browser_executable.get("sha256"), str) and len(browser_executable["sha256"]) == 64
        and isinstance(browser_executable.get("bytes"), int) and browser_executable["bytes"] > 0,
        f"{model} pinned browser executable identity drift",
    )
    _validate_browser_bundle(toolchain.get("browser_bundle") or {}, browser_executable)
    _require(trace.get("outcomes") == assertions, f"{model} trace/artifact outcomes differ")
    _require(trace.get("outcomes_sha256") == outcome_digest(trace["outcomes"]), f"{model} trace outcomes hash drift")

    identity = artifact.get("upstream_identity") or {}
    if model == "600s":
        expected = {"route": "/", "configuration_id": receipt["configuration_id"], "release": receipt["release"], "asset_sha256": receipt["sha256"], "runtime_sha256": receipt["runtime_sha256"]}
    else:
        expected = {"route": "/es1930m/", "configuration_id": receipt["configuration_id"], "release": receipt["release"], "asset_sha256": receipt["files"]["asset"]["sha256"], "runtime_sha256": receipt["runtime"]["sha256"]}
    for key, value in expected.items():
        _require(identity.get(key) == value, f"{model} browser identity drift: {key}")
    for name in ("load_exact_release", "desktop_controls", "mobile_controls", "modal_keyboard", "drag_orbit", "pinch_zoom", "reduced_motion", "fatal_failures", "screenshot_framing"):
        _passed(assertions, name)
    reduced = assertions["reduced_motion"]
    _validate_live_reduced_motion({key: value for key, value in reduced.items() if key != "outcome"}, f"{model} predeploy")
    pinch = assertions["pinch_zoom"]
    before_distance = pinch.get("before_desired_distance_m")
    after_distance = pinch.get("after_desired_distance_m")
    _require(before_distance is not None and after_distance is not None and float(before_distance) != float(after_distance), f"{model} pinch lacks numeric camera-distance proof")
    fatal = (assertions["fatal_failures"].get("cases") or {})
    _validate_fatal_failures(fatal)
    _validate_upstream_screenshot_framing(
        assertions["screenshot_framing"],
        "blender-showcase-v1.1.0" if model == "600s" else "glb",
    )
    _validate_accessibility_tree(
        (artifact.get("observations") or {}).get("accessibility_tree_snapshot") or {},
        EXPECTED_600S_AX_SLIDER_VALUES if model == "600s" else EXPECTED_ES_AX_SLIDER_VALUES,
    )

    if model == "es1930m":
        _passed(assertions, "auto_start_pause_resume")
        maximum = _passed(assertions, "maximum_pose_controls").get("values") or {}
        _require("5.64 metres platform height" in str((maximum.get("#lift-control") or {}).get("ariaValueText")), "ES full-lift engineering proof missing")
        _require("0.55 m extension" in str((maximum.get("#deck-control") or {}).get("ariaValueText")), "ES full-extension engineering proof missing")
        _require("80 mm L cylinder displacement" in str((maximum.get("#steer-control:left") or {}).get("ariaValueText")) and "80 mm R cylinder displacement" in str((maximum.get("#steer-control:right") or {}).get("ariaValueText")), "ES steering extrema engineering proof missing")
        screenshot_names = {Path(record.get("path", "")).name for record in (artifact.get("capture_artifacts") or {}).get("screenshots", [])}
        _require({"es1930m-regression-desktop.png", "es1930m-regression-mobile.png", "es1930m-regression-maximum-pose.png"}.issubset(screenshot_names), "ES required browser screenshots are incomplete")
    evidence = {
        "normalized_artifact_sha256": canonical_digest(normalized_browser_evidence(artifact)),
        "assertions_sha256": canonical_digest(assertions),
        "runner": runner,
        "toolchain": toolchain,
        "automation_trace": trace_record,
        "screenshots": screenshot_records,
    }
    return {
        "artifact": artifact,
        "evidence": evidence,
        "evidence_sha256": canonical_digest(evidence),
        "assertions": assertions,
    }


def validate_review_binding(review: dict, *, receipt: dict, receipt_600s: dict) -> dict:
    _require(review.get("schema_version") == "3.0.0", "ES review binding schema drift")
    binding = review.get("binding") or {}
    es = validate_artifact(ROOT / str(binding.get("es_browser_artifact", "")), receipt=receipt, model="es1930m")
    upstream_600s = validate_artifact(ROOT / str(binding.get("600s_browser_artifact", "")), receipt=receipt_600s, model="600s")
    _require(binding.get("es_browser_evidence") == es["evidence"], "ES immutable browser evidence binding drift")
    _require(binding.get("600s_browser_evidence") == upstream_600s["evidence"], "600S immutable browser evidence binding drift")
    gates = review.get("gates") or {}
    _require(set(gates) == set(PREDEPLOY_GATES) | {"deployed_pages_reviewed"}, "ES review gate set drift")
    for gate in PREDEPLOY_GATES:
        record = gates.get(gate) or {}
        _require(record.get("status") == "pass" and record.get("reviewed_runtime_sha256") == receipt["runtime"]["sha256"] and record.get("reviewed_asset_sha256") == receipt["files"]["asset"]["sha256"], f"ES predeploy gate is not exact: {gate}")
        _require(record.get("browser_evidence_sha256") in {es["evidence_sha256"], upstream_600s["evidence_sha256"]}, f"ES predeploy gate lacks executable browser binding: {gate}")
    deployed = gates.get("deployed_pages_reviewed") or {}
    _require(deployed.get("status") == "pending" and deployed.get("reviewed_runtime_sha256") is None and deployed.get("reviewed_asset_sha256") is None, "Local predeploy binding must not claim deployed Pages review")
    return {"es": es, "600s": upstream_600s, "predeploy_gates": len(PREDEPLOY_GATES)}
