#!/usr/bin/env python3
"""Verify the ES1930M candidate receipt and optionally require every release gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = ROOT / "assets/models/es1930m.asset-receipt.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_digest(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(str(path.relative_to(ROOT)).encode())
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-release", action="store_true", help="Fail unless every human/browser/deployment gate is true.")
    parser.add_argument("--require-predeploy", action="store_true", help="Fail unless every gate except exact public deployment review is true.")
    args = parser.parse_args()
    receipt = json.loads(RECEIPT_PATH.read_text())
    if receipt.get("configuration_id") != "ES1930M-PVC2404-US-STD-FR-FLA130-NM":
        raise RuntimeError("Receipt configuration identity drift")
    verified = []
    for label, record in receipt.get("files", {}).items():
        path = ROOT / record["path"]
        if not path.is_file() or digest(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
            raise RuntimeError(f"Receipt file drift: {label}")
        verified.append(record["path"])
    runtime_paths = [ROOT / path for path in receipt["runtime"]["files"]]
    if runtime_digest(runtime_paths) != receipt["runtime"]["sha256"]:
        raise RuntimeError("Receipt runtime drift")
    flags = receipt.get("review_flags") or {}
    incomplete = sorted(name for name, value in flags.items() if value is not True)
    if args.require_predeploy:
        predeploy_incomplete = sorted(name for name in incomplete if name != "deployed_pages_reviewed")
        if predeploy_incomplete:
            raise RuntimeError(f"Predeployment review gates incomplete: {predeploy_incomplete}")
        if receipt.get("release_status") not in {"candidate_not_deployable", "release"}:
            raise RuntimeError("Receipt has an unknown predeployment status")
    if args.require_release and incomplete:
        raise RuntimeError(f"Release review gates incomplete: {incomplete}")
    if args.require_release and receipt.get("release_status") != "release":
        raise RuntimeError("Receipt is not marked release")
    print(json.dumps({
        "status": "PASS",
        "configuration_id": receipt["configuration_id"],
        "verified_files": sorted(verified),
        "review_gates_complete": not incomplete,
        "incomplete_review_gates": incomplete,
        "release_status": receipt.get("release_status"),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
