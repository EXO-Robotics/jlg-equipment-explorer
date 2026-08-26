import assert from "node:assert/strict";
import { orbitDragDelta, telehandlerDragDelta } from "../viewer/pointer-gestures.mjs";

const touchRight = telehandlerDragDelta(20, 0, "touch");
const touchDown = telehandlerDragDelta(0, 20, "touch");
const mouseRight = telehandlerDragDelta(20, 0, "mouse");
const mouseDown = telehandlerDragDelta(0, 20, "mouse");
assert.ok(touchRight.azimuth > 0, "742 touch right-swipe mapping must remain unchanged");
assert.ok(touchDown.polar < 0, "742 touch down-swipe mapping must remain unchanged");
assert.ok(mouseRight.azimuth > 0, "742 mouse right-drag must adopt the direct turntable mapping");
assert.ok(mouseDown.polar < 0, "742 mouse down-drag must adopt the direct turntable mapping");

assert.deepEqual(touchRight, orbitDragDelta(20, 0, "touch"), "742 touch mapping must remain the accepted mapping");
assert.deepEqual(mouseRight, touchRight, "742 mouse drag must now match the accepted touch mapping");

console.log(JSON.stringify({ status: "PASS", touch_cases: 2, mouse_cases: 2, accepted_touch_preservation_cases: 1, mouse_alignment_cases: 1 }, null, 2));
