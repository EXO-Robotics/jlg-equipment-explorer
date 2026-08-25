#!/usr/bin/env python3
"""Validate the exported 600S GLB hierarchy without third-party packages."""

from __future__ import annotations

import json
import struct
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"

EXPECTED_PARENTS = {
    "Chassis": "600S_ROOT",
    "Frame": "Chassis",
    "AxleFront": "Chassis",
    "AxleRear": "Chassis",
    "Wheel_FL": "Chassis",
    "Wheel_FR": "Chassis",
    "Wheel_RL": "Chassis",
    "Wheel_RR": "Chassis",
    "TurntablePivot": "600S_ROOT",
    "Turntable": "TurntablePivot",
    "EngineCover": "Turntable",
    "Counterweight": "Turntable",
    "Controls": "Turntable",
    "BoomPivot": "Turntable",
    "MainBoom": "BoomPivot",
    "LiftCylinder": "BoomPivot",
    "Telescope": "MainBoom",
    "PlatformPivot": "Telescope",
    "Platform": "PlatformPivot",
    "Chassis_Hit": "Chassis",
    "Turntable_Hit": "Turntable",
    "Boom_Hit": "MainBoom",
    "Telescope_Hit": "Telescope",
    "Platform_Hit": "Platform",
}


def load_glb_json(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid GLB 2.0 header")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise RuntimeError("First GLB chunk is not JSON")
    return json.loads(data[20:20 + json_length].decode("utf-8"))


def main() -> None:
    document = load_glb_json(GLB_PATH)
    nodes = document.get("nodes", [])
    by_name: dict[str, int] = {}
    parents: dict[int, int] = {}
    for index, node in enumerate(nodes):
        name = node.get("name")
        if name:
            if name in by_name:
                raise RuntimeError(f"Duplicate node name: {name}")
            by_name[name] = index
        for child in node.get("children", []):
            parents[child] = index

    for child_name, parent_name in EXPECTED_PARENTS.items():
        if child_name not in by_name or parent_name not in by_name:
            raise RuntimeError(f"Missing required hierarchy node: {parent_name} -> {child_name}")
        actual_parent = parents.get(by_name[child_name])
        if actual_parent != by_name[parent_name]:
            actual_name = nodes[actual_parent].get("name") if actual_parent is not None else None
            raise RuntimeError(f"{child_name} parent is {actual_name!r}, expected {parent_name!r}")

    root = nodes[by_name["600S_ROOT"]]
    extras = root.get("extras", {})
    if extras.get("asset_version") != "0.1.0" or extras.get("units") != "meters":
        raise RuntimeError("Root provenance/version extras are missing")

    triangle_count = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            accessor_index = primitive.get("indices")
            if accessor_index is not None:
                triangle_count += document["accessors"][accessor_index]["count"] // 3
    if triangle_count > 20_000:
        raise RuntimeError(f"Blockout triangle budget exceeded: {triangle_count}")

    print(json.dumps({
        "status": "PASS",
        "asset": str(GLB_PATH.relative_to(PROJECT_ROOT)),
        "bytes": GLB_PATH.stat().st_size,
        "node_count": len(nodes),
        "mesh_count": len(document.get("meshes", [])),
        "triangle_count": triangle_count,
        "required_parent_edges": len(EXPECTED_PARENTS),
        "interaction_volumes": [name for name in EXPECTED_PARENTS if name.endswith("_Hit")],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
