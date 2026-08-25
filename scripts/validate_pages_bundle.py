#!/usr/bin/env python3
"""Fail closed if the Pages bundle lacks either machine or leaks source material."""

import json
import sys
from pathlib import Path

site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
required = {
    "index.html", "600s/index.html", "es1930m/index.html", "viewer/runtime.js",
    "machines/es1930m/machine.js", "assets/models/600s.glb", "assets/models/es1930m.glb",
    "assets/models/600s.asset-receipt.json", "assets/models/es1930m.asset-receipt.json",
}
missing = sorted(path for path in required if not (site / path).is_file())
leaks = sorted(str(path.relative_to(site)) for path in site.rglob("*") if path.suffix.lower() in {".blend", ".pdf"})
if missing or leaks:
    raise RuntimeError(f"Pages bundle invalid; missing={missing}; source_leaks={leaks}")
print(json.dumps({"status": "PASS", "required_files": len(required), "source_leaks": leaks}, indent=2))
