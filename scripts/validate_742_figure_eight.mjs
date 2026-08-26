import assert from "node:assert/strict";
import { solve742State } from "../machines/742/solver.js";
import { advanceFigureEight, JLG742_FIGURE_EIGHT, sampleFigureEight } from "../viewer/presentation-route.mjs";

const start = sampleFigureEight(0, JLG742_FIGURE_EIGHT);
const end = sampleFigureEight(Math.PI * 2, JLG742_FIGURE_EIGHT);
assert.ok(Math.hypot(start.x - end.x, start.z - end.z) < 1e-9, "742 route must close exactly");
assert.ok(sampleFigureEight(Math.PI / 4, JLG742_FIGURE_EIGHT).curvature * sampleFigureEight(Math.PI * 5 / 4, JLG742_FIGURE_EIGHT).curvature < 0, "742 route lobes must steer in opposite directions");
const rightTurn = sampleFigureEight(Math.PI / 4, JLG742_FIGURE_EIGHT);
assert.equal(Math.sign(rightTurn.wheelSpeedScales[0] - rightTurn.wheelSpeedScales[1]), Math.sign(rightTurn.curvature), "right/left front wheel speeds must reflect the turn direction");
assert.equal(Math.sign(rightTurn.wheelSpeedScales[2] - rightTurn.wheelSpeedScales[3]), Math.sign(rightTurn.curvature), "right/left rear wheel speeds must reflect the turn direction");

let phase = 0;
let previous = start;
let maximumStep = 0;
let minimumStep = Infinity;
let maximumHeadingStep = 0;
let maximumWheelAngle = 0;
let maximumTargetWheelAngle = 0;
let maximumSteeringFitError = 0;
let maximumRadius = 0;
let completedLoops = 0;
let samples = 0;
for (let index = 0; index < 20000 && completedLoops < 2; index += 1) {
  const next = advanceFigureEight(phase, 1 / 60, JLG742_FIGURE_EIGHT);
  if (next.phase < phase) completedLoops += 1;
  phase = next.phase;
  const step = Math.hypot(next.sample.x - previous.x, next.sample.z - previous.z);
  const headingStep = Math.abs(Math.atan2(Math.sin(next.sample.heading - previous.heading), Math.cos(next.sample.heading - previous.heading)));
  const solved = solve742State({ lift: 0, telescope: 0, tilt: 0, steer: next.sample.steer, level: 0, steerMode: "circle" });
  maximumStep = Math.max(maximumStep, step);
  minimumStep = Math.min(minimumStep, step);
  maximumHeadingStep = Math.max(maximumHeadingStep, headingStep);
  maximumWheelAngle = Math.max(maximumWheelAngle, ...Object.values(solved.wheelAngles).map(Math.abs));
  const targetWheelAngle = Math.max(Math.abs(next.sample.steerLeft), Math.abs(next.sample.steerRight));
  const solvedWheelAngle = Math.max(...Object.values(solved.wheelAngles).map(Math.abs));
  maximumTargetWheelAngle = Math.max(maximumTargetWheelAngle, targetWheelAngle);
  maximumSteeringFitError = Math.max(maximumSteeringFitError, Math.abs(solvedWheelAngle - targetWheelAngle));
  maximumRadius = Math.max(maximumRadius, Math.hypot(next.sample.x, next.sample.z));
  samples += 1;
  assert.ok(Number.isFinite(next.sample.x + next.sample.z + next.sample.heading + next.sample.steer), "742 route state must remain finite");
  assert.ok(Math.abs(next.sample.steer) <= 1, "742 steering command must remain normalized");
  assert.equal(next.sample.wheelSpeedScales.length, 4, "742 route must solve four wheel speeds");
  assert.ok(next.sample.wheelSpeedScales.every((scale) => scale > 0.65 && scale < 1.5), "742 wheel speeds must remain plausible");
  assert.equal(Math.sign(next.sample.steerRearLeft), -Math.sign(next.sample.steerLeft), "742 rear circle steer must oppose front steer");
  assert.equal(Math.sign(next.sample.steerRearRight), -Math.sign(next.sample.steerRight), "742 rear circle steer must oppose front steer");
  previous = next.sample;
}

const nominalStep = JLG742_FIGURE_EIGHT.speedMps / 60;
assert.equal(completedLoops, 2, "validation must traverse two complete figure-eight loops");
assert.ok(maximumStep < nominalStep * 1.03 && minimumStep > nominalStep * 0.96, "742 ground speed must remain continuous and approximately constant");
assert.ok(maximumHeadingStep < 0.02, "742 heading must not snap");
assert.ok(maximumWheelAngle < JLG742_FIGURE_EIGHT.maximumVisualSteerRadians, "742 solver steering must stay inside the published service limit");
assert.ok(maximumTargetWheelAngle < JLG742_FIGURE_EIGHT.maximumVisualSteerRadians, "742 route demand must stay inside the published service limit");
assert.ok(maximumSteeringFitError < 3 * Math.PI / 180, "742 reconstructed linkage must closely follow the route steering demand");
assert.ok(maximumRadius + 3.6 < 18, "742 figure-eight swept centerline must remain on the presentation floor with body margin");

console.log(JSON.stringify({
  status: "PASS",
  samples,
  completed_loops: completedLoops,
  final_phase_rad: phase,
  maximum_step_m: maximumStep,
  minimum_step_m: minimumStep,
  maximum_heading_step_rad: maximumHeadingStep,
  maximum_wheel_angle_deg: maximumWheelAngle * 180 / Math.PI,
  maximum_target_wheel_angle_deg: maximumTargetWheelAngle * 180 / Math.PI,
  maximum_steering_fit_error_deg: maximumSteeringFitError * 180 / Math.PI,
  maximum_center_radius_m: maximumRadius,
}, null, 2));
