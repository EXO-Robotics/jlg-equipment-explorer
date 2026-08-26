#!/usr/bin/env python3
"""Focused positive/negative tests for the 742 raw browser-evidence parser."""

from __future__ import annotations

import json

from validate_742_browser_evidence import (
    EXPECTED_SCREENSHOT_DIMENSIONS,
    _independent_selection_expected,
    _validate_environment,
    _validate_frame_capture,
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

    if EXPECTED_SCREENSHOT_DIMENSIONS["mobile_browser_interaction"] != {(390, 844), (844, 390)}:
        raise RuntimeError("mobile screenshot viewport contract drift")

    fixtures = expected_selection_outcomes()
    if len(fixtures) != 4 or [item["expectedVolume"] for item in fixtures] != ["front", "high-tie", "front", "front"]:
        raise RuntimeError("independent selection fixture set drift")
    ray = {
        "hitComponents": ["chassis", "cab"], "hitDistancesM": [1.0, 1.01],
        "visibleSurfaceComponent": None,
    }
    if _independent_selection_expected(ray) != "cab":
        raise RuntimeError("independent distance-tie priority recomputation drift")
    print(json.dumps({"status": "PASS", "negative_cases": 3, "selection_fixtures": len(fixtures), "screenshot_viewport_contracts": len(EXPECTED_SCREENSHOT_DIMENSIONS)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
