#!/usr/bin/env python3
"""Adversarial tests for portable/current-run 742 deployment proof bindings."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from validate_742_receipt import verify_deployment_rebuild_binding
from verify_pages_deployment import copy_if_distinct


WORKFLOW_URL = "https://github.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/123456"
SOURCE_COMMIT = "1" * 40


def expect_failure(callback, message: str) -> None:
    try:
        callback()
    except RuntimeError:
        return
    raise RuntimeError(message)


def main() -> None:
    negative_cases = 0
    with tempfile.TemporaryDirectory(prefix="742-deployment-proof-") as directory:
        root = Path(directory)
        source = root / "742-deterministic-rebuild-attestation.json"
        source.write_bytes(b'{"fixture":true}\n')

        if copy_if_distinct(source, source) is not False or source.read_bytes() != b'{"fixture":true}\n':
            raise RuntimeError("same-path rebuild attestation copy was not a safe no-op")
        copied = root / "nested" / source.name
        copied.parent.mkdir()
        if copy_if_distinct(source, copied) is not True or copied.read_bytes() != source.read_bytes():
            raise RuntimeError("distinct rebuild attestation copy did not preserve bytes")

        record = {
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "bytes": source.stat().st_size,
            "authority": "generated_in_deployment_workflow",
            "workflow_run_url": WORKFLOW_URL,
            "source_commit": SOURCE_COMMIT,
        }
        verify_deployment_rebuild_binding(record, source, WORKFLOW_URL, SOURCE_COMMIT)

        for mutation, description in (
            ({"artifact_name": "742-frozen-source-evidence", "artifact_run_url": WORKFLOW_URL}, "legacy private-artifact authority"),
            ({"workflow_run_url": WORKFLOW_URL + "0"}, "different workflow run"),
            ({"source_commit": "2" * 40}, "different source commit"),
            ({"authority": "downloaded_private_artifact"}, "wrong authority"),
            ({"sha256": "0" * 64}, "wrong companion hash"),
            ({"bytes": source.stat().st_size + 1}, "wrong companion size"),
        ):
            forged = dict(record)
            if "artifact_name" in mutation:
                forged = {"sha256": record["sha256"], "bytes": record["bytes"], **mutation}
            else:
                forged.update(mutation)
            expect_failure(
                lambda candidate=forged: verify_deployment_rebuild_binding(
                    candidate, source, WORKFLOW_URL, SOURCE_COMMIT
                ),
                f"742 deployment proof accepted {description}",
            )
            negative_cases += 1

    print(json.dumps({
        "status": "PASS",
        "same_path_copy_noop": True,
        "negative_cases": negative_cases,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
