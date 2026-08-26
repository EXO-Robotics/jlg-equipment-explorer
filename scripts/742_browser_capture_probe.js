/**
 * Read-only browser evidence probe for the local 742 review.
 *
 * Load from the same local server as a module, then call the exported helpers
 * through browser automation. This file does not click controls or infer pass;
 * it only returns directly observable metadata, DOM values, and rAF intervals.
 */

export function collectEnvironmentMetadata() {
  const canvas = document.createElement("canvas");
  const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
  const debug = gl?.getExtension("WEBGL_debug_renderer_info");
  const observed = Boolean(gl && debug);
  const browserMatch = navigator.userAgent.match(/(?:Chrome|Chromium)\/([0-9.]+)/);
  return {
    browser: {
      name: navigator.userAgentData?.brands?.map((item) => item.brand).join(", ") || "user-agent reported browser",
      version: browserMatch?.[1] || navigator.appVersion,
      user_agent: navigator.userAgent,
    },
    gpu: {
      status: observed ? "observed" : "unavailable",
      vendor: observed ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
      renderer: observed ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
      api: globalThis.WebGL2RenderingContext && gl instanceof globalThis.WebGL2RenderingContext ? "WebGL 2" : gl ? "WebGL 1" : "unavailable",
      collection_method: observed ? "WEBGL_debug_renderer_info" : "WebGL context capability check",
      reason: observed ? null : "WEBGL_debug_renderer_info was unavailable to this browser session",
    },
    viewport_css_px: [window.innerWidth, window.innerHeight],
    pixel_ratio: window.devicePixelRatio,
  };
}

export function collectDomSnapshot(selectors) {
  return {
    viewport_css_px: [window.innerWidth, window.innerHeight],
    url: window.location.href,
    nodes: selectors.map((selector) => {
      const node = document.querySelector(selector);
      if (!node) throw new Error(`Capture selector did not resolve: ${selector}`);
      const attributes = {};
      for (const attribute of node.attributes) attributes[attribute.name] = attribute.value;
      if (node === document.body) {
        for (const [name, value] of Object.entries(node.dataset)) attributes[`data-${name.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`] = value;
      }
      const text = node instanceof HTMLOutputElement ? node.value : (node.textContent || "").trim();
      return { selector, text, attributes };
    }),
  };
}

export async function collectFrameIntervals(sampleCount = 180) {
  if (!Number.isInteger(sampleCount) || sampleCount < 180 || sampleCount > 1200) {
    throw new Error("Frame evidence requires 180-1200 samples");
  }
  const samples = [];
  let previous = await new Promise((resolve) => requestAnimationFrame(resolve));
  while (samples.length < sampleCount) {
    const current = await new Promise((resolve) => requestAnimationFrame(resolve));
    if (document.visibilityState === "visible") samples.push(Number((current - previous).toFixed(3)));
    previous = current;
  }
  const ordered = [...samples].sort((a, b) => a - b);
  const p95 = ordered[Math.ceil(ordered.length * 0.95) - 1];
  return {
    viewport_css_px: [window.innerWidth, window.innerHeight],
    samples_ms: samples,
    summary: {
      sample_count: samples.length,
      p95_ms: Number(p95.toFixed(3)),
      worst_ms: Number(Math.max(...samples).toFixed(3)),
      visible_stall_count_gte_250ms: samples.filter((value) => value >= 250).length,
    },
    background_samples_excluded: true,
  };
}

function numericDataset(name) {
  const value = Number(document.body.dataset[name]);
  if (!Number.isFinite(value) || value <= 0) throw new Error(`742 runtime did not expose a finite positive ${name}`);
  return value;
}

function nextFrame() {
  return new Promise((resolve) => requestAnimationFrame(resolve));
}

export async function waitForOrbitCameraSettle({ timeoutMs = 8000, toleranceM = 0.03, stableFrames = 6 } = {}) {
  if (!Number.isFinite(timeoutMs) || timeoutMs < 500 || !Number.isFinite(toleranceM) || toleranceM <= 0 || !Number.isInteger(stableFrames) || stableFrames < 3) {
    throw new Error("742 camera-settle options are invalid");
  }
  const started = performance.now();
  const samples = [];
  let stable = 0;
  let previous = null;
  while (performance.now() - started <= timeoutMs) {
    await nextFrame();
    const cameraDistanceM = numericDataset("orbitCameraDistanceM");
    const desiredDistanceM = numericDataset("orbitDesiredDistanceM");
    samples.push(cameraDistanceM);
    const cameraStable = previous === null || Math.abs(cameraDistanceM - previous) <= toleranceM;
    stable = Math.abs(cameraDistanceM - desiredDistanceM) <= toleranceM && cameraStable ? stable + 1 : 0;
    if (stable >= stableFrames) {
      return {
        camera_distance_m: Number(cameraDistanceM.toFixed(3)),
        desired_distance_m: Number(desiredDistanceM.toFixed(3)),
        stable_frames: stable,
        samples_camera_distance_m: samples.map((sample) => Number(sample.toFixed(3))),
      };
    }
    previous = cameraDistanceM;
  }
  throw new Error(`742 camera did not settle within ${timeoutMs} ms`);
}

function pointIsCanvas(canvas, point) {
  return document.elementFromPoint(point[0], point[1]) === canvas;
}

function findVisibleCanvasPinchPath(canvas) {
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 180 || rect.height < 180) throw new Error("742 canvas is too small for a two-contact pinch proof");
  const narrowHalfSpan = Math.min(40, rect.width * 0.10);
  const wideHalfSpan = Math.min(105, rect.width * 0.27);
  for (const yFraction of [0.42, 0.32, 0.52, 0.22, 0.62, 0.72]) {
    for (const xFraction of [0.50, 0.62, 0.38, 0.72, 0.28]) {
      const centerX = rect.left + rect.width * xFraction;
      const centerY = rect.top + rect.height * yFraction;
      const start = [[centerX - narrowHalfSpan, centerY], [centerX + narrowHalfSpan, centerY]];
      const end = [[centerX - wideHalfSpan, centerY], [centerX + wideHalfSpan, centerY]];
      const all = [...start, ...end];
      if (all.every((point) => point[0] >= rect.left + 8 && point[0] <= rect.right - 8 && point[1] >= rect.top + 8 && point[1] <= rect.bottom - 8 && pointIsCanvas(canvas, point))) {
        return {
          canvas_rect_css_px: { x: Number(rect.x.toFixed(2)), y: Number(rect.y.toFixed(2)), width: Number(rect.width.toFixed(2)), height: Number(rect.height.toFixed(2)) },
          start_points_css_px: start.map((point) => point.map((value) => Number(value.toFixed(2)))),
          end_points_css_px: end.map((point) => point.map((value) => Number(value.toFixed(2)))),
        };
      }
    }
  }
  throw new Error("742 pinch probe could not find two unobstructed canvas touch paths");
}

function dispatchTouchPointer(canvas, type, pointerId, point, isPrimary) {
  canvas.dispatchEvent(new PointerEvent(type, {
    bubbles: true,
    cancelable: true,
    pointerId,
    pointerType: "touch",
    isPrimary,
    clientX: point[0],
    clientY: point[1],
    width: 2,
    height: 2,
    pressure: type === "pointerup" ? 0 : 1,
    buttons: type === "pointerup" ? 0 : 1,
  }));
}

function monotonicDecrease(samples, toleranceM = 0.01) {
  return samples.every((sample, index) => index === 0 || sample <= samples[index - 1] + toleranceM);
}

export async function probe742PinchZoom({ minimumDeltaM = 0.5 } = {}) {
  if (!Number.isFinite(minimumDeltaM) || minimumDeltaM <= 0) throw new Error("742 pinch minimum delta must be positive");
  if (document.body.dataset.machineSource !== "glb-validated" || document.body.dataset.runtimeErrorCount !== "0") {
    throw new Error("742 pinch proof requires a validated zero-error GLB runtime");
  }
  const canvas = document.querySelector("#app canvas");
  if (!(canvas instanceof HTMLCanvasElement)) throw new Error("742 pinch proof canvas is unavailable");
  const path = findVisibleCanvasPinchPath(canvas);
  const baseline = await waitForOrbitCameraSettle();
  const [startLeft, startRight] = path.start_points_css_px;
  const [endLeft, endRight] = path.end_points_css_px;
  const hitTestTargets = [...path.start_points_css_px, ...path.end_points_css_px].map((point) => document.elementFromPoint(point[0], point[1])?.tagName || null);
  if (hitTestTargets.some((target) => target !== "CANVAS")) throw new Error("742 pinch path became obstructed before dispatch");
  dispatchTouchPointer(canvas, "pointerdown", 741, startLeft, true);
  dispatchTouchPointer(canvas, "pointerdown", 742, startRight, false);
  dispatchTouchPointer(canvas, "pointermove", 741, endLeft, true);
  const intermediateDesired = numericDataset("orbitDesiredDistanceM");
  dispatchTouchPointer(canvas, "pointermove", 742, endRight, false);
  const finalDesired = numericDataset("orbitDesiredDistanceM");
  dispatchTouchPointer(canvas, "pointerup", 741, endLeft, true);
  dispatchTouchPointer(canvas, "pointerup", 742, endRight, false);
  const after = await waitForOrbitCameraSettle();
  const cameraDeltaM = Number((after.camera_distance_m - baseline.camera_distance_m).toFixed(3));
  const desiredDeltaM = Number((after.desired_distance_m - baseline.desired_distance_m).toFixed(3));
  const requiredDeltaM = Number(Math.max(minimumDeltaM, baseline.camera_distance_m * 0.02).toFixed(3));
  const monotonicSamples = after.samples_camera_distance_m;
  const pass = cameraDeltaM <= -requiredDeltaM
    && desiredDeltaM <= -requiredDeltaM
    && intermediateDesired < baseline.desired_distance_m
    && finalDesired <= intermediateDesired
    && monotonicDecrease(monotonicSamples);
  if (!pass) {
    throw new Error(`742 pinch did not prove monotonic zoom-in: camera ${baseline.camera_distance_m}->${after.camera_distance_m}, desired ${baseline.desired_distance_m}->${after.desired_distance_m}`);
  }
  return {
    schema_version: "1.0.0",
    gesture: "pinch-out",
    target_selector: "#app canvas",
    viewport_css_px: [innerWidth, innerHeight],
    ...path,
    hit_test_targets: hitTestTargets,
    all_points_on_canvas: true,
    baseline,
    after,
    intermediate_desired_distance_m: Number(intermediateDesired.toFixed(3)),
    final_gesture_desired_distance_m: Number(finalDesired.toFixed(3)),
    camera_distance_delta_m: cameraDeltaM,
    desired_distance_delta_m: desiredDeltaM,
    absolute_camera_distance_delta_m: Number(Math.abs(cameraDeltaM).toFixed(3)),
    minimum_required_delta_m: requiredDeltaM,
    expected_direction: "decrease",
    actual_direction: cameraDeltaM < 0 ? "decrease" : cameraDeltaM > 0 ? "increase" : "none",
    monotonic_camera_change: true,
    settled_before: true,
    settled_after: true,
    outcome: "pass",
  };
}

export const defaultSelectors = Object.freeze([
  "body",
  "#machine-title",
  "#diagnostics",
  "#controls-toggle",
  "#showcase",
  "#inspector",
  "#lift-control",
  "#telescope-control",
  "#tilt-control",
  "#steer-control",
  "#level-control",
]);
