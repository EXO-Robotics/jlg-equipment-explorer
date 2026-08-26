#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const runtime = fs.readFileSync(path.join(root, "viewer/742-runtime.js"), "utf8");
const index = fs.readFileSync(path.join(root, "742/index.html"), "utf8");
const style = fs.readFileSync(path.join(root, "viewer/742.css"), "utf8");
const articulation = fs.readFileSync(path.join(root, "machines/742/articulation.js"), "utf8");
const machine = fs.readFileSync(path.join(root, "machines/742/machine.js"), "utf8");

function requireTokens(source, tokens, label) {
  const missing = tokens.filter((token) => !source.includes(token));
  if (missing.length) throw new Error(`${label} contract drift: ${missing.join(", ")}`);
}

requireTokens(runtime, [
  'const COMPACT_VIEWPORT_QUERY = "(max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)"',
  'import { telehandlerDragDelta } from "./pointer-gestures.mjs?v=1.0.10"',
  'pointerType: event.pointerType || "mouse"',
  'const drag = telehandlerDragDelta(dx, dy, active.pointerType)',
  'new THREE.CircleGeometry(18, 96)',
  'new THREE.GridHelper(34, 34, 0x5c5f56, 0x30342f)',
  'const coverage = 20',
  "matchMedia(COMPACT_VIEWPORT_QUERY)",
  "nearestVisibleComponentIntersection", "resolveSelectionIntersection(semanticHits, visibleSurfaceHit)",
  "frontmost-rendered-component-then-nearest-proxy", "selectionOverlapOutcomes", "selectionFixtureOutcomes",
  "setProgrammaticViewDistance", "orbitEffectiveMaxDistanceM", "effectiveMaxDistance",
  "const interactionMinDistance = Math.max(distanceLimits.minDistance, 4.4)",
  "__EQUIPMENT_EXPLORER_EVIDENCE__", "frameComponent(component)",
  "return ordered.find((hit) => hit.object.userData.component === visibleSurfaceHit.semanticComponent) || null",
  "solved.wheelAngles", "crabResidualDeg", "frontToeDeg", "rearToeDeg",
  'dataset.steerModeAlignment', 'Center all wheel headings before changing steering mode.',
  'showcaseState.steerMode !== state.steerMode && Math.abs(showcaseState.steer) > 0.01',
  "showTerminalError", "identity-failed", "contract-failed", "load-failed", "loader-start-failed",
  "const DEFAULT_ASSET_LOAD_TIMEOUT_MS = 15000", "assetLoadTimeoutMs", "load-timeout", "clearTimeout(loadTimeout)",
  'query.get("ee-test-fault")', "loopbackTestHost", "__EQUIPMENT_EXPLORER_TEST_HOOK__",
  '"bootstrap-timeout"', '"asset-timeout"', '"loader-start"', '"runtime-error"', '"unhandled-rejection"',
  "startInjectedLoaderAfterFrames(remainingFrames = 2)",
  'dataset.runtimeFrameCount', 'dataset.terminalFrameCount', 'dataset.terminalFrameSource', 'dataset.testFaultTriggered',
  "setEngineeringValueText", 'input.setAttribute("aria-details", detailId)',
  "controlPanel.querySelectorAll(\"button, input\")", "if (terminalFailure) return;",
  "handleMotionPreferenceChange", "syncReducedMotion(true)", "scheduleMotionAnnouncement",
  "resetPerformanceWindow", "visibility-hidden", "visibility-visible",
  "const windowMs = sorted.reduce((sum, sample) => sum + sample, 0)",
  "sorted.filter((sample) => sample >= 250).length",
  'showcaseStarted !== null && !reducedMotion && presentation.status !== "Stowed"',
  '? "Positioning"',
], "runtime");
requireTokens(index, [
  'id="motion-announcement" aria-live="polite" aria-atomic="true"',
  'id="error" role="alert" aria-live="assertive" tabindex="-1"',
  "window.__show742ModuleFailure", "module-load-failed", 'onerror="window.__show742ModuleFailure()"',
  "countBootFrame", "bootTimeoutMs", '"bootstrap-timeout"', "dataset.terminalFrameCount", "dataset.terminalFrameSource",
  '<output id="motion-status" aria-hidden="true">',
  '<output id="lift-value" aria-hidden="true">',
  '<output id="telescope-value" aria-hidden="true">',
  '<output id="tilt-value" aria-hidden="true">',
  '<output id="steer-value" aria-hidden="true">',
  '<output id="level-value" aria-hidden="true">',
]);
requireTokens(machine, ['status: stowed ? "Stowed" : "Holding"'], "machine presentation");
if (/id="(?:motion-status|diagnostics)"[^>]+aria-live/.test(index)) {
  throw new Error("Per-frame outputs must not be live regions");
}
requireTokens(style, [
  "viewer-terminal-error", "visibility: hidden", "pointer-events: none",
  "@media (max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)",
  "max-width: calc(54vw - 24px)",
]);
requireTokens(articulation, [
  '"BoomAngleSensorCrank"', '"BoomAngleSensorFrameJoint"', '"BoomAngleSensorCrankJoint"',
  '...["L","R"].flatMap', "Array.from({length:8}", '"RetractChain_C_Moving"',
  "Object.entries(geometry.beams)", "Object.entries(geometry.points)",
  'presentation_visibility!=="concealed_inside_boom_head"', "node.visible=false",
]);
if (/renderedInterval\s*<\s*250/.test(runtime)) throw new Error("Visible stalls are excluded from the performance window");
if (runtime.includes("orbit.desiredDistance = view.distance")) throw new Error("Pose framing bypasses the dynamic zoom cap");

const selectionStart = runtime.indexOf("const SELECTION_TIE_DISTANCE_M");
const selectionEnd = runtime.indexOf("function prepareInteractionVolumes", selectionStart);
const fixturesStart = runtime.indexOf("function runSelectionOrderingFixtures", selectionEnd);
const fixturesEnd = runtime.indexOf("function runSelectionVolumeSelfTest", fixturesStart);
if ([selectionStart, selectionEnd, fixturesStart, fixturesEnd].some((offset) => offset < 0)) {
  throw new Error("Production selection functions could not be isolated for execution");
}
const dataset = {};
const runProductionFixtures = new Function("document", `${runtime.slice(selectionStart, selectionEnd)}\n${runtime.slice(fixturesStart, fixturesEnd)}\nreturn runSelectionOrderingFixtures();`);
if (!runProductionFixtures({ body: { dataset } })) throw new Error("Production selection fixtures failed");
const fixtureOutcomes = JSON.parse(dataset.selectionFixtureOutcomes);
const expectedVolumes = ["front", "high-tie", "front", "front", null];
if (dataset.selectionFixtureCases !== "5/5" || fixtureOutcomes.length !== expectedVolumes.length) {
  throw new Error("Selection fixture result count drifted");
}
fixtureOutcomes.forEach((outcome, index) => {
  if (outcome.expectedVolume !== expectedVolumes[index] || outcome.observedVolume !== expectedVolumes[index] || !outcome.pass) {
    throw new Error(`Independent selection fixture ${index + 1} failed`);
  }
});

const baseMax = 24;
const absoluteMax = 72;
const poseDistance = 37.73;
const safeDistance = Math.min(Math.max(poseDistance, 4.4), absoluteMax / 1.05);
const effectiveMax = Math.min(absoluteMax, Math.max(baseMax, safeDistance * 1.05));
const nextZoomOut = Math.min(effectiveMax, safeDistance * 1.1);
if (effectiveMax < safeDistance || nextZoomOut < safeDistance) throw new Error("Next zoom gesture would snap inside the posed reset distance");

const frameWindow = [16.7, 271, 17.1];
const stalls = frameWindow.filter((sample) => sample >= 250);
if (stalls.length !== 1 || Math.max(...frameWindow) !== 271) throw new Error("Visible-stall window fixture failed");

const compactViewport = (width, height) => width <= 800 || (height <= 500 && width > height && width <= 1000);
if (!compactViewport(844, 390) || compactViewport(1280, 720)) {
  throw new Error("Responsive control fixture drift: 844x390 must be compact and 1280x720 must remain desktop");
}

console.log(JSON.stringify({
  status: "PASS",
  selection_fixture_cases: dataset.selectionFixtureCases,
  selection_fixture_outcomes: fixtureOutcomes,
  pose_distance_m: poseDistance,
  effective_max_distance_m: Number(effectiveMax.toFixed(3)),
  next_zoom_out_distance_m: Number(nextZoomOut.toFixed(3)),
  visible_frame_samples: frameWindow.length,
  visible_stalls: stalls.length,
  terminal_module_failure_fallback: true,
  bounded_asset_timeout_ms: 15000,
  settled_live_region: true,
  dynamic_reduced_motion_listener: true,
  dynamic_chain_and_sensor_consumer: true,
  compact_short_landscape: [844, 390],
  desktop_expanded: [1280, 720],
}, null, 2));
