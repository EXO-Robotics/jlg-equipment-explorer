#!/usr/bin/env python3
"""Build the owned, evidence-bounded JLG 742 showcase asset in Blender."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())
BLEND_PATH = ROOT / "source/blender/742-showcase-v1.0.blend"
GLB_PATH = ROOT / "assets/models/742.glb"
MAT = {}
BOOM_LATERAL_OFFSET_M = 0.30


def solved_pose(state):
    completed = subprocess.run(
        ["node", str(ROOT / "scripts/solve_742_pose.mjs"), json.dumps(state)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(completed.stdout)


def material(name, color, metallic=0.0, roughness=0.5, alpha=1.0):
    mat = bpy.data.materials.new(name)
    rgba = (*color[:3], alpha)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        try:
            mat.surface_render_method = "DITHERED"
        except Exception:
            pass
        try:
            mat.use_transparency_overlap = False
        except Exception:
            pass
    return mat


def parent(child, owner):
    if owner is not None:
        child.parent = owner
    return child


def empty(name, location=(0, 0, 0), owner=None, display="PLAIN_AXES", size=0.08, component=None):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.empty_display_type = display
    obj.empty_display_size = size
    bpy.context.collection.objects.link(obj)
    parent(obj, owner)
    if component:
        obj["component"] = component
    return obj


def box(name, size, location, mat, owner=None, bevel=0.025, component=None, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(v / 2 for v in size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    obj.data.materials.append(mat)
    parent(obj, owner)
    if component:
        obj["component"] = component
    return obj


def cylinder(name, radius, depth, location, mat, owner=None, rotation=(0, 0, 0), vertices=24, component=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    parent(obj, owner)
    if component:
        obj["component"] = component
    return obj


def torus(name, major, minor, location, mat, owner=None, rotation=(0, 0, 0), component=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=40, minor_segments=12, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    parent(obj, owner)
    if component:
        obj["component"] = component
    return obj


def beam(name, start, end, radius, mat, owner=None, component=None, vertices=16):
    a, b = Vector(start), Vector(end)
    direction = b - a
    obj = cylinder(name, radius, direction.length, (a + b) / 2, mat, owner, vertices=vertices, component=component)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    obj["authored_length_m"] = direction.length
    obj["rig_axis"] = "local_y_after_gltf_export"
    return obj


def pose_beam(name, endpoints):
    obj = bpy.data.objects[name]
    a, b = (Vector(point) for point in endpoints)
    direction = b - a
    if direction.length < 1e-6:
        raise RuntimeError(f"{name} collapsed in authored pose")
    obj.location = (a + b) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    obj.scale = (1, 1, direction.length / float(obj.get("authored_length_m", direction.length)))


def square_beam(name, start, end, width, mat, owner=None, component=None):
    a, b = Vector(start), Vector(end)
    direction = b - a
    obj = box(name, (direction.length, width, width), (a + b) / 2, mat, owner, width * 0.15, component)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(direction.normalized())
    return obj


def wedge(name, length, height_front, height_rear, width, location, mat, owner=None, component=None):
    x0, x1 = -length / 2, length / 2
    y0 = -min(height_front, height_rear) / 2
    verts = [
        (x0, y0, -width / 2), (x0, y0, width / 2), (x0, y0 + height_rear, -width / 2), (x0, y0 + height_rear, width / 2),
        (x1, y0, -width / 2), (x1, y0, width / 2), (x1, y0 + height_front, -width / 2), (x1, y0 + height_front, width / 2),
    ]
    faces = [(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3),(0,1,3,2),(4,6,7,5)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    parent(obj, owner)
    if component:
        obj["component"] = component
    bevel = obj.modifiers.new("PanelSoftening", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 2
    return obj


def tube_curve(name, points, radius, mat, owner=None, component=None):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    curve.resolution_u = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, value in zip(spline.bezier_points, points):
        point.co = value
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    parent(obj, owner)
    if component:
        obj["component"] = component
    return obj


def label(name, text, location, mat, owner=None, size=0.16, rotation=(math.pi / 2, 0, 0), component=None):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.004
    obj.data.bevel_depth = 0.0015
    obj.data.materials.append(mat)
    parent(obj, owner)
    obj["marking_authority"] = "independently_typeset_nominative_mark"
    if component:
        obj["component"] = component
    return obj


def wheel(name, x, z, owner):
    pivot = empty(f"SteerPivot_{name}", (x, 0.643, z), owner, "ARROWS", 0.13, "steering")
    tire = torus(f"Tire_{name}", 0.47, 0.145, (0, 0, 0), MAT["rubber"], pivot, component="steering")
    tire["tire_spec"] = "370/75-28 standard"
    cylinder(f"WheelRimOuter_{name}", 0.30, 0.34, (0, 0, 0), MAT["cream"], pivot, vertices=32, component="steering")
    cylinder(f"WheelHub_{name}", 0.145, 0.358, (0, 0, 0), MAT["black"], pivot, vertices=24, component="steering")
    cylinder(f"PlanetaryCap_{name}", 0.085, 0.358, (0, 0, 0), MAT["zinc"], pivot, vertices=20, component="steering")
    for lug in range(8):
        angle = math.tau * lug / 8
        cylinder(f"Lug_{name}_{lug:02d}", 0.018, 0.358, (math.cos(angle) * 0.112, math.sin(angle) * 0.112, 0), MAT["zinc"], pivot, vertices=10, component="steering")
    for tread in range(28):
        angle = math.tau * tread / 28
        tread_obj = box(
            f"Tread_{name}_{tread:02d}", (0.075, 0.23, 0.36),
            (math.cos(angle) * 0.574, math.sin(angle) * 0.574, 0), MAT["rubber"], pivot, 0.018, "steering",
            rotation=(0, 0, angle + (0.22 if tread % 2 else -0.22)),
        )
        tread_obj["tread_block"] = True
    return pivot


def build():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    MAT.update({
        "orange": material("JLG Orange", (0.94, 0.39, 0.018), 0.12, 0.36),
        "orange_dark": material("JLG Orange Shadow", (0.63, 0.18, 0.008), 0.16, 0.42),
        "cream": material("Boom Cream", (0.80, 0.76, 0.62), 0.22, 0.38),
        "cream_dark": material("Boom Wear Cream", (0.55, 0.52, 0.41), 0.32, 0.42),
        "black": material("Structural Black", (0.018, 0.024, 0.024), 0.32, 0.40),
        "black_soft": material("Interior Black", (0.035, 0.045, 0.043), 0.02, 0.78),
        "rubber": material("Rough Terrain Rubber", (0.012, 0.016, 0.015), 0.0, 0.94),
        "zinc": material("Zinc Hardware", (0.48, 0.52, 0.51), 0.72, 0.28),
        "hydraulic": material("Hydraulic Cylinder", (0.27, 0.30, 0.29), 0.74, 0.26),
        "hose": material("Hydraulic Hose", (0.025, 0.032, 0.031), 0.0, 0.70),
        "glass": material("Cab Safety Glass", (0.15, 0.33, 0.38), 0.05, 0.18, 0.28),
        "lamp": material("Lamp Lens", (0.93, 0.82, 0.48), 0.05, 0.22),
        "red": material("Signal Red", (0.68, 0.02, 0.012), 0.06, 0.36),
        "white": material("Marking White", (0.88, 0.89, 0.83), 0.0, 0.58),
    })

    root = empty("742_ROOT", display="CUBE", size=0.24)
    # The reconstruction is authored in logical X-longitudinal/Y-up/Z-lateral
    # coordinates. This root basis maps that convention into Blender's Z-up
    # scene while the glTF exporter maps it back to Three.js Y-up coordinates.
    root.rotation_euler[0] = math.pi / 2
    root["model"] = "JLG 742"
    root["configuration_id"] = CONFIG["configuration_id"]
    root["pvc"] = "2411"
    root["release"] = CONFIG["target_release"]
    root["units"] = "meters"
    root["ownership"] = "owned_reconstruction_no_manufacturer_geometry"
    root["disclaimer"] = "visual reconstruction; not load, stability, service, training, or safety authority"

    running = empty("GroundRunningGear", owner=root, component="steering")
    front_x, rear_x = 1.71, -1.71
    wheel_lateral = 1.05025
    box("FrontAxle", (0.52, 0.26, 1.92), (front_x, 0.69, 0), MAT["black"], running, 0.05, "steering")
    box("RearAxle", (0.52, 0.26, 1.92), (rear_x, 0.69, 0), MAT["black"], running, 0.05, "steering")
    for axle_name, x in (("Front", front_x), ("Rear", rear_x)):
        # The axle/differential axis is lateral (logical Z). The short input
        # flange points longitudinally and is only a topology cue; cast detail
        # and exact housing dimensions remain reconstructed.
        cylinder(f"{axle_name}Differential", 0.22, 0.72, (x, 0.68, 0), MAT["black"], running, component="steering")
        cylinder(f"{axle_name}AxleTubeLeft", 0.11, 0.56, (x, 0.68, -0.62), MAT["black"], running, component="steering")
        cylinder(f"{axle_name}AxleTubeRight", 0.11, 0.56, (x, 0.68, 0.62), MAT["black"], running, component="steering")
        cylinder(f"{axle_name}PinionFlange", 0.10, 0.20, (x - 0.20, 0.68, 0), MAT["zinc"], running,
                 rotation=(0, math.pi / 2, 0), component="steering")
        steering_cylinder = empty(f"{axle_name}SteerCylinder", owner=running, component="steering")
        beam(f"{axle_name}SteerCylinderBarrel", (x, 0.76, -0.34), (x, 0.76, 0.34), 0.055, MAT["hydraulic"], steering_cylinder, "steering", 20)
        beam(f"{axle_name}SteerCylinderRodLeft", (x, 0.76, -0.34), (x, 0.76, -0.70), 0.028, MAT["zinc"], steering_cylinder, "steering", 16)
        beam(f"{axle_name}SteerCylinderRodRight", (x, 0.76, 0.34), (x, 0.76, 0.70), 0.028, MAT["zinc"], steering_cylinder, "steering", 16)
        beam(f"{axle_name}SteerBarLeft", (x, 0.76, -0.70), (x - 0.35, 0.59, -1.00025), 0.024, MAT["black"], steering_cylinder, "steering", 14)
        beam(f"{axle_name}SteerBarRight", (x, 0.76, 0.70), (x - 0.35, 0.59, 1.00025), 0.024, MAT["black"], steering_cylinder, "steering", 14)
    wheels = {name: wheel(name, x, z, running) for name, x, z in (
        ("FL", front_x, -wheel_lateral), ("FR", front_x, wheel_lateral), ("RL", rear_x, -wheel_lateral), ("RR", rear_x, wheel_lateral)
    )}
    for pivot in wheels.values():
        pivot["steering_authority"] = "mode_verified_angles_reconstructed"

    frame = empty("FrameLevelPivot", (0, 0.82, 0), root, "ARROWS", 0.20, "frame")
    frame["published_limit_degrees"] = 10
    frame["pivot_authority"] = "reconstructed_longitudinal_roll_axis_at_0.82m_visual_height_not_manufacturer_axle_centerline"
    chassis = empty("Chassis", (0, -0.82, 0), frame, component="chassis")
    box("MainFrame", (4.72, 0.34, 1.56), (0, 0.88, 0), MAT["black"], chassis, 0.09, "chassis")
    box("BellyPan", (4.60, 0.16, 1.63), (-0.05, 0.66, 0), MAT["black_soft"], chassis, 0.05, "chassis")
    for z in (-0.77, 0.77):
        box(f"FrameRail_{z:+.0f}", (4.65, 0.42, 0.18), (-0.015, 0.87, z), MAT["black"], chassis, 0.035, "chassis")
        for x in (front_x, rear_x):
            box(f"Fender_{x:+.0f}_{z:+.0f}", (1.28, 0.16, 0.34), (x, 1.22, z), MAT["orange"], chassis, 0.07, "chassis")
    box("RearCounterweight", (0.50, 0.88, 1.86), (-2.11, 1.18, 0), MAT["black"], chassis, 0.10, "chassis")
    box("FrontNose", (0.48, 0.64, 1.65), (2.58, 1.03, 0), MAT["black"], chassis, 0.08, "chassis")
    for z in (-0.70, 0.70):
        box(f"TowLug_{z:+.0f}", (0.20, 0.28, 0.18), (-2.25, 0.63, z), MAT["zinc"], chassis, 0.03, "chassis")
        cylinder(f"TowPin_{z:+.0f}", 0.045, 0.20, (-2.27, 0.63, z), MAT["black"], chassis, component="chassis")

    engine = empty("EngineCompartment", owner=chassis, component="hydraulics")
    # The stowed boom runs beside the open cab, over a low service hood. Keep
    # the center portion below the boom and the raised cover entirely outboard;
    # the validator measures both clearances from the exported GLB.
    wedge("EngineHoodLower", 2.35, 0.50, 0.54, 0.92, (-0.55, 1.02, 0.63), MAT["orange"], engine, "hydraulics")
    wedge("EngineHoodUpper", 1.50, 0.18, 0.24, 0.50, (-0.83, 1.36, 0.96), MAT["orange"], engine, "hydraulics")
    box("EngineHoodSpine", (1.34, 0.06, 0.50), (-0.86, 1.52, 0.96), MAT["orange_dark"], engine, 0.025, "hydraulics")
    for slot in range(9):
        box(f"EngineGrilleSlot_{slot:02d}", (0.035, 0.24, 0.012), (-1.48 + slot * 0.13, 1.39, 1.216), MAT["black"], engine, 0.008, "hydraulics", rotation=(0.14, 0, 0))
    box("RadiatorGrille", (0.72, 0.38, 0.025), (-2.02, 1.40, 1.105), MAT["black"], engine, 0.025, "hydraulics")
    for row in range(4):
        for col in range(7):
            cylinder(f"GrilleHole_{row}_{col}", 0.014, 0.032, (-2.29 + col * 0.09, 1.29 + row * 0.075, 1.12), MAT["black_soft"], engine, rotation=(math.pi / 2, 0, 0), vertices=8, component="hydraulics")
    box("FuelTankCue", (0.64, 0.42, 0.48), (-0.45, 1.03, 0.54), MAT["black_soft"], engine, 0.05, "hydraulics")
    box("HydraulicTankCue", (0.58, 0.48, 0.46), (0.28, 1.02, 0.55), MAT["hydraulic"], engine, 0.04, "hydraulics")
    box("MainValveBank", (0.38, 0.28, 0.32), (0.18, 1.25, 0.56), MAT["zinc"], engine, 0.025, "hydraulics")
    for index in range(6):
        cylinder(f"ValveSolenoid_{index}", 0.026, 0.16, (0.02 + index * 0.065, 1.34, 0.56), MAT["black"], engine, rotation=(math.pi / 2, 0, 0), vertices=12, component="hydraulics")

    cab = empty("OpenCab", owner=chassis, component="cab")
    cab_center_x, cab_center_z = 0.82, -0.64
    box("CabFloor", (1.52, 0.12, 0.94), (cab_center_x, 1.05, cab_center_z), MAT["black"], cab, 0.045, "cab")
    for x, z in ((0.18,-1.08),(1.46,-1.08),(0.18,-0.20),(1.46,-0.20)):
        square_beam(f"ROPSPost_{x}_{z}", (x,1.08,z), (x,2.30,z), 0.075, MAT["black"], cab, "cab")
    box("ROPSRoof", (1.58, 0.10, 1.02), (cab_center_x, 2.34, cab_center_z), MAT["black"], cab, 0.040, "cab")
    for rail_index, z in enumerate((-1.03,-0.76,-0.49,-0.25)):
        square_beam(f"RoofGuard_{rail_index}", (0.15,2.405,z), (1.50,2.405,z), 0.030, MAT["black"], cab, "cab")
    box("FrontWindshield", (0.035, 1.14, 0.78), (1.43, 1.76, cab_center_z), MAT["glass"], cab, 0.012, "cab", rotation=(0,0,-0.06))
    box("RearCabGlass", (0.035, 0.98, 0.78), (0.20, 1.74, cab_center_z), MAT["glass"], cab, 0.012, "cab")
    box("RoofGlass", (1.10, 0.020, 0.70), (0.83, 2.325, cab_center_z), MAT["glass"], cab, 0.008, "cab")
    box("SeatBase", (0.52, 0.30, 0.46), (0.70, 1.22, cab_center_z), MAT["black_soft"], cab, 0.07, "cab")
    box("OperatorSeat", (0.50, 0.68, 0.15), (0.48, 1.58, cab_center_z), MAT["black_soft"], cab, 0.07, "cab", rotation=(0,0,-0.12))
    box("Dashboard", (0.48, 0.30, 0.72), (1.25, 1.42, cab_center_z), MAT["black"], cab, 0.055, "cab", rotation=(0,0,0.12))
    torus("SteeringWheel", 0.15, 0.018, (1.04, 1.72, cab_center_z), MAT["black_soft"], cab, rotation=(math.pi / 2, 0.15, 0), component="cab")
    beam("SteeringColumn", (1.12,1.46,cab_center_z), (1.04,1.70,cab_center_z), 0.025, MAT["black"], cab, "cab")
    box("InstrumentDisplay", (0.16, 0.10, 0.24), (1.37, 1.59, cab_center_z), MAT["glass"], cab, 0.018, "cab")
    box("JoystickConsole", (0.34, 0.26, 0.18), (0.68, 1.38, -0.26), MAT["black"], cab, 0.04, "cab")
    beam("Joystick", (0.72,1.46,-0.26), (0.76,1.67,-0.26), 0.025, MAT["black_soft"], cab, "cab")
    box("BrakePedal", (0.20, 0.035, 0.12), (1.20, 1.17, -0.78), MAT["zinc"], cab, 0.012, "cab", rotation=(0,0,0.25))
    box("AcceleratorPedal", (0.16, 0.035, 0.10), (1.25, 1.18, -0.52), MAT["zinc"], cab, 0.012, "cab", rotation=(0,0,0.25))
    for side, z in (("outer",-1.17),("inner",-0.13)):
        beam(f"CabHandrail_{side}", (0.25,1.18,z), (1.48,2.30,z), 0.025, MAT["black"], cab, "cab")
    for side, z in (("L",-1.28),("R",-0.18)):
        beam(f"MirrorArm_{side}", (1.34,2.16,z), (1.50,2.22,z), 0.018, MAT["black"], cab, "cab")
        box(f"Mirror_{side}", (0.05,0.18,0.14), (1.55,2.22,z), MAT["glass"], cab, 0.025, "cab")
    for step in range(2):
        box(f"CabStep_{step}", (0.42, 0.08, 0.32), (0.95 + step * 0.15, 0.72 + step * 0.20, -1.05), MAT["zinc"], cab, 0.025, "cab")

    for x, z in ((2.40,-0.82),(2.40,0.82),(-2.28,-0.82),(-2.28,0.82)):
        box(f"WorkLamp_{x}_{z}", (0.12,0.12,0.06), (x,1.44,z), MAT["lamp"], chassis, 0.025, "chassis")
    label("ModelMark_Left", "742", (-1.02,1.75,-1.102), MAT["white"], chassis, 0.24, rotation=(math.pi/2,0,0), component="chassis")
    label("ModelMark_Right", "742", (-1.02,1.75,1.102), MAT["white"], chassis, 0.24, rotation=(math.pi/2,0,math.pi), component="chassis")

    boom_pivot = empty("BoomLiftPivot", (-2.158,1.018,BOOM_LATERAL_OFFSET_M), frame, "ARROWS", 0.18, "boom")
    boom_pivot["visual_angle_degrees"] = [0,69]
    base = empty("BoomBase", owner=boom_pivot, component="boom")
    box("BaseBoomWeldment", (5.55,0.62,0.72), (2.75,0,0), MAT["cream"], base, 0.055, "boom")
    box("BaseBoomLowerWear", (5.20,0.08,0.58), (2.75,-0.32,0), MAT["cream_dark"], base, 0.025, "boom")
    cylinder("BoomPivotPin", 0.20, 0.92, (0,0,0), MAT["zinc"], base, component="boom")
    mid = empty("BoomMid", (0.12,0,0), base, "ARROWS", 0.12, "boom")
    mid["visual_travel_m"] = 3.604
    box("MidBoomWeldment", (5.35,0.49,0.59), (2.65,0,0), MAT["cream_dark"], mid, 0.048, "boom")
    box("MidBoomTopPlate", (5.10,0.055,0.47), (2.65,0.27,0), MAT["cream"], mid, 0.018, "boom")
    fly = empty("BoomFly", (0.12,0,0), mid, "ARROWS", 0.12, "boom")
    fly["visual_travel_m"] = 3.604
    box("FlyBoomWeldment", (5.296,0.38,0.48), (2.648,0,0), MAT["cream"], fly, 0.042, "boom")
    box("FlyBoomNose", (0.40,0.52,0.58), (5.096,-0.10,0), MAT["black"], fly, 0.055, "boom")
    for section, owner, positions in (("Base",base,(0.08,5.30)),("Mid",mid,(0.05,5.08)),("Fly",fly,(0.05,5.12))):
        for idx, x in enumerate(positions):
            box(f"{section}WearBand_{idx}", (0.12,0.04,0.66 if section=="Base" else 0.50), (x,0.31 if section=="Base" else 0.25,0), MAT["black"], owner, 0.015, "boom")
    label("BoomMark_Left", "JLG  742", (1.75,0.02,-0.366), MAT["black"], base, 0.17, rotation=(math.pi/2,0,0), component="boom")
    label("BoomMark_Right", "JLG  742", (1.75,0.02,0.366), MAT["black"], base, 0.17, rotation=(math.pi/2,0,math.pi), component="boom")

    lift_cyl = empty("LiftCylinder", (0,-0.82,BOOM_LATERAL_OFFSET_M), frame, component="hydraulics")
    beam("LiftCylinderBarrel", (-1.80,0.70,0), (-0.45,1.35,0), 0.150, MAT["hydraulic"], lift_cyl, "hydraulics", 28)
    beam("LiftCylinderRod", (-0.65,1.27,0), (0.25,1.76,0), 0.090, MAT["zinc"], lift_cyl, "hydraulics", 24)
    cylinder("LiftCylinderBasePin", 0.12, 0.58, (-1.80,0.70,0), MAT["zinc"], lift_cyl, component="hydraulics")
    cylinder("LiftCylinderRodPin", 0.11, 0.64, (0.25,1.76,0), MAT["zinc"], lift_cyl, component="hydraulics")
    for node in ("LiftCylinderBarrel", "LiftCylinderRod"):
        bpy.data.objects[node]["published_stroke_m"] = 1.07
    for lane, z in enumerate((-0.16,-0.23)):
        points = [(-1.88,0.74,z),(-1.20,0.98,z),(-0.42,1.38,z),(0.25,1.76,z)]
        for segment in range(3):
            beam(f"LiftHose_{lane}_{segment}", points[segment], points[segment+1], 0.018, MAT["hose"], lift_cyl, "hydraulics", 12)
    beam("TelescopeCylinderBarrel", (0.55,-0.22,0), (2.25,-0.22,0), 0.085, MAT["hydraulic"], base, "hydraulics", 20)
    beam("TelescopeCylinderRod", (2.05,-0.22,0), (3.36,-0.22,0), 0.065, MAT["zinc"], base, "hydraulics", 18)
    bpy.data.objects["TelescopeCylinderBarrel"]["published_stroke_m"] = 3.604
    bpy.data.objects["TelescopeCylinderRod"]["published_stroke_m"] = 3.604
    beam("CompensationCylinderBarrel", (-2.00,1.50,-0.31), (-1.50,1.65,-0.31), 0.120, MAT["hydraulic"], lift_cyl, "hydraulics", 22)
    beam("CompensationCylinderRod", (-1.62,1.62,-0.31), (-1.35,1.82,-0.31), 0.060, MAT["zinc"], lift_cyl, "hydraulics", 18)
    bpy.data.objects["CompensationCylinderBarrel"]["published_stroke_m"] = 0.278
    bpy.data.objects["CompensationCylinderRod"]["published_stroke_m"] = 0.278
    for lane, lateral in enumerate((-0.29,-0.24,0.24)):
        beam(f"BoomRigidTube_{lane}", (0.35,-0.34,lateral), (5.05,-0.34,lateral), 0.011, MAT["zinc"], base, "hydraulics", 10)
    boom_hose_stow = solved_pose({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                                  "level": 0, "steerMode": "circle"})["geometry"]["beams"]
    for lane in range(4):
        for segment in range(10):
            points = boom_hose_stow[f"BoomHose_{lane}_{segment}"]
            beam(f"BoomHose_{lane}_{segment}", points[0], points[1], 0.014, MAT["hose"], base, "hydraulics", 10)
    for side, z in (("L",-0.24),("R",0.24)):
        cylinder(f"BoomSheave_{side}", 0.105, 0.035, (4.80,-0.22,z), MAT["zinc"], mid, component="boom")
    cylinder("RetractSheave_C", 0.095, 0.035, (0.15,-0.34,0), MAT["zinc"], mid, component="boom")
    chain_stow = solved_pose({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                              "level": 0, "steerMode": "circle"})["geometry"]["beams"]
    for name, endpoints in chain_stow.items():
        if "Chain" not in name:
            continue
        beam(name, endpoints[0], endpoints[1], 0.012, MAT["black"], base, "boom", 10)
        bpy.data.objects[name]["mechanism_alias"] = (
            "extend-chain-tangent-path" if name.startswith("ExtendChain") else "retract-chain-tangent-path"
        )
    box("BoomAngleSensorBracket", (0.18,0.14,0.05), (-2.25,1.72,-0.50), MAT["black"], lift_cyl, 0.012, "boom")
    cylinder("BoomAngleSensorBody", 0.080, 0.070, (-2.25,1.72,-0.56), MAT["hydraulic"], lift_cyl, vertices=20, component="boom")
    beam("BoomAngleSensorCrank", (-2.25,1.72,-0.56), (-2.20,1.63,-0.56), 0.014, MAT["zinc"], lift_cyl, "boom", 10)
    beam("BoomAngleSensorLink", (-2.20,1.63,-0.56), (-1.808,1.838,-0.56), 0.012, MAT["zinc"], lift_cyl, "boom", 10)
    cylinder("BoomAngleSensorFrameJoint", 0.026, 0.090, (-2.25,1.72,-0.56), MAT["zinc"], lift_cyl, vertices=14, component="boom")
    cylinder("BoomAngleSensorCrankJoint", 0.026, 0.090, (-2.20,1.63,-0.56), MAT["zinc"], lift_cyl, vertices=14, component="boom")
    cylinder("BoomAngleSensorBoomJoint", 0.026, 0.090, (-1.808,1.838,-0.56), MAT["zinc"], lift_cyl, vertices=14, component="boom")

    carriage_pivot = empty("CarriageTiltPivot", (5.296,-0.80,0), fly, "ARROWS", 0.15, "carriage")
    carriage = empty("Carriage", owner=carriage_pivot, component="carriage")
    box("QuickCoupler", (0.30,0.88,0.96), (-0.15,0.10,0), MAT["black"], carriage, 0.055, "carriage")
    box("CarriageBackrestTop", (0.12,0.12,1.27), (-0.06,0.42,0), MAT["black"], carriage, 0.028, "carriage")
    box("CarriageBackrestBottom", (0.16,0.12,1.27), (-0.08,-0.20,0), MAT["black"], carriage, 0.028, "carriage")
    for z in (-0.58,0.58):
        square_beam(f"CarriagePost_{z:+.0f}", (-0.08,-0.42,z), (-0.08,0.62,z), 0.075, MAT["black"], carriage, "carriage")
    cylinder("ForkPin", 0.038, 1.18, (0.0,0.28,0), MAT["zinc"], carriage, component="carriage")
    for side, z in (("L",-0.34),("R",0.34)):
        box(f"ForkShank_{side}", (0.060,0.92,0.102), (0.03,-0.19,z), MAT["black"], carriage, 0.018, "carriage")
        fork = box(f"Fork{side}", (1.2192,0.060,0.102), (0.6096,-0.68,z), MAT["black"], carriage, 0.016, "carriage")
        fork["published_fork_length_m"] = 1.2192
        fork["published_fork_thickness_m"] = 0.060
        fork["published_fork_width_m"] = 0.102
        cylinder(f"ForkCollar_{side}", 0.058, 0.12, (0.0,0.28,z), MAT["zinc"], carriage, component="carriage")
    beam("CarriageTiltCylinderBarrel", (4.216,-1.21,0.42), (4.82,-1.08,0.42), 0.120, MAT["hydraulic"], fly, "hydraulics", 20)
    beam("CarriageTiltCylinderRod", (4.70,-1.10,0.42), (5.15,-0.43,0.42), 0.060, MAT["zinc"], fly, "hydraulics", 18)
    beam("CarriageTiltLink", (5.15,-0.43,0.42), (5.216,-0.22,0.42), 0.028, MAT["zinc"], fly, "hydraulics", 14)
    for node in ("CarriageTiltCylinderBarrel", "CarriageTiltCylinderRod"):
        bpy.data.objects[node]["published_stroke_m"] = 0.388

    beam("FrameLevelCylinderBarrel", (-0.0133,0.6054,0.4865), (0.06,0.96,0.88), 0.120, MAT["hydraulic"], root, "frame", 20)
    beam("FrameLevelCylinderRod", (0.045,0.90,0.82), (0.1121,1.2428,1.1607), 0.055, MAT["zinc"], root, "frame", 18)
    for node in ("FrameLevelCylinderBarrel", "FrameLevelCylinderRod"):
        bpy.data.objects[node]["published_stroke_m"] = 0.168
    cylinder("FrameLevelIndicator", 0.055, 0.04, (1.30,1.73,-0.20), MAT["lamp"], cab, rotation=(math.pi/2,0,0), component="cab")
    ras = empty("RearAxleStabilizerCylinder", owner=root, component="steering")
    beam("RearAxleStabilizerBarrel", (-1.95,0.64,-0.45), (-1.72,0.80,-0.56), 0.120, MAT["hydraulic"], ras, "steering", 20)
    beam("RearAxleStabilizerRod", (-1.78,0.76,-0.53), (-1.55,0.92,-0.65), 0.055, MAT["zinc"], ras, "steering", 18)
    for node in ("RearAxleStabilizerBarrel", "RearAxleStabilizerRod"):
        bpy.data.objects[node]["published_stroke_m"] = 0.2

    # Semantic selection volumes are invisible in the runtime and excluded from visual bounds.
    for name, size, location, owner, component in (
        ("Chassis_Hit", (5.65,1.35,2.10), (0,0.33,0), frame, "chassis"),
        ("Cab_Hit", (1.65,1.55,1.10), (0.82,0.88,-0.64), frame, "cab"),
        ("Boom_Hit", (5.70,0.85,0.90), (2.75,0,0), base, "boom"),
        ("Carriage_Hit", (1.55,1.50,1.40), (0.55,-0.10,0), carriage, "carriage"),
        ("Steering_Hit", (4.30,1.35,2.40), (0,0.64,0), running, "steering"),
        ("Hydraulics_Hit", (2.65,1.30,1.30), (-0.55,0.63,0.58), frame, "hydraulics"),
    ):
        hit = box(name, size, location, MAT["black"], owner, 0, component)
        hit["is_hit_volume"] = True

    # Freeze the exported source at the exact runtime stow. Every dynamic beam
    # is posed by the executable production solver, eliminating renderer/build
    # math drift and preserving fixed barrel lengths in the authored GLB.
    stow = solved_pose({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                        "level": 0, "steerMode": "circle"})
    state = stow["state"]
    boom_pivot.rotation_euler[2] = state["boomAngle"]
    mid.location.x = 0.12 + state["midTranslation"]
    fly.location.x = 0.12 + state["flyTranslation"]
    carriage_pivot.rotation_euler[2] = state["carriageAngle"]
    frame.rotation_euler[0] = state["frameAngle"]
    for corner, angle in state["wheelAngles"].items():
        wheels[corner].rotation_euler[1] = angle
    for name, endpoints in stow["geometry"]["beams"].items():
        pose_beam(name, endpoints)
    for name, point in stow["geometry"]["points"].items():
        bpy.data.objects[name].location = point
    root["solver_contract"] = "machines/742/solver.js"
    chain_alias = lambda prefix: [prefix, f"{prefix}_Wrap", *[
        f"{prefix}_Wrap_{index}" for index in range(1, 8)
    ], f"{prefix}_Moving"]
    root["mechanism_aliases"] = json.dumps({
        "extend_chain_left": chain_alias("ExtendChain_L"),
        "extend_chain_right": chain_alias("ExtendChain_R"),
        "retract_chain": chain_alias("RetractChain_C"),
        "front_steer_actuator": ["FrontSteerCylinderBarrel", "FrontSteerCylinderRodLeft", "FrontSteerCylinderRodRight", "FrontSteerBarLeft", "FrontSteerBarRight"],
        "rear_steer_actuator": ["RearSteerCylinderBarrel", "RearSteerCylinderRodLeft", "RearSteerCylinderRodRight", "RearSteerBarLeft", "RearSteerBarRight"],
    }, sort_keys=True)

    bpy.context.scene["asset_configuration_id"] = CONFIG["configuration_id"]
    bpy.context.scene["evidence_freeze_date"] = "2026-08-25"
    bpy.context.scene["authoring_note"] = "Owned 742 reconstruction; official BIM and imagery excluded from asset"
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "METERS"

    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH), export_format="GLB", export_yup=True, export_apply=False,
        export_extras=True, export_cameras=False, export_lights=False,
    )
    print(json.dumps({"status":"PASS","blend":str(BLEND_PATH),"glb":str(GLB_PATH),"configuration_id":CONFIG["configuration_id"],"objects":len(bpy.data.objects)}, indent=2))


build()
