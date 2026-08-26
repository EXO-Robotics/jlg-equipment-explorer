#!/usr/bin/env python3
"""Portable posed-GLB gate for the committed 742 binary.

This gate uses only the Python standard library plus the production Node solver
bridge. It parses the actual committed GLB, verifies that its named mesh rigs
encode the solver's neutral endpoints, applies the production pose output to
those exact nodes, and measures the same presentation endpoints as the Blender
companion gate. Blender remains a separately pinned CI/authoring check.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb, positions


ROOT = Path(__file__).resolve().parents[1]
GLB = ROOT / "assets/models/742.glb"
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text(encoding="utf-8"))
MECHANISM = json.loads((ROOT / "machines/742/mechanism.json").read_text(encoding="utf-8"))
EXPECTED_ASSET_PATH = "assets/models/742.glb"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
BEAM_ENDPOINT_TOLERANCE_M = 2e-6
POINT_POSITION_TOLERANCE_M = 1e-9
NEUTRAL_FLOAT32_POSITION_TOLERANCE_M = 2e-6
MESH_AXIS_TOLERANCE_M = 2e-6
HOSE_TUBE_CLEARANCE_M = 0.005
PORTABLE_RENDER_LABEL_TOLERANCE_M = 2e-6
PORTABLE_HOSE_CHORD_TOLERANCE_DEGREES = 0.002

UNDERBODY_NODES = (
    "FrontDifferential", "RearDifferential", "FrontAxle", "RearAxle",
    "FrontAxleTubeLeft", "FrontAxleTubeRight", "RearAxleTubeLeft", "RearAxleTubeRight",
    "FrontPinionFlange", "RearPinionFlange", "BellyPan",
    "FrontSteerCylinderBarrel", "RearSteerCylinderBarrel",
    "FrontSteerBarLeft", "FrontSteerBarRight", "RearSteerBarLeft", "RearSteerBarRight",
)


def identity() -> list[list[float]]:
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def matmul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [[sum(left[row][inner] * right[inner][column] for inner in range(4))
             for column in range(4)] for row in range(4)]


def transform(matrix: list[list[float]], point: tuple[float, float, float]) -> tuple[float, float, float]:
    value = (*point, 1.0)
    return tuple(sum(matrix[row][column] * value[column] for column in range(4)) for row in range(3))


def translation_matrix(value: tuple[float, float, float]) -> list[list[float]]:
    result = identity()
    for axis in range(3):
        result[axis][3] = value[axis]
    return result


def rotation_x(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[1, 0, 0, 0], [0, cosine, -sine, 0], [0, sine, cosine, 0], [0, 0, 0, 1]]


def rotation_y(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, 0, sine, 0], [0, 1, 0, 0], [-sine, 0, cosine, 0], [0, 0, 0, 1]]


def rotation_z(angle: float) -> list[list[float]]:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, -sine, 0, 0], [sine, cosine, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def quaternion_matrix(value: list[float]) -> list[list[float]]:
    x, y, z, w = value
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length <= 0:
        raise RuntimeError("742 GLB contains a zero-length node quaternion")
    x, y, z, w = (component / length for component in (x, y, z, w))
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0],
        [0, 0, 0, 1],
    ]


def gltf_trs(node: dict) -> list[list[float]]:
    if "matrix" in node:
        raise RuntimeError(f"742 portable gate does not accept matrix-authored node transforms: {node.get('name')}")
    translation = tuple(node.get("translation") or (0.0, 0.0, 0.0))
    rotation = quaternion_matrix(node.get("rotation") or [0.0, 0.0, 0.0, 1.0])
    scale = tuple(node.get("scale") or (1.0, 1.0, 1.0))
    scale_matrix = identity()
    for axis in range(3):
        scale_matrix[axis][axis] = scale[axis]
    return matmul(translation_matrix(translation), matmul(rotation, scale_matrix))


# The production solver and imported Blender rig use X-forward, Y-up, Z-lateral
# coordinates below the exporter conversion root. glTF stores those local
# coordinates as (X, Z, -Y).
SOLVER_TO_GLTF = [[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]]
GLTF_TO_SOLVER = [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]
SOLVER_TO_BLENDER_WORLD = GLTF_TO_SOLVER


def solver_local_matrix(node: dict) -> list[list[float]]:
    return matmul(GLTF_TO_SOLVER, matmul(gltf_trs(node), SOLVER_TO_GLTF))


def solver_mesh_point(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return transform(GLTF_TO_SOLVER, point)


def distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((left[axis] - right[axis]) ** 2 for axis in range(3)))


def subtract(left: tuple[float, float, float], right: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(left[axis] - right[axis] for axis in range(3))


def normalize(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(sum(component * component for component in value))
    if length < 1e-9:
        raise RuntimeError("742 solver emitted a collapsed beam")
    return tuple(component / length for component in value)


def rotation_from_z(direction: tuple[float, float, float]) -> list[list[float]]:
    target = normalize(direction)
    cosine = max(-1.0, min(1.0, target[2]))
    if cosine < -1 + 1e-12:
        return rotation_x(math.pi)
    cross = (-target[1], target[0], 0.0)
    sine = math.sqrt(sum(component * component for component in cross))
    if sine < 1e-12:
        return identity()
    axis = tuple(component / sine for component in cross)
    x, y, z = axis
    one_minus = 1 - cosine
    return [
        [cosine + x * x * one_minus, x * y * one_minus - z * sine, x * z * one_minus + y * sine, 0],
        [y * x * one_minus + z * sine, cosine + y * y * one_minus, y * z * one_minus - x * sine, 0],
        [z * x * one_minus - y * sine, z * y * one_minus + x * sine, cosine + z * z * one_minus, 0],
        [0, 0, 0, 1],
    ]


def beam_matrix(endpoints: list[list[float]], authored_length: float) -> list[list[float]]:
    start, end = (tuple(point) for point in endpoints)
    direction = subtract(end, start)
    length = distance(start, end)
    rotation = rotation_from_z(direction)
    scale = identity()
    scale[2][2] = length / authored_length
    midpoint = tuple((start[axis] + end[axis]) / 2 for axis in range(3))
    return matmul(translation_matrix(midpoint), matmul(rotation, scale))


def local_beam_endpoints(matrix: list[list[float]], authored_length: float) -> list[tuple[float, float, float]]:
    return [transform(matrix, (0.0, 0.0, -authored_length / 2)),
            transform(matrix, (0.0, 0.0, authored_length / 2))]


def endpoint_pair_error(actual: list[tuple[float, float, float]], expected: list[list[float]]) -> float:
    direct = max(distance(actual[index], tuple(expected[index])) for index in (0, 1))
    reverse = max(distance(actual[index], tuple(expected[1 - index])) for index in (0, 1))
    return min(direct, reverse)


def dot(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sum(left[axis] * right[axis] for axis in range(3))


def segment_distance(
    first: list[tuple[float, float, float]], second: list[tuple[float, float, float]]
) -> float:
    """Return the exact closest distance between two finite 3D segments."""
    p0, p1 = first
    q0, q1 = second
    u, v, w = subtract(p1, p0), subtract(q1, q0), subtract(p0, q0)
    a, b, c = dot(u, u), dot(u, v), dot(v, v)
    d, e = dot(u, w), dot(v, w)
    denominator = a * c - b * b
    epsilon = 1e-14
    if denominator < epsilon:
        s_numerator, s_denominator = 0.0, 1.0
        t_numerator, t_denominator = e, c
    else:
        s_numerator, s_denominator = b * e - c * d, denominator
        t_numerator, t_denominator = a * e - b * d, denominator
        if s_numerator < 0:
            s_numerator, t_numerator, t_denominator = 0.0, e, c
        elif s_numerator > s_denominator:
            s_numerator, t_numerator, t_denominator = s_denominator, e + b, c
    if t_numerator < 0:
        t_numerator = 0.0
        if -d < 0:
            s_numerator = 0.0
        elif -d > a:
            s_numerator = s_denominator
        else:
            s_numerator, s_denominator = -d, a
    elif t_numerator > t_denominator:
        t_numerator = t_denominator
        if -d + b < 0:
            s_numerator = 0.0
        elif -d + b > a:
            s_numerator = s_denominator
        else:
            s_numerator, s_denominator = -d + b, a
    s = 0.0 if abs(s_numerator) < epsilon else s_numerator / s_denominator
    t = 0.0 if abs(t_numerator) < epsilon else t_numerator / t_denominator
    separation = tuple(w[axis] + s * u[axis] - t * v[axis] for axis in range(3))
    return math.sqrt(dot(separation, separation))


class PortablePoseGate:
    def __init__(self) -> None:
        self.document, self.blob = load_glb(GLB)
        self.nodes = self.document.get("nodes") or []
        self.by_name, self.parents = index_nodes(self.nodes)
        self.mesh_points: dict[str, list[tuple[float, float, float]]] = {}
        for name, index in self.by_name.items():
            node = self.nodes[index]
            if "mesh" not in node:
                continue
            raw = []
            for primitive in self.document["meshes"][node["mesh"]]["primitives"]:
                raw.extend(positions(self.document, self.blob, primitive["attributes"]["POSITION"]))
            self.mesh_points[name] = [solver_mesh_point(point) for point in raw]
        self.base_local = [solver_local_matrix(node) for node in self.nodes]
        root = self.by_name.get("742_ROOT")
        if root is None:
            raise RuntimeError("742 portable posed gate cannot find 742_ROOT")
        # Blender's glTF exporter adds a conversion transform at this root. The
        # production rig and solver both operate below it in the source basis;
        # world measurements apply GLTF_TO_SOLVER once in world_vertices().
        self.base_local[root] = identity()
        self.local = []
        self.world_cache: dict[int, list[list[float]]] = {}

    def solve(self, request: dict) -> dict:
        completed = subprocess.run(
            ["node", str(ROOT / "scripts/solve_742_pose.mjs"), json.dumps(request)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        if completed.returncode:
            raise RuntimeError(f"742 production solver bridge failed\n{completed.stdout}{completed.stderr}")
        result = json.loads(completed.stdout)
        if set(result or {}) != {"state", "geometry", "mechanism"}:
            raise RuntimeError("742 production solver pose schema drift")
        return result

    def node(self, name: str) -> tuple[int, dict]:
        if name not in self.by_name:
            raise RuntimeError(f"742 portable posed gate cannot find {name}")
        index = self.by_name[name]
        return index, self.nodes[index]

    def authored_length(self, name: str) -> float:
        _, node = self.node(name)
        value = (node.get("extras") or {}).get("authored_length_m")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            raise RuntimeError(f"742 GLB node lacks positive authored_length_m: {name}")
        return float(value)

    def verify_mesh_rig_axis(self, name: str) -> None:
        _, node = self.node(name)
        if (node.get("extras") or {}).get("rig_axis") != "local_y_after_gltf_export":
            raise RuntimeError(f"742 GLB beam rig-axis metadata drift: {name}")
        points = self.mesh_points.get(name) or []
        if not points:
            raise RuntimeError(f"742 GLB beam has no committed mesh positions: {name}")
        authored = self.authored_length(name)
        minimum = min(point[2] for point in points)
        maximum = max(point[2] for point in points)
        if abs(minimum + authored / 2) > MESH_AXIS_TOLERANCE_M or abs(maximum - authored / 2) > MESH_AXIS_TOLERANCE_M:
            raise RuntimeError(f"742 GLB beam mesh axis/length disagrees with authored contract: {name}")

    def reset(self) -> None:
        self.local = [[row[:] for row in matrix] for matrix in self.base_local]
        self.world_cache = {}

    def set_axis_rotation(self, name: str, matrix: list[list[float]]) -> None:
        index, _ = self.node(name)
        translation = tuple(self.local[index][axis][3] for axis in range(3))
        self.local[index] = matmul(translation_matrix(translation), matrix)

    def set_translation(self, name: str, point: list[float] | tuple[float, float, float]) -> None:
        index, _ = self.node(name)
        for axis in range(3):
            self.local[index][axis][3] = point[axis]

    def apply(self, pose: dict) -> None:
        self.reset()
        state = pose["state"]
        self.set_axis_rotation("BoomLiftPivot", rotation_z(state["boomAngle"]))
        mid_index, _ = self.node("BoomMid")
        fly_index, _ = self.node("BoomFly")
        self.local[mid_index][0][3] = 0.12 + state["midTranslation"]
        self.local[fly_index][0][3] = 0.12 + state["flyTranslation"]
        self.set_axis_rotation("CarriageTiltPivot", rotation_z(state["carriageAngle"]))
        self.set_axis_rotation("FrameLevelPivot", rotation_x(state["frameAngle"]))
        for corner, angle in state["wheelAngles"].items():
            self.set_axis_rotation(f"SteerPivot_{corner}", rotation_y(angle))
        for name, endpoints in pose["geometry"]["beams"].items():
            index, _ = self.node(name)
            self.local[index] = beam_matrix(endpoints, self.authored_length(name))
        for name, point in pose["geometry"]["points"].items():
            self.set_translation(name, point)
        self.world_cache = {}

    def world_matrix(self, index: int) -> list[list[float]]:
        if index in self.world_cache:
            return self.world_cache[index]
        parent = self.parents.get(index)
        value = self.local[index] if parent is None else matmul(self.world_matrix(parent), self.local[index])
        self.world_cache[index] = value
        return value

    def world_vertices(self, name: str) -> list[tuple[float, float, float]]:
        index, _ = self.node(name)
        matrix = matmul(SOLVER_TO_BLENDER_WORLD, self.world_matrix(index))
        return [transform(matrix, point) for point in self.mesh_points.get(name) or []]

    def posed_beam_endpoints(self, name: str) -> list[tuple[float, float, float]]:
        index, _ = self.node(name)
        return local_beam_endpoints(self.local[index], self.authored_length(name))

    def pose_contract(self, pose: dict) -> dict:
        self.apply(pose)
        beam_error = max(
            endpoint_pair_error(self.posed_beam_endpoints(name), endpoints)
            for name, endpoints in pose["geometry"]["beams"].items()
        )
        point_error = max(
            distance(tuple(self.local[self.by_name[name]][axis][3] for axis in range(3)), tuple(point))
            for name, point in pose["geometry"]["points"].items()
        )
        hose_groups: dict[str, list[str]] = {}
        for name in pose["geometry"]["beams"]:
            if name.startswith(("LiftHose_", "BoomHose_")):
                prefix, separator, segment = name.rpartition("_")
                if not separator or not segment.isdigit():
                    raise RuntimeError(f"742 solver emitted a malformed hose segment name: {name}")
                hose_groups.setdefault(prefix, []).append(name)
        for names in hose_groups.values():
            names.sort(key=lambda name: int(name.rpartition("_")[2]))
        hose_totals = {
            prefix: sum(distance(*self.posed_beam_endpoints(name)) for name in names)
            for prefix, names in sorted(hose_groups.items())
        }
        steering = {name: distance(*self.posed_beam_endpoints(name))
                    for name in ("FrontSteerBarLeft", "FrontSteerBarRight",
                                 "RearSteerBarLeft", "RearSteerBarRight")}
        tube_names = sorted(name for name in self.by_name if name.startswith("BoomRigidTube_"))
        if not tube_names:
            raise RuntimeError("742 committed GLB has no named rigid boom tubes")
        tubes = [self.posed_beam_endpoints(name) for name in tube_names]
        minimum_clearance = float("inf")
        maximum_direction_change = 0.0
        boom_hose_names = sorted(name for names in hose_groups.values() for name in names if name.startswith("BoomHose_"))
        if not boom_hose_names:
            raise RuntimeError("742 solver emitted no boom-hose segments")
        for prefix, names in hose_groups.items():
            if not prefix.startswith("BoomHose_"):
                continue
            segments = [self.posed_beam_endpoints(name) for name in names]
            for before, after in zip(segments, segments[1:]):
                before_direction = subtract(before[1], before[0])
                after_direction = subtract(after[1], after[0])
                cosine = max(-1.0, min(1.0, dot(before_direction, after_direction) /
                                       math.sqrt(dot(before_direction, before_direction) * dot(after_direction, after_direction))))
                maximum_direction_change = max(maximum_direction_change, math.degrees(math.acos(cosine)))
            for segment in segments:
                for tube in tubes:
                    minimum_clearance = min(minimum_clearance, segment_distance(segment, tube) - 0.025)
        return {
            "maximum_beam_endpoint_error_m": beam_error,
            "maximum_point_position_error_m": point_error,
            "hose_total_lengths_m": hose_totals,
            "steering_bar_lengths_m": steering,
            "minimum_boom_hose_to_rigid_tube_surface_clearance_m": minimum_clearance,
            "maximum_boom_hose_adjacent_direction_change_degrees": maximum_direction_change,
        }

    def fork_measurement(self) -> dict:
        points = [point for name in ("ForkL", "ForkR") for point in self.world_vertices(name)]
        fork_index, _ = self.node("ForkL")
        matrix = matmul(SOLVER_TO_BLENDER_WORLD, self.world_matrix(fork_index))
        direction = tuple(matrix[axis][0] for axis in range(3))
        return {
            "heel_x_m": min(point[0] for point in points),
            "tip_x_m": max(point[0] for point in points),
            "bottom_m": min(point[2] for point in points),
            "load_surface_m": max(point[2] for point in points),
            "pitch_degrees": math.degrees(math.atan2(direction[2], direction[0])),
        }

    def minimum_named_clearance(self, names: tuple[str, ...]) -> tuple[float, str]:
        values = [(point[2], name) for name in names for point in self.world_vertices(name)]
        return min(values)

    def plane_radius(self, center: tuple[float, float, float], names: list[str]) -> float:
        return max(math.hypot(point[0] - center[0], point[1] - center[1])
                   for name in names for point in self.world_vertices(name))


def validate_neutral_binary_contract(gate: PortablePoseGate, neutral: dict) -> dict:
    beam_errors = {}
    for name, endpoints in neutral["geometry"]["beams"].items():
        gate.verify_mesh_rig_axis(name)
        index, _ = gate.node(name)
        beam_errors[name] = endpoint_pair_error(
            local_beam_endpoints(gate.base_local[index], gate.authored_length(name)), endpoints
        )
    point_errors = {}
    for name, point in neutral["geometry"]["points"].items():
        index, _ = gate.node(name)
        actual = tuple(gate.base_local[index][axis][3] for axis in range(3))
        point_errors[name] = distance(actual, tuple(point))
    maximum_beam = max(beam_errors.values())
    maximum_point = max(point_errors.values())
    if maximum_beam > BEAM_ENDPOINT_TOLERANCE_M or maximum_point > NEUTRAL_FLOAT32_POSITION_TOLERANCE_M:
        raise RuntimeError(
            f"742 committed GLB neutral rig disagrees with production solver: beam={maximum_beam}, point={maximum_point}"
        )
    return {
        "beams_checked": len(beam_errors),
        "points_checked": len(point_errors),
        "maximum_neutral_beam_endpoint_error_m": maximum_beam,
        "maximum_neutral_point_position_error_m": maximum_point,
    }


def main() -> None:
    if CONFIG.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 portable posed gate configuration identity drift")
    gate = PortablePoseGate()
    failures: list[str] = []
    neutral = gate.solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0, "level": 0, "steerMode": "circle"})
    neutral_binary = validate_neutral_binary_contract(gate, neutral)
    pose_contracts = {"stow": gate.pose_contract(neutral)}
    front_tire_names = [name for name in gate.by_name if name.startswith(("Tire_FL", "Tire_FR", "Tread_FL_", "Tread_FR_"))]
    front_tire_plane = max(point[0] for name in front_tire_names for point in gate.world_vertices(name))
    underbody_clearance, underbody_node = gate.minimum_named_clearance(UNDERBODY_NODES)
    stow = gate.fork_measurement()
    if stow["bottom_m"] > 0.35:
        failures.append("actual committed GLB stowed fork bottom exceeds 0.35 m")

    level_clearances = []
    for index in range(41):
        level = -1 + index / 20
        pose = gate.solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
                           "level": level, "steerMode": "circle"})
        contract = gate.pose_contract(pose)
        clearance, node = gate.minimum_named_clearance(UNDERBODY_NODES)
        level_clearances.append({"level_fraction": level, "clearance_m": clearance, "limiting_node": node})
        if contract["maximum_beam_endpoint_error_m"] > BEAM_ENDPOINT_TOLERANCE_M:
            failures.append("portable posed GLB beam endpoints drifted while frame-leveling")
    level_minimum = min(level_clearances, key=lambda item: item["clearance_m"])
    published_clearance = MECHANISM["collision_proxies"]["minimum_rigid_underbody_clearance_m"]
    if level_minimum["clearance_m"] + 1e-6 < published_clearance:
        failures.append("actual committed GLB rigid underbody misses clearance during frame leveling")

    maximum_lift_pose = gate.solve({"lift": 1, "telescope": 1, "tilt": 0, "steer": 0,
                                    "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_lift"] = gate.pose_contract(maximum_lift_pose)
    maximum_lift = gate.fork_measurement()
    if abs(maximum_lift["load_surface_m"] - CONFIG["published_performance"]["maximum_lift_height_m"]) > 0.02:
        failures.append("actual committed GLB maximum-lift fork surface misses published height")
    if abs(maximum_lift["pitch_degrees"]) > 0.1:
        failures.append("actual committed GLB forks are not level at maximum lift")

    maximum_reach_pose = gate.solve({"lift": 3 / 69, "telescope": 1, "tilt": 0, "steer": 0,
                                     "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_reach"] = gate.pose_contract(maximum_reach_pose)
    maximum_reach = gate.fork_measurement()
    forward_reach = maximum_reach["heel_x_m"] + 0.6096 - front_tire_plane
    maximum_reach.update({"load_center_m": 0.6096, "forward_reach_m": forward_reach})
    if abs(forward_reach - CONFIG["published_performance"]["maximum_forward_reach_m"]) > 0.02:
        failures.append("actual committed GLB 24-inch load-center reach misses published reach")
    if abs(maximum_reach["pitch_degrees"]) > 0.1:
        failures.append("actual committed GLB forks are not level at selected reach pose")

    proof = MECHANISM["validated_actual_glb_measurements"]
    if (abs(maximum_lift["load_surface_m"] - proof["maximum_lift_fork_load_surface_m"]) > PORTABLE_RENDER_LABEL_TOLERANCE_M
            or abs(front_tire_plane - proof["maximum_reach_front_tire_tread_plane_x_m"]) > PORTABLE_RENDER_LABEL_TOLERANCE_M
            or abs(maximum_reach["heel_x_m"] + 0.6096 - proof["maximum_reach_24in_load_center_x_m"]) > PORTABLE_RENDER_LABEL_TOLERANCE_M
            or abs(forward_reach - proof["maximum_reach_m"]) > PORTABLE_RENDER_LABEL_TOLERANCE_M):
        failures.append("actual committed GLB measurements drifted from render-proof labels")

    circle_pose = gate.solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                              "level": 0, "steerMode": "circle"})
    pose_contracts["maximum_circle"] = gate.pose_contract(circle_pose)
    inner = max(abs(value) for value in circle_pose["state"]["wheelAngles"].values())
    steering_contract = MECHANISM["steering"]
    center_lateral = (steering_contract["wheel_center_track_m"] / 2
                      + (steering_contract["wheelbase_m"] / 2) / math.tan(inner))
    turn_center = (0.0, -center_lateral, 0.0)
    tire_names = [name for name in gate.by_name if name.startswith(("Tire_", "Tread_"))]
    visible_names = [name for name in gate.mesh_points if not (gate.nodes[gate.by_name[name]].get("extras") or {}).get("is_hit_volume")]
    body_names = [name for name in visible_names if name not in tire_names]
    circle = {
        "inner_wheel_angle_degrees": math.degrees(inner),
        "reconstructed_turn_center_lateral_m": center_lateral,
        "actual_glb_tire_swept_radius_m": gate.plane_radius(turn_center, tire_names),
        "actual_glb_body_swept_radius_m": gate.plane_radius(turn_center, body_names),
        "published_outside_turning_radius_m": CONFIG["published_dimensions_m"]["outside_turning_radius"],
        "boundary": "published reference locus is unresolved; actual reconstructed envelopes are reported, not equated",
    }
    steering_acceptance = steering_contract["acceptance"]
    circle_degrees = math.degrees(inner)
    if (circle_degrees < steering_acceptance["minimum_circle_wheel_angle_degrees"]
            or circle_degrees > steering_contract["visual_inner_limit_degrees"] + 1e-6):
        failures.append("actual committed GLB circle steering misses useful reconstructed travel")

    crab_pose = gate.solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                            "level": 0, "steerMode": "crab"})
    pose_contracts["maximum_crab"] = gate.pose_contract(crab_pose)
    crab_angles = list(crab_pose["state"]["wheelAngles"].values())
    crab_spread = math.degrees(max(crab_angles) - min(crab_angles))
    crab_maximum = math.degrees(max(abs(value) for value in crab_angles))
    if (crab_spread > steering_acceptance["maximum_dense_crab_residual_toe_degrees"]
            or crab_maximum < steering_acceptance["minimum_crab_wheel_angle_degrees"]):
        failures.append("actual committed GLB crab steering misses travel/toe boundary")
    crab = {
        "wheel_angles_degrees": {name: math.degrees(value) for name, value in crab_pose["state"]["wheelAngles"].items()},
        "maximum_heading_spread_degrees": crab_spread,
        "maximum_wheel_angle_degrees": crab_maximum,
        "boundary": "same static linkage in every mode; residual toe measured, not factory crab calibration",
    }

    front_pose = gate.solve({"lift": 0, "telescope": 0, "tilt": 0, "steer": 1,
                             "level": 0, "steerMode": "front"})
    pose_contracts["maximum_front"] = gate.pose_contract(front_pose)
    front_inner = math.degrees(max(abs(front_pose["state"]["wheelAngles"][name]) for name in ("FL", "FR")))
    rear_heading = math.degrees(max(abs(front_pose["state"]["wheelAngles"][name]) for name in ("RL", "RR")))
    if (front_inner < steering_acceptance["minimum_front_wheel_angle_degrees"]
            or front_inner > steering_contract["visual_inner_limit_degrees"] + 1e-6
            or rear_heading > 1e-9):
        failures.append("actual committed GLB full-travel front-only steering semantics drifted")

    for name, contract in pose_contracts.items():
        if contract["maximum_beam_endpoint_error_m"] > BEAM_ENDPOINT_TOLERANCE_M or contract["maximum_point_position_error_m"] > POINT_POSITION_TOLERANCE_M:
            failures.append(f"portable committed-GLB endpoint contract drifted at {name}")
        if max(contract["steering_bar_lengths_m"].values()) - min(contract["steering_bar_lengths_m"].values()) > BEAM_ENDPOINT_TOLERANCE_M:
            failures.append(f"actual committed GLB steering bars disagree at {name}")
        if contract["minimum_boom_hose_to_rigid_tube_surface_clearance_m"] < HOSE_TUBE_CLEARANCE_M:
            failures.append(f"actual committed GLB boom hose intersects rigid tube at {name}")
        if (contract["maximum_boom_hose_adjacent_direction_change_degrees"]
                > MECHANISM["service_lines"]["maximum_adjacent_chord_angle_degrees"]
                + PORTABLE_HOSE_CHORD_TOLERANCE_DEGREES):
            failures.append(f"actual committed GLB boom hose bend continuity drifted at {name}")
        for hose_name, total in contract["hose_total_lengths_m"].items():
            expected = (MECHANISM["service_lines"]["lift_hose_total_length_m"] if hose_name.startswith("Lift")
                        else MECHANISM["service_lines"]["boom_intersection_hose_total_length_m"])
            if abs(total - expected) > BEAM_ENDPOINT_TOLERANCE_M:
                failures.append(f"actual committed GLB {hose_name} fixed centerline length drifted at {name}")

    output = {
        "status": "PASS" if not failures else "FAIL",
        "gate_kind": "portable_committed_glb_production_solver",
        "asset": EXPECTED_ASSET_PATH,
        "asset_sha256": hashlib.sha256(GLB.read_bytes()).hexdigest(),
        "configuration_id": EXPECTED_ID,
        "production_solver_bridge": "scripts/solve_742_pose.mjs",
        "parser": "scripts/validate_742_portable_posed_glb.py",
        "blender_companion": "scripts/run_742_posed_glb_gate.py",
        "named_presets_posed": ["stow_0deg", "maximum_lift_69deg", "maximum_reach_selected_3deg", "maximum_circle_steer", "maximum_crab_steer", "maximum_front_steer", "frame_level_dense_41"],
        "neutral_binary_contract": neutral_binary,
        "portable_render_label_tolerance_m": PORTABLE_RENDER_LABEL_TOLERANCE_M,
        "portable_hose_chord_tolerance_degrees": PORTABLE_HOSE_CHORD_TOLERANCE_DEGREES,
        "front_tire_tread_plane_x_m": front_tire_plane,
        "minimum_named_rigid_underbody_clearance_m": underbody_clearance,
        "neutral_clearance_limiting_node": underbody_node,
        "minimum_frame_level_clearance": level_minimum,
        "pose_contracts": pose_contracts,
        "stow": stow,
        "maximum_lift": maximum_lift,
        "maximum_reach": maximum_reach,
        "maximum_circle_steer": circle,
        "maximum_crab_steer": crab,
        "maximum_front_steer": {
            "wheel_angles_degrees": {name: math.degrees(value) for name, value in front_pose["state"]["wheelAngles"].items()},
            "maximum_front_wheel_angle_degrees": front_inner,
            "maximum_rear_wheel_angle_degrees": rear_heading,
            "boundary": "front rack uses full reconstructed travel while the rear rack remains aligned",
        },
        "failures": failures,
        "boundary": "Portable committed-binary pose verification; pinned Blender remains a distinct CI/authoring companion.",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise RuntimeError("; ".join(sorted(set(failures))))


if __name__ == "__main__":
    main()
