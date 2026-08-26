#!/usr/bin/env python3
"""Assemble the static Pages bundle from an explicit public-file allowlist."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
FILES = ["index.html", "viewer.css", "viewer.js"]
TREES = ["600s", "es1930m", "742", "machines", "viewer", "vendor/three-r160"]
MODEL_FILES = [
    "600s.glb", "600s.version.js", "600s.configuration.json", "600s.asset-receipt.json",
    "es1930m.glb", "es1930m.asset-receipt.json", "742.glb",
]
RESEARCH_FILES = [
    "README.md", "REFERENCES.md", "CONFIGURATION.md", "DIMENSIONS.md", "ARTICULATION.md",
    "SOURCE_RECONCILIATION.md", "DETAILED_RECONSTRUCTION.md", "COMPARISON_MATRIX.md",
    "RIGHTS_AND_BIM_BOUNDARY.md", "SOURCE_MANIFEST.json", "MECHANISM_EVIDENCE.json",
    "reference-board/README.md",
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
for relative in RESEARCH_FILES:
    destination = SITE / "docs/research/742" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "docs/research/742" / relative, destination)
(SITE / ".nojekyll").touch()
print(f"PASS: assembled {SITE}")
