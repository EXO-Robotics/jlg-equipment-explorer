#!/usr/bin/env python3
"""Fail closed if the Pages bundle is incomplete or leaks non-public evidence."""

import hashlib
import json
import posixpath
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
workflow_source = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
posed_runner_source = (ROOT / "scripts/run_742_posed_glb_gate.py").read_text(encoding="utf-8")
posed_gate = "python3 -B scripts/run_742_posed_glb_gate.py"
if posed_gate not in (package.get("scripts") or {}).get("check:742", ""):
    raise RuntimeError("Pages CI contract requires the actual posed-GLB gate in check:742")
if 'os.environ.get("BLENDER_BIN")' not in posed_runner_source:
    raise RuntimeError("Posed-GLB runner must consume the checksum-pinned CI Blender path")
required_blender_ci_tokens = {
    'BLENDER_VERSION: "5.1.1"',
    "BLENDER_ARCHIVE: blender-5.1.1-linux-x64.tar.xz",
    "BLENDER_SHA256: 6f9fff89fef154ef7974d1a1c4b916ab4bc1f5618bcb48d5befee1bd0a7c7f2a",
    "BLENDER_BIN: ${{ github.workspace }}/.tooling/blender-5.1.1-linux-x64/blender",
    "https://mirror.blender.org/release/Blender5.1/blender-5.1.1-linux-x64.tar.xz",
    'test "$(uname -m)" = "x86_64"',
    'curl --fail --location --retry 3',
    'echo "${BLENDER_SHA256}  .tooling/${BLENDER_ARCHIVE}" | sha256sum --check -',
    'tar -xJf ".tooling/${BLENDER_ARCHIVE}" -C .tooling',
    'test -x "${BLENDER_BIN}"',
    'test "$("${BLENDER_BIN}" --version | head -n 1)" = "Blender ${BLENDER_VERSION}"',
    "npm run check",
}
missing_blender_ci_tokens = sorted(required_blender_ci_tokens - set(
    token for token in required_blender_ci_tokens if token in workflow_source
))
if missing_blender_ci_tokens:
    raise RuntimeError(f"Pages CI pinned-Blender contract drift: {missing_blender_ci_tokens}")
private_rebuild = "--rebuild-attestation _private-evidence/742/742-deterministic-rebuild-attestation.json"
deployment_rebuild = "--rebuild-attestation _attestations/742-deterministic-rebuild-attestation.json"
if (
    workflow_source.count(private_rebuild) != 2
    or workflow_source.count(deployment_rebuild) != 1
    or workflow_source.count("--require-release") != 1
):
    raise RuntimeError("Pages CI rebuild-attestation release path drift")
if workflow_source.index("Install checksum-pinned Blender 5.1.1") > workflow_source.index("npm run check"):
    raise RuntimeError("Pages CI must install pinned Blender before running the mandatory posed-GLB gate")
research = {
    "README.md", "REFERENCES.md", "CONFIGURATION.md", "DIMENSIONS.md", "ARTICULATION.md",
    "SOURCE_RECONCILIATION.md", "DETAILED_RECONSTRUCTION.md", "COMPARISON_MATRIX.md",
    "RIGHTS_AND_BIM_BOUNDARY.md", "SOURCE_MANIFEST.json", "MECHANISM_EVIDENCE.json",
    "reference-board/README.md",
}
required = {
    "index.html", "favicon.ico", "600s/index.html", "es1930m/index.html", "742/index.html", "viewer.css",
    "viewer/runtime.js", "viewer/742-runtime.js", "viewer/742.css", "viewer/presentation-route.mjs",
    "machines/742/machine.js", "machines/742/articulation.js", "machines/742/inspector.js",
    "machines/742/cameras.js", "machines/742/version.js", "machines/742/742.configuration.json",
    "machines/742/mechanism.json", "machines/742/solver.js", "assets/models/600s.glb", "assets/models/es1930m.glb",
    "assets/models/742.glb", "assets/models/600s.asset-receipt.json",
    "assets/models/es1930m.asset-receipt.json", "pages-build-manifest.json",
} | {f"docs/research/742/{path}" for path in research}
missing = sorted(path for path in required if not (site / path).is_file())
favicon = site / "favicon.ico"
favicon_routes = {
    "index.html": "./favicon.ico",
    "600s/index.html": "../favicon.ico",
    "742/index.html": "../favicon.ico",
    "es1930m/index.html": "../favicon.ico",
}
favicon_route_errors = []
for entry, expected_href in favicon_routes.items():
    html_path = site / entry
    source = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
    exact_link = f'<link rel="icon" href="{expected_href}" type="image/x-icon">'
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(entry), expected_href))
    if source.count(exact_link) != 1 or resolved != "favicon.ico":
        favicon_route_errors.append({"entry": entry, "href": expected_href, "resolved": resolved})
if not favicon.is_file() or favicon.stat().st_size <= 0 or favicon.read_bytes()[:4] != b"\x00\x00\x01\x00":
    favicon_route_errors.append({"target": "favicon.ico", "error": "missing-or-invalid-ico"})
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
if missing or favicon_route_errors or present_forbidden or source_leaks or manufacturer_leaks or private_evidence_leaks:
    raise RuntimeError(
        f"Pages bundle invalid; missing={missing}; favicon_routes={favicon_route_errors}; forbidden={present_forbidden}; "
        f"source_leaks={source_leaks}; manufacturer_leaks={sorted(set(manufacturer_leaks))}; "
        f"private_evidence_leaks={sorted(set(private_evidence_leaks))}"
    )
print(json.dumps({
    "status": "PASS", "required_files": len(required), "manifest_files": len(expected_records),
    "candidate_receipt_packaged": False, "review_evidence_packaged": False,
    "manufacturer_source_binaries": [], "favicon_routes_verified": len(favicon_routes),
    "posed_glb_ci_blender": "5.1.1-checksum-pinned",
}, indent=2, sort_keys=True))
