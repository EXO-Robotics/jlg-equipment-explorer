#!/usr/bin/env python3
"""Adversarial tests for checkout-independent posed-GLB result identity."""

from __future__ import annotations

import json
from pathlib import Path

from run_742_posed_glb_gate import (
    EXPECTED_ASSET_PATH,
    canonical_posed_glb_asset_path,
    canonicalize_posed_glb_result,
)


def expect_failure(callback, message: str) -> None:
    try:
        callback()
    except RuntimeError:
        return
    raise RuntimeError(message)


def main() -> None:
    checkout_a = Path("/private/tmp/742-portability/workspace-a")
    checkout_b = Path("/private/tmp/742-portability/different/workspace-b")
    values = [
        canonical_posed_glb_asset_path(EXPECTED_ASSET_PATH, checkout_a),
        canonical_posed_glb_asset_path(str(checkout_a / EXPECTED_ASSET_PATH), checkout_a),
        canonical_posed_glb_asset_path(str(checkout_b / EXPECTED_ASSET_PATH), checkout_b),
    ]
    if values != [EXPECTED_ASSET_PATH] * 3:
        raise RuntimeError("alternate checkout roots did not normalize to one canonical posed-GLB asset identity")

    original = {"status": "PASS", "asset": str(checkout_a / EXPECTED_ASSET_PATH), "measurement": 1}
    normalized = canonicalize_posed_glb_result(original, checkout_a)
    if normalized["asset"] != EXPECTED_ASSET_PATH or original["asset"] == EXPECTED_ASSET_PATH:
        raise RuntimeError("posed-GLB result normalization mutated input or retained an absolute path")

    negative_cases = 0
    for value, root, description in (
        (str(checkout_b / EXPECTED_ASSET_PATH), checkout_a, "absolute path from a different checkout"),
        ("../assets/models/742.glb", checkout_a, "parent traversal"),
        ("assets/models/not-742.glb", checkout_a, "wrong asset"),
        ("", checkout_a, "empty asset path"),
    ):
        expect_failure(
            lambda candidate=value, repository=root: canonical_posed_glb_asset_path(candidate, repository),
            f"accepted {description}",
        )
        negative_cases += 1

    print(json.dumps({
        "status": "PASS",
        "canonical_asset": EXPECTED_ASSET_PATH,
        "alternate_workspace_roots": 2,
        "negative_cases": negative_cases,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
