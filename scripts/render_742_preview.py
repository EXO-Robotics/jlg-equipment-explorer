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
MECHANISM = json.loads((ROOT / "machines/742/mechanism.json").read_text())
VALIDATED_GLB = MECHANISM["validated_actual_glb_measurements"]


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


def proof_beam(name, start, end, radius, material):
    a, b = Vector(start), Vector(end)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=direction.length,
                                       location=(a + b) / 2)
    target = bpy.context.object
    target.name = name
    target.rotation_mode = "QUATERNION"
    target.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    target.data.materials.append(material)
    return target


def proof_sphere(name, location, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=radius,
                                        location=location)
    target = bpy.context.object
    target.name = name
    target.data.materials.append(material)
    return target


def proof_label(name, body, location, size, material):
    bpy.ops.object.text_add(location=location, rotation=(math.pi / 2, 0, 0))
    target = bpy.context.object
    target.name = name
    target.data.body = body
    target.data.align_x = "CENTER"
    target.data.align_y = "CENTER"
    target.data.size = size
    target.data.extrude = .008
    target.data.materials.append(material)
    return target


def face_labels(labels, active_camera):
    for target in labels:
        direction = active_camera.location - target.location
        target.rotation_mode = "QUATERNION"
        target.rotation_quaternion = direction.to_track_quat("Z", "Y")


def mesh_world_points(names):
    return [target.matrix_world @ vertex.co for name in names
            for target in [bpy.data.objects[name]] for vertex in target.data.vertices]


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
    bpy.context.view_layer.update()


def pose_circle_steering(amount=1.0):
    apply_solved_pose(solved_pose(0, 0, steer=amount, steer_mode="circle"))


def pose_steering(mode, amount=1.0):
    apply_solved_pose(solved_pose(0, 0, steer=amount, steer_mode=mode))


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
scene.eevee.use_taa_reprojection = False
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

# Exact exported-GLB clearance datums requested by the mechanical review. The
# endpoints use the limiting AABB faces reported by validate_742_glb.py.
clearance_mat = bpy.data.materials.new("ClearanceDatumMaterial")
clearance_mat.diffuse_color = (1.0, 0.03, 0.01, 1.0)
clearance_mat.use_nodes = True
clearance_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1.0, 0.03, 0.01, 1.0)
clearance_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.01, 0.0, 1.0)
clearance_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.5
clearance_label_mat = bpy.data.materials.new("ClearanceDatumLabelMaterial")
clearance_label_mat.diffuse_color = (1.0, 0.72, 0.08, 1.0)
clearance_label_mat.use_nodes = True
clearance_label_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1.0, 0.72, 0.08, 1.0)
clearance_label_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.45, 0.02, 1.0)
clearance_label_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.8

cab_datum = [
    proof_beam("BoomCabClearanceDatum", (0.82, 0.1050270915, 1.80), (0.82, 0.0599998349, 1.80), .006, clearance_mat),
    proof_beam("BoomCabClearanceCabTick", (0.70, 0.1050270915, 1.80), (0.94, 0.1050270915, 1.80), .006, clearance_mat),
    proof_beam("BoomCabClearanceBoomTick", (0.70, 0.0599998349, 1.80), (0.94, 0.0599998349, 1.80), .006, clearance_mat),
    proof_sphere("BoomCabClearanceCabFace", (0.82, 0.1050270915, 1.80), .010, clearance_mat),
    proof_sphere("BoomCabClearanceBoomFace", (0.82, 0.0599998349, 1.80), .010, clearance_mat),
]
cab_label = proof_label("BoomCabClearanceLabel", "45.027 mm\nBOOM / CAB HANDRAIL", (1.736, 0.532, 2.261), .027, clearance_label_mat)
camera.data.lens = 62
camera.location = (3.2, 2.4, 2.45)
point_at(camera, (0.82, 0.08, 1.80))
face_labels([cab_label], camera)
scene.render.filepath = str(OUTPUT_DIR / "742-boom-cab-clearance-datum.png")
bpy.ops.render.render(write_still=True)
for obj in [*cab_datum, cab_label]:
    obj.hide_render = True

hood_cutaway = [bpy.data.objects[name] for name in ("EngineHoodLower", "EngineHoodUpper", "EngineHoodSpine")]
for obj in hood_cutaway:
    obj.hide_render = True
hose_datum = [
    proof_beam("HoseValveClearanceDatum", (0.20, -0.48, 1.3900001336), (0.20, -0.48, 1.4240000354), .005, clearance_mat),
    proof_beam("HoseValveClearanceValveTick", (0.10, -0.48, 1.3900001336), (0.30, -0.48, 1.3900001336), .005, clearance_mat),
    proof_beam("HoseValveClearanceHoseTick", (0.10, -0.48, 1.4240000354), (0.30, -0.48, 1.4240000354), .005, clearance_mat),
    proof_sphere("HoseValveClearanceValveFace", (0.20, -0.48, 1.3900001336), .009, clearance_mat),
    proof_sphere("HoseValveClearanceHoseFace", (0.20, -0.48, 1.4240000354), .009, clearance_mat),
]
hose_label = proof_label("HoseValveClearanceLabel", "34.000 mm\nHOSE TO MAIN VALVE BANK", (0.70, -1.35, 1.67), .043, clearance_label_mat)
camera.data.lens = 64
camera.location = (1.8, -3.0, 2.05)
point_at(camera, (0.20, -0.48, 1.405))
face_labels([hose_label], camera)
scene.render.filepath = str(OUTPUT_DIR / "742-hose-valve-clearance-datum.png")
bpy.ops.render.render(write_still=True)
for obj in [*hose_datum, hose_label]:
    obj.hide_render = True
for obj in hood_cutaway:
    obj.hide_render = False

pose_circle_steering(1.0)
steering_label_mat = bpy.data.materials.new("SteeringProofLabel")
steering_label_mat.use_nodes = True
steering_label_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.05, .012, .006, 1.0)
steer_cutaway = [
    obj for obj in bpy.data.objects
    if obj.type in {"MESH", "CURVE", "FONT"} and obj.get("component") not in {None, "steering"}
]
for obj in steer_cutaway:
    obj.hide_render = True
camera.data.lens = 58
camera.location = (0.0, 0.0, 10.4)
point_at(camera, (0.0, 0.0, 0.58))
plan_proof_mat = bpy.data.materials.new("SteeringConstructionOrange")
plan_proof_mat.diffuse_color = (1.0, .12, .01, 1.0)
plan_proof_mat.use_nodes = True
plan_proof_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1.0, .02, .002, 1.0)


def steering_plan_construction(pose, include_front_icr=False, rear_neutral=False):
    overlays = []
    half_track, half_base = 2.1005 / 2, 3.42 / 2
    for corner, angle in pose["state"]["wheelAngles"].items():
        pivot = bpy.data.objects[f"SteerPivot_{corner}"].matrix_world.translation
        overlays.append(proof_sphere(f"Proof_{corner}_Pivot", pivot + Vector((0, 0, .08)),
                                     .065, plan_proof_mat))
        if abs(angle) > 1e-8 and (include_front_icr or pose["state"]["steerMode"] == "circle"):
            side = -half_track if corner.endswith("L") else half_track
            axle_x = half_base if corner.startswith("F") else -half_base
            wheelbase = 3.42 if include_front_icr else 1.71
            center_lateral = side + wheelbase / math.tan(angle) if include_front_icr else side + axle_x / math.tan(angle)
            icr = Vector((0, center_lateral, pivot.z + .08))
            overlays.append(proof_beam(f"Proof_{corner}_ICRLine", pivot + Vector((0, 0, .08)),
                                       icr, .012, plan_proof_mat))
            overlays.append(proof_sphere(f"Proof_{corner}_ICR", icr, .05, plan_proof_mat))
    if rear_neutral:
        for corner in ("RL", "RR"):
            pivot = bpy.data.objects[f"SteerPivot_{corner}"].matrix_world.translation
            overlays.append(proof_beam(f"Proof_{corner}_HeldHeading",
                                       pivot + Vector((-.30, 0, .08)),
                                       pivot + Vector((.30, 0, .08)), .015, plan_proof_mat))
    return overlays


circle_pose = solved_pose(0, 0, steer=1.0, steer_mode="circle")
circle_overlays = steering_plan_construction(circle_pose)
circle_label = proof_label("Proof_CircleMode",
                           "CIRCLE / FL 55.000 / FR 54.914 / RL -55.000 / RR -54.914 deg\nSTATIC LINKAGE / TWO ACTUAL ICR CONSTRUCTIONS\nSCRUB DIAGNOSTIC 93.466% — NOT FACTORY ACKERMANN",
                           (0, -1.45, 1.72), .076, steering_label_mat)
circle_label.rotation_mode = "XYZ"; circle_label.rotation_euler = (0, 0, 0)
scene.render.filepath = str(OUTPUT_DIR / "742-circle-steering-plan.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(circle_label, do_unlink=True)
for target in circle_overlays:
    bpy.data.objects.remove(target, do_unlink=True)
pose_steering("crab", 1.0)
crab_pose = solved_pose(0, 0, steer=1.0, steer_mode="crab")
crab_overlays = steering_plan_construction(crab_pose)
crab_label = proof_label("Proof_CrabMode",
                         "CRAB / FL 55.000 / FR 54.914 / RL 54.914 / RR 55.000 deg\nSAME STATIC LINKAGE / FULL-POSE TOE 0.086 deg / DENSE MAX 0.753 deg",
                         (0, -1.45, 1.72), .080, steering_label_mat)
crab_label.rotation_mode = "XYZ"; crab_label.rotation_euler = (0, 0, 0)
scene.render.filepath = str(OUTPUT_DIR / "742-crab-steering-plan.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(crab_label, do_unlink=True)
for target in crab_overlays:
    bpy.data.objects.remove(target, do_unlink=True)
pose_steering("front", 1.0)
front_label_mat = bpy.data.materials.new("FrontModeProofLabel")
front_label_mat.diffuse_color = (.05, .012, .006, 1.0)
front_label_mat.use_nodes = True
front_label_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.05, .012, .006, 1.0)
front_pose = solved_pose(0, 0, steer=1.0, steer_mode="front")
front_overlays = steering_plan_construction(front_pose, include_front_icr=True, rear_neutral=True)
front_label = proof_label("Proof_FrontModeBoundary",
                          "FRONT / FL 55.000 / FR 54.914 deg / REAR HELD ALIGNED\nFULL STATIC-LINKAGE TRAVEL / ACTUAL FRONT ICR CONSTRUCTIONS\nSCRUB DIAGNOSTIC 61.060% — NOT FACTORY ACKERMANN",
                          (0, -1.45, 1.72), .076, front_label_mat)
front_label.rotation_mode = "XYZ"
front_label.rotation_euler = (0, 0, 0)
scene.render.filepath = str(OUTPUT_DIR / "742-front-steering-plan.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(front_label, do_unlink=True)
for target in front_overlays:
    bpy.data.objects.remove(target, do_unlink=True)
pose_circle_steering(1.0)
steer_names = {"FrontSteerCylinderBarrel", "FrontSteerCylinderRodLeft", "FrontSteerCylinderRodRight",
               "FrontSteerBarLeft", "FrontSteerBarRight"}
steer_occluders = [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT"}
                   and obj.get("component") == "steering"
                   and (obj.name.startswith(("Tire_", "Tread_", "WheelRim", "WheelHub", "PlanetaryCap", "Lug_"))
                        or obj.name.startswith(("Rear", "SteerPivot_RL", "SteerPivot_RR"))
                        or obj.name in {"FrontAxle", "FrontDifferential", "FrontAxleTubeLeft",
                                            "FrontAxleTubeRight", "FrontPinionFlange"})]
for obj in steer_occluders:
    obj.hide_render = True
bpy.context.view_layer.update()
front_marker_objects = []
for marker_name, beam_name, endpoint_index in (
    ("Proof_FrontRackLeft", "FrontSteerCylinderRodLeft", 1),
    ("Proof_FrontRackRight", "FrontSteerCylinderRodRight", 1),
    ("Proof_FrontKnuckleLeft", "FrontSteerBarLeft", 1),
    ("Proof_FrontKnuckleRight", "FrontSteerBarRight", 1),
):
    beam = bpy.data.objects[beam_name]
    half = float(beam.get("authored_length_m")) / 2
    endpoint = beam.matrix_world @ Vector((0, 0, -half if endpoint_index == 0 else half))
    front_marker_objects.append(proof_sphere(marker_name, endpoint, .055, plan_proof_mat))
steer_center = sum((bpy.data.objects[name].matrix_world.translation for name in steer_names), Vector()) / len(steer_names)
camera.data.lens = 55
camera.location = (6.5, 0.0, 2.2)
point_at(camera, steer_center)
scene.render.filepath = str(OUTPUT_DIR / "742-front-double-ended-steer-cylinder-cutaway.png")
bpy.ops.render.render(write_still=True)
for target in front_marker_objects:
    bpy.data.objects.remove(target, do_unlink=True)
for obj in steer_occluders:
    obj.hide_render = False
rear_keep = {"RearSteerCylinderBarrel", "RearSteerCylinderRodLeft", "RearSteerCylinderRodRight",
             "RearSteerBarLeft", "RearSteerBarRight",
             "SteerPivot_RL", "SteerPivot_RR"}
rear_visual_prefixes = ()
rear_occluders = [obj for obj in bpy.data.objects if obj.type in {"MESH", "CURVE", "FONT"}
                  and obj.get("component") == "steering" and obj.name not in rear_keep
                  and not obj.name.startswith(rear_visual_prefixes)]
for obj in rear_occluders:
    obj.hide_render = True
rear_marker_objects = []
for marker_name, beam_name, endpoint_index in (
    ("Proof_RearRackLeft", "RearSteerCylinderRodLeft", 1),
    ("Proof_RearRackRight", "RearSteerCylinderRodRight", 1),
    ("Proof_RearKnuckleLeft", "RearSteerBarLeft", 1),
    ("Proof_RearKnuckleRight", "RearSteerBarRight", 1),
):
    beam = bpy.data.objects[beam_name]
    half = float(beam.get("authored_length_m")) / 2
    endpoint = beam.matrix_world @ Vector((0, 0, -half if endpoint_index == 0 else half))
    rear_marker_objects.append(proof_sphere(marker_name, endpoint, .055, plan_proof_mat))
rear_center = (bpy.data.objects["SteerPivot_RL"].matrix_world.translation +
               bpy.data.objects["SteerPivot_RR"].matrix_world.translation) / 2
camera.data.lens = 58
camera.location = rear_center + Vector((0.0, -.45, 7.2))
point_at(camera, rear_center + Vector((0, -.45, 0)))
rear_label = proof_label("Proof_RearSteering",
                         "REAR AXLE / FIXED THROUGH-ROD RACK\nTWO RIGID TIE BARS\nFOUR VISIBLE JOINTS",
                         rear_center + Vector((0, -1.30, 1.55)), .050, steering_label_mat)
rear_label.rotation_mode = "XYZ"; rear_label.rotation_euler = (0, 0, 0)
scene.render.filepath = str(OUTPUT_DIR / "742-rear-steering-linkage.png")
bpy.ops.render.render(write_still=True)
bpy.data.objects.remove(rear_label, do_unlink=True)
for target in rear_marker_objects:
    bpy.data.objects.remove(target, do_unlink=True)
for obj in rear_occluders:
    obj.hide_render = False
for obj in steer_cutaway:
    obj.hide_render = False
pose_circle_steering(0.0)

cutaway_pose = solved_pose(0.61, 0.68)
apply_solved_pose(cutaway_pose)
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
chain_context_mat = bpy.data.materials.new("ChainContextOrange")
chain_context_mat.diffuse_color = (1.0, .16, .02, 1.0)
chain_context_mat.use_nodes = True
chain_bsdf = chain_context_mat.node_tree.nodes.get("Principled BSDF")
chain_bsdf.inputs["Base Color"].default_value = (1.0, .04, .005, 1.0)
if "Emission Color" in chain_bsdf.inputs:
    chain_bsdf.inputs["Emission Color"].default_value = (1.0, .015, .002, 1.0)
    chain_bsdf.inputs["Emission Strength"].default_value = 3.0
chain_context = []
for index, (label, beam_name) in enumerate((("FIXED ADJUSTER / FIRST SECTION", "RetractChain_C"),
                                            ("MOVING ATTACHMENT / THIRD SECTION", "RetractChain_C_Moving"))):
    beam_obj = bpy.data.objects[beam_name]
    half_authored = float(beam_obj.get("authored_length_m")) / 2
    endpoint = beam_obj.matrix_world @ Vector((0, 0, -half_authored if index == 0 else half_authored))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=.075, location=endpoint)
    marker = bpy.context.object
    marker.data.materials.append(chain_context_mat)
    chain_context.append(marker)
    label_location = chain_center + Vector((-.55 if index == 0 else .55, -.35, -.38 if index == 0 else .38))
    chain_context.append(proof_beam(f"Proof_{beam_name}_Leader", endpoint, label_location,
                                    .012, chain_context_mat))
    chain_context.append(proof_label(f"Proof_{beam_name}_Anchor", label,
                                     label_location, .12, chain_context_mat))
face_labels([obj for obj in chain_context if obj.type == "FONT"], camera)
scene.render.filepath = str(OUTPUT_DIR / "742-retract-chain-routing-cutaway.png")
bpy.ops.render.render(write_still=True)
for obj in chain_context:
    bpy.data.objects.remove(obj, do_unlink=True)
for obj in chain_cutaway:
    obj.hide_render = False
pose_mechanisms(1.0, 1.0)
datum_mat = bpy.data.materials.new("ProofDatumOrange")
datum_mat.diffuse_color = (1.0, 0.12, 0.015, 1.0)
datum_mat.use_nodes = True
datum_bsdf = datum_mat.node_tree.nodes.get("Principled BSDF")
datum_bsdf.inputs["Base Color"].default_value = (1.0, 0.015, 0.004, 1.0)
datum_bsdf.inputs["Roughness"].default_value = 0.24
if "Emission Color" in datum_bsdf.inputs:
    datum_bsdf.inputs["Emission Color"].default_value = (1.0, 0.008, 0.002, 1.0)
    datum_bsdf.inputs["Emission Strength"].default_value = 2.0
label_mat = bpy.data.materials.new("ProofLabelWhite")
label_mat.diffuse_color = (1.0, .96, .88, 1.0)
label_mat.use_nodes = True
label_bsdf = label_mat.node_tree.nodes.get("Principled BSDF")
label_bsdf.inputs["Base Color"].default_value = (1.0, .96, .88, 1.0)
if "Emission Color" in label_bsdf.inputs:
    label_bsdf.inputs["Emission Color"].default_value = (1.0, .78, .45, 1.0)
    label_bsdf.inputs["Emission Strength"].default_value = 2.0
max_lift_forks = mesh_world_points(("ForkL", "ForkR"))
max_lift_surface = VALIDATED_GLB["maximum_lift_fork_load_surface_m"]
level_datum = proof_beam("Proof_MaxLiftForkLevel", (2.2, -1.1, max_lift_surface),
                         (5.2, -1.1, max_lift_surface), .022, datum_mat)
lift_ground_datum = proof_beam("Proof_MaxLiftGround", (2.2, -1.1, 0),
                               (5.2, -1.1, 0), .022, datum_mat)
lift_dimension = proof_beam("Proof_MaxLiftDimension", (5.05, -1.1, 0),
                            (5.05, -1.1, max_lift_surface), .018, datum_mat)
lift_labels = [
    proof_label("Proof_MaxLiftValue", f"VALIDATED POSED-GLB FORK LOAD SURFACE  {max_lift_surface:.6f} m",
                (3.55, -1.12, max_lift_surface + .38), .24, label_mat),
    proof_label("Proof_MaxLiftGroundLabel", "GROUND DATUM  0.000 m",
                (4.25, -1.12, .68), .22, label_mat),
]
bpy.ops.object.light_add(type="AREA", location=(8.0, -5.0, 16.0))
max_lift_key = bpy.context.object
max_lift_key.name = "MaxLiftKey"
max_lift_key.data.energy = 1700
max_lift_key.data.size = 5.0
point_at(max_lift_key, (3.3, 0, 12.5))
scene.render.resolution_x = 1000
scene.render.resolution_y = 1200
camera.data.lens = 52
camera.location = (2.0, -28.0, 13.5)
point_at(camera, (2.0, 0, 7.0))
face_labels(lift_labels, camera)
scene.render.filepath = str(OUTPUT_DIR / "742-maximum-lift-level-forks.png")
bpy.ops.render.render(write_still=True)
level_datum.hide_render = True
lift_ground_datum.hide_render = True
lift_dimension.hide_render = True
for target in lift_labels:
    target.hide_render = True
fork_cutaway = [target for target in bpy.data.objects
                if target.type in {"MESH", "CURVE", "FONT"} and target.get("component") == "carriage"
                and not target.name.startswith(("Fork",))]
for target in fork_cutaway:
    target.hide_render = True
fork_center = sum(max_lift_forks, Vector()) / len(max_lift_forks)
fork_x_min = min(point.x for point in max_lift_forks)
fork_x_max = max(point.x for point in max_lift_forks)
fork_y_camera_side = min(point.y for point in max_lift_forks)
close_datum = [
    proof_beam("Proof_MaxLiftCloseSurface",
               (fork_x_min, fork_y_camera_side, max_lift_surface),
               (fork_x_max, fork_y_camera_side, max_lift_surface), .018, datum_mat),
    proof_beam("Proof_MaxLiftCloseHeelTick",
               (fork_x_min, fork_y_camera_side, max_lift_surface - .12),
               (fork_x_min, fork_y_camera_side, max_lift_surface + .12), .018, datum_mat),
    proof_beam("Proof_MaxLiftCloseTipTick",
               (fork_x_max, fork_y_camera_side, max_lift_surface - .12),
               (fork_x_max, fork_y_camera_side, max_lift_surface + .12), .018, datum_mat),
    proof_sphere("Proof_MaxLiftCloseHeelContact",
                 (fork_x_min, fork_y_camera_side, max_lift_surface), .035, datum_mat),
    proof_sphere("Proof_MaxLiftCloseTipContact",
                 (fork_x_max, fork_y_camera_side, max_lift_surface), .035, datum_mat),
    proof_label("Proof_MaxLiftCloseLabel",
                f"RED LINE = VALIDATED POSED-GLB FORK TOP / LOAD SURFACE\n{max_lift_surface:.6f} m ABOVE GROUND DATUM",
                ((fork_x_min + fork_x_max) / 2, fork_y_camera_side - .05,
                 max_lift_surface + .42), .105, label_mat),
]
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
camera.data.lens = 72
camera.location = fork_center + Vector((4.4, -7.2, 2.7))
point_at(camera, fork_center + Vector((0, 0, .16)))
face_labels([target for target in close_datum if target.type == "FONT"], camera)
scene.render.filepath = str(OUTPUT_DIR / "742-maximum-lift-forks-close.png")
bpy.ops.render.render(write_still=True)
for target in close_datum:
    bpy.data.objects.remove(target, do_unlink=True)
for target in fork_cutaway:
    target.hide_render = False
max_lift_key.hide_render = True
pose_mechanisms(3 / 69, 1.0)
bpy.context.view_layer.update()
front_tire_names = [target.name for target in bpy.data.objects
                    if target.type == "MESH" and target.name.startswith(("Tire_FL", "Tire_FR", "Tread_FL_", "Tread_FR_"))]
front_tire_plane = VALIDATED_GLB["maximum_reach_front_tire_tread_plane_x_m"]
reach_forks = mesh_world_points(("ForkL", "ForkR"))
load_center = VALIDATED_GLB["maximum_reach_24in_load_center_x_m"]
fork_heel = load_center - .6096
datum_objects = [
    proof_beam("Proof_FrontTirePlane", (front_tire_plane, -1.45, 0),
               (front_tire_plane, -1.45, 2.45), .018, datum_mat),
    proof_beam("Proof_LoadCenterPlane", (load_center, -1.45, 0),
               (load_center, -1.45, 2.45), .018, datum_mat),
    proof_beam("Proof_ReachDimension", (front_tire_plane, -1.45, 2.25),
               (load_center, -1.45, 2.25), .018, datum_mat),
    proof_beam("Proof_LoadCenterCross", (load_center - .18, -1.45, 1.04),
               (load_center + .18, -1.45, 1.04), .024, datum_mat),
    proof_beam("Proof_24InLoadCenter", (fork_heel, -1.45, 1.18),
               (load_center, -1.45, 1.18), .018, datum_mat),
    proof_label("Proof_FrontTirePlaneLabel", "FRONT TIRE TREAD PLANE",
                (front_tire_plane, -1.47, .34), .20, label_mat),
    proof_label("Proof_LoadCenterLabel", "24 in / 0.6096 m LOAD CENTER",
                ((fork_heel + load_center) / 2, -1.47, 1.46), .20, label_mat),
    proof_label("Proof_ReachValue", f"SELECTED RECONSTRUCTED 3 deg POSE   {VALIDATED_GLB['maximum_reach_m']:.6f} m REACH",
                ((front_tire_plane + load_center) / 2, -1.47, 2.92), .24, label_mat),
]
scene.render.resolution_x = 1400
scene.render.resolution_y = 800
camera.data.lens = 52
camera.location = (4.8, -30.0, 5.6)
point_at(camera, (4.8, 0, 1.45))
face_labels([target for target in datum_objects if target.type == "FONT"], camera)
scene.render.filepath = str(OUTPUT_DIR / "742-maximum-reach-24in-load-center.png")
bpy.ops.render.render(write_still=True)
for target in datum_objects:
    target.hide_render = True

# Blender 5.1 produces byte-variable PNG containers for identical Eevee pixels.
# macOS ImageIO's decode/re-encode removes that container-only variance while
# preserving the rendered RGBA pixels, so the review allowlist can bind stable
# bytes rather than a single-session encoder artifact.
owned_render_names = (
    "742-boom-pivot-angle-sensor.png",
    "742-boom-cab-clearance-datum.png",
    "742-cab-close.png",
    "742-circle-steering-plan.png",
    "742-crab-steering-plan.png",
    "742-front-steering-plan.png",
    "742-maximum-lift-forks-close.png",
    "742-maximum-lift-level-forks.png",
    "742-maximum-reach-24in-load-center.png",
    "742-hose-valve-clearance-datum.png",
    "742-rear-steering-linkage.png",
    "742-retract-chain-routing-cutaway.png",
    "742-front-double-ended-steer-cylinder-cutaway.png",
    "742-stowed-front-left.png",
)
for render_name in owned_render_names:
    render_path = OUTPUT_DIR / render_name
    normalized_path = render_path.with_name(f"{render_path.stem}.normalized.png")
    subprocess.run(("sips", "-s", "format", "png", str(render_path),
                    "--out", str(normalized_path)), check=True,
                   capture_output=True, text=True)
    normalized_path.replace(render_path)
print(OUTPUT_DIR)
