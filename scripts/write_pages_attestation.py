#!/usr/bin/env python3
"""Write a CI identity and hash manifest into the assembled site."""

import hashlib
import json
import os
from pathlib import Path

root = Path("_site").resolve()
files = {}
for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file() and candidate.name != "build-attestation.json"):
    files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
record = {"schema_version": "1.0.0", "github_sha": os.environ.get("GITHUB_SHA", "local"), "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"), "files": files}
(root / "build-attestation.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PASS: attested {len(files)} deployed files")
