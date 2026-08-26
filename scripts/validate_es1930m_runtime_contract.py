#!/usr/bin/env python3
"""Check duplicated browser constants and motion invariants against mechanism.json."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "machines/es1930m/mechanism.json").read_text())
source = (ROOT / "machines/es1930m/articulation.js").read_text()
viewer_source = (ROOT / "viewer/runtime.js").read_text()
route_source = (ROOT / "viewer/presentation-route.mjs").read_text()
html_source = (ROOT / "es1930m/index.html").read_text()

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
]
for snippet in required_presentation:
    if snippet not in viewer_source:
        raise RuntimeError(f"Presentation route contract missing: {snippet}")
for snippet in ("radiusX: 8.2", "radiusZ: 6.0", "Math.tanh", "const curvature = -planarCurvature", "speedMps: 0.72", "wheelbaseM: 1.07", "wheelRadiusM: 0.13"):
    if snippet not in route_source:
        raise RuntimeError(f"Figure-eight math contract missing: {snippet}")
for snippet in ('aria-label="Autonomous presentation route"', "Drive mode", "Start auto"):
    if snippet not in html_source:
        raise RuntimeError(f"600S-aligned control-board naming missing: {snippet}")
for snippet in ('"Auto loop"', '"Pause auto"', '"Resume auto"', 'dataset.autonomyMode'):
    if snippet not in viewer_source:
        raise RuntimeError(f"600S-aligned runtime naming missing: {snippet}")
print(json.dumps({"status": "PASS", "constants_checked": len(expected), "motion_contracts_checked": len(required_motion), "presentation_contracts_checked": len(required_presentation) + 7, "control_board_names_checked": 7}, indent=2))
