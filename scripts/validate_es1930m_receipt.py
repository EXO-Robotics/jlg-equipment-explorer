#!/usr/bin/env python3
"""Verify the ES1930M candidate receipt and optionally require every release gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from es1930m_review_binding import PREDEPLOY_GATES, validate_review_binding


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
    review = json.loads((ROOT / "docs/research/es1930m/REVIEW_EVIDENCE.json").read_text(encoding="utf-8"))
    receipt_600s = json.loads((ROOT / "assets/models/600s.asset-receipt.json").read_text(encoding="utf-8"))
    binding_report = None
    binding_error = None
    try:
        binding_report = validate_review_binding(review, receipt=receipt, receipt_600s=receipt_600s)
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        binding_error = str(error)
    claimed_binding = receipt.get("review_binding") or {}
    expected_binding_status = "exact_executable_predeploy_evidence" if binding_report is not None else "pending_or_stale"
    if claimed_binding.get("status") != expected_binding_status:
        raise RuntimeError("Receipt executable review-binding status drift")
    if binding_report is not None and set(PREDEPLOY_GATES) - {name for name, value in flags.items() if value is True}:
        raise RuntimeError("Exact executable binding did not propagate to every predeploy receipt gate")
    incomplete = sorted(name for name, value in flags.items() if value is not True)
    if args.require_predeploy:
        if binding_report is None:
            raise RuntimeError(f"Exact executable predeployment binding is unavailable: {binding_error}")
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
