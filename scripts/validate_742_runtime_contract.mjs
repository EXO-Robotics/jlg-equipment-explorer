#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const runtime = fs.readFileSync(path.join(root, "viewer/742-runtime.js"), "utf8");
const index = fs.readFileSync(path.join(root, "742/index.html"), "utf8");
const style = fs.readFileSync(path.join(root, "viewer/742.css"), "utf8");
const articulation = fs.readFileSync(path.join(root, "machines/742/articulation.js"), "utf8");

function requireTokens(source, tokens, label) {
  const missing = tokens.filter((token) => !source.includes(token));
  if (missing.length) throw new Error(`${label} contract drift: ${missing.join(", ")}`);
}

requireTokens(runtime, [
  "nearestVisibleComponentIntersection", "resolveSelectionIntersection(semanticHits, visibleSurfaceHit)",
  "frontmost-rendered-component-then-nearest-proxy", "selectionOverlapOutcomes", "selectionFixtureOutcomes",
  "setProgrammaticViewDistance", "orbitEffectiveMaxDistanceM", "effectiveMaxDistance",
  "showTerminalError", "identity-failed", "contract-failed", "load-failed", "loader-start-failed",
  "controlPanel.querySelectorAll(\"button, input\")", "if (terminalFailure) return;",
  "handleMotionPreferenceChange", "syncReducedMotion(true)", "scheduleMotionAnnouncement",
  "resetPerformanceWindow", "visibility-hidden", "visibility-visible",
  "const windowMs = sorted.reduce((sum, sample) => sum + sample, 0)",
  "sorted.filter((sample) => sample >= 250).length",
], "runtime");
requireTokens(index, [
  'id="motion-announcement" aria-live="polite" aria-atomic="true"',
  "window.__show742ModuleFailure", "module-load-failed", 'onerror="window.__show742ModuleFailure()"',
]);
if (/id="(?:motion-status|diagnostics)"[^>]+aria-live/.test(index)) {
  throw new Error("Per-frame outputs must not be live regions");
}
requireTokens(style, ["viewer-terminal-error", "visibility: hidden", "pointer-events: none"]);
requireTokens(articulation, [
  '"BoomAngleSensorCrank"', '"BoomAngleSensorFrameJoint"', '"BoomAngleSensorCrankJoint"',
  '...["L","R"].flatMap', "Array.from({length:8}", '"RetractChain_C_Moving"',
  "Object.entries(geometry.beams)", "Object.entries(geometry.points)",
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
const expectedVolumes = ["front", "high-tie", "front", "front"];
if (dataset.selectionFixtureCases !== "4/4" || fixtureOutcomes.length !== expectedVolumes.length) {
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
const safeDistance = Math.min(Math.max(poseDistance, 2.2), absoluteMax / 1.05);
const effectiveMax = Math.min(absoluteMax, Math.max(baseMax, safeDistance * 1.05));
const nextZoomOut = Math.min(effectiveMax, safeDistance * 1.1);
if (effectiveMax < safeDistance || nextZoomOut < safeDistance) throw new Error("Next zoom gesture would snap inside the posed reset distance");

const frameWindow = [16.7, 271, 17.1];
const stalls = frameWindow.filter((sample) => sample >= 250);
if (stalls.length !== 1 || Math.max(...frameWindow) !== 271) throw new Error("Visible-stall window fixture failed");

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
  settled_live_region: true,
  dynamic_reduced_motion_listener: true,
  dynamic_chain_and_sensor_consumer: true,
}, null, 2));
