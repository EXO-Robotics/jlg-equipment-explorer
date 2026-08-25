#!/usr/bin/env python3
"""Validate the frozen source manifest and fail closed on authority drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = PROJECT_ROOT / "docs/research/600s"
MANIFEST_PATH = RESEARCH_ROOT / "SOURCE_MANIFEST.json"
EVIDENCE_PATH = RESEARCH_ROOT / "MECHANISM_EVIDENCE.json"
EXPECTED_CURRENT = {"3122579800", "3122579700", "3122579600"}
EXPECTED_QUARANTINED = {"3122588600", "3122586300"}
REJECTED_CURRENT_PARTS = {"1683618", "1001099832"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources-dir",
        type=Path,
        help="Optionally verify any locally present PDF binaries against the manifest.",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    sources = manifest.get("sources") or []
    by_publication = {source.get("publication"): source for source in sources}

    missing_current = sorted(EXPECTED_CURRENT - by_publication.keys())
    if missing_current:
        raise RuntimeError(f"Missing current PVC 2607 sources: {missing_current}")
    missing_quarantine = sorted(EXPECTED_QUARANTINED - by_publication.keys())
    if missing_quarantine:
        raise RuntimeError(f"Missing quarantined PVC 2601 sources: {missing_quarantine}")

    for publication, source in by_publication.items():
        checksum = source.get("sha256", "")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise RuntimeError(f"Invalid SHA-256 for {publication}")
        if publication in EXPECTED_CURRENT:
            if source.get("pvc") != "2607" or source.get("admission") != "primary":
                raise RuntimeError(f"Current source admission drift for {publication}")
        if publication in EXPECTED_QUARANTINED:
            if source.get("pvc") != "2601" or source.get("admission") != "quarantined":
                raise RuntimeError(f"Cross-PVC quarantine drift for {publication}")

    claims = [
        claim
        for system in evidence.get("systems", [])
        for claim in system.get("claims", [])
    ]
    claim_ids = [claim.get("id") for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise RuntimeError("Duplicate mechanism evidence claim id")

    required_fields = {
        "id", "statement", "source", "pvc", "pages", "components",
        "part_numbers", "evidence_type", "authority", "geometry_use", "confidence",
    }
    for claim in claims:
        missing = sorted(required_fields - claim.keys())
        if missing:
            raise RuntimeError(f"Evidence claim {claim.get('id')} missing fields: {missing}")
        if claim["authority"] == "provisional-cross-pvc" and claim["geometry_use"] != "prohibited":
            raise RuntimeError(f"Cross-PVC claim {claim['id']} escaped geometry quarantine")
        if any(part in REJECTED_CURRENT_PARTS for part in claim["part_numbers"]):
            raise RuntimeError(f"Rejected legacy part admitted by {claim['id']}")

    rejected_text = json.dumps(evidence.get("rejected_or_quarantined_claims", []))
    for part in REJECTED_CURRENT_PARTS:
        if part not in rejected_text:
            raise RuntimeError(f"Missing explicit legacy-part rejection for {part}")

    local_checks = []
    if args.sources_dir:
        source_root = args.sources_dir.resolve()
        for source in sources:
            local_path = source_root / source["local_filename"]
            if not local_path.is_file():
                continue
            actual = sha256_file(local_path)
            if actual != source["sha256"]:
                raise RuntimeError(f"Local source checksum drift: {local_path.name}")
            local_checks.append(local_path.name)

    print(json.dumps({
        "status": "PASS",
        "claims": len(claims),
        "current_pvc2607_sources": sorted(EXPECTED_CURRENT),
        "quarantined_pvc2601_sources": sorted(EXPECTED_QUARANTINED),
        "local_binaries_verified": sorted(local_checks),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
