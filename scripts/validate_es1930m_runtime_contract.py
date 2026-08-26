#!/usr/bin/env python3
"""Check duplicated browser constants and motion invariants against mechanism.json."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPACT_VIEWPORT_QUERY = '(max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)'


def compact_viewport(width: int, height: int) -> bool:
    return width <= 800 or (height <= 500 and width > height and width <= 1000)


spec = json.loads((ROOT / "machines/es1930m/mechanism.json").read_text())
source = (ROOT / "machines/es1930m/articulation.js").read_text()
viewer_source = (ROOT / "viewer/runtime.js").read_text()
style_source = (ROOT / "viewer.css").read_text()
route_source = (ROOT / "viewer/presentation-route.mjs").read_text()
html_source = (ROOT / "es1930m/index.html").read_text()
machine_tabs_style = (ROOT / "viewer/machine-tabs.css").read_text()

expected = {
    "levels": spec["solver"]["level_count"],
    "armLength": spec["solver"]["arm_pin_center_length_m"],
    "basePivotY": spec["solver"]["base_pivot_height_m"],
    "deckOffsetY": spec["solver"]["deck_floor_offset_above_upper_pivots_m"],
    "stowedDeckY": spec["solver"]["stowed_deck_floor_height_m"],
    "indoorDeckY": spec["solver"]["indoor_deck_floor_height_m"],
    "outdoorDeckY": spec["solver"]["outdoor_deck_floor_height_m"],
    "extensionTravel": spec["deck_extension"]["travel_m"],
    "railFixedFrontX": spec["deck_extension"]["fixed_outer_rail_front_x_m"],
    "railMovingRearX": spec["deck_extension"]["moving_inner_rail_rear_x_m"],
    "railMinimumOverlap": spec["deck_extension"]["minimum_deployed_overlap_m"],
    "railMinimumLateralClearance": spec["deck_extension"]["minimum_nested_lateral_clearance_m"],
    "cylinderStroke": spec["lift_cylinder"]["published_stroke_m"],
    "steeringCylinderStrokeEachDirection": spec["steering"]["cylinder_stroke_each_direction_m"],
    "rearFixedX": spec["slides"]["rear_fixed_x_m"],
}
for name, value in expected.items():
    match = re.search(rf"\b{name}:\s*(-?[0-9.]+)", source)
    if not match or abs(float(match.group(1)) - float(value)) > 1e-9:
        raise RuntimeError(f"Runtime/mechanism constant drift: {name}")

required_motion = [
    "slide.position.y = state.boundaries.at(-1).front.y",
    "for (const spindle of rig.steerSpindles) spindle.rotation.y = 0",
    "selfTestES1930MRig",
    "cylinderUpperOffset",
    "kickerRollerOffset",
    "extension guard opening",
    "extension guard parent drift",
    "extension guard solid intersection",
    "new THREE.Box3().setFromObject(pair.moving)",
]
for snippet in required_motion:
    if snippet not in source:
        raise RuntimeError(f"Runtime motion contract missing: {snippet}")
required_presentation = [
    "steering and wheel motion are reconstructed; this is not a machine capability.",
    "setPresentationRouteEnabled(false, { reset: true })",
    "state.steer = next.sample.steer",
    "rig.root.rotation.y = sample.heading",
    "rig.steerSpindles[0].rotation.y = sample.steerRight",
    "rig.wheelRollPivots[index].rotation.z = presentationRoute.wheelRotations[index]",
    "orbit.desiredTarget.set(sample.x, 1.05, sample.z)",
    "const ASSET_LOAD_TIMEOUT_MS = 15000",
    "function showTerminalError(error, message, source = \"runtime-failed\")",
    'showTerminalError(error, `The ${machine.identity.model} asset failed its hierarchy or motion contract.',
    '"load-timeout"',
    '"load-failed"',
    '"loader-start-failed"',
    'document.querySelector(".interface")?.setAttribute("inert", "")',
    'controlPanel.querySelectorAll("button, input")',
    "if (terminalFailure) return",
    "function syncReducedMotion(announce = false)",
    'motionPreference.addEventListener("change", handleMotionPreferenceChange)',
    "setPresentationRouteEnabled(false)",
    "setEngineeringValueText(input, ariaValue)",
    'input.setAttribute("aria-details", detailId)',
    "document.body.dataset.runtimeFrameCount",
    "document.body.dataset.terminalFrameCount",
    "document.body.dataset.terminalFrameSource",
    'metres platform height',
    "function setOutputValue(output, value)",
    'document.body.dataset.viewerRuntimeActive = "true"',
    '__EQUIPMENT_EXPLORER_TEST_FAULT__ === "asset-contract"',
]
for snippet in required_presentation:
    if snippet not in viewer_source:
        raise RuntimeError(f"Presentation route contract missing: {snippet}")
for snippet in ("radiusX: 8.2", "radiusZ: 6.0", "Math.tanh", "const curvature = -planarCurvature", "speedMps: 0.72", "wheelbaseM: 1.07", "wheelRadiusM: 0.13"):
    if snippet not in route_source:
        raise RuntimeError(f"Figure-eight math contract missing: {snippet}")
for snippet in ('aria-label="Autonomous presentation route"', "Drive mode", "Manual", 'id="error" role="alert" aria-live="assertive" tabindex="-1"', '../viewer/runtime.js?v=1.0.12', '../viewer.css?v=1.0.11', '../viewer/multi-machine.css?v=1.0.9', '../viewer/machine-tabs.css?v=1.0.0', '<nav class="machine-tabs" aria-label="Machine showcases">', '<a href="../" aria-label="JLG 600S boom lift showcase">600S</a>', '<a href="../742/" aria-label="JLG 742 telehandler showcase">742</a>', '<a href="../es1930m/" aria-current="page" aria-label="JLG ES1930M scissor lift showcase">ES1930M</a>', "window.__showES1930MBootstrapFailure", 'dataset.viewerRuntimeActive === "true"', "countBootFrame", "dataset.terminalFrameCount", "dataset.terminalFrameSource", 'onerror="window.__showES1930MBootstrapFailure', "onload=\"document.body.dataset.viewerModuleLoaded='true'\""):
    if snippet not in html_source:
        raise RuntimeError(f"600S-aligned control-board naming missing: {snippet}")
if '<link rel="icon" href="../favicon.ico" type="image/x-icon">' not in html_source:
    raise RuntimeError("ES1930M project-Pages favicon route drift")
if html_source.count('aria-current="page"') != 1 or 'min-height: 42px' not in machine_tabs_style:
    raise RuntimeError("ES1930M shared machine-navigation contract drift")
if 'class="component-nav' in html_source or 'data-focus=' in html_source:
    raise RuntimeError("Removed component Explore tabs returned to the ES1930M route")
for snippet in ('"Auto loop"', '"Auto"', '"Manual"', 'dataset.autonomyMode'):
    if snippet not in viewer_source:
        raise RuntimeError(f"600S-aligned runtime naming missing: {snippet}")
if 'id="diagnostics" hidden aria-live=' in html_source:
    raise RuntimeError("Continuously sampled diagnostics must not be a live region")
if "const reducedMotion = query.get" in viewer_source:
    raise RuntimeError("Reduced-motion preference must remain live after startup")
for import_path, release in (("machine.js", "1.0.9"), ("pointer-gestures.mjs", "1.0.11"), ("presentation-route.mjs", "1.0.9")):
    if f'{import_path}?v={release}' not in viewer_source:
        raise RuntimeError(f"ES1930M runtime cache identity drift: {import_path}")
for snippet in ("directOrbitDragDelta", "const drag = directOrbitDragDelta(dx, dy, pointer.pointerType)"):
    if snippet not in viewer_source:
        raise RuntimeError(f"ES1930M direct mouse-orbit contract missing: {snippet}")
for snippet in (f'const COMPACT_VIEWPORT_QUERY = "{COMPACT_VIEWPORT_QUERY}"', "matchMedia(COMPACT_VIEWPORT_QUERY)"):
    if snippet not in viewer_source:
        raise RuntimeError(f"ES1930M compact responsive contract missing: {snippet}")
if f"@media {COMPACT_VIEWPORT_QUERY}" not in style_source:
    raise RuntimeError("ES1930M compact CSS query drift")
if not compact_viewport(844, 390) or compact_viewport(1280, 720):
    raise RuntimeError("ES1930M responsive fixtures drifted")
print(json.dumps({"status": "PASS", "constants_checked": len(expected), "motion_contracts_checked": len(required_motion), "presentation_contracts_checked": len(required_presentation) + 7, "control_board_names_checked": 7, "compact_short_landscape": [844, 390], "desktop_expanded": [1280, 720]}, indent=2))
