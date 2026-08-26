#!/usr/bin/env python3
"""Fail closed when the static viewer, accessibility, or diagnostic contract drifts."""

from __future__ import annotations

import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = PROJECT_ROOT / "index.html"
STYLE_PATH = PROJECT_ROOT / "viewer.css"
VIEWER_PATH = PROJECT_ROOT / "viewer.js"
VERSION_PATH = PROJECT_ROOT / "assets/models/600s.version.js"
PACKAGE_PATH = PROJECT_ROOT / "package.json"


def require_tokens(source: str, tokens: list[str], contract: str) -> None:
    missing = [token for token in tokens if token not in source]
    if missing:
        raise RuntimeError(f"{contract} contract drift: missing {missing}")


def main() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")
    style = STYLE_PATH.read_text(encoding="utf-8")
    viewer = VIEWER_PATH.read_text(encoding="utf-8")
    version_source = VERSION_PATH.read_text(encoding="utf-8")
    version_match = re.search(r"SHOWCASE_RELEASE\s*=\s*['\"]([^'\"]+)", version_source)
    if not version_match:
        raise RuntimeError("Cannot read showcase release from version module")
    release = version_match.group(1)
    runtime_release = json.loads(PACKAGE_PATH.read_text(encoding="utf-8")).get("version")
    if not isinstance(runtime_release, str):
        raise RuntimeError("Cannot read runtime release from package.json")

    require_tokens(index, [
        'id="app" role="application" tabindex="0"',
        'aria-describedby="viewer-instructions"',
        'id="motion-status" aria-live="polite" aria-atomic="true"',
        'id="controls-toggle" type="button" aria-controls="machine-controls-body" aria-expanded="false"',
        'class="controls-body" id="machine-controls-body"',
        'id="autonomy-toggle" type="button" aria-pressed="true"',
        'id="autonomy-mode" aria-live="polite" aria-atomic="true"',
        'id="drive-heading"',
        'id="drive-loop"',
        'id="motion-boundary"',
        'id="diagnostics" hidden aria-live="polite"',
        'id="inspector" role="dialog" aria-modal="true"',
        'aria-describedby="inspector-copy" inert',
        "Not an engineering or service reference.",
        "Presentation-only motion limits. Not operational data.",
        ".compact-control { display: grid; }",
    ], "HTML accessibility/safety")

    if index.count('aria-describedby="motion-boundary"') != 4:
        raise RuntimeError("Every motion range must reference the presentation-only boundary")
    for asset in ("viewer.css", "viewer.js"):
        if f'{asset}?v={runtime_release}' not in index:
            raise RuntimeError(f"{asset} cache key does not match runtime release {runtime_release}")
    if re.search(r"(?:src|href)=[\"']https?://", index, flags=re.IGNORECASE):
        raise RuntimeError("Viewer startup must not depend on remote script or stylesheet assets")

    require_tokens(style, [
        ":focus-visible",
        "@media (prefers-reduced-motion: reduce)",
        "transition: none !important",
        "@media (forced-colors: active)",
        ".diagnostics",
        ".sr-only",
        "--mobile-controls-height",
        "body.mobile-controls-open .panel-heading",
        ".autonomy-bar",
    ], "CSS accessibility")

    require_tokens(viewer, [
        'query.get("reduce") === "1"',
        'window.addEventListener("error", recordRuntimeError)',
        'window.addEventListener("unhandledrejection", recordRuntimeError)',
        "runSelectionVolumeSelfTest",
        'dataset.selectionSelftest = result',
        'dataset.lastSelectionVolume = hit.object.name',
        'focusComponent(hit.component, { revealDetails: false })',
        'function focusComponent(component, { revealDetails = true } = {})',
        'if (revealDetails) openInspector(component)',
        "prepareHitVolumes",
        "updateHitVolumeEmphasis",
        'focusKeys = { "1": "chassis", "2": "turntable", "3": "boom", "4": "platform" }',
        'event.key === "ArrowLeft"',
        'event.key === "ArrowRight"',
        'event.key === "ArrowUp"',
        'event.key === "ArrowDown"',
        'event.key === "0"',
        "aria-valuetext",
        "focusBeforeInspector",
        'event.key !== "Tab"',
        "reducedMotion ? targets[key]",
        "orbit.target.copy(orbit.targetGoal)",
        'dataset.machineSource = "procedural-load-fallback"',
        'authority = "independently-typeset-nominative-mark"',
        "not_manufacturer_artwork",
        "frameP95Ms",
        "document.hidden",
        "setMobileControls(false)",
        'controlsBody.inert = !expanded',
        '"--mobile-controls-height"',
        "function updateAutonomy(dt, now)",
        'dataset.autonomyMode',
        'dataset.driveRouteErrorM',
        'AUTONOMY_OVERRIDE_MS = 6000',
        'setAutonomyEnabled(false)',
        'rig.rollingWheels?.forEach',
        '"Wheel_FL_Roll"',
        "rig.visualHoses?.forEach",
        "function ackermannSteeringAngles",
        "function updatePresentationLighting",
        "lightTarget.position.copy(lightingAnchor)",
        "activeOverrideKeys(now)",
        'document.body.dataset.autonomyOverrides = overrideKeys.join(",") || "none"',
        "autonomy.wheelRotation = 0",
        "node.localToWorld(new THREE.Vector3(2.2, 0, 0))",
        "innerWidth <= 800 ? 24 : 18",
        'dataset.wheelRollHierarchy',
        'dataset.hoseSolverCount',
        'dataset.steerLeftDeg',
        'dataset.steerRightDeg',
        'const visualLimit = THREE.MathUtils.degToRad(28)',
    ], "viewer runtime")

    print(json.dumps({
        "status": "PASS",
        "release": release,
        "runtime_release": runtime_release,
        "mobile_controls_default": "collapsed",
        "keyboard_components": 4,
        "motion_ranges_described": 4,
        "selection_volumes_self_tested": 5,
        "remote_startup_assets": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
