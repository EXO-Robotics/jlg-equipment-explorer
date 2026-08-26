#!/usr/bin/env python3
"""Focused positive/negative tests for the 742 raw browser-evidence parser."""

from __future__ import annotations

import json

from validate_742_browser_evidence import (
    EXPECTED_SCREENSHOT_DIMENSIONS,
    _validate_accessibility_tree,
    _independent_selection_expected,
    _validate_environment,
    _validate_frame_capture,
    _validate_selection_fixtures,
    expected_selection_outcomes,
)


def expect_failure(callable_value, message: str) -> None:
    try:
        callable_value()
    except RuntimeError:
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

    environment = {
        "browser": {"name": "Chromium", "version": "140.0.0.0", "user_agent": "test user agent"},
        "os": {"name": "macOS", "version": "26.5.2", "build": "25F84"},
        "gpu": {
            "status": "observed", "vendor": "test vendor", "renderer": "test renderer",
            "api": "WebGL 2", "collection_method": "WEBGL_debug_renderer_info", "reason": None,
        },
        "automation": {"tool": "test tool", "version": "1.0.0"},
        "captured_at_utc": "2026-08-25T12:00:00Z",
        "physical_device_session": False,
        "assistive_technology_session": False,
    }
    _validate_environment(environment)
    overstated = json.loads(json.dumps(environment))
    overstated["assistive_technology_session"] = True
    expect_failure(lambda: _validate_environment(overstated), "unsupported assistive-technology claim was accepted")

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
    if len(fixtures) != 4 or [item["expectedVolume"] for item in fixtures] != ["front", "high-tie", "front", "front"]:
        raise RuntimeError("independent selection fixture set drift")
    raw_fixtures = [
        {"case": 1, "hits": [{"volume": "rear", "component": "rear", "distanceM": 2, "priority": 5}, {"volume": "front", "component": "front", "distanceM": 1, "priority": 0}], "visibleSurfaceComponent": None, "basis": "nearest-distance", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
        {"case": 2, "hits": [{"volume": "low-tie", "component": "low-tie", "distanceM": 1, "priority": 1}, {"volume": "high-tie", "component": "high-tie", "distanceM": 1.01, "priority": 4}], "visibleSurfaceComponent": None, "basis": "distance-tie", "expectedComponent": "high-tie", "observedComponent": "high-tie", "expectedVolume": "high-tie", "observedVolume": "high-tie", "pass": True},
        {"case": 3, "hits": [{"volume": "front", "component": "front", "distanceM": 1, "priority": 0}, {"volume": "front", "component": "front", "distanceM": 1.8, "priority": 0}, {"volume": "rear", "component": "rear", "distanceM": 2, "priority": 5}], "visibleSurfaceComponent": None, "basis": "nearest-distance", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
        {"case": 4, "hits": [{"volume": "rear", "component": "rear", "distanceM": 0.8, "priority": 5}, {"volume": "front", "component": "front", "distanceM": 1, "priority": 0}], "visibleSurfaceComponent": "front", "basis": "visible-surface", "expectedComponent": "front", "observedComponent": "front", "expectedVolume": "front", "observedVolume": "front", "pass": True},
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
    print(json.dumps({"status": "PASS", "negative_cases": 10, "selection_fixtures": len(fixtures), "screenshot_viewport_contracts": len(EXPECTED_SCREENSHOT_DIMENSIONS)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
