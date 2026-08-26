import assert from "node:assert/strict";
import { advanceFigureEight, ES1930M_FIGURE_EIGHT, sampleFigureEight } from "../viewer/presentation-route.mjs";

const start = sampleFigureEight(0);
const end = sampleFigureEight(Math.PI * 2);
assert.ok(Math.hypot(start.x - end.x, start.z - end.z) < 1e-9, "route must close exactly");
assert.ok(start.tangentLength > 0.1, "center crossing tangent must not collapse");
assert.ok(sampleFigureEight(Math.PI / 4).curvature * sampleFigureEight(Math.PI * 5 / 4).curvature < 0, "the two lobes must steer in opposite directions");

for (const phaseSample of [0.3, 1.1, 2.4, 3.6, 4.9, 5.7]) {
  const current = sampleFigureEight(phaseSample);
  const later = sampleFigureEight(phaseSample + 1e-5);
  const headingDelta = Math.atan2(Math.sin(later.heading - current.heading), Math.cos(later.heading - current.heading));
  assert.equal(Math.sign(current.curvature), Math.sign(headingDelta), "steering curvature must follow machine yaw instead of the mirrored X/Z determinant");
  assert.equal(Math.sign(current.steerLeft), Math.sign(headingDelta), "left wheel must steer into the route turn");
  assert.equal(Math.sign(current.steerRight), Math.sign(headingDelta), "right wheel must steer into the route turn");
}

let phase = 0;
let previous = sampleFigureEight(phase);
let maximumStep = 0;
let minimumStep = Infinity;
let maximumHeadingStep = 0;
let maximumVisualSteer = 0;
for (let index = 0; index < 2400; index += 1) {
  const next = advanceFigureEight(phase, 1 / 60);
  phase = next.phase;
  const step = Math.hypot(next.sample.x - previous.x, next.sample.z - previous.z);
  const headingStep = Math.abs(Math.atan2(Math.sin(next.sample.heading - previous.heading), Math.cos(next.sample.heading - previous.heading)));
  maximumStep = Math.max(maximumStep, step);
  minimumStep = Math.min(minimumStep, step);
  maximumHeadingStep = Math.max(maximumHeadingStep, headingStep);
  maximumVisualSteer = Math.max(maximumVisualSteer, Math.abs(next.sample.steerLeft), Math.abs(next.sample.steerRight));
  assert.ok(Number.isFinite(next.sample.x + next.sample.z + next.sample.heading + next.sample.steer), "route state must remain finite");
  assert.ok(Math.abs(next.sample.steer) <= 1, "steering actuator command must stay normalized");
  assert.ok(Math.abs(next.sample.steerLeft) <= ES1930M_FIGURE_EIGHT.maximumVisualSteerRadians, "left visual steering must remain bounded");
  assert.ok(Math.abs(next.sample.steerRight) <= ES1930M_FIGURE_EIGHT.maximumVisualSteerRadians, "right visual steering must remain bounded");
  assert.equal(next.sample.wheelSpeedScales.length, 4, "route must solve four wheel speeds");
  assert.ok(next.sample.wheelSpeedScales.every((scale) => scale > 0.7 && scale < 1.3), "wheel speed scales must remain physically plausible");
  if (Math.abs(next.sample.curvature) > 1e-5) {
    assert.notEqual(next.sample.wheelSpeedScales[0], next.sample.wheelSpeedScales[1], "front wheels must follow different path radii in a turn");
    assert.notEqual(next.sample.wheelSpeedScales[2], next.sample.wheelSpeedScales[3], "rear wheels must follow different path radii in a turn");
  }
  if (Math.abs(next.sample.curvature) > 1e-5) {
    assert.equal(Math.sign(next.sample.steerLeft), Math.sign(next.sample.curvature), "left visual steering must follow curvature");
    assert.equal(Math.sign(next.sample.steerRight), Math.sign(next.sample.curvature), "right visual steering must follow curvature");
  }
  previous = next.sample;
}
const nominalStep = ES1930M_FIGURE_EIGHT.speedMps / 60;
assert.ok(maximumStep < nominalStep * 1.03, "translation must remain continuous");
assert.ok(minimumStep > nominalStep * 0.96, "ground speed must remain approximately constant");
assert.ok(maximumHeadingStep < 0.02, "heading must not snap between samples");
const wheelRadiansPerSecond = ES1930M_FIGURE_EIGHT.speedMps / ES1930M_FIGURE_EIGHT.wheelRadiusM;
assert.ok(maximumVisualSteer < ES1930M_FIGURE_EIGHT.maximumVisualSteerRadians - 0.005, "route curvature must remain inside the reconstructed steering envelope without clamp scrub");
assert.ok(wheelRadiansPerSecond > 5 && wheelRadiansPerSecond < 6, "wheel roll rate must match route speed and authored radius");
console.log(JSON.stringify({ status: "PASS", samples: 2400, maximum_step_m: maximumStep, minimum_step_m: minimumStep, maximum_heading_step_rad: maximumHeadingStep, maximum_visual_steer_rad: maximumVisualSteer, wheel_radians_per_second: wheelRadiansPerSecond }, null, 2));
