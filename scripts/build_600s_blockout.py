"""Build and export the evidence-bounded detailed 600S Showcase v1.1."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


_SCRIPT = Path(globals().get("__file__") or globals()["_jlg_script"]).resolve()
PROJECT_ROOT = _SCRIPT.parents[1]
BLEND_PATH = PROJECT_ROOT / "source/blender/600s-showcase-v1.1.blend"
MIGRATION_SOURCE_PATHS = {
    PROJECT_ROOT / "source/blender/600s-showcase-v1.0.blend",
    PROJECT_ROOT / "source/blender/600s-detailed-v0.3.blend",
    PROJECT_ROOT / "source/blender/600s-blockout-v0.2.blend",
    PROJECT_ROOT / "source/blender/600s-blockout-v0.1.blend",
}
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"
SCENE_NAME = "JLG_600S_SHOWCASE_V11"
COLLECTION_NAME = "JLG_600S_SHOWCASE_V11"

PUBLISHED_ENVELOPE_M = Vector((8.71, 2.48, 2.50))
PLATFORM_SIZE_M = Vector((0.91, 2.44))
WHEELBASE_M = 2.50
GROUND_CLEARANCE_M = 0.29
TAILSWING_M = 1.22
TELESCOPE_TRAVEL_M = 0.90
TELESCOPE_MID_TRAVEL_M = 0.36
TELESCOPE_FLY_TRAVEL_M = 0.54
POWERTRACK_LINK_LENGTH_M = 0.198
POWERTRACK_LINK_PITCH_M = 0.20
POWERTRACK_BASE_DISPLAY_COUNT = 18
POWERTRACK_MOVING_DISPLAY_COUNT = 9
POWERTRACK_MAX_VISIBLE_GAP_M = 0.004
ASSET_VERSION = "1.1.0"
CONFIGURATION_ID = "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696"

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


def set_authority(obj: bpy.types.Object, value: str, evidence: str | None = None) -> bpy.types.Object:
    if value not in {"verified", "derived", "reconstructed", "deferred", "interaction_contract"}:
        raise ValueError(f"Unsupported authority class: {value}")
    obj["authority"] = value
    if evidence:
        obj["evidence"] = evidence
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
    authority: str = "reconstructed",
    evidence: str | None = None,
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
    set_authority(obj, "interaction_contract" if hit else authority, evidence)
    obj.display_type = "WIRE" if hit else "TEXTURED"
    obj.show_in_front = hit
    if round:
        bevel(obj, round, 2)
    return obj


def prism_xz(
    name: str,
    profile: tuple[tuple[float, float], ...],
    depth: float,
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    component: str,
    *,
    authority: str = "reconstructed",
    evidence: str | None = None,
    round: float | None = None,
) -> bpy.types.Object:
    """Extrude a side-view X/Z profile across local Y."""
    half = depth * 0.5
    count = len(profile)
    vertices = [(x, -half, z) for x, z in profile] + [(x, half, z) for x, z in profile]
    faces = [tuple(range(count)), tuple(range(count, count * 2))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, count + nxt, count + index))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = link_object(bpy.data.objects.new(name, mesh))
    obj.location = location
    obj.parent = parent
    obj.scale = (1.0, 1.0, 1.0)
    obj["component"] = component
    set_authority(obj, authority, evidence)
    if round:
        bevel(obj, round, 2)
    return obj


def torus_y(
    name: str,
    major_radius: float,
    minor_radius: float,
    parent: bpy.types.Object,
    location: tuple[float, float, float],
    mat: bpy.types.Material,
    component: str,
    major_segments: int = 28,
    minor_segments: int = 8,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for major_index in range(major_segments):
        theta = math.tau * major_index / major_segments
        for minor_index in range(minor_segments):
            phi = math.tau * minor_index / minor_segments
            radial = major_radius + minor_radius * math.cos(phi)
            vertices.append((radial * math.cos(theta), minor_radius * math.sin(phi), radial * math.sin(theta)))
    for major_index in range(major_segments):
        major_next = (major_index + 1) % major_segments
        for minor_index in range(minor_segments):
            minor_next = (minor_index + 1) % minor_segments
            a = major_index * minor_segments + minor_index
            b = major_next * minor_segments + minor_index
            c = major_next * minor_segments + minor_next
            d = major_index * minor_segments + minor_next
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = link_object(bpy.data.objects.new(name, mesh))
    obj.location = location
    obj.parent = parent
    obj.scale = (1.0, 1.0, 1.0)
    obj["component"] = component
    set_authority(obj, "reconstructed", "3122579800:46-50; 3122579600:141")
    shade_smooth(obj)
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
    authority: str = "reconstructed",
    evidence: str | None = None,
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
    set_authority(obj, authority, evidence)
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
    *,
    authority: str = "reconstructed",
    evidence: str | None = None,
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
    set_authority(obj, authority, evidence)
    shade_smooth(obj)
    return obj


def tube_path(
    name: str,
    points: tuple[tuple[float, float, float], ...],
    radius: float,
    parent: bpy.types.Object,
    mat: bpy.types.Material,
    component: str,
    segments: int = 10,
    *,
    authority: str = "reconstructed",
    evidence: str | None = None,
) -> bpy.types.Object:
    group = empty(name, parent)
    group["component"] = component
    set_authority(group, authority, evidence)
    for index, (start, end) in enumerate(zip(points, points[1:]), start=1):
        tube(
            f"{name}_Segment_{index:02d}", start, end, radius, group, mat,
            component, segments, authority=authority, evidence=evidence,
        )
    return group


def add_wheel(name: str, x: float, y: float, front: bool) -> bpy.types.Object:
    pivot = empty(name, chassis, (x, y, 0.65))
    pivot["component"] = "chassis"
    pivot["steering_pivot"] = front
    set_authority(pivot, "derived" if front else "verified", "3122579800:20-35")
    roll = empty(f"{name}_Roll", pivot)
    roll["component"] = "chassis"
    roll["runtime_axis"] = "local_y_blender_local_z_gltf"
    set_authority(roll, "derived", "3122579800:20-50; tire roll separated from steering/axle transform")
    torus_y(f"{name}_Tire", 0.45, 0.18, roll, (0.0, 0.0, 0.0), MAT_TIRE, "chassis")
    for tread_index in range(18):
        angle = math.tau * tread_index / 18
        radius = 0.6117
        tread = box(
            f"{name}_Tread_{tread_index + 1:02d}",
            (0.18, 0.40, 0.065),
            roll,
            (radius * math.cos(angle), 0.0, radius * math.sin(angle)),
            MAT_TIRE,
            "chassis",
            authority="reconstructed",
            evidence="3122579800:46-50",
        )
        tread.rotation_euler.y = math.pi / 2.0 - angle
    cylinder_mesh(
        f"{name}_Rim", 0.31, 0.31, roll, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_RIM, "chassis", 28,
        evidence="3122579800:46-50",
    )
    cylinder_mesh(
        f"{name}_DriveHub", 0.145, 0.35, roll, (0.0, 0.0, 0.0),
        (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "chassis", 20,
        evidence="3122579800:32-40",
    )
    for lug_index in range(9):
        angle = math.tau * lug_index / 9
        cylinder_mesh(
            f"{name}_Lug_{lug_index + 1:02d}", 0.018, 0.035, roll,
            (0.095 * math.cos(angle), -0.175 if y < 0 else 0.175, 0.095 * math.sin(angle)),
            (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "chassis", 8, smooth=False,
            evidence="3122579800:32-50",
        )
    knuckle = box(
        f"{name}_SteerKnuckle" if front else f"{name}_AxleEnd",
        (0.20, 0.16, 0.34), pivot, (0.0, -0.20 if y > 0 else 0.20, 0.0),
        MAT_DARK_METAL, "chassis", round=0.025, evidence="3122579800:28-35",
    )
    knuckle["steering"] = "front_2ws" if front else "rear_fixed"
    return pivot


def articulated_hose(
    name: str,
    fixed_start: tuple[float, float, float],
    fixed_end: tuple[float, float, float],
    moving_parent: bpy.types.Object,
    moving_anchor: tuple[float, float, float],
) -> bpy.types.Object:
    """Build one fixed hose leg plus one evidence-bounded moving visual leg."""
    group = empty(name, chassis)
    group["component"] = "chassis"
    set_authority(group, "reconstructed", "3122579800:28-31; routing reconstructed")
    tube(
        f"{name}_Segment_01", fixed_start, fixed_end, 0.015, group, MAT_HYDRAULIC, "chassis",
        evidence="3122579800:28-31; routing reconstructed",
    )
    lower = empty(f"{name}_LowerAnchor", group, fixed_end)
    upper = empty(f"{name}_UpperAnchor", moving_parent, moving_anchor)
    set_authority(lower, "reconstructed", "MECHANISM_EVIDENCE:STR-003; hose endpoint reconstructed")
    set_authority(upper, "reconstructed", "MECHANISM_EVIDENCE:STR-003; hose endpoint reconstructed")
    moving_parent_world = moving_parent.location + Vector(moving_anchor)
    direction = moving_parent_world - Vector(fixed_end)
    flexible = empty(f"{name}_Flexible", group, fixed_end)
    flexible["runtime_solver"] = "two_anchor_visual_hose"
    flexible["nominal_length_m"] = direction.length
    flexible.rotation_euler = direction.to_track_quat("X", "Z").to_euler()
    set_authority(flexible, "reconstructed", "3122579800:28-31; endpoint-follow visual solver")
    tube(
        f"{name}_Segment_02", (0.0, 0.0, 0.0), (direction.length, 0.0, 0.0), 0.015,
        flexible, MAT_HYDRAULIC, "chassis", evidence="3122579800:28-31; routing reconstructed",
    )
    return group


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


def world_aabb(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    """Return an object's world-space bounds for build-time attachment checks."""
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(point[axis] for point in corners) for axis in range(3)))
    maximum = Vector((max(point[axis] for point in corners) for axis in range(3)))
    return minimum, maximum


def assert_attached(part_name: str, support_name: str, minimum_overlap_m: float = 0.004) -> None:
    """Fail the build when a visible accessory drifts away from its support."""
    part_min, part_max = world_aabb(bpy.data.objects[part_name])
    support_min, support_max = world_aabb(bpy.data.objects[support_name])
    overlap = Vector((
        min(part_max[axis], support_max[axis]) - max(part_min[axis], support_min[axis])
        for axis in range(3)
    ))
    if any(value < minimum_overlap_m for value in overlap):
        raise RuntimeError(
            f"Detached accessory: {part_name} does not overlap {support_name}; "
            f"axis overlap={tuple(round(value, 4) for value in overlap)}"
        )


def assert_near(part_name: str, neighbor_name: str, maximum_gap_m: float) -> None:
    """Fail when adjacent presentation geometry has a visible world-space air gap."""
    part_min, part_max = world_aabb(bpy.data.objects[part_name])
    neighbor_min, neighbor_max = world_aabb(bpy.data.objects[neighbor_name])
    gap = Vector((
        max(part_min[axis] - neighbor_max[axis], neighbor_min[axis] - part_max[axis], 0.0)
        for axis in range(3)
    ))
    if any(value > maximum_gap_m for value in gap):
        raise RuntimeError(
            f"Disconnected presentation geometry: {part_name} -> {neighbor_name}; "
            f"axis gap={tuple(round(value, 4) for value in gap)}"
        )


if bpy.data.filepath:
    open_path = Path(bpy.data.filepath).resolve()
    allowed_paths = {BLEND_PATH.resolve(), *(path.resolve() for path in MIGRATION_SOURCE_PATHS)}
    if open_path not in allowed_paths:
        raise RuntimeError(f"Refusing to replace an unrelated saved Blender file: {open_path}")

generated_prefixes = ("JLG_600S_BLOCKOUT", "JLG_600S_DETAILED", "JLG_600S_SHOWCASE")
generated_collections = [
    value for value in list(bpy.data.collections)
    if value.name.startswith(generated_prefixes)
]
generated_objects = {obj for value in generated_collections for obj in value.all_objects}
generated_meshes = {obj.data for obj in generated_objects if obj.type == "MESH" and obj.data}
generated_materials = {
    material_slot.material
    for obj in generated_objects
    for material_slot in obj.material_slots
    if material_slot.material
}
for old_object in generated_objects:
    bpy.data.objects.remove(old_object, do_unlink=True)
for old_collection in generated_collections:
    bpy.data.collections.remove(old_collection)
for old_mesh in generated_meshes:
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
for old_material in generated_materials:
    if old_material.users == 0:
        bpy.data.materials.remove(old_material)

scene = bpy.data.scenes.new("JLG_600S_BUILD_TEMP")
if bpy.context.window:
    bpy.context.window.scene = scene
for old_scene in list(bpy.data.scenes):
    if old_scene != scene:
        bpy.data.scenes.remove(old_scene)
scene.name = SCENE_NAME

scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "METERS"
scene.unit_settings.scale_length = 1.0
scene["asset"] = "600S Showcase reconstruction v1.1"
scene["asset_version"] = ASSET_VERSION
scene["configuration_id"] = CONFIGURATION_ID
scene["published_envelope_m"] = list(PUBLISHED_ENVELOPE_M)
scene["wheelbase_m"] = WHEELBASE_M
scene["ground_clearance_m"] = GROUND_CLEARANCE_M
scene["tailswing_m"] = TAILSWING_M
scene["telescope_travel_m"] = TELESCOPE_TRAVEL_M
scene["telescope_mid_travel_m"] = TELESCOPE_MID_TRAVEL_M
scene["telescope_fly_travel_m"] = TELESCOPE_FLY_TRAVEL_M
scene["platform_leveling"] = "counter_rotate_local_z"
scene["evidence_boundary"] = (
    "published envelopes are approximate and verified; assembly relationships follow PVC 2607; "
    "undimensioned offsets and forms remain reconstructed; no safety or service simulation"
)

collection = bpy.data.collections.new(COLLECTION_NAME)
scene.collection.children.link(collection)

MAT_ORANGE = material("JLG_Orange_PowderCoat", (0.94, 0.30, 0.035, 1.0), 0.04, 0.48)
MAT_ORANGE_DEEP = material("JLG_Orange_Shadow", (0.64, 0.16, 0.025, 1.0), 0.05, 0.58)
MAT_BOOM = material("JLG_Boom_Cream", (0.78, 0.75, 0.57, 1.0), 0.03, 0.52)
MAT_DARK = material("JLG_Black_PowderCoat", (0.025, 0.03, 0.03, 1.0), 0.18, 0.64)
MAT_TIRE = material("JLG_Tire_Rubber", (0.012, 0.014, 0.013, 1.0), 0.0, 0.92)
MAT_METAL = material("JLG_Zinc_Steel", (0.42, 0.44, 0.42, 1.0), 0.68, 0.38)
MAT_DARK_METAL = material("JLG_Dark_Steel", (0.10, 0.115, 0.11, 1.0), 0.72, 0.44)
MAT_RIM = material("JLG_Rim_OffWhite", (0.72, 0.72, 0.66, 1.0), 0.58, 0.42)
MAT_HYDRAULIC = material("JLG_Hydraulic_Black", (0.018, 0.022, 0.021, 1.0), 0.12, 0.70)
MAT_ELECTRICAL = material("JLG_Electrical_Loom", (0.045, 0.050, 0.048, 1.0), 0.02, 0.82)
MAT_CONTROL_CABLE = material("JLG_Control_Cable", (0.075, 0.080, 0.075, 1.0), 0.03, 0.76)
MAT_WIRE_ROPE = material("JLG_Wire_Rope", (0.30, 0.32, 0.30, 1.0), 0.78, 0.42)
MAT_POWERTRACK = material("JLG_Powertrack_Carrier", (0.030, 0.034, 0.033, 1.0), 0.06, 0.78)
MAT_SENSOR = material("JLG_Sensor_Black", (0.035, 0.04, 0.04, 1.0), 0.04, 0.48)
MAT_RED = material("JLG_Control_Red", (0.64, 0.015, 0.01, 1.0), 0.02, 0.42)
MAT_AMBER = material("JLG_Beacon_Amber", (1.0, 0.32, 0.015, 0.68), 0.0, 0.18)
MAT_WHITE = material("JLG_Label_White", (0.92, 0.91, 0.84, 1.0), 0.02, 0.55)
MAT_WARNING = material("JLG_Warning_Yellow", (0.98, 0.62, 0.02, 1.0), 0.01, 0.50)
MAT_HIT = material("JLG_Interaction_Volume", (0.0, 0.0, 0.0, 0.0), 0.0, 1.0)

root = empty("600S_ROOT", None)
root["asset_version"] = ASSET_VERSION
root["authorship"] = "owned-simplified-reconstruction"
root["generation_scope"] = "June/July 2026 current-generation 600S"
root["configuration_id"] = CONFIGURATION_ID
root["configuration"] = "US ANSI; B3; 4WD/2WS; Deutz D2.9 49 hp; standard FF; 36x96 rapid platform"
root["units"] = "meters"
root["ground_clearance_m"] = GROUND_CLEARANCE_M
root["tailswing_m"] = TAILSWING_M
root["telescope_travel_m"] = TELESCOPE_TRAVEL_M
root["telescope_mid_travel_m"] = TELESCOPE_MID_TRAVEL_M
root["telescope_fly_travel_m"] = TELESCOPE_FLY_TRAVEL_M
root["telescope_staging"] = "evidence_bounded_coupled_visual"
root["platform_leveling"] = "counter_rotate_local_z"
root["release"] = ASSET_VERSION

chassis = empty("Chassis", root)
set_authority(chassis, "verified", "3122579800:19-68")
box("Frame", (3.50, 0.78, 0.22), chassis, (-0.10, 0.0, 0.40), MAT_DARK, "chassis", authority="derived", evidence="3131050:R0626_04")
front_pod_profile = (
    (-0.98, -0.28), (0.72, -0.28), (1.02, -0.12),
    (1.10, 0.22), (0.78, 0.48), (-0.68, 0.48), (-1.04, 0.18),
)
prism_xz(
    "ChassisFrontPod", front_pod_profile, 1.38, chassis, (1.00, 0.0, 0.64),
    MAT_ORANGE, "chassis", authority="reconstructed", evidence="3122579800:20-35,62; user side-profile reference",
    round=0.045,
)
bridge_profile = ((-1.25, -0.17), (1.15, -0.17), (1.24, 0.12), (0.92, 0.25), (-1.04, 0.25), (-1.28, 0.08))
prism_xz(
    "ChassisCenterBridge", bridge_profile, 1.02, chassis, (-0.15, 0.0, 0.72),
    MAT_ORANGE_DEEP, "chassis", authority="reconstructed", evidence="3122579800:20-35; user side-profile reference",
    round=0.035,
)
for side, y in (("L", 0.705), ("R", -0.705)):
    box(
        f"ChassisFrontPodInset_{side}", (0.86, 0.025, 0.22), chassis, (1.12, y, 0.72),
        MAT_DARK, "chassis", round=0.035, evidence="user side-profile reference; inset placement reconstructed",
    )
box("FrameRail_L", (3.75, 0.14, 0.18), chassis, (-0.15, 0.58, 0.65), MAT_DARK_METAL, "chassis", round=0.025, evidence="3122579800:62")
box("FrameRail_R", (3.75, 0.14, 0.18), chassis, (-0.15, -0.58, 0.65), MAT_DARK_METAL, "chassis", round=0.025, evidence="3122579800:62")
box("LowerDeck", (3.65, 1.52, 0.10), chassis, (-0.05, 0.0, 1.07), MAT_DARK_METAL, "chassis", round=0.025, evidence="3122579800:62")
box("ChassisTopPlate", (2.90, 1.50, 0.06), chassis, (-0.30, 0.0, 1.14), MAT_ORANGE, "chassis", round=0.025, evidence="3122579800:62; user side-profile reference")
box("BellyPan", (2.55, 0.95, 0.08), chassis, (-0.20, 0.0, 0.33), MAT_DARK, "chassis", evidence="3122579800:62")
box("AxleFront", (0.30, 2.05, 0.26), chassis, (1.25, 0.0, 0.65), MAT_DARK_METAL, "chassis", round=0.05, evidence="3122579800:20-21")
box("AxleRear", (0.30, 2.05, 0.26), chassis, (-1.25, 0.0, 0.65), MAT_DARK_METAL, "chassis", round=0.05, evidence="3122579800:24-26")
prism_xz(
    "AxleCradle_Front", ((-0.34, -0.28), (0.34, -0.28), (0.44, 0.18), (0.22, 0.34), (-0.22, 0.34), (-0.44, 0.18)),
    1.28, chassis, (1.25, 0.0, 0.64), MAT_ORANGE_DEEP, "chassis", authority="reconstructed",
    evidence="3122579800:20-21; cradle envelope reconstructed", round=0.035,
)
box(
    "AxleCradle_Rear", (0.52, 0.82, 0.40), chassis, (-1.25, 0.0, 0.65),
    MAT_DARK_METAL, "chassis", authority="reconstructed", evidence="3122579800:24-26; exposed rear pivot support",
    round=0.055,
)
box("AxlePumpkin_F", (0.48, 0.62, 0.38), chassis, (1.25, 0.0, 0.58), MAT_DARK_METAL, "chassis", round=0.06, evidence="3122579800:20-21")
box("AxlePumpkin_R", (0.48, 0.62, 0.38), chassis, (-1.25, 0.0, 0.58), MAT_DARK_METAL, "chassis", round=0.06, evidence="3122579800:24-26")
box("BoomRest", (0.62, 0.92, 0.18), chassis, (2.20, 0.0, 1.68), MAT_METAL, "chassis", round=0.03)
box("BoomRestPad", (0.42, 0.52, 0.06), chassis, (2.20, 0.0, 1.79), MAT_DARK, "chassis")
for side, y in (("L", 0.32), ("R", -0.32)):
    box(
        f"BoomRestPost_{side}", (0.18, 0.14, 0.80), chassis, (2.05, y, 1.26),
        MAT_ORANGE_DEEP, "chassis", round=0.025,
        evidence="3122579800:62; upright boom-rest support placement reconstructed",
    )
for side, y in (("L", 0.83), ("R", -0.83)):
    box(
        f"SideStep_{side}", (0.55, 0.22, 0.06), chassis, (0.85, y, 1.04),
        MAT_DARK_METAL, "chassis", round=0.018,
        evidence="3122579800:62; inset to meet chassis deck",
    )
    box(
        f"SideStepBracket_{side}", (0.12, 0.22, 0.18), chassis, (0.85, 0.73 if y > 0 else -0.73, 0.95),
        MAT_DARK_METAL, "chassis", round=0.018,
        evidence="3122579800:62; support bracket placement reconstructed",
    )
wheel_fl = add_wheel("Wheel_FL", 1.25, 1.04, True)
wheel_fr = add_wheel("Wheel_FR", 1.25, -1.04, True)
add_wheel("Wheel_RL", -1.25, 1.04, False)
add_wheel("Wheel_RR", -1.25, -1.04, False)

steer_tie_rod = empty("SteerTieRod", chassis)
set_authority(steer_tie_rod, "reconstructed", "3122579800:28-29; anchors reconstructed")
steer_tie_rod["runtime_solver"] = "two_anchor_visual_link"
steer_tie_rod.location = (1.25, -0.82, 0.72)
steer_tie_rod.rotation_euler = (0.0, 0.0, math.pi / 2.0)
steer_tie_lower = empty("SteerTieRodLowerAnchor", wheel_fr, (0.0, 0.22, 0.07))
steer_tie_upper = empty("SteerTieRodUpperAnchor", wheel_fl, (0.0, -0.22, 0.07))
set_authority(steer_tie_lower, "reconstructed", "MECHANISM_EVIDENCE:STR-001,STR-002")
set_authority(steer_tie_upper, "reconstructed", "MECHANISM_EVIDENCE:STR-001,STR-002")
tube("SteerTieRodBody", (0.0, 0.0, 0.0), (1.64, 0.0, 0.0), 0.035, steer_tie_rod, MAT_DARK_METAL, "chassis", 12, evidence="MECHANISM_EVIDENCE:STR-001,STR-002")

for side, wheel, body_y, wheel_y in (
    ("L", wheel_fl, 0.12, -0.22),
    ("R", wheel_fr, -0.12, 0.22),
):
    steer_cylinder = empty(f"SteerCylinder_{side}", chassis)
    set_authority(steer_cylinder, "reconstructed", "3122579800:28-29; anchors reconstructed")
    steer_cylinder["runtime_solver"] = "two_anchor_visual_cylinder"
    lower = empty(f"SteerCylinder_{side}_LowerAnchor", chassis, (1.08, body_y, 0.62))
    upper = empty(f"SteerCylinder_{side}_UpperAnchor", wheel, (0.0, wheel_y, 0.05))
    set_authority(lower, "reconstructed", "MECHANISM_EVIDENCE:STR-003")
    set_authority(upper, "reconstructed", "MECHANISM_EVIDENCE:STR-003")
    initial_lower = Vector((1.08, body_y, 0.62))
    initial_upper = Vector((1.25, 1.04 if side == "L" else -1.04, 0.65)) + Vector((0.0, wheel_y, 0.05))
    steer_cylinder.location = initial_lower
    steer_cylinder.rotation_euler = (initial_upper - initial_lower).to_track_quat("X", "Z").to_euler()
    tube(f"SteerCylinder_{side}_Barrel", (0.0, 0.0, 0.0), (0.38, 0.0, 0.0), 0.052, steer_cylinder, MAT_HYDRAULIC, "chassis", 14, evidence="3122579800:28-29")
    tube(f"SteerCylinder_{side}_Rod", (0.32, 0.0, 0.0), (0.72, 0.0, 0.0), 0.029, steer_cylinder, MAT_METAL, "chassis", 12, evidence="3122579800:28-29")
articulated_hose("SteerHydraulicHose_L", (0.70, 0.25, 0.73), (0.98, 0.42, 0.73), wheel_fl, (0.0, -0.22, 0.08))
articulated_hose("SteerHydraulicHose_R", (0.70, -0.25, 0.73), (0.98, -0.42, 0.73), wheel_fr, (0.0, 0.22, 0.08))
tube_path("ChassisDriveHarness_L", ((-1.95, 0.62, 0.82), (-0.25, 0.62, 0.82), (1.12, 0.62, 0.76)), 0.012, chassis, MAT_ELECTRICAL, "chassis", evidence="3122579800:908-920; routing reconstructed")
tube_path("ChassisDriveHarness_R", ((-1.95, -0.62, 0.82), (-0.25, -0.62, 0.82), (1.12, -0.62, 0.76)), 0.012, chassis, MAT_ELECTRICAL, "chassis", evidence="3122579800:908-920; routing reconstructed")
for side, y in (("L", 0.56), ("R", -0.56)):
    box(f"ForkPocket_{side}_Front", (0.74, 0.24, 0.15), chassis, (1.78, y, 0.45), MAT_DARK_METAL, "chassis", round=0.015, evidence="3131050:R0626_04")
    box(f"ForkPocket_{side}_Rear", (0.74, 0.24, 0.15), chassis, (-1.78, y, 0.45), MAT_DARK_METAL, "chassis", round=0.015, evidence="3131050:R0626_04")
for tag, x, y in (("FL", 1.50, 0.657), ("FR", 1.50, -0.657), ("RL", -1.55, 0.657), ("RR", -1.55, -0.657)):
    box(
        f"TieDownPocket_{tag}", (0.26, 0.035, 0.14), chassis, (x, y, 0.64),
        MAT_DARK, "chassis", round=0.024,
        evidence="3131050:R0626_04; flush transport-point cue, placement reconstructed",
    )

turntable_pivot = empty("TurntablePivot", root, (-0.45, 0.0, 1.18))
set_authority(turntable_pivot, "reconstructed", "3122579800:92; 3131050:R0626_04")
turntable = empty("Turntable", turntable_pivot)
set_authority(turntable, "verified", "3122579800:69-244")
cylinder_mesh("SlewRing", 0.78, 0.16, turntable, (0.0, 0.0, 0.08), (0.0, 0.0, 0.0), MAT_DARK_METAL, "turntable", 40, evidence="3122579800:86-94")
box("SlewRingBolts", (1.48, 1.48, 0.035), turntable, (0.0, 0.0, 0.18), MAT_METAL, "turntable", round=0.02, evidence="3122579800:92")
box("UpperFrame", (3.06, 1.84, 0.16), turntable, (-0.20, 0.0, 0.24), MAT_DARK_METAL, "turntable", round=0.035, evidence="3122579800:230")
hood_profile = ((-0.88, 0.12), (-0.82, 0.72), (-0.56, 1.08), (0.35, 1.16), (0.82, 0.92), (0.84, 0.16))
prism_xz("EngineCover", hood_profile, 0.60, turntable, (-0.18, 0.67, 0.10), MAT_ORANGE, "turntable", evidence="3122579800:194-204", round=0.055)
prism_xz("TankCover", hood_profile, 0.60, turntable, (-0.18, -0.67, 0.10), MAT_ORANGE, "turntable", evidence="3122579800:194-204", round=0.055)
box("EngineCoverSeam", (1.52, 0.018, 0.028), turntable, (-0.18, 0.36, 0.93), MAT_DARK, "turntable", evidence="3122579800:194-204")
box("TankCoverSeam", (1.52, 0.018, 0.028), turntable, (-0.18, -0.36, 0.93), MAT_DARK, "turntable", evidence="3122579800:194-204")
counter_profile = ((-2.3912, 0.16), (-2.36, 0.84), (-2.16, 1.14), (-1.70, 1.2112), (-0.48, 1.08), (0.08, 0.66), (0.34, 0.16))
prism_xz("Counterweight", counter_profile, 2.08, turntable, (0.0, 0.0, 0.0), MAT_ORANGE, "turntable", evidence="3122579800:230; 3131050:R0626_04", round=0.065)
box("CounterweightRearPanel", (0.035, 1.64, 0.62), turntable, (-2.415, 0.0, 0.68), MAT_ORANGE_DEEP, "turntable", round=0.02, evidence="3122579800:230")
box("EngineTray", (1.48, 0.54, 0.08), turntable, (-0.15, 0.67, 0.34), MAT_DARK_METAL, "turntable", evidence="3122579800:322-368")
box("FuelTank", (1.05, 0.48, 0.46), turntable, (-0.34, -0.67, 0.50), MAT_DARK, "turntable", round=0.08, authority="reconstructed", evidence="3122579800:106-120")
box("HydraulicTank", (0.88, 0.50, 0.55), turntable, (0.38, -0.67, 0.54), MAT_DARK_METAL, "turntable", round=0.03, authority="reconstructed", evidence="3122579800:106-120")
cylinder_mesh("FuelFillCap", 0.065, 0.035, turntable, (-0.62, -0.66, 0.82), (0.0, 0.0, 0.0), MAT_DARK, "turntable", 18, evidence="3122579800:106-120")
cylinder_mesh("HydraulicFillCap", 0.06, 0.04, turntable, (0.55, -0.66, 0.86), (0.0, 0.0, 0.0), MAT_WARNING, "turntable", 18, evidence="3122579800:106-120")
box("MainValveBank", (0.42, 0.34, 0.18), turntable, (0.28, 0.20, 0.42), MAT_METAL, "turntable", round=0.025, evidence="3122579800:70-84")
for coil_index, x in enumerate((0.14, 0.28, 0.42), start=1):
    cylinder_mesh(f"MainValveCoil_{coil_index}", 0.035, 0.12, turntable, (x, 0.41, 0.42), (math.pi / 2.0, 0.0, 0.0), MAT_SENSOR, "turntable", 12, evidence="3122579800:70-84")
box("EngineControlModule", (0.30, 0.10, 0.22), turntable, (-0.28, 0.40, 0.60), MAT_SENSOR, "turntable", round=0.025, evidence="3122579800:904-918")
tube_path("GroundControlHarness", ((0.88, -0.40, 0.64), (0.54, -0.24, 0.48), (0.28, 0.20, 0.50)), 0.016, turntable, MAT_ELECTRICAL, "turntable", evidence="3122579800:904-918; routing reconstructed")
tube_path("EngineHarness", ((-0.28, 0.40, 0.60), (-0.52, 0.44, 0.48), (-0.80, 0.48, 0.42)), 0.015, turntable, MAT_ELECTRICAL, "turntable", evidence="3122579800:904-918; routing reconstructed")
box("Controls", (0.38, 0.52, 0.58), turntable, (0.88, -0.62, 0.72), MAT_DARK, "turntable", round=0.035, evidence="3122579800:148-150")
box("GroundControlPanel", (0.07, 0.36, 0.30), turntable, (1.10, -0.62, 0.72), MAT_METAL, "turntable", round=0.015, evidence="3122579800:148-150")
for button_index, z in enumerate((0.63, 0.72, 0.81), start=1):
    cylinder_mesh(f"GroundControlButton_{button_index}", 0.025, 0.02, turntable, (1.14, -0.62, z), (0.0, math.pi / 2.0, 0.0), MAT_RED if button_index == 1 else MAT_DARK, "turntable", 10, smooth=False, evidence="3122579800:148-150")
cylinder_mesh("CS550Beacon", 0.08, 0.18, turntable, (-1.30, 0.78, 1.16), (0.0, 0.0, 0.0), MAT_AMBER, "turntable", 20, evidence="3131050:R0626_04")
box("CS550Base", (0.20, 0.20, 0.07), turntable, (-1.30, 0.78, 1.03), MAT_DARK, "turntable", round=0.025, evidence="3122579800:922-924")
box("RearCoolingGrille", (0.022, 1.28, 0.48), turntable, (-2.435, 0.0, 0.72), MAT_DARK, "turntable", round=0.012, evidence="3122579800:194-204")
for grille_index, z in enumerate((0.54, 0.62, 0.70, 0.78, 0.86), start=1):
    box(f"RearCoolingGrilleSlat_{grille_index}", (0.018, 1.20, 0.025), turntable, (-2.449, 0.0, z), MAT_DARK_METAL, "turntable", evidence="3122579800:194-204")
for side, y in (("Engine", 0.985), ("Tank", -0.985)):
    for latch_index, x in enumerate((-0.66, 0.32), start=1):
        box(f"{side}HoodLatch_{latch_index}", (0.10, 0.022, 0.055), turntable, (x, y, 0.52), MAT_DARK, "turntable", round=0.01, evidence="3122579800:194-204")
box("EngineServiceLabel", (0.42, 0.018, 0.16), turntable, (-0.28, 0.982, 0.78), MAT_WHITE, "turntable", round=0.008, evidence="3122579800:194-204")
box("TankServiceLabel", (0.36, 0.018, 0.14), turntable, (-0.28, -0.982, 0.78), MAT_WHITE, "turntable", round=0.008, evidence="3122579800:194-204")

boom_pivot = empty("BoomPivot", turntable, (-0.55, 0.0, 0.92))
set_authority(boom_pivot, "reconstructed", "3122579700:641,648")
main_boom = empty("MainBoom", boom_pivot)
set_authority(main_boom, "verified", "3122579600:28; 3122579700:641")
base_profile = ((0.0, -0.31), (4.78, -0.25), (5.12, -0.20), (5.12, 0.20), (4.78, 0.25), (0.0, 0.31))
prism_xz("BaseBoomShell", base_profile, 0.68, main_boom, (0.0, 0.0, 0.0), MAT_BOOM, "boom", evidence="3122579800:540; 3122579700:641", round=0.025)
for side, y in (("L", 0.39), ("R", -0.39)):
    prism_xz(f"BoomCheek_{side}", ((-0.18, -0.39), (0.58, -0.33), (0.74, 0.18), (0.42, 0.38), (-0.18, 0.34)), 0.07, main_boom, (0.0, y, 0.0), MAT_BOOM, "boom", evidence="3122579700:648", round=0.018)
cylinder_mesh("BoomPivotPin", 0.25, 0.90, main_boom, (0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "boom", 28, evidence="3122579700:648")
for index, x in enumerate((0.84, 1.18, 1.52, 1.86, 2.20, 2.54, 2.88, 3.22, 3.56), start=1):
    cylinder_mesh(f"BaseBoomServicePort_{index:02d}", 0.055, 0.012, main_boom, (x, 0.346, 0.24), (math.pi / 2.0, 0.0, 0.0), MAT_DARK, "boom", 12, evidence="3122579800:540")

powertrack = empty("Powertrack", main_boom, (0.0, 0.0, 0.0))
set_authority(powertrack, "verified", "MECHANISM_EVIDENCE:PWR-001,PWR-002")
powertrack["display_link_count_is_physical_claim"] = False
powertrack["display_link_length_m"] = POWERTRACK_LINK_LENGTH_M
powertrack["display_link_pitch_m"] = POWERTRACK_LINK_PITCH_M
powertrack["base_display_sample_count"] = POWERTRACK_BASE_DISPLAY_COUNT
powertrack["moving_display_sample_count"] = POWERTRACK_MOVING_DISPLAY_COUNT
powertrack_base_run = empty("PowertrackBaseRun", powertrack)
set_authority(powertrack_base_run, "reconstructed", "3122579700:643-645; display sampling only")
for link_index in range(POWERTRACK_BASE_DISPLAY_COUNT):
    x = 0.52 + link_index * POWERTRACK_LINK_PITCH_M
    box(f"PowertrackBaseDisplayLink_{link_index + 1:02d}", (POWERTRACK_LINK_LENGTH_M, 0.44, 0.09), powertrack_base_run, (x, 0.0, -0.49), MAT_POWERTRACK, "boom", round=0.012, evidence="MECHANISM_EVIDENCE:PWR-001,PWR-004")
box("PowertrackSupport", (2.60, 0.52, 0.08), main_boom, (1.72, 0.0, -0.59), MAT_DARK_METAL, "boom", round=0.018, evidence="3122579700:643-645")

telescope = empty("Telescope", main_boom, (3.60, 0.0, 0.0))
set_authority(telescope, "reconstructed", "MECHANISM_EVIDENCE:TEL-001,TEL-004")
telescope["telescope_travel_m"] = TELESCOPE_TRAVEL_M
telescope["mid_visual_travel_m"] = TELESCOPE_MID_TRAVEL_M
telescope["fly_visual_travel_m"] = TELESCOPE_FLY_TRAVEL_M
telescope["runtime_solver"] = "evidence_bounded_coupled_visual"
mid_boom = empty("MidBoom", telescope)
set_authority(mid_boom, "verified", "3122579600:28; 3122579700:641")
mid_profile = ((0.0, -0.245), (2.58, -0.20), (2.58, 0.20), (0.0, 0.245))
prism_xz("MidBoomShell", mid_profile, 0.54, mid_boom, (0.0, 0.0, 0.0), MAT_BOOM, "boom", evidence="3122579700:641", round=0.022)
box("MidBoomWearPadCollar", (0.18, 0.60, 0.53), mid_boom, (0.10, 0.0, 0.0), MAT_DARK_METAL, "boom", round=0.018, evidence="3122579800:540")

fly_boom = empty("FlyBoom", mid_boom, (0.75, 0.0, 0.0))
set_authority(fly_boom, "verified", "3122579600:28; 3122579700:641")
fly_profile = ((0.0, -0.19), (1.88, -0.16), (1.88, 0.16), (0.0, 0.19))
prism_xz("FlyBoomShell", fly_profile, 0.43, fly_boom, (0.0, 0.0, 0.0), MAT_ORANGE, "boom", evidence="MECHANISM_EVIDENCE:VIS-001", round=0.018)
box("FlyBoomWearPadCollar", (0.16, 0.48, 0.43), fly_boom, (0.09, 0.0, 0.0), MAT_DARK_METAL, "boom", round=0.015, evidence="3122579800:540")
box("BoomHead", (0.26, 0.46, 0.44), fly_boom, (1.78, 0.0, 0.0), MAT_ORANGE, "boom", round=0.035, evidence="3122579700:641")

powertrack_moving_run = empty("PowertrackMovingRun", mid_boom)
set_authority(powertrack_moving_run, "reconstructed", "3122579700:643-645; display sampling only")
for link_index in range(POWERTRACK_MOVING_DISPLAY_COUNT):
    x = 0.12 + link_index * POWERTRACK_LINK_PITCH_M
    box(f"PowertrackMovingDisplayLink_{link_index + 1:02d}", (POWERTRACK_LINK_LENGTH_M, 0.44, 0.09), powertrack_moving_run, (x, 0.0, -0.43), MAT_POWERTRACK, "boom", round=0.012, evidence="MECHANISM_EVIDENCE:PWR-001,PWR-004")
powertrack_bend = empty("PowertrackBend", mid_boom, (0.85, 0.0, -0.38))
set_authority(powertrack_bend, "reconstructed", "3122579700:645; display sampling only")
for bend_index, angle in enumerate((-1.15, -0.65, -0.15, 0.35, 0.85), start=1):
    link = box(f"PowertrackBendDisplayLink_{bend_index:02d}", (0.15, 0.44, 0.09), powertrack_bend, (0.16 * math.cos(angle), 0.0, 0.16 * math.sin(angle)), MAT_POWERTRACK, "boom", round=0.018, evidence="MECHANISM_EVIDENCE:PWR-001,PWR-004")
    link.rotation_euler.y = -angle
tube("PowertrackPushTube", (0.10, 0.0, -0.31), (1.45, 0.0, -0.30), 0.035, fly_boom, MAT_DARK_METAL, "boom", 12, evidence="MECHANISM_EVIDENCE:PWR-001,PWR-002")

box("TelescopeCylinderBarrel", (2.40, 0.16, 0.16), main_boom, (2.05, 0.0, -0.08), MAT_HYDRAULIC, "boom", round=0.06, evidence="MECHANISM_EVIDENCE:TEL-003")
box("TelescopeCylinderRod", (1.35, 0.08, 0.08), mid_boom, (0.42, 0.0, -0.08), MAT_METAL, "boom", round=0.03, evidence="MECHANISM_EVIDENCE:TEL-003")
for sheave_name, sheave_parent, sheave_x in (
    ("TelescopeExtendSheave_L", mid_boom, 0.18),
    ("TelescopeExtendSheave_R", mid_boom, 0.42),
    ("TelescopeRetractSheave_L", fly_boom, 0.14),
    ("TelescopeRetractSheave_R", fly_boom, 0.36),
):
    cylinder_mesh(sheave_name, 0.08, 0.08, sheave_parent, (sheave_x, 0.24, -0.04), (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "boom", 16, evidence="MECHANISM_EVIDENCE:TEL-003")
tube("TelescopeExtendWireRope", (0.52, 0.26, -0.13), (4.72, 0.26, -0.13), 0.008, main_boom, MAT_WIRE_ROPE, "boom", 8, evidence="MECHANISM_EVIDENCE:TEL-003")
tube("TelescopeRetractWireRope_L", (0.12, -0.22, -0.13), (2.22, -0.22, -0.13), 0.007, mid_boom, MAT_WIRE_ROPE, "boom", 8, evidence="MECHANISM_EVIDENCE:TEL-003")
tube("TelescopeRetractWireRope_R", (0.14, -0.18, -0.09), (1.56, -0.18, -0.09), 0.007, fly_boom, MAT_WIRE_ROPE, "boom", 8, evidence="MECHANISM_EVIDENCE:TEL-003")

for link_name, lower_location, upper_location, radius, mat in (
    ("TowerLink", (-0.42, 0.0, 0.38), (0.62, 0.0, -0.36), 0.115, MAT_DARK),
    ("TensionLink", (-0.22, 0.0, 0.58), (1.45, 0.0, -0.24), 0.085, MAT_ORANGE),
):
    link_group = empty(link_name, turntable)
    set_authority(link_group, "reconstructed", "MECHANISM_EVIDENCE:LIFT-001,LIFT-003")
    link_group["runtime_solver"] = "two_anchor_visual_link"
    lower = empty(f"{link_name}LowerAnchor", turntable, lower_location)
    upper = empty(f"{link_name}UpperAnchor", main_boom, upper_location)
    set_authority(lower, "reconstructed", "MECHANISM_EVIDENCE:LIFT-003")
    set_authority(upper, "reconstructed", "MECHANISM_EVIDENCE:LIFT-003")
    tube(f"{link_name}Body", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), radius, link_group, mat, "boom", 18, evidence="MECHANISM_EVIDENCE:LIFT-001")

lift_cylinder = empty("LiftCylinder", turntable, (0.02, 0.0, 0.35))
set_authority(lift_cylinder, "reconstructed", "3122579800:734; 3122579700:648")
lift_cylinder["runtime_solver"] = "two_anchor_visual"
lift_lower_anchor = empty("LiftCylinderLowerAnchor", turntable, (0.02, 0.0, 0.35))
set_authority(lift_lower_anchor, "reconstructed", "3122579700:648")
lift_upper_anchor = empty("LiftCylinderUpperAnchor", main_boom, (1.43, 0.0, -0.28))
set_authority(lift_upper_anchor, "reconstructed", "3122579700:648")
tube("LiftCylinderBarrel", (0.0, 0.0, 0.0), (0.92, 0.0, 0.0), 0.105, lift_cylinder, MAT_HYDRAULIC, "boom", 20, evidence="3122579800:734")
tube("LiftCylinderRod", (0.82, 0.0, 0.0), (1.52, 0.0, 0.0), 0.06, lift_cylinder, MAT_METAL, "boom", 18, evidence="3122579800:734")
cylinder_mesh("LiftCylinderBasePin", 0.14, 0.34, lift_cylinder, (0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "boom", 20, evidence="3122579700:648")
cylinder_mesh("LiftCylinderRodPin", 0.11, 0.30, lift_cylinder, (1.52, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "boom", 18, evidence="3122579700:648")
tube_path("LiftCylinderHose_A", ((0.04, 0.12, 0.02), (0.32, 0.13, 0.04), (0.62, 0.12, 0.02)), 0.014, lift_cylinder, MAT_HYDRAULIC, "boom", evidence="3122579800:734; routing reconstructed")
tube_path("LiftCylinderHose_B", ((0.06, -0.12, -0.02), (0.38, -0.13, 0.00), (0.78, -0.12, -0.02)), 0.014, lift_cylinder, MAT_HYDRAULIC, "boom", evidence="3122579800:734; routing reconstructed")
tube_path("BoomHydraulicBundle_L", ((0.48, 0.25, -0.34), (1.80, 0.25, -0.34), (3.30, 0.24, -0.31), (4.60, 0.22, -0.28)), 0.014, main_boom, MAT_HYDRAULIC, "boom", evidence="3122579800:724-804; routing reconstructed")
tube_path("BoomHydraulicBundle_R", ((0.48, -0.25, -0.34), (1.80, -0.25, -0.34), (3.30, -0.24, -0.31), (4.60, -0.22, -0.28)), 0.014, main_boom, MAT_HYDRAULIC, "boom", evidence="3122579800:724-804; routing reconstructed")

platform_pivot = empty("PlatformPivot", fly_boom, (1.54, 0.0, 0.0))
set_authority(platform_pivot, "reconstructed", "MECHANISM_EVIDENCE:PLT-001,PLT-002,PLT-003")
platform_pivot["platform_leveling"] = "counter_rotate_local_z"
platform_rotator = cylinder_mesh("PlatformRotator", 0.20, 0.44, platform_pivot, (0.0, 0.0, 0.0), (math.pi / 2.0, 0.0, 0.0), MAT_ORANGE, "platform", 28, evidence="3122579800:568; MECHANISM_EVIDENCE:PLT-002,PLT-003")
box("PlatformRotatorFlange", (0.10, 0.58, 0.46), platform_pivot, (0.04, 0.0, 0.0), MAT_DARK_METAL, "platform", round=0.05, evidence="3122579800:568")
prism_xz("PlatformSupport", ((-0.20, -0.38), (0.22, -0.34), (0.52, -0.12), (0.42, 0.14), (0.08, 0.26), (-0.20, 0.14)), 0.40, platform_pivot, (-0.02, 0.0, -0.20), MAT_ORANGE, "platform", evidence="MECHANISM_EVIDENCE:PLT-004", round=0.025)
box("PlatformLoadCell", (0.12, 0.30, 0.12), platform_pivot, (0.30, 0.0, -0.22), MAT_METAL, "platform", round=0.02, evidence="MECHANISM_EVIDENCE:PLT-004")
box("PlatformAngleSensor", (0.10, 0.12, 0.10), platform_pivot, (-0.08, 0.24, 0.02), MAT_SENSOR, "platform", round=0.02, evidence="MECHANISM_EVIDENCE:PLT-002")

platform_level_cylinder = empty("PlatformLevelCylinder", fly_boom)
set_authority(platform_level_cylinder, "reconstructed", "MECHANISM_EVIDENCE:PLT-001,PLT-003")
platform_level_cylinder["runtime_solver"] = "two_anchor_visual_cylinder"
platform_level_lower = empty("PlatformLevelCylinderLowerAnchor", fly_boom, (0.76, 0.0, -0.12))
platform_level_upper = empty("PlatformLevelCylinderUpperAnchor", platform_pivot, (-0.12, 0.0, -0.18))
set_authority(platform_level_lower, "reconstructed", "MECHANISM_EVIDENCE:PLT-004")
set_authority(platform_level_upper, "reconstructed", "MECHANISM_EVIDENCE:PLT-004")
tube("PlatformLevelCylinderBarrel", (0.0, 0.0, 0.0), (0.52, 0.0, 0.0), 0.060, platform_level_cylinder, MAT_HYDRAULIC, "platform", 16, evidence="MECHANISM_EVIDENCE:PLT-001,PLT-003")
tube("PlatformLevelCylinderRod", (0.44, 0.0, 0.0), (0.88, 0.0, 0.0), 0.032, platform_level_cylinder, MAT_METAL, "platform", 14, evidence="MECHANISM_EVIDENCE:PLT-001,PLT-003")
tube_path("PlatformRotatorHose_A", ((-0.12, 0.19, -0.18), (0.02, 0.20, -0.24), (0.20, 0.18, -0.30)), 0.013, platform_pivot, MAT_HYDRAULIC, "platform", evidence="3122579800:568-600; routing reconstructed")
tube_path("PlatformRotatorHose_B", ((-0.12, -0.19, -0.18), (0.02, -0.20, -0.24), (0.20, -0.18, -0.30)), 0.013, platform_pivot, MAT_HYDRAULIC, "platform", evidence="3122579800:568-600; routing reconstructed")
platform = empty("Platform", platform_pivot)
set_authority(platform, "verified", "3122579800:654,660,666-668")
box("PlatformDeck", (0.91, 2.44, 0.10), platform, (0.455, 0.0, -0.72), MAT_ORANGE, "platform", authority="verified", evidence="3131050:R0626_04")
box("PlatformFloor", (0.82, 2.32, 0.035), platform, (0.455, 0.0, -0.655), MAT_DARK_METAL, "platform", evidence="3122579800:654")
for slat_index in range(12):
    y = -1.05 + slat_index * (2.10 / 11)
    box(f"PlatformFloorSlat_{slat_index + 1:02d}", (0.78, 0.035, 0.018), platform, (0.455, y, -0.63), MAT_METAL, "platform", evidence="3122579800:654")
box("PlatformToeboard_L", (0.88, 0.045, 0.30), platform, (0.455, 1.197, -0.52), MAT_ORANGE, "platform", round=0.015, evidence="3122579800:654")
box("PlatformToeboard_R", (0.88, 0.045, 0.30), platform, (0.455, -1.197, -0.52), MAT_ORANGE, "platform", round=0.015, evidence="3122579800:654")
box("PlatformToeboard_F", (0.045, 2.40, 0.30), platform, (0.887, 0.0, -0.52), MAT_ORANGE, "platform", round=0.015, evidence="3122579800:654")
box("PlatformToeboard_B", (0.045, 2.40, 0.30), platform, (0.023, 0.0, -0.52), MAT_ORANGE, "platform", round=0.015, evidence="3122579800:654")
box("PlatformConsole", (0.31, 0.82, 0.20), platform, (0.68, -0.78, 0.08), MAT_DARK, "platform", round=0.070, evidence="3122579800:666-670")
box("PlatformConsoleLowerLip", (0.325, 0.84, 0.045), platform, (0.68, -0.78, 0.005), MAT_DARK_METAL, "platform", round=0.075, evidence="3122579800:668")
box("PlatformConsoleFace", (0.335, 0.84, 0.050), platform, (0.68, -0.78, 0.205), MAT_METAL, "platform", round=0.075, evidence="3122579800:668-670")
for mount_index, y in enumerate((-1.04, -0.52), start=1):
    tube(f"PlatformConsoleMount_{mount_index}", (0.55, y, -0.18), (0.55, y, 0.12), 0.022, platform, MAT_DARK_METAL, "platform", 10, evidence="3122579800:666; mount placement reconstructed")

# The current B3 console is a horizontal tray with two controllers, guarded toggle
# rows, emergency stop, speed controller, and a central indicator/legend field.
for joystick_index, (x, y) in enumerate(((0.70, -1.04), (0.70, -0.52)), start=1):
    cylinder_mesh(f"PlatformJoystickBase_{joystick_index}", 0.060, 0.018, platform, (x, y, 0.237), (0.0, 0.0, 0.0), MAT_DARK_METAL, "platform", 16, evidence="3122579800:668-670")
    cylinder_mesh(f"PlatformJoystickBoot_{joystick_index}", 0.045, 0.065, platform, (x, y, 0.275), (0.0, 0.0, 0.0), MAT_DARK, "platform", 14, evidence="3122579800:668-670")
    tube(f"PlatformJoystick_{joystick_index}", (x, y, 0.29), (x + (0.014 if joystick_index == 1 else -0.012), y, 0.326), 0.015, platform, MAT_DARK, "platform", 10, evidence="3122579800:668-670")
    cylinder_mesh(f"PlatformJoystickGrip_{joystick_index}", 0.030, 0.080, platform, (x + (0.014 if joystick_index == 1 else -0.012), y, 0.348), (0.0, 0.0, 0.0), MAT_DARK, "platform", 14, evidence="3122579800:668-670")
    cylinder_mesh(f"PlatformJoystickTopButton_{joystick_index}", 0.010, 0.012, platform, (x + (0.014 if joystick_index == 1 else -0.012), y, 0.394), (0.0, 0.0, 0.0), MAT_WARNING, "platform", 10, evidence="3122579800:668-670")

cylinder_mesh("PlatformEmergencyStopBase", 0.050, 0.022, platform, (0.60, -0.82, 0.237), (0.0, 0.0, 0.0), MAT_DARK, "platform", 16, evidence="3122579800:668")
cylinder_mesh("PlatformEmergencyStop", 0.050, 0.050, platform, (0.60, -0.82, 0.273), (0.0, 0.0, 0.0), MAT_RED, "platform", 16, evidence="3122579800:668")
cylinder_mesh("PlatformFunctionSpeedBase", 0.035, 0.016, platform, (0.79, -0.82, 0.235), (0.0, 0.0, 0.0), MAT_DARK, "platform", 14, evidence="3122579800:668")
cylinder_mesh("PlatformFunctionSpeedKnob", 0.026, 0.045, platform, (0.79, -0.82, 0.265), (0.0, 0.0, 0.0), MAT_DARK, "platform", 12, evidence="3122579800:668")

for toggle_index, (x, y) in enumerate((
    (0.585, -0.68), (0.585, -0.61), (0.585, -0.54),
    (0.815, -0.68), (0.815, -0.61),
    (0.585, -0.98), (0.585, -0.91), (0.815, -0.91),
), start=1):
    cylinder_mesh(f"PlatformToggleBase_{toggle_index}", 0.015, 0.012, platform, (x, y, 0.236), (0.0, 0.0, 0.0), MAT_DARK, "platform", 10, smooth=False, evidence="3122579800:668")
    tube(f"PlatformToggle_{toggle_index}", (x, y, 0.24), (x + (0.010 if toggle_index % 2 else -0.010), y, 0.278), 0.006, platform, MAT_METAL, "platform", 8, evidence="3122579800:668")
    box(f"PlatformToggleGuard_{toggle_index}", (0.020, 0.040, 0.055), platform, (x + (0.030 if x < 0.7 else -0.030), y, 0.258), MAT_DARK_METAL, "platform", round=0.008, evidence="3122579800:668")

box("PlatformConsoleDisplay", (0.12, 0.19, 0.012), platform, (0.704, -0.77, 0.236), MAT_DARK, "platform", round=0.015, evidence="3122579800:668-670")
for row in range(2):
    for column in range(4):
        cylinder_mesh(
            f"PlatformIndicator_{row + 1}_{column + 1}", 0.009, 0.006, platform,
            (0.679 + row * 0.050, -0.83 + column * 0.040, 0.245), (0.0, 0.0, 0.0),
            MAT_WARNING if (row + column) % 3 == 0 else MAT_WHITE, "platform", 8, smooth=False,
            evidence="3122579800:668-670; indicator layout simplified",
        )
box("PlatformConsoleDriveLabel", (0.07, 0.15, 0.008), platform, (0.805, -1.01, 0.238), MAT_WHITE, "platform", round=0.004, evidence="3122579800:668; decal 1702565")
box("PlatformConsoleLiftLabel", (0.07, 0.15, 0.008), platform, (0.805, -0.55, 0.238), MAT_WHITE, "platform", round=0.004, evidence="3122579800:668; decal 1702566")
tube("PlatformConsoleGuardFront", (0.53, -1.15, 0.285), (0.53, -0.41, 0.285), 0.014, platform, MAT_DARK_METAL, "platform", 10, evidence="3122579800:668")
tube("PlatformConsoleGuardRear", (0.85, -1.15, 0.285), (0.85, -0.41, 0.285), 0.014, platform, MAT_DARK_METAL, "platform", 10, evidence="3122579800:668")
box("PlatformFootswitch", (0.30, 0.18, 0.10), platform, (0.42, -0.58, -0.58), MAT_DARK, "platform", round=0.025, evidence="3122579800:666,674")
box("PlatformManualBox", (0.20, 0.09, 0.30), platform, (0.13, 1.12, -0.32), MAT_DARK, "platform", round=0.025, evidence="3122579800:654-674")
box("PlatformCapacityLabel", (0.018, 0.34, 0.15), platform, (0.899, 0.42, -0.44), MAT_WHITE, "platform", round=0.006, evidence="3122579600:135")
box("PlatformWarningLabel", (0.018, 0.30, 0.13), platform, (0.899, 0.00, -0.44), MAT_WARNING, "platform", round=0.006, evidence="3122579800:654-674")
tube_path("FootswitchHarness", ((0.42, -0.58, -0.56), (0.58, -0.70, -0.34), (0.66, -0.80, -0.04)), 0.010, platform, MAT_ELECTRICAL, "platform", evidence="3122579800:666-674; routing reconstructed")

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
        tube(f"PlatformPost_{end}{side}", (x, y, post_bottom_z), (x, y, post_top_z), 0.028, platform, MAT_ORANGE, "platform")
for x in post_x:
    tag = "B" if x < 0.4 else "F"
    tube(f"PlatformRailTop_{tag}", (x, post_y[0], rail_top_z), (x, post_y[1], rail_top_z), rail_top_r, platform, MAT_ORANGE, "platform", evidence="3122579800:654")
    tube(f"PlatformRailMid_{tag}", (x, post_y[0], rail_mid_z), (x, post_y[1], rail_mid_z), rail_mid_r, platform, MAT_ORANGE, "platform", evidence="3122579800:654")
for y in post_y:
    tag = "L" if y > 0 else "R"
    if y > 0:
        tube(f"PlatformRailTop_{tag}", (post_x[0], y, rail_top_z), (post_x[1], y, rail_top_z), rail_top_r, platform, MAT_ORANGE, "platform", evidence="3122579800:654")
        tube(f"PlatformRailMid_{tag}", (post_x[0], y, rail_mid_z), (post_x[1], y, rail_mid_z), rail_mid_r, platform, MAT_ORANGE, "platform", evidence="3122579800:654")

platform_gate = empty("PlatformSwingGate", platform, (0.06, -1.19, 0.0))
set_authority(platform_gate, "verified", "3122579800:660")
tube("PlatformGateTop", (0.02, 0.0, rail_top_z), (0.78, 0.0, rail_top_z), rail_top_r, platform_gate, MAT_ORANGE, "platform", evidence="3122579800:660")
tube("PlatformGateMid", (0.02, 0.0, rail_mid_z), (0.78, 0.0, rail_mid_z), rail_mid_r, platform_gate, MAT_ORANGE, "platform", evidence="3122579800:660")
tube("PlatformGateLatchPost", (0.78, 0.0, rail_mid_z), (0.78, 0.0, rail_top_z), 0.025, platform_gate, MAT_ORANGE, "platform", evidence="3122579800:660")
box("PlatformGateLatch", (0.09, 0.07, 0.05), platform_gate, (0.75, 0.0, 0.22), MAT_DARK, "platform", round=0.012, evidence="3122579800:660")

skyguard = empty("SkyGuard", platform, (0.0, 0.0, 0.0))
set_authority(skyguard, "verified", "3131050:R0626_04")
tube("SkyGuardPost_L", (0.12, 0.86, 0.18), (0.12, 0.86, 0.38), 0.025, skyguard, MAT_DARK, "platform", evidence="3122579800:680")
tube("SkyGuardPost_R", (0.12, -0.86, 0.18), (0.12, -0.86, 0.38), 0.025, skyguard, MAT_DARK, "platform", evidence="3122579800:680")
tube("SkyGuardSkyLine", (0.12, -0.86, 0.36), (0.12, 0.86, 0.36), 0.018, skyguard, MAT_DARK, "platform", 12, evidence="3122579800:680")
for side, y in (("L", 0.83), ("R", -0.83)):
    cylinder_mesh(f"LanyardPoint_{side}", 0.04, 0.025, platform, (0.10, y, 0.02), (math.pi / 2.0, 0.0, 0.0), MAT_DARK_METAL, "platform", 14, evidence="3122579800:654")

box("BoomSensorLower", (0.18, 0.12, 0.10), main_boom, (0.72, 0.34, -0.18), MAT_SENSOR, "boom", round=0.02, evidence="3122579800:898-904")
box("BoomSensorUpper", (0.16, 0.10, 0.09), mid_boom, (2.18, 0.27, -0.12), MAT_SENSOR, "boom", round=0.018, evidence="3122579800:900-904")
box("TeleProximitySensor", (0.10, 0.08, 0.08), fly_boom, (0.18, -0.23, 0.0), MAT_SENSOR, "boom", round=0.015, evidence="3122579800:1026")
tube("BoomCableUpper", (0.44, -0.30, -0.28), (4.50, -0.27, -0.24), 0.016, main_boom, MAT_CONTROL_CABLE, "boom", 10, evidence="3122579800:908-912")
tube("PlatformHarness", (0.10, -0.18, -0.12), (1.42, -0.18, -0.10), 0.014, fly_boom, MAT_ELECTRICAL, "boom", 10, evidence="3122579800:994-998")

box("Chassis_Hit", (5.70, 2.48, 1.14), chassis, (-0.05, 0.0, 0.57), MAT_HIT, "chassis", hit=True)
box("Turntable_Hit", (3.80, 2.16, 1.30), turntable, (-0.56, 0.0, 0.65), MAT_HIT, "turntable", hit=True)
box("Boom_Hit", (5.20, 0.90, 0.78), main_boom, (2.56, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Telescope_Hit", (2.02, 0.56, 0.60), fly_boom, (0.92, 0.0, 0.0), MAT_HIT, "boom", hit=True)
box("Platform_Hit", (0.91, 2.44, 1.17), platform, (0.455, 0.0, -0.185), MAT_HIT, "platform", hit=True)

bpy.context.view_layer.update()
objects = list(collection.all_objects)
for side in ("L", "R"):
    assert_attached(f"SideStep_{side}", "LowerDeck")
    assert_attached(f"SideStepBracket_{side}", f"SideStep_{side}")
    assert_attached(f"SideStepBracket_{side}", "ChassisFrontPod")
    assert_attached(f"BoomRestPost_{side}", "ChassisFrontPod")
    assert_attached(f"BoomRestPost_{side}", "BoomRest")
assert_attached("BoomRestPad", "BoomRest")
for tag, rail in (("FL", "FrameRail_L"), ("FR", "FrameRail_R"), ("RL", "FrameRail_L"), ("RR", "FrameRail_R")):
    assert_attached(f"TieDownPocket_{tag}", rail)
for wheel_name in ("Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"):
    if bpy.data.objects[f"{wheel_name}_Roll"].parent is not bpy.data.objects[wheel_name]:
        raise RuntimeError(f"{wheel_name} roll transform must remain below its steer/axle transform")
    if bpy.data.objects[f"{wheel_name}_Tire"].parent is not bpy.data.objects[f"{wheel_name}_Roll"]:
        raise RuntimeError(f"{wheel_name} tire must be owned by its roll transform")
    fixed_part = f"{wheel_name}_SteerKnuckle" if wheel_name in ("Wheel_FL", "Wheel_FR") else f"{wheel_name}_AxleEnd"
    if bpy.data.objects[fixed_part].parent is not bpy.data.objects[wheel_name]:
        raise RuntimeError(f"{fixed_part} must not inherit tire roll")
for side, wheel_name in (("L", "Wheel_FL"), ("R", "Wheel_FR")):
    hose_name = f"SteerHydraulicHose_{side}"
    if bpy.data.objects[f"{hose_name}_Flexible"].get("runtime_solver") != "two_anchor_visual_hose":
        raise RuntimeError(f"{hose_name} moving leg is missing its endpoint-follow solver")
    if bpy.data.objects[f"{hose_name}_UpperAnchor"].parent is not bpy.data.objects[wheel_name]:
        raise RuntimeError(f"{hose_name} moving anchor must follow {wheel_name}")
if powertrack_bend.parent is not powertrack_moving_run.parent:
    raise RuntimeError("Powertrack bend and moving run must inherit the same telescope stage")
for prefix, count in (
    ("PowertrackBaseDisplayLink", POWERTRACK_BASE_DISPLAY_COUNT),
    ("PowertrackMovingDisplayLink", POWERTRACK_MOVING_DISPLAY_COUNT),
):
    for link_index in range(1, count):
        assert_near(
            f"{prefix}_{link_index:02d}",
            f"{prefix}_{link_index + 1:02d}",
            POWERTRACK_MAX_VISIBLE_GAP_M,
        )
base_run_end_x = world_aabb(bpy.data.objects[f"PowertrackBaseDisplayLink_{POWERTRACK_BASE_DISPLAY_COUNT:02d}"])[1].x
moving_run_start_x_at_full_travel = (
    world_aabb(bpy.data.objects["PowertrackMovingDisplayLink_01"])[0].x + TELESCOPE_MID_TRAVEL_M
)
if moving_run_start_x_at_full_travel - base_run_end_x > POWERTRACK_MAX_VISIBLE_GAP_M:
    raise RuntimeError(
        "Powertrack sampled runs separate at full visual telescope travel: "
        f"gap={moving_run_start_x_at_full_travel - base_run_end_x:.4f} m"
    )
minimum, maximum, dimensions = world_bounds(objects)
for axis, actual, expected in zip("XYZ", dimensions, PUBLISHED_ENVELOPE_M):
    if not math.isclose(actual, expected, abs_tol=0.002):
        ranked = []
        for candidate in objects:
            if candidate.type != "MESH" or candidate.get("is_hit_volume"):
                continue
            corners = [candidate.matrix_world @ Vector(corner) for corner in candidate.bound_box]
            ranked.append((max(point.z for point in corners), min(point.z for point in corners), candidate.name))
        print(json.dumps({
            "highest_visible_objects": sorted(ranked, reverse=True)[:8],
            "lowest_visible_objects": sorted(ranked, key=lambda item: item[1])[:8],
        }, indent=2))
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

main_end_x = 5.12
telescope_start_x = 3.60
mid_overlap_100 = main_end_x - (telescope_start_x + TELESCOPE_MID_TRAVEL_M)
fly_overlap_100 = 2.58 - (0.75 + TELESCOPE_FLY_TRAVEL_M)
if mid_overlap_100 <= 0.001 or fly_overlap_100 <= 0.001:
    raise RuntimeError(
        f"Coupled telescope would separate at 100% travel: mid={mid_overlap_100:.4f} m, "
        f"fly={fly_overlap_100:.4f} m"
    )

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
    "asset": "600S Showcase v1.1",
    "configuration_id": CONFIGURATION_ID,
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
    "telescope_mid_overlap_at_100_m": round(mid_overlap_100, 4),
    "telescope_fly_overlap_at_100_m": round(fly_overlap_100, 4),
    "scene_count": len(bpy.data.scenes),
}
print(json.dumps(result, indent=2, sort_keys=True))
