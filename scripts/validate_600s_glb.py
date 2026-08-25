#!/usr/bin/env python3
"""Validate the exported 600S GLB against the contract and asset receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"
BLEND_PATH = PROJECT_ROOT / "source/blender/600s-detailed-v0.3.blend"
CONFIGURATION_PATH = PROJECT_ROOT / "assets/models/600s.configuration.json"
RECEIPT_PATH = PROJECT_ROOT / "assets/models/600s.asset-receipt.json"
RECEIPT_TEMPLATE_PATH = PROJECT_ROOT / "assets/models/600s.asset-receipt.template.json"
VERSION_JS_PATH = PROJECT_ROOT / "assets/models/600s.version.js"
INDEX_PATH = PROJECT_ROOT / "index.html"
VIEWER_PATH = PROJECT_ROOT / "viewer.js"
VIEWER_CSS_PATH = PROJECT_ROOT / "viewer.css"
PACKAGE_PATH = PROJECT_ROOT / "package.json"
VENDOR_HASHES = {
    "vendor/three-r160/build/three.module.min.js": "3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6",
    "vendor/three-r160/examples/jsm/loaders/GLTFLoader.js": "d073b438e6a07e1359741dd5d6c76c953420cc0d4fd84eb1bdde94315540e6a3",
    "vendor/three-r160/examples/jsm/utils/BufferGeometryUtils.js": "9be041e96308775d00e2695cc607645b9a9b64fd7c0e759dd8f7c00a8d92becb",
    "vendor/three-r160/LICENSE": "852e0e8699169bf9f6fdc6bda3e682d078dcbc738b5d33e74df594721bff271d",
}
RUNTIME_FILES = (
    INDEX_PATH,
    VIEWER_CSS_PATH,
    VIEWER_PATH,
    VERSION_JS_PATH,
    *(PROJECT_ROOT / relative_path for relative_path in VENDOR_HASHES if relative_path != "vendor/three-r160/LICENSE"),
)

ASSET_VERSION = "0.3.0"
CONFIGURATION_ID = "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696"
PUBLISHED_ENVELOPE_M = (8.71, 2.48, 2.50)  # length, width, height
PLATFORM_ENVELOPE_M = (0.91, 2.44)
WHEELBASE_M = 2.50
GROUND_CLEARANCE_M = 0.29
TAILSWING_M = 1.22
TELESCOPE_TRAVEL_M = 0.90
TRIANGLE_BUDGET = 60_000
ENVELOPE_TOLERANCE_M = 0.002
HASH_PREFIX_LEN = 12
TAILSWING_TOLERANCE_M = 0.002
REVIEW_FLAGS = (
    "loads_without_console_error",
    "articulation_pivots_pass",
    "selection_volumes_pass",
    "stowed_silhouette_reviewed",
    "working_pose_silhouette_pass",
    "mobile_view_reviewed",
    "provenance_reviewed",
)

EXPECTED_PARENTS = {
    "Chassis": "600S_ROOT",
    "Frame": "Chassis",
    "AxleFront": "Chassis",
    "AxleRear": "Chassis",
    "Wheel_FL": "Chassis",
    "Wheel_FR": "Chassis",
    "Wheel_RL": "Chassis",
    "Wheel_RR": "Chassis",
    "SteerHydraulicHose_L": "Chassis",
    "SteerHydraulicHose_R": "Chassis",
    "ChassisDriveHarness_L": "Chassis",
    "ChassisDriveHarness_R": "Chassis",
    "TurntablePivot": "600S_ROOT",
    "Turntable": "TurntablePivot",
    "SlewRing": "Turntable",
    "UpperFrame": "Turntable",
    "EngineCover": "Turntable",
    "TankCover": "Turntable",
    "Counterweight": "Turntable",
    "Controls": "Turntable",
    "MainValveBank": "Turntable",
    "EngineControlModule": "Turntable",
    "GroundControlHarness": "Turntable",
    "EngineHarness": "Turntable",
    "BoomPivot": "Turntable",
    "MainBoom": "BoomPivot",
    "Telescope": "MainBoom",
    "MidBoom": "Telescope",
    "FlyBoom": "MidBoom",
    "PlatformPivot": "FlyBoom",
    "Platform": "PlatformPivot",
    "LiftCylinder": "Turntable",
    "LiftCylinderLowerAnchor": "Turntable",
    "LiftCylinderUpperAnchor": "MainBoom",
    "LiftCylinderBarrel": "LiftCylinder",
    "LiftCylinderRod": "LiftCylinder",
    "LiftCylinderBasePin": "LiftCylinder",
    "LiftCylinderRodPin": "LiftCylinder",
    "LiftCylinderHose_A": "LiftCylinder",
    "LiftCylinderHose_B": "LiftCylinder",
    "BoomHydraulicBundle_L": "MainBoom",
    "BoomHydraulicBundle_R": "MainBoom",
    "BoomSensorLower": "MainBoom",
    "BoomSensorUpper": "MidBoom",
    "TeleProximitySensor": "FlyBoom",
    "BoomCableUpper": "MainBoom",
    "PlatformHarness": "FlyBoom",
    "TowerLinkLower": "BoomPivot",
    "TowerLinkUpper": "BoomPivot",
    "Powertrack": "MainBoom",
    "PlatformRotator": "PlatformPivot",
    "PlatformSwingGate": "Platform",
    "PlatformConsole": "Platform",
    "PlatformFootswitch": "Platform",
    "PlatformRotatorHose_A": "PlatformPivot",
    "PlatformRotatorHose_B": "PlatformPivot",
    "FootswitchHarness": "Platform",
    "Chassis_Hit": "Chassis",
    "Turntable_Hit": "Turntable",
    "Boom_Hit": "MainBoom",
    "Telescope_Hit": "Telescope",
    "Platform_Hit": "Platform",
}

HIT_VOLUMES = ("Chassis_Hit", "Turntable_Hit", "Boom_Hit", "Telescope_Hit", "Platform_Hit")
IDENTITY_CHAIN = ("MainBoom", "Telescope", "MidBoom", "FlyBoom", "PlatformPivot", "Platform")

POSITION_COMPONENT_TYPE = 5126
POSITION_STRIDE = 12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_sha256() -> str:
    digest = hashlib.sha256()
    for path in RUNTIME_FILES:
        relative_path = str(path.relative_to(PROJECT_ROOT)).encode("utf-8")
        digest.update(relative_path)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def version_js_text(cache_key: str) -> str:
    return (
        f"export const SHOWCASE_RELEASE = {ASSET_VERSION!r};\n"
        f"export const TELESCOPE_TRAVEL_M = {TELESCOPE_TRAVEL_M!r};\n"
        f"export const GLB_URL = {'assets/models/600s.glb?v=' + cache_key!r};\n"
    )


def load_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise RuntimeError("Invalid GLB 2.0 header")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise RuntimeError("First GLB chunk is not JSON")
    document = json.loads(data[20:20 + json_length].decode("utf-8"))
    bin_offset = 20 + json_length
    chunk_len, chunk_type = struct.unpack_from("<II", data, bin_offset)
    if chunk_type != 0x004E4942:
        raise RuntimeError("Second GLB chunk is not BIN")
    blob = data[bin_offset + 8:bin_offset + 8 + chunk_len]
    return document, blob


def qmul(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float, float]:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def qrot(q: tuple[float, ...], v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def node_index(nodes: list[dict[str, Any]]) -> tuple[dict[str, int], dict[int, int]]:
    by_name: dict[str, int] = {}
    parents: dict[int, int] = {}
    for index, node in enumerate(nodes):
        name = node.get("name")
        if name:
            if name in by_name:
                raise RuntimeError(f"Duplicate node name: {name}")
            by_name[name] = index
        for child in node.get("children", []):
            if not isinstance(child, int) or not 0 <= child < len(nodes):
                raise RuntimeError(f"Node {name!r} has invalid child index: {child!r}")
            if child in parents:
                first_parent = nodes[parents[child]].get("name")
                child_name = nodes[child].get("name")
                raise RuntimeError(f"Node {child_name!r} has multiple parents: {first_parent!r} and {name!r}")
            parents[child] = index
    return by_name, parents


def validate_rooted_tree(nodes: list[dict[str, Any]], parents: dict[int, int], root_index: int) -> None:
    if root_index in parents:
        parent_name = nodes[parents[root_index]].get("name")
        raise RuntimeError(f"600S_ROOT must not have a parent; found {parent_name!r}")

    reachable: set[int] = set()
    pending = [root_index]
    while pending:
        index = pending.pop()
        if index in reachable:
            raise RuntimeError(f"Cycle or repeated path reaches node {nodes[index].get('name')!r}")
        reachable.add(index)
        pending.extend(nodes[index].get("children", []))

    if len(reachable) != len(nodes):
        orphan_names = [nodes[index].get("name") or f"node[{index}]" for index in range(len(nodes)) if index not in reachable]
        raise RuntimeError(f"All GLB nodes must descend from 600S_ROOT; unreachable: {orphan_names}")


def world_trs(nodes: list[dict[str, Any]], parents: dict[int, int], index: int) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    chain = []
    current: int | None = index
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
        scaled_local_t = tuple(scale[i] * local_t[i] for i in range(3))
        rotated = qrot(rotation, scaled_local_t)
        translation = (
            translation[0] + rotated[0],
            translation[1] + rotated[1],
            translation[2] + rotated[2],
        )
        rotation = qmul(rotation, local_r)
        scale = (scale[0] * local_s[0], scale[1] * local_s[1], scale[2] * local_s[2])
    return translation, rotation, scale


def accessor_positions(document: dict[str, Any], blob: bytes, accessor_index: int) -> list[tuple[float, float, float]]:
    accessor = document["accessors"][accessor_index]
    if accessor.get("type") != "VEC3" or accessor.get("componentType") != POSITION_COMPONENT_TYPE:
        raise RuntimeError(f"POSITION accessor {accessor_index} must be float VEC3")
    if accessor.get("sparse"):
        raise RuntimeError(f"Sparse POSITION accessor {accessor_index} is not supported")
    view = document["bufferViews"][accessor["bufferView"]]
    if view.get("buffer", 0) != 0:
        raise RuntimeError(f"POSITION accessor {accessor_index} must use GLB buffer 0")
    stride = view.get("byteStride", POSITION_STRIDE)
    if stride < POSITION_STRIDE:
        raise RuntimeError(f"Invalid POSITION stride {stride}")
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    end = offset + max(accessor["count"] - 1, 0) * stride + POSITION_STRIDE
    if end > len(blob):
        raise RuntimeError(f"POSITION accessor {accessor_index} exceeds the GLB buffer")
    return [struct.unpack_from("<fff", blob, offset + index * stride) for index in range(accessor["count"])]


def mesh_world_aabb(
    document: dict[str, Any],
    blob: bytes,
    nodes: list[dict[str, Any]],
    parents: dict[int, int],
    node_i: int,
) -> tuple[list[float], list[float]]:
    node = nodes[node_i]
    if "mesh" not in node:
        raise RuntimeError(f"{node.get('name')} is not a mesh")
    translation, rotation, scale = world_trs(nodes, parents, node_i)
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        if "POSITION" not in primitive.get("attributes", {}):
            raise RuntimeError(f"Mesh {node.get('name')} has a primitive without POSITION")
        for x, y, z in accessor_positions(document, blob, primitive["attributes"]["POSITION"]):
            vx, vy, vz = qrot(rotation, (x * scale[0], y * scale[1], z * scale[2]))
            point = (translation[0] + vx, translation[1] + vy, translation[2] + vz)
            for axis in range(3):
                mins[axis] = min(mins[axis], point[axis])
                maxs[axis] = max(maxs[axis], point[axis])
    return mins, maxs


def visible_aabb(document: dict[str, Any], blob: bytes, nodes: list[dict[str, Any]], parents: dict[int, int]) -> tuple[list[float], list[float]]:
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    found = False
    for index, node in enumerate(nodes):
        if "mesh" not in node:
            continue
        extras = node.get("extras") or {}
        if extras.get("is_hit_volume"):
            continue
        mesh_min, mesh_max = mesh_world_aabb(document, blob, nodes, parents, index)
        found = True
        for axis in range(3):
            mins[axis] = min(mins[axis], mesh_min[axis])
            maxs[axis] = max(maxs[axis], mesh_max[axis])
    if not found:
        raise RuntimeError("No visible meshes found")
    return mins, maxs


def close(actual: float, expected: float, tolerance: float = ENVELOPE_TOLERANCE_M) -> bool:
    return math.isclose(actual, expected, abs_tol=tolerance)


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"Receipt {label} is stale: {actual!r} != {expected!r}")


def require_close_list(actual: Any, expected: list[float], label: str) -> None:
    if not isinstance(actual, list) or len(actual) != len(expected) or any(
        not close(float(value), float(target)) for value, target in zip(actual, expected)
    ):
        raise RuntimeError(f"Receipt {label} is stale: {actual!r} != {expected!r}")


def validate_receipt(receipt: dict[str, Any], report: dict[str, Any]) -> None:
    expected_values = {
        "asset": report["asset"],
        "authorship": "owned-simplified-reconstruction",
        "builder": "scripts/build_600s_blockout.py",
        "validator": "scripts/validate_600s_glb.py",
        "release": report["release"],
        "configuration_id": report["configuration_id"],
        "source_blend": report["source_blend"],
        "sha256": report["sha256"],
        "source_blend_sha256": report["source_blend_sha256"],
        "cache_key": report["cache_key"],
        "runtime_sha256": report["runtime_sha256"],
        "units": report["units"],
        "root_node": report["root_node"],
        "triangle_count": report["triangle_count"],
        "node_count": report["node_count"],
        "required_parent_edges": report["required_parent_edges"],
        "interaction_volumes": report["interaction_volumes"],
    }
    for key, expected in expected_values.items():
        require_equal(receipt.get(key), expected, key)
    review = receipt.get("review") or {}
    expected_status = "DETAILED_V0_3_ACCEPTED" if all(review.get(flag) is True for flag in REVIEW_FLAGS) else "DETAILED_V0_3_MECHANICAL_PASS"
    require_equal(receipt.get("status"), expected_status, "status")
    for key in ("visible_envelope_m", "platform_envelope_m"):
        require_close_list(receipt.get(key), report[key], key)
    for key in ("wheelbase_m", "ground_clearance_m", "tailswing_m", "telescope_travel_m", "telescope_overlap_at_100_m"):
        if not close(float(receipt.get(key, float("nan"))), float(report[key])):
            raise RuntimeError(f"Receipt {key} is stale")

    mechanical = receipt.get("mechanical_validation") or {}
    require_equal(mechanical.get("status"), report["status"], "mechanical_validation.status")
    for key in ("bytes", "mesh_count"):
        require_equal(mechanical.get(key), report[key], f"mechanical_validation.{key}")
    for key in ("visible_bounds_min_m", "visible_bounds_max_m"):
        require_close_list(mechanical.get(key), report[key], f"mechanical_validation.{key}")
    if not close(float(mechanical.get("telescope_overlap_stowed_m", float("nan"))), report["telescope_overlap_stowed_m"]):
        raise RuntimeError("Receipt mechanical_validation.telescope_overlap_stowed_m is stale")

    if not RECEIPT_TEMPLATE_PATH.is_file():
        raise RuntimeError(f"Missing receipt template: {RECEIPT_TEMPLATE_PATH}")
    template = json.loads(RECEIPT_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if set(template) != set(receipt):
        raise RuntimeError("Receipt and template top-level fields differ")
    for section in ("mechanical_validation", "review"):
        if set(template.get(section, {})) != set(receipt.get(section, {})):
            raise RuntimeError(f"Receipt and template {section} fields differ")
    if set(template.get("review", {}).get("evidence", {})) != set(receipt.get("review", {}).get("evidence", {})):
        raise RuntimeError("Receipt and template review evidence fields differ")
    require_equal(receipt.get("evidence_boundary"), template.get("evidence_boundary"), "evidence_boundary")
    if not isinstance(receipt.get("exported_at"), str) or not receipt["exported_at"].endswith("Z"):
        raise RuntimeError("Receipt exported_at must be a UTC timestamp")
    if expected_status == "DETAILED_V0_3_ACCEPTED":
        evidence = review.get("evidence") or {}
        for key in template["review"]["evidence"]:
            if not isinstance(evidence.get(key), str) or not evidence[key].strip():
                raise RuntimeError(f"Accepted receipt is missing review evidence: {key}")

    expected_version = version_js_text(report["cache_key"])
    if not VERSION_JS_PATH.is_file() or VERSION_JS_PATH.read_text(encoding="utf-8") != expected_version:
        raise RuntimeError("600s.version.js does not match the validated GLB")

    for relative_path, expected_hash in VENDOR_HASHES.items():
        vendor_path = PROJECT_ROOT / relative_path
        if not vendor_path.is_file():
            raise RuntimeError(f"Missing pinned viewer dependency: {relative_path}")
        if sha256_file(vendor_path) != expected_hash:
            raise RuntimeError(f"Pinned viewer dependency hash drift: {relative_path}")

    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    if package.get("version") != ASSET_VERSION:
        raise RuntimeError("package.json release does not match the asset")
    index_source = INDEX_PATH.read_text(encoding="utf-8")
    if "cdn.jsdelivr.net" in index_source:
        raise RuntimeError("index.html must use the pinned local Three.js runtime")
    for dependency_path in ("./vendor/three-r160/build/three.module.min.js", "./vendor/three-r160/examples/jsm/"):
        if dependency_path not in index_source:
            raise RuntimeError(f"index.html is missing pinned dependency path: {dependency_path}")
    for asset_name in ("viewer.css", "viewer.js"):
        if f'{asset_name}?v={ASSET_VERSION}' not in index_source:
            raise RuntimeError(f"index.html does not cache-key {asset_name} with the release")
    viewer_source = VIEWER_PATH.read_text(encoding="utf-8")
    if f'./assets/models/600s.version.js?v={ASSET_VERSION}' not in viewer_source:
        raise RuntimeError("viewer.js does not cache-key the asset manifest with the release")


def validate(*, require_receipt: bool = True) -> dict[str, Any]:
    if not GLB_PATH.is_file():
        raise RuntimeError(f"Missing GLB: {GLB_PATH}")
    if not BLEND_PATH.is_file():
        raise RuntimeError(f"Missing Blender source: {BLEND_PATH}")
    if not CONFIGURATION_PATH.is_file():
        raise RuntimeError(f"Missing frozen configuration: {CONFIGURATION_PATH}")

    configuration = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    if configuration.get("configuration_id") != CONFIGURATION_ID:
        raise RuntimeError("Frozen 600S configuration identity drift")
    if configuration.get("required_parent_edges") != EXPECTED_PARENTS:
        raise RuntimeError("Validator hierarchy has drifted from 600s.configuration.json")
    if configuration.get("interaction_volumes") != list(HIT_VOLUMES):
        raise RuntimeError("Validator interaction volumes have drifted from the frozen configuration")

    document, blob = load_glb(GLB_PATH)
    nodes = document.get("nodes") or []
    by_name, parents = node_index(nodes)

    scenes = document.get("scenes") or []
    if len(scenes) != 1:
        raise RuntimeError(f"Expected one export scene, found {len(scenes)}: {[scene.get('name') for scene in scenes]}")
    scene_nodes = scenes[0].get("nodes") or []
    if scene_nodes != [by_name.get("600S_ROOT")]:
        raise RuntimeError("Export scene must contain only 600S_ROOT")
    validate_rooted_tree(nodes, parents, by_name["600S_ROOT"])

    for child_name, parent_name in EXPECTED_PARENTS.items():
        if child_name not in by_name or parent_name not in by_name:
            raise RuntimeError(f"Missing required hierarchy node: {parent_name} -> {child_name}")
        actual_parent = parents.get(by_name[child_name])
        if actual_parent != by_name[parent_name]:
            actual_name = nodes[actual_parent].get("name") if actual_parent is not None else None
            raise RuntimeError(f"{child_name} parent is {actual_name!r}, expected {parent_name!r}")

    for section_name, section in (configuration.get("sections") or {}).items():
        for required_name in section.get("required_nodes") or []:
            if required_name not in by_name:
                raise RuntimeError(f"Missing {section_name} detail node: {required_name}")

    for hit_name in HIT_VOLUMES:
        node = nodes[by_name[hit_name]]
        if "mesh" not in node:
            raise RuntimeError(f"{hit_name} is not a mesh")
        extras = node.get("extras") or {}
        if extras.get("is_hit_volume") is not True:
            raise RuntimeError(f"{hit_name} is missing is_hit_volume extras")

    for index, node in enumerate(nodes):
        if "matrix" in node:
            raise RuntimeError(f"Matrix transform on {node.get('name')}; export explicit identity-scale TRS")
        scale = node.get("scale") or [1.0, 1.0, 1.0]
        if any(value < 0 for value in scale):
            raise RuntimeError(f"Negative scale on {node.get('name')}: {scale}")
        if any(abs(value - 1.0) > 1e-5 for value in scale):
            raise RuntimeError(f"Non-identity scale on {node.get('name')}: {scale}")
        rotation = node.get("rotation")
        if node.get("name") in IDENTITY_CHAIN and rotation and not all(
            close(value, expected, 1e-5) for value, expected in zip(rotation, (0.0, 0.0, 0.0, 1.0))
        ):
            raise RuntimeError(f"{node.get('name')} must be identity rotation at rest")

    root = nodes[by_name["600S_ROOT"]]
    extras = root.get("extras") or {}
    if extras.get("asset_version") != ASSET_VERSION or extras.get("units") != "meters":
        raise RuntimeError("Root provenance/version extras are missing or stale")
    if extras.get("configuration_id") != CONFIGURATION_ID:
        raise RuntimeError("Root configuration_id is missing or stale")
    travel = extras.get("telescope_travel_m", TELESCOPE_TRAVEL_M)
    if not close(float(travel), TELESCOPE_TRAVEL_M, 0.001):
        raise RuntimeError(f"Unexpected telescope_travel_m extra: {travel}")
    if extras.get("platform_leveling") != "counter_rotate_local_z":
        raise RuntimeError("Root is missing platform_leveling extra")
    if not close(float(extras.get("ground_clearance_m", float("nan"))), GROUND_CLEARANCE_M):
        raise RuntimeError("Root is missing the ground-clearance contract")
    if not close(float(extras.get("tailswing_m", float("nan"))), TAILSWING_M):
        raise RuntimeError("Root is missing the tailswing contract")

    cylinder = nodes[by_name["LiftCylinder"]]
    cylinder_extras = cylinder.get("extras") or {}
    if "mesh" in cylinder or cylinder_extras.get("runtime_solver") != "two_anchor_visual":
        raise RuntimeError("LiftCylinder must be an empty two-anchor visual-solver group")
    for anchor_name, parent_name in (
        ("LiftCylinderLowerAnchor", "Turntable"),
        ("LiftCylinderUpperAnchor", "MainBoom"),
    ):
        if anchor_name not in by_name:
            raise RuntimeError(f"Missing lift-cylinder anchor: {anchor_name}")
        anchor = nodes[by_name[anchor_name]]
        if "mesh" in anchor:
            raise RuntimeError(f"{anchor_name} must be a non-rendering transform node")
        if parents.get(by_name[anchor_name]) != by_name[parent_name]:
            raise RuntimeError(f"{anchor_name} must be parented to {parent_name}")

    triangle_count = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                raise RuntimeError("Only triangle-list primitives are accepted")
            accessor_index = primitive.get("indices")
            count = document["accessors"][accessor_index]["count"] if accessor_index is not None else document["accessors"][primitive["attributes"]["POSITION"]]["count"]
            triangle_count += count // 3
    if triangle_count > TRIANGLE_BUDGET:
        raise RuntimeError(f"Blockout triangle budget exceeded: {triangle_count}")

    mins, maxs = visible_aabb(document, blob, nodes, parents)
    size = [maxs[i] - mins[i] for i in range(3)]
    envelope = (size[0], size[2], size[1])
    for axis, actual, expected in zip(("length", "width", "height"), envelope, PUBLISHED_ENVELOPE_M):
        if not close(actual, expected):
            raise RuntimeError(f"Visible {axis} envelope drift: {actual:.4f} m != {expected:.4f} m")
    if mins[1] < -0.002:
        raise RuntimeError(f"Model penetrates ground: minY={mins[1]:.4f}")

    fl = world_trs(nodes, parents, by_name["Wheel_FL"])[0]
    rl = world_trs(nodes, parents, by_name["Wheel_RL"])[0]
    wheelbase = abs(fl[0] - rl[0])
    if not close(wheelbase, WHEELBASE_M, 0.001):
        raise RuntimeError(f"Wheelbase drift: {wheelbase:.4f} m")

    deck_min, deck_max = mesh_world_aabb(document, blob, nodes, parents, by_name["PlatformDeck"])
    platform_size = (deck_max[0] - deck_min[0], deck_max[2] - deck_min[2])
    if not close(platform_size[0], PLATFORM_ENVELOPE_M[0]) or not close(platform_size[1], PLATFORM_ENVELOPE_M[1]):
        raise RuntimeError(f"Platform envelope drift: {platform_size}")

    main_min, main_max = mesh_world_aabb(document, blob, nodes, parents, by_name["BaseBoomShell"])
    tel_min, tel_max = mesh_world_aabb(document, blob, nodes, parents, by_name["MidBoomShell"])
    overlap_stowed = main_max[0] - tel_min[0]
    overlap_100 = main_max[0] - (tel_min[0] + TELESCOPE_TRAVEL_M)
    if overlap_100 <= 0.001:
        raise RuntimeError(f"Telescope separates at 100% travel: overlap {overlap_100:.4f} m")

    frame_min, _ = mesh_world_aabb(document, blob, nodes, parents, by_name["Frame"])
    belly_min, _ = mesh_world_aabb(document, blob, nodes, parents, by_name["BellyPan"])
    ground_clearance = min(frame_min[1], belly_min[1])
    if not close(ground_clearance, GROUND_CLEARANCE_M):
        raise RuntimeError(f"Ground-clearance drift: {ground_clearance:.4f} m")

    counterweight_min, _ = mesh_world_aabb(document, blob, nodes, parents, by_name["Counterweight"])
    slew_x = world_trs(nodes, parents, by_name["TurntablePivot"])[0][0]
    tailswing = (slew_x - counterweight_min[0]) - PUBLISHED_ENVELOPE_M[1] / 2.0
    if not close(tailswing, TAILSWING_M, TAILSWING_TOLERANCE_M):
        raise RuntimeError(f"Tailswing drift: {tailswing:.4f} m")

    for hit_name in HIT_VOLUMES:
        hit_min, hit_max = mesh_world_aabb(document, blob, nodes, parents, by_name[hit_name])
        if any(hit_min[axis] < mins[axis] - ENVELOPE_TOLERANCE_M or hit_max[axis] > maxs[axis] + ENVELOPE_TOLERANCE_M for axis in range(3)):
            raise RuntimeError(f"{hit_name} extends outside the visible stowed envelope")

    glb_hash = sha256_file(GLB_PATH)
    blend_hash = sha256_file(BLEND_PATH)
    report = {
        "status": "PASS",
        "asset": str(GLB_PATH.relative_to(PROJECT_ROOT)),
        "configuration_id": CONFIGURATION_ID,
        "source_blend": str(BLEND_PATH.relative_to(PROJECT_ROOT)),
        "release": ASSET_VERSION,
        "bytes": GLB_PATH.stat().st_size,
        "sha256": glb_hash,
        "source_blend_sha256": blend_hash,
        "cache_key": glb_hash[:HASH_PREFIX_LEN],
        "runtime_sha256": runtime_sha256(),
        "node_count": len(nodes),
        "mesh_count": len(document.get("meshes", [])),
        "triangle_count": triangle_count,
        "required_parent_edges": len(EXPECTED_PARENTS),
        "interaction_volumes": list(HIT_VOLUMES),
        "visible_envelope_m": [round(value, 4) for value in envelope],
        "visible_bounds_min_m": [round(value, 4) for value in mins],
        "visible_bounds_max_m": [round(value, 4) for value in maxs],
        "wheelbase_m": round(wheelbase, 4),
        "ground_clearance_m": round(ground_clearance, 4),
        "tailswing_m": round(tailswing, 4),
        "platform_envelope_m": [round(value, 4) for value in platform_size],
        "telescope_travel_m": TELESCOPE_TRAVEL_M,
        "telescope_overlap_stowed_m": round(overlap_stowed, 4),
        "telescope_overlap_at_100_m": round(overlap_100, 4),
        "units": "meters",
        "root_node": "600S_ROOT",
    }
    if require_receipt:
        if not RECEIPT_PATH.is_file():
            raise RuntimeError(f"Missing asset receipt: {RECEIPT_PATH}")
        validate_receipt(json.loads(RECEIPT_PATH.read_text(encoding="utf-8")), report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-receipt", action="store_true", help="Validate geometry without requiring a matching receipt")
    args = parser.parse_args()
    report = validate(require_receipt=not args.skip_receipt)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
