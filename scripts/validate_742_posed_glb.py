#!/usr/bin/env python3
"""Pose the exported 742 GLB through the production solver and measure it.

Run with Blender so the gate exercises the actual exported named nodes:
  blender --background --factory-startup --python scripts/validate_742_posed_glb.py
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "assets/models/742.glb"
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())
MECHANISM = json.loads((ROOT / "machines/742/mechanism.json").read_text())


def solve(request):
    completed = subprocess.run(
        ["node", str(ROOT / "scripts/solve_742_pose.mjs"), json.dumps(request)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def obj(name):
    found = bpy.data.objects.get(name)
    if found is None:
        raise RuntimeError(f"posed GLB is missing {name}")
    return found


def set_beam(name, endpoints):
    target = obj(name)
    start, end = (Vector(point) for point in endpoints)
    direction = end - start
    if direction.length < 1e-6:
        raise RuntimeError(f"{name} collapsed while posing actual GLB")
    target.location = (start + end) / 2
    target.rotation_mode = "QUATERNION"
    target.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    target.scale = (1, 1, direction.length / float(target.get("authored_length_m", direction.length)))


def apply_pose(pose):
    state = pose["state"]
    for name in ("BoomLiftPivot", "CarriageTiltPivot", "FrameLevelPivot",
                 "SteerPivot_FL", "SteerPivot_FR", "SteerPivot_RL", "SteerPivot_RR"):
        obj(name).rotation_mode = "XYZ"
    obj("BoomLiftPivot").rotation_euler[2] = state["boomAngle"]
    obj("BoomMid").location.x = 0.12 + state["midTranslation"]
    obj("BoomFly").location.x = 0.12 + state["flyTranslation"]
    obj("CarriageTiltPivot").rotation_euler[2] = state["carriageAngle"]
    obj("FrameLevelPivot").rotation_euler[0] = state["frameAngle"]
    for corner, angle in state["wheelAngles"].items():
        obj(f"SteerPivot_{corner}").rotation_euler[1] = angle
    for name, endpoints in pose["geometry"]["beams"].items():
        set_beam(name, endpoints)
    for name, point in pose["geometry"]["points"].items():
        obj(name).location = point
    bpy.context.view_layer.update()


def vertices(target):
    if target.type != "MESH":
        return []
    return [target.matrix_world @ vertex.co for vertex in target.data.vertices]


def named_vertices(names):
    return [point for name in names for point in vertices(obj(name))]


def posed_beam_endpoints(name):
    target = obj(name)
    authored = float(target.get("authored_length_m", 0))
    if authored <= 0:
        raise RuntimeError(f"{name} has no authored-length contract")
    return [target.matrix_local @ Vector((0, 0, -authored / 2)),
            target.matrix_local @ Vector((0, 0, authored / 2))]


def endpoint_pair_error(actual, expected):
    direct = max((actual[index] - Vector(expected[index])).length for index in (0, 1))
    reverse = max((actual[index] - Vector(expected[1 - index])).length for index in (0, 1))
    return min(direct, reverse)


def pose_contract_measurement(pose):
    apply_pose(pose)
    beam_error = max(endpoint_pair_error(posed_beam_endpoints(name), endpoints)
                     for name, endpoints in pose["geometry"]["beams"].items())
    point_error = max((obj(name).location - Vector(point)).length
                      for name, point in pose["geometry"]["points"].items())
    hose_totals = {}
    for prefix in [*[f"LiftHose_{lane}" for lane in range(2)],
                   *[f"BoomHose_{lane}" for lane in range(4)]]:
        count = 3 if prefix.startswith("Lift") else 10
        hose_totals[prefix] = sum(
            (posed_beam_endpoints(f"{prefix}_{segment}")[1] -
             posed_beam_endpoints(f"{prefix}_{segment}")[0]).length
            for segment in range(count)
        )
    steer_lengths = {name: (posed_beam_endpoints(name)[1] - posed_beam_endpoints(name)[0]).length
                     for name in ("FrontSteerBarLeft", "FrontSteerBarRight",
                                  "RearSteerBarLeft", "RearSteerBarRight")}
    rigid_tubes = [posed_beam_endpoints(f"BoomRigidTube_{lane}") for lane in range(3)]
    minimum_hose_tube_clearance = float("inf")
    for lane in range(4):
        for segment in range(10):
            start, end = posed_beam_endpoints(f"BoomHose_{lane}_{segment}")
            for sample in range(21):
                point = start.lerp(end, sample / 20)
                for tube_start, tube_end in rigid_tubes:
                    axis = tube_end - tube_start
                    amount = max(0.0, min(1.0, (point - tube_start).dot(axis) / axis.length_squared))
                    minimum_hose_tube_clearance = min(minimum_hose_tube_clearance,
                                                     (point - tube_start.lerp(tube_end, amount)).length - .025)
    return {"maximum_beam_endpoint_error_m": beam_error,
            "maximum_point_position_error_m": point_error,
            "hose_total_lengths_m": hose_totals,
            "steering_bar_lengths_m": steer_lengths,
            "minimum_boom_hose_to_rigid_tube_surface_clearance_m": minimum_hose_tube_clearance}


def fork_measurement():
    points = named_vertices(("ForkL", "ForkR"))
    direction = obj("ForkL").matrix_world.to_3x3() @ Vector((1, 0, 0))
    return {
        "heel_x_m": min(point.x for point in points),
        "tip_x_m": max(point.x for point in points),
        "bottom_m": min(point.z for point in points),
        "load_surface_m": max(point.z for point in points),
        "pitch_degrees": math.degrees(math.atan2(direction.z, direction.x)),
    }


def plane_radius(center, names):
    return max(math.hypot(point.x - center.x, point.y - center.y)
               for name in names for point in vertices(obj(name)))


def minimum_named_clearance(names):
    samples = [(point.z, name) for name in names for point in vertices(obj(name))]
    return min(samples)


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    failures = []

    neutral = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                     "level": 0, "steerMode": "circle"})
    pose_contracts = {"stow": pose_contract_measurement(neutral)}
    front_tire_names = [target.name for target in bpy.data.objects
                        if target.name.startswith(("Tire_FL", "Tire_FR", "Tread_FL_", "Tread_FR_"))]
    front_tire_plane = max(point.x for name in front_tire_names for point in vertices(obj(name)))
    underbody_names = (
        "FrontDifferential", "RearDifferential", "FrontAxle", "RearAxle",
        "FrontAxleTubeLeft", "FrontAxleTubeRight", "RearAxleTubeLeft", "RearAxleTubeRight",
        "FrontPinionFlange", "RearPinionFlange", "BellyPan",
        "FrontSteerCylinderBarrel", "RearSteerCylinderBarrel",
        "FrontSteerBarLeft", "FrontSteerBarRight", "RearSteerBarLeft", "RearSteerBarRight",
    )
    underbody_clearance, underbody_node = minimum_named_clearance(underbody_names)
    if underbody_clearance + 1e-6 < MECHANISM["collision_proxies"]["minimum_rigid_underbody_clearance_m"]:
        failures.append("actual GLB rigid-underbody proxy misses the approximate published clearance")
    stow = fork_measurement()

    level_clearances = []
    for index in range(41):
        level = -1 + index / 20
        pose = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                      "level": level, "steerMode": "circle"})
        contract = pose_contract_measurement(pose)
        clearance, node = minimum_named_clearance(underbody_names)
        level_clearances.append({"level_fraction": level, "clearance_m": clearance,
                                 "limiting_node": node})
        if contract["maximum_beam_endpoint_error_m"] > 2e-6:
            failures.append("actual GLB dynamic beam endpoint closure drifted while frame-leveling")
    level_minimum = min(level_clearances, key=lambda record: record["clearance_m"])
    if level_minimum["clearance_m"] + 1e-6 < MECHANISM["collision_proxies"]["minimum_rigid_underbody_clearance_m"]:
        failures.append("actual GLB rigid-underbody proxy misses approximate clearance at frame-level extrema")

    max_lift_pose = solve({"lift": 1, "telescope": 1, "tilt": 0, "steer": 0,
                           "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_lift"] = pose_contract_measurement(max_lift_pose)
    max_lift = fork_measurement()
    if abs(max_lift["load_surface_m"] - CONFIG["published_performance"]["maximum_lift_height_m"]) > 0.02:
        failures.append("actual posed GLB maximum-lift fork surface misses 12.80 m")
    if abs(max_lift["pitch_degrees"]) > 0.1:
        failures.append("actual posed GLB forks are not level at maximum lift")
    proof_values = MECHANISM["validated_actual_glb_measurements"]
    if abs(max_lift["load_surface_m"] - proof_values["maximum_lift_fork_load_surface_m"]) > 1e-6:
        failures.append("maximum-lift render proof label drifted from actual posed GLB")

    max_reach_pose = solve({"lift": 3 / 69, "telescope": 1, "tilt": 0, "steer": 0,
                            "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_reach"] = pose_contract_measurement(max_reach_pose)
    max_reach = fork_measurement()
    forward_reach = max_reach["heel_x_m"] + .6096 - front_tire_plane
    if (abs(front_tire_plane - proof_values["maximum_reach_front_tire_tread_plane_x_m"]) > 1e-6
            or abs(max_reach["heel_x_m"] + .6096 - proof_values["maximum_reach_24in_load_center_x_m"]) > 1e-6
            or abs(forward_reach - proof_values["maximum_reach_m"]) > 1e-6):
        failures.append("maximum-reach render proof labels drifted from actual posed GLB")
    if abs(forward_reach - CONFIG["published_performance"]["maximum_forward_reach_m"]) > 0.02:
        failures.append("actual posed GLB 24-inch load-center reach misses 8.86 m")
    if abs(max_reach["pitch_degrees"]) > 0.1:
        failures.append("actual posed GLB forks are not level at selected 3-degree reach pose")

    circle_pose = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                         "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_circle"] = pose_contract_measurement(circle_pose)
    inner = max(abs(value) for value in circle_pose["state"]["wheelAngles"].values())
    center_lateral = 2.1005 / 2 + (3.42 / 2) / math.tan(inner)
    turn_center = Vector((0, -center_lateral, 0))
    tire_names = [target.name for target in bpy.data.objects if target.name.startswith(("Tire_", "Tread_"))]
    visible_meshes = [target.name for target in bpy.data.objects
                      if target.type == "MESH" and not target.get("is_hit_volume")]
    body_names = [name for name in visible_meshes if name not in tire_names]
    tire_swept_radius = plane_radius(turn_center, tire_names)
    body_swept_radius = plane_radius(turn_center, body_names)

    crab_pose = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                       "level": 0, "steerMode": "crab"})
    pose_contracts["maximum_crab"] = pose_contract_measurement(crab_pose)
    crab_angles = list(crab_pose["state"]["wheelAngles"].values())
    crab_spread = math.degrees(max(crab_angles) - min(crab_angles))
    if crab_spread > 2.1:
        failures.append("actual GLB crab wheel headings exceed residual-toe boundary")

    front_pose = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                        "level": 0, "steerMode": "front"})
    pose_contracts["maximum_limited_front"] = pose_contract_measurement(front_pose)
    front_inner = math.degrees(max(abs(front_pose["state"]["wheelAngles"][name]) for name in ("FL", "FR")))
    rear_heading = math.degrees(max(abs(front_pose["state"]["wheelAngles"][name]) for name in ("RL", "RR")))
    if front_inner > 5.181 or rear_heading > 1e-9:
        failures.append("actual GLB limited front-only steering semantics drifted")

    for name, contract in pose_contracts.items():
        if contract["maximum_beam_endpoint_error_m"] > 2e-6 or contract["maximum_point_position_error_m"] > 1e-9:
            failures.append(f"actual GLB named endpoint contract drifted at {name}")
        if max(contract["steering_bar_lengths_m"].values()) - min(contract["steering_bar_lengths_m"].values()) > 2e-6:
            failures.append(f"actual GLB steering bars disagree in length at {name}")
        if contract["minimum_boom_hose_to_rigid_tube_surface_clearance_m"] < .005:
            failures.append(f"actual GLB boom hose intersects rigid tube at {name}")

    output = {
        "status": "PASS" if not failures else "FAIL",
        "asset": str(GLB.relative_to(ROOT)),
        "production_solver_bridge": "scripts/solve_742_pose.mjs",
        "named_presets_posed": ["stow_0deg", "maximum_lift_69deg", "maximum_reach_selected_3deg", "maximum_circle_steer", "maximum_crab_steer", "maximum_limited_front_steer", "frame_level_dense_41"],
        "front_tire_tread_plane_x_m": front_tire_plane,
        "minimum_named_rigid_underbody_clearance_m": underbody_clearance,
        "neutral_clearance_limiting_node": underbody_node,
        "minimum_frame_level_clearance": level_minimum,
        "pose_contracts": pose_contracts,
        "stow": stow,
        "maximum_lift": max_lift,
        "maximum_reach": {**max_reach, "load_center_m": .6096, "forward_reach_m": forward_reach},
        "maximum_circle_steer": {
            "inner_wheel_angle_degrees": math.degrees(inner),
            "reconstructed_turn_center_lateral_m": center_lateral,
            "actual_glb_tire_swept_radius_m": tire_swept_radius,
            "actual_glb_body_swept_radius_m": body_swept_radius,
            "published_outside_turning_radius_m": CONFIG["published_dimensions_m"]["outside_turning_radius"],
            "boundary": "published reference locus is unresolved; actual reconstructed envelopes are reported, not equated",
        },
        "maximum_crab_steer": {
            "wheel_angles_degrees": {name: math.degrees(value) for name, value in crab_pose["state"]["wheelAngles"].items()},
            "maximum_heading_spread_degrees": crab_spread,
            "boundary": "continuous translated racks and fixed bars; residual toe measured, not factory crab calibration",
        },
        "failures": failures,
    }
    print("742_POSED_GLB_JSON=" + json.dumps(output, sort_keys=True))
    if failures:
        raise RuntimeError("; ".join(failures))


main()
