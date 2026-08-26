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
