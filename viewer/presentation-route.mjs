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
  const steerForSide = (side) => Math.max(
    -route.maximumVisualSteerRadians,
    Math.min(
      route.maximumVisualSteerRadians,
      Math.atan((route.wheelbaseM * curvature) / (1 - side * curvature * route.trackM / 2)),
    ),
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
    tangentLength,
    wheelSpeedScales: Object.freeze([
      Math.hypot(1 + curvature * route.trackM / 2, curvature * route.wheelbaseM),
      Math.hypot(1 - curvature * route.trackM / 2, curvature * route.wheelbaseM),
      1 + curvature * route.trackM / 2,
      1 - curvature * route.trackM / 2,
    ]),
  });
}

export function advanceFigureEight(phase, deltaSeconds, route = ES1930M_FIGURE_EIGHT) {
  const sample = sampleFigureEight(phase, route);
  const nextPhase = wrapPhase(sample.phase + route.speedMps * Math.max(0, deltaSeconds) / sample.tangentLength);
  return Object.freeze({ phase: nextPhase, sample: sampleFigureEight(nextPhase, route) });
}
