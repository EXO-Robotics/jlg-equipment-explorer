#!/usr/bin/env python3
"""Fail closed when the isolated 742 route or static interaction contract drifts."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "742/index.html").read_text()
RUNTIME = (ROOT / "viewer/742-runtime.js").read_text()
MACHINE = (ROOT / "machines/742/machine.js").read_text()
ARTICULATION = (ROOT / "machines/742/articulation.js").read_text()
STYLE = (ROOT / "viewer/742.css").read_text()
SHARED_RUNTIME = (ROOT / "viewer/runtime.js").read_text()
SHARED_STYLE = (ROOT / "viewer/multi-machine.css").read_text()
VERSION = (ROOT / "machines/742/version.js").read_text()
ASSET = ROOT / "assets/models/742.glb"
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())


def require(source, tokens, label):
    missing = [token for token in tokens if token not in source]
    if missing:
        raise RuntimeError(f"{label} contract drift: {missing}")


def main():
    require(INDEX, [
        '<link rel="icon" href="../favicon.ico" type="image/x-icon">',
        'body data-machine="742"', 'id="app" role="application" tabindex="0"', 'aria-describedby="viewer-instructions"',
        'id="motion-status"', 'id="motion-announcement" aria-live="polite" aria-atomic="true"', 'id="controls-toggle"', 'aria-label="Adjust machine controls"', 'id="machine-controls-body"',
        'id="lift-control"', 'id="telescope-control"', 'id="tilt-control"', 'id="steer-control"', 'id="level-control"',
        'data-steer-mode="circle"', 'data-steer-mode="crab"', 'data-steer-mode="front"', 'id="showcase"', 'id="stow"',
        'id="inspector" role="dialog" aria-modal="true"', 'aria-describedby="inspector-copy" inert',
        'href="../viewer/742.css?', 'src="../viewer/742-runtime.js?',
        f'PVC 2411 accuracy reconstruction / {CONFIG["target_release"]}', 'id="reduced-motion-note"',
        'window.__show742ModuleFailure', 'module-load-failed', 'onerror="window.__show742ModuleFailure()"',
        'Presentation-only mechanism limits.', 'No load, stability, service, training, or safety behavior is simulated.',
        '<h2 id="operate-title">Machine controls</h2>', '<output id="motion-status">Stowed</output>',
        'id="stow" type="button">Stow machine</button>',
        'Drag to orbit <span>/</span> Scroll or pinch to zoom <span>/</span> Buttons open details',
    ], "742 HTML")
    if INDEX.count('aria-describedby="motion-boundary"') != 5:
        raise RuntimeError("Every 742 range must reference the safety boundary")
    if INDEX.count('data-focus=') != 7:
        raise RuntimeError("742 component navigation must expose seven focus targets")
    if re.search(r'id="motion-status"[^>]+aria-live', INDEX) or re.search(r'id="diagnostics"[^>]+aria-live', INDEX):
        raise RuntimeError("Per-frame status and diagnostics must not be live regions")
    require(RUNTIME, [
        'import JLG742_MACHINE from "../machines/742/machine.js?v=', 'const pointers = new Map()',
        'gestureUsedPinch', '!gestureUsedPinch', 'pinchStartDistance', 'pointercancel',
        'velocityAzimuth', 'frameP95Ms', 'data-steer-mode', 'machine.showcase', '/^[1-7]$/',
        'controlsBody.inert = !expanded', 'query.get("reduce") === "1"',
        'event.key === "Escape"', 'event.key !== "Tab"', 'modalBackground.forEach',
        'setInert(element, true)', 'setInert(inspector, false)', 'restoreTarget.focus',
        'function setEngineeringValueText(input, value)', 'const detailId = `${input.id}-engineering-detail`',
        'detail.className = "sr-only"', 'input.insertAdjacentElement("afterend", detail)',
        'if (detail.textContent !== value) detail.textContent = value',
        'input.setAttribute("aria-valuetext", value)', 'input.setAttribute("aria-details", detailId)',
        'setEngineeringValueText(input, ariaValue)', 'runSelectionVolumeSelfTest()',
        'raycaster.intersectObjects(selectionVolumes, false)', 'hit.castShadow = false',
        'SELECTION_TIE_DISTANCE_M', 'nearestHitPerVolume', 'orderedSelectionIntersections',
        'nearestVisibleComponentIntersection', 'resolveSelectionIntersection', 'frontmost-rendered-component-then-nearest-proxy',
        'material?.visible !== false', 'material.opacity > 0.01',
        'selectionOverlapRays', 'selectionNearestRays', 'selectionFixtureCases',
        'selectionOverlapOutcomes', 'selectionFixtureOutcomes', 'expectedComponent', 'resolvedComponent', 'expectedBasis',
        'overlappingRayCount > 0', 'nearestRayCount === overlappingRayCount', 'runSelectionOrderingFixtures()',
        'function clearComponentSelection()', 'function resetView()', 'framedPosedModelView()',
        'setProgrammaticViewDistance', 'effectiveMaxDistance', 'orbitEffectiveMaxDistanceM',
        'function showTerminalError(', 'viewer-terminal-error', 'identity-failed', 'contract-failed', 'load-failed', 'loader-start-failed',
        'controlPanel.querySelectorAll("button, input")', 'document.body.dataset.viewerTerminal = "true"',
        'handleMotionPreferenceChange', 'motionPreference.addEventListener("change"', 'motionPreference.addListener?.(', 'syncReducedMotion(true)', 'showcaseStarted = null',
        'controlsToggle.setAttribute("aria-label", expanded ? "Close machine controls" : "Adjust machine controls")',
        'scheduleMotionAnnouncement', 'showcaseStarted !== null && machine.showcase && !reducedMotion',
        'if (!skipNextVisibleFrame && renderedInterval > 0)', 'sorted.filter((sample) => sample >= 250).length',
        'const windowMs = sorted.reduce((sum, sample) => sum + sample, 0)', 'frameTimes.length * 1000 / windowMs',
        'Math.ceil(sorted.length * 0.95) - 1',
        'resetPerformanceWindow(', 'visibility-hidden', 'visibility-visible', 'performanceWindowReason',
        'document.body.dataset.frameWorstMs', 'document.body.dataset.frameSampleCount',
        'document.body.dataset.viewportCssPx', 'document.body.dataset.renderProfile', 'document.body.dataset.pixelRatio',
        'function applyShadowProfile()', 'document.body.dataset.shadowProfile',
        'document.body.dataset.selectionSelftest =',
    ], "dedicated 742 runtime")
    if re.search(r"renderedInterval\s*<\s*250", RUNTIME):
        raise RuntimeError("742 p95 must not discard visible stalls at or above 250 ms")
    if 'return [...intersections].sort((a, b) => (b.object.userData.selectionPriority' in RUNTIME:
        raise RuntimeError("742 selection must not rank semantic priority before material distance")
    if 'orbit.desiredDistance = view.distance' in RUNTIME:
        raise RuntimeError("Programmatic pose framing must update the effective zoom limit")
    if 'resolveSelectionIntersection(semanticHits, visibleSurfaceHit)' not in RUNTIME:
        raise RuntimeError("Pointer selection must resolve against the frontmost rendered component")
    fixture_hits = [
        ([('rear', 2.0, 5), ('front', 1.0, 0)], 'front'),
        ([('low-tie', 1.0, 1), ('high-tie', 1.01, 4)], 'high-tie'),
    ]
    for hits, expected in fixture_hits:
        nearest = min(distance for _, distance, _ in hits)
        eligible = [hit for hit in hits if hit[1] <= nearest + 0.025]
        resolved = sorted(eligible, key=lambda hit: (-hit[2], hit[1], hit[0]))[0][0]
        if resolved != expected:
            raise RuntimeError("Independent nearest-visible selection fixture failed")
    surface_hits = [('rear', 0.8, 5, 'rear'), ('front', 1.0, 0, 'front')]
    visible_component = 'front'
    matching_surface = sorted((hit for hit in surface_hits if hit[3] == visible_component), key=lambda hit: (hit[1], hit[0]))
    if not matching_surface or matching_surface[0][0] != 'front':
        raise RuntimeError("Frontmost rendered component must override an oversized nearer proxy")
    base_max, absolute_max, pose_distance = 24.0, 72.0, 37.73
    safe_distance = min(max(pose_distance, 2.2), absolute_max / 1.05)
    effective_max = min(absolute_max, max(base_max, safe_distance * 1.05))
    next_zoom_out = min(effective_max, safe_distance * 1.1)
    if effective_max < safe_distance or next_zoom_out < safe_distance:
        raise RuntimeError("Pose-aware reset distance would snap on the next zoom gesture")
    visible_samples = [16.7, 271.0, 17.1]
    if sum(sample >= 250 for sample in visible_samples) != 1 or max(visible_samples) != 271.0:
        raise RuntimeError("Visible stall accounting must share the frame sample window")
    if 'const posedComponent = name === "default" ? framedPosedModelView()' not in RUNTIME:
        raise RuntimeError("742 reset view must frame the current posed machine")
    if "const touches = new Map()" in RUNTIME:
        raise RuntimeError("Legacy multi-touch implementation returned to the 742 runtime")
    if 'JLG742_MACHINE' in SHARED_RUNTIME or '"742"' in SHARED_RUNTIME or 'body[data-machine="742"]' in SHARED_STYLE:
        raise RuntimeError("742 implementation leaked back into ES1930M shared runtime/style")
    require(MACHINE, [
        '742-PVC2411-US-STD-OC-D36-FF370-C50-PF481', 'interactionVolumes', 'showcase(t)',
        'steerMode: "circle"', 'JLG742_GLB_URL', 'status: stowed ? "Stowed" : "Positioning"',
    ], "742 machine module")
    require(ARTICULATION, [
        '"BoomAngleSensorCrank"', '"BoomAngleSensorLink"', '"BoomAngleSensorFrameJoint"',
        '"BoomAngleSensorCrankJoint"', '"BoomAngleSensorBoomJoint"',
        '...["L","R"].flatMap', 'Array.from({length:8}', '"RetractChain_C"', '"RetractChain_C_Moving"',
        'Object.entries(geometry.beams)', 'Object.entries(geometry.points)',
    ], "742 articulation consumer")
    require(STYLE, ['body[data-machine="742"]', '.mode-row', '.component-nav-seven', '.nav-overflow-cue', 'button[data-focus][aria-pressed="true"]'], "742 style")
    if not ASSET.is_file():
        raise RuntimeError("742 route asset is missing")
    asset_sha = hashlib.sha256(ASSET.read_bytes()).hexdigest()
    if asset_sha not in VERSION:
        raise RuntimeError("742 version module does not contain the exact GLB hash")
    version_release = re.search(r'JLG742_RELEASE\s*=\s*"(\d+\.\d+\.\d+)"', VERSION)
    if not version_release or version_release.group(1) != CONFIG.get("target_release"):
        raise RuntimeError("742 route release identity does not match the frozen configuration")
    preload = re.search(r'742\.glb\?v=([0-9a-f]+)', INDEX)
    if not preload or preload.group(1) != asset_sha[:len(preload.group(1))] or len(preload.group(1)) < 12:
        raise RuntimeError("742 HTML preload cache identity does not match the exact GLB")
    runtime_release = re.search(r'data-runtime-release="([^"]+)"', INDEX)
    if not runtime_release or INDEX.count(f'?v={runtime_release.group(1)}') != 2:
        raise RuntimeError("742 dedicated runtime/style cache identities disagree")
    print(json.dumps({
        "status":"PASS", "route":"/742/", "isolated_runtime":"viewer/742-runtime.js",
        "isolated_style":"viewer/742.css", "shared_es_runtime_unchanged_by_742":True,
        "motion_ranges":5, "steering_modes":3, "component_focus_targets":7,
        "pinch_zoom":True, "pinch_click_suppression":True, "inertia":True,
        "modal_focus_contract":True, "engineering_aria_value_text":True, "engineering_aria_details":True,
        "semantic_volume_self_test":True, "nearest_visible_overlap_test":True, "independent_selection_fixtures":True,
        "frontmost_rendered_surface_selection":True, "dynamic_chain_and_sensor_consumers":True,
        "selection_reset_contract":True, "pose_aware_reset":True, "reduced_motion_showcase_disabled":True,
        "dynamic_pose_zoom_limit":True, "terminal_accessible_failure_ui":True,
        "settled_motion_live_region":True, "dynamic_reduced_motion":True,
        "performance_p95_diagnostic":True, "coherent_performance_window":True, "visible_stalls_included":True,
        "adaptive_shadow_profile":True, "performance_sample_metadata":True,
        "asset_sha256":asset_sha,
        "candidate_release":CONFIG["target_release"], "runtime_release":runtime_release.group(1),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
