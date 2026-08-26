#!/usr/bin/env python3
"""Verify the exact deployed 742 public surface against the CI build manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
SOURCE_EVIDENCE_ARTIFACT = "742-frozen-source-evidence"
REQUIRED_742_PUBLIC_FILES = {
    "742/index.html", "assets/models/742.glb", "viewer.css", "viewer/742.css", "viewer/742-runtime.js", "viewer/auto-override.mjs",
    "machines/742/machine.js", "machines/742/articulation.js", "machines/742/inspector.js",
    "machines/742/cameras.js", "machines/742/version.js", "machines/742/742.configuration.json",
    "machines/742/mechanism.json", "machines/742/solver.js", "docs/research/742/README.md", "docs/research/742/REFERENCES.md",
    "docs/research/742/CONFIGURATION.md", "docs/research/742/DIMENSIONS.md",
    "docs/research/742/ARTICULATION.md", "docs/research/742/SOURCE_RECONCILIATION.md",
    "docs/research/742/DETAILED_RECONSTRUCTION.md", "docs/research/742/COMPARISON_MATRIX.md",
    "docs/research/742/RIGHTS_AND_BIM_BOUNDARY.md", "docs/research/742/SOURCE_MANIFEST.json",
    "docs/research/742/MECHANISM_EVIDENCE.json", "docs/research/742/reference-board/README.md",
}


def fetch(url: str, expected: dict | None = None, expected_bytes: bytes | None = None) -> tuple[int, bytes]:
    last_status, last_payload = 0, b""
    for attempt in range(6):
        request = urllib.request.Request(url, headers={"User-Agent": "jlg-equipment-explorer-pages-verifier/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                last_status, last_payload = response.status, response.read()
        except urllib.error.HTTPError as error:
            last_status, last_payload = error.code, error.read()
        except urllib.error.URLError:
            last_status, last_payload = 0, b""
        actual = {"sha256": hashlib.sha256(last_payload).hexdigest(), "bytes": len(last_payload)}
        if last_status == 200 and (expected is None or actual == expected) and (expected_bytes is None or last_payload == expected_bytes):
            return last_status, last_payload
        if attempt < 5:
            time.sleep(5)
    return last_status, last_payload


def copy_if_distinct(source: Path, destination: Path) -> bool:
    """Copy an attestation companion unless the workflow already wrote it there."""
    if source.resolve() == destination.resolve():
        return False
    shutil.copy2(source, destination)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--build-manifest", type=Path, default=Path("_site/pages-build-manifest.json"))
    parser.add_argument("--candidate-receipt", type=Path, default=ROOT / "assets/models/742.asset-receipt.json")
    parser.add_argument("--workflow-run-url", required=True)
    parser.add_argument("--source-replay-result", type=Path, required=True)
    parser.add_argument("--source-evidence-run-url", required=True)
    parser.add_argument("--rebuild-attestation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    if not re.fullmatch(r"https://exo-robotics\.github\.io/jlg-equipment-explorer/", base_url):
        raise RuntimeError(f"742 deployment verifier requires the canonical Pages base URL: {base_url}")
    if not re.fullmatch(r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", args.workflow_run_url):
        raise RuntimeError("742 deployment workflow-run URL is malformed")
    if not re.fullmatch(r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", args.source_evidence_run_url):
        raise RuntimeError("742 private release-evidence workflow-run URL is malformed")

    source_replay_bytes = args.source_replay_result.read_bytes()
    source_replay = json.loads(source_replay_bytes)
    source_manifest = json.loads((ROOT / "docs/research/742/SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    expected_source_names = sorted(
        source["local_filename"] for source in source_manifest["sources"]
        if source.get("local_filename") and source.get("sha256") and source.get("bytes")
    )
    expected_source_replay_fields = {
        "admitted_source_binaries", "claims", "committed_source_binaries", "configuration_id",
        "frozen_source_binary_status", "local_binaries_missing", "local_binaries_verified",
        "local_binaries_verified_count", "owned_review_renders_verified", "browser_captures_verified", "primary_publications",
        "source_expressions_resolved", "status",
    }
    if set(source_replay) != expected_source_replay_fields:
        raise RuntimeError("742 frozen-source replay result schema drift")
    if (
        source_replay["status"] != "PASS"
        or source_replay["configuration_id"] != EXPECTED_ID
        or source_replay["frozen_source_binary_status"] != "VERIFIED"
        or source_replay["admitted_source_binaries"] != len(expected_source_names)
        or source_replay["local_binaries_verified_count"] != len(expected_source_names)
        or source_replay["local_binaries_verified"] != expected_source_names
        or source_replay["local_binaries_missing"] != []
    ):
        raise RuntimeError("742 frozen-source replay result is not a complete 11/11 verification")

    candidate_receipt = json.loads(args.candidate_receipt.read_text(encoding="utf-8"))
    if candidate_receipt.get("configuration_id") != EXPECTED_ID:
        raise RuntimeError("742 candidate receipt identity drift")
    rebuild_bytes = args.rebuild_attestation.read_bytes()
    rebuild = json.loads(rebuild_bytes)
    if (
        rebuild.get("schema_version") != "1.0.0"
        or rebuild.get("kind") != "742-deterministic-glb-rebuild-attestation"
        or rebuild.get("configuration_id") != EXPECTED_ID
        or rebuild.get("glb_byte_identical") is not True
    ):
        raise RuntimeError("742 deterministic rebuild attestation is incomplete")
    receipt_asset = candidate_receipt.get("files", {}).get("asset", {})
    if rebuild.get("committed_glb") != {
        "path": receipt_asset.get("path"),
        "sha256": receipt_asset.get("sha256"),
        "bytes": receipt_asset.get("bytes"),
    }:
        raise RuntimeError("742 deterministic rebuild attestation does not bind the candidate GLB")
    local_manifest_bytes = args.build_manifest.read_bytes()
    manifest = json.loads(local_manifest_bytes)
    if set(manifest) != {"schema_version", "kind", "source_commit", "files"} or manifest["schema_version"] != "1.0.0" or manifest["kind"] != "github-pages-build-manifest":
        raise RuntimeError("742 Pages build manifest schema/identity drift")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_commit", "")):
        raise RuntimeError("742 Pages build manifest source commit is malformed")
    public_files = set(manifest.get("files") or {})
    if missing := sorted(REQUIRED_742_PUBLIC_FILES - public_files):
        raise RuntimeError(f"742 Pages build manifest is missing required public files: {missing}")
    for relative in public_files:
        candidate = PurePosixPath(relative)
        if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative or relative == "pages-build-manifest.json":
            raise RuntimeError(f"742 Pages build manifest has an unsafe file path: {relative}")
    if "assets/models/742.asset-receipt.json" in manifest["files"]:
        raise RuntimeError("Non-release 742 candidate receipt was included in Pages")

    manifest_url = urllib.parse.urljoin(base_url, "pages-build-manifest.json")
    manifest_status, deployed_manifest_bytes = fetch(manifest_url, expected_bytes=local_manifest_bytes)
    if manifest_status != 200 or deployed_manifest_bytes != local_manifest_bytes:
        raise RuntimeError("Public Pages build manifest does not exactly match the workflow artifact")

    verified_files = {}
    for relative in sorted(public_files):
        expected = manifest["files"][relative]
        url = urllib.parse.urljoin(base_url, relative)
        status, payload = fetch(url, expected=expected)
        actual = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        if status != 200 or actual != expected:
            raise RuntimeError(
                f"742 deployed file drift: {relative}: status={status} expected={expected} actual={actual}"
            )
        verified_files[relative] = {"url": url, "http_status": status, **actual}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest_copy = args.output.parent / "pages-build-manifest.json"
    copy_if_distinct(args.build_manifest, manifest_copy)
    rebuild_copy = args.output.parent / "742-deterministic-rebuild-attestation.json"
    copy_if_distinct(args.rebuild_attestation, rebuild_copy)
    record = {
        "schema_version": "3.0.0",
        "kind": "github-pages-http-attestation",
        "configuration_id": EXPECTED_ID,
        "source_commit": manifest["source_commit"],
        "workflow_run_url": args.workflow_run_url,
        "base_url": base_url,
        "pages_build_manifest_url": manifest_url,
        "pages_build_manifest_http_status": manifest_status,
        "pages_build_manifest_sha256": hashlib.sha256(local_manifest_bytes).hexdigest(),
        "pages_build_manifest_bytes": len(local_manifest_bytes),
        "candidate_receipt_sha256": hashlib.sha256(args.candidate_receipt.read_bytes()).hexdigest(),
        "frozen_source_replay": {
            "status": "verified_before_deployment",
            "configuration_id": EXPECTED_ID,
            "verified_count": source_replay["local_binaries_verified_count"],
            "result_sha256": hashlib.sha256(source_replay_bytes).hexdigest(),
            "result_bytes": len(source_replay_bytes),
            "artifact_name": SOURCE_EVIDENCE_ARTIFACT,
            "artifact_run_url": args.source_evidence_run_url,
        },
        "deterministic_rebuild_attestation": {
            "sha256": hashlib.sha256(rebuild_bytes).hexdigest(),
            "bytes": len(rebuild_bytes),
            "authority": "generated_in_deployment_workflow",
            "workflow_run_url": args.workflow_run_url,
            "source_commit": manifest["source_commit"],
        },
        "verified_files": verified_files,
    }
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "output": str(args.output), "source_commit": manifest["source_commit"],
        "verified_files": len(verified_files),
        "frozen_source_replay": record["frozen_source_replay"]["status"],
        "deterministic_rebuild": "verified",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
