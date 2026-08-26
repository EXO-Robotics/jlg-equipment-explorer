#!/usr/bin/env python3
"""Write a deterministic, byte-counting manifest for the assembled Pages site."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


root = Path("_site").resolve()
manifest_path = root / "pages-build-manifest.json"
source_commit = os.environ.get("GITHUB_SHA")
if not source_commit:
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
if not re.fullmatch(r"[0-9a-f]{40}", source_commit or ""):
    raise RuntimeError("Pages build manifest requires an exact 40-character source commit")
files = {}
for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file() and candidate != manifest_path):
    relative = str(path.relative_to(root))
    if relative != ".nojekyll":
        committed = subprocess.run(
            ["git", "show", f"{source_commit}:{relative}"], capture_output=True, check=False,
        )
        if committed.returncode or committed.stdout != path.read_bytes():
            raise RuntimeError(f"Pages bundle bytes are not present at source commit {source_commit}: {relative}")
    files[relative] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
record = {
    "schema_version": "1.0.0",
    "kind": "github-pages-build-manifest",
    "source_commit": source_commit,
    "files": files,
}
manifest_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "manifest": str(manifest_path), "files": len(files)}, sort_keys=True))
