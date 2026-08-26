#!/usr/bin/env python3
"""Validate ES1930M GLB identity, hierarchy, pivots, bounds, and mesh budget."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = ROOT / "assets/models/es1930m.glb"
BLEND_PATH = ROOT / "source/blender/es1930m-showcase-v1.0.blend"
CONFIG_PATH = ROOT / "machines/es1930m/es1930m.configuration.json"
MECHANISM_PATH = ROOT / "machines/es1930m/mechanism.json"
VERSION_PATH = ROOT / "machines/es1930m/version.js"
CONFIGURATION_ID = "ES1930M-PVC2404-US-STD-FR-FLA130-NM"
TRIANGLE_BUDGET = 60_000
HIT_VOLUMES = {"Chassis_Hit", "Scissor_Hit", "Platform_Hit", "Steering_Hit"}
REQUIRED_MECHANISM_NODES = {
    "LowerSlideBlock_RIGHT_PLANE", "LowerSlideBlock_LEFT_PLANE",
    "UpperSlideBlock_RIGHT_PLANE", "UpperSlideBlock_LEFT_PLANE",
    "KickerArmWeb_SCISSOR_CYLINDER", "KickerArmWeb_CYLINDER_ROLLER", "KickerArmWeb_ROLLER_SCISSOR",
    "PIVOT_KICKER_TO_SCISSOR", "PIVOT_KICKER_ROLLER", "PIVOT_LIFT_CYLINDER_UPPER",
    "TopRail_-1", "TopRail_1", "MidRail_-1", "MidRail_1",
    "ExtensionTopRail_-1", "ExtensionTopRail_1", "ExtensionMidRail_-1", "ExtensionMidRail_1",
    "MainToeBoard_-1", "MainToeBoard_1", "ExtensionToeBoard_-1", "ExtensionToeBoard_1",
    "ExtensionFrontToeBoard",
    "FrontWheelRoll_R", "FrontWheelRoll_L", "RearWheelRoll_R", "RearWheelRoll_L",
}
REQUIRED_CONTROL_NODES = {
    "PlatformControlCarrier", "PlatformControlCarrierBack", "PlatformControlCarrierLeftGuard",
    "PlatformControlCarrierRightGuard", "PlatformControlCarrierFloor", "PlatformControlCarrierTopLip",
    "PlatformControlCarrierRailHook", "PlatformControlModule", "PlatformControlHousing",
    "PlatformControlFaceBezel", "PlatformControlFace", "PlatformIndicatorLegendPanel", "PlatformBatteryBarField",
    "PlatformIndoorCapacityIndicator", "PlatformOutdoorCapacityIndicator", "PlatformSystemFaultIndicator",
    "PlatformBatteryDischargeIndicatorRed", "PlatformBatteryDischargeIndicatorGreen1",
    "PlatformBatteryDischargeIndicatorGreen2", "PlatformTiltIndicator", "PlatformOverloadIndicator",
    "PlatformEmergencyStop", "PlatformEmergencyStopBase", "PlatformEmergencyStopMushroom",
    "PlatformEmergencyStopCollar", "PlatformLiftDriveSelector", "PlatformHornButton",
    "PlatformIndoorOutdoorSelector", "PlatformDriveSpeedSelector", "PlatformUSBPort",
    "PlatformAlarm", "PlatformAlarmBody", "PlatformAlarmGrille", "PlatformJoystick",
    "PlatformJoystickMountPlate", "PlatformJoystickBootRing_1", "PlatformJoystickBootRing_2",
    "PlatformJoystickBootRing_3", "PlatformJoystickGrip", "PlatformJoystickTopRocker",
    "PlatformJoystickTrigger", "PlatformControlCable", "PlatformControlCableConnector",
    "PlatformControlCableLead", "PlatformControlCableDrop", "PlatformPhoneCradle",
    "PlatformPhoneCradleBack", "PlatformPhoneCradleBottom", "PlatformPhoneCradleLipLeft", "PlatformPhoneCradleLipRight",
}
REQUIRED_EDGES = {
    "Chassis": "ES1930M_ROOT",
    "ScissorAssembly": "ES1930M_ROOT",
    "LiftCylinder": "ES1930M_ROOT",
    "PlatformAssembly": "ES1930M_ROOT",
    "FrontSteerAssembly": "Chassis",
    "PotholeProtection": "Chassis",
    "BatteryCompartments": "Chassis",
    "GroundControls": "Chassis",
    "ExtensionDeck": "PlatformAssembly",
    "FixedRails": "PlatformAssembly",
    "ExtensionRails": "ExtensionDeck",
    "SelfClosingGate": "ExtensionDeck",
    "PlatformControls": "PlatformAssembly",
    "PlatformControlCarrier": "PlatformControls",
    "PlatformControlModule": "PlatformControls",
    "PlatformEmergencyStop": "PlatformControlModule",
    "PlatformAlarm": "PlatformControlModule",
    "PlatformJoystick": "PlatformControlModule",
    "PlatformControlCable": "PlatformControls",
    "PlatformPhoneCradle": "PlatformControlCarrier",
    "FrontWheelRoll_R": "SteerSpindle_R",
    "FrontWheelRoll_L": "SteerSpindle_L",
    "RearWheelRoll_R": "Chassis",
    "RearWheelRoll_L": "Chassis",
    "TopRail_-1": "FixedRails",
    "TopRail_1": "FixedRails",
    "MidRail_-1": "FixedRails",
    "MidRail_1": "FixedRails",
    "MainToeBoard_-1": "FixedRails",
    "MainToeBoard_1": "FixedRails",
    "ExtensionTopRail_-1": "ExtensionRails",
    "ExtensionTopRail_1": "ExtensionRails",
    "ExtensionMidRail_-1": "ExtensionRails",
    "ExtensionMidRail_1": "ExtensionRails",
    "ExtensionToeBoard_-1": "ExtensionDeck",
    "ExtensionToeBoard_1": "ExtensionDeck",
    "ExtensionFrontToeBoard": "ExtensionDeck",
    **{f"Level{index:02d}": "ScissorAssembly" for index in range(1, 6)},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_glb(path: Path):
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid GLB 2.0 header")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise RuntimeError("First GLB chunk is not JSON")
    document = json.loads(data[20:20 + json_length].decode("utf-8"))
    binary_offset = 20 + json_length
    binary_length, binary_type = struct.unpack_from("<II", data, binary_offset)
    if binary_type != 0x004E4942:
        raise RuntimeError("Second GLB chunk is not BIN")
    return document, data[binary_offset + 8:binary_offset + 8 + binary_length]


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qrot(q, vector):
    x, y, z, w = q
    vx, vy, vz = vector
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


def index_nodes(nodes):
    by_name = {}
    parents = {}
    for index, node in enumerate(nodes):
        if name := node.get("name"):
            if name in by_name:
                raise RuntimeError(f"Duplicate node name: {name}")
            by_name[name] = index
        for child in node.get("children", []):
            if child in parents:
                raise RuntimeError(f"Node {nodes[child].get('name')} has multiple parents")
            parents[child] = index
    return by_name, parents


def world_trs(nodes, parents, index):
    chain = []
    current = index
    while current is not None:
        chain.append(nodes[current])
        current = parents.get(current)
    translation = (0.0, 0.0, 0.0)
    rotation = (0.0, 0.0, 0.0, 1.0)
    scale = (1.0, 1.0, 1.0)
    for node in reversed(chain):
        local_t = tuple(node.get("translation") or (0.0, 0.0, 0.0))
        local_r = tuple(node.get("rotation") or (0.0, 0.0, 0.0, 1.0))
        local_s = tuple(node.get("scale") or (1.0, 1.0, 1.0))
        shifted = qrot(rotation, tuple(scale[axis] * local_t[axis] for axis in range(3)))
        translation = tuple(translation[axis] + shifted[axis] for axis in range(3))
        rotation = qmul(rotation, local_r)
        scale = tuple(scale[axis] * local_s[axis] for axis in range(3))
    return translation, rotation, scale


def positions(document, blob, accessor_index):
    accessor = document["accessors"][accessor_index]
    if accessor.get("type") != "VEC3" or accessor.get("componentType") != 5126:
        raise RuntimeError("POSITION must be float VEC3")
    view = document["bufferViews"][accessor["bufferView"]]
    stride = view.get("byteStride", 12)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return [struct.unpack_from("<fff", blob, offset + index * stride) for index in range(accessor["count"])]


def visible_bounds(document, blob, nodes, parents):
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    for node_index, node in enumerate(nodes):
        if "mesh" not in node or (node.get("extras") or {}).get("is_hit_volume"):
            continue
        translation, rotation, scale = world_trs(nodes, parents, node_index)
        mesh = document["meshes"][node["mesh"]]
        for primitive in mesh["primitives"]:
            for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
                transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
                point = tuple(translation[axis] + transformed[axis] for axis in range(3))
                for axis in range(3):
                    minimum[axis] = min(minimum[axis], point[axis])
                    maximum[axis] = max(maximum[axis], point[axis])
    return minimum, maximum


def node_bounds(document, blob, nodes, parents, index):
    node = nodes[index]
    if "mesh" not in node:
        raise RuntimeError(f"Node has no mesh: {node.get('name')}")
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    translation, rotation, scale = world_trs(nodes, parents, index)
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
            transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
            point = tuple(translation[axis] + transformed[axis] for axis in range(3))
            for axis in range(3):
                minimum[axis] = min(minimum[axis], point[axis])
                maximum[axis] = max(maximum[axis], point[axis])
    return minimum, maximum


def descends_from(index, ancestor, parents):
    current = index
    while current in parents:
        current = parents[current]
        if current == ancestor:
            return True
    return False


def main():
    config = json.loads(CONFIG_PATH.read_text())
    mechanism = json.loads(MECHANISM_PATH.read_text())
    if {config.get("configuration_id"), mechanism.get("configuration_id")} != {CONFIGURATION_ID}:
        raise RuntimeError("Configuration identity drift")
    document, blob = load_glb(GLB_PATH)
    asset_sha256 = sha256(GLB_PATH)
    version_text = VERSION_PATH.read_text()
    match = re.search(r'ES1930M_ASSET_SHA256\s*=\s*"([0-9a-f]{64})"', version_text)
    if not match or match.group(1) != asset_sha256:
        raise RuntimeError("ES1930M version cache identity does not match GLB")
    nodes = document.get("nodes") or []
    by_name, parents = index_nodes(nodes)
    if "ES1930M_ROOT" not in by_name or by_name["ES1930M_ROOT"] in parents:
        raise RuntimeError("Missing or parented ES1930M_ROOT")
    root_extras = nodes[by_name["ES1930M_ROOT"]].get("extras") or {}
    if (
        root_extras.get("configuration_id") != CONFIGURATION_ID
        or root_extras.get("pvc") != "2404"
        or root_extras.get("release") != "1.0.3"
    ):
        raise RuntimeError("GLB root evidence identity mismatch")
    if missing := sorted(REQUIRED_MECHANISM_NODES - by_name.keys()):
        raise RuntimeError(f"Missing mechanism nodes: {missing}")
    if missing := sorted(REQUIRED_CONTROL_NODES - by_name.keys()):
        raise RuntimeError(f"Missing platform control nodes: {missing}")
    for child, expected_parent in REQUIRED_EDGES.items():
        if child not in by_name:
            raise RuntimeError(f"Missing required node: {child}")
        actual_parent = nodes[parents[by_name[child]]].get("name") if by_name[child] in parents else None
        if actual_parent != expected_parent:
            raise RuntimeError(f"Parent mismatch for {child}: {actual_parent} != {expected_parent}")

    link_groups = []
    pivot_markers = []
    for name, index in by_name.items():
        extras = nodes[index].get("extras") or {}
        if extras.get("pin_center_length_m") is not None:
            link_groups.append(name)
            if abs(extras["pin_center_length_m"] - mechanism["solver"]["arm_pin_center_length_m"]) > 1e-6:
                raise RuntimeError(f"Authored link length drift: {name}")
        if extras.get("is_pivot_marker"):
            pivot_markers.append(name)
    if len(link_groups) != 20:
        raise RuntimeError(f"Expected 20 explicit scissor link groups, found {len(link_groups)}")
    if len(pivot_markers) < 68:
        raise RuntimeError(f"Expected at least 68 pivot markers, found {len(pivot_markers)}")
    controls_root = by_name["PlatformControls"]
    control_meshes = [
        name for name, index in by_name.items()
        if "mesh" in nodes[index]
        and descends_from(index, controls_root, parents)
        and (nodes[index].get("extras") or {}).get("component") == "controls"
    ]
    if len(control_meshes) < 62:
        raise RuntimeError(f"Platform control detail regression: expected at least 62 tagged meshes, found {len(control_meshes)}")
    if any(name.startswith("PlatformControlCableCoil") for name in by_name):
        raise RuntimeError("Standard frozen configuration must not include the optional coiled control cable")
    for name in HIT_VOLUMES:
        if name not in by_name or not (nodes[by_name[name]].get("extras") or {}).get("is_hit_volume"):
            raise RuntimeError(f"Missing declared interaction volume: {name}")

    rail_contract = mechanism["deck_extension"]
    travel = rail_contract["travel_m"]
    minimum_required_overlap = rail_contract["minimum_deployed_overlap_m"]
    minimum_lateral_clearance = rail_contract["minimum_nested_lateral_clearance_m"]
    continuity_samples = (0.0, 0.5, 1.0)
    guard_pairs = []
    for side in (-1, 1):
        for fixed_name, moving_name in (
            (f"TopRail_{side}", f"ExtensionTopRail_{side}"),
            (f"MidRail_{side}", f"ExtensionMidRail_{side}"),
            (f"MainToeBoard_{side}", f"ExtensionToeBoard_{side}"),
        ):
            fixed_bounds = node_bounds(document, blob, nodes, parents, by_name[fixed_name])
            moving_bounds = node_bounds(document, blob, nodes, parents, by_name[moving_name])
            fixed_front = fixed_bounds[1][0]
            moving_rear = moving_bounds[0][0]
            fixed_lateral = abs((fixed_bounds[0][2] + fixed_bounds[1][2]) / 2)
            moving_lateral = abs((moving_bounds[0][2] + moving_bounds[1][2]) / 2)
            if moving_lateral >= fixed_lateral - 0.010:
                raise RuntimeError(f"Moving guard is not nested inboard: {moving_name}")
            lateral_clearance = max(
                fixed_bounds[0][2] - moving_bounds[1][2],
                moving_bounds[0][2] - fixed_bounds[1][2],
                0.0,
            )
            if lateral_clearance + 1e-6 < minimum_lateral_clearance:
                raise RuntimeError(f"Guard solids intersect laterally: {fixed_name}/{moving_name} clearance={lateral_clearance}")
            overlaps = [fixed_front - (moving_rear + travel * sample) for sample in continuity_samples]
            if min(overlaps) + 1e-6 < minimum_required_overlap:
                raise RuntimeError(f"Guard continuity opens at extension: {fixed_name}/{moving_name} overlaps={overlaps}")
            guard_pairs.append({"fixed": fixed_name, "moving": moving_name, "overlap_m": overlaps, "lateral_clearance_m": lateral_clearance})

    triangles = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                raise RuntimeError("Only triangle primitives are admitted")
            accessor = document["accessors"][primitive["indices"]]
            triangles += accessor["count"] // 3
    if triangles > TRIANGLE_BUDGET:
        raise RuntimeError(f"Triangle budget exceeded: {triangles}")

    minimum, maximum = visible_bounds(document, blob, nodes, parents)
    envelope = [maximum[axis] - minimum[axis] for axis in range(3)]
    expected = [1.48, 1.98, 0.76]
    for axis, (actual, target) in enumerate(zip(envelope, expected)):
        if abs(actual - target) > 0.012:
            raise RuntimeError(f"Stowed envelope axis {axis} drift: {actual:.4f} vs {target:.4f}")
    extension_root = by_name["ExtensionDeck"]
    extension_max_x = float("-inf")
    for node_index, node in enumerate(nodes):
        if "mesh" not in node or not descends_from(node_index, extension_root, parents):
            continue
        translation, rotation, scale = world_trs(nodes, parents, node_index)
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
                transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
                extension_max_x = max(extension_max_x, translation[0] + transformed[0])
    deployed_length = extension_max_x + mechanism["deck_extension"]["travel_m"] - minimum[0]
    if abs(deployed_length - config["published_dimensions_m"]["machine_length_extension_deployed"]) > 0.012:
        raise RuntimeError(f"Deployed extension envelope drift: {deployed_length:.4f} m")

    print(json.dumps({
        "status": "PASS",
        "asset": str(GLB_PATH.relative_to(ROOT)),
        "sha256": asset_sha256,
        "source_blend_sha256": sha256(BLEND_PATH),
        "configuration_id": CONFIGURATION_ID,
        "nodes": len(nodes),
        "meshes": len(document.get("meshes", [])),
        "triangles": triangles,
        "link_groups": len(link_groups),
        "pivot_markers": len(pivot_markers),
        "interaction_volumes": sorted(HIT_VOLUMES),
        "visible_bounds_min_m": minimum,
        "visible_bounds_max_m": maximum,
        "visible_envelope_xyz_m": envelope,
        "deployed_extension_envelope_m": deployed_length,
        "guard_continuity_pairs": guard_pairs,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
