#!/usr/bin/env python3
"""Write mechanical 600S receipt facts. Review evidence is preserved, never auto-accepted."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_600s_glb import (
    ASSET_VERSION,
    GLB_PATH,
    HASH_PREFIX_LEN,
    PROJECT_ROOT,
    RECEIPT_PATH,
    RECEIPT_TEMPLATE_PATH,
    REVIEW_FLAGS,
    sha256_file,
    validate,
    version_js_text,
)


VERSION_JS_PATH = PROJECT_ROOT / "assets/models/600s.version.js"

REVIEW_DEFAULT = {
    "loads_without_console_error": False,
    "articulation_pivots_pass": False,
    "selection_volumes_pass": False,
    "stowed_silhouette_reviewed": False,
    "working_pose_silhouette_pass": False,
    "mobile_view_reviewed": False,
    "provenance_reviewed": False,
    "evidence": {
        "browser": None,
        "motion": None,
        "selection": None,
        "silhouette_scope": None,
    },
}


def load_existing_record(sha256: str, source_blend_sha256: str, runtime_sha256: str) -> tuple[dict, str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if RECEIPT_PATH.is_file():
        current = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        if (
            current.get("sha256") == sha256
            and current.get("source_blend_sha256") == source_blend_sha256
            and current.get("runtime_sha256") == runtime_sha256
            and current.get("release") == ASSET_VERSION
        ):
            review = current.get("review")
            if isinstance(review, dict):
                merged = dict(REVIEW_DEFAULT)
                merged.update(review)
                merged["evidence"] = dict(REVIEW_DEFAULT["evidence"], **(review.get("evidence") or {}))
                return merged, current.get("exported_at") or now
    return dict(REVIEW_DEFAULT), now


def write_version_js(cache_key: str) -> None:
    VERSION_JS_PATH.write_text(version_js_text(cache_key), encoding="utf-8")


def main() -> None:
    # The manifest participates in the runtime hash, so update it before validation.
    write_version_js(sha256_file(GLB_PATH)[:HASH_PREFIX_LEN])
    mechanical = validate(require_receipt=False)
    review, exported_at = load_existing_record(
        mechanical["sha256"], mechanical["source_blend_sha256"], mechanical["runtime_sha256"]
    )
    accepted = all(review.get(flag) is True for flag in REVIEW_FLAGS)
    receipt = {
        "asset": mechanical["asset"],
        "status": "SHOWCASE_V1_1_ACCEPTED" if accepted else "SHOWCASE_V1_1_MECHANICAL_PASS",
        "release": ASSET_VERSION,
        "configuration_id": mechanical["configuration_id"],
        "authorship": "owned-simplified-reconstruction",
        "source_blend": mechanical["source_blend"],
        "builder": "scripts/build_600s_blockout.py",
        "validator": "scripts/validate_600s_glb.py",
        "exported_at": exported_at,
        "sha256": mechanical["sha256"],
        "source_blend_sha256": mechanical["source_blend_sha256"],
        "cache_key": mechanical["cache_key"],
        "runtime_sha256": mechanical["runtime_sha256"],
        "units": "meters",
        "root_node": "600S_ROOT",
        "visible_envelope_m": mechanical["visible_envelope_m"],
        "wheelbase_m": mechanical["wheelbase_m"],
        "ground_clearance_m": mechanical["ground_clearance_m"],
        "tailswing_m": mechanical["tailswing_m"],
        "platform_envelope_m": mechanical["platform_envelope_m"],
        "telescope_travel_m": mechanical["telescope_travel_m"],
        "telescope_overlap_at_100_m": mechanical["telescope_overlap_at_100_m"],
        "triangle_count": mechanical["triangle_count"],
        "node_count": mechanical["node_count"],
        "required_parent_edges": mechanical["required_parent_edges"],
        "interaction_volumes": mechanical["interaction_volumes"],
        "mechanical_validation": {
            "status": mechanical["status"],
            "bytes": mechanical["bytes"],
            "mesh_count": mechanical["mesh_count"],
            "visible_bounds_min_m": mechanical["visible_bounds_min_m"],
            "visible_bounds_max_m": mechanical["visible_bounds_max_m"],
            "telescope_overlap_stowed_m": mechanical["telescope_overlap_stowed_m"],
            "powertrack_push_tube_stowed_min_overlap_m": mechanical["powertrack_push_tube_stowed_min_overlap_m"],
            "powertrack_push_tube_full_travel_min_overlap_m": mechanical["powertrack_push_tube_full_travel_min_overlap_m"],
        },
        "review": review,
        "evidence_boundary": json.loads(RECEIPT_TEMPLATE_PATH.read_text(encoding="utf-8"))["evidence_boundary"],
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    write_version_js(mechanical["cache_key"])
    print(json.dumps({
        "status": "WROTE_RECEIPT",
        "receipt": str(RECEIPT_PATH.relative_to(PROJECT_ROOT)),
        "version_js": str(VERSION_JS_PATH.relative_to(PROJECT_ROOT)),
        "sha256": mechanical["sha256"],
        "cache_key": mechanical["cache_key"],
        "glb": str(GLB_PATH.relative_to(PROJECT_ROOT)),
        "review_auto_accepted": accepted,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
