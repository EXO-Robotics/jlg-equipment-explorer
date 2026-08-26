#!/usr/bin/env python3
"""Validate exact, executable upstream browser evidence before ES predeploy binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


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
    trace_record = (artifact.get("capture_artifacts") or {}).get("automation_trace") or {}
    trace_path = _validate_record(trace_record, f"{model} raw automation trace")
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assertions = (artifact.get("observations") or {}).get("assertions") or {}
    _require(trace.get("schema_version") == "2.0.0" and trace.get("gate") == gate, f"{model} trace identity drift")
    _require(trace.get("runner") == runner, f"{model} trace runner drift")
    _require(trace.get("outcomes") == assertions, f"{model} trace/artifact outcomes differ")
    _require(trace.get("outcomes_sha256") == outcome_digest(assertions), f"{model} trace outcomes hash drift")

    identity = artifact.get("upstream_identity") or {}
    if model == "600s":
        expected = {"route": "/", "configuration_id": receipt["configuration_id"], "release": receipt["release"], "asset_sha256": receipt["sha256"], "runtime_sha256": receipt["runtime_sha256"]}
    else:
        expected = {"route": "/es1930m/", "configuration_id": receipt["configuration_id"], "release": receipt["release"], "asset_sha256": receipt["files"]["asset"]["sha256"], "runtime_sha256": receipt["runtime"]["sha256"]}
    for key, value in expected.items():
        _require(identity.get(key) == value, f"{model} browser identity drift: {key}")

    for name in ("load_exact_release", "desktop_controls", "mobile_controls", "modal_keyboard", "drag_orbit", "pinch_zoom", "reduced_motion", "fatal_failures"):
        _passed(assertions, name)
    reduced = assertions["reduced_motion"]
    samples = reduced.get("raw_samples") or {}
    moving_start, before_reduce = samples.get("moving_start") or {}, samples.get("before_reduce") or {}
    reduced_start, reduced_end, relaxed = samples.get("reduced_start") or {}, samples.get("reduced_end") or {}, samples.get("relaxed") or {}
    recomputed_moving = moving_start.get("x") != before_reduce.get("x") or moving_start.get("z") != before_reduce.get("z")
    recomputed_frozen = reduced_start.get("x") == reduced_end.get("x") and reduced_start.get("z") == reduced_end.get("z")
    recomputed_no_resume = relaxed.get("autonomyPressed") == "false" and reduced_end.get("x") == relaxed.get("x") and reduced_end.get("z") == relaxed.get("z")
    _require(reduced.get("transition") == "no-preference->reduce->no-preference" and reduced.get("moving_before") is True and reduced.get("frozen_while_reduced") is True and reduced.get("did_not_auto_resume") is True and reduced.get("manual_controls_enabled") is True, f"{model} live reduced-motion proof is incomplete")
    _require(recomputed_moving and recomputed_frozen and recomputed_no_resume, f"{model} raw reduced-motion samples do not independently prove stop/no-resume")
    pinch = assertions["pinch_zoom"]
    before_distance = pinch.get("before_desired_distance_m")
    after_distance = pinch.get("after_desired_distance_m")
    _require(before_distance is not None and after_distance is not None and float(before_distance) != float(after_distance), f"{model} pinch lacks numeric camera-distance proof")
    fatal = (assertions["fatal_failures"].get("cases") or {})
    _require(set(fatal) == {"module", "webgl", "network", "contract"}, f"{model} fatal fault case set is incomplete")
    for fault, expected_source in {"module": "module-load-failed", "webgl": "webgl-unavailable", "network": "load-failed", "contract": "contract-failed"}.items():
        case = fatal[fault]
        terminal = case.get("terminal_first") or {}
        terminal_after = case.get("terminal_after_250ms") or {}
        _require(case.get("outcome") == "pass" and case.get("expected_source") == expected_source and case.get("animation_state_stable_250ms") is True, f"{model} {fault} fatal assertion failed")
        _require(terminal.get("viewer_terminal") is True and terminal.get("error_role") == "alert" and terminal.get("error_aria_live") == "assertive" and terminal.get("error_visible") is True and terminal.get("error_focused") is True and terminal.get("app_inert") is True and terminal.get("interface_inert") is True and terminal.get("disabled_control_count") == terminal.get("total_control_count") and terminal.get("total_control_count", 0) > 0, f"{model} {fault} terminal accessibility contract failed")
        _require(terminal_after.get("drive_x") == terminal.get("drive_x") and terminal_after.get("drive_z") == terminal.get("drive_z") and terminal_after.get("viewer_terminal") is True, f"{model} {fault} terminal animation state did not remain stable")

    if model == "es1930m":
        _passed(assertions, "auto_start_pause_resume")
        maximum = _passed(assertions, "maximum_pose_controls").get("values") or {}
        _require("5.64 metres platform height" in str((maximum.get("#lift-control") or {}).get("ariaValueText")), "ES full-lift engineering proof missing")
        _require("0.55 m extension" in str((maximum.get("#deck-control") or {}).get("ariaValueText")), "ES full-extension engineering proof missing")
        _require("80 mm L cylinder displacement" in str((maximum.get("#steer-control:left") or {}).get("ariaValueText")) and "80 mm R cylinder displacement" in str((maximum.get("#steer-control:right") or {}).get("ariaValueText")), "ES steering extrema engineering proof missing")
        screenshot_names = {Path(record.get("path", "")).name for record in (artifact.get("capture_artifacts") or {}).get("screenshots", [])}
        _require({"es1930m-regression-desktop.png", "es1930m-regression-mobile.png", "es1930m-regression-maximum-pose.png"}.issubset(screenshot_names), "ES required browser screenshots are incomplete")
    return {"artifact": artifact, "artifact_sha256": digest(path), "trace_sha256": digest(trace_path), "runner_sha256": runner["sha256"], "assertions": assertions}


def validate_review_binding(review: dict, *, receipt: dict, receipt_600s: dict) -> dict:
    _require(review.get("schema_version") == "2.0.0", "ES review binding schema drift")
    binding = review.get("binding") or {}
    es = validate_artifact(ROOT / str(binding.get("es_browser_artifact", "")), receipt=receipt, model="es1930m")
    upstream_600s = validate_artifact(ROOT / str(binding.get("600s_browser_artifact", "")), receipt=receipt_600s, model="600s")
    _require(binding.get("es_browser_artifact_sha256") == es["artifact_sha256"], "ES review artifact binding hash drift")
    _require(binding.get("600s_browser_artifact_sha256") == upstream_600s["artifact_sha256"], "600S regression artifact binding hash drift")
    gates = review.get("gates") or {}
    _require(set(gates) == set(PREDEPLOY_GATES) | {"deployed_pages_reviewed"}, "ES review gate set drift")
    for gate in PREDEPLOY_GATES:
        record = gates.get(gate) or {}
        _require(record.get("status") == "pass" and record.get("reviewed_runtime_sha256") == receipt["runtime"]["sha256"] and record.get("reviewed_asset_sha256") == receipt["files"]["asset"]["sha256"], f"ES predeploy gate is not exact: {gate}")
        _require(record.get("browser_artifact_sha256") in {es["artifact_sha256"], upstream_600s["artifact_sha256"]}, f"ES predeploy gate lacks executable browser binding: {gate}")
    deployed = gates.get("deployed_pages_reviewed") or {}
    _require(deployed.get("status") == "pending" and deployed.get("reviewed_runtime_sha256") is None and deployed.get("reviewed_asset_sha256") is None, "Local predeploy binding must not claim deployed Pages review")
    return {"es": es, "600s": upstream_600s, "predeploy_gates": len(PREDEPLOY_GATES)}
