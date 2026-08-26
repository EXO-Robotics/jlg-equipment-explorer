#!/usr/bin/env python3
"""Sample the authored ES1930M mechanism and prove visual kinematic closure."""

from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "machines/es1930m/mechanism.json"


def distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.sqrt(sum((av - bv) ** 2 for av, bv in zip(a, b)))


def orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def proper_segment_intersection(first, second, epsilon=1e-10) -> bool:
    a, b = first
    c, d = second
    o1 = orientation(a, b, c)
    o2 = orientation(a, b, d)
    o3 = orientation(c, d, a)
    o4 = orientation(c, d, b)
    return o1 * o2 < -epsilon and o3 * o4 < -epsilon


def interpolate(a, b, amount):
    return tuple(a[index] + (b[index] - a[index]) * amount for index in range(len(a)))


def solve(spec: dict, lift: float) -> dict:
    solver = spec["solver"]
    level_count = solver["level_count"]
    arm_length = solver["arm_pin_center_length_m"]
    base_y = solver["base_pivot_height_m"]
    deck_offset = solver["deck_floor_offset_above_upper_pivots_m"]
    floor_y = solver["stowed_deck_floor_height_m"] + lift * (
        solver["indoor_deck_floor_height_m"] - solver["stowed_deck_floor_height_m"]
    )
    rise = (floor_y - base_y - deck_offset) / level_count
    if not 0 < rise < arm_length:
        raise RuntimeError(f"Lift {lift:.3f} is outside reconstructed arm geometry")
    span = math.sqrt(arm_length**2 - rise**2)

    front_x = spec["slides"]["front_fixed_x_m"]
    boundaries = []
    for boundary in range(level_count + 1):
        y = base_y + boundary * rise
        boundaries.append({
            "rear": (front_x - span, y),
            "front": (front_x, y),
        })

    levels = []
    for level in range(level_count):
        lower = boundaries[level]
        upper = boundaries[level + 1]
        levels.append({
            "a": (lower["rear"], upper["front"]),
            "b": (lower["front"], upper["rear"]),
            "center_a": ((lower["rear"][0] + upper["front"][0]) / 2, (lower["rear"][1] + upper["front"][1]) / 2),
            "center_b": ((lower["front"][0] + upper["rear"][0]) / 2, (lower["front"][1] + upper["rear"][1]) / 2),
        })

    cylinder = spec["lift_cylinder"]
    lower_pin = tuple(cylinder["reconstructed_lower_frame_pin_m"][:2])
    kicker_center = interpolate(levels[0]["b"][0], levels[0]["b"][1], cylinder["reconstructed_kicker_pivot_fraction_on_level01_b"])
    direction = ((levels[0]["b"][1][0] - levels[0]["b"][0][0]) / arm_length, (levels[0]["b"][1][1] - levels[0]["b"][0][1]) / arm_length)
    offset = cylinder["reconstructed_cylinder_pin_offset_link_frame_m"]
    upper_pin = (kicker_center[0] + direction[0] * offset[0] - direction[1] * offset[1], kicker_center[1] + direction[1] * offset[0] + direction[0] * offset[1])
    pin_distance = distance(lower_pin, upper_pin)

    return {
        "lift": lift,
        "floor_y": floor_y,
        "rise": rise,
        "span": span,
        "boundaries": boundaries,
        "levels": levels,
        "cylinder_lower_pin": lower_pin,
        "cylinder_upper_pin": upper_pin,
        "cylinder_pin_distance": pin_distance,
        "kicker_pivot": kicker_center,
    }


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    solver = spec["solver"]
    arm_length = solver["arm_pin_center_length_m"]
    closure_epsilon = solver["closure_epsilon_m"]
    link_epsilon = solver["link_length_epsilon_m"]
    samples = [solve(spec, index / 100) for index in range(101)]

    max_link_error = 0.0
    max_closure_error = 0.0
    max_front_anchor_error = 0.0
    max_translation_step = 0.0
    collision_assertions = 0
    failures = []
    collision = spec["collision_proxies"]
    for state in samples:
        for level_index, level in enumerate(state["levels"]):
            for link_name in ("a", "b"):
                error = abs(distance(*level[link_name]) - arm_length)
                max_link_error = max(max_link_error, error)
            center_error = distance(level["center_a"], level["center_b"])
            max_closure_error = max(max_closure_error, center_error)
            max_front_anchor_error = max(max_front_anchor_error, abs(state["boundaries"][level_index]["front"][0] - spec["slides"]["front_fixed_x_m"]))
            if level_index:
                prior = state["levels"][level_index - 1]
                for side in ("rear", "front"):
                    shared = state["boundaries"][level_index][side]
                    candidates = [point for link in (prior, level) for pair in (link["a"], link["b"]) for point in pair]
                    local_error = min(distance(shared, point) for point in candidates)
                    max_closure_error = max(max_closure_error, local_error)

        # A and B are expected to cross within one level, and neighboring levels
        # share end pivots. Any proper centerline crossing between non-adjacent
        # levels would indicate branch inversion or an impossible stack collision.
        for first_level in range(solver["level_count"]):
            for second_level in range(first_level + 2, solver["level_count"]):
                for first_branch in ("a", "b"):
                    for second_branch in ("a", "b"):
                        collision_assertions += 1
                        if proper_segment_intersection(
                            state["levels"][first_level][first_branch],
                            state["levels"][second_level][second_branch],
                        ):
                            failures.append(
                                f"non-adjacent link intersection at lift {state['lift']:.2f}: "
                                f"level {first_level + 1}{first_branch} / level {second_level + 1}{second_branch}"
                            )

        # Exclude the intended upper pin neighborhood, then require the arm body
        # plus half its authored section height to remain below the deck underside.
        deck_underside_y = state["floor_y"] - collision["platform_deck_thickness_m"]
        exclusion = collision["platform_joint_exclusion_fraction"]
        for branch in ("a", "b"):
            start, end = state["levels"][-1][branch]
            trimmed = interpolate(start, end, 1 - exclusion)
            collision_assertions += 1
            if trimmed[1] + collision["arm_section_height_m"] / 2 > deck_underside_y + 1e-9:
                failures.append(f"top arm body intersects platform proxy at lift {state['lift']:.2f}")

        # Both scissor planes and their authored lane offsets must remain inside
        # the published machine width, while the center-mounted cylinder retains
        # clearance from the nearest arm plane outside intentional pin hardware.
        half_arm_lateral = collision["arm_section_lateral_m"] / 2
        for plane in solver["lateral_planes_m"]:
            collision_assertions += 1
            if abs(plane) + abs(solver["crossing_arm_lane_offset_m"]) + half_arm_lateral > abs(collision["machine_lateral_bounds_m"][1]) + 1e-9:
                failures.append(f"scissor plane escapes machine width at lift {state['lift']:.2f}")
        nearest_arm_surface = min(abs(plane) for plane in solver["lateral_planes_m"]) - abs(solver["crossing_arm_lane_offset_m"]) - half_arm_lateral
        cylinder_surface = 0.035
        collision_assertions += 1
        if nearest_arm_surface - cylinder_surface < collision["minimum_cylinder_to_arm_plane_clearance_m"]:
            failures.append("center lift cylinder violates lateral scissor-plane clearance")

        # Pivot centerlines must remain within the frozen longitudinal envelope.
        for boundary in state["boundaries"]:
            for side in ("rear", "front"):
                collision_assertions += 1
                if not collision["machine_longitudinal_bounds_m"][0] <= boundary[side][0] <= collision["machine_longitudinal_bounds_m"][1]:
                    failures.append(f"pivot escapes longitudinal envelope at lift {state['lift']:.2f}")

    for prior, current in zip(samples, samples[1:]):
        for boundary_index in range(solver["level_count"] + 1):
            for side in ("rear", "front"):
                step = distance(prior["boundaries"][boundary_index][side], current["boundaries"][boundary_index][side])
                max_translation_step = max(max_translation_step, step)
        max_translation_step = max(max_translation_step, distance(prior["cylinder_upper_pin"], current["cylinder_upper_pin"]))

    cylinder = spec["lift_cylinder"]
    observed_stroke = samples[-1]["cylinder_pin_distance"] - samples[0]["cylinder_pin_distance"]
    if max_link_error > link_epsilon:
        failures.append(f"link length error {max_link_error}")
    if max_closure_error > closure_epsilon:
        failures.append(f"shared pivot closure error {max_closure_error}")
    if max_front_anchor_error > closure_epsilon:
        failures.append(f"front fixed-anchor drift {max_front_anchor_error}")
    if max_translation_step > solver["continuity_max_translation_per_0_01_sample_m"]:
        failures.append(f"continuity step {max_translation_step}")
    if abs(observed_stroke - cylinder["published_stroke_m"]) > cylinder["stroke_tolerance_m"]:
        failures.append(f"cylinder stroke {observed_stroke}")
    if any(current["rise"] <= prior["rise"] for prior, current in zip(samples, samples[1:])):
        failures.append("solver branch is not monotonically rising")
    if failures:
        raise RuntimeError("; ".join(failures))

    outdoor_ratio = (
        solver["outdoor_deck_floor_height_m"] - solver["stowed_deck_floor_height_m"]
    ) / (
        solver["indoor_deck_floor_height_m"] - solver["stowed_deck_floor_height_m"]
    )
    print(json.dumps({
        "status": "PASS",
        "configuration_id": spec["configuration_id"],
        "samples": len(samples),
        "levels": solver["level_count"],
        "maximum_link_length_error_m": max_link_error,
        "maximum_shared_pivot_error_m": max_closure_error,
        "maximum_front_fixed_anchor_error_m": max_front_anchor_error,
        "maximum_translation_per_0_01_sample_m": max_translation_step,
        "cylinder_observed_stroke_m": observed_stroke,
        "outdoor_lift_ratio": outdoor_ratio,
        "collision_proxy_assertions": collision_assertions,
        "collision_proxy_status": "PASS",
        "stowed_span_m": samples[0]["span"],
        "indoor_raised_span_m": samples[-1]["span"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
