import assert from "node:assert/strict";
import { pointerDistance, scaledPinchDistance } from "../viewer/pointer-gestures.mjs";

const start = pointerDistance({ x: 100, y: 100 }, { x: 200, y: 100 });
const spread = pointerDistance({ x: 75, y: 100 }, { x: 225, y: 100 });
const squeeze = pointerDistance({ x: 125, y: 100 }, { x: 175, y: 100 });
assert.equal(start, 100);
assert.equal(spread, 150);
assert.equal(squeeze, 50);
assert.ok(scaledPinchDistance(6, start, spread) < 6, "finger spread must zoom in");
assert.ok(scaledPinchDistance(6, start, squeeze) > 6, "finger squeeze must zoom out");
assert.equal(scaledPinchDistance(17, start, 10), 18, "zoom-out clamp");
assert.equal(scaledPinchDistance(2, start, 1000), 1.6, "zoom-in clamp");
assert.equal(scaledPinchDistance(6, 0, spread), 6, "invalid baseline must be stable");
console.log(JSON.stringify({ status: "PASS", synthetic_two_pointer_cases: 5 }, null, 2));
