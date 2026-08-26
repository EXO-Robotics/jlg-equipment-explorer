#!/usr/bin/env python3
"""Fail closed if the Pages bundle is incomplete or leaks non-public evidence."""

import hashlib
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
workflow_source = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
receipt = json.loads((ROOT / "assets/models/742.asset-receipt.json").read_text(encoding="utf-8"))
posed_runner_source = (ROOT / "scripts/run_742_posed_glb_gate.py").read_text(encoding="utf-8")
rebuild_verifier_source = (ROOT / "scripts/verify_742_deterministic_rebuild.py").read_text(encoding="utf-8")
deployment_verifier_source = (ROOT / "scripts/verify_pages_deployment.py").read_text(encoding="utf-8")
receipt_validator_source = (ROOT / "scripts/validate_742_receipt.py").read_text(encoding="utf-8")
portable_posed_gate = "python3 -B scripts/validate_742_portable_posed_glb.py"
pinned_posed_invocation = 'BLENDER_BIN="${BLENDER_BIN}" python3 -B scripts/run_742_posed_glb_gate.py'


def validate_posed_gate_placement(package_check: str, workflow: str) -> None:
    if portable_posed_gate not in package_check:
        raise RuntimeError("Repository check:742 must include the portable posed-GLB gate")
    if "python3 -B scripts/run_742_posed_glb_gate.py" in package_check:
        raise RuntimeError("Pinned-Blender posed-GLB gate must remain a separate Pages workflow step")
    posed_step = workflow.find("- name: Run pinned-Blender posed-GLB companion gate")
    repository_step = workflow.find("- name: Validate repository contracts")
    deploy_step = workflow.find("- name: Deploy to GitHub Pages")
    if min(posed_step, repository_step, deploy_step) < 0:
        raise RuntimeError("Pages workflow posed/repository/deploy step contract is incomplete")
    if not posed_step < repository_step < deploy_step:
        raise RuntimeError("Pages workflow must run pinned posing before repository validation and deployment")
    posed_block = workflow[posed_step:repository_step]
    if pinned_posed_invocation not in posed_block or "> _attestations/742-blender-posed-glb-result.json" not in posed_block:
        raise RuntimeError("Pages workflow lacks the exact pinned-Blender posed-GLB invocation/result")


def expect_placement_failure(package_check: str, workflow: str, description: str) -> None:
    try:
        validate_posed_gate_placement(package_check, workflow)
    except RuntimeError:
        return
    raise RuntimeError(f"Pages posed-gate negative fixture passed: {description}")


package_check_742 = (package.get("scripts") or {}).get("check:742", "")
validate_posed_gate_placement(package_check_742, workflow_source)
expect_placement_failure(
    package_check_742.replace(portable_posed_gate, ""), workflow_source,
    "missing portable gate",
)
expect_placement_failure(
    package_check_742, workflow_source.replace(pinned_posed_invocation, "python3 -B scripts/run_742_posed_glb_gate.py"),
    "unpinned workflow invocation",
)
expect_placement_failure(
    package_check_742,
    workflow_source.replace("- name: Run pinned-Blender posed-GLB companion gate", "- name: Disabled pose companion gate"),
    "missing exact posed workflow step",
)
_posed_fixture_start = workflow_source.find("- name: Run pinned-Blender posed-GLB companion gate")
_repository_fixture_start = workflow_source.find("- name: Validate repository contracts")
_late_posed_workflow = (
    workflow_source[:_posed_fixture_start]
    + workflow_source[_repository_fixture_start:]
    + "\n"
    + workflow_source[_posed_fixture_start:_repository_fixture_start]
)
expect_placement_failure(package_check_742, _late_posed_workflow, "posed gate after deployment")
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
checkout_block = workflow_source.split("- name: Check out repository", 1)[-1].split("- name:", 1)[0]
if "fetch-depth: 0" not in checkout_block:
    raise RuntimeError("Pages CI must fetch full history before checking reviewed-source ancestry")
shallow = subprocess.check_output(
    ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True,
).strip()
if shallow != "false":
    raise RuntimeError("Pages validation requires a full-history checkout")
reviewed_source_commit = ((receipt.get("human_review") or {}).get("binding") or {}).get("reviewed_source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", reviewed_source_commit):
    raise RuntimeError("742 receipt reviewed-source commit is missing or malformed")
if subprocess.run(
    ["git", "cat-file", "-e", f"{reviewed_source_commit}^{{commit}}"], cwd=ROOT, check=False,
).returncode:
    raise RuntimeError("742 reviewed-source commit is absent from the full-history checkout")
if subprocess.run(
    ["git", "merge-base", "--is-ancestor", reviewed_source_commit, "HEAD"], cwd=ROOT, check=False,
).returncode:
    raise RuntimeError("742 reviewed-source commit is not an ancestor of the Pages candidate")
rebuild_companion = "_attestations/742-deterministic-rebuild-attestation.json"
required_rebuild_ci_tokens = {
    'test "${GITHUB_SHA}" = "$(git rev-parse HEAD)"',
    "git diff --exit-code",
    "git diff --cached --exit-code",
    "python3 -B scripts/verify_742_deterministic_rebuild.py",
    '--blender "${BLENDER_BIN}"',
    f"--output {rebuild_companion}",
    "--require-human-reviewed",
    "--require-release",
    "git merge-base --is-ancestor",
}
missing_rebuild_ci_tokens = sorted(token for token in required_rebuild_ci_tokens if token not in workflow_source)
if missing_rebuild_ci_tokens:
    raise RuntimeError(f"Pages CI in-job deterministic-rebuild contract drift: {missing_rebuild_ci_tokens}")
if workflow_source.count("python3 -B scripts/verify_742_deterministic_rebuild.py") != 1:
    raise RuntimeError("Pages CI must perform exactly one two-build deterministic-rebuild invocation")
required_two_build_tokens = {
    'build_once(args.blender, temp / "run-1")',
    'build_once(args.blender, temp / "run-2")',
    "run1_glb != run2_glb or run1_glb != committed_glb",
}
missing_two_build_tokens = sorted(token for token in required_two_build_tokens if token not in rebuild_verifier_source)
if missing_two_build_tokens:
    raise RuntimeError(f"742 deterministic rebuild no longer proves two current-GLB builds: {missing_two_build_tokens}")
required_deployment_authority_tokens = {
    '"authority": "generated_in_deployment_workflow"',
    '"workflow_run_url": args.workflow_run_url',
    '"source_commit": manifest["source_commit"]',
    "copy_if_distinct(args.rebuild_attestation, rebuild_copy)",
}
missing_deployment_authority_tokens = sorted(
    token for token in required_deployment_authority_tokens if token not in deployment_verifier_source
)
if missing_deployment_authority_tokens:
    raise RuntimeError(f"Pages deployment rebuild-authority contract drift: {missing_deployment_authority_tokens}")
for token in ('"authority"', '"workflow_run_url"', '"source_commit"', 'generated_in_deployment_workflow'):
    if token not in receipt_validator_source:
        raise RuntimeError(f"742 receipt no longer verifies in-job rebuild authority: {token}")
private_rebuild = "_private-evidence/742/742-deterministic-rebuild-attestation.json"
if private_rebuild in workflow_source or workflow_source.count(f"--rebuild-attestation {rebuild_companion}") != 3:
    raise RuntimeError("Pages CI must use only its in-job deterministic-rebuild companion")
install_index = workflow_source.index("Install checksum-pinned Blender 5.1.1")
rebuild_index = workflow_source.index("python3 -B scripts/verify_742_deterministic_rebuild.py")
validation_index = workflow_source.index("npm run check")
deploy_index = workflow_source.index("uses: actions/deploy-pages@")
predeploy_index = workflow_source.index("Enforce strict 742 predeployment gate")
configure_index = workflow_source.index("uses: actions/configure-pages@")
upload_index = workflow_source.index("uses: actions/upload-pages-artifact@")
http_verify_index = workflow_source.index("Verify exact deployed 742 public surface")
final_release_index = workflow_source.index("--require-release")
if not install_index < rebuild_index < validation_index < predeploy_index < configure_index < upload_index < deploy_index:
    raise RuntimeError("Pages CI must install Blender, rebuild twice, validate, then deploy in that order")
if not deploy_index < http_verify_index < final_release_index:
    raise RuntimeError("Only HTTP verification and final release confirmation may run after Pages deployment")
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
    "full_history_checkout": True, "reviewed_source_ancestry": True,
}, indent=2, sort_keys=True))
