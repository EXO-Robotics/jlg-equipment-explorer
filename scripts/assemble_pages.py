#!/usr/bin/env python3
"""Assemble the two-machine static Pages bundle from an explicit allowlist."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FILES = ["index.html", "viewer.css", "viewer.js"]
TREES = ["600s", "es1930m", "machines", "viewer", "vendor/three-r160"]
MODEL_FILES = [
    "600s.glb", "600s.version.js", "600s.configuration.json", "600s.asset-receipt.json",
    "es1930m.glb", "es1930m.asset-receipt.json",
]

if SITE.exists():
    shutil.rmtree(SITE)
SITE.mkdir()
for relative in FILES:
    shutil.copy2(ROOT / relative, SITE / relative)
for relative in TREES:
    shutil.copytree(ROOT / relative, SITE / relative)
(SITE / "assets/models").mkdir(parents=True)
for name in MODEL_FILES:
    shutil.copy2(ROOT / "assets/models" / name, SITE / "assets/models" / name)
(SITE / ".nojekyll").touch()
print(f"PASS: assembled {SITE}")
