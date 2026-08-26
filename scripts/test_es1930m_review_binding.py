#!/usr/bin/env python3
"""Adversarial checks for the acyclic ES executable-evidence binding."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from es1930m_review_binding import (
    ES_ARTIFACT,
    ROOT,
    UPSTREAM_600S_ARTIFACT,
    validate_artifact,
    validate_review_binding,
)
from validate_742_browser_evidence import validate_pending_template


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_failure(label: str, operation) -> None:
    try:
        operation()
    except (KeyError, TypeError, ValueError, RuntimeError):
        return
    raise RuntimeError(f"negative fixture unexpectedly passed: {label}")


def main() -> None:
    es_receipt = load(ROOT / "assets/models/es1930m.asset-receipt.json")
    receipt_600s = load(ROOT / "assets/models/600s.asset-receipt.json")
    review = load(ROOT / "docs/research/es1930m/REVIEW_EVIDENCE.json")
    artifact = load(ES_ARTIFACT)
    if artifact.get("capture_status") == "recapture-required":
        validate_pending_template(ES_ARTIFACT, "es1930m_browser_regression")
        validate_pending_template(UPSTREAM_600S_ARTIFACT, "600s_browser_regression")
        if es_receipt.get("review_binding", {}).get("status") != "pending_or_stale":
            raise RuntimeError("pending ES browser capture must keep the receipt review binding pending")
        if any(es_receipt.get("review_flags", {}).values()):
            raise RuntimeError("pending ES browser capture cannot preserve a positive review flag")
        print(json.dumps({
            "status": "PASS",
            "pending_transition": True,
            "pending_templates": 2,
            "negative_fixtures": 0,
        }, indent=2, sort_keys=True))
        return

    baseline = validate_artifact(ES_ARTIFACT, receipt=es_receipt, model="es1930m")
    binding_exact = es_receipt.get("review_binding", {}).get("status") == "exact_executable_predeploy_evidence"
    if binding_exact:
        validate_review_binding(review, receipt=es_receipt, receipt_600s=receipt_600s)
    elif es_receipt.get("review_binding", {}).get("status") != "pending_or_stale" or any(es_receipt.get("review_flags", {}).values()):
        raise RuntimeError("unbound fresh ES browser capture must remain explicitly pending")

    negatives = 0
    with tempfile.TemporaryDirectory(prefix="es1930m-review-binding-") as directory:
        temporary = Path(directory)

        envelope = load(ES_ARTIFACT)
        envelope["candidate_tree_sha256"] = "f" * 64
        envelope["reviewed_source_commit"] = "e" * 40
        envelope_path = temporary / "envelope.json"
        write(envelope_path, envelope)
        rebound = validate_artifact(envelope_path, receipt=es_receipt, model="es1930m")
        if rebound["evidence_sha256"] != baseline["evidence_sha256"]:
            raise RuntimeError("742 review envelope changed immutable ES evidence identity")

        semantic = load(ES_ARTIFACT)
        semantic["observations"]["assertions"]["pinch_zoom"]["after_desired_distance_m"] = "999.00"
        semantic_path = temporary / "semantic.json"
        write(semantic_path, semantic)
        expect_failure("semantic outcome mutation", lambda: validate_artifact(semantic_path, receipt=es_receipt, model="es1930m"))
        negatives += 1

        trace = load(ES_ARTIFACT)
        source_trace = ROOT / trace["capture_artifacts"]["automation_trace"]["path"]
        changed_trace = temporary / "trace.json"
        changed_trace.write_bytes(source_trace.read_bytes() + b"\n")
        trace["capture_artifacts"]["automation_trace"]["path"] = str(changed_trace)
        trace_path = temporary / "trace-artifact.json"
        write(trace_path, trace)
        expect_failure("raw trace byte mutation", lambda: validate_artifact(trace_path, receipt=es_receipt, model="es1930m"))
        negatives += 1

        pixels = load(ES_ARTIFACT)
        source_png = ROOT / pixels["capture_artifacts"]["screenshots"][0]["path"]
        changed_png = temporary / "capture.png"
        changed_png.write_bytes(source_png.read_bytes() + b"changed")
        pixels["capture_artifacts"]["screenshots"][0]["path"] = str(changed_png)
        pixels_path = temporary / "pixel-artifact.json"
        write(pixels_path, pixels)
        expect_failure("screenshot pixel mutation", lambda: validate_artifact(pixels_path, receipt=es_receipt, model="es1930m"))
        negatives += 1

        runner = load(ES_ARTIFACT)
        runner["capture_runner"]["sha256"] = "0" * 64
        runner_path = temporary / "runner.json"
        write(runner_path, runner)
        expect_failure("runner mutation", lambda: validate_artifact(runner_path, receipt=es_receipt, model="es1930m"))
        negatives += 1

        toolchain = load(ES_ARTIFACT)
        toolchain["environment"]["automation"]["version"] = "0.0.0"
        toolchain_path = temporary / "toolchain.json"
        write(toolchain_path, toolchain)
        expect_failure("toolchain mutation", lambda: validate_artifact(toolchain_path, receipt=es_receipt, model="es1930m"))
        negatives += 1

        runtime = copy.deepcopy(es_receipt)
        runtime["runtime"]["sha256"] = "0" * 64
        expect_failure("runtime identity mutation", lambda: validate_artifact(ES_ARTIFACT, receipt=runtime, model="es1930m"))
        negatives += 1

        if binding_exact:
            contradiction = copy.deepcopy(review)
            contradiction["binding"]["es_browser_evidence"]["assertions_sha256"] = "0" * 64
            expect_failure(
                "review evidence contradiction",
                lambda: validate_review_binding(contradiction, receipt=es_receipt, receipt_600s=receipt_600s),
            )
            negatives += 1

    print(json.dumps({
        "status": "PASS",
        "binding_status": "exact" if binding_exact else "pending",
        "envelope_exclusions": ["candidate_tree_sha256", "reviewed_source_commit"],
        "negative_fixtures": negatives,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
