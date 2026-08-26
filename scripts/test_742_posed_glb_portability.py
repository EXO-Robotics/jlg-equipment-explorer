#!/usr/bin/env python3
"""Adversarial tests for checkout-independent posed-GLB result identity."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from run_742_posed_glb_gate import (
    EXPECTED_ASSET_PATH,
    canonical_posed_glb_asset_path,
    canonicalize_posed_glb_result,
)
from validate_742_portable_posed_glb import (
    PortablePoseGate,
    segment_distance,
    validate_neutral_binary_contract,
)


def expect_failure(callback, message: str) -> None:
    try:
        callback()
    except RuntimeError:
        return
    raise RuntimeError(message)


def compare_blender_companion(portable: dict, path: Path) -> dict:
    companion = json.loads(path.read_text(encoding="utf-8"))
    if companion.get("status") != "PASS" or companion.get("asset") != EXPECTED_ASSET_PATH:
        raise RuntimeError("pinned-Blender companion identity/status drift")
    if companion.get("production_solver_bridge") != portable["production_solver_bridge"]:
        raise RuntimeError("portable and pinned-Blender gates use different solver bridges")
    if companion.get("named_presets_posed") != portable["named_presets_posed"]:
        raise RuntimeError("portable and pinned-Blender gates cover different named presets")

    comparisons = {
        "maximum_lift_surface_m": abs(
            portable["maximum_lift"]["load_surface_m"] - companion["maximum_lift"]["load_surface_m"]
        ),
        "maximum_reach_m": abs(
            portable["maximum_reach"]["forward_reach_m"] - companion["maximum_reach"]["forward_reach_m"]
        ),
        "minimum_frame_level_clearance_m": abs(
            portable["minimum_frame_level_clearance"]["clearance_m"]
            - companion["minimum_frame_level_clearance"]["clearance_m"]
        ),
        "maximum_circle_wheel_angle_degrees": abs(
            portable["maximum_circle_steer"]["inner_wheel_angle_degrees"]
            - companion["maximum_circle_steer"]["inner_wheel_angle_degrees"]
        ),
        "maximum_crab_wheel_angle_degrees": abs(
            portable["maximum_crab_steer"]["maximum_wheel_angle_degrees"]
            - companion["maximum_crab_steer"]["maximum_wheel_angle_degrees"]
        ),
        "maximum_front_wheel_angle_degrees": abs(
            portable["maximum_front_steer"]["maximum_front_wheel_angle_degrees"]
            - companion["maximum_front_steer"]["maximum_front_wheel_angle_degrees"]
        ),
        "minimum_hose_tube_clearance_m": abs(
            min(item["minimum_boom_hose_to_rigid_tube_surface_clearance_m"]
                for item in portable["pose_contracts"].values())
            - min(item["minimum_boom_hose_to_rigid_tube_surface_clearance_m"]
                  for item in companion["pose_contracts"].values())
        ),
        "maximum_hose_chord_degrees": abs(
            max(item["maximum_boom_hose_adjacent_direction_change_degrees"]
                for item in portable["pose_contracts"].values())
            - max(item["maximum_boom_hose_adjacent_direction_change_degrees"]
                  for item in companion["pose_contracts"].values())
        ),
    }
    if (max(comparisons[name] for name in (
            "maximum_lift_surface_m", "maximum_reach_m", "minimum_frame_level_clearance_m",
            "minimum_hose_tube_clearance_m",
        )) > 2e-6
            or max(comparisons[name] for name in (
                "maximum_circle_wheel_angle_degrees", "maximum_crab_wheel_angle_degrees",
                "maximum_front_wheel_angle_degrees",
            )) > 1e-9
            or comparisons["maximum_hose_chord_degrees"] > 0.002
            or max(item["maximum_beam_endpoint_error_m"]
                   for item in companion["pose_contracts"].values()) > 2e-6):
        raise RuntimeError(f"portable/pinned-Blender posed-GLB agreement drift: {comparisons}")
    return {
        "status": "pass",
        "path": str(path),
        "maximum_absolute_differences": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender-result", type=Path)
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[1]
    package = json.loads((repository_root / "package.json").read_text(encoding="utf-8"))
    standard_check = package["scripts"]["check:742"]
    if ("validate_742_portable_posed_glb.py" not in standard_check
            or "run_742_posed_glb_gate.py" in standard_check
            or "Blender" in standard_check or "blender" in standard_check):
        raise RuntimeError("standard 742 check is not isolated from Blender startup")
    pages_workflow = (repository_root / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    if ("Run pinned-Blender posed-GLB companion gate" not in pages_workflow
            or "scripts/run_742_posed_glb_gate.py" not in pages_workflow):
        raise RuntimeError("Pages CI no longer runs the distinct pinned-Blender companion")

    checkout_a = Path("/private/tmp/742-portability/workspace-a")
    checkout_b = Path("/private/tmp/742-portability/different/workspace-b")
    values = [
        canonical_posed_glb_asset_path(EXPECTED_ASSET_PATH, checkout_a),
        canonical_posed_glb_asset_path(str(checkout_a / EXPECTED_ASSET_PATH), checkout_a),
        canonical_posed_glb_asset_path(str(checkout_b / EXPECTED_ASSET_PATH), checkout_b),
    ]
    if values != [EXPECTED_ASSET_PATH] * 3:
        raise RuntimeError("alternate checkout roots did not normalize to one canonical posed-GLB asset identity")

    original = {"status": "PASS", "asset": str(checkout_a / EXPECTED_ASSET_PATH), "measurement": 1}
    normalized = canonicalize_posed_glb_result(original, checkout_a)
    if normalized["asset"] != EXPECTED_ASSET_PATH or original["asset"] == EXPECTED_ASSET_PATH:
        raise RuntimeError("posed-GLB result normalization mutated input or retained an absolute path")

    negative_cases = 0
    for value, root, description in (
        (str(checkout_b / EXPECTED_ASSET_PATH), checkout_a, "absolute path from a different checkout"),
        ("../assets/models/742.glb", checkout_a, "parent traversal"),
        ("assets/models/not-742.glb", checkout_a, "wrong asset"),
        ("", checkout_a, "empty asset path"),
    ):
        expect_failure(
            lambda candidate=value, repository=root: canonical_posed_glb_asset_path(candidate, repository),
            f"accepted {description}",
        )
        negative_cases += 1

    gate = PortablePoseGate()
    if segment_distance([(0, 0, 0), (1, 0, 0)], [(0.5, -1, 0), (0.5, 1, 0)]) > 1e-12:
        raise RuntimeError("portable finite-segment distance missed a crossing")
    if abs(segment_distance([(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (1, 1, 0)]) - 1) > 1e-12:
        raise RuntimeError("portable finite-segment distance missed parallel separation")
    if abs(segment_distance([(0, 0, 0), (1, 0, 0)], [(2, 1, 0), (2, 2, 0)]) - 2 ** 0.5) > 1e-12:
        raise RuntimeError("portable finite-segment distance missed endpoint clamping")
    neutral = gate.solve({
        "lift": 0, "telescope": 0, "tilt": 0, "steer": 0,
        "level": 0, "steerMode": "circle",
    })
    binary_contract = validate_neutral_binary_contract(gate, neutral)
    if binary_contract["beams_checked"] < 100 or binary_contract["points_checked"] != 4:
        raise RuntimeError("portable committed-binary endpoint coverage drift")

    sample = next((name for name in sorted(neutral["geometry"]["beams"])
                   if name.startswith("BoomHose_")), None)
    if sample is None:
        raise RuntimeError("portable committed-binary proof has no boom-hose beam")
    node = gate.nodes[gate.by_name[sample]]
    original_axis = node["extras"]["rig_axis"]
    node["extras"]["rig_axis"] = "forged-axis"
    expect_failure(lambda: gate.verify_mesh_rig_axis(sample), "accepted forged GLB rig-axis metadata")
    node["extras"]["rig_axis"] = original_axis
    negative_cases += 1

    original_points = gate.mesh_points[sample]
    gate.mesh_points[sample] = [(point[0], point[1], point[2] + 0.01) for point in original_points]
    expect_failure(lambda: gate.verify_mesh_rig_axis(sample), "accepted forged GLB beam mesh extent")
    gate.mesh_points[sample] = original_points
    negative_cases += 1

    forged_pose = json.loads(json.dumps(neutral))
    forged_pose["geometry"]["beams"][sample][0][0] += 0.01
    expect_failure(
        lambda: validate_neutral_binary_contract(gate, forged_pose),
        "accepted forged solver/committed-GLB neutral endpoint",
    )
    negative_cases += 1

    portable_result = None
    if args.blender_result:
        portable_result = json.loads(subprocess.check_output(
            [sys.executable, "-B", str(repository_root / "scripts/validate_742_portable_posed_glb.py")],
            cwd=repository_root, text=True,
        ))
    companion_agreement = (compare_blender_companion(portable_result, args.blender_result)
                           if args.blender_result else {"status": "not_supplied"})

    print(json.dumps({
        "status": "PASS",
        "canonical_asset": EXPECTED_ASSET_PATH,
        "alternate_workspace_roots": 2,
        "portable_beams_checked": binary_contract["beams_checked"],
        "portable_points_checked": binary_contract["points_checked"],
        "standard_gate": "portable_no_blender_startup",
        "pinned_blender_companion": "pages_ci",
        "companion_agreement": companion_agreement,
        "negative_cases": negative_cases,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
