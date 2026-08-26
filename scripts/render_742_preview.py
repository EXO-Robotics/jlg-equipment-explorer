#!/usr/bin/env python3
"""Render review-only stills from the owned 742 Blender source."""

import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tmp/742/review-renders"


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def rotate_xy(point, angle):
    x, y, z = point
    return (math.cos(angle) * x - math.sin(angle) * y, math.sin(angle) * x + math.cos(angle) * y, z)


def set_beam(name, start, end):
    obj = bpy.data.objects[name]
    a, b = Vector(start), Vector(end)
    direction = b - a
    obj.location = (a + b) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    obj.scale = (1, 1, direction.length / float(obj.get("authored_length_m", direction.length)))


def pose_circle_steering(amount=1.0):
    inner = math.radians(55) * amount
    half_wheelbase = 3.42 / 2
    track = 2.1005
    if abs(inner) < 1e-7:
        outer = 0.0
    else:
        center_radius = track / 2 + half_wheelbase / math.tan(abs(inner))
        outer = math.atan(half_wheelbase / (center_radius + track / 2))
    angles = {"FL": outer, "FR": inner, "RL": -outer, "RR": -inner}
    for corner, angle in angles.items():
        bpy.data.objects[f"SteerPivot_{corner}"].rotation_euler[1] = angle

    def joint(x, lateral, angle):
        inward = 0.16 if lateral < 0 else -0.16
        dx = -0.12 * math.cos(angle) - inward * math.sin(angle)
        dz = -0.12 * math.sin(angle) + inward * math.cos(angle)
        return Vector((x + dx, 0.59, lateral + dz))

    for axle, x, left, right in (("Front", 1.71, "FL", "FR"), ("Rear", -1.71, "RL", "RR")):
        left_cap, right_cap = Vector((x, 0.76, -0.46)), Vector((x, 0.76, 0.46))
        set_beam(f"{axle}SteerCylinderBarrel", left_cap, right_cap)
        set_beam(f"{axle}SteerCylinderRodLeft", left_cap, joint(x, -1.05025, angles[left]))
        set_beam(f"{axle}SteerCylinderRodRight", right_cap, joint(x, 1.05025, angles[right]))


def pose_mechanisms(lift, telescope, tilt=0.0, level=0.0):
    angle = math.radians(3 + 66 * lift)
    travel = 3.604 * telescope
    boom = bpy.data.objects["BoomLiftPivot"]
    mid = bpy.data.objects["BoomMid"]
    fly = bpy.data.objects["BoomFly"]
    carriage = bpy.data.objects["CarriageTiltPivot"]
    frame = bpy.data.objects["FrameLevelPivot"]
    boom.rotation_euler[2] = angle
    mid.location.x = 0.12 + travel
    fly.location.x = 0.12 + travel
    carriage.rotation_euler[2] = -angle + math.radians(tilt)
    frame.rotation_euler[0] = math.radians(level)

    pivot = Vector((-2.158, 1.838, 0))
    lift_base = Vector((-1.80, 0.70, 0))
    lift_anchor = pivot + Vector(rotate_xy((2.412, -0.20, 0), angle))
    delta = lift_anchor - lift_base
    set_beam("LiftCylinderBarrel", lift_base, lift_base + delta * 0.72)
    set_beam("LiftCylinderRod", lift_base + delta * 0.55, lift_anchor)
    bpy.data.objects["LiftCylinderRodPin"].location = lift_anchor
    for lane, lateral in enumerate((-0.16, -0.23)):
        start = Vector((-1.88, 0.74 if lane == 0 else 0.70, lateral))
        end = Vector((lift_anchor.x, lift_anchor.y, lateral))
        delta = end - start
        path = (start, start + delta * 0.34 + Vector((0, -0.12, 0)), start + delta * 0.70 + Vector((0, -0.09, 0)), end)
        for segment in range(3):
            set_beam(f"LiftHose_{lane}_{segment}", path[segment], path[segment + 1])

    tele_start, tele_end = Vector((0.55, -0.22, 0)), Vector((3.36 + travel, -0.22, 0))
    tele_delta = tele_end - tele_start
    set_beam("TelescopeCylinderBarrel", tele_start, tele_start + tele_delta * 0.62)
    set_beam("TelescopeCylinderRod", tele_start + tele_delta * 0.48, tele_end)

    compensation_base = Vector((-2.00, 1.50, -0.31))
    compensation_anchor = pivot + Vector(rotate_xy((0.80, 0.30, -0.31), angle))
    compensation_delta = compensation_anchor - compensation_base
    set_beam("CompensationCylinderBarrel", compensation_base, compensation_base + compensation_delta * 0.67)
    set_beam("CompensationCylinderRod", compensation_base + compensation_delta * 0.52, compensation_anchor)

    mid_x, fly_x = 0.12 + travel, 0.12 + travel
    for lane, lateral in enumerate((-0.27, -0.20, 0.20, 0.27)):
        start, end = Vector((0.15, -0.38, lateral)), Vector((mid_x + fly_x + 2.95, -0.32, lateral))
        delta = end - start
        path = (start, start + delta * 0.34 + Vector((0, -0.08, 0)), start + delta * 0.69 + Vector((0, -0.06, 0)), end)
        for segment in range(3):
            set_beam(f"BoomHose_{lane}_{segment}", path[segment], path[segment + 1])
    for side, lateral in (("L", -0.24), ("R", 0.24)):
        set_beam(f"ExtendChain_{side}", (0.40, -0.22, lateral), (mid_x + fly_x + 4.70, -0.22, lateral))
    set_beam("RetractChain_C", (5.10, -0.29, 0), (mid_x + fly_x + 0.20, -0.29, 0))

    carriage_pivot = Vector((5.296, -0.80, 0))
    carriage_angle = -angle + math.radians(tilt)
    tilt_base = Vector((4.216, -1.21, 0.42))
    rod_anchor = carriage_pivot + Vector(rotate_xy((-0.1494, 0.3705, 0.42), carriage_angle))
    link_anchor = carriage_pivot + Vector(rotate_xy((-0.08, 0.58, 0.42), carriage_angle))
    delta = rod_anchor - tilt_base
    set_beam("CarriageTiltCylinderBarrel", tilt_base, tilt_base + delta * 0.66)
    set_beam("CarriageTiltCylinderRod", tilt_base + delta * 0.50, rod_anchor)
    set_beam("CarriageTiltLink", rod_anchor, link_anchor)

    level_base = Vector((-0.0133, 0.6054, 0.4865))
    frame_pivot = Vector((0, 0.82, 0))
    level_anchor = Vector((0.1121, 1.2428, 1.1607)) - frame_pivot
    level_anchor.rotate(Matrix.Rotation(math.radians(level), 4, "X"))
    level_anchor += frame_pivot
    delta = level_anchor - level_base
    set_beam("FrameLevelCylinderBarrel", level_base, level_base + delta * 0.67)
    set_beam("FrameLevelCylinderRod", level_base + delta * 0.52, level_anchor)

    ras_base = Vector((-1.95, 0.64, -0.45))
    ras_anchor = Vector((-1.55, 0.92, -0.65)) - frame_pivot
    ras_anchor.rotate(Matrix.Rotation(math.radians(level), 4, "X"))
    ras_anchor += frame_pivot
    ras_delta = ras_anchor - ras_base
    set_beam("RearAxleStabilizerBarrel", ras_base, ras_base + ras_delta * 0.67)
    set_beam("RearAxleStabilizerRod", ras_base + ras_delta * 0.52, ras_anchor)

    sensor_base = Vector((-2.15, 1.64, -0.56))
    sensor_anchor = pivot + Vector(rotate_xy((0.35, -0.10, -0.56), angle))
    set_beam("BoomAngleSensorLink", sensor_base, sensor_anchor)
    bpy.data.objects["BoomAngleSensorBoomJoint"].location = sensor_anchor


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
camera.location = (4.5, 0.0, 1.55)
point_at(camera, (1.71, 0.0, 0.70))
scene.render.filepath = str(OUTPUT_DIR / "742-front-double-ended-steer-cylinder-cutaway.png")
bpy.ops.render.render(write_still=True)
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
