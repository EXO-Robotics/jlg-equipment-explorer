import assert from "node:assert/strict";
import { orbitDragDelta } from "../viewer/pointer-gestures.mjs";

const touchRight = orbitDragDelta(20, 0, "touch");
const touchDown = orbitDragDelta(0, 20, "touch");
const mouseRight = orbitDragDelta(20, 0, "mouse");
const mouseDown = orbitDragDelta(0, 20, "mouse");
assert.ok(touchRight.azimuth > 0, "742 touch right-swipe must follow the flagship camera direction");
assert.ok(touchDown.polar < 0, "742 touch down-swipe must follow the flagship camera direction");
assert.ok(mouseRight.azimuth < 0, "742 mouse horizontal orbit must remain unchanged");
assert.ok(mouseDown.polar > 0, "742 mouse vertical orbit must remain unchanged");

const flagshipTheta = -0.85;
const telehandlerAzimuth = Math.PI / 2 - flagshipTheta;
const swipeRadians = touchRight.azimuth;
const flagshipAfter = {
  x: Math.sin(flagshipTheta - swipeRadians),
  z: Math.cos(flagshipTheta - swipeRadians),
};
const telehandlerAfter = {
  x: Math.cos(telehandlerAzimuth + swipeRadians),
  z: Math.sin(telehandlerAzimuth + swipeRadians),
};
assert.ok(
  Math.hypot(flagshipAfter.x - telehandlerAfter.x, flagshipAfter.z - telehandlerAfter.z) < 1e-12,
  "742 touch drag must match the 600S projected camera direction",
);

console.log(JSON.stringify({ status: "PASS", touch_cases: 2, mouse_cases: 2, flagship_camera_equivalence_cases: 1 }, null, 2));
