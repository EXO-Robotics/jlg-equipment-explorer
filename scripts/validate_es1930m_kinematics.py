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


def circle_intersection(
    anchor: tuple[float, float],
    center: tuple[float, float],
    anchor_radius: float,
    center_radius: float,
) -> tuple[float, float]:
    dx = center[0] - anchor[0]
    dy = center[1] - anchor[1]
    separation = math.hypot(dx, dy)
    if separation <= 0 or separation > anchor_radius + center_radius or separation < abs(anchor_radius - center_radius):
        raise RuntimeError("Reconstructed kicker/cylinder circles do not intersect")
    along = (anchor_radius**2 - center_radius**2 + separation**2) / (2 * separation)
    height = math.sqrt(max(anchor_radius**2 - along**2, 0.0))
    base_x = anchor[0] + along * dx / separation
    base_y = anchor[1] + along * dy / separation
    option_a = (base_x - height * dy / separation, base_y + height * dx / separation)
    option_b = (base_x + height * dy / separation, base_y - height * dx / separation)
    return max(option_a, option_b, key=lambda point: point[1])


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

    boundaries = []
    for boundary in range(level_count + 1):
        y = base_y + boundary * rise
        boundaries.append({
            "left": (-span / 2, y),
            "right": (span / 2, y),
        })

    levels = []
    for level in range(level_count):
        lower = boundaries[level]
        upper = boundaries[level + 1]
        levels.append({
            "a": (lower["left"], upper["right"]),
            "b": (lower["right"], upper["left"]),
            "center_a": ((lower["left"][0] + upper["right"][0]) / 2, (lower["left"][1] + upper["right"][1]) / 2),
            "center_b": ((lower["right"][0] + upper["left"][0]) / 2, (lower["right"][1] + upper["left"][1]) / 2),
        })

    cylinder = spec["lift_cylinder"]
    pin_distance = cylinder["reconstructed_closed_pin_distance_m"] + lift * cylinder["published_stroke_m"]
    lower_pin = tuple(cylinder["lower_pin_m"][:2])
    kicker_center = tuple(cylinder["kicker_pivot_m"][:2])
    upper_pin = circle_intersection(lower_pin, kicker_center, pin_distance, cylinder["kicker_pin_radius_m"])

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
    symmetry_epsilon = solver["symmetry_epsilon_m"]
    samples = [solve(spec, index / 100) for index in range(101)]

    max_link_error = 0.0
    max_closure_error = 0.0
    max_symmetry_error = 0.0
    max_translation_step = 0.0
    for state in samples:
        for level_index, level in enumerate(state["levels"]):
            for link_name in ("a", "b"):
                error = abs(distance(*level[link_name]) - arm_length)
                max_link_error = max(max_link_error, error)
            center_error = distance(level["center_a"], level["center_b"])
            max_closure_error = max(max_closure_error, center_error)
            symmetry_error = abs(level["center_a"][0] + level["center_b"][0])
            max_symmetry_error = max(max_symmetry_error, symmetry_error)
            if level_index:
                prior = state["levels"][level_index - 1]
                for side in ("left", "right"):
                    shared = state["boundaries"][level_index][side]
                    candidates = [point for link in (prior, level) for pair in (link["a"], link["b"]) for point in pair]
                    local_error = min(distance(shared, point) for point in candidates)
                    max_closure_error = max(max_closure_error, local_error)

    for prior, current in zip(samples, samples[1:]):
        for boundary_index in range(solver["level_count"] + 1):
            for side in ("left", "right"):
                step = distance(prior["boundaries"][boundary_index][side], current["boundaries"][boundary_index][side])
                max_translation_step = max(max_translation_step, step)
        max_translation_step = max(max_translation_step, distance(prior["cylinder_upper_pin"], current["cylinder_upper_pin"]))

    cylinder = spec["lift_cylinder"]
    observed_stroke = samples[-1]["cylinder_pin_distance"] - samples[0]["cylinder_pin_distance"]
    failures = []
    if max_link_error > link_epsilon:
        failures.append(f"link length error {max_link_error}")
    if max_closure_error > closure_epsilon:
        failures.append(f"shared pivot closure error {max_closure_error}")
    if max_symmetry_error > symmetry_epsilon:
        failures.append(f"symmetry error {max_symmetry_error}")
    if max_translation_step > solver["continuity_max_translation_per_0_01_sample_m"]:
        failures.append(f"continuity step {max_translation_step}")
    if abs(observed_stroke - cylinder["published_stroke_m"]) > 1e-9:
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
        "maximum_symmetry_error_m": max_symmetry_error,
        "maximum_translation_per_0_01_sample_m": max_translation_step,
        "cylinder_observed_stroke_m": observed_stroke,
        "outdoor_lift_ratio": outdoor_ratio,
        "stowed_span_m": samples[0]["span"],
        "indoor_raised_span_m": samples[-1]["span"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
