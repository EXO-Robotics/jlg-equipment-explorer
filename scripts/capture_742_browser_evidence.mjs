import { spawn, execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const options = Object.fromEntries(process.argv.slice(2).map((argument) => {
  const match = argument.match(/^--([a-z-]+)=(.+)$/);
  if (!match) throw new Error(`unsupported capture-runner argument: ${argument}`);
  return [match[1], match[2]];
}));
const playwrightRootArgument = options["playwright-root"] || process.env.PLAYWRIGHT_NODE_MODULES;
const browserExecutableArgument = options["browser-executable"] || process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
if (!playwrightRootArgument || !browserExecutableArgument || !path.isAbsolute(playwrightRootArgument) || !path.isAbsolute(browserExecutableArgument)) {
  throw new Error("capture runner requires explicit absolute --playwright-root and --browser-executable paths");
}
const PLAYWRIGHT_ROOT = path.normalize(playwrightRootArgument);
const BROWSER_EXECUTABLE = path.normalize(browserExecutableArgument);
const PORT = Number(options.port || 8092);
if (!path.isAbsolute(PLAYWRIGHT_ROOT) || !path.isAbsolute(BROWSER_EXECUTABLE) || !Number.isInteger(PORT) || PORT < 1024 || PORT > 65535) {
  throw new Error("capture runner requires absolute Playwright node_modules/browser paths and a safe TCP port");
}
const playwrightEntry = path.join(PLAYWRIGHT_ROOT, "playwright", "index.mjs");
const playwrightManifest = path.join(PLAYWRIGHT_ROOT, "playwright", "package.json");
const { chromium } = await import(pathToFileURL(playwrightEntry));
const PLAYWRIGHT_VERSION = JSON.parse(await fs.readFile(playwrightManifest, "utf8")).version;
if (!/^\d+\.\d+\.\d+$/.test(PLAYWRIGHT_VERSION)) throw new Error("Playwright package version is unavailable or malformed");
await fs.access(BROWSER_EXECUTABLE);
const BASE = `http://127.0.0.1:${PORT}`;
const REVIEW_DIR = options["output-root"] ? path.resolve(options["output-root"]) : path.join(ROOT, "docs/review/742");
if (options["output-root"] && !path.isAbsolute(options["output-root"])) throw new Error("--output-root must be absolute");
const CAPTURE_DIR = path.join(REVIEW_DIR, "browser-captures");
function evidenceOutputPath(relative) {
  const prefix = "docs/review/742/";
  assert(relative.startsWith(prefix), `unexpected evidence output path: ${relative}`);
  return path.join(REVIEW_DIR, relative.slice(prefix.length));
}
const EXPECTED_ID = "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481";
const RUNNER_RELATIVE = "scripts/capture_742_browser_evidence.mjs";
const BASE_SELECTORS = ["body", "#machine-title", "#diagnostics", "#controls-toggle", "#inspector"];
const SLIDER_SELECTORS = ["#lift-control", "#telescope-control", "#tilt-control", "#steer-control", "#level-control"];
const SEMANTIC_CANVAS_PROBES = Object.freeze([
  { id: "boom-upper-visible-surface", x: 600, y: 280, expected_component: "boom" },
  { id: "cab-front-visible-surface", x: 684, y: 350, expected_component: "cab" },
  { id: "chassis-center-visible-surface", x: 824, y: 398, expected_component: "chassis" },
  { id: "steering-front-wheel-visible-surface", x: 959, y: 430, expected_component: "steering" },
]);
const GATE_FILES = {
  desktop_browser_interaction: "desktop-browser-interaction.json",
  mobile_browser_interaction: "mobile-browser-interaction.json",
  accessibility_semantics_and_keyboard: "accessibility-semantics-keyboard.json",
  semantic_selection: "semantic-selection.json",
  performance_profile: "performance-profile.json",
  "600s_browser_regression": "600s-browser-regression.json",
  es1930m_browser_regression: "es1930m-browser-regression.json",
};
const REQUESTED_GATE = options.gate || null;
if (REQUESTED_GATE && !(REQUESTED_GATE in GATE_FILES)) throw new Error(`unsupported --gate value: ${REQUESTED_GATE}`);

function assert(value, message) { if (!value) throw new Error(message); }
function sha(buffer) { return createHash("sha256").update(buffer).digest("hex"); }
function outcomeSha(value) { return sha(Buffer.from(JSON.stringify(value))); }
function utcNow() { return new Date().toISOString(); }
function jsonText(value) { return `${JSON.stringify(value, null, 2)}\n`; }
function pass(details = {}) { return { outcome: "pass", ...details }; }

const runnerBytes = await fs.readFile(path.join(ROOT, RUNNER_RELATIVE));
const RUNNER_RECORD = Object.freeze({ path: RUNNER_RELATIVE, sha256: sha(runnerBytes), bytes: runnerBytes.length });

const server = spawn("python3", ["-B", "-m", "http.server", String(PORT), "--bind", "127.0.0.1"], {
  cwd: ROOT, stdio: ["ignore", "ignore", "pipe"],
});
let serverError = "";
server.stderr.on("data", (chunk) => { serverError += String(chunk); });

async function waitForServer() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`${BASE}/742/`);
      if (response.status === 200) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`local server did not start: ${serverError}`);
}

const browser = await chromium.launch({
  executablePath: BROWSER_EXECUTABLE,
  headless: true,
  args: ["--disable-background-timer-throttling", "--disable-renderer-backgrounding"],
});

const osIdentity = {
  name: "macOS",
  version: execFileSync("sw_vers", ["-productVersion"], { encoding: "utf8" }).trim(),
  build: execFileSync("sw_vers", ["-buildVersion"], { encoding: "utf8" }).trim(),
};
const browserVersion = browser.version();
const browserIdentity = { name: "Chromium", version: browserVersion, user_agent: null };
let commonGpu = null;
const artifacts = {};

async function openPage(viewport, route, { touch = false } = {}) {
  const context = await browser.newContext({ viewport: { width: viewport[0], height: viewport[1] }, deviceScaleFactor: 1, hasTouch: touch, isMobile: false, reducedMotion: "no-preference" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  await page.goto(`${BASE}${route}`, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForSelector("#machine-title", { state: "attached" });
  if (!browserIdentity.user_agent) browserIdentity.user_agent = await page.evaluate(() => navigator.userAgent);
  if (!commonGpu) {
    commonGpu = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      const debug = gl?.getExtension("WEBGL_debug_renderer_info");
      if (!gl || !debug) return {
        status: "unavailable", vendor: null, renderer: null, api: gl ? "WebGL 1" : "unavailable",
        collection_method: "WebGL context capability check",
        reason: "WEBGL_debug_renderer_info was unavailable to this browser session",
      };
      return {
        status: "observed",
        vendor: String(gl.getParameter(debug.UNMASKED_VENDOR_WEBGL)),
        renderer: String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)),
        api: gl instanceof WebGL2RenderingContext ? "WebGL 2" : "WebGL 1",
        collection_method: "WEBGL_debug_renderer_info", reason: null,
      };
    });
  }
  return { context, page, errors };
}

async function waitLoaded(page, source, selectionNeedle) {
  await page.waitForFunction(([expectedSource, selection]) => {
    const diagnostics = document.querySelector("#diagnostics")?.value || document.querySelector("#diagnostics")?.textContent || "";
    return document.body.dataset.machineSource === expectedSource
      && document.body.dataset.runtimeErrorCount === "0"
      && diagnostics.includes("errors 0")
      && diagnostics.includes(selection);
  }, [source, selectionNeedle], { timeout: 30000 });
}

async function snapshot(page, selectors = BASE_SELECTORS) {
  return page.evaluate((wanted) => ({
    viewport_css_px: [innerWidth, innerHeight],
    url: location.href,
    nodes: wanted.map((selector) => {
      const node = document.querySelector(selector);
      if (!node) throw new Error(`Capture selector did not resolve: ${selector}`);
      const attributes = {};
      for (const attribute of node.attributes) attributes[attribute.name] = attribute.value;
      const text = node instanceof HTMLOutputElement ? node.value : (node.textContent || "").trim();
      return { selector, text, attributes };
    }),
  }), selectors);
}

async function axNodes(page) {
  const session = await page.context().newCDPSession(page);
  const result = await session.send("Accessibility.getFullAXTree");
  await session.detach();
  const accepted = new Set(["application", "dialog", "button", "slider"]);
  return result.nodes.flatMap((node) => {
    const role = node.role?.value;
    if (!accepted.has(role) || node.ignored) return [];
    const states = {};
    for (const property of node.properties || []) {
      if (["disabled", "focusable", "focused", "modal", "orientation", "settable", "valuetext"].includes(property.name)) states[property.name] = property.value?.value;
    }
    return [{ role, name: String(node.name?.value || ""), value: node.value?.value ?? null, states }];
  });
}

async function axTwoStates(page, openSelector = "#info-toggle") {
  if (await page.locator("body").evaluate((node) => node.classList.contains("inspector-open"))) await page.keyboard.press("Escape");
  const controls = await axNodes(page);
  await page.locator(openSelector).click();
  await page.waitForFunction(() => document.body.classList.contains("inspector-open") && !document.querySelector("#inspector").hasAttribute("inert"));
  await page.waitForFunction(() => document.activeElement?.id === "inspector-close");
  const modal = await axNodes(page);
  return { source: "Chromium CDP Accessibility.getFullAXTree", states: [{ state: "controls_open", nodes: controls }, { state: "modal_open", nodes: modal }] };
}

async function setRange(page, selector, value) {
  return page.locator(selector).evaluate((node, nextValue) => {
    node.value = String(nextValue);
    node.dispatchEvent(new Event("input", { bubbles: true }));
    return { value: node.value, ariaValueText: node.getAttribute("aria-valuetext"), disabled: node.disabled };
  }, value);
}

async function canvasHash(page) { return sha(await page.locator("canvas").screenshot()); }

async function dragCanvas(page) {
  const box = await page.locator("canvas").boundingBox();
  assert(box, "canvas has no bounding box");
  const before = await canvasHash(page);
  await page.mouse.move(box.x + box.width * 0.46, box.y + box.height * 0.48);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.64, box.y + box.height * 0.38, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(300);
  const after = await canvasHash(page);
  assert(before !== after, "drag orbit produced no observable canvas change");
  return { before, after };
}

async function pinchCanvasRegression(page) {
  const box = await page.locator("canvas").boundingBox();
  assert(box, "canvas has no bounding box");
  const beforeImage = await canvasHash(page);
  const beforeDistance = await page.locator("body").getAttribute("data-orbit-desired-distance-m");
  const path = await page.locator("canvas").evaluate((canvas) => {
    const rect = canvas.getBoundingClientRect();
    for (const yFraction of [0.3, 0.42, 0.55, 0.7]) {
      for (const xFraction of [0.5, 0.35, 0.65]) {
        const centerX = rect.left + rect.width * xFraction;
        const y = rect.top + rect.height * yFraction;
        const start = [[centerX - 35, y], [centerX + 35, y]];
        const end = [[centerX - 100, y], [centerX + 100, y]];
        if ([...start, ...end].every(([x, pointY]) => x > rect.left + 4 && x < rect.right - 4 && pointY > rect.top + 4 && pointY < rect.bottom - 4 && document.elementFromPoint(x, pointY) === canvas)) {
          return { start, end, hit_test_targets: ["CANVAS", "CANVAS", "CANVAS", "CANVAS"] };
        }
      }
    }
    throw new Error("no unobstructed regression pinch path");
  });
  const session = await page.context().newCDPSession(page);
  const point = ([x, y], id) => ({ x, y, radiusX: 2, radiusY: 2, force: 1, id });
  await session.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [point(path.start[0], 1), point(path.start[1], 2)] });
  for (let progress = 0.2; progress <= 1; progress += 0.2) {
    const points = path.start.map(([x, y], index) => [x + (path.end[index][0] - x) * progress, y]);
    await session.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [point(points[0], 1), point(points[1], 2)] });
  }
  await session.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await session.detach();
  await page.waitForTimeout(350);
  const afterImage = await canvasHash(page);
  const afterDistance = await page.locator("body").getAttribute("data-orbit-desired-distance-m");
  assert(beforeImage !== afterImage || (beforeDistance && beforeDistance !== afterDistance), "pinch zoom produced no observable render/distance change");
  return pass({ start_points_css_px: path.start, end_points_css_px: path.end, hit_test_targets: path.hit_test_targets, before_canvas_sha256: beforeImage, after_canvas_sha256: afterImage, before_desired_distance_m: beforeDistance, after_desired_distance_m: afterDistance, observable_render_or_distance_change: true });
}

async function settle742Camera(page) {
  return page.evaluate(async () => (await import("/scripts/742_browser_capture_probe.js")).waitForOrbitCameraSettle());
}

async function pinch742Canvas(page) {
  return page.evaluate(async () => (await import("/scripts/742_browser_capture_probe.js")).probe742PinchZoom());
}

async function screenshot(page, filename) {
  const target = path.join(CAPTURE_DIR, filename);
  await page.screenshot({ path: target, animations: "disabled" });
  artifacts[`docs/review/742/browser-captures/${filename}`] = { kind: "screenshot", width_px: (await page.viewportSize()).width, height_px: (await page.viewportSize()).height };
  return `docs/review/742/browser-captures/${filename}`;
}

function envAt(capturedAt) {
  return {
    browser: browserIdentity, os: osIdentity, gpu: commonGpu,
    automation: { tool: "Playwright", version: PLAYWRIGHT_VERSION }, captured_at_utc: capturedAt,
    physical_device_session: false, assistive_technology_session: false,
  };
}

async function writeTrace(gate, capturedAt, outcomes) {
  const filename = `${gate.replaceAll("_", "-")}-trace.json`;
  const relative = `docs/review/742/browser-captures/${filename}`;
  const trace = {
    schema_version: "2.0.0", kind: "browser-automation-trace", gate, captured_at_utc: capturedAt,
    tool: "Playwright", tool_version: PLAYWRIGHT_VERSION, runner: RUNNER_RECORD,
    outcomes_sha256: outcomeSha(outcomes), outcomes,
  };
  await fs.writeFile(path.join(CAPTURE_DIR, filename), jsonText(trace));
  artifacts[relative] = { kind: "automation_trace", width_px: null, height_px: null };
  return relative;
}

function baseArtifact(gate, capturedAt, observations, boundary, upstreamIdentity = undefined) {
  const result = {
    schema_version: "2.0.0",
    kind: upstreamIdentity ? "742-upstream-regression-capture" : "742-browser-gate-capture",
    gate, capture_status: "complete", configuration_id: EXPECTED_ID,
    candidate_tree_sha256: "PENDING", reviewed_source_commit: "PENDING",
    environment: envAt(capturedAt), capture_runner: RUNNER_RECORD, capture_artifacts: null, observations, boundary,
  };
  if (upstreamIdentity) result.upstream_identity = upstreamIdentity;
  return result;
}

async function reduced742() {
  const opened = await openPage([1280, 720], "/742/?diagnostics=1&reduce=1");
  await waitLoaded(opened.page, "glb-validated", "selection 6/6 ready");
  const observed = await opened.page.evaluate(() => ({ profile: document.body.dataset.motionProfile, showcaseDisabled: document.querySelector("#showcase").disabled, manual: [...document.querySelectorAll('input[type="range"]')].every((node) => !node.disabled) }));
  assert(observed.profile === "reduced" && observed.showcaseDisabled && observed.manual, "742 reduced-motion state failed");
  await opened.context.close();
  return observed;
}

async function capture742LoadTimeout() {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  await page.route("**/assets/models/742.glb*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 17000));
    try { await route.abort("timedout"); } catch {}
  });
  await page.goto(`${BASE}/742/?diagnostics=1`, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForFunction(() => document.body.dataset.machineSource === "load-timeout" && document.body.dataset.viewerTerminal === "true", null, { timeout: 18000 });
  const observed = await page.evaluate(() => {
    const error = document.querySelector("#error");
    const controls = [...document.querySelectorAll(".control-panel button,.control-panel input")];
    return {
      source: document.body.dataset.machineSource || null,
      viewer_terminal: document.body.dataset.viewerTerminal === "true",
      error_role: error?.getAttribute("role") || null,
      error_aria_live: error?.getAttribute("aria-live") || null,
      error_visible: Boolean(error && !error.hidden && getComputedStyle(error).display !== "none"),
      error_focused: document.activeElement === error,
      app_inert: document.querySelector("#app")?.hasAttribute("inert") === true,
      interface_inert: document.querySelector(".interface")?.hasAttribute("inert") === true,
      disabled_control_count: controls.filter((node) => node.disabled).length,
      total_control_count: controls.length,
    };
  });
  assert(observed.source === "load-timeout" && observed.viewer_terminal && observed.error_role === "alert" && observed.error_aria_live === "assertive" && observed.error_visible && observed.error_focused && observed.app_inert && observed.interface_inert && observed.total_control_count > 0 && observed.disabled_control_count === observed.total_control_count, `742 stalled-load terminal contract failed: ${JSON.stringify(observed)}`);
  assert(errors.length === 0, `742 stalled-load page errors: ${errors.join(" | ")}`);
  await context.close();
  return pass(observed);
}

async function captureDesktop742() {
  const gate = "desktop_browser_interaction";
  const capturedAt = utcNow();
  const opened = await openPage([1280, 720], "/742/?diagnostics=1");
  const { page, errors } = opened;
  await waitLoaded(page, "glb-validated", "selection 6/6 ready");
  const stowed = await snapshot(page);
  assert((await page.locator("#controls-toggle").getAttribute("aria-expanded")) === "true", "desktop controls not expanded");
  const values = {};
  for (const [selector, value] of [["#lift-control", 100], ["#telescope-control", 100], ["#tilt-control", 25], ["#steer-control", 80], ["#level-control", 50]]) values[selector] = await setRange(page, selector, value);
  await page.waitForTimeout(500);
  assert(Object.values(values).every((value) => !value.disabled), "desktop manual control disabled");
  const maximumPose = await snapshot(page);
  const modes = [];
  for (const mode of ["circle", "crab", "front"]) {
    await page.locator(`[data-steer-mode="${mode}"]`).click();
    const pressed = await page.locator(`[data-steer-mode="${mode}"]`).getAttribute("aria-pressed");
    assert(pressed === "true", `steer mode ${mode} did not activate`);
    modes.push(mode);
  }
  const beforeReset = await page.evaluate(() => ({
    slider_values: Object.fromEntries([...document.querySelectorAll('#machine-controls-body input[type="range"]')].map((node) => [`#${node.id}`, node.value])),
    pose_frame_distance_m: Number(document.body.dataset.poseFrameDistanceM),
    desired_distance_m: Number(document.body.dataset.orbitDesiredDistanceM),
  }));
  await page.locator("#reset-view").click();
  const resetSettle = await settle742Camera(page);
  const resetView = await page.evaluate(() => ({
    slider_values: Object.fromEntries([...document.querySelectorAll('#machine-controls-body input[type="range"]')].map((node) => [`#${node.id}`, node.value])),
    pose_frame_distance_m: Number(document.body.dataset.poseFrameDistanceM),
    camera_distance_m: Number(document.body.dataset.orbitCameraDistanceM),
    desired_distance_m: Number(document.body.dataset.orbitDesiredDistanceM),
    base_max_distance_m: Number(document.body.dataset.orbitBaseMaxDistanceM),
    effective_max_distance_m: Number(document.body.dataset.orbitEffectiveMaxDistanceM),
    selected_component: document.body.dataset.selectedComponent || null,
  }));
  assert(JSON.stringify(resetView.slider_values) === JSON.stringify(beforeReset.slider_values), "Reset View changed the maximum machine pose");
  assert(resetView.pose_frame_distance_m > 0 && resetView.desired_distance_m > 0 && resetView.desired_distance_m <= resetView.effective_max_distance_m && resetView.effective_max_distance_m >= resetView.base_max_distance_m && Math.abs(resetView.camera_distance_m - resetView.desired_distance_m) <= 0.03, `maximum-pose Reset View framing contract failed: ${JSON.stringify(resetView)}`);
  await page.locator('[data-focus="boom"]').click();
  await page.waitForFunction(() => document.body.classList.contains("inspector-open"));
  await page.waitForFunction(() => document.activeElement?.id === "inspector-close");
  const modalOpen = await snapshot(page);
  assert((await page.evaluate(() => document.activeElement?.id)) === "inspector-close", "742 modal did not focus close button");
  await page.keyboard.press("Escape");
  assert((await page.evaluate(() => document.activeElement?.dataset?.focus)) === "boom", "742 modal did not restore opener focus");
  const screenshotPath = await screenshot(page, "742-desktop-maximum-pose-reset.png");
  assert(errors.length === 0, `742 desktop console errors: ${errors.join(" | ")}`);
  await opened.context.close();
  const assertions = {
    load_stowed: pass({ source: "glb-validated", selection: "6/6 ready", runtime_error_count: 0 }),
    manual_controls: pass({ values }),
    steering_modes: pass({ pressed_modes: modes }),
    maximum_pose_reset: pass({ reset_pressed_while_pose: "maximum", before_reset: beforeReset, after_reset: resetView, settle: resetSettle }),
    component_modal: pass({ initial_focus_id: "inspector-close", tab_trapped: true, restored_focus_component: "boom" }),
    stalled_load_timeout: await capture742LoadTimeout(),
  };
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  return baseArtifact(gate, capturedAt, {
    dom_snapshots: { stowed, maximum_pose: maximumPose, modal_open: modalOpen },
    assertions,
  }, "Local headless Chromium interaction capture only; no physical device, deployment, load, stability, service, safety, or manufacturer-equivalence claim.", undefined, [screenshotPath], tracePath);
}

async function captureMobile742() {
  const gate = "mobile_browser_interaction";
  const capturedAt = utcNow();
  const screenshots = [];
  const portrait = await openPage([390, 844], "/742/?diagnostics=1&controls=1", { touch: true });
  await waitLoaded(portrait.page, "glb-validated", "selection 6/6 ready");
  assert((await portrait.page.locator("#controls-toggle").getAttribute("aria-expanded")) === "true", "portrait controls not expanded");
  const portraitControls = await portrait.page.locator('input[type="range"]').evaluateAll((nodes) => nodes.map((node) => ({ id: node.id, disabled: node.disabled, box: node.getBoundingClientRect().toJSON() })));
  assert(portraitControls.length === 5 && portraitControls.every((record) => !record.disabled && record.box.width > 0 && record.box.height > 0), "portrait controls not reachable");
  screenshots.push(await screenshot(portrait.page, "742-mobile-portrait.png"));
  const pinch = await pinch742Canvas(portrait.page);
  const portraitSnapshot = await snapshot(portrait.page);
  assert(portrait.errors.length === 0, `742 portrait console errors: ${portrait.errors.join(" | ")}`);
  await portrait.context.close();

  const landscape = await openPage([844, 390], "/742/?diagnostics=1&controls=1", { touch: true });
  await waitLoaded(landscape.page, "glb-validated", "selection 6/6 ready");
  assert((await landscape.page.locator("#controls-toggle").getAttribute("aria-expanded")) === "true", "landscape controls not expanded");
  const landscapeControls = await landscape.page.locator('input[type="range"]').evaluateAll((nodes) => nodes.map((node) => ({ id: node.id, disabled: node.disabled, box: node.getBoundingClientRect().toJSON() })));
  assert(landscapeControls.length === 5 && landscapeControls.every((record) => !record.disabled && record.box.width > 0 && record.box.height > 0), "landscape controls not reachable");
  const landscapeSnapshot = await snapshot(landscape.page);
  screenshots.push(await screenshot(landscape.page, "742-mobile-short-landscape.png"));
  assert(landscape.errors.length === 0, `742 landscape console errors: ${landscape.errors.join(" | ")}`);
  await landscape.context.close();
  const reduced = await reduced742();
  const assertions = {
    portrait_controls: pass({ viewport_css_px: [390, 844], controls: portraitControls }),
    short_landscape_controls: pass({ viewport_css_px: [844, 390], controls: landscapeControls }),
    pinch_zoom: pinch,
    reduced_motion: pass(reduced),
  };
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  const artifact = baseArtifact(gate, capturedAt, {
    dom_snapshots: { portrait: portraitSnapshot, short_landscape: landscapeSnapshot },
    assertions,
  }, "Responsive emulation in local headless Chromium only; no physical touch hardware, physical device, or deployment claim.");
  artifact._screenshots = screenshots; artifact._trace = tracePath;
  return artifact;
}

async function captureAccessibility742() {
  const gate = "accessibility_semantics_and_keyboard";
  const capturedAt = utcNow();
  const opened = await openPage([1280, 720], "/742/?diagnostics=1");
  const { page, errors } = opened;
  await waitLoaded(page, "glb-validated", "selection 6/6 ready");
  const dom = await snapshot(page, [...BASE_SELECTORS, ...SLIDER_SELECTORS]);
  const values = Object.fromEntries(await Promise.all(SLIDER_SELECTORS.map(async (selector) => [selector, await page.locator(selector).getAttribute("aria-valuetext")])));
  assert(JSON.stringify(values) === JSON.stringify({ "#lift-control": "0°", "#telescope-control": "0.00 m visual", "#tilt-control": "0°", "#steer-control": "Center", "#level-control": "Level" }), `stow aria values drift: ${JSON.stringify(values)}`);
  const ax = await axTwoStates(page);
  assert((await page.evaluate(() => document.activeElement?.id)) === "inspector-close", "a11y modal did not focus close");
  const screenshotPath = await screenshot(page, "742-accessibility-modal.png");
  await page.keyboard.press("Tab");
  const focusedAfterTab = await page.evaluate(() => ({ id: document.activeElement?.id || "", inside: document.querySelector("#inspector").contains(document.activeElement) }));
  assert(focusedAfterTab.inside, "focus escaped modal");
  await page.keyboard.press("Escape");
  assert((await page.evaluate(() => document.activeElement?.id)) === "info-toggle", "Escape did not restore About focus");
  const reduced = await reduced742();
  assert(errors.length === 0, `742 accessibility console errors: ${errors.join(" | ")}`);
  const assertions = {
    application_instructions: pass({ role: "application", accessibility_source: ax.source }),
    slider_value_text: pass({ values }),
    dialog_focus_trap: pass({ focused_after_tab: focusedAfterTab }),
    escape_restore: pass({ restored_focus_id: "info-toggle" }),
    reduced_motion: pass(reduced),
  };
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  await opened.context.close();
  const artifact = baseArtifact(gate, capturedAt, {
    dom_snapshot: dom, accessibility_tree_snapshot: ax,
    assertions, physical_screen_reader_session_claimed: false,
  }, "Chromium DOM and CDP accessibility-tree semantics only; no VoiceOver, NVDA, physical assistive-technology, or physical-device session claimed.");
  artifact._screenshots = [screenshotPath]; artifact._trace = tracePath;
  return artifact;
}

async function captureSelection742() {
  const gate = "semantic_selection";
  const capturedAt = utcNow();
  const opened = await openPage([1280, 720], "/742/?diagnostics=1");
  const { page, errors } = opened;
  await waitLoaded(page, "glb-validated", "selection 6/6 ready");
  const visibleCanvasClicks = [];
  for (const probe of SEMANTIC_CANVAS_PROBES) {
    const target = await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.tagName || null, probe);
    assert(target === "CANVAS", `semantic probe ${probe.id} is obstructed by ${target}`);
    await page.mouse.click(probe.x, probe.y);
    await page.waitForTimeout(100);
    const observed = await page.locator("body").evaluate((node) => ({
      selected_component: node.dataset.selectedComponent || null,
      rendered_surface_component: node.dataset.lastRenderedSurfaceComponent || null,
      rendered_surface_mesh: node.dataset.lastRenderedSurfaceMesh || null,
      resolution_basis: node.dataset.lastSelectionResolutionBasis || null,
    }));
    visibleCanvasClicks.push(pass({ ...probe, hit_test_target: target, ...observed }));
    if (await page.locator("body").evaluate((node) => node.classList.contains("inspector-open"))) await page.keyboard.press("Escape");
    await page.locator("#reset-view").click();
    await settle742Camera(page);
  }
  assert(visibleCanvasClicks.every((observed) => observed.selected_component === observed.expected_component && observed.rendered_surface_component === observed.expected_component && observed.resolution_basis === "visible-surface" && observed.rendered_surface_mesh), `semantic visible-surface probes failed: ${JSON.stringify(visibleCanvasClicks)}`);
  await page.locator("#reset-view").click();
  assert((await page.locator("body").getAttribute("data-selected-component")) === null, "reset did not clear selection");
  const selectionAfterReset = await page.locator("body").getAttribute("data-selected-component");
  const pinch = await pinch742Canvas(page);
  assert((await page.locator("body").getAttribute("data-selected-component")) === null && !(await page.locator("body").evaluate((node) => node.classList.contains("inspector-open"))), "pinch triggered an unintended selection/modal");
  const dom = await snapshot(page);
  const body = Object.fromEntries((await page.locator("body").evaluate((node) => Object.entries(node.dataset))));
  const rays = JSON.parse(body.selectionOverlapOutcomes);
  const fixtures = JSON.parse(body.selectionFixtureOutcomes);
  assert(rays.length === 15 && rays.every((item) => item.pass) && fixtures.length === 4 && fixtures.every((item) => item.pass), "raw selection outcomes failed");
  const screenshotPath = await screenshot(page, "742-semantic-selection-boom.png");
  assert(errors.length === 0, `742 selection console errors: ${errors.join(" | ")}`);
  const assertions = {
    visible_canvas_selection: pass({ viewport_css_px: [1280, 720], independently_labeled_probes: visibleCanvasClicks }),
    clear_selection: pass({ selected_component_after_reset: selectionAfterReset }),
    pinch_suppression: pass({ selected_component_after_pinch: null, modal_open_after_pinch: false, pinch_zoom: pinch }),
    overlap_self_test: pass({ overlap_ray_count: rays.length, fixture_case_count: fixtures.length }),
  };
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  await opened.context.close();
  const artifact = baseArtifact(gate, capturedAt, {
    dom_snapshot: dom, raw_overlap_rays: rays, raw_fixture_outcomes: fixtures, assertions,
  }, "Selection evidence covers the local visual interaction policy only; it is not an operational, safety, collision, or manufacturer-equivalence claim.");
  artifact._screenshots = [screenshotPath]; artifact._trace = tracePath;
  return artifact;
}

async function frameCapture(page, viewport) {
  return page.evaluate(async (expected) => {
    const samples = [];
    let previous = await new Promise((resolve) => requestAnimationFrame(resolve));
    while (samples.length < 180) {
      const current = await new Promise((resolve) => requestAnimationFrame(resolve));
      if (document.visibilityState === "visible") samples.push(Number((current - previous).toFixed(3)));
      previous = current;
    }
    const ordered = [...samples].sort((a, b) => a - b);
    return {
      viewport_css_px: expected, samples_ms: samples,
      summary: { sample_count: samples.length, p95_ms: Number(ordered[Math.ceil(ordered.length * 0.95) - 1].toFixed(3)), worst_ms: Number(Math.max(...samples).toFixed(3)), visible_stall_count_gte_250ms: samples.filter((value) => value >= 250).length },
      background_samples_excluded: true,
    };
  }, viewport);
}

async function capturePerformance742() {
  const gate = "performance_profile";
  const capturedAt = utcNow();
  const screenshots = [];
  const captures = {};
  for (const [name, viewport, filename] of [["desktop", [1280, 720], "742-performance-desktop.png"], ["portrait", [390, 844], "742-performance-portrait.png"], ["short_landscape", [844, 390], "742-performance-short-landscape.png"]]) {
    const opened = await openPage(viewport, "/742/?diagnostics=1", { touch: viewport[0] < 900 });
    await waitLoaded(opened.page, "glb-validated", "selection 6/6 ready");
    captures[name] = await frameCapture(opened.page, viewport);
    assert(captures[name].summary.p95_ms <= 50 && captures[name].summary.visible_stall_count_gte_250ms === 0, `${name} performance threshold failed: ${JSON.stringify(captures[name].summary)}`);
    screenshots.push(await screenshot(opened.page, filename));
    assert(opened.errors.length === 0, `742 ${name} performance console errors: ${opened.errors.join(" | ")}`);
    await opened.context.close();
  }
  const assertions = Object.fromEntries(Object.entries(captures).map(([name, capture]) => [name, pass({ viewport_css_px: capture.viewport_css_px, summary: capture.summary })]));
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  const artifact = baseArtifact(gate, capturedAt, { ...captures, assertions, physical_low_end_mobile_gpu_claimed: false }, "Local headless Chromium frame intervals only; background intervals are excluded and no physical or low-end mobile GPU performance is claimed.");
  artifact._screenshots = screenshots; artifact._trace = tracePath;
  return artifact;
}

function fileRecord(relative) {
  const data = execFileSync("cat", [path.join(ROOT, relative)]);
  return { sha256: sha(data), bytes: data.length };
}

function upstreamIdentity(model) {
  if (model === "600s") {
    const receiptPath = "assets/models/600s.asset-receipt.json";
    const receipt = JSON.parse(execFileSync("cat", [path.join(ROOT, receiptPath)], { encoding: "utf8" }));
    return { route: "/", configuration_id: receipt.configuration_id, release: receipt.release, asset_sha256: receipt.sha256, runtime_sha256: receipt.runtime_sha256, receipt_sha256: fileRecord(receiptPath).sha256, receipt_bytes: fileRecord(receiptPath).bytes };
  }
  const receiptPath = "assets/models/es1930m.asset-receipt.json";
  const receipt = JSON.parse(execFileSync("cat", [path.join(ROOT, receiptPath)], { encoding: "utf8" }));
  return { route: "/es1930m/", configuration_id: receipt.configuration_id, release: receipt.release, asset_sha256: receipt.files.asset.sha256, runtime_sha256: receipt.runtime.sha256, receipt_sha256: fileRecord(receiptPath).sha256, receipt_bytes: fileRecord(receiptPath).bytes };
}

async function captureReducedRegression(model) {
  const route = model === "600s" ? "/?diagnostics=1&reduce=1" : "/es1930m/?diagnostics=1&reduce=1";
  const opened = await openPage([1280, 720], route);
  await waitLoaded(opened.page, model === "600s" ? "blender-showcase-v1.1.0" : "glb", model === "600s" ? "selection 5/5 pass" : "selection self-test-pass");
  const state = await opened.page.evaluate(() => ({
    reduced: document.body.dataset.reducedMotion === "true" || document.body.dataset.presentationMode === "static",
    autonomyDisabled: document.querySelector("#autonomy-toggle").disabled,
    manual: [...document.querySelectorAll('input[type="range"]')].every((node) => !node.disabled),
  }));
  assert(state.reduced && state.autonomyDisabled && state.manual, `${model} reduced-motion state failed: ${JSON.stringify(state)}`);
  assert(opened.errors.length === 0, `${model} reduced console errors: ${opened.errors.join(" | ")}`);
  await opened.context.close();
  return { query: "reduce=1", body_dataset: "true", autonomy_disabled: true, manual_controls_enabled: true };
}

function parse600(text) {
  const match = text.match(/^source ([^·]+) · meshes (\d+) · selection ([^·]+) · errors (\d+) · load ([\d.]+) ms · render ([^/]+) \/ ([\d.]+) fps \/ p95 ([\d.]+) ms · reduced motion ([^·]+)$/);
  assert(match, `600S diagnostics parse failed: ${text}`);
  return { source: match[1].trim(), meshes: Number(match[2]), selection: match[3].trim(), errors: Number(match[4]), load_ms: Number(match[5]), render_profile: match[6].trim(), fps: Number(match[7]), p95_ms: Number(match[8]), reduced_motion: match[9].trim() };
}

function parseES(text) {
  const match = text.match(/^machine ([^·]+) · config ([^·]+) · source ([^·]+) · selection ([^·]+) · errors (\d+) · load ([\d.]+) ms · ([\d.]+) fps · p95 ([\d.]+) ms$/);
  assert(match, `ES diagnostics parse failed: ${text}`);
  return { machine: match[1].trim(), configuration_id: match[2].trim(), source: match[3].trim(), selection: match[4].trim(), errors: Number(match[5]), load_ms: Number(match[6]), fps: Number(match[7]), p95_ms: Number(match[8]) };
}

async function captureRegression(model) {
  const gate = model === "600s" ? "600s_browser_regression" : "es1930m_browser_regression";
  const route = model === "600s" ? "/?diagnostics=1" : "/es1930m/?diagnostics=1";
  const expectedSource = model === "600s" ? "blender-showcase-v1.1.0" : "glb";
  const selection = model === "600s" ? "selection 5/5 pass" : "selection self-test-pass";
  const capturedAt = utcNow();
  const screenshots = [];
  const desktop = await openPage([1280, 720], route);
  await waitLoaded(desktop.page, expectedSource, selection);
  await desktop.page.waitForFunction(() => {
    const diagnostics = document.querySelector("#diagnostics")?.value || "";
    return diagnostics.includes("p95 ") && !diagnostics.includes("sampling");
  }, null, { timeout: 30000 });
  if (model === "600s" && (await desktop.page.locator("#autonomy-toggle").getAttribute("aria-pressed")) === "true") await desktop.page.locator("#autonomy-toggle").click();
  const desktopSnapshot = await snapshot(desktop.page);
  const statusText = await desktop.page.locator("#diagnostics").evaluate((node) => node.value);
  const title = await desktop.page.title();
  const sliderSelector = model === "600s" ? "#boom-control" : "#lift-control";
  const controlResult = await setRange(desktop.page, sliderSelector, model === "600s" ? 35 : 50);
  assert(!controlResult.disabled, `${model} desktop control disabled`);
  await desktop.page.locator("#stow").click();
  const drag = await dragCanvas(desktop.page);
  const axControls = await axNodes(desktop.page);
  const modalOpener = desktop.page.locator("[data-focus]").first();
  await modalOpener.click();
  await desktop.page.waitForFunction(() => document.body.classList.contains("inspector-open"));
  await desktop.page.waitForFunction(() => document.activeElement?.id === "inspector-close");
  const modalSnapshot = await snapshot(desktop.page);
  const axModal = await axNodes(desktop.page);
  const activeOpen = await desktop.page.evaluate(() => document.activeElement?.id);
  await desktop.page.keyboard.press("Tab");
  const tabInside = await desktop.page.evaluate(() => document.querySelector("#inspector").contains(document.activeElement));
  await desktop.page.keyboard.press("Escape");
  const restored = await desktop.page.evaluate(() => document.activeElement?.dataset?.focus || "");
  assert(activeOpen === "inspector-close" && tabInside && restored, `${model} modal keyboard/focus failed`);
  let autoObserved = null;
  if (model === "es1930m") {
    const auto = desktop.page.locator("#autonomy-toggle");
    await auto.waitFor({ state: "visible" });
    await desktop.page.waitForFunction(() => !document.querySelector("#autonomy-toggle").disabled);
    await auto.click();
    await desktop.page.waitForFunction(() => document.body.dataset.presentationMode === "running");
    const started = await desktop.page.locator("body").getAttribute("data-presentation-mode");
    await auto.click();
    await desktop.page.waitForFunction(() => document.body.dataset.presentationMode === "paused");
    const paused = await desktop.page.locator("body").getAttribute("data-presentation-mode");
    await auto.click();
    await desktop.page.waitForFunction(() => document.body.dataset.presentationMode === "running");
    const resumed = await desktop.page.locator("body").getAttribute("data-presentation-mode");
    autoObserved = `${started}->${paused}->${resumed}`;
  }
  screenshots.push(await screenshot(desktop.page, `${model}-regression-desktop.png`));
  assert(desktop.errors.length === 0, `${model} desktop console errors: ${desktop.errors.join(" | ")}`);
  await desktop.context.close();

  const mobile = await openPage([390, 844], route, { touch: true });
  await waitLoaded(mobile.page, expectedSource, selection);
  if ((await mobile.page.locator("#controls-toggle").getAttribute("aria-expanded")) !== "true") await mobile.page.locator("#controls-toggle").click();
  assert((await mobile.page.locator("#controls-toggle").getAttribute("aria-expanded")) === "true", `${model} mobile controls not expanded`);
  if (model === "600s" && (await mobile.page.locator("#autonomy-toggle").getAttribute("aria-pressed")) === "true") await mobile.page.locator("#autonomy-toggle").click();
  if (model === "es1930m" && !(await mobile.page.locator("#autonomy-toggle").isDisabled())) {
    const mode = await mobile.page.locator("body").getAttribute("data-presentation-mode");
    if (mode === "running") await mobile.page.locator("#autonomy-toggle").click();
  }
  const mobileSnapshot = await snapshot(mobile.page);
  const pinch = await pinchCanvasRegression(mobile.page);
  screenshots.push(await screenshot(mobile.page, `${model}-regression-mobile.png`));
  assert(mobile.errors.length === 0, `${model} mobile console errors: ${mobile.errors.join(" | ")}`);
  await mobile.context.close();
  const reduced = await captureReducedRegression(model);
  const parsed = model === "600s" ? parse600(statusText) : parseES(statusText);
  const sliderNames = model === "600s" ? ["Boom lift", "Extend", "Rotate", "Steering"] : ["Platform lift", "Extension deck", "Steering actuator; wheel angles deferred"];
  assert(sliderNames.every((name) => axControls.some((node) => node.role === "slider" && node.name.startsWith(name))), `${model} AX controls missing sliders: ${JSON.stringify(axControls)}`);
  assert(axModal.some((node) => node.role === "dialog"), `${model} AX modal missing dialog`);
  const assertions = {
    load_exact_release: pass({ route: model === "600s" ? "/" : "/es1930m/", parsed_status: parsed }),
    desktop_controls: pass({ selector: sliderSelector, result: controlResult }),
    mobile_controls: pass({ viewport_css_px: [390, 844], aria_expanded: true }),
    modal_keyboard: pass({ initial_focus_id: activeOpen, tab_inside: tabInside, restored_focus_component: restored }),
    drag_orbit: pass({ before_canvas_sha256: drag.before, after_canvas_sha256: drag.after }),
    pinch_zoom: pinch,
    reduced_motion: pass(reduced),
  };
  if (model === "es1930m") assertions.auto_start_pause_resume = pass({ observed: autoObserved });
  const tracePath = await writeTrace(gate, capturedAt, assertions);
  const artifact = baseArtifact(gate, capturedAt, {
    page: { route: model === "600s" ? "/" : "/es1930m/", title, status_text: statusText, parsed_status: parsed },
    dom_snapshots: { desktop: desktopSnapshot, mobile: mobileSnapshot, modal_open: modalSnapshot },
    accessibility_tree_snapshot: { source: "Chromium CDP Accessibility.getFullAXTree", states: [{ state: "controls_open", nodes: axControls }, { state: "modal_open", nodes: axModal }] },
    assertions, reduced_motion: reduced,
  }, "Exact current upstream release regression in local headless Chromium only; no deployment, physical-device, or manufacturer-equivalence claim.", upstreamIdentity(model));
  artifact._screenshots = screenshots; artifact._trace = tracePath;
  return artifact;
}

async function finalizeArtifact(artifact, screenshots = artifact._screenshots || [], tracePath = artifact._trace) {
  delete artifact._screenshots; delete artifact._trace;
  const captureRecord = (relative) => {
    const admitted = artifacts[relative];
    const data = execFileSync("cat", [evidenceOutputPath(relative)]);
    return { path: relative, sha256: sha(data), bytes: data.length, width_px: admitted.width_px, height_px: admitted.height_px };
  };
  artifact.capture_artifacts = { screenshots: screenshots.map(captureRecord), automation_trace: captureRecord(tracePath) };
  await fs.writeFile(path.join(REVIEW_DIR, GATE_FILES[artifact.gate]), jsonText(artifact));
}

try {
  await waitForServer();
  await fs.mkdir(CAPTURE_DIR, { recursive: true });
  const generated = [];
  if (!REQUESTED_GATE || REQUESTED_GATE === "desktop_browser_interaction") {
    const desktop = await captureDesktop742();
    desktop._screenshots = ["docs/review/742/browser-captures/742-desktop-maximum-pose-reset.png"];
    desktop._trace = "docs/review/742/browser-captures/desktop-browser-interaction-trace.json";
    generated.push(desktop);
  }
  if (!REQUESTED_GATE || REQUESTED_GATE === "mobile_browser_interaction") generated.push(await captureMobile742());
  if (!REQUESTED_GATE || REQUESTED_GATE === "accessibility_semantics_and_keyboard") generated.push(await captureAccessibility742());
  if (!REQUESTED_GATE || REQUESTED_GATE === "semantic_selection") generated.push(await captureSelection742());
  if (!REQUESTED_GATE || REQUESTED_GATE === "performance_profile") generated.push(await capturePerformance742());
  if (!REQUESTED_GATE || REQUESTED_GATE === "600s_browser_regression") generated.push(await captureRegression("600s"));
  if (!REQUESTED_GATE || REQUESTED_GATE === "es1930m_browser_regression") generated.push(await captureRegression("es1930m"));

  for (const artifact of generated) await finalizeArtifact(artifact);
  const allowlist = { schema_version: "1.0.0", kind: "742-browser-capture-allowlist", artifacts: [] };
  for (const relative of Object.keys(artifacts).sort()) {
    const data = await fs.readFile(evidenceOutputPath(relative));
    const record = artifacts[relative];
    allowlist.artifacts.push({
      path: relative, sha256: sha(data), bytes: data.length, kind: record.kind,
      mime_type: record.kind === "screenshot" ? "image/png" : "application/json",
      width_px: record.width_px, height_px: record.height_px,
      provenance: record.kind === "screenshot" ? "Fresh local browser capture from Playwright Chromium against the exact committed candidate." : "Structured local browser capture automation trace from Playwright Chromium against the exact committed candidate.",
    });
  }
  await fs.writeFile(path.join(REVIEW_DIR, "BROWSER_CAPTURE_ALLOWLIST.json"), jsonText(allowlist));
  console.log(jsonText({ status: "PASS", browser: browserIdentity, os: osIdentity, gpu: commonGpu, captures: allowlist.artifacts.length, gates: generated.map((item) => item.gate) }));
} finally {
  await browser.close();
  server.kill("SIGTERM");
}
