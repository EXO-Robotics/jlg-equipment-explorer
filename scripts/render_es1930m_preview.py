#!/usr/bin/env python3
"""Render a review-only preview from the frozen ES1930M source blend."""

from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "tmp/es1930m/review-renders"


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


# Interaction volumes are exported for browser ray selection and hidden by the
# runtime. Mirror that presentation contract in offline review renders.
for obj in bpy.data.objects:
    if obj.name.endswith("_Hit"):
        obj.hide_render = True


bpy.ops.object.camera_add(location=(3.2, -3.7, 2.55))
camera = bpy.context.object
camera.name = "ReviewCamera"
camera.data.lens = 58
point_at(camera, (0, 0, 0.95))
bpy.context.scene.camera = camera

bpy.ops.mesh.primitive_plane_add(size=18, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "ReviewFloor"
floor_material = bpy.data.materials.new("ReviewFloorMaterial")
floor_material.diffuse_color = (0.07, 0.085, 0.085, 1)
floor.data.materials.append(floor_material)

for name, location, energy, size, color in (
    ("Key", (3.5, -4.0, 6.0), 1050, 4.0, (1.0, 0.88, 0.72)),
    ("Fill", (-4.0, -1.5, 3.5), 700, 3.0, (0.65, 0.78, 1.0)),
    ("Rim", (1.0, 4.0, 4.5), 900, 3.0, (1.0, 0.55, 0.28)),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy
    lamp.data.shape = "DISK"
    lamp.data.size = size
    lamp.data.color = color
    point_at(lamp, (0, 0, 0.9))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (0.018, 0.025, 0.027)
scene.view_settings.look = "AgX - Medium High Contrast"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

views = {
    "front-right": (3.2, -3.7, 2.55),
    "front-left": (3.2, 3.7, 2.55),
    "rear-right": (-3.2, -3.7, 2.55),
    "rear-left": (-3.2, 3.7, 2.55),
}
for name, location in views.items():
    camera.location = location
    point_at(camera, (0, 0, 0.95))
    output = OUTPUT_DIR / f"es1930m-stowed-{name}.png"
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(output)
