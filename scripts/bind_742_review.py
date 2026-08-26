#!/usr/bin/env python3
"""Bind already-performed 742 observations to an exact pending candidate commit.

This tool only updates identity fields and artifact hashes. It does not perform,
repeat, or infer any visual, browser, accessibility, performance, or regression
observation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_742_review import EXPECTED_ARTIFACT_PATHS, HUMAN_GATES, ROOT, validate_review_manifest


def record(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-receipt", type=Path, default=ROOT / "assets/models/742.asset-receipt.json")
    parser.add_argument("--reviewed-source-commit", required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/review/742/review-manifest.json")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.reviewed_source_commit):
        raise RuntimeError("742 review binding requires an exact 40-character reviewed commit")
    receipt = json.loads(args.candidate_receipt.read_text(encoding="utf-8"))
    if receipt.get("release_status") != "candidate_review_pending" or receipt.get("human_review", {}).get("status") != "pending":
        raise RuntimeError("742 review binding requires a pending candidate receipt")
    candidate_hash = receipt.get("candidate_tree_sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_hash):
        raise RuntimeError("742 pending receipt candidate tree hash is malformed")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if set(manifest.get("gates") or {}) != set(HUMAN_GATES):
        raise RuntimeError("742 review manifest gate set drift")
    manifest["schema_version"] = "2.0.0"
    manifest["candidate_tree_sha256"] = candidate_hash
    manifest["reviewed_source_commit"] = args.reviewed_source_commit
    for gate in HUMAN_GATES:
        artifact_path = ROOT / EXPECTED_ARTIFACT_PATHS[gate]
        if artifact_path.suffix.lower() == ".json":
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact["candidate_tree_sha256"] = candidate_hash
            artifact["reviewed_source_commit"] = args.reviewed_source_commit
            artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest["gates"][gate]["artifact"] = record(artifact_path)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    canonical_paths = [ROOT / item["path"] for item in receipt["files"].values()]
    canonical_paths.extend(ROOT / path for path in receipt["runtime"]["files"])
    canonical_paths.extend(ROOT / check["validator"]["path"] for check in receipt["automated_checks"].values())
    reviewed, binding = validate_review_manifest(args.manifest, candidate_hash, canonical_paths)
    print(json.dumps({
        "status": "PASS", "candidate_tree_sha256": candidate_hash,
        "reviewed_source_commit": binding["reviewed_source_commit"], "gates_bound": len(reviewed),
        "warning": "Binding updated only; this tool did not perform the recorded observations.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
