#!/usr/bin/env python3
"""Run the actual posed-GLB gate through Blender and emit its canonical JSON."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_742_posed_glb.py"
MARKER = "742_POSED_GLB_JSON="


def blender_binary() -> str:
    candidates = [
        os.environ.get("BLENDER_BIN"),
        shutil.which("blender"),
        "/Applications/Blender.app/Contents/MacOS/Blender",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError("742 posed-GLB gate requires Blender; set BLENDER_BIN to its executable")


def main() -> None:
    completed = subprocess.run(
        [blender_binary(), "--background", "--factory-startup", "--python", str(SCRIPT)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    marker_lines = [line[len(MARKER):] for line in completed.stdout.splitlines()
                    if line.startswith(MARKER)]
    if not marker_lines:
        raise RuntimeError(f"742 posed-GLB gate emitted no result\n{completed.stdout}{completed.stderr}")
    result = json.loads(marker_lines[-1])
    if completed.returncode or result.get("status") != "PASS":
        raise RuntimeError(f"742 posed-GLB gate failed\n{json.dumps(result, indent=2, sort_keys=True)}\n{completed.stderr}")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
