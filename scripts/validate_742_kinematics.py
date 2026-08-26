#!/usr/bin/env python3
"""Validate the actual production 742 solver and posed-GLB rig contract.

The numerical work executes machines/742/solver.js through the Node bridge;
this Python gate deliberately owns no parallel articulation mathematics.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from validate_es1930m_glb import index_nodes, load_glb

ROOT = Path(__file__).resolve().parents[1]
MECH = json.loads((ROOT / "machines/742/mechanism.json").read_text())
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())
GLB = ROOT / "assets/models/742.glb"

DYNAMIC_PARENT = {
    "LiftCylinderBarrel": "LiftCylinder", "LiftCylinderRod": "LiftCylinder",
    "LiftHose_0_0": "LiftCylinder", "LiftHose_1_2": "LiftCylinder",
    "TelescopeCylinderBarrel": "BoomBase", "TelescopeCylinderRod": "BoomBase",
    "CompensationCylinderBarrel": "LiftCylinder", "CompensationCylinderRod": "LiftCylinder",
    "BoomHose_0_0": "BoomBase", "BoomHose_3_2": "BoomBase",
    "ExtendChain_L": "BoomBase", "RetractChain_C": "BoomBase",
    "RetractChain_C_Wrap": "BoomBase", "RetractChain_C_Moving": "BoomBase",
    "CarriageTiltCylinderBarrel": "BoomFly", "CarriageTiltCylinderRod": "BoomFly",
    "CarriageTiltLink": "BoomFly", "FrameLevelCylinderBarrel": "742_ROOT",
    "FrameLevelCylinderRod": "742_ROOT", "RearAxleStabilizerBarrel": "RearAxleStabilizerCylinder",
    "RearAxleStabilizerRod": "RearAxleStabilizerCylinder",
    "FrontSteerCylinderBarrel": "FrontSteerCylinder", "FrontSteerCylinderRodLeft": "FrontSteerCylinder",
    "FrontSteerCylinderRodRight": "FrontSteerCylinder", "FrontSteerBarLeft": "FrontSteerCylinder",
    "FrontSteerBarRight": "FrontSteerCylinder", "RearSteerCylinderBarrel": "RearSteerCylinder",
    "RearSteerCylinderRodLeft": "RearSteerCylinder", "RearSteerCylinderRodRight": "RearSteerCylinder",
    "RearSteerBarLeft": "RearSteerCylinder", "RearSteerBarRight": "RearSteerCylinder",
    "BoomAngleSensorLink": "LiftCylinder",
}
POINT_PARENT = {"BoomAngleSensorBoomJoint": "LiftCylinder"}


def validate_glb_hierarchy(failures: list[str]) -> None:
    document, _ = load_glb(GLB)
    nodes = document.get("nodes") or []
    by_name, parents = index_nodes(nodes)
    for name, expected_parent in DYNAMIC_PARENT.items():
        if name not in by_name:
            failures.append(f"posed GLB is missing {name}")
            continue
        parent_index = parents.get(by_name[name])
        actual_parent = nodes[parent_index].get("name") if parent_index is not None else None
        if actual_parent != expected_parent:
            failures.append(f"{name} parent is {actual_parent}, expected {expected_parent}")
        extras = nodes[by_name[name]].get("extras") or {}
        if extras.get("authored_length_m", 0) <= 0:
            failures.append(f"{name} lacks an authored-length rig contract")
    for name, expected_parent in POINT_PARENT.items():
        if name not in by_name:
            failures.append(f"posed GLB is missing {name}")
            continue
        parent_index = parents.get(by_name[name])
        actual_parent = nodes[parent_index].get("name") if parent_index is not None else None
        if actual_parent != expected_parent:
            failures.append(f"{name} parent is {actual_parent}, expected {expected_parent}")


def main() -> None:
    failures: list[str] = []
    validate_glb_hierarchy(failures)
    completed = subprocess.run(
        ["node", str(ROOT / "scripts/validate_742_solver.mjs")],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    if result["unique_multidimensional_state_samples"] != 416745:
        failures.append("dense multidimensional solver grid was not fully executed")
    if result["continuous_retract_chain_samples"] < 2001:
        failures.append("continuous retract-chain sweep is not dense enough")
    if result["minimum_retract_chain_segment_m"] < 0.15:
        failures.append("retract-chain route approached a collapsed segment")
    if result["minimum_retract_leg_vertical_separation_m"] < 0.15:
        failures.append("retract-chain legs approached a crossover")
    if result["maximum_retract_endpoint_step_m"] > 0.004:
        failures.append("retract-chain endpoint continuity exceeded the dense-step bound")
    if result["minimum_fork_blade_y_m"] < MECH["collision_proxies"]["minimum_fork_y_m"] - 1e-6:
        failures.append("fork blade crossed the flat-floor proxy")
    target_height = CONFIG["published_performance"]["maximum_lift_height_m"]
    if abs(result["maximum_level_fork_surface_y_m"] - target_height) > 0.05:
        failures.append("maximum level fork surface misses the published height")
    stow = result["stow"]
    acceptance = MECH["boom"]["runtime_stow"]["neutral_fork_surface_acceptance_m"]
    if not acceptance[0] <= stow["fork_load_surface_m"] <= acceptance[1]:
        failures.append("neutral stowed fork surface is outside its explicit acceptance band")
    stow_contract = MECH["boom"]["runtime_stow"]
    if abs(stow["total_length_rear_plane_to_fork_tip_m"] - stow_contract["exact_total_length_with_48in_forks_m"]) > stow_contract["total_length_tolerance_m"]:
        failures.append("runtime stow misses its exact rear-plane-to-fork-tip length contract")
    if abs(result["maximum_reach_pose"]["forward_reach_m"] - CONFIG["published_performance"]["maximum_forward_reach_m"]) > 0.02:
        failures.append("separate 3-degree maximum-reach pose misses the published reach")
    if result["maximum_ackermann_center_error_m"] > 1e-9:
        failures.append("reconstructed Ackermann axes do not share one center")
    steering = result["steering_linkage"]
    if steering["minimum_straight_rod_length_m"] <= 0.10 or steering["minimum_steering_bar_length_m"] <= 0.10:
        failures.append("steering rod/bar topology approached a collapsed link")
    if steering["maximum_rod_bar_closure_error_m"] > 1e-12:
        failures.append("steering rod/bar joint lost endpoint closure")
    strokes = MECH["hydraulic_cylinder_strokes_m"]
    expected = {"lift": strokes["lift"], "telescope": strokes["telescope"],
                "compensation": strokes["compensation_master"], "carriageTilt": strokes["head_tilt_slave"],
                "frameLevel": strokes["frame_sway"]}
    for name, target in expected.items():
        actual = result["cylinder_ranges"][name]["stroke_usage_m"]
        if abs(actual - target) > 0.002:
            failures.append(f"{name} pin-distance usage {actual:.6f} m misses evidence stroke {target:.6f} m")
    for name, measurements in result["cylinder_ranges"].items():
        barrel_range = measurements["fixed_barrel_length_range_m"]
        if barrel_range[1] - barrel_range[0] > 1e-12:
            failures.append(f"{name} barrel changes length")
        if measurements["minimum_rod_exposure_m"] <= 0:
            failures.append(f"{name} rod has non-positive exposure")
    for path in (ROOT / "scripts/build_742.py", ROOT / "scripts/render_742_preview.py"):
        if "solve_742_pose.mjs" not in path.read_text():
            failures.append(f"{path.name} does not execute the production solver bridge")
    if failures:
        raise RuntimeError("; ".join(sorted(set(failures))))
    result.update({
        "configuration_id": CONFIG["configuration_id"],
        "dynamic_hierarchy_nodes_checked": sorted(DYNAMIC_PARENT),
        "dynamic_point_nodes_checked": sorted(POINT_PARENT),
        "rear_axle_stabilization_published_stroke_m": strokes["rear_axle_stabilization"],
        "rear_axle_stabilization_usage_boundary": "only frame-level-induced endpoint travel is shown; free/slow/locked RAS behavior is not simulated",
    })
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
