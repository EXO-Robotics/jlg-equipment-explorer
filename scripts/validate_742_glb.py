#!/usr/bin/env python3
"""Validate the owned 742 GLB identity, hierarchy, geometry budget, and envelope."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb, positions, qrot, visible_bounds, world_trs


ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "assets/models/742.glb"
BLEND = ROOT / "source/blender/742-showcase-v1.0.blend"
CONFIG_PATH = ROOT / "machines/742/742.configuration.json"
MECHANISM_PATH = ROOT / "machines/742/mechanism.json"
CLEARANCE_OBSTACLES_PATH = ROOT / "machines/742/clearance-obstacles.json"
EVIDENCE_PATH = ROOT / "docs/research/742/MECHANISM_EVIDENCE.json"
VERSION = ROOT / "machines/742/version.js"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
TRIANGLE_BUDGET = 60000
REQUIRED_EDGES = {
    "GroundRunningGear":"742_ROOT", "FrameLevelPivot":"742_ROOT", "Chassis":"FrameLevelPivot",
    "OpenCab":"Chassis", "BoomLiftPivot":"FrameLevelPivot", "BoomBase":"BoomLiftPivot",
    "BoomMid":"BoomBase", "BoomFly":"BoomMid", "CarriageTiltPivot":"BoomFly", "Carriage":"CarriageTiltPivot",
    "SteerPivot_FL":"GroundRunningGear", "SteerPivot_FR":"GroundRunningGear", "SteerPivot_RL":"GroundRunningGear", "SteerPivot_RR":"GroundRunningGear",
    "Chassis_Hit":"FrameLevelPivot", "Cab_Hit":"FrameLevelPivot", "Boom_Hit":"BoomBase", "Carriage_Hit":"Carriage",
    "Steering_Hit":"GroundRunningGear", "Hydraulics_Hit":"FrameLevelPivot"
}
REQUIRED_MECHANICAL_DETAIL = {
    "LiftCylinderBarrel", "LiftCylinderRod", "LiftCylinderBasePin", "LiftCylinderRodPin",
    "TelescopeCylinderBarrel", "TelescopeCylinderRod", "CompensationCylinderBarrel", "CompensationCylinderRod",
    "CarriageTiltCylinderBarrel", "CarriageTiltCylinderRod", "CarriageTiltLink",
    "FrameLevelCylinderBarrel", "FrameLevelCylinderRod", "RearAxleStabilizerBarrel", "RearAxleStabilizerRod",
    "FrontSteerCylinder", "FrontSteerCylinderBarrel", "FrontSteerCylinderRodLeft", "FrontSteerCylinderRodRight",
    "RearSteerCylinder", "RearSteerCylinderBarrel", "RearSteerCylinderRodLeft", "RearSteerCylinderRodRight",
    "FrontSteerBarLeft", "FrontSteerBarRight", "RearSteerBarLeft", "RearSteerBarRight",
    *{name for prefix in ("ExtendChain_L", "ExtendChain_R", "RetractChain_C")
      for name in ([prefix, f"{prefix}_Wrap"] + [f"{prefix}_Wrap_{index}" for index in range(1, 8)] + [f"{prefix}_Moving"])},
    "BoomSheave_L", "BoomSheave_R", "RetractSheave_C",
    "BoomAngleSensorBracket", "BoomAngleSensorBody", "BoomAngleSensorCrank", "BoomAngleSensorLink",
    "BoomAngleSensorFrameJoint", "BoomAngleSensorCrankJoint", "BoomAngleSensorBoomJoint",
    "BoomRigidTube_0", "BoomRigidTube_1", "BoomRigidTube_2", "ForkL", "ForkR",
}
STOWED_BOOM_ENVELOPE_NODES = {
    "BaseBoomWeldment", "BaseBoomLowerWear", "MidBoomWeldment",
    "MidBoomTopPlate", "FlyBoomWeldment",
}
STOWED_SERVICE_ENVELOPE_PREFIXES = ("BoomHose_", "RetractChain_", "ExtendChain_")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def node_world_bounds(document, blob, nodes, parents, node_index):
    node = nodes[node_index]
    if "mesh" not in node:
        raise RuntimeError(f"Cannot measure non-mesh node: {node.get('name')}")
    minimum = [float("inf")] * 3
    maximum = [float("-inf")] * 3
    translation, rotation, scale = world_trs(nodes, parents, node_index)
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
            transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
            point = [translation[axis] + transformed[axis] for axis in range(3)]
            for axis in range(3):
                minimum[axis] = min(minimum[axis], point[axis])
                maximum[axis] = max(maximum[axis], point[axis])
    return minimum, maximum


def aabb_clearance(first, second):
    first_min, first_max = first
    second_min, second_max = second
    gaps = [max(second_min[axis] - first_max[axis], first_min[axis] - second_max[axis], 0.0)
            for axis in range(3)]
    return math.sqrt(sum(gap * gap for gap in gaps))


def descendants(nodes, parents, ancestor_index):
    result = []
    for node_index in range(len(nodes)):
        current = node_index
        while current in parents:
            current = parents[current]
            if current == ancestor_index:
                result.append(node_index)
                break
    return result


def main():
    config = json.loads(CONFIG_PATH.read_text())
    mechanism = json.loads(MECHANISM_PATH.read_text())
    if config.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 configuration identity drift")
    document, blob = load_glb(GLB)
    glb_hash = digest(GLB)
    clearance_obstacles = json.loads(CLEARANCE_OBSTACLES_PATH.read_text(encoding="utf-8"))
    if (
        clearance_obstacles.get("schema_version") != "1.0.0"
        or clearance_obstacles.get("configuration_id") != EXPECTED_ID
        or clearance_obstacles.get("asset_sha256") != glb_hash
    ):
        raise RuntimeError("742 GLB-derived clearance obstacle fixture identity drift")
    match = re.search(r'JLG742_ASSET_SHA256\s*=\s*"([0-9a-f]{64})"', VERSION.read_text())
    if not match or match.group(1) != glb_hash:
        raise RuntimeError("742 cache identity does not match GLB")
    nodes = document.get("nodes") or []
    by_name, parents = index_nodes(nodes)
    fixture_obstacles = [*clearance_obstacles.get("cab", []), *clearance_obstacles.get("engine", [])]
    if not fixture_obstacles or len({record.get("name") for record in fixture_obstacles}) != len(fixture_obstacles):
        raise RuntimeError("742 GLB-derived clearance obstacle fixture set drift")
    for record in fixture_obstacles:
        name, expected_bounds = record.get("name"), record.get("bounds")
        if name not in by_name or not isinstance(expected_bounds, list) or len(expected_bounds) != 2:
            raise RuntimeError(f"742 clearance obstacle fixture node drift: {name}")
        actual_bounds = node_world_bounds(document, blob, nodes, parents, by_name[name])
        if any(abs(actual_bounds[edge][axis] - expected_bounds[edge][axis]) > 1e-6 for edge in range(2) for axis in range(3)):
            raise RuntimeError(f"742 clearance obstacle fixture no longer matches exported GLB node: {name}")
    root_index = by_name.get("742_ROOT")
    if root_index is None or root_index in parents:
        raise RuntimeError("742_ROOT is missing or parented")
    extras = nodes[root_index].get("extras") or {}
    if extras.get("configuration_id") != EXPECTED_ID or extras.get("ownership") != "owned_reconstruction_no_manufacturer_geometry":
        raise RuntimeError("742 GLB identity/ownership metadata drift")
    if extras.get("solver_contract") != "machines/742/solver.js":
        raise RuntimeError("742 GLB is not bound to the executable production solver")
    aliases = json.loads(extras.get("mechanism_aliases") or "{}")
    for alias, prefix in (("extend_chain_left", "ExtendChain_L"),
                          ("extend_chain_right", "ExtendChain_R"),
                          ("retract_chain", "RetractChain_C")):
        expected = [prefix, f"{prefix}_Wrap", *[
            f"{prefix}_Wrap_{index}" for index in range(1, 8)
        ], f"{prefix}_Moving"]
        if aliases.get(alias) != expected:
            raise RuntimeError(f"742 {alias} ordered path aliases drifted")
    if extras.get("release") != config.get("target_release"):
        raise RuntimeError("742 GLB release metadata does not match configuration target")
    boom_pivot_translation, _, _ = world_trs(nodes, parents, by_name["BoomLiftPivot"])
    mechanism_pivot = mechanism["boom"]["pivot_m"]
    if any(abs(actual - expected) > 1e-6 for actual, expected in zip(boom_pivot_translation, mechanism_pivot)):
        raise RuntimeError(f"742 boom pivot drift: {boom_pivot_translation} != {mechanism_pivot}")
    boom_angles = (nodes[by_name["BoomLiftPivot"]].get("extras") or {}).get("visual_angle_degrees")
    if boom_angles != config["visual_motion_limits"]["boom_angle_degrees"]:
        raise RuntimeError(f"742 boom-angle metadata drift: {boom_angles}")
    for child, expected_parent in REQUIRED_EDGES.items():
        if child not in by_name:
            raise RuntimeError(f"Missing required node: {child}")
        parent_index = parents.get(by_name[child])
        actual = nodes[parent_index].get("name") if parent_index is not None else None
        if actual != expected_parent:
            raise RuntimeError(f"Parent mismatch for {child}: {actual} != {expected_parent}")
    for hit in config["interaction_volumes"]:
        if not (nodes[by_name[hit]].get("extras") or {}).get("is_hit_volume"):
            raise RuntimeError(f"Interaction volume metadata missing: {hit}")
    missing_detail = sorted(REQUIRED_MECHANICAL_DETAIL - set(by_name))
    if missing_detail:
        raise RuntimeError(f"Missing mechanical detail contracts: {missing_detail}")
    evidence = json.loads(EVIDENCE_PATH.read_text())
    evidence_components = {component for system in evidence["systems"]
                           for claim in system["claims"] for component in claim["components"]}
    unresolved_components = sorted(evidence_components - set(by_name))
    if unresolved_components:
        raise RuntimeError(f"Evidence components do not resolve to exact GLB nodes: {unresolved_components}")
    triangles = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4 or "indices" not in primitive:
                raise RuntimeError("742 asset must use indexed triangle primitives")
            triangles += document["accessors"][primitive["indices"]]["count"] // 3
    if triangles > TRIANGLE_BUDGET:
        raise RuntimeError(f"Triangle budget exceeded: {triangles}")
    # Detail is admitted by named, hierarchical mechanisms above rather than by
    # a mesh/node-count floor, which would reward arbitrary object splitting.
    fork_extents = []
    for fork_name in ("ForkL", "ForkR"):
        node = nodes[by_name[fork_name]]
        raw = []
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            raw.extend(positions(document, blob, primitive["attributes"]["POSITION"]))
        fork_extents.append([max(point[axis] for point in raw) - min(point[axis] for point in raw) for axis in range(3)])
        extras = node.get("extras") or {}
        published = [extras.get("published_fork_length_m"), extras.get("published_fork_width_m"), extras.get("published_fork_thickness_m")]
        for axis, (actual, target) in enumerate(zip(fork_extents[-1], published)):
            if target is None or abs(actual - target) > 0.002:
                raise RuntimeError(f"{fork_name} axis {axis} is {actual:.4f} m, expected {target}")
    minimum, maximum = visible_bounds(document, blob, nodes, parents)
    envelope = [maximum[i] - minimum[i] for i in range(3)]
    stow_contract = mechanism["boom"]["runtime_stow"]
    if abs(envelope[0] - stow_contract["exact_total_length_with_48in_forks_m"]) > stow_contract["total_length_tolerance_m"]:
        raise RuntimeError(f"Exact runtime-stow total length drift: {envelope[0]:.6f} m")
    if minimum[1] < -0.005:
        raise RuntimeError(f"Ground-running geometry penetrates the floor: {minimum[1]:.4f} m")
    if not 2.34 <= envelope[1] <= 2.55:
        raise RuntimeError(f"Stowed height drift: {envelope[1]}")
    if not 2.35 <= envelope[2] <= 2.70:
        raise RuntimeError(f"Stowed width drift: {envelope[2]}")
    boom_bounds = {name: node_world_bounds(document, blob, nodes, parents, by_name[name])
                   for name in STOWED_BOOM_ENVELOPE_NODES}
    clearance_results = {}
    for group_name, ancestor_name, contract_key in (
        ("cab", "OpenCab", "minimum_stowed_boom_to_cab_clearance_m"),
        ("engine_hood", "EngineCompartment", "minimum_stowed_boom_to_engine_hood_clearance_m"),
    ):
        target_nodes = [node_index for node_index in descendants(nodes, parents, by_name[ancestor_name])
                        if "mesh" in nodes[node_index]
                        and not (nodes[node_index].get("extras") or {}).get("is_hit_volume")]
        candidates = []
        for boom_name, bounds in boom_bounds.items():
            for target_index in target_nodes:
                candidates.append((
                    aabb_clearance(bounds, node_world_bounds(document, blob, nodes, parents, target_index)),
                    boom_name,
                    nodes[target_index].get("name", ""),
                ))
        measured, boom_node, target_node = min(candidates)
        required = mechanism["collision_proxies"][contract_key]
        if measured + 1e-6 < required:
            raise RuntimeError(
                f"Stowed boom/{group_name} clearance {measured:.4f} m misses {required:.4f} m "
                f"between {boom_node} and {target_node}"
            )
        clearance_results[group_name] = {
            "clearance_m": measured, "minimum_m": required,
            "boom_node": boom_node, "target_node": target_node,
        }
    service_bounds = {
        name: node_world_bounds(document, blob, nodes, parents, node_index)
        for name, node_index in by_name.items()
        if name.startswith(STOWED_SERVICE_ENVELOPE_PREFIXES) and "mesh" in nodes[node_index]
    }
    service_clearance_results = {}
    for group_name, ancestor_name in (("cab", "OpenCab"), ("engine", "EngineCompartment")):
        target_nodes = [node_index for node_index in descendants(nodes, parents, by_name[ancestor_name])
                        if "mesh" in nodes[node_index]
                        and not (nodes[node_index].get("extras") or {}).get("is_hit_volume")]
        candidates = []
        for service_name, bounds in service_bounds.items():
            for target_index in target_nodes:
                candidates.append((
                    aabb_clearance(bounds, node_world_bounds(document, blob, nodes, parents, target_index)),
                    service_name,
                    nodes[target_index].get("name", ""),
                ))
        measured, service_node, target_node = min(candidates)
        required = mechanism["collision_proxies"]["minimum_stowed_service_line_to_cab_or_engine_clearance_m"]
        if measured + 1e-6 < required:
            raise RuntimeError(
                f"Stowed service-line/{group_name} clearance {measured:.4f} m misses {required:.4f} m "
                f"between {service_node} and {target_node}"
            )
        service_clearance_results[group_name] = {
            "clearance_m": measured, "minimum_m": required,
            "service_node": service_node, "target_node": target_node,
        }
    base_lateral_min, base_lateral_max = float("inf"), float("-inf")
    for node_index, node in enumerate(nodes):
        name = node.get("name", "")
        if "mesh" not in node or name.startswith("Mirror") or (node.get("extras") or {}).get("is_hit_volume"):
            continue
        translation, rotation, scale = world_trs(nodes, parents, node_index)
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
                transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
                lateral = translation[2] + transformed[2]
                base_lateral_min = min(base_lateral_min, lateral)
                base_lateral_max = max(base_lateral_max, lateral)
    base_width = base_lateral_max - base_lateral_min
    if abs(base_width - config["published_dimensions_m"]["width"]) > 0.012:
        raise RuntimeError(f"Base-machine width drift: {base_width:.4f} m")
    visual_lateral_bounds = mechanism["collision_proxies"]["visual_bounds_including_mirrors_m"]
    reconstructed_overall_width = visual_lateral_bounds[1] - visual_lateral_bounds[0]
    if abs(envelope[2] - reconstructed_overall_width) > 0.012:
        raise RuntimeError(f"Mirror-inclusive visual width drift: {envelope[2]:.4f} m")
    less_forks_min, less_forks_max = float("inf"), float("-inf")
    for node_index, node in enumerate(nodes):
        name = node.get("name", "")
        if "mesh" not in node or name.startswith("Fork") or (node.get("extras") or {}).get("is_hit_volume"):
            continue
        translation, rotation, scale = world_trs(nodes, parents, node_index)
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
                transformed = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
                longitudinal = translation[0] + transformed[0]
                less_forks_min = min(less_forks_min, longitudinal)
                less_forks_max = max(less_forks_max, longitudinal)
    length_less_forks = less_forks_max - less_forks_min
    if abs(length_less_forks - config["published_dimensions_m"]["length_less_forks"]) > 0.02:
        raise RuntimeError(f"Length-less-forks drift: {length_less_forks:.4f} m")
    if GLB.stat().st_size > 4_000_000:
        raise RuntimeError("742 GLB exceeds four-megabyte delivery ceiling")
    print(json.dumps({
        "status":"PASS", "configuration_id":EXPECTED_ID, "asset":str(GLB.relative_to(ROOT)), "sha256":glb_hash,
        "clearance_obstacle_fixture": {"path": str(CLEARANCE_OBSTACLES_PATH.relative_to(ROOT)), "sha256": digest(CLEARANCE_OBSTACLES_PATH), "nodes": [record["name"] for record in fixture_obstacles]},
        "source_blend_sha256":digest(BLEND), "bytes":GLB.stat().st_size, "nodes":len(nodes),
        "meshes":len(document.get("meshes", [])), "triangles":triangles, "triangle_budget":TRIANGLE_BUDGET,
        "interaction_volumes":sorted(config["interaction_volumes"]), "visible_bounds_min_m":minimum,
        "visible_bounds_max_m":maximum, "visible_envelope_xyz_m":envelope,
        "base_machine_width_excluding_mirrors_m": base_width,
        "mirror_inclusive_visual_width_m": envelope[2],
        "length_less_forks_m": length_less_forks,
        "fork_mesh_extents_length_width_thickness_m": fork_extents,
        "exact_runtime_stow_total_length_with_forks_m": envelope[0],
        "boom_pivot_world_m": boom_pivot_translation,
        "stowed_boom_clearance": clearance_results,
        "stowed_service_line_clearance": service_clearance_results,
        "mechanical_detail_contracts": sorted(REQUIRED_MECHANICAL_DETAIL),
        "evidence_components_resolved_to_exact_nodes": sorted(evidence_components),
        "detail_validation_basis": "named mechanisms and dimensions; no mesh-count quality floor"
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
