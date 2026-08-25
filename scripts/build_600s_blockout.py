"""Build and export the evidence-bounded 600S structural blockout v0.1."""

from __future__ import annotations

import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BLEND_PATH = PROJECT_ROOT / "source/blender/600s-blockout-v0.1.blend"
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"
SCENE_NAME = "JLG_600S_BLOCKOUT_V01"
COLLECTION_NAME = "JLG_600S_BLOCKOUT_V01"

PUBLISHED_ENVELOPE_M = Vector((8.71, 2.48, 2.50))
PLATFORM_ENVELOPE_M = Vector((0.91, 2.44, 1.12))
WHEELBASE_M = 2.50


def material(name: str, rgba: tuple[float, float, float, float], metallic: float, roughness: float) -> bpy.types.Material:
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = rgba
    value.use_nodes = True
    value.metallic = metallic
    value.roughness = roughness
    principled = value.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = rgba
    metallic_input = principled.inputs.get("Metallic IOR Level") or principled.inputs.get("Metallic")
    if metallic_input is not None:
        metallic_input.default_value = metallic
    principled.inputs["Roughness"].default_value = roughness
    if rgba[3] < 1.0:
        principled.inputs["Alpha"].default_value = rgba[3]
        value.surface_render_method = "DITHERED"
    return value


MAT_ORANGE = material("JLG_Blockout_Orange", (0.91, 0.48, 0.035, 1.0), 0.08, 0.62)
MAT_DARK = material("JLG_Blockout_Dark", (0.055, 0.065, 0.055, 1.0), 0.12, 0.78)
MAT_METAL = material("JLG_Blockout_Metal", (0.34, 0.37, 0.33, 1.0), 0.52, 0.48)
MAT_HIT = material("JLG_Interaction_Volume", (0.0, 0.0, 0.0, 0.0), 0.0, 1.0)


def link_object(obj: bpy.types.Object) -> bpy.types.Object:
    collection.objects.link(obj)
    return obj


def empty(name: str, parent: bpy.types.Object | None, location=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    obj = link_object(bpy.data.objects.new(name, None))
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.22
    obj.location = location
    obj.parent = parent
    return obj


def box(
    name: str,
    dimensions: tuple[float, float, float],
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    component: str,
    *,
    hit: bool = False,
) -> bpy.types.Object:
    x, y, z = (axis / 2.0 for axis in dimensions)
    vertices = [
        (-x, -y, -z), (-x, -y, z), (-x, y, -z), (-x, y, z),
        (x, -y, -z), (x, -y, z), (x, y, -z), (x, y, z),
    ]
    faces = [
        (0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4),
        (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = link_object(bpy.data.objects.new(name, mesh))
    obj.location = location
    obj.parent = parent
    obj["component"] = component
    obj["is_hit_volume"] = hit
    obj["authority"] = "interaction_contract" if hit else "visual_blockout"
    obj.display_type = "WIRE" if hit else "TEXTURED"
    obj.show_in_front = hit
    return obj


def cylinder_mesh(
    name: str,
    radius: float,
    depth: float,
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    rotation: tuple[float, float, float],
    mat: bpy.types.Material,
    component: str,
    segments: int = 20,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=depth,
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = link_object(bpy.data.objects.new(name, mesh))
    obj.location = location
    obj.rotation_euler = rotation
    obj.parent = parent
    obj["component"] = component
    obj["authority"] = "visual_blockout"
    return obj


def add_wheel(name: str, x: float, y: float, front: bool) -> bpy.types.Object:
    pivot = empty(name, chassis, (x, y, 0.65))
    pivot["component"] = "chassis"
    pivot["steering_pivot"] = front
    cylinder_mesh(
        f"{name}_Tire", 0.65, 0.40, pivot, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_DARK, "chassis", 28,
    )
    cylinder_mesh(
        f"{name}_Hub", 0.22, 0.38, pivot, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_METAL, "chassis", 20,
    )
    return pivot


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector, Vector]:
    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    for obj in objects:
        if obj.type != "MESH" or obj.get("is_hit_volume"):
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            minimum.x = min(minimum.x, point.x)
            minimum.y = min(minimum.y, point.y)
            minimum.z = min(minimum.z, point.z)
            maximum.x = max(maximum.x, point.x)
            maximum.y = max(maximum.y, point.y)
            maximum.z = max(maximum.z, point.z)
    return minimum, maximum, maximum - minimum


if bpy.data.filepath and Path(bpy.data.filepath).resolve() != BLEND_PATH.resolve():
    raise RuntimeError("Refusing to replace an unrelated saved Blender file")

for old_collection in [
    value for value in bpy.data.collections
    if value.name == COLLECTION_NAME or value.name.startswith(f"{COLLECTION_NAME}.")
]:
    for old_object in list(old_collection.all_objects):
        bpy.data.objects.remove(old_object, do_unlink=True)
    bpy.data.collections.remove(old_collection)
for old_scene in [
    value for value in bpy.data.scenes
    if value.name == SCENE_NAME or value.name.startswith(f"{SCENE_NAME}.")
]:
    bpy.data.scenes.remove(old_scene)

scene = bpy.data.scenes.new(SCENE_NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "METERS"
scene.unit_settings.scale_length = 1.0
scene["asset"] = "600S structural blockout v0.1"
scene["published_envelope_m"] = list(PUBLISHED_ENVELOPE_M)
scene["wheelbase_m"] = WHEELBASE_M
scene["evidence_boundary"] = "overall envelopes verified; internal offsets visually reconstructed"

collection = bpy.data.collections.new(COLLECTION_NAME)
scene.collection.children.link(collection)

root = empty("600S_ROOT", None)
root["asset_version"] = "0.1.0"
root["authorship"] = "owned-simplified-reconstruction"
root["generation_scope"] = "June/July 2026 current-generation 600S"
root["units"] = "meters"

chassis = empty("Chassis", root)
box("Frame", (5.60, 1.75, 0.46), chassis, (-0.10, 0.0, 0.52), MAT_DARK, "chassis")
box("LowerDeck", (4.95, 1.92, 0.16), chassis, (-0.05, 0.0, 1.12), MAT_ORANGE, "chassis")
box("AxleFront", (0.22, 2.05, 0.22), chassis, (1.25, 0.0, 0.65), MAT_METAL, "chassis")
box("AxleRear", (0.22, 2.05, 0.22), chassis, (-1.25, 0.0, 0.65), MAT_METAL, "chassis")
add_wheel("Wheel_FL", 1.25, 1.04, True)
add_wheel("Wheel_FR", 1.25, -1.04, True)
add_wheel("Wheel_RL", -1.25, 1.04, False)
add_wheel("Wheel_RR", -1.25, -1.04, False)

turntable_pivot = empty("TurntablePivot", root, (-0.45, 0.0, 1.18))
turntable_pivot["authority"] = "visual_blockout_pending_manual_offset"
turntable = empty("Turntable", turntable_pivot)
cylinder_mesh("SlewRing", 0.72, 0.18, turntable, (0.0, 0.0, 0.09), (0.0, 0.0, 0.0), MAT_METAL, "turntable", 32)
box("UpperDeck", (2.95, 1.82, 0.24), turntable, (-0.15, 0.0, 0.31), MAT_ORANGE, "turntable")
box("EngineCover", (1.85, 1.34, 0.80), turntable, (-0.15, 0.0, 0.91), MAT_DARK, "turntable")
box("Counterweight", (1.50, 1.96, 1.15), turntable, (-1.30, 0.0, 0.695), MAT_ORANGE, "turntable")
box("Controls", (0.44, 0.58, 0.62), turntable, (0.92, -0.56, 0.82), MAT_DARK, "turntable")

boom_pivot = empty("BoomPivot", turntable, (-0.55, 0.0, 0.92))
boom_pivot["authority"] = "visual_blockout_pending_manual_hinge"
main_boom = empty("MainBoom", boom_pivot)
box("MainBoomShell", (5.60, 0.62, 0.56), main_boom, (2.80, 0.0, 0.0), MAT_ORANGE, "boom")
cylinder_mesh("BoomPivotPin", 0.31, 0.82, main_boom, (0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_METAL, "boom", 24)

telescope = empty("Telescope", main_boom, (4.65, 0.0, 0.0))
telescope["authority"] = "visual_blockout_pending_manual_nested_length"
box("TelescopeShell", (1.15, 0.48, 0.42), telescope, (0.575, 0.0, 0.0), MAT_DARK, "boom")

platform_pivot = empty("PlatformPivot", telescope, (1.25, 0.0, 0.0))
platform_pivot["authority"] = "visual_blockout_pending_manual_rotator_center"
platform = empty("Platform", platform_pivot)
box("PlatformDeck", (0.91, 2.44, 0.12), platform, (0.455, 0.0, -0.72), MAT_ORANGE, "platform")
box("PlatformControls", (0.22, 0.58, 0.34), platform, (0.72, -0.88, -0.43), MAT_DARK, "platform")
for x in (0.03, 0.88):
    for y in (-1.19, 1.19):
        box(f"PlatformPost_{x}_{y}", (0.06, 0.06, 1.06), platform, (x, y, -0.13), MAT_METAL, "platform")
for x in (0.03, 0.88):
    box(f"PlatformRailSide_{x}", (0.06, 2.44, 0.06), platform, (x, 0.0, 0.37), MAT_METAL, "platform")
for y in (-1.19, 1.19):
    box(f"PlatformRailEnd_{y}", (0.91, 0.06, 0.06), platform, (0.455, y, 0.37), MAT_METAL, "platform")

lift_cylinder = cylinder_mesh(
    "LiftCylinder", 0.13, 1.75, boom_pivot, (0.64, 0.0, -0.58),
    (0.0, math.pi / 3.0, 0.0), MAT_METAL, "boom", 18,
)
lift_cylinder["authority"] = "visual_only_unresolved_anchors"

box("Chassis_Hit", (5.90, 2.48, 1.35), chassis, (-0.05, 0.0, 0.70), MAT_HIT, "chassis", hit=True)
box("Turntable_Hit", (3.25, 2.18, 1.45), turntable, (-0.42, 0.0, 0.74), MAT_HIT, "turntable", hit=True)
box("Boom_Hit", (5.70, 0.90, 0.92), main_boom, (2.80, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Telescope_Hit", (1.45, 0.78, 0.78), telescope, (0.65, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Platform_Hit", (1.05, 2.48, 1.30), platform, (0.455, 0.0, -0.10), MAT_HIT, "platform", hit=True)

bpy.context.view_layer.update()
objects = list(collection.all_objects)
minimum, maximum, dimensions = world_bounds(objects)
for axis, actual, expected in zip("XYZ", dimensions, PUBLISHED_ENVELOPE_M):
    if not math.isclose(actual, expected, abs_tol=0.002):
        raise RuntimeError(f"Published {axis} envelope drift: {actual:.4f} m != {expected:.4f} m")
if not math.isclose(
    bpy.data.objects["Wheel_FL"].location.x - bpy.data.objects["Wheel_RL"].location.x,
    WHEELBASE_M,
    abs_tol=0.001,
):
    raise RuntimeError("Wheelbase drift")

BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)

bpy.ops.object.select_all(action="DESELECT")
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.gltf(
    filepath=str(GLB_PATH),
    check_existing=False,
    export_format="GLB",
    use_selection=True,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
    export_yup=True,
    export_apply=False,
    export_animations=False,
    export_draco_mesh_compression_enable=False,
)

result = {
    "status": "PASS",
    "asset": "600S Blockout v0.1",
    "blend_path": str(BLEND_PATH),
    "glb_path": str(GLB_PATH),
    "object_count": len(objects),
    "visible_bounds_min_m": [round(value, 4) for value in minimum],
    "visible_bounds_max_m": [round(value, 4) for value in maximum],
    "visible_dimensions_m": [round(value, 4) for value in dimensions],
    "wheelbase_m": WHEELBASE_M,
    "platform_envelope_m": list(PLATFORM_ENVELOPE_M),
}
