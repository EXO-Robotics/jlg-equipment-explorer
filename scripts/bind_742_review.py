#!/usr/bin/env python3
"""Bind fresh, completed 742 observations to one pending candidate commit.

Binding never performs a review. The two explicit confirmations are required so
the tool cannot silently convert pending templates into pass records. All writes
are rolled back if semantic parsing or commit-byte verification fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_742_browser_evidence import BROWSER_GATES
from validate_742_review import (
    BROWSER_CAPTURE_ALLOWLIST_PATH,
    EXPECTED_ARTIFACT_PATHS,
    HUMAN_GATES,
    ROOT,
    read_owned_render_allowlist_records,
    validate_pending_extended_visual_observation,
    validate_owned_render_semantic_coverage,
    validate_review_manifest,
)


def record(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _candidate_canonical_paths(receipt: dict) -> list[Path]:
    paths = [ROOT / item["path"] for item in receipt["files"].values()]
    paths.extend(ROOT / path for path in receipt["runtime"]["files"])
    paths.extend(ROOT / check["validator"]["path"] for check in receipt["automated_checks"].values())
    if any(str(path.relative_to(ROOT)) == BROWSER_CAPTURE_ALLOWLIST_PATH for path in paths):
        raise RuntimeError("742 pending receipt incorrectly treats the post-capture allowlist as candidate input")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-receipt", type=Path, default=ROOT / "assets/models/742.asset-receipt.json")
    parser.add_argument("--reviewed-source-commit", required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/review/742/review-manifest.json")
    parser.add_argument(
        "--confirm-browser-observations-reviewed", action="store_true",
        help="Confirm that every schema-2 browser capture was freshly observed and reviewed; binding is not observation.",
    )
    parser.add_argument(
        "--confirm-visual-observations-reviewed", action="store_true",
        help="Confirm that the final stowed, extended, and cab renders were freshly reviewed.",
    )
    args = parser.parse_args()
    if not args.confirm_browser_observations_reviewed or not args.confirm_visual_observations_reviewed:
        raise RuntimeError("742 review binding requires explicit browser and visual observation confirmations")
    if not re.fullmatch(r"[0-9a-f]{40}", args.reviewed_source_commit):
        raise RuntimeError("742 review binding requires an exact 40-character reviewed commit")
    receipt = json.loads(args.candidate_receipt.read_text(encoding="utf-8"))
    if receipt.get("release_status") != "candidate_review_pending" or receipt.get("human_review", {}).get("status") != "pending":
        raise RuntimeError("742 review binding requires a pending candidate receipt")
    candidate_hash = receipt.get("candidate_tree_sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", candidate_hash):
        raise RuntimeError("742 pending receipt candidate tree hash is malformed")
    canonical_paths = _candidate_canonical_paths(receipt)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "3.0.0" or set(manifest.get("gates") or {}) != set(HUMAN_GATES):
        raise RuntimeError("742 pending review manifest schema/gate set drift")
    if manifest.get("candidate_tree_sha256") != "PENDING" or manifest.get("reviewed_source_commit") != "PENDING" or manifest.get("environment") is not None:
        raise RuntimeError("742 rebind requires an unbound pending review manifest")
    if any(gate.get("status") != "pending" or gate.get("artifact") is not None for gate in manifest["gates"].values()):
        raise RuntimeError("742 rebind requires every review gate to remain pending")
    allowed_png = read_owned_render_allowlist_records()
    validate_owned_render_semantic_coverage(allowed_png)
    validate_pending_extended_visual_observation(
        ROOT / EXPECTED_ARTIFACT_PATHS["extended_visual_fidelity"],
        allowed_png,
    )

    browser_environments = []
    for gate in BROWSER_GATES:
        artifact = json.loads((ROOT / EXPECTED_ARTIFACT_PATHS[gate]).read_text(encoding="utf-8"))
        if artifact.get("schema_version") != "2.0.0" or artifact.get("capture_status") != "complete":
            raise RuntimeError(f"742 browser capture is not complete: {gate}")
        if artifact.get("candidate_tree_sha256") != "PENDING" or artifact.get("reviewed_source_commit") != "PENDING":
            raise RuntimeError(f"742 browser capture is already bound: {gate}")
        environment = artifact.get("environment") or {}
        browser_environments.append({"browser": environment.get("browser"), "os": environment.get("os")})
    if any(environment != browser_environments[0] for environment in browser_environments[1:]):
        raise RuntimeError("742 browser captures disagree on browser/OS identity")

    json_paths = [ROOT / EXPECTED_ARTIFACT_PATHS[gate] for gate in HUMAN_GATES if EXPECTED_ARTIFACT_PATHS[gate].endswith(".json")]
    touched = [args.manifest, *json_paths]
    originals = {path: path.read_bytes() for path in touched}
    try:
        manifest["candidate_tree_sha256"] = candidate_hash
        manifest["reviewed_source_commit"] = args.reviewed_source_commit
        manifest["environment"] = browser_environments[0]
        for gate in HUMAN_GATES:
            artifact_path = ROOT / EXPECTED_ARTIFACT_PATHS[gate]
            if artifact_path.suffix.lower() == ".json":
                artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
                artifact["candidate_tree_sha256"] = candidate_hash
                artifact["reviewed_source_commit"] = args.reviewed_source_commit
                if gate == "extended_visual_fidelity":
                    artifact["environment"]["os"] = browser_environments[0]["os"]
                _write_json(artifact_path, artifact)
            manifest["gates"][gate]["status"] = "pass"
            manifest["gates"][gate]["artifact"] = record(artifact_path)
        _write_json(args.manifest, manifest)

        reviewed, binding = validate_review_manifest(args.manifest, candidate_hash, canonical_paths)
    except Exception:
        for path, contents in originals.items():
            path.write_bytes(contents)
        raise
    print(json.dumps({
        "status": "PASS",
        "candidate_tree_sha256": candidate_hash,
        "reviewed_source_commit": binding["reviewed_source_commit"],
        "browser_capture_allowlist": binding["browser_capture_allowlist"],
        "gates_bound": len(reviewed),
        "warning": "Binding updated only after explicit confirmations; this tool did not perform the recorded observations.",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
