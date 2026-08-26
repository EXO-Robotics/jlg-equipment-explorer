#!/usr/bin/env python3
"""Validate the frozen ES1930M source and mechanism evidence ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = PROJECT_ROOT / "docs/research/es1930m"
MANIFEST_PATH = RESEARCH_ROOT / "SOURCE_MANIFEST.json"
EVIDENCE_PATH = RESEARCH_ROOT / "MECHANISM_EVIDENCE.json"
CONFIG_PATH = PROJECT_ROOT / "machines/es1930m/es1930m.configuration.json"
EXPECTED_PRIMARY = {"3122602400", "3122602300", "3122602200"}
EXPECTED_QUARANTINED = {"3122602600", "3122602500"}
EXPECTED_CONFIGURATION = "ES1930M-PVC2404-US-STD-FR-FLA130-NM"
EXPECTED_BRANDING_CLAIMS = {"BR-001", "BR-002"}
EXPECTED_BRANDING_PARTS = {"1001322860", "1001322861", "1001304327", "1001256675", "1001256676", "1001304321", "1001304322"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources-dir",
        type=Path,
        help="Verify locally present source PDFs against frozen hashes.",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    ids = {
        manifest.get("target", {}).get("configuration_id"),
        evidence.get("configuration_id"),
        config.get("configuration_id"),
    }
    if ids != {EXPECTED_CONFIGURATION}:
        fail(f"Configuration identity drift: {sorted(str(value) for value in ids)}")
    if config.get("pvc") != "2404" or config.get("scissor_topology", {}).get("levels") != 5:
        fail("Frozen PVC or five-level scissor topology drift")

    sources = manifest.get("sources") or []
    publications = [source.get("publication") for source in sources if source.get("publication")]
    if len(publications) != len(set(publications)):
        fail("Source manifest contains duplicate publication identifiers")
    by_publication = {source.get("publication"): source for source in sources if source.get("publication")}
    if missing := sorted(EXPECTED_PRIMARY - by_publication.keys()):
        fail(f"Missing PVC 2404 primary sources: {missing}")
    if missing := sorted(EXPECTED_QUARANTINED - by_publication.keys()):
        fail(f"Missing quarantined cross-PVC sources: {missing}")

    for publication, source in by_publication.items():
        if not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")):
            fail(f"Invalid SHA-256 for {publication}")
        if publication in EXPECTED_PRIMARY:
            if source.get("pvc") != "2404" or source.get("admission") != "primary":
                fail(f"Primary source admission drift for {publication}")
        if publication in EXPECTED_QUARANTINED:
            if source.get("pvc") != "1001" or source.get("admission") != "quarantined":
                fail(f"Cross-PVC quarantine drift for {publication}")

    claims = [
        claim
        for system in evidence.get("systems", [])
        for claim in system.get("claims", [])
    ]
    claim_ids = [claim.get("id") for claim in claims]
    if not claims or len(claim_ids) != len(set(claim_ids)):
        fail("Mechanism evidence claims are missing or have duplicate IDs")
    if missing := sorted(EXPECTED_BRANDING_CLAIMS - set(claim_ids)):
        fail(f"PVC 2404 brand/model evidence claims are missing: {missing}")
    branding_parts = {
        part
        for claim in claims
        if claim.get("id") in EXPECTED_BRANDING_CLAIMS
        for part in claim.get("part_numbers", [])
    }
    if branding_parts != EXPECTED_BRANDING_PARTS:
        fail(f"PVC 2404 brand/model part-number binding drift: {sorted(branding_parts)}")

    required = {
        "id", "statement", "source", "pvc", "pages", "components",
        "part_numbers", "evidence_type", "authority", "geometry_use", "confidence",
    }
    for claim in claims:
        if missing := sorted(required - claim.keys()):
            fail(f"Evidence claim {claim.get('id')} missing fields: {missing}")
        if "1001" in str(claim["pvc"]) and "prohibited" not in claim["geometry_use"]:
            fail(f"Cross-PVC claim {claim['id']} escaped geometry quarantine")
        if not claim["pages"] or not claim["components"]:
            fail(f"Evidence claim {claim['id']} lacks page/component binding")
        cited = str(claim["source"]).split("+")
        if unresolved := sorted(set(cited) - by_publication.keys()):
            fail(f"Evidence claim {claim['id']} cites unknown publications: {unresolved}")
        for page in claim["pages"]:
            if not isinstance(page, int) or page < 1:
                fail(f"Evidence claim {claim['id']} has invalid page {page!r}")
            if not any(page <= int(by_publication[publication].get("pages", 0)) for publication in cited):
                fail(f"Evidence claim {claim['id']} page {page} exceeds every cited publication")
        if any(by_publication[publication].get("admission") == "quarantined" for publication in cited) and "prohibited" not in claim["geometry_use"]:
            fail(f"Evidence claim {claim['id']} uses a quarantined publication for geometry")

    local_checks = []
    if args.sources_dir:
        source_root = args.sources_dir.resolve()
        for source in sources:
            filename = source.get("local_filename")
            checksum = source.get("sha256")
            if not filename or not checksum:
                continue
            local_path = source_root / filename
            if not local_path.is_file():
                fail(f"Required local source is missing: {filename}")
            if sha256_file(local_path) != checksum:
                fail(f"Local source checksum drift: {filename}")
            local_checks.append(filename)
        expected_local = sorted(source["local_filename"] for source in sources if source.get("local_filename"))
        if sorted(local_checks) != expected_local:
            fail("Full local source verification did not cover every declared binary")

    print(json.dumps({
        "status": "PASS",
        "configuration_id": EXPECTED_CONFIGURATION,
        "claims": len(claims),
        "branding_claims": sorted(EXPECTED_BRANDING_CLAIMS),
        "primary_pvc2404_sources": sorted(EXPECTED_PRIMARY),
        "quarantined_pvc1001_sources": sorted(EXPECTED_QUARANTINED),
        "local_binaries_verified": sorted(local_checks),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
