#!/usr/bin/env python3
"""Bind exact executable browser evidence to ES1930M predeployment gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from es1930m_review_binding import (
    ES_ARTIFACT,
    PREDEPLOY_GATES,
    ROOT,
    UPSTREAM_600S_ARTIFACT,
    digest,
    validate_artifact,
    validate_review_binding,
)


REVIEW = ROOT / "docs/research/es1930m/REVIEW_EVIDENCE.json"
ES_RECEIPT = ROOT / "assets/models/es1930m.asset-receipt.json"
RECEIPT_600S = ROOT / "assets/models/600s.asset-receipt.json"
STATIC_COMMANDS = (
    ("es_runtime_contract", [sys.executable, "-B", "scripts/validate_es1930m_runtime_contract.py"]),
    ("es_gestures", ["node", "scripts/validate_es1930m_gestures.mjs"]),
    ("es_figure_eight", ["node", "scripts/validate_es1930m_figure_eight.mjs"]),
    ("es_kinematics", [sys.executable, "-B", "scripts/validate_es1930m_kinematics.py"]),
    ("es_glb", [sys.executable, "-B", "scripts/validate_es1930m_glb.py"]),
    ("600s_suite", ["npm", "run", "check:600s"]),
)


def run_static_checks() -> dict:
    records = {}
    for name, command in STATIC_COMMANDS:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if completed.returncode:
            raise RuntimeError(f"Static predeploy check failed: {name}\n{completed.stdout}\n{completed.stderr}")
        records[name] = {"command": command, "status": "pass"}
    return records


def gate_record(gate: str, *, runtime_sha: str, asset_sha: str, evidence_sha: str) -> dict:
    summaries = {
        "stowed_silhouette_reviewed": "Exact current GLB loaded at desktop and mobile with bound screenshots, selection self-test pass and zero runtime errors.",
        "platform_controls_visual_reviewed": "The exact current maximum-pose browser capture and GLB contract include the authored platform-control hierarchy.",
        "raised_pose_browser_reviewed": "Executable controls reached 5.64 m platform height and captured the exact raised pose.",
        "extension_browser_reviewed": "Executable controls reached the verified 0.55 m deck extension and the kinematic/GLB gates passed.",
        "steering_boundary_reviewed": "Executable steering reached 80 mm right cylinder displacement and the route solver gate passed.",
        "figure_eight_presentation_reviewed": "Executable auto start, pause and resume passed with the 2400-sample route validator.",
        "mobile_drag_direction_reviewed": "Current mobile browser capture plus deterministic touch-direction and camera-basis tests passed; no physical device is claimed.",
        "accessibility_reviewed": "CDP accessibility tree, engineering slider values, modal focus trap, Escape restoration, live reduced-motion transition and all terminal alerts passed; no AT session is claimed.",
        "desktop_browser_zero_errors": "Exact current runtime loaded with zero runtime and console errors before browser interactions.",
        "mobile_and_pinch_reviewed": "390x844 controls and numeric camera-distance pinch proof passed in emulated Chromium; no physical touchscreen is claimed.",
        "selection_and_focus_reviewed": "The exported selection self-test and platform modal focus/restore browser assertions passed.",
        "performance_reviewed": "Exact current runtime reported a finite local Chromium FPS and p95 sample; no physical low-end device claim is made.",
        "600s_regression_suite_pass": "Exact current 600S browser regression, fatal-path suite, live reduced-motion transition and repository validators passed.",
    }
    return {
        "status": "pass",
        "reviewed_runtime_sha256": runtime_sha,
        "reviewed_asset_sha256": asset_sha,
        "browser_evidence_sha256": evidence_sha,
        "method": "Hash-bound executable local Chromium capture plus repository static/model validators",
        "evidence": summaries[gate],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", action="store_true", help="Write the validated binding and regenerate the ES receipt.")
    args = parser.parse_args()
    es_receipt = json.loads(ES_RECEIPT.read_text(encoding="utf-8"))
    receipt_600s = json.loads(RECEIPT_600S.read_text(encoding="utf-8"))
    static = run_static_checks()
    es = validate_artifact(ES_ARTIFACT, receipt=es_receipt, model="es1930m")
    upstream_600s = validate_artifact(UPSTREAM_600S_ARTIFACT, receipt=receipt_600s, model="600s")
    runtime_sha = es_receipt["runtime"]["sha256"]
    asset_sha = es_receipt["files"]["asset"]["sha256"]
    gates = {
        gate: gate_record(
            gate,
            runtime_sha=runtime_sha,
            asset_sha=asset_sha,
            evidence_sha=upstream_600s["evidence_sha256"] if gate == "600s_regression_suite_pass" else es["evidence_sha256"],
        )
        for gate in PREDEPLOY_GATES
    }
    gates["deployed_pages_reviewed"] = {
        "status": "pending",
        "reviewed_runtime_sha256": None,
        "reviewed_asset_sha256": None,
        "browser_evidence_sha256": None,
        "method": "Exact public deployment review is intentionally deferred until after Pages deployment.",
        "evidence": "No deployment, physical-device, or assistive-technology claim is made by this predeploy binding.",
    }
    review = {
        "schema_version": "3.0.0",
        "policy": "Predeploy gates pass only from immutable raw traces, screenshots, repository-owned runner/toolchain identity, normalized semantic assertions, and passing repository validators. The later 742 candidate/review binding envelope is excluded; public deployment remains a separate pending gate.",
        "binding": {
            "es_browser_artifact": str(ES_ARTIFACT.relative_to(ROOT)),
            "es_browser_evidence": es["evidence"],
            "600s_browser_artifact": str(UPSTREAM_600S_ARTIFACT.relative_to(ROOT)),
            "600s_browser_evidence": upstream_600s["evidence"],
            "static_checks": static,
            "physical_device_session": False,
            "assistive_technology_session": False,
            "deployment_claimed": False,
        },
        "gates": gates,
    }
    validate_review_binding(review, receipt=es_receipt, receipt_600s=receipt_600s)
    if args.bind:
        REVIEW.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, "-B", "scripts/write_es1930m_receipt.py"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "-B", "scripts/validate_es1930m_receipt.py", "--require-predeploy"], cwd=ROOT, check=True)
    print(json.dumps({"status": "PASS", "mode": "bound" if args.bind else "dry-run", "runtime_sha256": runtime_sha, "asset_sha256": asset_sha, "predeploy_gates": len(PREDEPLOY_GATES), "deployment_claimed": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
