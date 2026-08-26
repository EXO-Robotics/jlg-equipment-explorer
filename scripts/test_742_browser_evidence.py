#!/usr/bin/env python3
"""Focused positive/negative tests for the 742 raw browser-evidence parser."""

from __future__ import annotations

import hashlib
import json

from validate_742_browser_evidence import (
    CAPTURE_RUNNER_PATH,
    EXPECTED_PLAYWRIGHT_VERSION,
    EXPECTED_SCREENSHOT_DIMENSIONS,
    canonical_digest,
    _validate_accessibility_tree,
    _independent_selection_expected,
    _validate_environment,
    _validate_fatal_failures,
    _validate_742_terminal_failure_matrix,
    _validate_live_reduced_motion,
    _validate_capture_runner,
    _validate_structured_trace_outcomes,
    _validate_frame_capture,
    _validate_742_pinch_zoom,
    _validate_selection_fixtures,
    _validate_upstream_screenshot_framing,
    _validate_742_clean_presentation_frame,
    _validate_upstream_identity,
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
        "screenshot_diagnostic": {
            "kind": "captured_visible_frame_window",
            "label_text": "desktop captured window · 180 visible frames · p95 16.667 ms · worst 16.667 ms · stalls ≥250 ms 0",
            "summary": {
                "sample_count": 180, "p95_ms": 16.667, "worst_ms": 16.667,
                "visible_stall_count_gte_250ms": 0,
            },
        },
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
    mismatched_diagnostic = json.loads(json.dumps(frame))
    mismatched_diagnostic["screenshot_diagnostic"]["label_text"] = "rolling diagnostics"
    expect_failure(lambda: _validate_frame_capture(mismatched_diagnostic, [1280, 720]), "mismatched screenshot diagnostic window was accepted")

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
    executable = {
        "product": "chromium", "revision": "1234", "browser_version": "151.0.7922.34",
        "executable_basename": "Chromium", "sha256": "1" * 64, "bytes": 1000000,
    }
    bundle_entries = [
        {"path": "Chromium", "type": "file", "bytes": 1000000, "sha256": "1" * 64},
        {"path": "Resources/icudtl.dat", "type": "file", "bytes": 250, "sha256": "2" * 64},
        {"path": "Versions/Current", "type": "symlink", "target": "151.0.7922.34"},
    ]
    root_chunks = [
        f"file\0Chromium\0{1000000}\0{'1' * 64}\n",
        f"file\0Resources/icudtl.dat\0{250}\0{'2' * 64}\n",
        "symlink\0Versions/Current\0" + "151.0.7922.34\n",
    ]
    browser_bundle = {
        "schema_version": "1.0.0", "root_basename": "Chromium.app",
        "executable_relative_path": "Chromium", "file_count": 2, "symlink_count": 1,
        "total_file_bytes": 1000250, "manifest_sha256": canonical_digest(bundle_entries),
        "root_digest_sha256": hashlib.sha256("".join(root_chunks).encode()).hexdigest(),
        "entries": bundle_entries,
    }
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
            "browser_executable": executable,
            "browser_bundle": browser_bundle,
        },
        "captured_at_utc": "2026-08-25T12:00:00Z",
        "physical_device_session": False,
        "assistive_technology_session": False,
    }
    _validate_environment(environment)
    upstream_identity = {
        "route": "/es1930m/", "configuration_id": "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
        "release": "1.0.4", "asset_sha256": "a" * 64, "runtime_sha256": "b" * 64,
    }
    _validate_upstream_identity(upstream_identity, dict(upstream_identity))
    cyclic_receipt_identity = {**upstream_identity, "receipt_sha256": "c" * 64, "receipt_bytes": 4000}
    expect_failure(lambda: _validate_upstream_identity(cyclic_receipt_identity, upstream_identity), "stale/cyclic upstream receipt identity was accepted")
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
    missing_bundle = json.loads(json.dumps(environment))
    missing_bundle["automation"].pop("browser_bundle")
    expect_failure(lambda: _validate_environment(missing_bundle), "launcher-only Chromium proof was accepted")
    mutated_resource = json.loads(json.dumps(environment))
    mutated_resource["automation"]["browser_bundle"]["entries"][1]["sha256"] = "3" * 64
    expect_failure(lambda: _validate_environment(mutated_resource), "mutated Chromium resource was accepted")

    terminal = {
        "source": "module-load-failed", "viewer_terminal": True,
        "error_role": "alert", "error_aria_live": "assertive", "error_visible": True,
        "error_focused": True, "app_inert": True, "interface_inert": True,
        "disabled_control_count": 4, "total_control_count": 4,
        "drive_x": "1.000", "drive_z": "2.000",
        "boot_frame_count": "8", "runtime_frame_count": "12", "terminal_frame_count": "12",
        "terminal_frame_source": "runtime",
    }
    frame_baseline = {
        "counter": "runtime",
        "samples": [
            {"counter": "runtime", "value": 8, "at_ms": 100.0},
            {"counter": "runtime", "value": 12, "at_ms": 166.7},
        ],
    }
    fatal_cases = {}
    for fault, source in {
        "module": "module-load-failed", "webgl": "webgl-unavailable",
        "network": "load-failed", "contract": "contract-failed",
    }.items():
        first = {**terminal, "source": source}
        fatal_cases[fault] = {
            "outcome": "pass", "fault": fault, "expected_source": source,
            "animation_baseline": frame_baseline,
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
    null_baseline = json.loads(json.dumps(fatal_cases))
    null_baseline["module"]["animation_baseline"]["samples"][0]["value"] = None
    expect_failure(lambda: _validate_fatal_failures(null_baseline), "null fatal animation baseline was accepted")
    frozen_baseline = json.loads(json.dumps(fatal_cases))
    frozen_baseline["module"]["animation_baseline"]["samples"][1]["value"] = 8
    expect_failure(lambda: _validate_fatal_failures(frozen_baseline), "unchanging fatal animation baseline was accepted")
    mismatched_counter_source = json.loads(json.dumps(fatal_cases))
    mismatched_counter_source["module"]["terminal_first"]["terminal_frame_source"] = "boot"
    expect_failure(lambda: _validate_fatal_failures(mismatched_counter_source), "mismatched terminal counter source was accepted")

    matrix_cases = {}
    for fault, source in {
        "bootstrap-timeout": "bootstrap-timeout", "asset-timeout": "load-timeout",
        "loader-start": "loader-start-failed", "runtime-error": "unexpected-runtime-error",
        "unhandled-rejection": "unhandled-rejection",
    }.items():
        first = {**terminal, "source": source}
        motion = None
        if fault in {"runtime-error", "unhandled-rejection"}:
            motion = {
                "start": {"controls": {"lift-control": "0"}, "runtime_frame_count": 8},
                "end": {"controls": {"lift-control": "2"}, "runtime_frame_count": 12},
            }
        matrix_cases[fault] = {
            "outcome": "pass", "fault": fault, "expected_source": source,
            "upstream_request_held": fault == "asset-timeout",
            "animation_baseline": frame_baseline, "showcase_motion": motion,
            "terminal_first": first, "terminal_after_250ms": dict(first),
            "animation_state_stable_250ms": True,
        }
    terminal_matrix = {"outcome": "pass", "cases": matrix_cases}
    _validate_742_terminal_failure_matrix(terminal_matrix)
    missing_fault = json.loads(json.dumps(terminal_matrix))
    missing_fault["cases"].pop("loader-start")
    expect_failure(lambda: _validate_742_terminal_failure_matrix(missing_fault), "incomplete 742 fatal matrix was accepted")
    no_showcase_motion = json.loads(json.dumps(terminal_matrix))
    no_showcase_motion["cases"]["runtime-error"]["showcase_motion"] = None
    expect_failure(lambda: _validate_742_terminal_failure_matrix(no_showcase_motion), "runtime fault without showcase motion was accepted")
    no_upstream_hold = json.loads(json.dumps(terminal_matrix))
    no_upstream_hold["cases"]["asset-timeout"]["upstream_request_held"] = False
    expect_failure(lambda: _validate_742_terminal_failure_matrix(no_upstream_hold), "asset timeout without a held upstream request was accepted")

    reduced = {
        "transition": "no-preference->reduce->no-preference",
        "controller": "autonomy",
        "raw_samples": {
            "moving_start": {"x": "0.0", "z": "0.0"},
            "before_reduce": {"x": "0.1", "z": "0.0"},
            "reduced_start": {"x": "0.1", "z": "0.0"},
            "reduced_end": {"x": "0.1", "z": "0.0"},
            "relaxed": {"x": "0.1", "z": "0.0", "control_pressed": "false", "manual": True},
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
    null_motion = json.loads(json.dumps(reduced))
    null_motion["raw_samples"]["moving_start"]["x"] = None
    expect_failure(lambda: _validate_live_reduced_motion(null_motion, "fixture"), "null reduced-motion baseline was accepted")
    showcase_reduced = json.loads(json.dumps(reduced))
    showcase_reduced["controller"] = "showcase"
    showcase_reduced["raw_samples"] = {
        "moving_start": {"lift": "0", "telescope": "0", "tilt": "0", "steer": "0", "level": "0"},
        "before_reduce": {"lift": "12", "telescope": "4", "tilt": "2", "steer": "1", "level": "1"},
        "reduced_start": {"lift": "12", "telescope": "4", "tilt": "2", "steer": "1", "level": "1"},
        "reduced_end": {"lift": "12", "telescope": "4", "tilt": "2", "steer": "1", "level": "1"},
        "relaxed": {"lift": "12", "telescope": "4", "tilt": "2", "steer": "1", "level": "1", "control_pressed": "false", "manual": True},
    }
    _validate_live_reduced_motion(showcase_reduced, "742 fixture")

    def projected_bounds(viewport, camera_distance, margin=20):
        width, height = viewport
        return {
            "basis": "projected-stowed-visible-glb-aabb",
            "viewport_css_px": viewport,
            "canvas_rect_css_px": {"x": 0, "y": 0, "width": width, "height": height},
            "asset_bounds_m": {"min": [-1.0, 0.0, -0.5], "max": [2.0, 2.0, 0.5], "size": [3.0, 2.0, 1.0]},
            "projected_bounds_css_px": {"left": margin, "right": width - margin, "top": margin, "bottom": height - margin},
            "edge_margins_css_px": {"left": margin, "right": margin, "top": margin, "bottom": margin},
            "minimum_edge_margin_css_px": 16,
            "camera_distance_m": camera_distance,
            "camera_orientation": {"kind": "azimuth-polar", "azimuth_rad": -0.72, "polar_rad": 1.18},
            "occlusion_checks": [
                {
                    "selector": ".control-panel",
                    "rect_css_px": {"left": 0, "right": width, "top": height - 10, "bottom": height},
                    "intersects_machine_bounds": False,
                },
            ],
            "whole_machine_contained": True,
        }

    framing_state = {
        "reset_pressed": True, "stow_pressed": True, "controls_expanded": False,
        "camera_distance_m": 12.0, "desired_distance_m": 12.0,
        "viewer_terminal": False, "machine_source": "glb", "reset_distance_m": 10.0,
        "presentation_zoom_delta_y": 200, "presentation_orbit_right_steps": 0,
        "machine_bounds": projected_bounds([390, 844], 12.0),
    }
    desktop_framing = {
        **framing_state, "controls_expanded": True,
        "machine_bounds": projected_bounds([1280, 720], 12.0),
    }
    screenshot_framing = {"outcome": "pass", "desktop": desktop_framing, "mobile": framing_state}
    _validate_upstream_screenshot_framing(screenshot_framing, "glb")
    clipped_framing = json.loads(json.dumps(screenshot_framing))
    clipped_framing["mobile"]["machine_bounds"]["edge_margins_css_px"]["right"] = 2.0
    expect_failure(lambda: _validate_upstream_screenshot_framing(clipped_framing, "glb"), "clipped whole-machine projected bounds were accepted")
    expanded_mobile = json.loads(json.dumps(screenshot_framing))
    expanded_mobile["mobile"]["controls_expanded"] = True
    expect_failure(lambda: _validate_upstream_screenshot_framing(expanded_mobile, "glb"), "expanded mobile controls were accepted for overview screenshot")
    boom_framing = json.loads(json.dumps(screenshot_framing))
    boom_framing["desktop"]["machine_source"] = "blender-showcase-v1.1.0"
    boom_framing["mobile"]["machine_source"] = "blender-showcase-v1.1.0"
    boom_framing["mobile"]["presentation_orbit_right_steps"] = 3
    boom_framing["mobile"]["machine_bounds"]["camera_orientation"] = {"kind": "theta-phi", "theta_rad": 1.12, "phi_rad": 1.44}
    _validate_upstream_screenshot_framing(boom_framing, "blender-showcase-v1.1.0")
    forged_boom_orbit = json.loads(json.dumps(boom_framing))
    forged_boom_orbit["mobile"]["machine_bounds"]["camera_orientation"]["theta_rad"] = 0.76
    expect_failure(lambda: _validate_upstream_screenshot_framing(forged_boom_orbit, "blender-showcase-v1.1.0"), "forged 600S mobile keyboard orbit was accepted")
    clean_742_frame = {
        "reset_pressed": True, "stow_pressed": True, "controls_expanded": False,
        "selected_component": None, "camera_distance_m": 12.0, "desired_distance_m": 12.0,
        "pose_frame_distance_m": 9.0, "effective_max_distance_m": 24.0,
        "reset_distance_m": 9.0, "presentation_zoom_delta_y": 200,
        "machine_bounds": projected_bounds([390, 844], 12.0),
    }
    _validate_742_clean_presentation_frame(clean_742_frame, [390, 844])
    trusted_containment = json.loads(json.dumps(clean_742_frame))
    trusted_containment["machine_bounds"]["projected_bounds_css_px"]["left"] = -1.0
    expect_failure(lambda: _validate_742_clean_presentation_frame(trusted_containment, [390, 844]), "forged whole-machine containment boolean was accepted")
    occluded_machine = json.loads(json.dumps(clean_742_frame))
    occluded_machine["machine_bounds"]["occlusion_checks"][0]["intersects_machine_bounds"] = True
    expect_failure(lambda: _validate_742_clean_presentation_frame(occluded_machine, [390, 844]), "machine bounds behind visible controls were accepted")
    malformed_camera = json.loads(json.dumps(clean_742_frame))
    malformed_camera["machine_bounds"]["camera_orientation"].pop("polar_rad")
    expect_failure(lambda: _validate_742_clean_presentation_frame(malformed_camera, [390, 844]), "incomplete projected camera orientation was accepted")
    expanded_short_landscape = json.loads(json.dumps(clean_742_frame))
    expanded_short_landscape["machine_bounds"]["viewport_css_px"] = [844, 390]
    expanded_short_landscape["machine_bounds"]["canvas_rect_css_px"].update({"width": 844, "height": 390})
    expanded_short_landscape["machine_bounds"]["projected_bounds_css_px"].update({"right": 824, "bottom": 370})
    expanded_short_landscape["controls_expanded"] = True
    expect_failure(lambda: _validate_742_clean_presentation_frame(expanded_short_landscape, [844, 390]), "expanded compact short-landscape controls were accepted")

    def ax_value(value, value_type="string", related=None):
        return {"type": value_type, "value": value, "related_nodes": related or []}

    def ax_node(node_id, role, name, *, value=None, description="", properties=None):
        return {
            "node_id": node_id, "backend_dom_node_id": node_id, "role": role,
            "name": ax_value(name), "description": ax_value(description),
            "value": ax_value(value, "number" if isinstance(value, (int, float)) else "string"),
            "properties": properties or [],
        }

    slider_values = {"Boom lift": "0°", "Boom telescope": "0.00 m visual"}
    dom_sliders = []
    slider_nodes = []
    for index, (name, engineering) in enumerate(slider_values.items(), 1):
        detail_id = f"slider-{index}-engineering-detail"
        dom_sliders.append({
            "selector": f"#slider-{index}", "name": name, "aria_valuetext": engineering,
            "aria_details": [detail_id], "details_text": [{"id": detail_id, "text": engineering}],
        })
        slider_nodes.append(ax_node(
            f"slider-{index}", "slider", name, value=0,
            properties=[
                {"name": "focusable", "value": ax_value(True, "boolean")},
                {"name": "settable", "value": ax_value(True, "boolean")},
                {"name": "disabled", "value": ax_value(False, "boolean")},
                {"name": "valuetext", "value": ax_value("0")},
                {"name": "details", "value": ax_value(None, "idrefList", [{"backend_dom_node_id": 100 + index, "idref": detail_id, "text": engineering}])},
            ],
        ))
    ax_tree = {
        "source": "Chromium CDP Accessibility.getFullAXTree",
        "dom_sliders": dom_sliders,
        "states": [
            {"state": "controls_open", "nodes": [
                ax_node("app", "application", "742 application"),
                ax_node("button", "button", "About"),
                *slider_nodes,
                ax_node("status", "status", "Ready", properties=[{"name": "live", "value": ax_value("polite")}]),
            ]},
            {"state": "modal_open", "nodes": [
                ax_node("dialog", "dialog", "Evidence boundary"),
                ax_node("close", "button", "Close inspector"),
                ax_node("modal-status", "status", "Inspector open", properties=[{"name": "live", "value": ax_value("polite")}]),
            ]},
        ],
    }
    _validate_accessibility_tree(ax_tree, slider_values)
    numeric_fallback = json.loads(json.dumps(ax_tree))
    numeric_fallback["states"][0]["nodes"][2]["properties"][-1]["value"]["related_nodes"] = []
    expect_failure(lambda: _validate_accessibility_tree(numeric_fallback, slider_values), "numeric-only AX fallback was accepted")
    mismatched_detail = json.loads(json.dumps(ax_tree))
    mismatched_detail["dom_sliders"][0]["details_text"][0]["text"] = "0"
    expect_failure(lambda: _validate_accessibility_tree(mismatched_detail, slider_values), "mismatched AX engineering detail was accepted")
    unnamed = json.loads(json.dumps(ax_tree))
    unnamed["states"][0]["nodes"][2]["name"]["value"] = ""
    expect_failure(lambda: _validate_accessibility_tree(unnamed, slider_values), "unnamed AX slider was accepted")
    disabled = json.loads(json.dumps(ax_tree))
    disabled["states"][0]["nodes"][2]["properties"][2]["value"]["value"] = True
    expect_failure(lambda: _validate_accessibility_tree(disabled, slider_values), "disabled AX slider was accepted")
    no_live = json.loads(json.dumps(ax_tree))
    no_live["states"][0]["nodes"].pop()
    expect_failure(lambda: _validate_accessibility_tree(no_live, slider_values), "AX tree without live/status semantics was accepted")

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
