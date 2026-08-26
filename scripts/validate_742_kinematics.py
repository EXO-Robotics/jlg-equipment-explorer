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

from validate_es1930m_glb import index_nodes, load_glb, node_bounds

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
    "BoomAngleSensorCrank": "LiftCylinder", "BoomAngleSensorLink": "LiftCylinder",
    **{name: "BoomBase" for prefix in ("ExtendChain_L", "ExtendChain_R", "RetractChain_C")
       for name in ([prefix, f"{prefix}_Wrap"] + [f"{prefix}_Wrap_{index}" for index in range(1, 8)] + [f"{prefix}_Moving"])},
}
POINT_PARENT = {name: "LiftCylinder" for name in (
    "BoomAngleSensorFrameJoint", "BoomAngleSensorCrankJoint", "BoomAngleSensorBoomJoint"
)}

UNDERBODY_NODES = (
    "FrontDifferential", "RearDifferential", "FrontAxle", "RearAxle",
    "FrontAxleTubeLeft", "FrontAxleTubeRight", "RearAxleTubeLeft", "RearAxleTubeRight",
    "FrontPinionFlange", "RearPinionFlange", "BellyPan",
    "FrontSteerCylinderBarrel", "RearSteerCylinderBarrel",
    "FrontSteerBarLeft", "FrontSteerBarRight", "RearSteerBarLeft", "RearSteerBarRight",
)


def validate_glb_hierarchy(failures: list[str]) -> tuple[float, float]:
    document, blob = load_glb(GLB)
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
    front_tire_names = [name for name in by_name
                        if name.startswith(("Tire_FL", "Tire_FR", "Tread_FL_", "Tread_FR_"))]
    front_tire_plane = max(node_bounds(document, blob, nodes, parents, by_name[name])[1][0]
                           for name in front_tire_names)
    underbody_clearance = min(node_bounds(document, blob, nodes, parents, by_name[name])[0][1]
                              for name in UNDERBODY_NODES)
    boom_metadata = (nodes[by_name["BoomLiftPivot"]].get("extras") or {}).get("visual_angle_degrees")
    if boom_metadata != [0, 69]:
        failures.append(f"BoomLiftPivot GLB metadata is {boom_metadata}, expected [0, 69]")
    return front_tire_plane, underbody_clearance


def main() -> None:
    failures: list[str] = []
    front_tire_plane, underbody_clearance = validate_glb_hierarchy(failures)
    completed = subprocess.run(
        ["node", str(ROOT / "scripts/validate_742_solver.mjs")],
        check=True, capture_output=True, text=True,
    )
    result = json.loads(completed.stdout)
    if result["unique_multidimensional_state_samples"] != 416745:
        failures.append("dense multidimensional solver grid was not fully executed")
    if result["continuous_all_chain_samples"] < 2001:
        failures.append("continuous all-chain sweep is not dense enough")
    for name, chain in result["chain_paths"].items():
        if chain["maximum_total_length_drift_m"] > 1e-9:
            failures.append(f"{name} total length is not invariant")
        if chain["minimum_segment_length_m"] < 0.04 or chain["wrap_degrees"] != 180:
            failures.append(f"{name} route collapsed or lost its U-wrap")
    if result["maximum_chain_tangent_dot_error"] > 1e-12:
        failures.append("chain straight legs are not tangent to their reconstructed sheaves")
    if result["minimum_chain_to_sheave_surface_clearance_m"] <= 0:
        failures.append("chain centerline/tube intersects a sheave surface")
    if result["maximum_chain_endpoint_step_m"] > 0.004:
        failures.append("chain endpoint continuity exceeded the dense-step bound")
    if result["continuous_hose_samples"] < 2001:
        failures.append("continuous service-line sweep is not dense enough")
    for name, hose in result["hose_paths"].items():
        if hose["maximum_total_length_drift_m"] > 1e-9:
            failures.append(f"{name} changes total hose length")
        minimum = 0.05 if name.startswith("BoomHose") else 0.10
        if hose["minimum_segment_length_m"] < minimum:
            failures.append(f"{name} articulated route collapsed")
    if result["maximum_hose_endpoint_step_m"] > 0.002:
        failures.append("service-line endpoint continuity exceeded the dense-step bound")
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
    reach = result["maximum_reach_pose"]
    reach["front_tire_tread_plane_x_m"] = front_tire_plane
    reach["forward_reach_m"] = reach["load_center_world_x_m"] - front_tire_plane
    if abs(reach["forward_reach_m"] - CONFIG["published_performance"]["maximum_forward_reach_m"]) > 0.02:
        failures.append("separate 3-degree maximum-reach pose misses the published reach")
    steering = result["steering_linkage"]
    if steering["minimum_straight_rod_length_m"] <= 0.10:
        failures.append("steering rod topology approached a collapsed link")
    if steering["maximum_steering_bar_length_drift_m"] > 1e-12:
        failures.append("steering bars are not invariant rigid links")
    if steering["maximum_opposed_rod_joint_span_drift_m"] > 1e-12:
        failures.append("double-ended steering rod joint span is not invariant")
    if steering["maximum_rod_bar_closure_error_m"] > 1e-12:
        failures.append("steering rod/bar joint lost endpoint closure")
    if abs(steering["maximum_inner_wheel_angle_degrees"] - 55) > 1e-9:
        failures.append("rigid steering linkage misses the published 55-degree inner-wheel limit")
    if steering["maximum_ackermann_relative_error"] > 0.005:
        failures.append("reconstructed rigid linkage exceeds its visual Ackermann-fit boundary")
    if steering["maximum_four_wheel_icr_relative_spread"] > 0.005:
        failures.append("four-wheel circle-steer linkage lost its reconstructed ICR closure")
    if steering["maximum_crab_heading_spread_degrees"] > 2.1 or steering["maximum_crab_corresponding_heading_error_degrees"] > 2.1:
        failures.append("continuous-rack crab presentation exceeded its explicit residual-toe boundary")
    if steering["maximum_front_mode_icr_relative_spread"] > 0.05:
        failures.append("limited-rack front-only presentation exceeded its reconstructed ICR-fit boundary")
    for name, values in result["rigid_link_ranges_m"].items():
        if values[1] - values[0] > 1e-12:
            failures.append(f"{name} changes length")
    if underbody_clearance + 1e-6 < MECH["collision_proxies"]["minimum_rigid_underbody_clearance_m"]:
        failures.append("actual GLB named rigid-underbody proxy misses approximate published clearance")
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
        "actual_glb_front_tire_tread_plane_x_m": front_tire_plane,
        "actual_glb_minimum_named_rigid_underbody_clearance_m": underbody_clearance,
        "posed_glb_blender_gate": "scripts/run_742_posed_glb_gate.py",
        "rear_axle_stabilization_published_stroke_m": strokes["rear_axle_stabilization"],
        "rear_axle_stabilization_usage_boundary": "only frame-level-induced endpoint travel is shown; free/slow/locked RAS behavior is not simulated",
    })
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
