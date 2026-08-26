#!/usr/bin/env python3
"""Fail closed if the Pages bundle is incomplete or leaks non-public evidence."""

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
research = {
    "README.md", "REFERENCES.md", "CONFIGURATION.md", "DIMENSIONS.md", "ARTICULATION.md",
    "SOURCE_RECONCILIATION.md", "DETAILED_RECONSTRUCTION.md", "COMPARISON_MATRIX.md",
    "RIGHTS_AND_BIM_BOUNDARY.md", "SOURCE_MANIFEST.json", "MECHANISM_EVIDENCE.json",
    "reference-board/README.md",
}
required = {
    "index.html", "600s/index.html", "es1930m/index.html", "742/index.html", "viewer.css",
    "viewer/runtime.js", "viewer/742-runtime.js", "viewer/742.css", "viewer/presentation-route.mjs",
    "machines/742/machine.js", "machines/742/articulation.js", "machines/742/inspector.js",
    "machines/742/cameras.js", "machines/742/version.js", "machines/742/742.configuration.json",
    "machines/742/mechanism.json", "machines/742/solver.js", "assets/models/600s.glb", "assets/models/es1930m.glb",
    "assets/models/742.glb", "assets/models/600s.asset-receipt.json",
    "assets/models/es1930m.asset-receipt.json", "pages-build-manifest.json",
} | {f"docs/research/742/{path}" for path in research}
missing = sorted(path for path in required if not (site / path).is_file())
forbidden_paths = {
    "assets/models/742.asset-receipt.json", "docs/review/742", "_private-evidence", "_attestations",
}
present_forbidden = sorted(path for path in forbidden_paths if (site / path).exists())

source_manifest = json.loads((ROOT / "docs/research/742/SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
manufacturer_records = {
    (source["sha256"], source["bytes"]): source["local_filename"]
    for source in source_manifest["sources"] if source.get("sha256") and source.get("bytes")
}
manufacturer_names = {source.get("local_filename") for source in source_manifest["sources"] if source.get("local_filename")}
manufacturer_leaks = []
private_evidence_paths = [ROOT / "assets/models/742.asset-receipt.json"]
review_root = ROOT / "docs/review/742"
private_evidence_paths.extend(path for path in review_root.rglob("*") if path.is_file())
private_evidence_records = {
    (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size): str(path.relative_to(ROOT))
    for path in private_evidence_paths if path.is_file()
}
private_evidence_leaks = []
for path in (candidate for candidate in site.rglob("*") if candidate.is_file()):
    record = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
    if path.name in manufacturer_names or record in manufacturer_records:
        manufacturer_leaks.append(str(path.relative_to(site)))
    if record in private_evidence_records:
        private_evidence_leaks.append(str(path.relative_to(site)))

forbidden_suffixes = {".blend", ".blend1", ".pdf", ".ifc", ".ifczip", ".zip", ".obj", ".stl", ".fbx", ".dae", ".step", ".stp", ".iges", ".igs"}
source_leaks = sorted(str(path.relative_to(site)) for path in site.rglob("*") if path.is_file() and path.suffix.lower() in forbidden_suffixes)

manifest_path = site / "pages-build-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
if set(manifest) != {"schema_version", "kind", "source_commit", "files"} or manifest.get("schema_version") != "1.0.0" or manifest.get("kind") != "github-pages-build-manifest":
    raise RuntimeError("Pages build manifest schema/identity drift")
if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_commit", "")):
    raise RuntimeError("Pages build manifest source commit is malformed")
expected_records = {}
for path in sorted(
    candidate for candidate in site.rglob("*")
    if candidate.is_file() and candidate != manifest_path and candidate.name != ".nojekyll"
):
    expected_records[str(path.relative_to(site))] = {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
    }
if manifest.get("files") != expected_records:
    raise RuntimeError("Pages build manifest does not exactly describe the assembled bundle")
if missing or present_forbidden or source_leaks or manufacturer_leaks or private_evidence_leaks:
    raise RuntimeError(
        f"Pages bundle invalid; missing={missing}; forbidden={present_forbidden}; "
        f"source_leaks={source_leaks}; manufacturer_leaks={sorted(set(manufacturer_leaks))}; "
        f"private_evidence_leaks={sorted(set(private_evidence_leaks))}"
    )
print(json.dumps({
    "status": "PASS", "required_files": len(required), "manifest_files": len(expected_records),
    "candidate_receipt_packaged": False, "review_evidence_packaged": False,
    "manufacturer_source_binaries": [],
}, indent=2, sort_keys=True))
