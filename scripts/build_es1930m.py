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


def bevelled_box(name, size, location, mat, parent=None, bevel=0.012, component=None, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
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


def torus(name, major_radius, minor_radius, location, mat, parent=None, rotation=(0, 0, 0), component=None):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=20,
        minor_segments=8,
        location=location,
        rotation=rotation,
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
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
    # Keep the independently typeset markings as shallow applied films.  The
    # earlier rounded extrusion multiplied the glyph triangulation enough to
    # break the mobile GLB budget without adding visible accuracy at this size.
    obj.data.resolution_u = 1
    obj.data.extrude = 0.00025
    obj.data.bevel_depth = 0.0
    obj.data.materials.append(mat)
    if parent:
        parent_keep_transform(obj, parent)
    obj["marking_authority"] = "independently_typeset_nominative_mark"
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
        "green": material("Indicator Green", (0.035, 0.56, 0.12, 1), 0.0, 0.30),
        "yellow": material("Indicator Amber", (0.96, 0.52, 0.025, 1), 0.0, 0.32),
        "blue": material("Display Blue Black", (0.018, 0.075, 0.105, 1), 0.05, 0.25),
        "teal": material("Model Badge Teal", (0.025, 0.56, 0.66, 1), 0.02, 0.34),
        "rubber": material("Control Rubber", (0.012, 0.014, 0.013, 1), 0.0, 0.88),
        "white": material("Marking White", (0.82, 0.83, 0.77, 1), 0.02, 0.65),
        "battery": material("Battery Case", (0.12, 0.14, 0.15, 1), 0.05, 0.74),
        "deck": material("Deck Surface", (0.19, 0.20, 0.18, 1), 0.45, 0.55),
    })

    root = empty("ES1930M_ROOT", (0, 0, 0), display="CUBE", size=0.12)
    root["model"] = "JLG ES1930M"
    root["configuration_id"] = CONFIG["configuration_id"]
    root["pvc"] = "2404"
    root["release"] = "1.0.5"
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

    # PVC 2404 parts Fig. 8-7 (items 825A, 1001256675/1001256676
    # and door treatments 1001304321/1001304322) places the JLG identity on
    # both chassis access-door faces. The deployed marks are independently
    # typeset text and simple owned backing geometry, not copied decal artwork.
    for side, suffix in ((-1, "RH"), (1, "LH")):
        # The access-door skin ends at +/-0.3795 m. Model these as thin applied
        # films just outside the skin; thicker plaques incorrectly broaden the
        # published 30-inch machine envelope.
        panel_y = side * 0.3802
        badge = bevelled_box(f"ChassisJLGPlate_{suffix}", (0.22, 0.0010, 0.105), (0.20, panel_y, 0.40), MAT["black"], chassis, 0.0002, "chassis")
        badge["marking_source"] = "PVC2404_parts_fig_8_7_items_825A"
        facing_rotation = (math.pi / 2, 0, 0) if side < 0 else (math.pi / 2, 0, math.pi)
        mark = text_label(f"ChassisJLGMark_{suffix}", "JLG", (0.20, side * 0.3808, 0.405), MAT["white"], chassis, facing_rotation, 0.068)
        mark["marking_source"] = "PVC2404_parts_fig_8_7_items_825A"
        accent = bevelled_box(
            f"ChassisJLGAccent_{suffix}",
            (0.075, 0.0010, 0.024),
            (0.286, side * 0.3807, 0.355),
            MAT["teal"],
            chassis,
            0.0002,
            "chassis",
            rotation=(0, side * 0.25, 0),
        )
        accent["marking_source"] = "official_standard_machine_gallery_V01_V02"
        bevelled_box(f"SafetyLabel_{side}", (0.13, 0.0010, 0.065), (-0.10, panel_y, 0.42), MAT["white"], chassis, 0.0002, "chassis")

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
        side_name = "R" if side < 0 else "L"
        front_roll = empty(f"FrontWheelRoll_{side_name}", parent=spindle, display="ARROWS", size=0.045)
        front_roll["component"] = "steering"
        front_roll["authority"] = "reconstructed_presentation_motion"
        cylinder(f"FrontTire_{side}", 0.13, 0.09, (0, 0, 0), MAT["tire"], front_roll, rotation=(math.pi / 2, 0, 0), vertices=32, component="steering")
        cylinder(f"FrontHub_{side}", 0.061, 0.09, (0, 0, 0), MAT["wheel"], front_roll, rotation=(math.pi / 2, 0, 0), component="steering")
        for tread_index in range(12):
            angle = tread_index * math.tau / 12
            bevelled_box(
                f"FrontTread_{side}_{tread_index:02d}", (0.040, 0.096, 0.012),
                (0.128 * math.cos(angle), 0, 0.128 * math.sin(angle)), MAT["rubber"], front_roll,
                0.002, "steering", rotation=(0, angle + math.pi / 2, 0),
            )
        bevelled_box(f"FrontHubIndex_{side}", (0.045, 0.096, 0.010), (0.028, 0, 0), MAT["zinc"], front_roll, 0.002, "steering")
        rear_roll = empty(f"RearWheelRoll_{side_name}", (rear_x, side * wheel_lateral, 0.135), chassis, "ARROWS", 0.045)
        rear_roll["component"] = "chassis"
        rear_roll["authority"] = "reconstructed_presentation_motion"
        cylinder(f"RearTire_{side}", 0.13, 0.09, (0, 0, 0), MAT["tire"], rear_roll, rotation=(math.pi / 2, 0, 0), vertices=32, component="chassis")
        cylinder(f"RearHub_{side}", 0.058, 0.09, (0, 0, 0), MAT["wheel"], rear_roll, rotation=(math.pi / 2, 0, 0), component="chassis")
        for tread_index in range(12):
            angle = tread_index * math.tau / 12
            bevelled_box(
                f"RearTread_{side}_{tread_index:02d}", (0.040, 0.096, 0.012),
                (0.128 * math.cos(angle), 0, 0.128 * math.sin(angle)), MAT["rubber"], rear_roll,
                0.002, "chassis", rotation=(0, angle + math.pi / 2, 0),
            )
        bevelled_box(f"RearHubIndex_{side}", (0.045, 0.096, 0.010), (0.028, 0, 0), MAT["zinc"], rear_roll, 0.002, "chassis")
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
    # The official standard-machine gallery shows the end-board wordmark
    # applied directly to orange, with a dark outline rather than a plaque.
    front_outline = text_label("PlatformJLGOutline_Front", "JLG", (moving_front + 0.022, 0, deck_y + 0.128), MAT["black"], extension, (math.pi / 2, 0, math.pi / 2), 0.104)
    front_outline["marking_source"] = "official_standard_machine_gallery_V01"
    front_mark = text_label("PlatformJLGMark_Front", "JLG", (moving_front + 0.024, 0, deck_y + 0.128), MAT["white"], extension, (math.pi / 2, 0, math.pi / 2), 0.090)
    front_mark["marking_source"] = "PVC2404_parts_fig_8_7_item_825A"
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
        suffix = "RH" if side < 0 else "LH"
        facing_rotation = (math.pi / 2, 0, 0) if side < 0 else (math.pi / 2, 0, math.pi)
        badge_x = 0.27
        plate = bevelled_box(f"PlatformModelBadgePlate_{suffix}", (0.38, 0.007, 0.125), (badge_x, side * (fixed_lateral + 0.020), deck_y + 0.128), MAT["black"], rails, 0.006, "platform")
        plate["marking_source"] = f"PVC2404_parts_fig_8_7_item_822{'A' if side < 0 else 'B'}"
        accent = bevelled_box(f"PlatformModelBadgeAccent_{suffix}", (0.040, 0.008, 0.142), (badge_x - 0.176, side * (fixed_lateral + 0.022), deck_y + 0.128), MAT["teal"], rails, 0.004, "platform", rotation=(0, side * 0.52, 0))
        accent["marking_source"] = f"PVC2404_parts_fig_8_7_item_822{'A' if side < 0 else 'B'}"
        model_mark = text_label(f"PlatformModelMark_{suffix}", "ES1930M", (badge_x + 0.025, side * (fixed_lateral + 0.025), deck_y + 0.148), MAT["white"], rails, facing_rotation, 0.056)
        model_mark["marking_source"] = f"PVC2404_parts_fig_8_7_item_822{'A' if side < 0 else 'B'}"
        family_mark = text_label(f"PlatformFamilyMark_{suffix}", "MICRO-SIZED", (badge_x + 0.025, side * (fixed_lateral + 0.025), deck_y + 0.104), MAT["white"], rails, facing_rotation, 0.022)
        family_mark["marking_source"] = "official_standard_machine_gallery_V01_V02"
    bevelled_box("RearToeBoard", (0.035, 0.67, 0.25), (x_min, 0, deck_y + 0.125), MAT["jlg_orange"], rails, 0.012, "platform")
    rear_outline = text_label("PlatformJLGOutline_Rear", "JLG", (x_min - 0.022, 0, deck_y + 0.128), MAT["black"], rails, (math.pi / 2, 0, -math.pi / 2), 0.104)
    rear_outline["marking_source"] = "official_standard_machine_gallery_V01"
    rear_mark = text_label("PlatformJLGMark_Rear", "JLG", (x_min - 0.024, 0, deck_y + 0.128), MAT["white"], rails, (math.pi / 2, 0, -math.pi / 2), 0.090)
    rear_mark["marking_source"] = "PVC2404_parts_fig_8_7_item_825A"
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

    # PVC 2404 parts Fig. 4-14/4-15 and operation Fig. 11 define a removable
    # controller module nested inside a deep molded carrier. The control faces
    # inboard so the operator can reach it while the carrier remains outside the
    # working envelope. Dimensions here are visually reconciled, not service data.
    controls = empty("PlatformConsole", parent=platform)
    controls["component"] = "controls"
    controls["authority"] = "PVC2404_parts_fig_4_14_4_15_operation_fig_11_visual_reconstruction"

    carrier = empty("PlatformControlCarrier", parent=controls)
    carrier["component"] = "controls"
    bevelled_box("PlatformControlCarrierBack", (0.345, 0.038, 0.300), (0.32, -0.313, 1.765), MAT["black"], carrier, 0.018, "controls")
    bevelled_box("PlatformControlCarrierLeftGuard", (0.042, 0.170, 0.255), (0.158, -0.245, 1.750), MAT["black"], carrier, 0.016, "controls")
    bevelled_box("PlatformControlCarrierRightGuard", (0.042, 0.170, 0.255), (0.482, -0.245, 1.750), MAT["black"], carrier, 0.016, "controls")
    bevelled_box("PlatformControlCarrierFloor", (0.345, 0.170, 0.040), (0.32, -0.245, 1.632), MAT["black"], carrier, 0.014, "controls")
    bevelled_box("PlatformControlCarrierTopLip", (0.345, 0.080, 0.035), (0.32, -0.278, 1.905), MAT["black"], carrier, 0.012, "controls")
    bevelled_box("PlatformControlCarrierLeftWindow", (0.010, 0.080, 0.090), (0.136, -0.238, 1.770), MAT["deck"], carrier, 0.004, "controls")
    bevelled_box("PlatformControlCarrierRightWindow", (0.010, 0.080, 0.090), (0.504, -0.238, 1.770), MAT["deck"], carrier, 0.004, "controls")
    bevelled_box("PlatformControlCarrierRailHook", (0.285, 0.050, 0.040), (0.32, -0.320, 1.930), MAT["black"], carrier, 0.010, "controls")
    for side, x in (("Left", 0.19), ("Right", 0.45)):
        cylinder(f"PlatformControlCarrierMountBolt_{side}", 0.010, 0.040, (x, -0.343, 1.692), MAT["zinc"], carrier, rotation=(math.pi / 2, 0, 0), vertices=16, component="controls")
        cylinder(f"PlatformControlCarrierMountWasher_{side}", 0.017, 0.006, (x, -0.365, 1.692), MAT["zinc"], carrier, rotation=(math.pi / 2, 0, 0), vertices=20, component="controls")

    module = empty("PlatformConsoleModule", parent=controls)
    module["component"] = "controls"
    module["part_number"] = "1001274605"
    housing = bevelled_box("PlatformConsoleHousing", (0.285, 0.125, 0.215), (0.32, -0.230, 1.755), MAT["black"], module, 0.022, "controls")
    housing["part_number"] = "1001274604"
    bevelled_box("PlatformConsoleUpperShoulder", (0.270, 0.112, 0.055), (0.32, -0.225, 1.875), MAT["black"], module, 0.018, "controls", rotation=(math.radians(-8), 0, 0))
    bevelled_box("PlatformConsoleFaceBezel", (0.258, 0.020, 0.112), (0.32, -0.157, 1.795), MAT["zinc"], module, 0.009, "controls", rotation=(math.radians(-7), 0, 0))
    bevelled_box("PlatformConsoleFace", (0.244, 0.012, 0.100), (0.32, -0.144, 1.795), MAT["black"], module, 0.007, "controls", rotation=(math.radians(-7), 0, 0))
    # The upper face is a symbol-and-status legend, not a display. Recessed
    # pictograms and battery bars keep the PVC 2404 visual organization legible
    # without claiming live telemetry or inventing printed text.
    bevelled_box("PlatformConsoleDisplay", (0.190, 0.007, 0.060), (0.345, -0.136, 1.822), MAT["black"], module, 0.004, "controls", rotation=(math.radians(-7), 0, 0))
    icon_y = -0.127
    icon_xs = (0.272, 0.296, 0.320, 0.348, 0.376, 0.404, 0.428)
    # Indoor house, outdoor sun, fault cross, battery field, tilt triangle,
    # and overload platform are small molded/printed-symbol proxies.
    for suffix, a, b in (
        ("IndoorRoofL", (icon_xs[0] - 0.008, icon_y, 1.833), (icon_xs[0], icon_y, 1.841)),
        ("IndoorRoofR", (icon_xs[0], icon_y, 1.841), (icon_xs[0] + 0.008, icon_y, 1.833)),
        ("IndoorBase", (icon_xs[0] - 0.007, icon_y, 1.832), (icon_xs[0] + 0.007, icon_y, 1.832)),
        ("FaultSlashA", (icon_xs[2] - 0.007, icon_y, 1.830), (icon_xs[2] + 0.007, icon_y, 1.844)),
        ("FaultSlashB", (icon_xs[2] - 0.007, icon_y, 1.844), (icon_xs[2] + 0.007, icon_y, 1.830)),
        ("TiltBase", (icon_xs[5] - 0.008, icon_y, 1.831), (icon_xs[5] + 0.008, icon_y, 1.831)),
        ("TiltLeft", (icon_xs[5] - 0.008, icon_y, 1.831), (icon_xs[5], icon_y, 1.844)),
        ("TiltRight", (icon_xs[5], icon_y, 1.844), (icon_xs[5] + 0.008, icon_y, 1.831)),
        ("OverloadDeck", (icon_xs[6] - 0.008, icon_y, 1.837), (icon_xs[6] + 0.008, icon_y, 1.837)),
        ("OverloadArrow", (icon_xs[6], icon_y, 1.844), (icon_xs[6], icon_y, 1.831)),
    ):
        square_beam_between(f"PlatformLegend{suffix}", a, b, 0.0022, MAT["white"], module, "controls")
    cylinder("PlatformLegendOutdoorSun", 0.006, 0.005, (icon_xs[1], icon_y, 1.837), MAT["white"], module, rotation=(math.pi / 2, 0, 0), vertices=16, component="controls")
    bevelled_box("PlatformBatteryBarField", (0.046, 0.005, 0.020), (0.362, -0.129, 1.837), MAT["black"], module, 0.002, "controls", rotation=(math.radians(-7), 0, 0))
    for bar_index, (bar_x, mat) in enumerate(((0.346, MAT["red"]), (0.354, MAT["yellow"]), (0.362, MAT["green"]), (0.370, MAT["green"]), (0.378, MAT["green"]))):
        bevelled_box(f"PlatformBatteryBar_{bar_index + 1}", (0.005, 0.007, 0.011 + bar_index * 0.0015), (bar_x, -0.125, 1.837), mat, module, 0.001, "controls")
    for name, x, z, mat in (
        ("PlatformIndoorCapacityIndicator", icon_xs[0], 1.815, MAT["green"]),
        ("PlatformOutdoorCapacityIndicator", icon_xs[1], 1.815, MAT["yellow"]),
        ("PlatformSystemFaultIndicator", icon_xs[2], 1.815, MAT["red"]),
        ("PlatformBatteryDischargeIndicatorRed", 0.350, 1.815, MAT["red"]),
        ("PlatformBatteryDischargeIndicatorGreen1", 0.362, 1.815, MAT["green"]),
        ("PlatformBatteryDischargeIndicatorGreen2", 0.374, 1.815, MAT["green"]),
        ("PlatformTiltIndicator", icon_xs[5], 1.815, MAT["red"]),
        ("PlatformOverloadIndicator", icon_xs[6], 1.815, MAT["red"]),
    ):
        cylinder(name, 0.0055, 0.009, (x, -0.126, z), mat, module, rotation=(math.pi / 2, 0, 0), vertices=16, component="controls")
    for corner, (x, z) in enumerate(((0.205, 1.755), (0.435, 1.755), (0.205, 1.835), (0.435, 1.835))):
        cylinder(f"PlatformConsoleFaceScrew_{corner + 1}", 0.005, 0.010, (x, -0.128, z), MAT["zinc"], module, rotation=(math.pi / 2, 0, 0), vertices=12, component="controls")

    # The lower bank follows operation Fig. 11: mushroom stop, lift/drive,
    # horn, indoor/outdoor mode, and drive speed. Indicator colors describe
    # lenses only; they do not assert a live machine state.
    estop = empty("PlatformEmergencyStop", parent=module)
    estop["component"] = "controls"
    cylinder("PlatformEmergencyStopBase", 0.032, 0.018, (0.222, -0.142, 1.704), MAT["black"], estop, rotation=(math.pi / 2, 0, 0), vertices=24, component="controls")
    cylinder("PlatformEmergencyStopMushroom", 0.038, 0.028, (0.222, -0.123, 1.704), MAT["red"], estop, rotation=(math.pi / 2, 0, 0), vertices=28, component="controls")
    torus("PlatformEmergencyStopCollar", 0.034, 0.005, (0.222, -0.141, 1.704), MAT["yellow"], estop, rotation=(math.pi / 2, 0, 0), component="controls")

    for name, x, z in (
        ("PlatformLiftDriveSelector", 0.302, 1.710),
        ("PlatformIndoorOutdoorSelector", 0.378, 1.710),
        ("PlatformDriveSpeedSelector", 0.442, 1.710),
    ):
        cylinder(f"{name}Bezel", 0.017, 0.014, (x, -0.140, z), MAT["zinc"], module, rotation=(math.pi / 2, 0, 0), vertices=20, component="controls")
        bevelled_box(name, (0.011, 0.018, 0.030), (x, -0.127, z + 0.007), MAT["black"], module, 0.004, "controls", rotation=(0, 0, math.radians(8)))
    cylinder("PlatformHornButtonBezel", 0.017, 0.014, (0.300, -0.140, 1.664), MAT["zinc"], module, rotation=(math.pi / 2, 0, 0), vertices=20, component="controls")
    cylinder("PlatformHornButton", 0.012, 0.020, (0.300, -0.126, 1.664), MAT["black"], module, rotation=(math.pi / 2, 0, 0), vertices=20, component="controls")
    bevelled_box("PlatformUSBPortBezel", (0.050, 0.012, 0.027), (0.408, -0.134, 1.664), MAT["zinc"], module, 0.005, "controls")
    bevelled_box("PlatformUSBPort", (0.031, 0.008, 0.011), (0.408, -0.126, 1.664), MAT["black"], module, 0.002, "controls")
    cradle = empty("PlatformPhoneCradle", parent=carrier)
    cradle["component"] = "controls"
    bevelled_box("PlatformPhoneCradleBack", (0.112, 0.015, 0.102), (0.424, -0.132, 1.605), MAT["black"], cradle, 0.008, "controls")
    bevelled_box("PlatformPhoneCradleBottom", (0.112, 0.042, 0.018), (0.424, -0.110, 1.558), MAT["black"], cradle, 0.006, "controls")
    for side, x in (("Left", 0.372), ("Right", 0.476)):
        bevelled_box(f"PlatformPhoneCradleLip{side}", (0.014, 0.040, 0.102), (x, -0.110, 1.605), MAT["black"], cradle, 0.005, "controls")

    alarm = empty("PlatformAlarm", parent=module)
    alarm["component"] = "controls"
    cylinder("PlatformAlarmBody", 0.029, 0.022, (0.475, -0.236, 1.810), MAT["black"], alarm, rotation=(0, math.pi / 2, 0), vertices=24, component="controls")
    cylinder("PlatformAlarmGrille", 0.024, 0.006, (0.489, -0.236, 1.810), MAT["zinc"], alarm, rotation=(0, math.pi / 2, 0), vertices=24, component="controls")
    for offset_y, offset_z in ((0, 0), (-0.010, 0), (0.010, 0), (0, -0.010), (0, 0.010)):
        cylinder(f"PlatformAlarmPort_{offset_y}_{offset_z}", 0.0035, 0.008, (0.494, -0.236 + offset_y, 1.810 + offset_z), MAT["black"], alarm, rotation=(0, math.pi / 2, 0), vertices=10, component="controls")

    joystick = empty("PlatformJoystick", parent=module)
    joystick["component"] = "controls"
    joystick["part_number"] = "1600402"
    bevelled_box("PlatformJoystickMountPlate", (0.118, 0.105, 0.020), (0.238, -0.222, 1.892), MAT["black"], joystick, 0.010, "controls")
    for ring, (major, minor, z) in enumerate(((0.040, 0.009, 1.904), (0.035, 0.008, 1.914), (0.030, 0.007, 1.924))):
        torus(f"PlatformJoystickBootRing_{ring + 1}", major, minor, (0.238, -0.222, z), MAT["rubber"], joystick, component="controls")
    cylinder("PlatformJoystickShaft", 0.013, 0.066, (0.238, -0.222, 1.940), MAT["zinc"], joystick, vertices=18, component="controls")
    cylinder("PlatformJoystickGrip", 0.026, 0.082, (0.238, -0.222, 1.930), MAT["rubber"], joystick, vertices=24, component="controls")
    bevelled_box("PlatformJoystickTopRocker", (0.034, 0.023, 0.012), (0.238, -0.222, 1.972), MAT["zinc"], joystick, 0.005, "controls")
    bevelled_box("PlatformJoystickTrigger", (0.022, 0.014, 0.043), (0.238, -0.187, 1.938), MAT["black"], joystick, 0.005, "controls", rotation=(math.radians(-12), 0, 0))
    for corner, (x, y) in enumerate(((0.195, -0.255), (0.281, -0.255), (0.195, -0.189), (0.281, -0.189))):
        cylinder(f"PlatformJoystickMountScrew_{corner + 1}", 0.0045, 0.010, (x, y, 1.905), MAT["zinc"], joystick, vertices=12, component="controls")

    cable = empty("PlatformConsoleCable", parent=controls)
    cable["component"] = "controls"
    cylinder("PlatformConsoleCableConnector", 0.021, 0.040, (0.500, -0.273, 1.688), MAT["zinc"], cable, rotation=(0, math.pi / 2, 0), vertices=20, component="controls")
    # Standard-machine evidence supports the removable box harness, but JLG
    # lists the coiled platform-control cable as an option. Keep this frozen
    # configuration to a short relaxed lead with reconstructed routing.
    beam_between("PlatformConsoleCableLead", (0.520, -0.273, 1.688), (0.548, -0.300, 1.640), 0.009, MAT["rubber"], cable, "controls", vertices=12)
    beam_between("PlatformConsoleCableDrop", (0.548, -0.300, 1.640), (0.525, -0.310, 1.575), 0.009, MAT["rubber"], cable, "controls", vertices=12)

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
