#!/usr/bin/env python3
"""Fail-closed semantic validation for raw 742 browser-review captures.

The module accepts recapture-required templates for pre-commit/static checks, but
only ``validate_complete_browser_artifact`` can satisfy a human review gate.
Typed summaries alone are intentionally insufficient: completed captures bind
raw frame intervals, DOM/accessibility snapshots, exact screenshots, and an
automation trace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
BROWSER_GATES = (
    "desktop_browser_interaction",
    "mobile_browser_interaction",
    "accessibility_semantics_and_keyboard",
    "semantic_selection",
    "performance_profile",
    "600s_browser_regression",
    "es1930m_browser_regression",
)
COMMON_FIELDS = {
    "schema_version", "kind", "gate", "capture_status", "configuration_id",
    "candidate_tree_sha256", "reviewed_source_commit", "environment",
    "capture_runner", "capture_artifacts", "observations", "boundary",
}
EXPECTED_SELECTION_PRIORITY = {
    "chassis": 0,
    "steering": 1,
    "boom": 2,
    "hydraulics": 3,
    "cab": 4,
    "carriage": 5,
}
EXPECTED_SELECTION_FIXTURES = [
    {"case": 1, "basis": "nearest-distance", "expectedVolume": "front", "observedVolume": "front", "pass": True},
    {"case": 2, "basis": "distance-tie", "expectedVolume": "high-tie", "observedVolume": "high-tie", "pass": True},
    {"case": 3, "basis": "nearest-distance", "expectedVolume": "front", "observedVolume": "front", "pass": True},
    {"case": 4, "basis": "visible-surface", "expectedVolume": "front", "observedVolume": "front", "pass": True},
]
EXPECTED_SELECTION_VOLUME = {
    "chassis": "Chassis_Hit", "cab": "Cab_Hit", "boom": "Boom_Hit",
    "carriage": "Carriage_Hit", "steering": "Steering_Hit", "hydraulics": "Hydraulics_Hit",
}
EXPECTED_STOW_SLIDER_VALUES = {
    "Boom lift": "0°",
    "Boom telescope": "0.00 m visual",
    "Carriage tilt": "0°",
    "Steering angle": "Center",
    "Frame level": "Level",
}
CAPTURE_RUNNER_PATH = "scripts/capture_742_browser_evidence.mjs"
EXPECTED_SCREENSHOT_DIMENSIONS = {
    "desktop_browser_interaction": {(1280, 720)},
    "mobile_browser_interaction": {(390, 844), (844, 390)},
    "accessibility_semantics_and_keyboard": {(1280, 720)},
    "semantic_selection": {(1280, 720)},
    "performance_profile": {(1280, 720), (390, 844), (844, 390)},
    "600s_browser_regression": {(1280, 720), (390, 844)},
    "es1930m_browser_regression": {(1280, 720), (390, 844)},
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_capture_runner(record: dict) -> None:
    if set(record or {}) != {"path", "sha256", "bytes"} or record.get("path") != CAPTURE_RUNNER_PATH:
        raise RuntimeError("742 committed capture-runner identity drift")
    runner = ROOT / CAPTURE_RUNNER_PATH
    if not runner.is_file() or digest(runner) != record["sha256"] or runner.stat().st_size != record["bytes"]:
        raise RuntimeError("742 committed capture-runner hash/size binding drift")


def _validate_structured_trace_outcomes(trace: dict, gate: str) -> None:
    outcomes = trace.get("outcomes")
    if not isinstance(outcomes, dict) or len(outcomes) < 3 or any(
        not isinstance(value, dict) or value.get("outcome") != "pass" for value in outcomes.values()
    ):
        raise RuntimeError(f"742 browser automation trace structured outcomes are incomplete: {gate}")
    encoded = json.dumps(outcomes, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != trace.get("outcomes_sha256"):
        raise RuntimeError(f"742 browser automation trace outcome hash drift: {gate}")


def expected_selection_outcomes() -> list[dict]:
    return [dict(item) for item in EXPECTED_SELECTION_FIXTURES]


def _validate_selection_fixtures(observed: list, dom_records: list) -> None:
    if observed != dom_records:
        raise RuntimeError("742 selection fixture observations do not exactly bind the captured DOM dataset")
    if not isinstance(observed, list) or len(observed) != len(EXPECTED_SELECTION_FIXTURES):
        raise RuntimeError("742 raw selection fixture count drift")
    fixture_fields = {
        "case", "hits", "visibleSurfaceComponent", "basis", "expectedComponent",
        "observedComponent", "expectedVolume", "observedVolume", "pass",
    }
    hit_fields = {"volume", "component", "distanceM", "priority"}
    projection = []
    for index, fixture in enumerate(observed, start=1):
        if set(fixture or {}) != fixture_fields or fixture["case"] != index:
            raise RuntimeError("742 raw selection fixture schema/order drift")
        hits = fixture["hits"]
        if not isinstance(hits, list) or len(hits) < 2:
            raise RuntimeError("742 raw selection fixture hit set is incomplete")
        for hit in hits:
            if set(hit or {}) != hit_fields:
                raise RuntimeError("742 raw selection fixture hit schema drift")
            if not all(isinstance(hit[name], str) and hit[name] for name in ("volume", "component")):
                raise RuntimeError("742 raw selection fixture hit identity drift")
            if (
                isinstance(hit["distanceM"], bool)
                or not isinstance(hit["distanceM"], (int, float))
                or not math.isfinite(hit["distanceM"])
                or hit["distanceM"] < 0
                or isinstance(hit["priority"], bool)
                or not isinstance(hit["priority"], int)
                or hit["priority"] < 0
            ):
                raise RuntimeError("742 raw selection fixture hit distance/priority drift")
        surface = fixture["visibleSurfaceComponent"]
        if surface is not None and (not isinstance(surface, str) or not surface):
            raise RuntimeError("742 raw selection fixture visible-surface identity drift")
        surface_hits = [hit for hit in hits if hit["component"] == surface] if surface is not None else []
        if surface is not None and not surface_hits:
            raise RuntimeError("742 raw selection fixture visible surface has no corresponding hit")
        if surface_hits:
            expected = min(surface_hits, key=lambda hit: (hit["distanceM"], hit["volume"]))
            basis = "visible-surface"
        else:
            minimum = min(hit["distanceM"] for hit in hits)
            eligible = [hit for hit in hits if hit["distanceM"] <= minimum + 0.025]
            highest_priority = max(hit["priority"] for hit in eligible)
            winners = [hit for hit in eligible if hit["priority"] == highest_priority]
            expected = min(winners, key=lambda hit: (hit["distanceM"], hit["volume"]))
            basis = "distance-tie" if len(eligible) > 1 else "nearest-distance"
        if (
            fixture["basis"] != basis
            or fixture["expectedComponent"] != expected["component"]
            or fixture["observedComponent"] != expected["component"]
            or fixture["expectedVolume"] != expected["volume"]
            or fixture["observedVolume"] != expected["volume"]
            or fixture["pass"] is not True
        ):
            raise RuntimeError("742 raw selection fixture outcome disagrees with independent recomputation")
        projection.append({
            field: fixture[field]
            for field in ("case", "basis", "expectedVolume", "observedVolume", "pass")
        })
    if projection != expected_selection_outcomes():
        raise RuntimeError("742 raw selection fixture projection disagrees with committed expectations")


def _independent_selection_expected(ray: dict) -> str:
    hits = list(zip(ray["hitComponents"], ray["hitDistancesM"]))
    surface = ray["visibleSurfaceComponent"]
    if surface is not None:
        surface_hits = [hit for hit in hits if hit[0] == surface]
        if surface_hits:
            return min(surface_hits, key=lambda hit: hit[1])[0]
    minimum = min(distance for _, distance in hits)
    eligible = [hit for hit in hits if hit[1] <= minimum + 0.025]
    priority = max(EXPECTED_SELECTION_PRIORITY[component] for component, _ in eligible)
    winners = [hit for hit in eligible if EXPECTED_SELECTION_PRIORITY[hit[0]] == priority]
    return min(winners, key=lambda hit: (hit[1], EXPECTED_SELECTION_VOLUME[hit[0]]))[0]


def _capture_allowlist() -> dict[str, dict]:
    path = ROOT / "docs/review/742/BROWSER_CAPTURE_ALLOWLIST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"schema_version", "kind", "artifacts"}:
        raise RuntimeError("742 browser-capture allowlist schema drift")
    if data["schema_version"] != "1.0.0" or data["kind"] != "742-browser-capture-allowlist":
        raise RuntimeError("742 browser-capture allowlist identity drift")
    result = {}
    fields = {"path", "sha256", "bytes", "kind", "mime_type", "width_px", "height_px", "provenance"}
    for record in data["artifacts"]:
        if set(record) != fields:
            raise RuntimeError("742 browser-capture allowlist record schema drift")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts or not str(relative).startswith("docs/review/742/browser-captures/"):
            raise RuntimeError(f"Unsafe 742 browser-capture path: {relative}")
        if str(relative) in result:
            raise RuntimeError(f"Duplicate 742 browser-capture path: {relative}")
        if record["kind"] == "screenshot":
            if relative.suffix.lower() != ".png" or record["mime_type"] != "image/png":
                raise RuntimeError(f"742 browser screenshot identity drift: {relative}")
            if not all(isinstance(record[name], int) and record[name] > 0 for name in ("width_px", "height_px")):
                raise RuntimeError(f"742 browser screenshot dimensions missing: {relative}")
        elif record["kind"] == "automation_trace":
            if relative.suffix.lower() != ".json" or record["mime_type"] != "application/json" or record["width_px"] is not None or record["height_px"] is not None:
                raise RuntimeError(f"742 automation trace identity drift: {relative}")
        else:
            raise RuntimeError(f"742 browser-capture kind drift: {relative}")
        if not isinstance(record["provenance"], str) or "local browser capture" not in record["provenance"].lower():
            raise RuntimeError(f"742 browser-capture provenance missing: {relative}")
        artifact = ROOT / relative
        if not artifact.is_file() or digest(artifact) != record["sha256"] or artifact.stat().st_size != record["bytes"]:
            raise RuntimeError(f"742 browser-capture artifact drift: {relative}")
        if record["kind"] == "screenshot":
            payload = artifact.read_bytes()
            if payload[:8] != b"\x89PNG\r\n\x1a\n" or len(payload) < 24 or struct.unpack(">II", payload[16:24]) != (record["width_px"], record["height_px"]):
                raise RuntimeError(f"742 browser screenshot PNG structure/dimensions drift: {relative}")
        result[str(relative)] = record
    return result


def _verify_capture_record(record: dict, expected_kind: str, allowlist: dict[str, dict]) -> None:
    expected_fields = {"path", "sha256", "bytes", "width_px", "height_px"}
    if set(record or {}) != expected_fields:
        raise RuntimeError("742 browser-capture artifact record schema drift")
    admitted = allowlist.get(record["path"])
    if not admitted or admitted["kind"] != expected_kind:
        raise RuntimeError(f"742 browser-capture artifact is not allowlisted: {record.get('path')}")
    for field in expected_fields:
        if record[field] != admitted[field]:
            raise RuntimeError(f"742 browser-capture allowlist record mismatch: {record['path']}:{field}")


def _validate_environment(environment: dict) -> None:
    fields = {
        "browser", "os", "gpu", "automation", "captured_at_utc",
        "physical_device_session", "assistive_technology_session",
    }
    if set(environment or {}) != fields:
        raise RuntimeError("742 browser-capture environment schema drift")
    browser = environment["browser"]
    if set(browser or {}) != {"name", "version", "user_agent"}:
        raise RuntimeError("742 browser identity schema drift")
    if not all(isinstance(browser[name], str) and browser[name].strip() for name in browser):
        raise RuntimeError("742 browser identity is incomplete")
    if not re.search(r"\d+(?:\.\d+){2,3}", browser["version"]):
        raise RuntimeError("742 browser version is not exact")
    os_record = environment["os"]
    if set(os_record or {}) != {"name", "version", "build"} or not all(
        isinstance(os_record[name], str) and os_record[name].strip() for name in os_record
    ):
        raise RuntimeError("742 OS identity is incomplete")
    gpu = environment["gpu"]
    if set(gpu or {}) != {"status", "vendor", "renderer", "api", "collection_method", "reason"}:
        raise RuntimeError("742 GPU identity schema drift")
    if gpu["status"] == "observed":
        if not all(isinstance(gpu[name], str) and gpu[name].strip() for name in ("vendor", "renderer", "api", "collection_method")) or gpu["reason"] is not None:
            raise RuntimeError("742 observed GPU metadata is incomplete")
    elif gpu["status"] == "unavailable":
        if gpu["vendor"] is not None or gpu["renderer"] is not None or not isinstance(gpu["reason"], str) or not gpu["reason"].strip():
            raise RuntimeError("742 unavailable GPU metadata lacks an honest reason")
    else:
        raise RuntimeError("742 GPU observation status drift")
    automation = environment["automation"]
    if set(automation or {}) != {"tool", "version"} or not all(
        isinstance(automation[name], str) and automation[name].strip() for name in automation
    ):
        raise RuntimeError("742 browser automation identity is incomplete")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", environment["captured_at_utc"] or ""):
        raise RuntimeError("742 browser capture UTC timestamp is malformed")
    if environment["physical_device_session"] is not False or environment["assistive_technology_session"] is not False:
        raise RuntimeError("742 local browser evidence overstates physical-device or assistive-technology proof")


def _validate_capture_artifacts(
    capture: dict, allowlist: dict[str, dict], minimum_screenshots: int, gate: str, environment: dict, runner: dict
) -> dict:
    if set(capture or {}) != {"screenshots", "automation_trace"}:
        raise RuntimeError("742 browser capture-artifact schema drift")
    screenshots = capture["screenshots"]
    if not isinstance(screenshots, list) or len(screenshots) < minimum_screenshots:
        raise RuntimeError("742 browser gate lacks required screenshots")
    paths = []
    for screenshot in screenshots:
        _verify_capture_record(screenshot, "screenshot", allowlist)
        paths.append(screenshot["path"])
    if len(paths) != len(set(paths)):
        raise RuntimeError("742 browser gate repeats one screenshot as multiple observations")
    observed_dimensions = {(item["width_px"], item["height_px"]) for item in screenshots}
    if observed_dimensions != EXPECTED_SCREENSHOT_DIMENSIONS[gate]:
        raise RuntimeError(f"742 browser screenshots do not bind every exact required viewport: {gate}")
    trace_record = capture["automation_trace"]
    _verify_capture_record(trace_record, "automation_trace", allowlist)
    trace = json.loads((ROOT / trace_record["path"]).read_text(encoding="utf-8"))
    fields = {"schema_version", "kind", "gate", "captured_at_utc", "tool", "tool_version", "runner", "outcomes_sha256", "outcomes"}
    if set(trace or {}) != fields or trace["schema_version"] != "2.0.0" or trace["kind"] != "browser-automation-trace":
        raise RuntimeError(f"742 browser automation trace schema drift: {gate}")
    if trace["gate"] != gate or trace["captured_at_utc"] != environment["captured_at_utc"]:
        raise RuntimeError(f"742 browser automation trace identity/time drift: {gate}")
    if trace["tool"] != environment["automation"]["tool"] or trace["tool_version"] != environment["automation"]["version"]:
        raise RuntimeError(f"742 browser automation trace tool identity drift: {gate}")
    if trace["runner"] != runner:
        raise RuntimeError(f"742 browser automation trace runner binding drift: {gate}")
    _validate_structured_trace_outcomes(trace, gate)
    return trace


def _validate_dom_snapshot(snapshot: dict, expected_viewport: list[int] | None = None) -> None:
    if set(snapshot or {}) != {"viewport_css_px", "url", "nodes"}:
        raise RuntimeError("742 DOM snapshot schema drift")
    if expected_viewport is not None and snapshot["viewport_css_px"] != expected_viewport:
        raise RuntimeError("742 DOM snapshot viewport drift")
    if not re.fullmatch(r"https?://[^\s]+", snapshot["url"] or ""):
        raise RuntimeError("742 DOM snapshot URL is malformed")
    nodes = snapshot["nodes"]
    if not isinstance(nodes, list) or len(nodes) < 3:
        raise RuntimeError("742 DOM snapshot is incomplete")
    selectors = set()
    for node in nodes:
        if set(node or {}) != {"selector", "text", "attributes"} or not isinstance(node["selector"], str):
            raise RuntimeError("742 DOM snapshot node schema drift")
        if not isinstance(node["text"], str) or not isinstance(node["attributes"], dict):
            raise RuntimeError("742 DOM snapshot node value drift")
        selectors.add(node["selector"])
    if "body" not in selectors or "#machine-title" not in selectors or "#diagnostics" not in selectors:
        raise RuntimeError("742 DOM snapshot omits machine identity or diagnostics")


def _snapshot_node(snapshot: dict, selector: str) -> dict:
    for node in snapshot["nodes"]:
        if node["selector"] == selector:
            return node
    raise RuntimeError(f"742 DOM snapshot omits required selector: {selector}")


def _require_loaded_zero_error_snapshot(snapshot: dict) -> None:
    body = _snapshot_node(snapshot, "body")
    diagnostics = _snapshot_node(snapshot, "#diagnostics")
    source = body["attributes"].get("data-machine-source")
    if source not in {"blender-showcase-v1.1.0", "glb", "glb-validated"} or "errors 0" not in diagnostics["text"]:
        raise RuntimeError("742 DOM snapshot does not prove an exact GLB load with zero runtime errors")


def _validate_transcript(transcript: list, required_ids: tuple[str, ...]) -> None:
    if not isinstance(transcript, list) or len(transcript) != len(required_ids):
        raise RuntimeError("742 browser interaction transcript length drift")
    expected_fields = {"sequence", "id", "action", "target", "expected", "observed", "outcome"}
    for index, (step, expected_id) in enumerate(zip(transcript, required_ids), start=1):
        if set(step or {}) != expected_fields or step["sequence"] != index or step["id"] != expected_id:
            raise RuntimeError(f"742 browser transcript step identity drift: {expected_id}")
        if step["outcome"] != "pass" or not all(isinstance(step[name], str) and step[name].strip() for name in ("action", "target", "expected", "observed")):
            raise RuntimeError(f"742 browser transcript step did not pass: {expected_id}")


def _validate_742_pinch_zoom(observed: dict, expected_viewport: list[int]) -> None:
    fields = {
        "schema_version", "gesture", "target_selector", "viewport_css_px", "canvas_rect_css_px",
        "start_points_css_px", "end_points_css_px", "hit_test_targets", "all_points_on_canvas",
        "baseline", "after", "intermediate_desired_distance_m", "final_gesture_desired_distance_m",
        "camera_distance_delta_m", "desired_distance_delta_m", "absolute_camera_distance_delta_m",
        "minimum_required_delta_m", "expected_direction", "actual_direction", "monotonic_camera_change",
        "settled_before", "settled_after", "outcome",
    }
    if set(observed or {}) != fields:
        raise RuntimeError("742 pinch raw-observation schema drift")
    if (
        observed["schema_version"] != "1.0.0"
        or observed["gesture"] != "pinch-out"
        or observed["target_selector"] != "#app canvas"
        or observed["viewport_css_px"] != expected_viewport
        or observed["all_points_on_canvas"] is not True
        or observed["hit_test_targets"] != ["CANVAS"] * 4
        or observed["expected_direction"] != "decrease"
        or observed["actual_direction"] != "decrease"
        or observed["monotonic_camera_change"] is not True
        or observed["settled_before"] is not True
        or observed["settled_after"] is not True
        or observed["outcome"] != "pass"
    ):
        raise RuntimeError("742 pinch identity/direction/settle contract failed")
    rect = observed["canvas_rect_css_px"]
    if set(rect or {}) != {"x", "y", "width", "height"} or any(
        isinstance(rect[name], bool) or not isinstance(rect[name], (int, float)) or not math.isfinite(rect[name])
        for name in rect
    ) or rect["width"] < 180 or rect["height"] < 180:
        raise RuntimeError("742 pinch canvas rectangle is malformed")
    points = [*observed["start_points_css_px"], *observed["end_points_css_px"]]
    if len(observed["start_points_css_px"]) != 2 or len(observed["end_points_css_px"]) != 2 or any(
        not isinstance(point, list) or len(point) != 2 or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in point
        ) for point in points
    ):
        raise RuntimeError("742 pinch touch coordinates are malformed")
    if any(
        not (rect["x"] <= point[0] <= rect["x"] + rect["width"] and rect["y"] <= point[1] <= rect["y"] + rect["height"])
        for point in points
    ):
        raise RuntimeError("742 pinch touch coordinate is outside the canvas")
    start_span = abs(observed["start_points_css_px"][1][0] - observed["start_points_css_px"][0][0])
    end_span = abs(observed["end_points_css_px"][1][0] - observed["end_points_css_px"][0][0])
    if end_span <= start_span + 40:
        raise RuntimeError("742 pinch-out contact separation did not materially increase")
    settle_fields = {"camera_distance_m", "desired_distance_m", "stable_frames", "samples_camera_distance_m"}
    for label in ("baseline", "after"):
        record = observed[label]
        if set(record or {}) != settle_fields or not isinstance(record["stable_frames"], int) or record["stable_frames"] < 6:
            raise RuntimeError(f"742 pinch {label} settle record drift")
        samples = record["samples_camera_distance_m"]
        if not isinstance(samples, list) or len(samples) < record["stable_frames"] or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0 for value in samples
        ):
            raise RuntimeError(f"742 pinch {label} camera samples are malformed")
        if not math.isclose(record["camera_distance_m"], record["desired_distance_m"], rel_tol=0, abs_tol=0.03):
            raise RuntimeError(f"742 pinch {label} camera did not settle to desired distance")
    baseline, after = observed["baseline"], observed["after"]
    camera_delta = round(after["camera_distance_m"] - baseline["camera_distance_m"], 3)
    desired_delta = round(after["desired_distance_m"] - baseline["desired_distance_m"], 3)
    required = observed["minimum_required_delta_m"]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (
        camera_delta, desired_delta, required, observed["intermediate_desired_distance_m"], observed["final_gesture_desired_distance_m"]
    )) or required < 0.5:
        raise RuntimeError("742 pinch distance values are malformed")
    if (
        not math.isclose(observed["camera_distance_delta_m"], camera_delta, rel_tol=0, abs_tol=0.001)
        or not math.isclose(observed["desired_distance_delta_m"], desired_delta, rel_tol=0, abs_tol=0.001)
        or not math.isclose(observed["absolute_camera_distance_delta_m"], abs(camera_delta), rel_tol=0, abs_tol=0.001)
        or camera_delta > -required
        or desired_delta > -required
        or observed["intermediate_desired_distance_m"] >= baseline["desired_distance_m"]
        or observed["final_gesture_desired_distance_m"] > observed["intermediate_desired_distance_m"]
    ):
        raise RuntimeError("742 pinch did not prove a meaningful zoom-in distance change")
    samples = after["samples_camera_distance_m"]
    if any(sample > samples[index - 1] + 0.011 for index, sample in enumerate(samples) if index):
        raise RuntimeError("742 pinch camera trajectory is not monotonic toward zoom-in")


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


def _validate_frame_capture(capture: dict, expected_viewport: list[int]) -> None:
    if set(capture or {}) != {"viewport_css_px", "samples_ms", "summary", "background_samples_excluded"}:
        raise RuntimeError("742 raw frame-capture schema drift")
    if capture["viewport_css_px"] != expected_viewport or capture["background_samples_excluded"] is not True:
        raise RuntimeError("742 raw frame-capture viewport/background boundary drift")
    samples = capture["samples_ms"]
    if not isinstance(samples, list) or len(samples) < 180 or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value < 1000 for value in samples
    ):
        raise RuntimeError("742 raw frame samples are incomplete or malformed")
    summary = capture["summary"]
    expected_fields = {"sample_count", "p95_ms", "worst_ms", "visible_stall_count_gte_250ms"}
    if set(summary or {}) != expected_fields:
        raise RuntimeError("742 frame summary schema drift")
    recomputed = {
        "sample_count": len(samples),
        "p95_ms": round(_p95(samples), 3),
        "worst_ms": round(max(samples), 3),
        "visible_stall_count_gte_250ms": sum(value >= 250 for value in samples),
    }
    if summary != recomputed:
        raise RuntimeError("742 frame summary is not derivable from the raw samples")
    if summary["p95_ms"] > 50 or summary["visible_stall_count_gte_250ms"] != 0:
        raise RuntimeError("742 local browser performance threshold did not pass")


def _validate_accessibility_tree(snapshot: dict, slider_names: set[str]) -> None:
    if set(snapshot or {}) != {"source", "states"} or snapshot["source"] != "Chromium CDP Accessibility.getFullAXTree":
        raise RuntimeError("742 accessibility-tree snapshot schema drift")
    states = snapshot["states"]
    if not isinstance(states, list) or [record.get("state") for record in states] != ["controls_open", "modal_open"]:
        raise RuntimeError("742 accessibility-tree state set drift")
    state_nodes = {}
    for record in states:
        if set(record or {}) != {"state", "nodes"} or not isinstance(record["nodes"], list) or not record["nodes"]:
            raise RuntimeError("742 accessibility-tree state snapshot is empty")
        state_nodes[record["state"]] = record["nodes"]
    observed_sliders = []
    roles_by_state = {}
    for state, nodes in state_nodes.items():
        roles = set()
        for node in nodes:
            if set(node or {}) != {"role", "name", "value", "states"} or not isinstance(node["states"], dict):
                raise RuntimeError("742 accessibility-tree node schema drift")
            roles.add(node["role"])
            if state == "controls_open" and node["role"] == "slider":
                observed_sliders.append(node["name"])
                value = node["value"]
                value_text = node["states"].get("valuetext")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not isinstance(value_text, str)
                    or not re.fullmatch(r"-?(?:\d+(?:\.\d+)?|\.\d+)", value_text)
                    or not math.isclose(float(value_text), float(value), rel_tol=0, abs_tol=1e-9)
                ):
                    raise RuntimeError(f"742 accessibility-tree slider native numeric value drift: {node['name']}")
                if (
                    node["states"].get("focusable") is not True
                    or node["states"].get("settable") is not True
                    or node["states"].get("disabled") not in {None, False}
                ):
                    raise RuntimeError(f"742 accessibility-tree slider enabled/focusable/settable state drift: {node['name']}")
        roles_by_state[state] = roles
    if (
        not {"application", "button"}.issubset(roles_by_state["controls_open"])
        or not {"dialog", "button"}.issubset(roles_by_state["modal_open"])
        or len(observed_sliders) != len(slider_names)
        or set(observed_sliders) != slider_names
    ):
        raise RuntimeError("742 accessibility-tree snapshot omits required semantics")


def _validate_regression(gate: str, observations: dict) -> None:
    fields = {"page", "dom_snapshots", "accessibility_tree_snapshot", "assertions", "reduced_motion"}
    if set(observations or {}) != fields:
        raise RuntimeError(f"742 upstream regression observation schema drift: {gate}")
    page = observations["page"]
    if set(page or {}) != {"route", "title", "status_text", "parsed_status"}:
        raise RuntimeError(f"742 upstream regression page schema drift: {gate}")
    snapshots = observations["dom_snapshots"]
    if set(snapshots or {}) != {"desktop", "mobile", "modal_open"}:
        raise RuntimeError(f"742 upstream regression responsive snapshot set drift: {gate}")
    _validate_dom_snapshot(snapshots["desktop"], [1280, 720])
    _validate_dom_snapshot(snapshots["mobile"], [390, 844])
    _validate_dom_snapshot(snapshots["modal_open"], [1280, 720])
    for name in ("desktop", "mobile", "modal_open"):
        _require_loaded_zero_error_snapshot(snapshots[name])
    for name in ("desktop", "mobile"):
        toggle = _snapshot_node(snapshots[name], "#controls-toggle")
        if toggle["attributes"].get("aria-expanded") != "true":
            raise RuntimeError(f"742 upstream regression controls were not expanded: {gate}:{name}")
    modal = _snapshot_node(snapshots["modal_open"], "#inspector")
    modal_body = _snapshot_node(snapshots["modal_open"], "body")
    if "inert" in modal["attributes"] or "inspector-open" not in modal_body["attributes"].get("class", ""):
        raise RuntimeError(f"742 upstream regression modal-open DOM state drift: {gate}")
    reduced = observations["reduced_motion"]
    if set(reduced or {}) != {"query", "body_dataset", "autonomy_disabled", "manual_controls_enabled"}:
        raise RuntimeError(f"742 upstream regression reduced-motion schema drift: {gate}")
    if reduced["query"] != "reduce=1" or reduced["body_dataset"] != "true" or reduced["autonomy_disabled"] is not True or reduced["manual_controls_enabled"] is not True:
        raise RuntimeError(f"742 upstream regression reduced-motion contract failed: {gate}")
    if gate == "600s_browser_regression":
        if page["route"] != "/" or page["title"] != "600S Interactive Equipment Study":
            raise RuntimeError("742 600S regression route/title drift")
        required = {"load_exact_release", "desktop_controls", "mobile_controls", "modal_keyboard", "drag_orbit", "pinch_zoom", "reduced_motion"}
        slider_names = {"Boom lift", "Extend", "Rotate", "Steering"}
        parsed = page["parsed_status"]
        fields = {"source", "meshes", "selection", "errors", "load_ms", "render_profile", "fps", "p95_ms", "reduced_motion"}
        if set(parsed or {}) != fields or any((
            parsed["source"] != "blender-showcase-v1.1.0", parsed["meshes"] != 92,
            parsed["selection"] != "5/5 pass", parsed["errors"] != 0,
            parsed["render_profile"] != "desktop", parsed["reduced_motion"] != "off",
            not isinstance(parsed["load_ms"], (int, float)) or parsed["load_ms"] < 0,
            not isinstance(parsed["fps"], (int, float)) or parsed["fps"] <= 0,
            not isinstance(parsed["p95_ms"], (int, float)) or not 0 < parsed["p95_ms"] <= 50,
        )) or "selection 5/5 pass" not in page["status_text"] or "errors 0" not in page["status_text"]:
            raise RuntimeError("742 600S regression status dataset did not pass")
    else:
        if page["route"] != "/es1930m/" or page["title"] != "ES1930M Interactive Equipment Study":
            raise RuntimeError("742 ES1930M regression route/title drift")
        required = {"load_exact_release", "desktop_controls", "mobile_controls", "modal_keyboard", "drag_orbit", "pinch_zoom", "auto_start_pause_resume", "reduced_motion"}
        slider_names = {"Platform lift", "Extension deck", "Steering actuator; wheel angles deferred"}
        parsed = page["parsed_status"]
        fields = {"machine", "configuration_id", "source", "selection", "errors", "load_ms", "fps", "p95_ms"}
        if set(parsed or {}) != fields or any((
            parsed["machine"] != "es1930m",
            parsed["configuration_id"] != "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
            parsed["source"] != "glb", parsed["selection"] != "self-test-pass", parsed["errors"] != 0,
            not isinstance(parsed["load_ms"], (int, float)) or parsed["load_ms"] < 0,
            not isinstance(parsed["fps"], (int, float)) or parsed["fps"] <= 0,
            not isinstance(parsed["p95_ms"], (int, float)) or not 0 < parsed["p95_ms"] <= 50,
        )) or "selection self-test-pass" not in page["status_text"] or "errors 0" not in page["status_text"]:
            raise RuntimeError("742 ES1930M regression status dataset did not pass")
    if set(observations["assertions"] or {}) != required:
        raise RuntimeError(f"742 upstream regression structured outcome set drift: {gate}")
    pinch = observations["assertions"]["pinch_zoom"]
    if pinch.get("hit_test_targets") != ["CANVAS"] * 4 or pinch.get("observable_render_or_distance_change") is not True or pinch.get("before_canvas_sha256") == pinch.get("after_canvas_sha256"):
        raise RuntimeError(f"742 upstream regression pinch outcome is not independently observable: {gate}")
    _validate_accessibility_tree(observations["accessibility_tree_snapshot"], slider_names)


def validate_complete_browser_artifact(
    path: Path,
    gate: str,
    candidate_tree_sha256: str,
    reviewed_commit: str,
    expected_upstream_identity: dict | None = None,
) -> dict:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected_fields = COMMON_FIELDS | ({"upstream_identity"} if expected_upstream_identity is not None else set())
    if set(artifact) != expected_fields or artifact.get("schema_version") != "2.0.0":
        raise RuntimeError(f"742 browser evidence schema drift: {gate}")
    expected_kind = "742-upstream-regression-capture" if expected_upstream_identity is not None else "742-browser-gate-capture"
    if artifact.get("kind") != expected_kind or artifact.get("gate") != gate or artifact.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError(f"742 browser evidence identity drift: {gate}")
    if artifact.get("capture_status") != "complete":
        raise RuntimeError(f"742 browser evidence still requires recapture: {gate}")
    if artifact.get("candidate_tree_sha256") != candidate_tree_sha256 or artifact.get("reviewed_source_commit") != reviewed_commit:
        raise RuntimeError(f"742 browser evidence candidate binding drift: {gate}")
    if expected_upstream_identity is not None and artifact.get("upstream_identity") != expected_upstream_identity:
        raise RuntimeError(f"742 upstream regression exact-release binding drift: {gate}")
    if not isinstance(artifact.get("boundary"), str) or not artifact["boundary"].strip():
        raise RuntimeError(f"742 browser evidence boundary missing: {gate}")
    _validate_capture_runner(artifact["capture_runner"])
    _validate_environment(artifact["environment"])
    allowlist = _capture_allowlist()
    minimum_screenshots = 3 if gate == "performance_profile" else 2 if "regression" in gate or gate == "mobile_browser_interaction" else 1
    trace = _validate_capture_artifacts(
        artifact["capture_artifacts"], allowlist, minimum_screenshots,
        gate, artifact["environment"], artifact["capture_runner"],
    )
    observations = artifact["observations"]
    assertions = observations.get("assertions") if isinstance(observations, dict) else None
    if not isinstance(assertions, dict) or assertions != trace["outcomes"]:
        raise RuntimeError(f"742 structured browser outcomes do not exactly cross-bind trace and gate artifact: {gate}")
    if gate in {"600s_browser_regression", "es1930m_browser_regression"}:
        _validate_regression(gate, observations)
    elif gate == "performance_profile":
        if set(observations or {}) != {"desktop", "portrait", "short_landscape", "assertions", "physical_low_end_mobile_gpu_claimed"} or observations["physical_low_end_mobile_gpu_claimed"] is not False:
            raise RuntimeError("742 performance raw-capture schema/boundary drift")
        _validate_frame_capture(observations["desktop"], [1280, 720])
        _validate_frame_capture(observations["portrait"], [390, 844])
        _validate_frame_capture(observations["short_landscape"], [844, 390])
        if set(assertions) != {"desktop", "portrait", "short_landscape"} or any(assertions[name].get("summary") != observations[name]["summary"] for name in assertions):
            raise RuntimeError("742 performance structured summaries do not bind raw frame captures")
    elif gate == "semantic_selection":
        fields = {"dom_snapshot", "raw_overlap_rays", "raw_fixture_outcomes", "assertions"}
        if set(observations or {}) != fields:
            raise RuntimeError("742 semantic-selection evidence schema drift")
        _validate_dom_snapshot(observations["dom_snapshot"], [1280, 720])
        _require_loaded_zero_error_snapshot(observations["dom_snapshot"])
        body = _snapshot_node(observations["dom_snapshot"], "body")
        if (
            body["attributes"].get("data-selection-selftest") != "pass"
            or body["attributes"].get("data-selection-overlap-rays") != "15"
            or body["attributes"].get("data-selection-nearest-rays") != "15"
            or body["attributes"].get("data-selection-fixture-cases") != "4/4"
            or body["attributes"].get("data-selection-policy") != "frontmost-rendered-component-then-nearest-proxy-0.025m-semantic-tie"
        ):
            raise RuntimeError("742 semantic-selection raw DOM self-test fields drift")
        observed_fixtures = observations["raw_fixture_outcomes"]
        rays = observations["raw_overlap_rays"]
        if not isinstance(rays, list) or len(rays) != 15:
            raise RuntimeError("742 raw selection overlap-ray count drift")
        ray_fields = {
            "ray", "pairComponents", "hitComponents", "hitDistancesM", "visibleSurfaceComponent",
            "expectedComponent", "resolvedComponent", "expectedVolume", "resolvedVolume", "basis", "pass",
        }
        for index, ray in enumerate(rays, start=1):
            if set(ray or {}) != ray_fields or ray["ray"] != index or ray["basis"] not in {"visible-surface", "distance-tie", "nearest-distance"}:
                raise RuntimeError("742 raw selection ray schema/policy drift")
            hits, distances = ray["hitComponents"], ray["hitDistancesM"]
            if not isinstance(hits, list) or not isinstance(distances, list) or len(hits) < 2 or len(hits) != len(distances):
                raise RuntimeError("742 raw selection ray hit set is incomplete")
            if len(set(hits)) != len(hits) or any(component not in EXPECTED_SELECTION_PRIORITY for component in hits) or any(
                not isinstance(distance, (int, float)) or distance < 0 for distance in distances
            ) or not isinstance(ray["pairComponents"], list) or len(ray["pairComponents"]) != 2 or any(
                component not in EXPECTED_SELECTION_PRIORITY for component in ray["pairComponents"]
            ) or not set(ray["pairComponents"]).issubset(hits) or ray["visibleSurfaceComponent"] not in {None, *EXPECTED_SELECTION_PRIORITY}:
                raise RuntimeError("742 raw selection ray hit identity/distance drift")
            expected = _independent_selection_expected(ray)
            minimum = min(distances)
            eligible = [distance for distance in distances if distance <= minimum + 0.025]
            expected_basis = "visible-surface" if ray["visibleSurfaceComponent"] in hits else "distance-tie" if len(eligible) > 1 else "nearest-distance"
            if (
                ray["expectedComponent"] != expected or ray["resolvedComponent"] != expected
                or ray["expectedVolume"] != EXPECTED_SELECTION_VOLUME[expected]
                or ray["resolvedVolume"] != EXPECTED_SELECTION_VOLUME[expected]
                or ray["basis"] != expected_basis
                or ray["pass"] is not True
            ):
                raise RuntimeError("742 selection resolution disagrees with independently recomputed outcome")
        try:
            dom_rays = json.loads(body["attributes"]["data-selection-overlap-outcomes"])
            dom_fixtures = json.loads(body["attributes"]["data-selection-fixture-outcomes"])
        except (KeyError, json.JSONDecodeError) as error:
            raise RuntimeError("742 semantic-selection DOM lacks parseable raw outcomes") from error
        if dom_rays != rays:
            raise RuntimeError("742 semantic-selection ray observations do not match the captured DOM dataset")
        _validate_selection_fixtures(observed_fixtures, dom_fixtures)
        if set(assertions) != {"visible_canvas_selection", "clear_selection", "pinch_suppression", "overlap_self_test"}:
            raise RuntimeError("742 semantic-selection structured outcome set drift")
        probes = assertions["visible_canvas_selection"].get("independently_labeled_probes")
        expected_probes = {
            "boom-upper-visible-surface": "boom", "cab-front-visible-surface": "cab",
            "chassis-center-visible-surface": "chassis", "steering-front-wheel-visible-surface": "steering",
        }
        if not isinstance(probes, list) or len(probes) != len(expected_probes):
            raise RuntimeError("742 semantic visible-canvas probe count drift")
        for probe in probes:
            if (
                probe.get("outcome") != "pass" or expected_probes.get(probe.get("id")) != probe.get("expected_component")
                or probe.get("hit_test_target") != "CANVAS" or probe.get("selected_component") != probe.get("expected_component")
                or probe.get("rendered_surface_component") != probe.get("expected_component")
                or probe.get("resolution_basis") != "visible-surface" or not probe.get("rendered_surface_mesh")
                or not all(isinstance(probe.get(axis), int) for axis in ("x", "y"))
            ):
                raise RuntimeError("742 semantic visible-canvas frontmost-surface outcome failed")
        if assertions["clear_selection"].get("selected_component_after_reset") is not None:
            raise RuntimeError("742 semantic Reset View did not clear selection")
        _validate_742_pinch_zoom(assertions["pinch_suppression"].get("pinch_zoom"), [1280, 720])
    elif gate == "accessibility_semantics_and_keyboard":
        fields = {"dom_snapshot", "accessibility_tree_snapshot", "assertions", "physical_screen_reader_session_claimed"}
        if set(observations or {}) != fields or observations["physical_screen_reader_session_claimed"] is not False:
            raise RuntimeError("742 accessibility evidence schema/boundary drift")
        _validate_dom_snapshot(observations["dom_snapshot"], [1280, 720])
        _require_loaded_zero_error_snapshot(observations["dom_snapshot"])
        _validate_accessibility_tree(observations["accessibility_tree_snapshot"], set(EXPECTED_STOW_SLIDER_VALUES))
        for selector, expected in {
            "#lift-control": "0°", "#telescope-control": "0.00 m visual", "#tilt-control": "0°",
            "#steer-control": "Center", "#level-control": "Level",
        }.items():
            if _snapshot_node(observations["dom_snapshot"], selector)["attributes"].get("aria-valuetext") != expected:
                raise RuntimeError(f"742 accessibility DOM slider value text drift: {selector}")
        if set(assertions) != {"application_instructions", "slider_value_text", "dialog_focus_trap", "escape_restore", "reduced_motion"}:
            raise RuntimeError("742 accessibility structured outcome set drift")
    elif gate == "desktop_browser_interaction":
        if set(observations or {}) != {"dom_snapshots", "assertions"} or set(observations["dom_snapshots"] or {}) != {"stowed", "maximum_pose", "modal_open"}:
            raise RuntimeError("742 desktop browser evidence schema drift")
        for snapshot in observations["dom_snapshots"].values():
            _validate_dom_snapshot(snapshot, [1280, 720])
            _require_loaded_zero_error_snapshot(snapshot)
        if set(assertions) != {"load_stowed", "manual_controls", "steering_modes", "maximum_pose_reset", "component_modal", "stalled_load_timeout"}:
            raise RuntimeError("742 desktop structured outcome set drift")
        reset = assertions["maximum_pose_reset"]
        before, after = reset.get("before_reset", {}), reset.get("after_reset", {})
        if (
            reset.get("reset_pressed_while_pose") != "maximum" or before.get("slider_values") != after.get("slider_values")
            or not isinstance(after.get("desired_distance_m"), (int, float))
            or not isinstance(after.get("camera_distance_m"), (int, float))
            or not isinstance(after.get("effective_max_distance_m"), (int, float))
            or after["desired_distance_m"] > after["effective_max_distance_m"]
            or abs(after["camera_distance_m"] - after["desired_distance_m"]) > 0.03
            or after.get("selected_component") is not None
        ):
            raise RuntimeError("742 maximum-pose Reset View distance/limit proof failed")
        timeout = assertions["stalled_load_timeout"]
        if any((timeout.get("source") != "load-timeout", timeout.get("viewer_terminal") is not True, timeout.get("error_role") != "alert", timeout.get("error_aria_live") != "assertive", timeout.get("error_visible") is not True, timeout.get("error_focused") is not True, timeout.get("app_inert") is not True, timeout.get("interface_inert") is not True, timeout.get("disabled_control_count") != timeout.get("total_control_count"))):
            raise RuntimeError("742 stalled-load accessible terminal proof failed")
    elif gate == "mobile_browser_interaction":
        if set(observations or {}) != {"dom_snapshots", "assertions"} or set(observations["dom_snapshots"] or {}) != {"portrait", "short_landscape"}:
            raise RuntimeError("742 mobile browser evidence schema drift")
        _validate_dom_snapshot(observations["dom_snapshots"]["portrait"], [390, 844])
        _validate_dom_snapshot(observations["dom_snapshots"]["short_landscape"], [844, 390])
        _require_loaded_zero_error_snapshot(observations["dom_snapshots"]["portrait"])
        _require_loaded_zero_error_snapshot(observations["dom_snapshots"]["short_landscape"])
        if set(assertions) != {"portrait_controls", "short_landscape_controls", "pinch_zoom", "reduced_motion"}:
            raise RuntimeError("742 mobile structured outcome set drift")
        _validate_742_pinch_zoom(assertions["pinch_zoom"], [390, 844])
    else:
        raise RuntimeError(f"Unsupported 742 browser gate: {gate}")
    return artifact["environment"]


def validate_pending_template(path: Path, expected_gate: str) -> None:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    expected_kind = "742-upstream-regression-capture" if "regression" in expected_gate else "742-browser-gate-capture"
    expected_fields = COMMON_FIELDS | ({"upstream_identity"} if "regression" in expected_gate else set())
    if set(artifact) != expected_fields or artifact.get("schema_version") != "2.0.0" or artifact.get("kind") != expected_kind:
        raise RuntimeError(f"742 pending browser template schema drift: {expected_gate}")
    if artifact.get("gate") != expected_gate or artifact.get("configuration_id") != EXPECTED_ID or artifact.get("capture_status") != "recapture-required":
        raise RuntimeError(f"742 pending browser template identity drift: {expected_gate}")
    if artifact.get("candidate_tree_sha256") != "PENDING" or artifact.get("reviewed_source_commit") != "PENDING":
        raise RuntimeError(f"742 pending browser template is already bound: {expected_gate}")
    if artifact.get("environment") is not None or artifact.get("capture_artifacts") != {"screenshots": [], "automation_trace": None} or artifact.get("observations") != {}:
        raise RuntimeError(f"742 pending browser template contains unsupported observations: {expected_gate}")
    if "regression" in expected_gate and artifact.get("upstream_identity") != "REFRESH_FROM_CURRENT_RECEIPT_AT_CAPTURE":
        raise RuntimeError(f"742 pending upstream identity placeholder drift: {expected_gate}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or [ROOT / f"docs/review/742/{gate.replace('_', '-')}.json" for gate in BROWSER_GATES]
    if not args.allow_pending:
        raise RuntimeError("Use validate_742_review.py for completed and commit-bound browser evidence")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_pending_template(path, data.get("gate", ""))
    print(json.dumps({"status": "PASS", "pending_templates": len(paths)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
