export function pointerDistance(first, second) {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

export function scaledPinchDistance(cameraDistance, previousPointerDistance, nextPointerDistance, minimum = 1.6, maximum = 18) {
  if (!(previousPointerDistance > 0) || !(nextPointerDistance > 0)) return cameraDistance;
  return Math.max(minimum, Math.min(maximum, cameraDistance * previousPointerDistance / nextPointerDistance));
}

export function orbitDragDelta(dx, dy, pointerType = "mouse", sensitivity = 0.006) {
  const directTouch = pointerType === "touch";
  return Object.freeze({
    azimuth: dx * sensitivity * (directTouch ? 1 : -1),
    polar: dy * sensitivity * (directTouch ? -1 : 1),
  });
}

// The 742 is presented as a direct-manipulation turntable on both inputs.
// Touch already has the desired mapping; desktop mouse drag adopts it too.
export function telehandlerDragDelta(dx, dy, pointerType = "mouse", sensitivity = 0.006) {
  return orbitDragDelta(dx, dy, pointerType === "mouse" ? "touch" : pointerType, sensitivity);
}
