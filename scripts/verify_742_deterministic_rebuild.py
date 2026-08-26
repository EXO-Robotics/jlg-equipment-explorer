#!/usr/bin/env python3
"""Rebuild the 742 twice in isolated directories and attest byte-identical GLBs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"


def file_record(path: Path) -> dict:
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}


def build_once(blender: Path, run_root: Path) -> tuple[dict, dict]:
    (run_root / "scripts").mkdir(parents=True)
    (run_root / "machines/742").mkdir(parents=True)
    (run_root / "assets/models").mkdir(parents=True)
    (run_root / "source/blender").mkdir(parents=True)
    shutil.copy2(ROOT / "scripts/build_742.py", run_root / "scripts/build_742.py")
    shutil.copy2(ROOT / "scripts/solve_742_pose.mjs", run_root / "scripts/solve_742_pose.mjs")
    shutil.copy2(ROOT / "machines/742/742.configuration.json", run_root / "machines/742/742.configuration.json")
    shutil.copy2(ROOT / "machines/742/solver.js", run_root / "machines/742/solver.js")
    completed = subprocess.run(
        [str(blender), "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(run_root / "scripts/build_742.py")],
        cwd=run_root, text=True, capture_output=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"742 isolated Blender rebuild failed\n{completed.stdout}\n{completed.stderr}")
    glb = run_root / "assets/models/742.glb"
    blend = run_root / "source/blender/742-showcase-v1.0.blend"
    if not glb.is_file() or not blend.is_file():
        raise RuntimeError(
            f"742 isolated Blender rebuild did not create both canonical outputs\n{completed.stdout}\n{completed.stderr}"
        )
    return file_record(glb), file_record(blend)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.blender.is_file():
        raise RuntimeError(f"Blender executable is missing: {args.blender}")
    version = subprocess.check_output([str(args.blender), "--version"], text=True).splitlines()[0].strip()
    if not re.fullmatch(r"Blender \d+\.\d+\.\d+.*", version):
        raise RuntimeError(f"Could not identify Blender version: {version}")
    with tempfile.TemporaryDirectory(prefix="jlg742-rebuild-") as temporary:
        temp = Path(temporary)
        run1_glb, run1_blend = build_once(args.blender, temp / "run-1")
        run2_glb, run2_blend = build_once(args.blender, temp / "run-2")
    committed_glb = file_record(ROOT / "assets/models/742.glb")
    if run1_glb != run2_glb or run1_glb != committed_glb:
        raise RuntimeError(
            f"742 deterministic GLB rebuild drift: run1={run1_glb} run2={run2_glb} committed={committed_glb}"
        )
    record = {
        "schema_version": "1.0.0",
        "kind": "742-deterministic-glb-rebuild-attestation",
        "configuration_id": EXPECTED_ID,
        "blender_version": version,
        "builder": {"path": "scripts/build_742.py", **file_record(ROOT / "scripts/build_742.py")},
        "solver_bridge": {"path": "scripts/solve_742_pose.mjs", **file_record(ROOT / "scripts/solve_742_pose.mjs")},
        "solver": {"path": "machines/742/solver.js", **file_record(ROOT / "machines/742/solver.js")},
        "configuration": {"path": "machines/742/742.configuration.json", **file_record(ROOT / "machines/742/742.configuration.json")},
        "run_1_glb": run1_glb,
        "run_2_glb": run2_glb,
        "committed_glb": {"path": "assets/models/742.glb", **committed_glb},
        "run_1_blend": run1_blend,
        "run_2_blend": run2_blend,
        "glb_byte_identical": True,
        "blend_byte_identity_claimed": run1_blend == run2_blend,
        "boundary": "The GLB was rebuilt twice from the exact builder/configuration with one Blender version. Blend-file byte identity is reported separately and is not required.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "output": str(args.output), "blender_version": version,
        "glb_sha256": committed_glb["sha256"], "blend_byte_identical": record["blend_byte_identity_claimed"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
