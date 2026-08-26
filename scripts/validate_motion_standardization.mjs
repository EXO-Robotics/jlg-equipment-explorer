#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  AUTO_OVERRIDE_MS,
  activeAutoOverrides,
  beginAutoOverride,
  clearAutoOverrides,
  createAutoOverrideController,
  dampMotion,
  endAutoOverride,
  holdAutoOverride,
} from "../viewer/auto-override.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const boom = read("viewer.js");
const scissor = read("viewer/runtime.js");
const telehandler = read("viewer/742-runtime.js");
const scissorMachine = read("machines/es1930m/machine.js");

assert.equal(AUTO_OVERRIDE_MS, 6000, "shared override hold must match the 600S golden blueprint");
assert.ok(boom.includes("const AUTONOMY_OVERRIDE_MS = 6000"), "600S golden override duration drifted");
for (const [name, source] of [["ES1930M", scissor], ["742", telehandler]]) {
  assert.ok(source.includes('from "./auto-override.mjs?v=1.0.0"'), `${name} does not use the shared override controller`);
  assert.ok(source.includes('query.get("auto") !== "0"'), `${name} does not default to Auto like 600S`);
  assert.ok(source.includes("holdAutoOverride(controlOverrides, control.id)"), `${name} slider input does not create a timed override`);
  assert.ok(source.includes("dampMotion("), `${name} auto recovery is not frame-rate-independent`);
}
assert.ok(scissorMachine.includes("showcaseDurationMs: 60000"), "ES1930M automatic mechanism cycle is missing");
assert.ok(scissorMachine.includes("published 20-25 s rated band"), "ES1930M lift timing lost its evidence boundary");
assert.ok(!telehandler.includes("lastShowcaseFrameAt"), "742 retained stepped 100 ms camera reframing");
assert.ok(telehandler.includes("showcaseProgress = (showcaseProgress + delta"), "742 mechanism phase is not delta-driven");
assert.ok(telehandler.includes("setProgrammaticViewDistance(dampMotion(orbit.desiredDistance, follow.distance, 2.2, delta))"), "742 follow distance is not continuously damped");

const controller = createAutoOverrideController(["lift", "steer"]);
beginAutoOverride(controller, "lift");
holdAutoOverride(controller, "lift", 1000);
assert.deepEqual(activeAutoOverrides(controller, 6999), ["lift"]);
endAutoOverride(controller, "lift");
assert.deepEqual(activeAutoOverrides(controller, 7001), []);
clearAutoOverrides(controller);
assert.deepEqual(activeAutoOverrides(controller, 1000), []);

const integrate = (fps) => {
  let value = 0;
  for (let frame = 0; frame < fps; frame += 1) value = dampMotion(value, 1, 3.2, 1 / fps);
  return value;
};
const at30 = integrate(30);
const at60 = integrate(60);
assert.ok(Math.abs(at30 - at60) < 1e-12, "motion damping changes with frame rate");
assert.ok(at60 > 0.95 && at60 < 1, "motion damping response is outside the intended smooth range");

console.log(JSON.stringify({
  status: "PASS",
  golden_blueprint: "600S",
  default_auto_routes: ["600S", "742", "ES1930M"],
  override_hold_ms: AUTO_OVERRIDE_MS,
  damping_30hz: at30,
  damping_60hz: at60,
  telehandler_camera: "continuous-damped-follow",
}, null, 2));
