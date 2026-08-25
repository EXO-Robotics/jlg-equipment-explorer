export function pointerDistance(first, second) {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

export function scaledPinchDistance(cameraDistance, previousPointerDistance, nextPointerDistance, minimum = 1.6, maximum = 18) {
  if (!(previousPointerDistance > 0) || !(nextPointerDistance > 0)) return cameraDistance;
  return Math.max(minimum, Math.min(maximum, cameraDistance * previousPointerDistance / nextPointerDistance));
}
