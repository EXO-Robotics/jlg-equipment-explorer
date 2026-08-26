export const JLG742_CAMERAS = Object.freeze({
  default: Object.freeze({ target: [1.60, 1.22, 0], distance: 11.2, azimuth: -1.10, polar: 1.18 }),
  chassis: Object.freeze({ target: [0, 0.92, 0], distance: 6.8, azimuth: -0.66, polar: 1.20 }),
  cab: Object.freeze({ target: [0.80, 1.70, -0.62], distance: 3.9, azimuth: -0.55, polar: 1.12 }),
  boom: Object.freeze({ target: [0.40, 1.65, 0], distance: 6.7, azimuth: -0.78, polar: 1.15 }),
  carriage: Object.freeze({ target: [2.55, 0.75, 0], distance: 4.2, azimuth: -0.56, polar: 1.18 }),
  steering: Object.freeze({ target: [1.70, 0.62, 0], distance: 4.0, azimuth: 0.02, polar: 1.28 }),
  hydraulics: Object.freeze({ target: [-0.55, 1.50, 0.58], distance: 4.3, azimuth: 0.66, polar: 1.12 }),
  frame: Object.freeze({ target: [-0.40, 0.78, 0], distance: 5.4, azimuth: -0.90, polar: 1.28 }),
});

export function jlg742FollowView(state, compact) {
  const reach = state.telescope * 8.86;
  return Object.freeze({
    target: [0.2 + reach * 0.40, 1.60 + state.lift * 5.4 + state.telescope * 1.8, 0],
    distance: (compact ? 13.0 : 12.0) + reach + state.lift * 5.0,
  });
}

export function jlg742ComponentView(component, state, compact) {
  if (component === "boom" && (state.lift > 0.1 || state.telescope > 0.1)) {
    return Object.freeze({ ...jlg742FollowView(state, compact), azimuth: -0.72, polar: 1.12 });
  }
  return Object.freeze(JLG742_CAMERAS[component] || JLG742_CAMERAS.default);
}
