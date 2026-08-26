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


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    failures = []

    neutral = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                     "level": 0, "steerMode": "circle"})
    apply_pose(neutral)
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
    underbody_clearance = min(point.z for point in named_vertices(underbody_names))
    if underbody_clearance + 1e-6 < MECHANISM["collision_proxies"]["minimum_rigid_underbody_clearance_m"]:
        failures.append("actual GLB rigid-underbody proxy misses the approximate published clearance")
    stow = fork_measurement()

    max_lift_pose = solve({"lift": 1, "telescope": 1, "tilt": 0, "steer": 0,
                           "level": 0, "steerMode": "circle"})
    apply_pose(max_lift_pose)
    max_lift = fork_measurement()
    if abs(max_lift["load_surface_m"] - CONFIG["published_performance"]["maximum_lift_height_m"]) > 0.02:
        failures.append("actual posed GLB maximum-lift fork surface misses 12.80 m")
    if abs(max_lift["pitch_degrees"]) > 0.1:
        failures.append("actual posed GLB forks are not level at maximum lift")

    max_reach_pose = solve({"lift": 3 / 69, "telescope": 1, "tilt": 0, "steer": 0,
                            "level": 0, "steerMode": "circle"})
    apply_pose(max_reach_pose)
    max_reach = fork_measurement()
    forward_reach = max_reach["heel_x_m"] + .6096 - front_tire_plane
    if abs(forward_reach - CONFIG["published_performance"]["maximum_forward_reach_m"]) > 0.02:
        failures.append("actual posed GLB 24-inch load-center reach misses 8.86 m")
    if abs(max_reach["pitch_degrees"]) > 0.1:
        failures.append("actual posed GLB forks are not level at selected 3-degree reach pose")

    circle_pose = solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                         "level": 0, "steerMode": "circle"})
    apply_pose(circle_pose)
    inner = max(abs(value) for value in circle_pose["state"]["wheelAngles"].values())
    center_lateral = 2.1005 / 2 + (3.42 / 2) / math.tan(inner)
    turn_center = Vector((0, -center_lateral, 0))
    tire_names = [target.name for target in bpy.data.objects if target.name.startswith(("Tire_", "Tread_"))]
    visible_meshes = [target.name for target in bpy.data.objects
                      if target.type == "MESH" and not target.get("is_hit_volume")]
    body_names = [name for name in visible_meshes if name not in tire_names]
    tire_swept_radius = plane_radius(turn_center, tire_names)
    body_swept_radius = plane_radius(turn_center, body_names)

    output = {
        "status": "PASS" if not failures else "FAIL",
        "asset": str(GLB),
        "production_solver_bridge": "scripts/solve_742_pose.mjs",
        "named_presets_posed": ["stow_0deg", "maximum_lift_69deg", "maximum_reach_selected_3deg", "maximum_circle_steer"],
        "front_tire_tread_plane_x_m": front_tire_plane,
        "minimum_named_rigid_underbody_clearance_m": underbody_clearance,
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
        "failures": failures,
    }
    print("742_POSED_GLB_JSON=" + json.dumps(output, sort_keys=True))
    if failures:
        raise RuntimeError("; ".join(failures))


main()
