#!/usr/bin/env python3
"""Focused positive/negative tests for the 742 raw browser-evidence parser."""

from __future__ import annotations

import hashlib
import json

from validate_742_browser_evidence import (
    CAPTURE_RUNNER_PATH,
    EXPECTED_PLAYWRIGHT_VERSION,
    EXPECTED_SCREENSHOT_DIMENSIONS,
    _validate_accessibility_tree,
    _independent_selection_expected,
    _validate_environment,
    _validate_fatal_failures,
    _validate_live_reduced_motion,
    _validate_capture_runner,
    _validate_structured_trace_outcomes,
    _validate_frame_capture,
    _validate_742_pinch_zoom,
    _validate_selection_fixtures,
    expected_selection_outcomes,
)
from bind_742_review import _candidate_canonical_paths
from validate_742_receipt import (
    BROWSER_CAPTURE_ALLOWLIST_PATH,
    CANONICAL_FILES,
    ROOT,
    verify_browser_capture_allowlist_binding,
)


NEGATIVE_CASES = 0


def expect_failure(callable_value, message: str) -> None:
    global NEGATIVE_CASES
    try:
        callable_value()
    except RuntimeError:
        NEGATIVE_CASES += 1
        return
    raise RuntimeError(message)


def main() -> None:
    samples = [16.667] * 180
    frame = {
        "viewport_css_px": [1280, 720],
        "samples_ms": samples,
        "summary": {
            "sample_count": 180,
            "p95_ms": 16.667,
            "worst_ms": 16.667,
            "visible_stall_count_gte_250ms": 0,
        },
        "background_samples_excluded": True,
    }
    _validate_frame_capture(frame, [1280, 720])
    forged = json.loads(json.dumps(frame))
    forged["summary"]["p95_ms"] = 15.0
    expect_failure(lambda: _validate_frame_capture(forged, [1280, 720]), "forged p95 summary was accepted")
    stalled = json.loads(json.dumps(frame))
    stalled["samples_ms"][-1] = 250.0
    stalled["summary"] = {
        "sample_count": 180, "p95_ms": 16.667, "worst_ms": 250.0,
        "visible_stall_count_gte_250ms": 1,
    }
    expect_failure(lambda: _validate_frame_capture(stalled, [1280, 720]), "visible 250 ms stall was accepted")

    pinch = {
        "schema_version": "1.0.0", "gesture": "pinch-out", "target_selector": "#app canvas",
        "viewport_css_px": [390, 844], "canvas_rect_css_px": {"x": 0, "y": 0, "width": 390, "height": 844},
        "start_points_css_px": [[155, 300], [235, 300]], "end_points_css_px": [[90, 300], [300, 300]],
        "hit_test_targets": ["CANVAS"] * 4, "all_points_on_canvas": True,
        "baseline": {"camera_distance_m": 30.8, "desired_distance_m": 30.8, "stable_frames": 6, "samples_camera_distance_m": [30.8] * 6},
        "after": {"camera_distance_m": 10.267, "desired_distance_m": 10.267, "stable_frames": 6, "samples_camera_distance_m": [30.0, 25.0, 20.0, 15.0, 11.0, 10.27, 10.267, 10.267, 10.267, 10.267, 10.267, 10.267]},
        "intermediate_desired_distance_m": 15.4, "final_gesture_desired_distance_m": 10.267,
        "camera_distance_delta_m": -20.533, "desired_distance_delta_m": -20.533,
        "absolute_camera_distance_delta_m": 20.533, "minimum_required_delta_m": 0.616,
        "expected_direction": "decrease", "actual_direction": "decrease", "monotonic_camera_change": True,
        "settled_before": True, "settled_after": True, "outcome": "pass",
    }
    _validate_742_pinch_zoom(pinch, [390, 844])
    unchanged_pinch = json.loads(json.dumps(pinch))
    unchanged_pinch["after"]["camera_distance_m"] = 30.8
    unchanged_pinch["after"]["desired_distance_m"] = 30.8
    unchanged_pinch["camera_distance_delta_m"] = 0
    unchanged_pinch["desired_distance_delta_m"] = 0
    unchanged_pinch["absolute_camera_distance_delta_m"] = 0
    expect_failure(lambda: _validate_742_pinch_zoom(unchanged_pinch, [390, 844]), "zero-distance pinch was accepted")
    obstructed_pinch = json.loads(json.dumps(pinch))
    obstructed_pinch["hit_test_targets"][0] = "SECTION"
    expect_failure(lambda: _validate_742_pinch_zoom(obstructed_pinch, [390, 844]), "pinch behind controls was accepted")
    wrong_direction_pinch = json.loads(json.dumps(pinch))
    wrong_direction_pinch["actual_direction"] = "increase"
    expect_failure(lambda: _validate_742_pinch_zoom(wrong_direction_pinch, [390, 844]), "wrong-direction pinch was accepted")
    nonmonotonic_pinch = json.loads(json.dumps(pinch))
    nonmonotonic_pinch["after"]["samples_camera_distance_m"][3] = 26.0
    expect_failure(lambda: _validate_742_pinch_zoom(nonmonotonic_pinch, [390, 844]), "nonmonotonic pinch was accepted")

    runner_path = ROOT / CAPTURE_RUNNER_PATH
    runner_record = {"path": CAPTURE_RUNNER_PATH, "sha256": hashlib.sha256(runner_path.read_bytes()).hexdigest(), "bytes": runner_path.stat().st_size}
    _validate_capture_runner(runner_record)
    wrong_runner = dict(runner_record)
    wrong_runner["sha256"] = "0" * 64
    expect_failure(lambda: _validate_capture_runner(wrong_runner), "mutated committed capture-runner binding was accepted")
    outcomes = {"first": {"outcome": "pass", "value": 1}, "second": {"outcome": "pass", "value": 2}, "third": {"outcome": "pass", "value": 3}}
    trace = {"outcomes": outcomes, "outcomes_sha256": hashlib.sha256(json.dumps(outcomes, separators=(",", ":")).encode()).hexdigest()}
    _validate_structured_trace_outcomes(trace, "test_gate")
    forged_trace = json.loads(json.dumps(trace))
    forged_trace["outcomes"]["first"]["value"] = 99
    expect_failure(lambda: _validate_structured_trace_outcomes(forged_trace, "test_gate"), "forged structured trace outcome was accepted")
    free_form_trace = {"outcomes": {"first": "looked good", "second": "pass", "third": "worked"}, "outcomes_sha256": "0" * 64}
    expect_failure(lambda: _validate_structured_trace_outcomes(free_form_trace, "test_gate"), "free-form transcript was accepted as trace authority")

    lock_path = ROOT / "package-lock.json"
    environment = {
        "browser": {"name": "Chromium", "version": "151.0.7922.34", "user_agent": "test user agent"},
        "os": {"name": "macOS", "version": "26.5.2", "build": "25F84"},
        "gpu": {
            "status": "observed", "vendor": "test vendor", "renderer": "test renderer",
            "api": "WebGL 2", "collection_method": "WEBGL_debug_renderer_info", "reason": None,
        },
        "automation": {
            "tool": "Playwright", "version": EXPECTED_PLAYWRIGHT_VERSION,
            "source": "repo-locked-default",
            "lockfile": {
                "path": "package-lock.json",
                "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                "bytes": lock_path.stat().st_size,
            },
            "browser_executable": {
                "product": "chromium", "revision": "1234", "browser_version": "151.0.7922.34",
                "executable_basename": "Chromium", "sha256": "1" * 64, "bytes": 1000000,
            },
        },
        "captured_at_utc": "2026-08-25T12:00:00Z",
        "physical_device_session": False,
        "assistive_technology_session": False,
    }
    _validate_environment(environment)
    overstated = json.loads(json.dumps(environment))
    overstated["assistive_technology_session"] = True
    expect_failure(lambda: _validate_environment(overstated), "unsupported assistive-technology claim was accepted")
    external_toolchain = json.loads(json.dumps(environment))
    external_toolchain["automation"]["source"] = "explicit-override"
    expect_failure(lambda: _validate_environment(external_toolchain), "external-only browser toolchain was accepted")
    wrong_browser_hash = json.loads(json.dumps(environment))
    wrong_browser_hash["automation"]["browser_executable"]["sha256"] = "not-a-digest"
    expect_failure(lambda: _validate_environment(wrong_browser_hash), "malformed browser executable digest was accepted")
    wrong_revision = json.loads(json.dumps(environment))
    wrong_revision["automation"]["browser_executable"]["revision"] = "9999"
    expect_failure(lambda: _validate_environment(wrong_revision), "wrong bundled Chromium revision was accepted")
    wrong_lock = json.loads(json.dumps(environment))
    wrong_lock["automation"]["lockfile"]["sha256"] = "0" * 64
    expect_failure(lambda: _validate_environment(wrong_lock), "wrong Playwright lockfile digest was accepted")

    terminal = {
        "source": "module-load-failed", "viewer_terminal": True,
        "error_role": "alert", "error_aria_live": "assertive", "error_visible": True,
        "error_focused": True, "app_inert": True, "interface_inert": True,
        "disabled_control_count": 4, "total_control_count": 4,
        "drive_x": "1.000", "drive_z": "2.000",
    }
    fatal_cases = {}
    for fault, source in {
        "module": "module-load-failed", "webgl": "webgl-unavailable",
        "network": "load-failed", "contract": "contract-failed",
    }.items():
        first = {**terminal, "source": source}
        fatal_cases[fault] = {
            "outcome": "pass", "fault": fault, "expected_source": source,
            "terminal_first": first, "terminal_after_250ms": dict(first),
            "animation_state_stable_250ms": True,
        }
    _validate_fatal_failures(fatal_cases)
    moving_terminal = json.loads(json.dumps(fatal_cases))
    moving_terminal["network"]["terminal_after_250ms"]["drive_x"] = "1.001"
    expect_failure(lambda: _validate_fatal_failures(moving_terminal), "animating fatal terminal state was accepted")
    inaccessible_terminal = json.loads(json.dumps(fatal_cases))
    inaccessible_terminal["webgl"]["terminal_first"]["error_focused"] = False
    expect_failure(lambda: _validate_fatal_failures(inaccessible_terminal), "unfocused fatal alert was accepted")

    reduced = {
        "transition": "no-preference->reduce->no-preference",
        "raw_samples": {
            "moving_start": {"x": "0.0", "z": "0.0"},
            "before_reduce": {"x": "0.1", "z": "0.0"},
            "reduced_start": {"x": "0.1", "z": "0.0"},
            "reduced_end": {"x": "0.1", "z": "0.0"},
            "relaxed": {"x": "0.1", "z": "0.0", "autonomyPressed": "false", "manual": True},
        },
        "moving_before": True, "frozen_while_reduced": True,
        "did_not_auto_resume": True, "manual_controls_enabled": True,
    }
    _validate_live_reduced_motion(reduced, "fixture")
    auto_resumed = json.loads(json.dumps(reduced))
    auto_resumed["raw_samples"]["relaxed"]["x"] = "0.2"
    expect_failure(lambda: _validate_live_reduced_motion(auto_resumed, "fixture"), "auto-resumed reduced-motion sample was accepted")
    trusted_boolean = json.loads(json.dumps(reduced))
    trusted_boolean["raw_samples"]["reduced_end"]["x"] = "0.2"
    expect_failure(lambda: _validate_live_reduced_motion(trusted_boolean, "fixture"), "forged reduced-motion boolean overrode raw samples")

    slider_names = {"Boom lift", "Boom telescope"}
    ax_tree = {
        "source": "Chromium CDP Accessibility.getFullAXTree",
        "states": [
            {"state": "controls_open", "nodes": [
                {"role": "application", "name": "742 application", "value": None, "states": {"focusable": True}},
                {"role": "button", "name": "About", "value": None, "states": {"focusable": True}},
                {"role": "slider", "name": "Boom lift", "value": 0, "states": {"focusable": True, "settable": True, "valuetext": "0"}},
                {"role": "slider", "name": "Boom telescope", "value": 32.5, "states": {"focusable": True, "settable": True, "valuetext": "32.5"}},
            ]},
            {"state": "modal_open", "nodes": [
                {"role": "dialog", "name": "Evidence boundary", "value": None, "states": {"modal": True}},
                {"role": "button", "name": "Close inspector", "value": None, "states": {"focusable": True}},
            ]},
        ],
    }
    _validate_accessibility_tree(ax_tree, slider_names)
    fabricated_units = json.loads(json.dumps(ax_tree))
    fabricated_units["states"][0]["nodes"][2]["states"]["valuetext"] = "0°"
    expect_failure(lambda: _validate_accessibility_tree(fabricated_units, slider_names), "fabricated AX display units were accepted")
    unnamed = json.loads(json.dumps(ax_tree))
    unnamed["states"][0]["nodes"][2]["name"] = ""
    expect_failure(lambda: _validate_accessibility_tree(unnamed, slider_names), "unnamed AX slider was accepted")
    disabled = json.loads(json.dumps(ax_tree))
    disabled["states"][0]["nodes"][2]["states"]["disabled"] = True
    expect_failure(lambda: _validate_accessibility_tree(disabled, slider_names), "disabled AX slider was accepted")

    if EXPECTED_SCREENSHOT_DIMENSIONS["mobile_browser_interaction"] != {(390, 844), (844, 390)}:
        raise RuntimeError("mobile screenshot viewport contract drift")

    fixtures = expected_selection_outcomes()
    if len(fixtures) != 5 or [item["expectedVolume"] for item in fixtures] != ["front", "high-tie", "front", "front", None]:
        raise RuntimeError("independent selection fixture set drift")
    raw_fixtures = [
        {"case": 1, "hits": [{"volume": "rear", "component": "rear", "distanceM": 2, "priority": 5}, {"volume": "front", "component": "front", "distanceM": 1, "priority": 0}], "visibleSurfaceComponent": None, "basis": "nearest-distance", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
        {"case": 2, "hits": [{"volume": "low-tie", "component": "low-tie", "distanceM": 1, "priority": 1}, {"volume": "high-tie", "component": "high-tie", "distanceM": 1.01, "priority": 4}], "visibleSurfaceComponent": None, "basis": "distance-tie", "expectedComponent": "high-tie", "observedComponent": "high-tie", "expectedVolume": "high-tie", "observedVolume": "high-tie", "pass": True},
        {"case": 3, "hits": [{"volume": "front", "component": "front", "distanceM": 1, "priority": 0}, {"volume": "front", "component": "front", "distanceM": 1.8, "priority": 0}, {"volume": "rear", "component": "rear", "distanceM": 2, "priority": 5}], "visibleSurfaceComponent": None, "basis": "nearest-distance", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
        {"case": 4, "hits": [{"volume": "rear", "component": "rear", "distanceM": 0.8, "priority": 5}, {"volume": "front", "component": "front", "distanceM": 1, "priority": 0}], "visibleSurfaceComponent": "front", "basis": "visible-surface", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
        {"case": 5, "hits": [{"volume": "rear", "component": "rear", "distanceM": 0.8, "priority": 5}], "visibleSurfaceComponent": "front", "basis": "visible-surface", "expectedComponent": None, "observedComponent": None, "expectedVolume": None, "observedVolume": None, "pass": True},
    ]
    _validate_selection_fixtures(raw_fixtures, json.loads(json.dumps(raw_fixtures)))
    stripped_fixture = json.loads(json.dumps(raw_fixtures))
    stripped_fixture[0].pop("hits")
    expect_failure(lambda: _validate_selection_fixtures(stripped_fixture, stripped_fixture), "stripped raw fixture was accepted")
    forged_hit = json.loads(json.dumps(raw_fixtures))
    forged_hit[0]["hits"][0]["distanceM"] = 0.5
    expect_failure(lambda: _validate_selection_fixtures(forged_hit, forged_hit), "forged fixture winner was accepted")
    forged_observation = json.loads(json.dumps(raw_fixtures))
    forged_observation[1]["observedVolume"] = "low-tie"
    expect_failure(lambda: _validate_selection_fixtures(forged_observation, forged_observation), "forged fixture observation was accepted")
    dom_mismatch = json.loads(json.dumps(raw_fixtures))
    dom_mismatch[3]["hits"][0]["priority"] = 4
    expect_failure(lambda: _validate_selection_fixtures(raw_fixtures, dom_mismatch), "fixture record not bound exactly to DOM was accepted")
    ray = {
        "hitComponents": ["chassis", "cab"], "hitDistancesM": [1.0, 1.01],
        "visibleSurfaceComponent": None,
    }
    if _independent_selection_expected(ray) != "cab":
        raise RuntimeError("independent distance-tie priority recomputation drift")

    if BROWSER_CAPTURE_ALLOWLIST_PATH in CANONICAL_FILES.values():
        raise RuntimeError("post-capture browser allowlist re-entered the candidate canonical file set")
    expect_failure(
        lambda: _candidate_canonical_paths({
            "files": {"bad": {"path": BROWSER_CAPTURE_ALLOWLIST_PATH}},
            "runtime": {"files": []},
            "automated_checks": {},
        }),
        "binder accepted browser allowlist as a candidate canonical path",
    )
    allowlist_path = ROOT / BROWSER_CAPTURE_ALLOWLIST_PATH
    allowlist_record = {
        "path": BROWSER_CAPTURE_ALLOWLIST_PATH,
        "sha256": hashlib.sha256(allowlist_path.read_bytes()).hexdigest(),
        "bytes": allowlist_path.stat().st_size,
    }
    verify_browser_capture_allowlist_binding(allowlist_record)
    expect_failure(
        lambda: verify_browser_capture_allowlist_binding(None),
        "missing browser allowlist binding was accepted",
    )
    wrong_path = dict(allowlist_record)
    wrong_path["path"] = "docs/review/742/not-the-browser-allowlist.json"
    expect_failure(
        lambda: verify_browser_capture_allowlist_binding(wrong_path),
        "wrong browser allowlist binding path was accepted",
    )
    wrong_hash = dict(allowlist_record)
    wrong_hash["sha256"] = "0" * 64
    expect_failure(
        lambda: verify_browser_capture_allowlist_binding(wrong_hash),
        "mutated browser allowlist binding hash was accepted",
    )
    wrong_size = dict(allowlist_record)
    wrong_size["bytes"] += 1
    expect_failure(
        lambda: verify_browser_capture_allowlist_binding(wrong_size),
        "mutated browser allowlist binding size was accepted",
    )
    print(json.dumps({"status": "PASS", "negative_cases": NEGATIVE_CASES, "selection_fixtures": len(fixtures), "screenshot_viewport_contracts": len(EXPECTED_SCREENSHOT_DIMENSIONS)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
