#!/usr/bin/env python3
"""Sweep the actual exported 742 boom meshes against actual static GLB obstacles."""

from __future__ import annotations

import json
import math
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb, positions, qrot, world_trs
from validate_742_glb import aabb_clearance, descendants, node_world_bounds


ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "assets/models/742.glb"
MECHANISM = json.loads((ROOT / "machines/742/mechanism.json").read_text(encoding="utf-8"))
BOOM_NODES = (
    "BaseBoomWeldment", "BaseBoomLowerWear", "MidBoomWeldment",
    "MidBoomTopPlate", "FlyBoomWeldment",
)


def world_vertices(document, blob, nodes, parents, node_index):
    node = nodes[node_index]
    translation, rotation, scale = world_trs(nodes, parents, node_index)
    result = []
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        for raw in positions(document, blob, primitive["attributes"]["POSITION"]):
            rotated = qrot(rotation, tuple(raw[axis] * scale[axis] for axis in range(3)))
            result.append(tuple(translation[axis] + rotated[axis] for axis in range(3)))
    return result


def under(nodes, parents, node_index, ancestor_index):
    current = node_index
    while current in parents:
        current = parents[current]
        if current == ancestor_index:
            return True
    return False


def posed_bounds(vertices, pivot, angle, telescope_shift):
    cosine, sine = math.cos(angle), math.sin(angle)
    transformed = []
    for x, y, z in vertices:
        local_x = x - pivot[0] + telescope_shift
        local_y = y - pivot[1]
        transformed.append((
            pivot[0] + cosine * local_x - sine * local_y,
            pivot[1] + sine * local_x + cosine * local_y,
            z,
        ))
    return (
        [min(point[axis] for point in transformed) for axis in range(3)],
        [max(point[axis] for point in transformed) for axis in range(3)],
    )


def main():
    document, blob = load_glb(GLB)
    nodes = document["nodes"]
    by_name, parents = index_nodes(nodes)
    pivot = MECHANISM["boom"]["pivot_m"]
    mid_travel = MECHANISM["boom"]["mid_visual_travel_m"]
    fly_travel = MECHANISM["boom"]["fly_visual_travel_m"]
    mid_index, fly_index = by_name["BoomMid"], by_name["BoomFly"]
    boom = {}
    for name in BOOM_NODES:
        node_index = by_name[name]
        travel = "fly" if under(nodes, parents, node_index, fly_index) else "mid" if under(nodes, parents, node_index, mid_index) else "base"
        boom[name] = {"vertices": world_vertices(document, blob, nodes, parents, node_index), "travel": travel}

    target_groups = {}
    for group, ancestor in (("cab", "OpenCab"), ("engine", "EngineCompartment")):
        target_groups[group] = {
            nodes[node_index].get("name", ""): node_world_bounds(document, blob, nodes, parents, node_index)
            for node_index in descendants(nodes, parents, by_name[ancestor])
            if "mesh" in nodes[node_index] and not (nodes[node_index].get("extras") or {}).get("is_hit_volume")
        }

    minima = {"cab": float("inf"), "engine": float("inf")}
    limiters = {"cab": None, "engine": None}
    for lift_index in range(201):
        lift = lift_index / 200
        angle = math.radians(MECHANISM["boom"]["maximum_visual_angle_degrees"] * lift)
        for telescope_index in range(201):
            telescope = telescope_index / 200
            for boom_name, record in boom.items():
                shift = 0.0
                if record["travel"] == "mid":
                    shift = telescope * mid_travel
                elif record["travel"] == "fly":
                    shift = telescope * (mid_travel + fly_travel)
                bounds = posed_bounds(record["vertices"], pivot, angle, shift)
                for group, targets in target_groups.items():
                    for target_name, target_bounds in targets.items():
                        clearance = aabb_clearance(bounds, target_bounds)
                        if clearance < minima[group]:
                            minima[group] = clearance
                            limiters[group] = {
                                "boom_node": boom_name,
                                "target_node": target_name,
                                "lift": lift,
                                "telescope": telescope,
                            }

    contract = MECHANISM["collision_proxies"]
    if minima["cab"] + 1e-6 < contract["minimum_stowed_boom_to_cab_clearance_m"]:
        raise RuntimeError(f"Actual posed GLB boom/cab clearance failed: {minima['cab']}")
    if minima["engine"] + 1e-6 < contract["minimum_stowed_boom_to_engine_hood_clearance_m"]:
        raise RuntimeError(f"Actual posed GLB boom/engine clearance failed: {minima['engine']}")
    print(json.dumps({
        "status": "PASS",
        "gate_kind": "actual_exported_glb_dense_rigid_boom_clearance_sweep",
        "samples": 201 * 201,
        "lift_samples": 201,
        "telescope_samples": 201,
        "minimum_cab_surface_clearance_m": minima["cab"],
        "minimum_engine_surface_clearance_m": minima["engine"],
        "cab_limiting_pair": limiters["cab"],
        "engine_limiting_pair": limiters["engine"],
        "boom_nodes": list(BOOM_NODES),
        "obstacle_nodes": {group: sorted(records) for group, records in target_groups.items()},
        "authority": "actual exported GLB mesh vertices posed through the production lift/telescope transform; owned reconstruction, not manufacturer clearance authority",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
