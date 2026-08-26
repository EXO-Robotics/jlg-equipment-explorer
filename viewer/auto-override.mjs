export const AUTO_OVERRIDE_MS = 6000;

export function createAutoOverrideController(controlIds, holdMs = AUTO_OVERRIDE_MS) {
  const ids = Object.freeze([...controlIds]);
  return {
    ids,
    holdMs,
    activeControl: null,
    overrideUntil: Object.fromEntries(ids.map((id) => [id, 0])),
  };
}

export function beginAutoOverride(controller, controlId) {
  if (controller.ids.includes(controlId)) controller.activeControl = controlId;
}

export function endAutoOverride(controller, controlId) {
  if (controller.activeControl === controlId) controller.activeControl = null;
}

export function holdAutoOverride(controller, controlId, now = performance.now()) {
  if (!controller.ids.includes(controlId)) return;
  controller.overrideUntil[controlId] = now + controller.holdMs;
}

export function clearAutoOverrides(controller) {
  controller.activeControl = null;
  for (const id of controller.ids) controller.overrideUntil[id] = 0;
}

export function activeAutoOverrides(controller, now = performance.now()) {
  return controller.ids.filter((id) => controller.activeControl === id || now < controller.overrideUntil[id]);
}

export function dampMotion(current, target, response, deltaSeconds) {
  const blend = 1 - Math.exp(-Math.max(0, response) * Math.max(0, deltaSeconds));
  return current + (target - current) * blend;
}
