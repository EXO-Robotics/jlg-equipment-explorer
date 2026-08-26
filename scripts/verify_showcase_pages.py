#!/usr/bin/env python3
"""Verify every deployed combined-showcase byte and write a presentation-only attestation."""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


def fetch(url, expected=None):
    status, payload = 0, b""
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "equipment-explorer-showcase-verifier/1.0"}), timeout=30) as response:
                status, payload = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, payload = error.code, error.read()
        except urllib.error.URLError:
            status, payload = 0, b""
        actual = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        if status == 200 and (expected is None or actual == expected):
            return status, payload
        if attempt < 7:
            time.sleep(5)
    return status, payload


parser = argparse.ArgumentParser()
parser.add_argument("--base-url", required=True)
parser.add_argument("--build-manifest", type=Path, required=True)
parser.add_argument("--workflow-run-url", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
base = args.base_url.rstrip("/") + "/"
if not re.fullmatch(r"https://exo-robotics\.github\.io/jlg-equipment-explorer/", base):
    raise RuntimeError(f"Unexpected Pages base URL: {base}")
if not re.fullmatch(r"https://github\.com/EXO-Robotics/jlg-equipment-explorer/actions/runs/\d+", args.workflow_run_url):
    raise RuntimeError("Malformed deployment workflow URL")

manifest_bytes = args.build_manifest.read_bytes()
manifest = json.loads(manifest_bytes)
manifest_url = urllib.parse.urljoin(base, "pages-build-manifest.json")
status, deployed_manifest = fetch(manifest_url)
if status != 200 or deployed_manifest != manifest_bytes:
    raise RuntimeError("Deployed build manifest does not exactly match the workflow artifact")

verified = {}
for relative, expected in sorted(manifest["files"].items()):
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative:
        raise RuntimeError(f"Unsafe manifest path: {relative}")
    url = urllib.parse.urljoin(base, relative)
    file_status, payload = fetch(url, expected)
    actual = {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    if file_status != 200 or actual != expected:
        raise RuntimeError(f"Deployed file drift: {relative}: {file_status} {actual} != {expected}")
    verified[relative] = {"url": url, "http_status": file_status, **actual}

for route in ("", "600s/", "742/", "es1930m/"):
    route_status, _ = fetch(urllib.parse.urljoin(base, route))
    if route_status != 200:
        raise RuntimeError(f"Showcase route unavailable: /{route}")

record = {
    "schema_version": "1.0.0", "kind": "public-presentation-not-release",
    "source_commit": manifest["source_commit"], "workflow_run_url": args.workflow_run_url,
    "base_url": base, "pages_build_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    "routes_http_200": ["/", "/600s/", "/742/", "/es1930m/"], "verified_files": verified,
    "release_certification": "not_asserted",
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "PASS", "kind": record["kind"], "verified_files": len(verified)}, sort_keys=True))
