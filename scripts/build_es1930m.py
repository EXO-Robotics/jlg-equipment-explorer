#!/usr/bin/env python3
"""Build the evidence-bounded ES1930M PVC 2404 showcase asset in Blender."""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "machines/es1930m/mechanism.json").read_text())
CONFIG = json.loads((ROOT / "machines/es1930m/es1930m.configuration.json").read_text())
BLEND_PATH = ROOT / "source/blender/es1930m-showcase-v1.0.blend"
GLB_PATH = ROOT / "assets/models/es1930m.glb"


def material(name: str, color: tuple[float, float, float, float], metallic=0.0, roughness=0.55):
    result = bpy.data.materials.new(name)
    result.diffuse_color = color
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return result


MAT = {}


def parent_keep_transform(child, parent):
    child.parent = parent


def empty(name: str, location=(0, 0, 0), parent=None, display="PLAIN_AXES", size=0.04):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = location
    bpy.context.collection.objects.link(obj)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def bevelled_box(name, size, location, mat, parent=None, bevel=0.012, component=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(value / 2 for value in size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    obj.data.materials.append(mat)
    if component:
        obj["component"] = component
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def cylinder(name, radius, depth, location, mat, parent=None, rotation=(0, 0, 0), vertices=24, component=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    if component:
        obj["component"] = component
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def beam_between(name, a, b, radius, mat, parent=None, component=None, vertices=16):
    start, end = Vector(a), Vector(b)
    direction = end - start
    obj = cylinder(name, radius, direction.length, (start + end) / 2, mat, parent, vertices=vertices, component=component)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    return obj


def square_beam_between(name, a, b, thickness, mat, parent=None, component=None):
    start, end = Vector(a), Vector(b)
    direction = end - start
    obj = bevelled_box(name, (direction.length, thickness, thickness), (start + end) / 2, mat, parent, thickness * 0.12, component)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(direction.normalized())
    return obj


def text_label(name, text, location, mat, parent=None, rotation=(math.pi / 2, 0, 0), size=0.065):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.0015
    obj.data.bevel_depth = 0.0005
    obj.data.materials.append(mat)
    if parent:
        parent_keep_transform(obj, parent)
    return obj


def link_group(name, a, b, lateral, lane, parent):
    start = Vector((a[0], lateral + lane, a[1]))
    end = Vector((b[0], lateral + lane, b[1]))
    center = (start + end) / 2
    direction = end - start
    group = empty(name, center, parent, "ARROWS", 0.055)
    group["component"] = "scissor"
    group["pin_center_length_m"] = direction.length
    group["authority"] = "reconstructed_geometry_verified_topology"
    group.rotation_mode = "QUATERNION"
    group.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(direction.normalized())
    arm = bevelled_box(f"{name}_Arm", (direction.length, 0.052, 0.105), (0, 0, 0), MAT["scissor"], group, 0.018, "scissor")
    arm.location = (0, 0, 0)
    for suffix, sign in (("PIVOT_A", -1), ("PIVOT_B", 1)):
        pivot = empty(f"{name}_{suffix}", (sign * direction.length / 2, 0, 0), group, "SPHERE", 0.026)
        pivot["is_pivot_marker"] = True
    center_pivot = empty(f"{name}_PIVOT_CENTER", (0, 0, 0), group, "SPHERE", 0.028)
    center_pivot["is_pivot_marker"] = True
    return group


def solve_stowed():
    solver = SPEC["solver"]
    rise = (
        solver["stowed_deck_floor_height_m"]
        - solver["base_pivot_height_m"]
        - solver["deck_floor_offset_above_upper_pivots_m"]
    ) / solver["level_count"]
    span = math.sqrt(solver["arm_pin_center_length_m"] ** 2 - rise**2)
    boundaries = []
    for index in range(solver["level_count"] + 1):
        height = solver["base_pivot_height_m"] + index * rise
        rear = SPEC["slides"]["rear_fixed_x_m"]
        boundaries.append({"rear": (rear, height), "front": (rear + span, height)})
    return rise, span, boundaries


def build():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass

    MAT.update({
        "jlg_orange": material("JLG Safety Orange", (0.94, 0.45, 0.025, 1), 0.06, 0.42),
        "scissor": material("JLG Scissor Sand", (0.56, 0.49, 0.34, 1), 0.34, 0.46),
        "tire": material("Nonmarking Tire", (0.105, 0.11, 0.10, 1), 0.0, 0.92),
        "wheel": material("Wheel Hub", (0.29, 0.31, 0.29, 1), 0.55, 0.38),
        "zinc": material("Zinc Hardware", (0.50, 0.53, 0.51, 1), 0.72, 0.30),
        "black": material("Control Black", (0.025, 0.03, 0.028, 1), 0.15, 0.52),
        "red": material("Emergency Red", (0.68, 0.018, 0.012, 1), 0.05, 0.40),
        "white": material("Marking White", (0.82, 0.83, 0.77, 1), 0.02, 0.65),
        "battery": material("Battery Case", (0.12, 0.14, 0.15, 1), 0.05, 0.74),
        "deck": material("Deck Surface", (0.19, 0.20, 0.18, 1), 0.45, 0.55),
    })

    root = empty("ES1930M_ROOT", (0, 0, 0), display="CUBE", size=0.12)
    root["model"] = "JLG ES1930M"
    root["configuration_id"] = CONFIG["configuration_id"]
    root["pvc"] = "2404"
    root["release"] = "1.0.2"
    root["units"] = "meters"
    root["disclaimer"] = "visual reconstruction; not a safety, stability, load, or service simulation"

    chassis = empty("Chassis", parent=root)
    chassis["component"] = "chassis"
    bevelled_box("Chassis_MainFrame", (1.43, 0.66, 0.20), (0, 0, 0.26), MAT["scissor"], chassis, 0.035, "chassis")
    bevelled_box("Chassis_LowerTray", (1.40, 0.72, 0.11), (0, 0, 0.145), MAT["black"], chassis, 0.035, "chassis")
    bevelled_box("LeftBatteryDoor", (0.68, 0.035, 0.30), (0.20, 0.362, 0.39), MAT["jlg_orange"], chassis, 0.025, "battery_compartment")
    bevelled_box("RightHydraulicDoor", (0.68, 0.035, 0.30), (0.20, -0.362, 0.39), MAT["jlg_orange"], chassis, 0.025, "hydraulics")
    bevelled_box("RearCounterweight", (0.33, 0.69, 0.34), (-0.58, 0, 0.39), MAT["black"], chassis, 0.045, "chassis")
    for side in (-1, 1):
        bevelled_box(f"FrontNosePost_{side}", (0.27, 0.11, 0.30), (0.60, side * 0.29, 0.37), MAT["black"], chassis, 0.035, "steering")
    bevelled_box("FrontNoseCrossmember", (0.27, 0.69, 0.075), (0.60, 0, 0.49), MAT["black"], chassis, 0.025, "steering")
    bevelled_box("FrontLowerBumper", (0.27, 0.69, 0.055), (0.60, 0, 0.23), MAT["black"], chassis, 0.022, "steering")

    for side in (-1, 1):
        panel_y = side * 0.374
        bevelled_box(f"ModelBadgePlate_{side}", (0.34, 0.006, 0.12), (0.18, panel_y, 0.40), MAT["black"], chassis, 0.006, "chassis")
        facing_rotation = (math.pi / 2, 0, 0) if side < 0 else (math.pi / 2, 0, math.pi)
        text_label(f"ES1930M_Label_{side}", "ES1930M", (0.18, side * 0.378, 0.41), MAT["white"], chassis, facing_rotation, 0.055)
        bevelled_box(f"SafetyLabel_{side}", (0.13, 0.006, 0.065), (-0.10, panel_y, 0.42), MAT["white"], chassis, 0.003, "chassis")

    batteries = empty("BatteryCompartments", parent=chassis)
    for side in (-1, 1):
        case = bevelled_box(f"Battery_{'R' if side < 0 else 'L'}_12V130Ah", (0.44, 0.24, 0.20), (0.05, side * 0.205, 0.34), MAT["battery"], batteries, 0.018, "battery_compartment")
        case["battery"] = "12 V 130 Ah flooded lead-acid"
        for terminal_x in (-0.12, 0.12):
            cylinder(f"BatteryTerminal_{side}_{terminal_x}", 0.018, 0.025, (0.05 + terminal_x, side * 0.205, 0.452), MAT["zinc"], batteries)

    hydraulics = empty("HydraulicPowerpack", parent=chassis)
    bevelled_box("HydraulicReservoir", (0.34, 0.22, 0.18), (-0.15, -0.18, 0.34), MAT["black"], hydraulics, 0.018, "hydraulics")
    cylinder("HydraulicPumpMotor", 0.07, 0.24, (0.08, -0.18, 0.40), MAT["zinc"], hydraulics, rotation=(0, math.pi / 2, 0), component="hydraulics")
    bevelled_box("HydraulicValveBlock", (0.13, 0.12, 0.08), (-0.03, -0.17, 0.51), MAT["zinc"], hydraulics, 0.008, "hydraulics")

    ground = empty("GroundControls", parent=chassis)
    bevelled_box("GroundControlPanel", (0.22, 0.022, 0.15), (-0.49, -0.35, 0.48), MAT["black"], ground, 0.012, "controls")
    cylinder("GroundEmergencyStop", 0.022, 0.025, (-0.45, -0.365, 0.51), MAT["red"], ground, rotation=(math.pi / 2, 0, 0), component="controls")
    cylinder("GroundSelector", 0.013, 0.024, (-0.53, -0.365, 0.47), MAT["zinc"], ground, rotation=(math.pi / 2, 0, 0), component="controls")

    steer = empty("FrontSteerAssembly", parent=chassis)
    wheel_x = 0.535
    rear_x = wheel_x - CONFIG["published_dimensions_m"]["wheelbase"]
    wheel_lateral = 0.335
    for side in (-1, 1):
        spindle = empty(f"SteerSpindle_{'R' if side < 0 else 'L'}", (wheel_x, side * wheel_lateral, 0.135), steer, "ARROWS", 0.07)
        spindle["component"] = "steering"
        cylinder(f"FrontTire_{side}", 0.13, 0.09, (0, 0, 0), MAT["tire"], spindle, rotation=(math.pi / 2, 0, 0), vertices=32, component="steering")
        cylinder(f"FrontHub_{side}", 0.061, 0.09, (0, 0, 0), MAT["wheel"], spindle, rotation=(math.pi / 2, 0, 0), component="steering")
        cylinder(f"RearTire_{side}", 0.13, 0.09, (rear_x, side * wheel_lateral, 0.135), MAT["tire"], chassis, rotation=(math.pi / 2, 0, 0), vertices=32, component="chassis")
        cylinder(f"RearHub_{side}", 0.058, 0.09, (rear_x, side * wheel_lateral, 0.135), MAT["wheel"], chassis, rotation=(math.pi / 2, 0, 0), component="chassis")
    steer_cyl = empty("SteerCylinder", parent=steer)
    beam_between("SteerCylinderBarrel", (0.535, -0.22, 0.24), (0.535, 0.22, 0.24), 0.032, MAT["scissor"], steer_cyl, "steering")
    beam_between("SteerCylinderRod", (0.535, -0.31, 0.24), (0.535, 0.31, 0.24), 0.0175, MAT["zinc"], steer_cyl, "steering")
    for side in (-1, 1):
        pivot = empty(f"PIVOT_STEER_{'R' if side < 0 else 'L'}", (wheel_x, side * 0.31, 0.24), steer, "SPHERE", 0.025)
        pivot["is_pivot_marker"] = True

    pothole = empty("PotholeProtection", parent=chassis)
    for side in (-1, 1):
        bevelled_box(f"PotholeBar_{'R' if side < 0 else 'L'}", (1.02, 0.045, 0.075), (-0.04, side * 0.345, 0.10), MAT["scissor"], pothole, 0.012, "pothole")
        beam_between(f"PotholeLink_{side}", (-0.28, side * 0.31, 0.16), (-0.16, side * 0.345, 0.10), 0.012, MAT["zinc"], pothole, "pothole")

    scissor = empty("ScissorAssembly", parent=root)
    rise, span, boundaries = solve_stowed()
    lane_offset = SPEC["solver"]["crossing_arm_lane_offset_m"]
    for level in range(5):
        level_root = empty(f"Level{level + 1:02d}", parent=scissor)
        lower, upper = boundaries[level], boundaries[level + 1]
        for plane_name, lateral in (("Right", -0.27), ("Left", 0.27)):
            link_group(f"Level{level + 1:02d}_A_{plane_name}", lower["rear"], upper["front"], lateral, -lane_offset, level_root)
            link_group(f"Level{level + 1:02d}_B_{plane_name}", lower["front"], upper["rear"], lateral, lane_offset, level_root)
        for boundary_name, point in (("LOWER_L", lower["rear"]), ("LOWER_R", lower["front"]), ("UPPER_L", upper["rear"]), ("UPPER_R", upper["front"])):
            pin = beam_between(f"Level{level + 1:02d}_PIN_{boundary_name}", (point[0], -0.31, point[1]), (point[0], 0.31, point[1]), 0.024, MAT["zinc"], level_root, "scissor")
            pin["is_pivot_pin"] = True
        center_x = (lower["rear"][0] + upper["front"][0]) / 2
        center_y = (lower["rear"][1] + upper["front"][1]) / 2
        center_pin = beam_between(f"Level{level + 1:02d}_PIN_CENTER", (center_x, -0.31, center_y), (center_x, 0.31, center_y), 0.026, MAT["zinc"], level_root, "scissor")
        center_pin["is_pivot_pin"] = True

    front_x = boundaries[0]["front"][0]
    rear_x = boundaries[0]["rear"][0]
    for plane, lateral in (("RIGHT_PLANE", -0.27), ("LEFT_PLANE", 0.27)):
        block = bevelled_box(f"LowerSlideBlock_{plane}", (0.12, 0.065, 0.06), (front_x, lateral, SPEC["solver"]["base_pivot_height_m"]), MAT["zinc"], scissor, 0.012, "scissor")
        block["slide_axis"] = "X"
        pivot = empty(f"PIVOT_STACK_LOWER_FRONT_{plane}", (front_x, lateral, SPEC["solver"]["base_pivot_height_m"]), scissor, "SPHERE", 0.03)
        pivot["is_pivot_marker"] = True
        fixed = empty(f"PIVOT_STACK_LOWER_REAR_{plane}", (rear_x, lateral, SPEC["solver"]["base_pivot_height_m"]), scissor, "SPHERE", 0.03)
        fixed["is_pivot_marker"] = True
        upper_block = bevelled_box(f"UpperSlideBlock_{plane}", (0.12, 0.065, 0.06), (boundaries[-1]["front"][0], lateral, boundaries[-1]["front"][1]), MAT["zinc"], scissor, 0.012, "scissor")
        upper_block["slide_axis"] = "X"

    cylinder_root = empty("LiftCylinder", parent=root)
    cylinder_spec = SPEC["lift_cylinder"]
    lower = Vector((cylinder_spec["reconstructed_lower_frame_pin_m"][0], 0, cylinder_spec["reconstructed_lower_frame_pin_m"][1]))
    a_start = Vector((boundaries[0]["rear"][0], 0, boundaries[0]["rear"][1]))
    a_end = Vector((boundaries[1]["front"][0], 0, boundaries[1]["front"][1]))
    center = a_start.lerp(a_end, cylinder_spec["reconstructed_kicker_pivot_fraction_on_level01_a"])
    arm_direction = (a_end - a_start).normalized()
    arm_normal = Vector((-arm_direction.z, 0, arm_direction.x))
    cylinder_offset = cylinder_spec["reconstructed_cylinder_pin_offset_link_frame_m"]
    roller_offset = cylinder_spec["reconstructed_kicker_roller_offset_link_frame_m"]
    upper = center + arm_direction * cylinder_offset[0] + arm_normal * cylinder_offset[1]
    roller = center + arm_direction * roller_offset[0] + arm_normal * roller_offset[1]
    barrel_end = lower.lerp(upper, 0.72)
    rod_start = lower.lerp(upper, 0.48)
    beam_between("LiftCylinderBarrel", lower, barrel_end, 0.035, MAT["scissor"], cylinder_root, "lift_cylinder", 24)
    beam_between("LiftCylinderRod", rod_start, upper, 0.0225, MAT["zinc"], cylinder_root, "lift_cylinder", 24)
    for name, point in (("PIVOT_LIFT_CYLINDER_LOWER", lower), ("PIVOT_LIFT_CYLINDER_UPPER", upper), ("PIVOT_KICKER_TO_SCISSOR", center), ("PIVOT_KICKER_ROLLER", roller)):
        marker = empty(name, point, cylinder_root, "SPHERE", 0.03)
        marker["is_pivot_marker"] = True
    beam_between("KickerArmWeb_SCISSOR_CYLINDER", center, upper, 0.038, MAT["scissor"], cylinder_root, "scissor", 18)
    beam_between("KickerArmWeb_CYLINDER_ROLLER", upper, roller, 0.038, MAT["scissor"], cylinder_root, "scissor", 18)
    beam_between("KickerArmWeb_ROLLER_SCISSOR", roller, center, 0.038, MAT["scissor"], cylinder_root, "scissor", 18)
    cylinder("KickerRoller", 0.052, 0.075, roller, MAT["zinc"], cylinder_root, rotation=(math.pi / 2, 0, 0), component="scissor")

    platform = empty("PlatformAssembly", parent=root)
    deck_y = SPEC["solver"]["stowed_deck_floor_height_m"]
    platform["component"] = "platform"
    bevelled_box("MainDeck", (1.34, 0.70, 0.075), (0.02, 0, deck_y - 0.038), MAT["deck"], platform, 0.018, "platform")
    for groove in range(-5, 6):
        bevelled_box(f"DeckGrip_{groove:+03d}", (0.008, 0.64, 0.006), (0.02 + groove * 0.105, 0, deck_y + 0.002), MAT["zinc"], platform, 0.002, "platform")
    extension = empty("ExtensionDeck", parent=platform)
    extension["component"] = "extension_deck"
    extension["travel_m"] = 0.55
    bevelled_box("ExtensionDeckWeldment", (0.568, 0.67, 0.06), (0.434, 0, deck_y + 0.008), MAT["deck"], extension, 0.015, "extension_deck")
    rail_contract = SPEC["deck_extension"]
    fixed_lateral = rail_contract["fixed_outer_rail_lateral_m"]
    moving_lateral = rail_contract["moving_inner_rail_lateral_m"]
    x_min = rail_contract["fixed_outer_rail_rear_x_m"]
    x_max = rail_contract["fixed_outer_rail_front_x_m"]
    moving_rear = rail_contract["moving_inner_rail_rear_x_m"]
    moving_front = rail_contract["moving_inner_rail_front_x_m"]
    moving_length = moving_front - moving_rear
    moving_center = (moving_front + moving_rear) / 2
    for side in (-1, 1):
        toe = bevelled_box(f"ExtensionToeBoard_{side}", (moving_length, 0.035, 0.25), (moving_center, side * moving_lateral, deck_y + 0.125), MAT["jlg_orange"], extension, 0.012, "extension_deck")
        toe["guard_branch"] = "moving_inner"
        toe["authored_rear_x_m"] = moving_rear
    bevelled_box("ExtensionFrontToeBoard", (0.035, moving_lateral * 2, 0.25), (moving_front, 0, deck_y + 0.125), MAT["jlg_orange"], extension, 0.012, "extension_deck")
    for side in (-1, 1):
        for x in (0.18, 0.56):
            cylinder(f"ExtensionRoller_{side}_{x}", 0.025, 0.036, (x, side * 0.315, deck_y - 0.035), MAT["zinc"], extension, rotation=(math.pi / 2, 0, 0), component="extension_deck")

    rails = empty("FixedRails", parent=platform)
    top = 1.962
    rail_size = 0.034
    fixed_length = x_max - x_min
    fixed_center = (x_max + x_min) / 2
    for side in (-1, 1):
        toe = bevelled_box(f"MainToeBoard_{side}", (fixed_length, 0.035, 0.25), (fixed_center, side * fixed_lateral, deck_y + 0.125), MAT["jlg_orange"], rails, 0.012, "platform")
        toe["guard_branch"] = "fixed_outer"
        toe["authored_front_x_m"] = x_max
    bevelled_box("RearToeBoard", (0.035, 0.67, 0.25), (x_min, 0, deck_y + 0.125), MAT["jlg_orange"], rails, 0.012, "platform")
    for side in (-1, 1):
        y = side * fixed_lateral
        top_rail = square_beam_between(f"TopRail_{side}", (x_min, y, top), (x_max, y, top), rail_size, MAT["jlg_orange"], rails, "platform")
        mid_rail = square_beam_between(f"MidRail_{side}", (x_min, y, 1.48), (x_max, y, 1.48), rail_size, MAT["jlg_orange"], rails, "platform")
        for rail in (top_rail, mid_rail):
            rail["guard_branch"] = "fixed_outer"
            rail["authored_front_x_m"] = x_max
        for index, x in enumerate((x_min, -0.20, moving_rear)):
            square_beam_between(f"RailPost_{side}_{index}", (x, y, deck_y + 0.02), (x, y, top), rail_size, MAT["jlg_orange"], rails, "platform")
    for height in (1.48, top):
        square_beam_between(f"RearRail_{height}", (x_min, -0.332, height), (x_min, 0.332, height), rail_size, MAT["jlg_orange"], rails, "platform")

    extension_rails = empty("ExtensionRails", parent=extension)
    for side in (-1, 1):
        y = side * moving_lateral
        top_rail = square_beam_between(f"ExtensionTopRail_{side}", (moving_rear, y, top), (moving_front, y, top), rail_size, MAT["jlg_orange"], extension_rails, "extension_deck")
        mid_rail = square_beam_between(f"ExtensionMidRail_{side}", (moving_rear, y, 1.48), (moving_front, y, 1.48), rail_size, MAT["jlg_orange"], extension_rails, "extension_deck")
        for rail in (top_rail, mid_rail):
            rail["guard_branch"] = "moving_inner"
            rail["authored_rear_x_m"] = moving_rear
        for index, x in enumerate((0.42, x_max)):
            square_beam_between(f"ExtensionRailPost_{side}_{index}", (x, y, deck_y + 0.02), (x, y, top), rail_size, MAT["jlg_orange"], extension_rails, "extension_deck")
    gate = empty("SelfClosingGate", parent=extension)
    for height in (1.48, top):
        square_beam_between(f"GateRail_{height}", (x_max, -moving_lateral, height), (x_max, moving_lateral, height), rail_size, MAT["jlg_orange"], gate, "platform")
    gate_hinge = empty("PIVOT_GATE_HINGE", (x_max, -moving_lateral, top), gate, "SPHERE", 0.025)
    gate_hinge["is_pivot_marker"] = True

    controls = empty("PlatformControls", parent=platform)
    bevelled_box("PlatformControlBox", (0.22, 0.16, 0.13), (0.42, -0.27, 1.78), MAT["black"], controls, 0.022, "controls")
    cylinder("PlatformEmergencyStop", 0.022, 0.026, (0.37, -0.365, 1.80), MAT["red"], controls, rotation=(math.pi / 2, 0, 0), component="controls")
    cylinder("PlatformJoystick", 0.016, 0.105, (0.46, -0.31, 1.88), MAT["black"], controls, rotation=(0.12, 0, 0), component="controls")

    for name, size, location, component in (
        ("Chassis_Hit", (1.48, 0.76, 0.55), (0, 0, 0.30), "chassis"),
        ("Scissor_Hit", (1.12, 0.65, 0.55), (0, 0, 0.58), "scissor"),
        ("Platform_Hit", (1.38, 0.74, 1.10), (0.02, 0, 1.44), "platform"),
        ("Steering_Hit", (0.34, 0.76, 0.34), (0.54, 0, 0.20), "steering"),
    ):
        hit = bevelled_box(name, size, location, MAT["black"], root, 0, component)
        hit["is_hit_volume"] = True

    bpy.context.scene["asset_configuration_id"] = CONFIG["configuration_id"]
    bpy.context.scene["evidence_freeze_date"] = "2026-08-25"
    bpy.context.scene["authoring_note"] = "PVC 2404 topology with explicitly reconstructed pivot coordinates"
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "METERS"

    BLEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    GLB_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
    )
    print(json.dumps({
        "status": "PASS",
        "blend": str(BLEND_PATH),
        "glb": str(GLB_PATH),
        "configuration_id": CONFIG["configuration_id"],
        "objects": len(bpy.data.objects),
    }, indent=2))


build()
