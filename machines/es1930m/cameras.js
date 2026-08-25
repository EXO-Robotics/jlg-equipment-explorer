export const ES1930M_CAMERAS = Object.freeze({
  default: Object.freeze({ position: [3.4, 2.45, 4.0], target: [0, 1.05, 0] }),
  stowedSide: Object.freeze({ position: [0.15, 1.35, 4.4], target: [0, 0.85, 0] }),
  raisedMechanism: Object.freeze({ position: [3.8, 3.0, 6.7], target: [0, 2.8, 0] }),
  platform: Object.freeze({ position: [2.0, 2.25, 2.7], target: [0.05, 1.45, 0] }),
  chassis: Object.freeze({ position: [2.4, 1.15, 1.35], target: [0, 0.35, 0] }),
});

export function es1930mFollowView(state, compact) {
  return Object.freeze({
    target: [0, 1.05 + ((compact ? 3.95 : 3.85) - 1.05) * state.lift, 0],
    distance: (compact ? 5.3 : 4.5) + ((compact ? 15.5 : 13.0) - (compact ? 5.3 : 4.5)) * state.lift,
  });
}

export function es1930mComponentView(component, state, compact) {
  const views = {
    chassis: { target: [0, 0.36, 0], distance: 2.55, azimuth: -0.72, polar: 1.22 },
    scissor: { target: [0, 0.72 + ((compact ? 3.95 : 3.85) - 0.72) * state.lift, 0], distance: 3.4 + ((compact ? 15.5 : 13.0) - 3.4) * state.lift, azimuth: -0.75, polar: 1.16 },
    platform: { target: [0.05, Math.max(1.45, 0.90 + (5.64 - 0.90) * state.lift + 0.45), 0], distance: 3.2, azimuth: -0.72, polar: 1.15 },
    steering: { target: [0.52, 0.28, 0], distance: 2.15, azimuth: 0, polar: 1.28 },
    default: { target: [0, 1.05, 0], distance: compact ? 5.3 : 4.5, azimuth: -0.72, polar: 1.18 },
  };
  return Object.freeze(views[component] || views.default);
}
