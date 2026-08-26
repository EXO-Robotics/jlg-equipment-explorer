#!/usr/bin/env python3
"""Render review-only stills from the owned 742 Blender source."""

import math
import json
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tmp/742/review-renders"


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def set_beam(name, start, end):
    obj = bpy.data.objects[name]
    a, b = Vector(start), Vector(end)
    direction = b - a
    obj.location = (a + b) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    obj.scale = (1, 1, direction.length / float(obj.get("authored_length_m", direction.length)))


def solved_pose(lift, telescope, tilt=0.0, steer=0.0, level=0.0, steer_mode="circle"):
    request = {"lift": lift, "telescope": telescope, "tilt": tilt / 12 if tilt >= 0 else tilt / 5,
               "steer": steer, "level": level / 10, "steerMode": steer_mode}
    completed = subprocess.run(["node", str(ROOT / "scripts/solve_742_pose.mjs"), json.dumps(request)],
                               check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def apply_solved_pose(pose):
    state = pose["state"]
    bpy.data.objects["BoomLiftPivot"].rotation_euler[2] = state["boomAngle"]
    bpy.data.objects["BoomMid"].location.x = 0.12 + state["midTranslation"]
    bpy.data.objects["BoomFly"].location.x = 0.12 + state["flyTranslation"]
    bpy.data.objects["CarriageTiltPivot"].rotation_euler[2] = state["carriageAngle"]
    bpy.data.objects["FrameLevelPivot"].rotation_euler[0] = state["frameAngle"]
    for corner, angle in state["wheelAngles"].items():
        bpy.data.objects[f"SteerPivot_{corner}"].rotation_euler[1] = angle
    for name, endpoints in pose["geometry"]["beams"].items():
        set_beam(name, endpoints[0], endpoints[1])
    for name, point in pose["geometry"]["points"].items():
        bpy.data.objects[name].location = point


def pose_circle_steering(amount=1.0):
    apply_solved_pose(solved_pose(0, 0, steer=amount, steer_mode="circle"))


def pose_mechanisms(lift, telescope, tilt=0.0, level=0.0):
    apply_solved_pose(solved_pose(lift, telescope, tilt=tilt, level=level))


for obj in bpy.data.objects:
    if obj.name.endswith("_Hit"):
        obj.hide_render = True

bpy.ops.object.camera_add(location=(8.5, 4.3, -8.8))
camera = bpy.context.object
camera.name = "ReviewCamera"
camera.data.lens = 58
bpy.context.scene.camera = camera

bpy.ops.mesh.primitive_plane_add(size=28, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "ReviewFloor"
mat = bpy.data.materials.new("ReviewFloorMaterial")
mat.diffuse_color = (0.045, 0.055, 0.055, 1)
floor.data.materials.append(mat)

for name, location, energy, size, color in (
    ("Key", (5.0, -5.0, 8.0), 1350, 5.0, (1.0, 0.88, 0.72)),
    ("Fill", (-5.0, -2.0, 5.0), 850, 4.0, (0.62, 0.76, 1.0)),
    ("Rim", (1.0, 6.0, 6.0), 1100, 4.0, (1.0, 0.50, 0.22)),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy
    lamp.data.shape = "DISK"
    lamp.data.size = size
    lamp.data.color = color
    point_at(lamp, (0, 1.1, 0))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (0.012, 0.018, 0.020)
scene.view_settings.look = "AgX - Medium High Contrast"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

views = {
    "stowed-front-left": ((7.8, 7.8, 4.4), (0, 0, 1.25)),
    "stowed-front-right": ((7.8, -7.8, 4.4), (0, 0, 1.25)),
    "stowed-side": ((0.0, -10.5, 2.7), (0, 0, 1.25)),
    "cab-close": ((4.0, 4.2, 3.0), (0.75, 0.55, 1.65)),
}
for name, (location, target) in views.items():
    camera.location = location
    point_at(camera, target)
    scene.render.filepath = str(OUTPUT_DIR / f"742-{name}.png")
    bpy.ops.render.render(write_still=True)

pose_circle_steering(1.0)
steer_cutaway = [
    obj for obj in bpy.data.objects
    if obj.type in {"MESH", "CURVE", "FONT"} and obj.get("component") not in {None, "steering"}
]
for obj in steer_cutaway:
    obj.hide_render = True
steer_names = {"FrontSteerCylinderBarrel", "FrontSteerCylinderRodLeft", "FrontSteerCylinderRodRight",
               "FrontSteerBarLeft", "FrontSteerBarRight"}
steer_occluders = [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT"}
                   and obj.get("component") == "steering" and obj.name not in steer_names]
for obj in steer_occluders:
    obj.hide_render = True
bpy.context.view_layer.update()
steer_center = sum((bpy.data.objects[name].matrix_world.translation for name in steer_names), Vector()) / len(steer_names)
camera.location = (4.5, 0.0, 1.55)
point_at(camera, steer_center)
scene.render.filepath = str(OUTPUT_DIR / "742-front-double-ended-steer-cylinder-cutaway.png")
bpy.ops.render.render(write_still=True)
for obj in steer_occluders:
    obj.hide_render = False
for obj in steer_cutaway:
    obj.hide_render = False
pose_circle_steering(0.0)

pose_mechanisms(0.61, 0.68)
camera.location = (12.0, 14.0, 9.2)
point_at(camera, (2.2, 0, 5.0))
scene.render.filepath = str(OUTPUT_DIR / "742-extended-front-left.png")
bpy.ops.render.render(write_still=True)
camera.location = (-5.0, 2.4, 2.8)
point_at(camera, (-2.03, 0.35, 1.60))
scene.render.filepath = str(OUTPUT_DIR / "742-boom-pivot-angle-sensor.png")
bpy.ops.render.render(write_still=True)
camera.location = (8.8, -10.5, 6.2)
point_at(camera, (1.5, 0.0, 4.3))
scene.render.filepath = str(OUTPUT_DIR / "742-boom-underside-lines-chains.png")
bpy.ops.render.render(write_still=True)
chain_keep = ("Chain", "Sheave", "BoomRigidTube", "BoomHose")
chain_cutaway = [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT"}
                 and not any(token in obj.name for token in chain_keep)]
for obj in chain_cutaway:
    obj.hide_render = True
bpy.context.view_layer.update()
chain_objects = [obj for obj in bpy.data.objects if any(token in obj.name for token in chain_keep)
                 and obj.type in {"MESH", "CURVE"}]
chain_center = sum((obj.matrix_world.translation for obj in chain_objects), Vector()) / len(chain_objects)
camera.location = chain_center + Vector((3.8, -7.2, 2.6))
point_at(camera, chain_center)
scene.render.filepath = str(OUTPUT_DIR / "742-retract-chain-routing-cutaway.png")
bpy.ops.render.render(write_still=True)
for obj in chain_cutaway:
    obj.hide_render = False
pose_mechanisms(1.0, 1.0)
camera.location = (27.0, 30.0, 21.0)
point_at(camera, (3.0, 0, 8.0))
scene.render.filepath = str(OUTPUT_DIR / "742-maximum-lift-level-forks.png")
bpy.ops.render.render(write_still=True)
pose_mechanisms(0.0, 1.0)
camera.location = (15.0, -23.0, 7.5)
point_at(camera, (3.6, 0, 1.7))
scene.render.filepath = str(OUTPUT_DIR / "742-maximum-reach-24in-load-center.png")
bpy.ops.render.render(write_still=True)
print(OUTPUT_DIR)
