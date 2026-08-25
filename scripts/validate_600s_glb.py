#!/usr/bin/env python3
"""Validate the exported 600S GLB against the contract and asset receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLB_PATH = PROJECT_ROOT / "assets/models/600s.glb"
BLEND_PATH = PROJECT_ROOT / "source/blender/600s-showcase-v1.1.blend"
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

ASSET_VERSION = "1.1.0"
CONFIGURATION_ID = "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696"
PUBLISHED_ENVELOPE_M = (8.71, 2.48, 2.50)  # length, width, height
PLATFORM_ENVELOPE_M = (0.91, 2.44)
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

EXPECTED_PARENTS = json.loads(CONFIGURATION_PATH.read_text(encoding="utf-8"))["required_parent_edges"]

HIT_VOLUMES = ("Chassis_Hit", "Turntable_Hit", "Boom_Hit", "Telescope_Hit", "Platform_Hit")
IDENTITY_CHAIN = ("MainBoom", "Telescope", "MidBoom", "FlyBoom", "PlatformPivot", "Platform")
LEGACY_DETACHED_ACCESSORIES = ("TieDown_FL", "TieDown_FR", "TieDown_RL", "TieDown_RR")
ACCESSORY_ATTACHMENTS = (
    ("BoomRestPost_L", "ChassisFrontPod"),
    ("BoomRestPost_R", "ChassisFrontPod"),
    ("BoomRestPost_L", "BoomRest"),
    ("BoomRestPost_R", "BoomRest"),
    ("BoomRestPad", "BoomRest"),
    ("SideStep_L", "LowerDeck"),
    ("SideStep_R", "LowerDeck"),
    ("SideStepBracket_L", "SideStep_L"),
    ("SideStepBracket_R", "SideStep_R"),
    ("SideStepBracket_L", "ChassisFrontPod"),
    ("SideStepBracket_R", "ChassisFrontPod"),
    ("TieDownPocket_FL", "FrameRail_L"),
    ("TieDownPocket_FR", "FrameRail_R"),
    ("TieDownPocket_RL", "FrameRail_L"),
    ("TieDownPocket_RR", "FrameRail_R"),
)

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
        f"export const TELESCOPE_MID_TRAVEL_M = {TELESCOPE_MID_TRAVEL_M!r};\n"
        f"export const TELESCOPE_FLY_TRAVEL_M = {TELESCOPE_FLY_TRAVEL_M!r};\n"
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


def qz(radians: float) -> tuple[float, float, float, float]:
    return (0.0, 0.0, math.sin(radians * 0.5), math.cos(radians * 0.5))


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
    expected_status = "SHOWCASE_V1_1_ACCEPTED" if all(review.get(flag) is True for flag in REVIEW_FLAGS) else "SHOWCASE_V1_1_MECHANICAL_PASS"
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
    if expected_status == "SHOWCASE_V1_1_ACCEPTED":
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
    runtime_version = package.get("version")
    if not isinstance(runtime_version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", runtime_version):
        raise RuntimeError("package.json must declare a semantic runtime version")
    index_source = INDEX_PATH.read_text(encoding="utf-8")
    if "cdn.jsdelivr.net" in index_source:
        raise RuntimeError("index.html must use the pinned local Three.js runtime")
    for dependency_path in ("./vendor/three-r160/build/three.module.min.js", "./vendor/three-r160/examples/jsm/"):
        if dependency_path not in index_source:
            raise RuntimeError(f"index.html is missing pinned dependency path: {dependency_path}")
    for asset_name in ("viewer.css", "viewer.js"):
        if f'{asset_name}?v={runtime_version}' not in index_source:
            raise RuntimeError(f"index.html does not cache-key {asset_name} with runtime {runtime_version}")
    if f'assets/models/600s.glb?v={report["cache_key"]}' not in index_source:
        raise RuntimeError("index.html GLB preload cache key does not match the validated asset")
    viewer_source = VIEWER_PATH.read_text(encoding="utf-8")
    if f'./assets/models/600s.version.js?v={runtime_version}' not in viewer_source:
        raise RuntimeError("viewer.js does not cache-key the asset manifest with the runtime release")


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
    if scenes[0].get("name") != "JLG_600S_SHOWCASE_V11":
        raise RuntimeError(f"Showcase scene identity drift: {scenes[0].get('name')!r}")
    scene_extras = scenes[0].get("extras") or {}
    if scene_extras.get("asset") != "600S Showcase reconstruction v1.1":
        raise RuntimeError(f"Showcase scene asset label drift: {scene_extras.get('asset')!r}")
    if scene_extras.get("asset_version") != ASSET_VERSION:
        raise RuntimeError("Showcase scene release metadata drift")
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

    legacy_accessories = sorted(name for name in LEGACY_DETACHED_ACCESSORIES if name in by_name)
    if legacy_accessories:
        raise RuntimeError(f"Detached legacy chassis accessories remain in the GLB: {legacy_accessories}")
    for part_name, support_name in ACCESSORY_ATTACHMENTS:
        if part_name not in by_name or support_name not in by_name:
            raise RuntimeError(f"Missing chassis attachment pair: {part_name} -> {support_name}")
        part_min, part_max = mesh_world_aabb(document, blob, nodes, parents, by_name[part_name])
        support_min, support_max = mesh_world_aabb(document, blob, nodes, parents, by_name[support_name])
        overlap = [
            min(part_max[axis], support_max[axis]) - max(part_min[axis], support_min[axis])
            for axis in range(3)
        ]
        if any(value < 0.004 for value in overlap):
            raise RuntimeError(
                f"Detached chassis accessory: {part_name} does not overlap {support_name}; "
                f"axis overlap={[round(value, 4) for value in overlap]}"
            )

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
    if not close(float(extras.get("telescope_mid_travel_m", float("nan"))), TELESCOPE_MID_TRAVEL_M, 0.001):
        raise RuntimeError("Root is missing the visual MidBoom travel contract")
    if not close(float(extras.get("telescope_fly_travel_m", float("nan"))), TELESCOPE_FLY_TRAVEL_M, 0.001):
        raise RuntimeError("Root is missing the visual FlyBoom travel contract")
    if extras.get("telescope_staging") != "evidence_bounded_coupled_visual":
        raise RuntimeError("Root is missing the coupled telescope evidence boundary")
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

    visual_solvers = {
        "TowerLink": "two_anchor_visual_link",
        "TensionLink": "two_anchor_visual_link",
        "SteerTieRod": "two_anchor_visual_link",
        "SteerCylinder_L": "two_anchor_visual_cylinder",
        "SteerCylinder_R": "two_anchor_visual_cylinder",
        "PlatformLevelCylinder": "two_anchor_visual_cylinder",
        "SteerHydraulicHose_L_Flexible": "two_anchor_visual_hose",
        "SteerHydraulicHose_R_Flexible": "two_anchor_visual_hose",
    }
    for solver_name, solver_kind in visual_solvers.items():
        solver = nodes[by_name[solver_name]]
        if "mesh" in solver or (solver.get("extras") or {}).get("runtime_solver") != solver_kind:
            raise RuntimeError(f"{solver_name} must be an empty {solver_kind} group")

    for wheel_name in ("Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"):
        roll_name = f"{wheel_name}_Roll"
        roll = nodes[by_name[roll_name]]
        if "mesh" in roll or (roll.get("extras") or {}).get("runtime_axis") != "local_y_blender_local_z_gltf":
            raise RuntimeError(f"{roll_name} must be an empty tire-only roll transform")
        for moving_name in (f"{wheel_name}_Tire", f"{wheel_name}_Rim", f"{wheel_name}_DriveHub"):
            if parents.get(by_name[moving_name]) != by_name[roll_name]:
                raise RuntimeError(f"{moving_name} must inherit {roll_name}")
        fixed_name = f"{wheel_name}_SteerKnuckle" if wheel_name in ("Wheel_FL", "Wheel_FR") else f"{wheel_name}_AxleEnd"
        if parents.get(by_name[fixed_name]) != by_name[wheel_name]:
            raise RuntimeError(f"{fixed_name} must not inherit tire roll")

    for side in ("L", "R"):
        flexible = nodes[by_name[f"SteerHydraulicHose_{side}_Flexible"]]
        nominal_length = float((flexible.get("extras") or {}).get("nominal_length_m", 0.0))
        if not 0.30 < nominal_length < 0.80:
            raise RuntimeError(f"SteerHydraulicHose_{side} nominal moving-leg length drift: {nominal_length}")

    if parents.get(by_name["PowertrackBend"]) != parents.get(by_name["PowertrackMovingRun"]):
        raise RuntimeError("Powertrack bend and moving run must inherit the same telescope stage")

    powertrack_extras = nodes[by_name["Powertrack"]].get("extras") or {}
    expected_powertrack_extras = {
        "display_link_count_is_physical_claim": False,
        "display_link_length_m": POWERTRACK_LINK_LENGTH_M,
        "display_link_pitch_m": POWERTRACK_LINK_PITCH_M,
        "base_display_sample_count": POWERTRACK_BASE_DISPLAY_COUNT,
        "moving_display_sample_count": POWERTRACK_MOVING_DISPLAY_COUNT,
    }
    for key, expected in expected_powertrack_extras.items():
        actual = powertrack_extras.get(key)
        if isinstance(expected, float):
            if not close(float(actual), expected, 0.0005):
                raise RuntimeError(f"Powertrack {key} drift: {actual!r} != {expected!r}")
        elif actual != expected:
            raise RuntimeError(f"Powertrack {key} drift: {actual!r} != {expected!r}")

    maximum_powertrack_gap = 0.0
    for prefix, count in (
        ("PowertrackBaseDisplayLink", POWERTRACK_BASE_DISPLAY_COUNT),
        ("PowertrackMovingDisplayLink", POWERTRACK_MOVING_DISPLAY_COUNT),
    ):
        for link_index in range(1, count):
            left_name = f"{prefix}_{link_index:02d}"
            right_name = f"{prefix}_{link_index + 1:02d}"
            if left_name not in by_name or right_name not in by_name:
                raise RuntimeError(f"Missing powertrack display neighbor: {left_name} -> {right_name}")
            left_min, left_max = mesh_world_aabb(document, blob, nodes, parents, by_name[left_name])
            right_min, right_max = mesh_world_aabb(document, blob, nodes, parents, by_name[right_name])
            axis_gap = [
                max(left_min[axis] - right_max[axis], right_min[axis] - left_max[axis], 0.0)
                for axis in range(3)
            ]
            maximum_powertrack_gap = max(maximum_powertrack_gap, *axis_gap)
            if any(value > POWERTRACK_MAX_VISIBLE_GAP_M for value in axis_gap):
                raise RuntimeError(
                    f"Disconnected powertrack display neighbors: {left_name} -> {right_name}; "
                    f"axis gap={[round(value, 4) for value in axis_gap]}"
                )

    base_end_name = f"PowertrackBaseDisplayLink_{POWERTRACK_BASE_DISPLAY_COUNT:02d}"
    base_end_max = mesh_world_aabb(document, blob, nodes, parents, by_name[base_end_name])[1][0]
    moving_start_min = mesh_world_aabb(
        document, blob, nodes, parents, by_name["PowertrackMovingDisplayLink_01"]
    )[0][0]
    full_travel_run_gap = max(0.0, moving_start_min + TELESCOPE_MID_TRAVEL_M - base_end_max)
    if full_travel_run_gap > POWERTRACK_MAX_VISIBLE_GAP_M:
        raise RuntimeError(f"Powertrack sampled runs separate at full visual travel: {full_travel_run_gap:.4f} m")

    materials = {material.get("name") for material in document.get("materials", [])}
    required_system_materials = {
        "JLG_Hydraulic_Black", "JLG_Electrical_Loom", "JLG_Control_Cable",
        "JLG_Wire_Rope", "JLG_Powertrack_Carrier",
    }
    if not required_system_materials.issubset(materials):
        raise RuntimeError(f"Visible-system material taxonomy drift: {sorted(required_system_materials - materials)}")

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

    platform_leveling_max_error_degrees = 0.0
    for boom_degrees in (0.0, 36.0, 72.0):
        posed_nodes = [dict(node) for node in nodes]
        posed_nodes[by_name["BoomPivot"]]["rotation"] = qz(math.radians(boom_degrees))
        posed_nodes[by_name["PlatformPivot"]]["rotation"] = qz(math.radians(-boom_degrees))
        deck_rotation = world_trs(posed_nodes, parents, by_name["PlatformDeck"])[1]
        deck_up = qrot(deck_rotation, (0.0, 1.0, 0.0))
        deck_up_length = math.sqrt(sum(value * value for value in deck_up))
        up_alignment = max(-1.0, min(1.0, deck_up[1] / max(deck_up_length, 1e-9)))
        level_error_degrees = math.degrees(math.acos(up_alignment))
        platform_leveling_max_error_degrees = max(platform_leveling_max_error_degrees, level_error_degrees)
        if level_error_degrees > 0.05:
            raise RuntimeError(
                f"Platform leveling drift at boom {boom_degrees:.0f} degrees: {level_error_degrees:.4f} degrees"
            )

    main_min, main_max = mesh_world_aabb(document, blob, nodes, parents, by_name["BaseBoomShell"])
    mid_min, mid_max = mesh_world_aabb(document, blob, nodes, parents, by_name["MidBoomShell"])
    fly_min, _ = mesh_world_aabb(document, blob, nodes, parents, by_name["FlyBoomShell"])
    overlap_stowed = main_max[0] - mid_min[0]
    mid_overlap_100 = main_max[0] - (mid_min[0] + TELESCOPE_MID_TRAVEL_M)
    fly_overlap_stowed = mid_max[0] - fly_min[0]
    fly_overlap_100 = fly_overlap_stowed - TELESCOPE_FLY_TRAVEL_M
    overlap_100 = min(mid_overlap_100, fly_overlap_100)
    if overlap_100 <= 0.001:
        raise RuntimeError(
            f"Coupled telescope separates at 100% travel: mid={mid_overlap_100:.4f}, "
            f"fly={fly_overlap_100:.4f}"
        )

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
        "validated_chassis_attachments": len(ACCESSORY_ATTACHMENTS),
        "powertrack_max_neighbor_gap_m": round(maximum_powertrack_gap, 4),
        "platform_leveling_max_error_degrees": round(platform_leveling_max_error_degrees, 4),
        "powertrack_full_travel_run_gap_m": round(full_travel_run_gap, 4),
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
        "telescope_mid_travel_m": TELESCOPE_MID_TRAVEL_M,
        "telescope_fly_travel_m": TELESCOPE_FLY_TRAVEL_M,
        "telescope_mid_overlap_at_100_m": round(mid_overlap_100, 4),
        "telescope_fly_overlap_at_100_m": round(fly_overlap_100, 4),
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
