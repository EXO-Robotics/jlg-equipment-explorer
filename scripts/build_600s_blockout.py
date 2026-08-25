"""Build and export the evidence-bounded 600S structural blockout v0.2."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


_SCRIPT = Path(globals().get("__file__") or globals()["_jlg_script"]).resolve()
PROJECT_ROOT = _SCRIPT.parents[1]
BLEND_PATH = PROJECT_ROOT / "source/blender/600s-blockout-v0.2.blend"
MIGRATION_SOURCE_PATHS = {
    PROJECT_ROOT / "source/blender/600s-blockout-v0.1.blend",
}
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"
SCENE_NAME = "JLG_600S_BLOCKOUT_V02"
COLLECTION_NAME = "JLG_600S_BLOCKOUT_V02"

PUBLISHED_ENVELOPE_M = Vector((8.71, 2.48, 2.50))
PLATFORM_SIZE_M = Vector((0.91, 2.44))
WHEELBASE_M = 2.50
GROUND_CLEARANCE_M = 0.29
TAILSWING_M = 1.22
TELESCOPE_TRAVEL_M = 0.90
ASSET_VERSION = "0.2.0"

CHASSIS_HALF_WIDTH_M = PUBLISHED_ENVELOPE_M.y / 2.0
COUNTERWEIGHT_REAR_RADIUS_M = CHASSIS_HALF_WIDTH_M + TAILSWING_M
COUNTERWEIGHT_FRONT_X = -0.57
COUNTERWEIGHT_LENGTH_M = COUNTERWEIGHT_REAR_RADIUS_M + COUNTERWEIGHT_FRONT_X
COUNTERWEIGHT_CENTER_X = (COUNTERWEIGHT_FRONT_X - COUNTERWEIGHT_REAR_RADIUS_M) / 2.0
PLATFORM_PIVOT_X = 1.24


def material(name: str, rgba: tuple[float, float, float, float], metallic: float, roughness: float) -> bpy.types.Material:
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = rgba
    value.use_nodes = True
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


def link_object(obj: bpy.types.Object) -> bpy.types.Object:
    collection.objects.link(obj)
    return obj


def empty(name: str, parent: bpy.types.Object | None, location=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    obj = link_object(bpy.data.objects.new(name, None))
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.22
    obj.location = location
    obj.parent = parent
    obj.scale = (1.0, 1.0, 1.0)
    return obj


def shade_smooth(obj: bpy.types.Object) -> None:
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def bevel(obj: bpy.types.Object, width: float = 0.028, segments: int = 2) -> bpy.types.Object:
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.bevel(
        bm,
        geom=list(bm.edges),
        offset=width,
        offset_type="OFFSET",
        segments=segments,
        profile=0.7,
        affect="EDGES",
        clamp_overlap=True,
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
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
    round: float | None = None,
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
    obj.scale = (1.0, 1.0, 1.0)
    obj["component"] = component
    obj["is_hit_volume"] = hit
    obj["authority"] = "interaction_contract" if hit else "visual_blockout"
    obj.display_type = "WIRE" if hit else "TEXTURED"
    obj.show_in_front = hit
    if round:
        bevel(obj, round, 2)
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
    *,
    smooth: bool = True,
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
    obj.scale = (1.0, 1.0, 1.0)
    obj["component"] = component
    obj["authority"] = "visual_blockout"
    if smooth:
        shade_smooth(obj)
    return obj


def tube(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    parent: bpy.types.Object,
    mat: bpy.types.Material,
    component: str,
    segments: int = 10,
) -> bpy.types.Object:
    a = Vector(start)
    b = Vector(end)
    direction = b - a
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius,
        depth=direction.length,
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    obj = link_object(bpy.data.objects.new(name, mesh))
    obj.location = (a + b) * 0.5
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    obj.parent = parent
    obj.scale = (1.0, 1.0, 1.0)
    obj["component"] = component
    obj["authority"] = "visual_blockout"
    shade_smooth(obj)
    return obj


def add_wheel(name: str, x: float, y: float, front: bool) -> bpy.types.Object:
    pivot = empty(name, chassis, (x, y, 0.65))
    pivot["component"] = "chassis"
    pivot["steering_pivot"] = front
    cylinder_mesh(
        f"{name}_Tire", 0.65, 0.40, pivot, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_TIRE, "chassis", 28,
    )
    cylinder_mesh(
        f"{name}_Rim", 0.42, 0.30, pivot, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_METAL, "chassis", 24,
    )
    cylinder_mesh(
        f"{name}_Hub", 0.16, 0.34, pivot, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_METAL, "chassis", 16,
    )
    cylinder_mesh(
        f"{name}_Kingpin", 0.055, 0.30, pivot, (0.0, 0.0, 0.18),
        (0.0, 0.0, 0.0), MAT_METAL, "chassis", 12,
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


if bpy.data.filepath:
    open_path = Path(bpy.data.filepath).resolve()
    allowed_paths = {BLEND_PATH.resolve(), *(path.resolve() for path in MIGRATION_SOURCE_PATHS)}
    if open_path not in allowed_paths:
        raise RuntimeError(f"Refusing to replace an unrelated saved Blender file: {open_path}")

for old_collection in list(bpy.data.collections):
    if old_collection.name.startswith("JLG_600S_BLOCKOUT"):
        for old_object in list(old_collection.all_objects):
            bpy.data.objects.remove(old_object, do_unlink=True)
        bpy.data.collections.remove(old_collection)

scene = bpy.data.scenes.new(SCENE_NAME)
if bpy.context.window:
    bpy.context.window.scene = scene
for old_scene in list(bpy.data.scenes):
    if old_scene != scene:
        bpy.data.scenes.remove(old_scene)

for datablock_collection in (bpy.data.meshes, bpy.data.materials, bpy.data.objects, bpy.data.cameras, bpy.data.lights):
    for datablock in list(datablock_collection):
        if datablock.users == 0:
            datablock_collection.remove(datablock)

scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "METERS"
scene.unit_settings.scale_length = 1.0
scene["asset"] = "600S structural blockout v0.2"
scene["asset_version"] = ASSET_VERSION
scene["published_envelope_m"] = list(PUBLISHED_ENVELOPE_M)
scene["wheelbase_m"] = WHEELBASE_M
scene["ground_clearance_m"] = GROUND_CLEARANCE_M
scene["tailswing_m"] = TAILSWING_M
scene["telescope_travel_m"] = TELESCOPE_TRAVEL_M
scene["platform_leveling"] = "counter_rotate_local_z"
scene["evidence_boundary"] = (
    "overall envelopes verified; telescope travel is a visual overlap cap; "
    "internal offsets remain visually reconstructed"
)

collection = bpy.data.collections.new(COLLECTION_NAME)
scene.collection.children.link(collection)

MAT_ORANGE = material("JLG_Blockout_Orange", (0.93, 0.42, 0.04, 1.0), 0.06, 0.58)
MAT_ORANGE_DEEP = material("JLG_Blockout_OrangeDeep", (0.72, 0.28, 0.03, 1.0), 0.08, 0.64)
MAT_DARK = material("JLG_Blockout_Dark", (0.045, 0.05, 0.048, 1.0), 0.14, 0.74)
MAT_TIRE = material("JLG_Blockout_Tire", (0.02, 0.022, 0.02, 1.0), 0.0, 0.94)
MAT_METAL = material("JLG_Blockout_Metal", (0.38, 0.40, 0.36, 1.0), 0.62, 0.42)
MAT_HIT = material("JLG_Interaction_Volume", (0.0, 0.0, 0.0, 0.0), 0.0, 1.0)

root = empty("600S_ROOT", None)
root["asset_version"] = ASSET_VERSION
root["authorship"] = "owned-simplified-reconstruction"
root["generation_scope"] = "June/July 2026 current-generation 600S"
root["units"] = "meters"
root["ground_clearance_m"] = GROUND_CLEARANCE_M
root["tailswing_m"] = TAILSWING_M
root["telescope_travel_m"] = TELESCOPE_TRAVEL_M
root["platform_leveling"] = "counter_rotate_local_z"
root["release"] = ASSET_VERSION

chassis = empty("Chassis", root)
box("Frame", (5.60, 1.75, 0.46), chassis, (-0.10, 0.0, 0.52), MAT_DARK, "chassis")
box("FrameRail_L", (5.20, 0.16, 0.22), chassis, (-0.05, 0.78, 0.72), MAT_DARK, "chassis")
box("FrameRail_R", (5.20, 0.16, 0.22), chassis, (-0.05, -0.78, 0.72), MAT_DARK, "chassis")
box("LowerDeck", (4.55, 1.70, 0.12), chassis, (0.05, 0.0, 1.08), MAT_ORANGE, "chassis", round=0.02)
box("BellyPan", (4.20, 1.28, 0.08), chassis, (-0.15, 0.0, 0.33), MAT_DARK, "chassis")
box("AxleFront", (0.28, 2.05, 0.28), chassis, (1.25, 0.0, 0.65), MAT_METAL, "chassis", round=0.04)
box("AxleRear", (0.28, 2.05, 0.28), chassis, (-1.25, 0.0, 0.65), MAT_METAL, "chassis", round=0.04)
box("AxlePumpkin_F", (0.46, 0.62, 0.36), chassis, (1.25, 0.0, 0.58), MAT_METAL, "chassis", round=0.05)
box("AxlePumpkin_R", (0.46, 0.62, 0.36), chassis, (-1.25, 0.0, 0.58), MAT_METAL, "chassis", round=0.05)
box("BoomRest", (0.62, 0.92, 0.18), chassis, (2.20, 0.0, 1.68), MAT_METAL, "chassis", round=0.03)
box("BoomRestPad", (0.42, 0.52, 0.06), chassis, (2.20, 0.0, 1.79), MAT_DARK, "chassis")
box("SideStep_L", (0.55, 0.28, 0.08), chassis, (0.85, 0.92, 1.02), MAT_METAL, "chassis")
box("SideStep_R", (0.55, 0.28, 0.08), chassis, (0.85, -0.92, 1.02), MAT_METAL, "chassis")
add_wheel("Wheel_FL", 1.25, 1.04, True)
add_wheel("Wheel_FR", 1.25, -1.04, True)
add_wheel("Wheel_RL", -1.25, 1.04, False)
add_wheel("Wheel_RR", -1.25, -1.04, False)

turntable_pivot = empty("TurntablePivot", root, (-0.45, 0.0, 1.18))
turntable_pivot["authority"] = "visual_blockout_pending_manual_offset"
turntable = empty("Turntable", turntable_pivot)
cylinder_mesh("SlewRing", 0.78, 0.16, turntable, (0.0, 0.0, 0.08), (0.0, 0.0, 0.0), MAT_METAL, "turntable", 36)
box("UpperDeck", (2.72, 1.88, 0.16), turntable, (-0.18, 0.0, 0.24), MAT_ORANGE, "turntable", round=0.03)
box("EngineCover", (1.62, 0.62, 0.72), turntable, (-0.22, 0.74, 0.78), MAT_DARK, "turntable", round=0.04)
box("EngineCover_R", (1.62, 0.62, 0.72), turntable, (-0.22, -0.74, 0.78), MAT_DARK, "turntable", round=0.04)
box("HoodLip_L", (1.40, 0.50, 0.08), turntable, (-0.18, 0.74, 1.16), MAT_DARK, "turntable")
box("HoodLip_R", (1.40, 0.50, 0.08), turntable, (-0.18, -0.74, 1.16), MAT_DARK, "turntable")
box(
    "Counterweight", (COUNTERWEIGHT_LENGTH_M, 2.08, 1.08), turntable,
    (COUNTERWEIGHT_CENTER_X, 0.0, 0.66), MAT_ORANGE, "turntable", round=0.06,
)
box("CounterweightCap", (1.20, 1.86, 0.20), turntable, (-1.80, 0.0, 1.16), MAT_ORANGE_DEEP, "turntable", round=0.04)
box("Controls", (0.38, 0.52, 0.58), turntable, (0.88, -0.62, 0.72), MAT_DARK, "turntable", round=0.025)
box("GroundControlPanel", (0.08, 0.36, 0.28), turntable, (1.10, -0.62, 0.72), MAT_METAL, "turntable")

boom_pivot = empty("BoomPivot", turntable, (-0.55, 0.0, 0.92))
boom_pivot["authority"] = "visual_blockout_pending_manual_hinge"
main_boom = empty("MainBoom", boom_pivot)
box("MainBoomShell", (5.60, 0.62, 0.56), main_boom, (2.80, 0.0, 0.0), MAT_ORANGE, "boom")
box("BoomCheek_L", (0.62, 0.08, 0.62), main_boom, (0.12, 0.37, 0.0), MAT_METAL, "boom")
box("BoomCheek_R", (0.62, 0.08, 0.62), main_boom, (0.12, -0.37, 0.0), MAT_METAL, "boom")
box("BoomCollar", (0.14, 0.70, 0.64), main_boom, (5.53, 0.0, 0.0), MAT_METAL, "boom")
cylinder_mesh("BoomPivotPin", 0.28, 0.86, main_boom, (0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_METAL, "boom", 24)

telescope = empty("Telescope", main_boom, (4.65, 0.0, 0.0))
telescope["authority"] = "visual_blockout_pending_manual_nested_length"
telescope["telescope_travel_m"] = TELESCOPE_TRAVEL_M
box("TelescopeShell", (1.15, 0.46, 0.40), telescope, (0.575, 0.0, 0.0), MAT_DARK, "boom")
box("TelescopeWearPad", (0.18, 0.50, 0.44), telescope, (0.08, 0.0, 0.0), MAT_METAL, "boom")
box("BoomHead", (0.24, 0.40, 0.34), telescope, (1.13, 0.0, 0.0), MAT_METAL, "boom", round=0.03)

platform_pivot = empty("PlatformPivot", telescope, (PLATFORM_PIVOT_X, 0.0, 0.0))
platform_pivot["authority"] = "visual_blockout_pending_manual_rotator_center"
platform_pivot["platform_leveling"] = "counter_rotate_local_z"
platform = empty("Platform", platform_pivot)
box("PlatformDeck", (0.91, 2.44, 0.10), platform, (0.455, 0.0, -0.72), MAT_ORANGE, "platform")
box("PlatformToeboard_L", (0.88, 0.04, 0.14), platform, (0.455, 1.20, -0.60), MAT_ORANGE_DEEP, "platform")
box("PlatformToeboard_R", (0.88, 0.04, 0.14), platform, (0.455, -1.20, -0.60), MAT_ORANGE_DEEP, "platform")
box("PlatformToeboard_F", (0.04, 2.40, 0.14), platform, (0.89, 0.0, -0.60), MAT_ORANGE_DEEP, "platform")
box("PlatformToeboard_B", (0.04, 2.40, 0.14), platform, (0.02, 0.0, -0.60), MAT_ORANGE_DEEP, "platform")
box("PlatformControls", (0.20, 0.50, 0.36), platform, (0.74, -0.86, -0.38), MAT_DARK, "platform", round=0.02)
box("PlatformControlFace", (0.04, 0.40, 0.24), platform, (0.86, -0.86, -0.34), MAT_METAL, "platform")

post_x = (0.06, 0.85)
post_y = (-1.19, 1.19)
post_bottom_z = -0.66
post_top_z = 0.40
rail_top_r = 0.026
rail_mid_r = 0.022
rail_top_z = post_top_z - rail_top_r
rail_mid_z = 0.14
for x in post_x:
    for y in post_y:
        side = "L" if y > 0 else "R"
        end = "B" if x < 0.4 else "F"
        tube(f"PlatformPost_{end}{side}", (x, y, post_bottom_z), (x, y, post_top_z), 0.028, platform, MAT_METAL, "platform")
for x in post_x:
    tag = "B" if x < 0.4 else "F"
    tube(f"PlatformRailTop_{tag}", (x, post_y[0], rail_top_z), (x, post_y[1], rail_top_z), rail_top_r, platform, MAT_METAL, "platform")
    tube(f"PlatformRailMid_{tag}", (x, post_y[0], rail_mid_z), (x, post_y[1], rail_mid_z), rail_mid_r, platform, MAT_METAL, "platform")
for y in post_y:
    tag = "L" if y > 0 else "R"
    tube(f"PlatformRailTop_{tag}", (post_x[0], y, rail_top_z), (post_x[1], y, rail_top_z), rail_top_r, platform, MAT_METAL, "platform")
    tube(f"PlatformRailMid_{tag}", (post_x[0], y, rail_mid_z), (post_x[1], y, rail_mid_z), rail_mid_r, platform, MAT_METAL, "platform")

lift_cylinder = empty("LiftCylinder", boom_pivot)
lift_cylinder["component"] = "boom"
lift_cylinder["authority"] = "geometry_deferred_unresolved_anchors"
lift_cylinder["visual_state"] = "contract_node_only"

box("Chassis_Hit", (5.70, 2.48, 1.28), chassis, (-0.05, 0.0, 0.68), MAT_HIT, "chassis", hit=True)
box("Turntable_Hit", (3.80, 2.16, 1.30), turntable, (-0.56, 0.0, 0.65), MAT_HIT, "turntable", hit=True)
box("Boom_Hit", (5.60, 0.86, 0.80), main_boom, (2.80, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Telescope_Hit", (1.26, 0.70, 0.64), telescope, (0.62, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Platform_Hit", (0.91, 2.44, 1.17), platform, (0.455, 0.0, -0.185), MAT_HIT, "platform", hit=True)

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

frame_clearance = min(
    min((bpy.data.objects[name].matrix_world @ Vector(corner)).z for corner in bpy.data.objects[name].bound_box)
    for name in ("Frame", "BellyPan")
)
if not math.isclose(frame_clearance, GROUND_CLEARANCE_M, abs_tol=0.002):
    raise RuntimeError(f"Ground-clearance drift: {frame_clearance:.4f} m != {GROUND_CLEARANCE_M:.4f} m")

counterweight = bpy.data.objects["Counterweight"]
counterweight_rear_x = min((counterweight.matrix_world @ Vector(corner)).x for corner in counterweight.bound_box)
slew_x = turntable_pivot.matrix_world.translation.x
tailswing = (slew_x - counterweight_rear_x) - CHASSIS_HALF_WIDTH_M
if not math.isclose(tailswing, TAILSWING_M, abs_tol=0.002):
    raise RuntimeError(f"Tailswing drift: {tailswing:.4f} m != {TAILSWING_M:.4f} m")

deck = bpy.data.objects["PlatformDeck"]
if not math.isclose(deck.dimensions.x, PLATFORM_SIZE_M.x, abs_tol=0.002) or not math.isclose(
    deck.dimensions.y, PLATFORM_SIZE_M.y, abs_tol=0.002
):
    raise RuntimeError(f"Platform envelope drift: {tuple(deck.dimensions)}")

main_end_x = 5.60
telescope_start_x = 4.65
overlap_100 = main_end_x - (telescope_start_x + TELESCOPE_TRAVEL_M)
if overlap_100 <= 0.001:
    raise RuntimeError(f"Telescope would separate at 100% travel: overlap {overlap_100:.4f} m")

for obj in objects:
    if any(abs(axis - 1.0) > 1e-6 for axis in obj.scale):
        raise RuntimeError(f"Non-identity scale on {obj.name}: {tuple(obj.scale)}")

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
    "asset": "600S Blockout v0.2",
    "asset_version": ASSET_VERSION,
    "blend_path": str(BLEND_PATH),
    "glb_path": str(GLB_PATH),
    "object_count": len(objects),
    "visible_bounds_min_m": [round(value, 4) for value in minimum],
    "visible_bounds_max_m": [round(value, 4) for value in maximum],
    "visible_dimensions_m": [round(value, 4) for value in dimensions],
    "wheelbase_m": WHEELBASE_M,
    "ground_clearance_m": round(frame_clearance, 4),
    "tailswing_m": round(tailswing, 4),
    "platform_envelope_m": [PLATFORM_SIZE_M.x, PLATFORM_SIZE_M.y],
    "telescope_travel_m": TELESCOPE_TRAVEL_M,
    "telescope_overlap_at_100_m": round(overlap_100, 4),
    "scene_count": len(bpy.data.scenes),
}
print(json.dumps(result, indent=2, sort_keys=True))
