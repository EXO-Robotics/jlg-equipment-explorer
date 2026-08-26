export const ES1930M_FIGURE_EIGHT = Object.freeze({
  radiusX: 8.2,
  radiusZ: 6.0,
  speedMps: 0.72,
  steeringResponse: 0.78,
  wheelbaseM: 1.07,
  trackM: 0.67,
  wheelRadiusM: 0.13,
  maximumVisualSteerRadians: 0.58,
});

export const JLG742_FIGURE_EIGHT = Object.freeze({
  radiusX: 12.5,
  radiusZ: 8.0,
  speedMps: 0.72,
  steeringResponse: 2.65,
  wheelbaseM: 3.42,
  trackM: 2.1005,
  wheelRadiusM: 0.643,
  maximumVisualSteerRadians: 55 * Math.PI / 180,
  fourWheelSteer: true,
});

export function wrapPhase(phase) {
  const turn = Math.PI * 2;
  return ((phase % turn) + turn) % turn;
}

export function sampleFigureEight(phase, route = ES1930M_FIGURE_EIGHT) {
  const t = wrapPhase(phase);
  const sin = Math.sin(t);
  const cos = Math.cos(t);
  const dx = route.radiusX * cos;
  const dz = route.radiusZ * Math.cos(2 * t);
  const ddx = -route.radiusX * sin;
  const ddz = -2 * route.radiusZ * Math.sin(2 * t);
  const tangentLength = Math.max(Math.hypot(dx, dz), 1e-6);
  const planarCurvature = (dx * ddz - dz * ddx) / (tangentLength ** 3);
  // Three.js heading maps local machine-forward +X through world -Z for
  // positive yaw. Negate the X/Z planar determinant so positive steering
  // follows positive machine yaw, matching the 600S route convention.
  const curvature = -planarCurvature;
  const axleOffsetM = route.fourWheelSteer ? route.wheelbaseM / 2 : route.wheelbaseM;
  const steerForSide = (side, axleDirection = 1) => Math.max(
    -route.maximumVisualSteerRadians,
    Math.min(
      route.maximumVisualSteerRadians,
      Math.atan((axleDirection * axleOffsetM * curvature) / (1 - side * curvature * route.trackM / 2)),
    ),
  );
  const wheelSpeedScale = (side, axleDirection = 1) => Math.hypot(
    1 + side * curvature * route.trackM / 2,
    curvature * axleOffsetM * axleDirection,
  );
  return Object.freeze({
    phase: t,
    x: route.radiusX * sin,
    z: route.radiusZ * sin * cos,
    heading: Math.atan2(-dz, dx),
    curvature,
    planarCurvature,
    steer: Math.tanh(curvature * route.steeringResponse),
    steerLeft: steerForSide(1),
    steerRight: steerForSide(-1),
    steerRearLeft: route.fourWheelSteer ? steerForSide(1, -1) : 0,
    steerRearRight: route.fourWheelSteer ? steerForSide(-1, -1) : 0,
    tangentLength,
    wheelSpeedScales: Object.freeze([
      wheelSpeedScale(1),
      wheelSpeedScale(-1),
      wheelSpeedScale(1, route.fourWheelSteer ? -1 : 0),
      wheelSpeedScale(-1, route.fourWheelSteer ? -1 : 0),
    ]),
  });
}

export function advanceFigureEight(phase, deltaSeconds, route = ES1930M_FIGURE_EIGHT) {
  const sample = sampleFigureEight(phase, route);
  const nextPhase = wrapPhase(sample.phase + route.speedMps * Math.max(0, deltaSeconds) / sample.tangentLength);
  return Object.freeze({ phase: nextPhase, sample: sampleFigureEight(nextPhase, route) });
}
