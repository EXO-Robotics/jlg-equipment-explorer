#!/usr/bin/env python3
"""Fail closed when the isolated 742 route or static interaction contract drifts."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "742/index.html").read_text()
RUNTIME = (ROOT / "viewer/742-runtime.js").read_text()
MACHINE = (ROOT / "machines/742/machine.js").read_text()
STYLE = (ROOT / "viewer/742.css").read_text()
SHARED_RUNTIME = (ROOT / "viewer/runtime.js").read_text()
SHARED_STYLE = (ROOT / "viewer/multi-machine.css").read_text()
VERSION = (ROOT / "machines/742/version.js").read_text()
ASSET = ROOT / "assets/models/742.glb"
CONFIG = json.loads((ROOT / "machines/742/742.configuration.json").read_text())


def require(source, tokens, label):
    missing = [token for token in tokens if token not in source]
    if missing:
        raise RuntimeError(f"{label} contract drift: {missing}")


def main():
    require(INDEX, [
        'body data-machine="742"', 'id="app" role="application" tabindex="0"', 'aria-describedby="viewer-instructions"',
        'id="motion-status" aria-live="polite" aria-atomic="true"', 'id="controls-toggle"', 'id="machine-controls-body"',
        'id="lift-control"', 'id="telescope-control"', 'id="tilt-control"', 'id="steer-control"', 'id="level-control"',
        'data-steer-mode="circle"', 'data-steer-mode="crab"', 'data-steer-mode="front"', 'id="showcase"', 'id="stow"',
        'id="inspector" role="dialog" aria-modal="true"', 'aria-describedby="inspector-copy" inert',
        'href="../viewer/742.css?', 'src="../viewer/742-runtime.js?',
        'Presentation-only mechanism limits.', 'No load, stability, service, training, or safety behavior is simulated.',
    ], "742 HTML")
    if INDEX.count('aria-describedby="motion-boundary"') != 5:
        raise RuntimeError("Every 742 range must reference the safety boundary")
    if INDEX.count('data-focus=') != 7:
        raise RuntimeError("742 component navigation must expose seven focus targets")
    require(RUNTIME, [
        'import JLG742_MACHINE from "../machines/742/machine.js?v=', 'const pointers = new Map()',
        'gestureUsedPinch', '!gestureUsedPinch', 'pinchStartDistance', 'pointercancel',
        'velocityAzimuth', 'frameP95Ms', 'data-steer-mode', 'machine.showcase', '/^[1-7]$/',
        'controlsBody.inert = !expanded', 'query.get("reduce") === "1"',
        'event.key === "Escape"', 'event.key !== "Tab"', 'modalBackground.forEach',
        'setInert(element, true)', 'setInert(inspector, false)', 'restoreTarget.focus',
        'setAttribute("aria-valuetext", value)', 'runSelectionVolumeSelfTest()',
        'raycaster.intersectObjects(selectionVolumes, false)', 'hit.castShadow = false',
        'document.body.dataset.selectionSelftest =', 'document.body.dataset.machineSource = "contract-failed"',
    ], "dedicated 742 runtime")
    if "const touches = new Map()" in RUNTIME:
        raise RuntimeError("Legacy multi-touch implementation returned to the 742 runtime")
    if 'JLG742_MACHINE' in SHARED_RUNTIME or '"742"' in SHARED_RUNTIME or 'body[data-machine="742"]' in SHARED_STYLE:
        raise RuntimeError("742 implementation leaked back into ES1930M shared runtime/style")
    require(MACHINE, [
        '742-PVC2411-US-STD-OC-D36-FF370-C50-PF481', 'interactionVolumes', 'showcase(t)',
        'steerMode: "circle"', 'JLG742_GLB_URL',
    ], "742 machine module")
    require(STYLE, ['body[data-machine="742"]', '.mode-row', '.component-nav-seven', '.nav-overflow-cue'], "742 style")
    if not ASSET.is_file():
        raise RuntimeError("742 route asset is missing")
    asset_sha = hashlib.sha256(ASSET.read_bytes()).hexdigest()
    if asset_sha not in VERSION:
        raise RuntimeError("742 version module does not contain the exact GLB hash")
    version_release = re.search(r'JLG742_RELEASE\s*=\s*"(\d+\.\d+\.\d+)"', VERSION)
    if not version_release or version_release.group(1) != CONFIG.get("target_release"):
        raise RuntimeError("742 route release identity does not match the frozen configuration")
    preload = re.search(r'742\.glb\?v=([0-9a-f]+)', INDEX)
    if not preload or preload.group(1) != asset_sha[:len(preload.group(1))] or len(preload.group(1)) < 12:
        raise RuntimeError("742 HTML preload cache identity does not match the exact GLB")
    runtime_release = re.search(r'data-runtime-release="([^"]+)"', INDEX)
    if not runtime_release or INDEX.count(f'?v={runtime_release.group(1)}') != 2:
        raise RuntimeError("742 dedicated runtime/style cache identities disagree")
    print(json.dumps({
        "status":"PASS", "route":"/742/", "isolated_runtime":"viewer/742-runtime.js",
        "isolated_style":"viewer/742.css", "shared_es_runtime_unchanged_by_742":True,
        "motion_ranges":5, "steering_modes":3, "component_focus_targets":7,
        "pinch_zoom":True, "pinch_click_suppression":True, "inertia":True,
        "modal_focus_contract":True, "engineering_aria_value_text":True,
        "semantic_volume_self_test":True, "asset_failure_ui":True, "performance_p95_diagnostic":True,
        "asset_sha256":asset_sha,
        "candidate_release":CONFIG["target_release"], "runtime_release":runtime_release.group(1),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
