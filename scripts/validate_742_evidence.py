#!/usr/bin/env python3
"""Validate the frozen 742 configuration and source-evidence ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research/742"
MANIFEST = RESEARCH / "SOURCE_MANIFEST.json"
EVIDENCE = RESEARCH / "MECHANISM_EVIDENCE.json"
CONFIG = ROOT / "machines/742/742.configuration.json"
MECHANISM = ROOT / "machines/742/mechanism.json"
REFERENCES = RESEARCH / "REFERENCES.md"
OWNED_RENDER_ALLOWLIST = ROOT / "docs/review/742/OWNED_RENDER_ALLOWLIST.json"
BROWSER_CAPTURE_ALLOWLIST = ROOT / "docs/review/742/BROWSER_CAPTURE_ALLOWLIST.json"
EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481"
PRIMARY_PUBLICATIONS = {"3132247", "3132245", "3122332100", "3122331300", "3122329900", "3122333200", "3122333100"}
ADMITTED = {"primary", "visual-only", "visual-envelope-only"}
SYMBOLIC_CLAIM_SOURCES = {"evidence-gap", "implementation-boundary"}
CLAIM_AUTHORITIES = {"verified-current", "reconstructed", "deferred", "mixed"}
GEOMETRY_USES = {
    "topology-only", "published-dimension", "prohibited",
    "published-dimension-plus-reconstruction", "published-limit-plus-reconstruction",
}
EVIDENCE_TYPES = {"topological", "functional", "dimensional", "visual"}
FORBIDDEN_SOURCE_SUFFIXES = {
    ".pdf", ".ifc", ".ifczip", ".zip", ".obj", ".stl", ".fbx", ".dae",
    ".step", ".stp", ".iges", ".igs", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
    ".webp", ".avif", ".bmp", ".gltf", ".glb", ".blend", ".3ds", ".dwg", ".dxf",
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_owned_render_allowlist() -> dict[Path, dict]:
    record = json.loads(OWNED_RENDER_ALLOWLIST.read_text(encoding="utf-8"))
    if set(record) != {"schema_version", "kind", "artifacts"}:
        raise RuntimeError("742 owned-render allowlist schema drift")
    if record["schema_version"] != "1.0.0" or record["kind"] != "owned-742-review-render-allowlist":
        raise RuntimeError("742 owned-render allowlist identity drift")
    allowed: dict[Path, dict] = {}
    fields = {"path", "sha256", "bytes", "width_px", "height_px", "provenance"}
    for artifact in record.get("artifacts") or []:
        if set(artifact) != fields:
            raise RuntimeError("742 owned-render record schema drift")
        relative = Path(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".png":
            raise RuntimeError(f"Unsafe 742 owned-render path: {relative}")
        if relative in allowed or not str(relative).startswith("docs/review/742/"):
            raise RuntimeError(f"Duplicate or out-of-scope 742 owned-render path: {relative}")
        path = ROOT / relative
        if not path.is_file() or digest(path) != artifact["sha256"] or path.stat().st_size != artifact["bytes"]:
            raise RuntimeError(f"742 owned-render artifact drift: {relative}")
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
            raise RuntimeError(f"742 owned-render is not a valid PNG: {relative}")
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != (artifact["width_px"], artifact["height_px"]):
            raise RuntimeError(f"742 owned-render dimensions drift: {relative}")
        if not isinstance(artifact["provenance"], str) or "independently authored" not in artifact["provenance"]:
            raise RuntimeError(f"742 owned-render provenance is not explicit: {relative}")
        allowed[relative] = artifact
    if not allowed:
        raise RuntimeError("742 owned-render allowlist is empty")
    return allowed


def read_browser_capture_allowlist() -> dict[Path, dict]:
    record = json.loads(BROWSER_CAPTURE_ALLOWLIST.read_text(encoding="utf-8"))
    if set(record) != {"schema_version", "kind", "artifacts"}:
        raise RuntimeError("742 browser-capture allowlist schema drift")
    if record["schema_version"] != "1.0.0" or record["kind"] != "742-browser-capture-allowlist":
        raise RuntimeError("742 browser-capture allowlist identity drift")
    allowed: dict[Path, dict] = {}
    fields = {"path", "sha256", "bytes", "kind", "mime_type", "width_px", "height_px", "provenance"}
    for artifact in record.get("artifacts") or []:
        if set(artifact) != fields:
            raise RuntimeError("742 browser-capture record schema drift")
        relative = Path(artifact["path"])
        if relative.is_absolute() or ".." in relative.parts or not str(relative).startswith("docs/review/742/browser-captures/"):
            raise RuntimeError(f"Unsafe 742 browser-capture path: {relative}")
        if relative in allowed:
            raise RuntimeError(f"Duplicate 742 browser-capture path: {relative}")
        if artifact["kind"] == "screenshot":
            if relative.suffix.lower() != ".png" or artifact["mime_type"] != "image/png":
                raise RuntimeError(f"742 browser screenshot identity drift: {relative}")
        elif artifact["kind"] == "automation_trace":
            if relative.suffix.lower() != ".json" or artifact["mime_type"] != "application/json":
                raise RuntimeError(f"742 automation trace identity drift: {relative}")
        else:
            raise RuntimeError(f"742 browser-capture kind drift: {relative}")
        path = ROOT / relative
        if not path.is_file() or digest(path) != artifact["sha256"] or path.stat().st_size != artifact["bytes"]:
            raise RuntimeError(f"742 browser-capture artifact drift: {relative}")
        if artifact["kind"] == "screenshot":
            data = path.read_bytes()
            if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
                raise RuntimeError(f"742 browser screenshot is not a valid PNG: {relative}")
            width, height = struct.unpack(">II", data[16:24])
            if (width, height) != (artifact["width_px"], artifact["height_px"]):
                raise RuntimeError(f"742 browser screenshot dimensions drift: {relative}")
        elif artifact["width_px"] is not None or artifact["height_px"] is not None:
            raise RuntimeError(f"742 automation trace cannot claim image dimensions: {relative}")
        if not isinstance(artifact["provenance"], str) or "local browser capture" not in artifact["provenance"].lower():
            raise RuntimeError(f"742 browser-capture provenance is not explicit: {relative}")
        allowed[relative] = artifact
    return allowed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources-dir", type=Path)
    parser.add_argument("--manifest-only", action="store_true", help="Validate the repository ledger without claiming source binaries were reverified.")
    parser.add_argument("--require-source-binaries", action="store_true", help="Fail unless every admitted frozen source binary is present and hash verified.")
    args = parser.parse_args()
    if args.manifest_only and args.sources_dir:
        raise RuntimeError("--manifest-only cannot be combined with --sources-dir")
    if args.require_source_binaries and not args.sources_dir:
        raise RuntimeError("--require-source-binaries requires --sources-dir")
    manifest = json.loads(MANIFEST.read_text())
    evidence = json.loads(EVIDENCE.read_text())
    config = json.loads(CONFIG.read_text())
    mechanism = json.loads(MECHANISM.read_text())
    if set(manifest) != {"schema_version", "evidence_freeze_date", "target", "repository_policy", "sources"}:
        raise RuntimeError("742 source manifest top-level schema drift")
    if manifest.get("schema_version") != "1.0.0" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", manifest.get("evidence_freeze_date", "")):
        raise RuntimeError("742 source manifest schema version/freeze date drift")
    if manifest.get("target") != {"model": "742", "pvc": "2411", "configuration_id": EXPECTED_ID}:
        raise RuntimeError("742 source manifest target drift")
    if set(evidence) != {"schema_version", "evidence_freeze_date", "configuration_id", "systems"}:
        raise RuntimeError("742 mechanism evidence top-level schema drift")
    if evidence.get("schema_version") != "1.0.0" or evidence.get("evidence_freeze_date") != manifest["evidence_freeze_date"]:
        raise RuntimeError("742 evidence schema/freeze identity drift")
    policy = manifest.get("repository_policy") or {}
    expected_policy_fields = {
        "source_binaries_committed", "signed_download_urls_committed", "manufacturer_geometry_committed",
        "manual_illustrations_are_scale_drawings", "verification_policy",
    }
    if set(policy) != expected_policy_fields or any(policy[name] is not False for name in expected_policy_fields - {"verification_policy"}):
        raise RuntimeError("742 repository evidence policy drift")
    if not isinstance(policy["verification_policy"], str) or not policy["verification_policy"]:
        raise RuntimeError("742 repository evidence verification policy is missing")
    identities = {
        manifest["target"]["configuration_id"], evidence["configuration_id"],
        config["configuration_id"], mechanism["configuration_id"],
    }
    if identities != {EXPECTED_ID} or config.get("pvc") != "2411":
        raise RuntimeError(f"742 configuration identity drift: {identities}")
    if config.get("target_release") != "1.4.0":
        raise RuntimeError("742 target release drift")
    choices = config.get("choices") or {}
    for key in ("engine", "drive", "steer", "tires", "cab", "carriage", "forks"):
        if not choices.get(key):
            raise RuntimeError(f"Frozen choice missing: {key}")
    expected_published_dimensions = {
        "length_less_forks": 5.76, "width": 2.46, "height": 2.43, "wheelbase": 3.42,
        "ground_clearance": 0.432, "outside_turning_radius": 3.66,
        "fork_length": 1.2192, "carriage_width": 1.27,
    }
    if config.get("published_dimensions_m") != expected_published_dimensions:
        raise RuntimeError("742 published dimension set drift")
    performance = config.get("published_performance") or {}
    if performance.get("maximum_lift_height_m") != 12.8 or performance.get("maximum_forward_reach_m") != 8.86:
        raise RuntimeError("742 published height/reach identity drift")
    if (config.get("visual_motion_limits") or {}).get("steer_degrees") != [-55, 55]:
        raise RuntimeError("742 evidence-derived 55-degree steering limit drift")
    expected_strokes = {
        "lift": 1.07, "telescope": 3.604, "head_tilt_slave": 0.388,
        "compensation_master": 0.278, "frame_sway": 0.168, "rear_axle_stabilization": 0.2,
    }
    if mechanism.get("hydraulic_cylinder_strokes_m") != expected_strokes:
        raise RuntimeError("742 evidence-derived hydraulic cylinder stroke set drift")
    if (mechanism.get("steering") or {}).get("visual_inner_limit_degrees") != 55:
        raise RuntimeError("742 mechanism steering limit drift")
    if (mechanism.get("boom") or {}).get("level_fork_surface_height_at_max_pose_m") != 12.8:
        raise RuntimeError("742 mechanism maximum-height target drift")
    reach_pose = mechanism.get("reach_pose") or {}
    if reach_pose.get("published_forward_reach_m") != 8.86 or reach_pose.get("load_center_m") != 0.6096:
        raise RuntimeError("742 mechanism maximum-reach proof identity drift")
    sources = manifest.get("sources") or []
    source_ids = [source.get("id") for source in sources]
    if len(source_ids) != len(set(source_ids)) or any(not value for value in source_ids):
        raise RuntimeError("742 source IDs are missing or duplicated")
    publications = {source.get("publication") for source in sources if source.get("admission") == "primary"}
    if publications != PRIMARY_PUBLICATIONS:
        raise RuntimeError(
            f"742 primary publication set drift: missing={sorted(PRIMARY_PUBLICATIONS - publications)} "
            f"extra={sorted(publications - PRIMARY_PUBLICATIONS)}"
        )
    primary_by_publication = {
        source["publication"]: source for source in sources
        if source.get("admission") == "primary" and source.get("publication")
    }
    expected_primary_pvc = {
        "3122332100": "2411", "3122331300": "2411", "3122329900": "2411",
        "3122333200": "2411", "3122333100": "2411",
        "3132247": "current-product", "3132245": "current-product-family",
    }
    for publication, pvc in expected_primary_pvc.items():
        if primary_by_publication[publication].get("pvc") != pvc:
            raise RuntimeError(f"Primary publication {publication} escaped its admitted PVC scope")
    admitted_sources = []
    filenames = []
    for source in sources:
        admission = source.get("admission", "")
        checksum = source.get("sha256")
        if admission in ADMITTED:
            admitted_sources.append(source)
            required = {"id", "kind", "sha256", "bytes", "local_filename", "admission"}
            if missing := sorted(required - source.keys()):
                raise RuntimeError(f"Admitted source {source.get('id')} missing {missing}")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum or "") or not isinstance(source.get("bytes"), int) or source["bytes"] <= 0:
                raise RuntimeError(f"Invalid checksum/byte count for {source.get('id')}")
            filename = source["local_filename"]
            if Path(filename).name != filename or Path(filename).suffix.lower() not in FORBIDDEN_SOURCE_SUFFIXES:
                raise RuntimeError(f"Unsafe or unexpected local filename for {source.get('id')}")
            filenames.append(filename)
            if admission == "primary" and not (source.get("url") or source.get("catalog_url")):
                raise RuntimeError(f"Primary source has no canonical locator: {source.get('id')}")
        if source.get("pvc") == "2605" and not admission.startswith("quarantined"):
            raise RuntimeError("PVC 2605 operation record escaped quarantine")
    if len(filenames) != len(set(filenames)):
        raise RuntimeError("742 admitted source filenames are duplicated")
    references = REFERENCES.read_text(encoding="utf-8")
    missing_reference_ids = sorted(source["id"] for source in admitted_sources if f"`{source['id']}`" not in references)
    if missing_reference_ids:
        raise RuntimeError(f"Public references do not resolve admitted manifest IDs: {missing_reference_ids}")
    systems = evidence.get("systems") or []
    system_ids = [system.get("id") for system in systems]
    if len(system_ids) != len(set(system_ids)) or any(not value for value in system_ids):
        raise RuntimeError("742 evidence system IDs are missing or duplicated")
    claims = [claim for system in systems for claim in system.get("claims", [])]
    ids = [claim.get("id") for claim in claims]
    if len(claims) < 12 or len(ids) != len(set(ids)):
        raise RuntimeError("742 mechanism evidence is incomplete or duplicated")
    required = {"id","statement","source","pvc","pages","components","part_numbers","evidence_type","authority","geometry_use","confidence"}
    for claim in claims:
        if missing := sorted(required - claim.keys()):
            raise RuntimeError(f"Claim {claim.get('id')} missing {missing}")
        if not claim["components"]:
            raise RuntimeError(f"Claim {claim['id']} has no component binding")
        if not isinstance(claim["statement"], str) or not claim["statement"].strip():
            raise RuntimeError(f"Claim {claim['id']} has no statement")
        if claim["authority"] not in CLAIM_AUTHORITIES or claim["geometry_use"] not in GEOMETRY_USES:
            raise RuntimeError(f"Claim {claim['id']} has an invalid authority/geometry-use enum")
        if not isinstance(claim["evidence_type"], list) or not claim["evidence_type"] or not set(claim["evidence_type"]).issubset(EVIDENCE_TYPES):
            raise RuntimeError(f"Claim {claim['id']} has an invalid evidence-type enum")
        if claim["authority"] in {"reconstructed", "deferred"} and claim["geometry_use"] != "prohibited":
            raise RuntimeError(f"Non-authoritative claim {claim['id']} cannot authorize geometry")
        if not isinstance(claim["part_numbers"], list) or any(not isinstance(value, str) for value in claim["part_numbers"]):
            raise RuntimeError(f"Claim {claim['id']} has invalid part numbers")
        expressions = claim["source"].split("+")
        unresolved = [value for value in expressions if value not in primary_by_publication and value not in SYMBOLIC_CLAIM_SOURCES]
        if unresolved:
            raise RuntimeError(f"Claim {claim['id']} has unresolved source expressions: {unresolved}")
        numeric_sources = [primary_by_publication[value] for value in expressions if value in primary_by_publication]
        if claim["authority"] == "mixed":
            if not numeric_sources or "implementation-boundary" not in expressions or claim["geometry_use"] not in {
                "published-dimension-plus-reconstruction", "published-limit-plus-reconstruction"
            }:
                raise RuntimeError(f"Mixed-authority claim {claim['id']} lacks its publication/reconstruction split")
        elif claim["geometry_use"] in {"published-dimension-plus-reconstruction", "published-limit-plus-reconstruction"}:
            raise RuntimeError(f"Non-mixed claim {claim['id']} uses a mixed geometry authority")
        if numeric_sources:
            page_limits = [source.get("pages") for source in numeric_sources if isinstance(source.get("pages"), int)]
            for page in claim["pages"]:
                if not isinstance(page, int) or page < 1 or (page_limits and page > max(page_limits)):
                    raise RuntimeError(f"Claim {claim['id']} has an impossible page expression: {page}")
        elif claim["pages"]:
            raise RuntimeError(f"Non-publication claim {claim['id']} must not assert source pages")

    by_claim_id = {claim["id"]: claim for claim in claims}
    required_mechanical_bindings = {
        "BOOM-003": ("3122333200+implementation-boundary", [7], "mixed", "published-dimension-plus-reconstruction"),
        "HYD-001": ("3122333200", [7], "verified-current", "published-dimension"),
        "DIM-001": ("3132247", [1], "verified-current", "published-dimension"),
        "DIM-002": ("3132247", [1], "verified-current", "published-dimension"),
        "DIM-003": ("3132247", [1], "verified-current", "published-dimension"),
        "DIM-004": ("3132247", [1], "verified-current", "published-dimension"),
        "DIM-005": ("implementation-boundary", [], "reconstructed", "prohibited"),
        "STEER-003": ("3122333200+3122332100+3122331300+implementation-boundary", [7, 16, 65], "mixed", "published-dimension-plus-reconstruction"),
    }
    for claim_id, expected in required_mechanical_bindings.items():
        claim = by_claim_id.get(claim_id) or {}
        observed = (claim.get("source"), claim.get("pages"), claim.get("authority"), claim.get("geometry_use"))
        if observed != expected:
            raise RuntimeError(f"Evidence-derived mechanical binding drift: {claim_id}: {observed}")

    owned_review_renders = read_owned_render_allowlist()
    browser_captures = read_browser_capture_allowlist()
    tracked_output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    tracked = [Path(value.decode()) for value in tracked_output.split(b"\0") if value]
    allowed_binary_artifacts = {
        Path("tools/blender_mcp_official/dist/blender_mcp_addon-1.0.0.zip"),
        Path("assets/social/equipment-explorer-pages-thumbnail.png"),
        Path("assets/models/600s.glb"), Path("assets/models/es1930m.glb"), Path("assets/models/742.glb"),
        Path("source/blender/600s-blockout-v0.2.blend"), Path("source/blender/600s-detailed-v0.3.blend"),
        Path("source/blender/600s-showcase-v1.0.blend"), Path("source/blender/600s-showcase-v1.1.blend"),
        Path("source/blender/es1930m-showcase-v1.0.blend"), Path("source/blender/742-showcase-v1.0.blend"),
        *owned_review_renders, *browser_captures,
    }
    leaked = sorted(
        str(path) for path in tracked
        if path.suffix.lower() in FORBIDDEN_SOURCE_SUFFIXES and path not in allowed_binary_artifacts
    )
    tracked_names = {path.name for path in tracked}
    leaked.extend(sorted(filename for filename in filenames if filename in tracked_names))
    manufacturer_hashes_by_size: dict[int, set[str]] = {}
    for source in admitted_sources:
        manufacturer_hashes_by_size.setdefault(source["bytes"], set()).add(source["sha256"])
    # Review captures may be created after the first candidate commit and before
    # the reviewed receipt/second commit. Scan every exact allowlisted artifact
    # now, not only the current Git index, so an untracked manufacturer image
    # cannot be laundered through a browser-screenshot or owned-render record.
    for relative in {*owned_review_renders, *browser_captures}:
        path = ROOT / relative
        if path.stat().st_size in manufacturer_hashes_by_size and digest(path) in manufacturer_hashes_by_size[path.stat().st_size]:
            leaked.append(str(relative))
    for relative in tracked:
        path = ROOT / relative
        if path.is_file() and path.stat().st_size in manufacturer_hashes_by_size:
            if digest(path) in manufacturer_hashes_by_size[path.stat().st_size]:
                leaked.append(str(relative))
    if leaked:
        raise RuntimeError(f"Manufacturer source binaries committed: {sorted(set(leaked))}")
    verified = []
    missing_binaries = [] if args.sources_dir else [source["local_filename"] for source in admitted_sources]
    if args.sources_dir:
        if not args.sources_dir.is_dir():
            raise RuntimeError(f"742 source directory is missing: {args.sources_dir}")
        for source in admitted_sources:
            filename, checksum = source["local_filename"], source["sha256"]
            path = args.sources_dir / filename
            if not path.is_file():
                missing_binaries.append(filename)
                continue
            if digest(path) != checksum:
                raise RuntimeError(f"Local source checksum drift: {filename}")
            if path.stat().st_size != source["bytes"]:
                raise RuntimeError(f"Local source byte count drift: {filename}")
            verified.append(filename)
    if args.require_source_binaries and missing_binaries:
        raise RuntimeError(f"Required frozen source binaries are missing: {sorted(missing_binaries)}")
    binary_status = "VERIFIED" if len(verified) == len(admitted_sources) else "NOT_VERIFIED"
    print(json.dumps({
        "status":"PASS",
        "configuration_id":EXPECTED_ID,
        "primary_publications":sorted(PRIMARY_PUBLICATIONS),
        "claims":len(claims),
        "source_expressions_resolved":True,
        "admitted_source_binaries":len(admitted_sources),
        "local_binaries_verified":sorted(verified),
        "local_binaries_verified_count":len(verified),
        "local_binaries_missing":sorted(missing_binaries),
        "frozen_source_binary_status":binary_status,
        "committed_source_binaries":0,
        "owned_review_renders_verified":len(owned_review_renders),
        "browser_captures_verified":len(browser_captures),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
