#!/usr/bin/env python3
"""Validate the combined public presentation bundle without asserting release certification."""

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
MANIFEST = SITE / "pages-build-manifest.json"
ROUTES = {
    "index.html": ("./", "./742/", "./es1930m/", "./"),
    "742/index.html": ("../", "../742/", "../es1930m/", "../742/"),
    "es1930m/index.html": ("../", "../742/", "../es1930m/", "../es1930m/"),
}
REQUIRED = {
    "index.html", "600s/index.html", "742/index.html", "es1930m/index.html",
    "viewer.css", "viewer/machine-tabs.css", "viewer.js", "viewer/runtime.js",
    "viewer/742.css", "viewer/742-runtime.js", "assets/models/600s.glb",
    "assets/models/es1930m.glb", "assets/models/742.glb",
    "assets/social/equipment-explorer-pages-thumbnail.png", "pages-build-manifest.json",
}
SOCIAL_IMAGE = "https://exo-robotics.github.io/jlg-equipment-explorer/assets/social/equipment-explorer-pages-thumbnail.png"


missing = sorted(path for path in REQUIRED if not (SITE / path).is_file())
if missing:
    raise RuntimeError(f"Combined showcase bundle missing required files: {missing}")

for path, (boom, telehandler, scissor, current) in ROUTES.items():
    source = (SITE / path).read_text(encoding="utf-8")
    if source.count('class="machine-tabs"') != 1 or source.count('aria-current="page"') != 1:
        raise RuntimeError(f"Machine navigation identity drift: {path}")
    for href in (boom, telehandler, scissor):
        if f'href="{href}"' not in source:
            raise RuntimeError(f"Machine navigation target missing from {path}: {href}")
    if f'href="{current}" aria-current="page"' not in source:
        raise RuntimeError(f"Current machine marker drift: {path}")
    if source.count(f'<meta property="og:image" content="{SOCIAL_IMAGE}">') != 1:
        raise RuntimeError(f"Open Graph thumbnail drift: {path}")
    if source.count(f'<meta name="twitter:image" content="{SOCIAL_IMAGE}">') != 1:
        raise RuntimeError(f"Large-card thumbnail drift: {path}")

for forbidden in ("assets/models/742.asset-receipt.json", "docs/review/742", "_private-evidence", "_attestations"):
    if (SITE / forbidden).exists():
        raise RuntimeError(f"Private or non-release evidence leaked into presentation bundle: {forbidden}")

for path in SITE.rglob("*"):
    if path.is_file() and path.suffix.lower() in {".blend", ".blend1", ".pdf", ".ifc", ".zip", ".fbx", ".step", ".stp"}:
        raise RuntimeError(f"Source binary leaked into presentation bundle: {path.relative_to(SITE)}")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if manifest.get("kind") != "github-pages-build-manifest" or set(manifest) != {"schema_version", "kind", "source_commit", "files"}:
    raise RuntimeError("Combined showcase manifest identity drift")
expected = {}
for path in sorted(candidate for candidate in SITE.rglob("*") if candidate.is_file() and candidate not in {MANIFEST, SITE / ".nojekyll"}):
    payload = path.read_bytes()
    expected[str(path.relative_to(SITE))] = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
if manifest.get("files") != expected:
    raise RuntimeError("Combined showcase manifest does not exactly bind the public bundle")

print(json.dumps({
    "status": "PASS", "kind": "public-presentation-not-release", "routes": list(ROUTES),
    "manifest_files": len(expected), "manufacturer_source_binaries": 0, "private_review_evidence": 0,
}, indent=2, sort_keys=True))
