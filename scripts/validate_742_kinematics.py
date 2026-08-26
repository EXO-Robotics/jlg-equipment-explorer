#!/usr/bin/env python3
"""Validate the 742 presentation hierarchy across honest multidimensional poses.

This is a geometry/continuity validator for the independently reconstructed
showcase. It is deliberately not a manufacturer dynamics, capacity, stability,
interlock, service, or safety model.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb


ROOT = Path(__file__).resolve().parents[1]
MECH = json.loads((ROOT / "machines/742/mechanism.json").read_text())
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())
GLB = ROOT / "assets/models/742.glb"

PIVOT = tuple(MECH["boom"]["pivot_m"][:2])
MID_ORIGIN = MECH["boom"]["mid_authored_origin_m"]
FLY_ORIGIN = MECH["boom"]["fly_authored_origin_m"]
CARRIAGE_ORIGIN = tuple(MECH["boom"]["carriage_authored_origin_m"][:2])
FORK_X = (0.0, 1.2192)
FORK_Y = (-0.71, -0.65)  # blade bottom / upper load surface
FORK_Z = (-0.391, 0.391)  # two 102 mm blades centered at +/-0.34 m
STEER_VALUES = (-1.0, -0.5, 0.0, 0.5, 1.0)
STEER_MODES = ("circle", "crab", "front")
TILT_DEGREES = (-5.0, -2.5, 0.0, 3.0, 6.0, 9.0, 12.0)
LEVEL_DEGREES = tuple(-10.0 + 2.5 * value for value in range(9))

DYNAMIC_PARENT = {
    "LiftCylinderBarrel": "LiftCylinder", "LiftCylinderRod": "LiftCylinder",
    "LiftHose_0_0": "LiftCylinder", "LiftHose_1_2": "LiftCylinder",
    "TelescopeCylinderBarrel": "BoomBase", "TelescopeCylinderRod": "BoomBase",
    "CompensationCylinderBarrel": "LiftCylinder", "CompensationCylinderRod": "LiftCylinder",
    "BoomHose_0_0": "BoomBase", "BoomHose_3_2": "BoomBase",
    "ExtendChain_L": "BoomBase", "RetractChain_C": "BoomBase",
    "CarriageTiltCylinderBarrel": "BoomFly", "CarriageTiltCylinderRod": "BoomFly",
    "CarriageTiltLink": "BoomFly", "FrameLevelCylinderBarrel": "742_ROOT",
    "FrameLevelCylinderRod": "742_ROOT", "RearAxleStabilizerBarrel": "RearAxleStabilizerCylinder",
    "RearAxleStabilizerRod": "RearAxleStabilizerCylinder",
    "FrontSteerCylinderBarrel": "FrontSteerCylinder", "FrontSteerCylinderRodLeft": "FrontSteerCylinder",
    "FrontSteerCylinderRodRight": "FrontSteerCylinder", "RearSteerCylinderBarrel": "RearSteerCylinder",
    "RearSteerCylinderRodLeft": "RearSteerCylinder", "RearSteerCylinderRodRight": "RearSteerCylinder",
    "BoomAngleSensorLink": "LiftCylinder",
}
POINT_PARENT = {"BoomAngleSensorBoomJoint": "LiftCylinder"}


def rotate(point: tuple[float, float], angle: float) -> tuple[float, float]:
    x, y = point
    return math.cos(angle) * x - math.sin(angle) * y, math.sin(angle) * x + math.cos(angle) * y


def wheel_angles(steer: float, mode: str) -> dict[str, float]:
    inner = abs(steer) * math.radians(MECH["steering"]["visual_inner_limit_degrees"])
    if inner < 1e-9:
        return dict.fromkeys(("FL", "FR", "RL", "RR"), 0.0)
    sign = 1 if steer > 0 else -1
    if mode == "crab":
        return dict.fromkeys(("FL", "FR", "RL", "RR"), sign * inner)
    axle_span = MECH["steering"]["wheelbase_m"] / (2 if mode == "circle" else 1)
    track = MECH["steering"]["wheel_center_track_m"]
    center_radius = track / 2 + axle_span / math.tan(inner)
    outer = math.atan(axle_span / (center_radius + track / 2))
    if mode == "front":
        return ({"FL": outer, "FR": inner, "RL": 0, "RR": 0} if sign > 0
                else {"FL": -inner, "FR": -outer, "RL": 0, "RR": 0})
    return ({"FL": outer, "FR": inner, "RL": -outer, "RR": -inner} if sign > 0
            else {"FL": -inner, "FR": -outer, "RL": inner, "RR": outer})


def fork_vertices(angle: float, telescope: float, tilt: float, level: float):
    travel = telescope * MECH["boom"]["mid_visual_travel_m"]
    reach = MID_ORIGIN + travel + FLY_ORIGIN + travel + CARRIAGE_ORIGIN[0]
    cx, cy = rotate((reach, CARRIAGE_ORIGIN[1]), angle)
    cx += PIVOT[0]
    cy += PIVOT[1]
    tilt_radians = math.radians(tilt)
    level_radians = math.radians(level)
    for x in FORK_X:
        for y in FORK_Y:
            tx, ty = rotate((x, y), tilt_radians)
            for z in FORK_Z:
                leveled_y = 0.82 + math.cos(level_radians) * (cy + ty - 0.82) - math.sin(level_radians) * z
                yield cx + tx, leveled_y, z


def validate_glb_hierarchy(failures: list[str]):
    document, _ = load_glb(GLB)
    nodes = document.get("nodes") or []
    by_name, parents = index_nodes(nodes)
    for name, expected_parent in DYNAMIC_PARENT.items():
        if name not in by_name:
            failures.append(f"posed GLB is missing {name}")
            continue
        parent_index = parents.get(by_name[name])
        actual_parent = nodes[parent_index].get("name") if parent_index is not None else None
        if actual_parent != expected_parent:
            failures.append(f"{name} parent is {actual_parent}, expected {expected_parent}")
        extras = nodes[by_name[name]].get("extras") or {}
        if extras.get("authored_length_m", 0) <= 0:
            failures.append(f"{name} lacks an authored-length rig contract")
    for name, expected_parent in POINT_PARENT.items():
        if name not in by_name:
            failures.append(f"posed GLB is missing {name}")
            continue
        parent_index = parents.get(by_name[name])
        actual_parent = nodes[parent_index].get("name") if parent_index is not None else None
        if actual_parent != expected_parent:
            failures.append(f"{name} parent is {actual_parent}, expected {expected_parent}")
    for required in ("ExtendChain_L", "ExtendChain_R", "RetractChain_C", "BoomAngleSensorBody", "BoomAngleSensorLink",
                     "BoomRigidTube_0", "BoomRigidTube_1", "BoomRigidTube_2"):
        if required not in by_name:
            failures.append(f"posed GLB is missing required mechanism cue {required}")


def main():
    failures: list[str] = []
    validate_glb_hierarchy(failures)
    sample_count = 0
    min_fork_y = math.inf
    max_fork_surface_y = -math.inf
    min_base_mid_overlap = math.inf
    min_mid_fly_overlap = math.inf
    min_lift_cylinder_length = math.inf
    max_lift_cylinder_length = -math.inf
    max_ackermann_error = 0.0
    outside_turn_radius = 0.0
    min_compensation_length = math.inf
    max_compensation_length = -math.inf
    min_tilt_length = math.inf
    max_tilt_length = -math.inf
    min_frame_sway_length = math.inf
    max_frame_sway_length = -math.inf
    min_ras_length = math.inf
    max_ras_length = -math.inf
    max_endpoint_step = 0.0
    previous_grid: dict[tuple[int, int], tuple[float, float]] = {}

    for lift_index in range(21):
        lift = lift_index / 20
        angle = math.radians(3 + 66 * lift)
        for telescope_index in range(21):
            telescope = telescope_index / 20
            travel = telescope * MECH["boom"]["mid_visual_travel_m"]
            min_base_mid_overlap = min(min_base_mid_overlap, 5.525 - (MID_ORIGIN + travel - 0.025))
            min_mid_fly_overlap = min(min_mid_fly_overlap, 5.325 - (FLY_ORIGIN + travel - 0.025))

            carriage_reach = MID_ORIGIN + travel + FLY_ORIGIN + travel + CARRIAGE_ORIGIN[0]
            endpoint = rotate((carriage_reach, CARRIAGE_ORIGIN[1]), angle)
            endpoint = endpoint[0] + PIVOT[0], endpoint[1] + PIVOT[1]
            previous_grid[(lift_index, telescope_index)] = endpoint
            for neighbor in ((lift_index - 1, telescope_index), (lift_index, telescope_index - 1)):
                if neighbor in previous_grid:
                    prior = previous_grid[neighbor]
                    max_endpoint_step = max(max_endpoint_step, math.hypot(endpoint[0] - prior[0], endpoint[1] - prior[1]))

            lift_anchor_delta = rotate((2.412, -0.20), angle)
            lift_anchor = PIVOT[0] + lift_anchor_delta[0], PIVOT[1] + lift_anchor_delta[1]
            lift_length = math.hypot(lift_anchor[0] + 1.80, lift_anchor[1] - 0.70)
            min_lift_cylinder_length = min(min_lift_cylinder_length, lift_length)
            max_lift_cylinder_length = max(max_lift_cylinder_length, lift_length)

            compensation_delta = rotate((0.80, 0.30), angle)
            compensation_anchor = PIVOT[0] + compensation_delta[0], PIVOT[1] + compensation_delta[1]
            compensation_length = math.hypot(compensation_anchor[0] + 2.0, compensation_anchor[1] - 1.5)
            min_compensation_length = min(min_compensation_length, compensation_length)
            max_compensation_length = max(max_compensation_length, compensation_length)

            for tilt in TILT_DEGREES:
                for level in LEVEL_DEGREES:
                    vertices = tuple(fork_vertices(angle, telescope, tilt, level))
                    min_fork_y = min(min_fork_y, *(vertex[1] for vertex in vertices))
                    if lift_index == 20 and telescope_index == 20 and tilt == 0 and level == 0:
                        # Every second Y entry is the upper fork load surface.
                        max_fork_surface_y = max(max_fork_surface_y, *(vertex[1] for vertex in vertices))
                    carriage_angle = math.radians(tilt) - angle
                    moving = rotate((-0.1494, 0.3705), carriage_angle)
                    tilt_length = math.hypot(CARRIAGE_ORIGIN[0] + moving[0] - 4.216,
                                             CARRIAGE_ORIGIN[1] + moving[1] + 1.21)
                    min_tilt_length = min(min_tilt_length, tilt_length)
                    max_tilt_length = max(max_tilt_length, tilt_length)

                    level_radians = math.radians(level)
                    def rolled(anchor):
                        x, y, z = anchor
                        return (x, 0.82 + math.cos(level_radians) * (y - 0.82) - math.sin(level_radians) * z,
                                math.sin(level_radians) * (y - 0.82) + math.cos(level_radians) * z)
                    frame_length = math.dist((-0.0133, 0.6054, 0.4865), rolled((0.1121, 1.2428, 1.1607)))
                    ras_length = math.dist((-1.95, 0.64, -0.45), rolled((-1.55, 0.92, -0.65)))
                    min_frame_sway_length = min(min_frame_sway_length, frame_length)
                    max_frame_sway_length = max(max_frame_sway_length, frame_length)
                    min_ras_length = min(min_ras_length, ras_length)
                    max_ras_length = max(max_ras_length, ras_length)
                    for mode in STEER_MODES:
                        for steer in STEER_VALUES:
                            angles = wheel_angles(steer, mode)
                            sample_count += 1
                            if mode != "crab" and steer:
                                inner = max(abs(value) for value in angles.values())
                                nonzero = sorted(abs(value) for value in angles.values() if abs(value) > 1e-9)
                                outer = nonzero[0]
                                axle_span = MECH["steering"]["wheelbase_m"] / (2 if mode == "circle" else 1)
                                track = MECH["steering"]["wheel_center_track_m"]
                                center_from_inner = track / 2 + axle_span / math.tan(inner)
                                center_from_outer = axle_span / math.tan(outer) - track / 2
                                max_ackermann_error = max(max_ackermann_error, abs(center_from_inner - center_from_outer))
                                if mode == "circle" and abs(steer) == 1:
                                    outside_turn_radius = max(outside_turn_radius, math.hypot(
                                        center_from_inner + track / 2, MECH["steering"]["wheelbase_m"] / 2))

    required_overlap = MECH["collision_proxies"]["minimum_boom_overlap_m"]
    if min_base_mid_overlap < required_overlap or min_mid_fly_overlap < required_overlap:
        failures.append("nested boom overlap fell below the reconstructed proxy")
    if min_fork_y < MECH["collision_proxies"]["minimum_fork_y_m"] - 1e-6:
        failures.append(f"fork blade crossed flat-floor clearance: {min_fork_y:.6f} m")
    target_height = CONFIG["published_performance"]["maximum_lift_height_m"]
    if abs(max_fork_surface_y - target_height) > 0.05:
        failures.append(f"level fork surface is {max_fork_surface_y:.4f} m, not {target_height:.3f} m +/- 0.05 m")
    if max_ackermann_error > 1e-9:
        failures.append(f"Ackermann center mismatch: {max_ackermann_error}")
    circle_max = wheel_angles(1.0, "circle")
    front_max = wheel_angles(1.0, "front")
    if not (circle_max["FR"] > circle_max["FL"] > 0 and circle_max["RR"] < circle_max["RL"] < 0):
        failures.append("positive circle-steer mapping must be FR inner, FL outer, RR opposite inner, RL opposite outer")
    if not (front_max["FR"] > front_max["FL"] > 0 and front_max["RL"] == front_max["RR"] == 0):
        failures.append("positive front-steer mapping must be FR inner, FL outer, rear neutral")
    strokes = MECH["hydraulic_cylinder_strokes_m"]
    lift_usage = max_lift_cylinder_length - min_lift_cylinder_length
    compensation_usage = max_compensation_length - min_compensation_length
    tilt_usage = max_tilt_length - min_tilt_length
    frame_usage = max_frame_sway_length - min_frame_sway_length
    ras_usage = max_ras_length - min_ras_length
    for label, actual, expected, tolerance in (
        ("lift", lift_usage, strokes["lift"], 0.012),
        ("compensation", compensation_usage, strokes["compensation_master"], 0.012),
        ("head tilt", tilt_usage, strokes["head_tilt_slave"], 0.012),
        ("frame sway", frame_usage, strokes["frame_sway"], 0.006),
    ):
        if abs(actual - expected) > tolerance:
            failures.append(f"{label} visual pin-distance delta {actual:.4f} m differs from evidence stroke {expected:.4f} m")
    if abs(MECH["boom"]["mid_visual_travel_m"] - strokes["telescope"]) > 1e-9:
        failures.append("telescope visual travel drifted from evidence stroke")
    if abs(outside_turn_radius - MECH["steering"]["outside_turning_radius_crosscheck_m"]) > 0.08:
        failures.append(f"circle outside wheel-center radius {outside_turn_radius:.3f} m misses published cross-check")

    reach_pose = MECH["reach_pose"]
    reach_angle = math.radians(reach_pose["boom_angle_degrees"])
    reach_travel = reach_pose["telescope_fraction"] * MECH["boom"]["mid_visual_travel_m"]
    reach_axis = MID_ORIGIN + reach_travel + FLY_ORIGIN + reach_travel + CARRIAGE_ORIGIN[0]
    reach_point_x, _ = rotate((reach_axis, CARRIAGE_ORIGIN[1]), reach_angle)
    forward_reach = PIVOT[0] + reach_point_x + reach_pose["load_center_m"] - reach_pose["front_tire_plane_x_m"]
    if abs(forward_reach - reach_pose["published_forward_reach_m"]) > 0.02:
        failures.append(f"24-inch load-center reach {forward_reach:.4f} m misses published 8.86 m")
    if abs(CONFIG["visual_motion_limits"]["frame_level_degrees"][1]) != CONFIG["published_performance"]["frame_level_degrees_each_side"]:
        failures.append("frame-level presentation limit drift")
    if failures:
        raise RuntimeError("; ".join(sorted(set(failures))))

    print(json.dumps({
        "status": "PASS",
        "configuration_id": CONFIG["configuration_id"],
        "unique_multidimensional_state_samples": sample_count,
        "sample_axes": {
            "lift": 21, "telescope": 21, "tilt": len(TILT_DEGREES),
            "frame_level": len(LEVEL_DEGREES), "steer": len(STEER_VALUES), "steering_modes": len(STEER_MODES),
        },
        "minimum_base_mid_overlap_m": min_base_mid_overlap,
        "minimum_mid_fly_overlap_m": min_mid_fly_overlap,
        "minimum_fork_blade_y_m": min_fork_y,
        "maximum_level_fork_surface_y_m": max_fork_surface_y,
        "published_maximum_lift_height_m": target_height,
        "lift_cylinder_pin_distance_range_m": [min_lift_cylinder_length, max_lift_cylinder_length],
        "evidence_stroke_usage_m": {
            "lift": lift_usage, "telescope": MECH["boom"]["mid_visual_travel_m"],
            "compensation_master": compensation_usage, "head_tilt_slave": tilt_usage,
            "frame_sway": frame_usage, "rear_axle_stabilization_visible_subset": ras_usage,
        },
        "rear_axle_stabilization_published_stroke_m": strokes["rear_axle_stabilization"],
        "rear_axle_stabilization_usage_boundary": "only frame-level-induced endpoint travel is shown; free/slow/locked RAS states are not simulated",
        "maximum_ackermann_center_error_m": max_ackermann_error,
        "circle_outside_wheel_center_radius_m": outside_turn_radius,
        "positive_circle_max_wheel_angles_degrees": {key: math.degrees(value) for key, value in circle_max.items()},
        "positive_front_max_wheel_angles_degrees": {key: math.degrees(value) for key, value in front_max.items()},
        "published_outside_turning_radius_crosscheck_m": MECH["steering"]["outside_turning_radius_crosscheck_m"],
        "maximum_reach_pose": {"boom_angle_degrees": reach_pose["boom_angle_degrees"], "telescope_fraction": 1.0,
                                "load_center_m": reach_pose["load_center_m"], "forward_reach_m": forward_reach},
        "maximum_adjacent_endpoint_step_m": max_endpoint_step,
        "dynamic_hierarchy_nodes_checked": sorted(DYNAMIC_PARENT),
        "dynamic_point_nodes_checked": sorted(POINT_PARENT),
        "boundary": "independent visual geometry and endpoint-continuity solver only; not manufacturer dynamics, load, stability, interlock, service, or safety authority",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
