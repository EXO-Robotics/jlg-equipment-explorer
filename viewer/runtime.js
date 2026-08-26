import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import ES1930M_MACHINE from "../machines/es1930m/machine.js?v=1.1.0";
import { directOrbitDragDelta, pointerDistance, scaledPinchDistance } from "./pointer-gestures.mjs?v=1.0.11";
import { advanceFigureEight, sampleFigureEight } from "./presentation-route.mjs?v=1.0.9";
import { activeAutoOverrides, beginAutoOverride, clearAutoOverrides, createAutoOverrideController, dampMotion, endAutoOverride, holdAutoOverride } from "./auto-override.mjs?v=1.0.0";

const MACHINES = Object.freeze({ es1930m: ES1930M_MACHINE });
const machine = MACHINES[document.body.dataset.machine];
if (!machine) throw new Error(`Unknown equipment route: ${document.body.dataset.machine}`);

document.body.dataset.viewerStarted = "true";
document.body.dataset.configurationId = machine.configurationId;
const query = new URLSearchParams(location.search);
const forceReducedMotion = query.get("reduce") === "1";
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
const ASSET_LOAD_TIMEOUT_MS = 15000;
let reducedMotion = forceReducedMotion || motionPreference.matches;
const app = document.querySelector("#app");
const loader = document.querySelector("#loader");
const loaderStatus = document.querySelector("#loader-status");
const loaderDetail = document.querySelector("#loader-detail");
const errorPanel = document.querySelector("#error");
const errorCopy = document.querySelector("#error-copy");
const controlsBody = document.querySelector("#machine-controls-body");
const controlsToggle = document.querySelector("#controls-toggle");
const controlPanel = document.querySelector(".control-panel");
const COMPACT_VIEWPORT_QUERY = "(max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)";
const mobileQuery = matchMedia(COMPACT_VIEWPORT_QUERY);
const diagnostics = document.querySelector("#diagnostics");
const diagnosticsEnabled = query.get("diagnostics") === "1";
const autonomyToggle = document.querySelector("#autonomy-toggle");
const autonomyMode = document.querySelector("#autonomy-mode");
const autonomyNote = document.querySelector("#autonomy-note");
const driveHeading = document.querySelector("#drive-heading");
const driveLoop = document.querySelector("#drive-loop");
const motionStatus = document.querySelector("#motion-status");

const state = { ...machine.stowState };
const runtime = { errors: 0, frames: 0, fps: "sampling", p95: "sampling", frameDurations: [], loadMs: "pending", selection: "pending" };
let model = null;
let rig = null;
let selected = null;
let lastFrame = performance.now();
let fpsStart = lastFrame;
let terminalFailure = false;
let animationFrameId = null;
let assetLoadTimeout = null;
let runtimeFrameCount = 0;
const presentationRoute = {
  enabled: false,
  requested: !reducedMotion && query.get("auto") !== "0",
  phase: 0,
  mechanismProgress: 0,
  distanceM: 0,
  wheelRotations: [0, 0, 0, 0],
};
const controlOverrides = createAutoOverrideController(machine.controls.map((control) => control.id));

function recordError(error) {
  runtime.errors += 1;
  document.body.dataset.runtimeErrorCount = String(runtime.errors);
  if (error) console.error(error);
  updateDiagnostics();
}
document.body.dataset.runtimeErrorCount = "0";

function updateDiagnostics() {
  diagnostics.hidden = !diagnosticsEnabled;
  diagnostics.value = `machine ${machine.id} · config ${machine.configurationId} · source ${document.body.dataset.machineSource || "loading"} · selection ${runtime.selection} · errors ${runtime.errors} · load ${runtime.loadMs} · ${runtime.fps} · ${runtime.p95}`;
}

function showTerminalError(error, message, source = "runtime-failed") {
  if (terminalFailure) return;
  terminalFailure = true;
  presentationRoute.enabled = false;
  clearTimeout(assetLoadTimeout);
  if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
  animationFrameId = null;
  document.body.dataset.machineSource = source;
  document.body.dataset.viewerRuntimeActive = "false";
  const useRuntimeFrameCount = runtimeFrameCount >= 2;
  const terminalFrameCount = useRuntimeFrameCount ? runtimeFrameCount : Number(document.body.dataset.bootFrameCount || 0);
  document.body.dataset.terminalFrameCount = String(terminalFrameCount);
  document.body.dataset.terminalFrameSource = useRuntimeFrameCount ? "runtime" : "boot";
  document.body.dataset.viewerTerminal = "true";
  document.body.classList.remove("inspector-open", "mobile-controls-open");
  document.body.classList.add("viewer-terminal-error");
  recordError(error);
  loader.hidden = true;
  errorCopy.textContent = message;
  errorPanel.hidden = false;
  app.setAttribute("inert", "");
  document.querySelector(".interface")?.setAttribute("inert", "");
  document.querySelector("#inspector")?.setAttribute("inert", "");
  controlsBody.inert = true;
  controlPanel.setAttribute("aria-disabled", "true");
  controlPanel.querySelectorAll("button, input").forEach((control) => { control.disabled = true; });
  errorPanel.focus({ preventScroll: true });
}

addEventListener("error", (event) => showTerminalError(event.error, "The ES1930M viewer stopped after an unexpected runtime error. No substitute was shown."));
addEventListener("unhandledrejection", (event) => showTerminalError(event.reason, "The ES1930M viewer stopped after an unexpected runtime error. No substitute was shown."));
document.body.dataset.viewerRuntimeActive = "true";

function rendererOrNull() {
  try {
    const canvas = document.createElement("canvas");
    if (!window.WebGLRenderingContext || !(canvas.getContext("webgl2") || canvas.getContext("webgl"))) return null;
    return new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  } catch {
    return null;
  }
}

const renderer = rendererOrNull();
if (!renderer) {
  showTerminalError(new Error("WebGL unavailable"), "This interactive study needs a browser with WebGL enabled.", "webgl-unavailable");
  throw new Error("WebGL unavailable");
}
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, mobileQuery.matches ? 1.35 : 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.04;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111719);
scene.fog = new THREE.Fog(0x111719, 14, 28);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.04, 50);
scene.add(new THREE.HemisphereLight(0xdce9f1, 0x262a25, 2.0));
for (const [color, intensity, position] of [[0xffefd4, 4.0, [-5, 9, 7]], [0x9fc9e2, 2.0, [5, 4, 6]], [0xff8b43, 1.5, [5, 4, -5]]]) {
  const light = new THREE.DirectionalLight(color, intensity);
  light.position.set(...position);
  light.castShadow = intensity > 3;
  light.shadow.mapSize.set(mobileQuery.matches ? 1024 : 2048, mobileQuery.matches ? 1024 : 2048);
  scene.add(light);
}
const floor = new THREE.Mesh(new THREE.CircleGeometry(18, 96), new THREE.MeshStandardMaterial({ color: 0x242a2a, roughness: 0.96, metalness: 0 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);
const grid = new THREE.GridHelper(34, 34, 0x5c5f56, 0x30342f);
grid.position.y = 0.004;
grid.material.transparent = true;
grid.material.opacity = 0.12;
scene.add(grid);

const orbit = { azimuth: -0.72, polar: 1.18, distance: mobileQuery.matches ? 5.3 : 4.5, target: new THREE.Vector3(0, 1.05, 0), desiredTarget: new THREE.Vector3(0, 1.05, 0), desiredDistance: mobileQuery.matches ? 5.3 : 4.5 };
function updateCamera(delta = 1) {
  const ease = reducedMotion ? 1 : Math.min(1, delta * 7);
  orbit.target.lerp(orbit.desiredTarget, ease);
  orbit.distance = THREE.MathUtils.lerp(orbit.distance, orbit.desiredDistance, ease);
  document.body.dataset.orbitCameraDistanceM = orbit.distance.toFixed(3);
  document.body.dataset.orbitDesiredDistanceM = orbit.desiredDistance.toFixed(3);
  const sinPolar = Math.sin(orbit.polar);
  camera.position.set(
    orbit.target.x + orbit.distance * sinPolar * Math.cos(orbit.azimuth),
    orbit.target.y + orbit.distance * Math.cos(orbit.polar),
    orbit.target.z + orbit.distance * sinPolar * Math.sin(orbit.azimuth),
  );
  camera.lookAt(orbit.target);
}
updateCamera();

const pointers = new Map();
let pinchDistance = null;
renderer.domElement.addEventListener("pointerdown", (event) => {
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: 0, pointerType: event.pointerType || "mouse" });
  renderer.domElement.setPointerCapture(event.pointerId);
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinchDistance = pointerDistance(a, b);
  }
});
renderer.domElement.addEventListener("pointermove", (event) => {
  const pointer = pointers.get(event.pointerId);
  if (!pointer) return;
  const dx = event.clientX - pointer.x;
  const dy = event.clientY - pointer.y;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  pointer.moved += Math.abs(dx) + Math.abs(dy);
  if (pointers.size >= 2) {
    const [a, b] = [...pointers.values()];
    const nextDistance = pointerDistance(a, b);
    orbit.desiredDistance = scaledPinchDistance(orbit.desiredDistance, pinchDistance, nextDistance);
    pinchDistance = nextDistance;
    for (const active of pointers.values()) active.moved += Math.abs(dx) + Math.abs(dy) + 8;
    return;
  }
  const drag = directOrbitDragDelta(dx, dy, pointer.pointerType);
  orbit.azimuth += drag.azimuth;
  orbit.polar = THREE.MathUtils.clamp(orbit.polar + drag.polar, 0.25, 1.52);
});
function finishPointer(event, allowSelection) {
  const pointer = pointers.get(event.pointerId);
  if (allowSelection && pointers.size === 1 && pointer?.moved < 8) selectAt(event.clientX, event.clientY);
  pointers.delete(event.pointerId);
  pinchDistance = null;
}
renderer.domElement.addEventListener("pointerup", (event) => finishPointer(event, true));
renderer.domElement.addEventListener("pointercancel", (event) => finishPointer(event, false));
renderer.domElement.addEventListener("lostpointercapture", (event) => finishPointer(event, false));
renderer.domElement.addEventListener("wheel", (event) => {
  event.preventDefault();
  orbit.desiredDistance = THREE.MathUtils.clamp(orbit.desiredDistance * Math.exp(event.deltaY * 0.001), 1.6, 18);
}, { passive: false });

const raycaster = new THREE.Raycaster();
const pointerNdc = new THREE.Vector2();
function componentFor(object) {
  let current = object;
  while (current && current !== model) {
    if (current.userData?.component) return current.userData.component;
    current = current.parent;
  }
  return null;
}
function selectAt(clientX, clientY) {
  if (!model) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointerNdc.set((clientX - rect.left) / rect.width * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointerNdc, camera);
  const volumes = machine.interactionVolumes.map((name) => model.getObjectByName(name)).filter(Boolean);
  const hit = raycaster.intersectObjects(volumes, false)[0];
  const component = hit ? componentFor(hit.object) : null;
  runtime.selection = component || "miss";
  if (component) {
    setPresentationRouteEnabled(false, { reset: true });
    openInspector(component);
  }
  updateDiagnostics();
}

function setOutputValue(output, value) {
  if (output.value !== value) output.value = value;
}

function setEngineeringValueText(input, value) {
  const detailId = `${input.id}-engineering-detail`;
  let detail = document.getElementById(detailId);
  if (!detail) {
    detail = document.createElement("span");
    detail.id = detailId;
    detail.className = "sr-only";
    input.insertAdjacentElement("afterend", detail);
  }
  if (detail.textContent !== value) detail.textContent = value;
  if (input.getAttribute("aria-valuetext") !== value) input.setAttribute("aria-valuetext", value);
  if (input.getAttribute("aria-details") !== detailId) input.setAttribute("aria-details", detailId);
}

function setControlOutputs() {
  const presentation = machine.presentState(state);
  for (const control of machine.controls) {
    const output = document.querySelector(`#${control.outputId}`);
    const input = document.querySelector(`#${control.inputId}`);
    const value = presentation.outputs[control.id];
    setOutputValue(output, value);
    const ariaValue = control.id === "lift"
      ? `${(0.90 + state.lift * (machine.specifications.indoorPlatformHeightM - 0.90)).toFixed(2)} metres platform height; ${presentation.status}`
      : control.id === "deck"
        ? `${value} extension; ${presentation.status}`
        : `${value} cylinder displacement; ${presentation.status}`;
    setEngineeringValueText(input, ariaValue);
  }
  document.body.dataset.zone = presentation.zone;
  if (!presentationRoute.enabled) setOutputValue(motionStatus, presentation.status);
}

function normalizedHeadingDegrees(radians) {
  return Math.round(((THREE.MathUtils.radToDeg(radians) % 360) + 360) % 360);
}

function resetPresentationPose() {
  if (!rig) return;
  rig.root.position.set(0, 0, 0);
  rig.root.rotation.y = 0;
  presentationRoute.phase = 0;
  presentationRoute.mechanismProgress = 0;
  presentationRoute.distanceM = 0;
  presentationRoute.wheelRotations.fill(0);
  for (const spindle of rig.steerSpindles) spindle.rotation.y = 0;
  for (const wheel of rig.wheelRollPivots) wheel.rotation.z = 0;
  document.body.dataset.driveX = "0.00";
  document.body.dataset.driveZ = "0.00";
}

function updatePresentationTelemetry(sample = sampleFigureEight(presentationRoute.phase)) {
  const locked = reducedMotion;
  const paused = !presentationRoute.enabled && presentationRoute.distanceM > 0;
  const overrideIds = presentationRoute.enabled ? activeAutoOverrides(controlOverrides) : [];
  const overrideLabel = overrideIds.map((id) => machine.controls.find((control) => control.id === id)?.label || id).join(" + ");
  const modeText = locked ? "Static pose" : presentationRoute.enabled ? overrideIds.length ? `Override · ${overrideLabel}` : "Auto loop" : paused ? "Auto paused" : "Manual";
  const noteText = locked
    ? "Motion disabled by reduced-motion preference."
    : presentationRoute.enabled
      ? overrideIds.length ? "Auto keeps driving; adjusted controls resume after 6 s." : "Move a slider for a 6 s override."
      : "All machine controls are live.";
  if (autonomyMode.value !== modeText) autonomyMode.value = modeText;
  if (autonomyNote.textContent !== noteText) autonomyNote.textContent = noteText;
  const heading = `${String(normalizedHeadingDegrees(sample.heading)).padStart(3, "0")}°`;
  const loop = `${Math.round((sample.phase / (Math.PI * 2)) * 100)}%`;
  if (driveHeading.textContent !== heading) driveHeading.textContent = heading;
  if (driveLoop.textContent !== loop) driveLoop.textContent = loop;
  autonomyToggle.disabled = locked || !rig;
  const pressed = String(presentationRoute.enabled);
  if (autonomyToggle.getAttribute("aria-pressed") !== pressed) autonomyToggle.setAttribute("aria-pressed", pressed);
  const buttonText = locked ? "Static" : presentationRoute.enabled ? "Auto" : "Manual";
  if (autonomyToggle.textContent !== buttonText) autonomyToggle.textContent = buttonText;
  autonomyToggle.setAttribute("aria-label", locked ? "Automatic drive unavailable" : presentationRoute.enabled ? "Switch to manual drive" : "Switch to automatic drive");
  document.body.dataset.presentationMode = locked ? "static" : presentationRoute.enabled ? "running" : paused ? "paused" : "ready";
  document.body.dataset.autonomyMode = locked ? "static" : presentationRoute.enabled ? overrideIds.length ? "override" : "auto" : paused ? "paused" : "manual";
  document.body.dataset.autonomyOverrides = overrideIds.join(",") || "none";
  if (presentationRoute.enabled) setOutputValue(motionStatus, overrideIds.length ? "Manual override" : "Autonomous");
  else if (paused) setOutputValue(motionStatus, "Paused");
}

function applyPresentationVisualSample(sample, steeringOverridden = false, delta = 1 / 60) {
  rig.steerSpindles[0].rotation.y = steeringOverridden ? 0 : sample.steerRight;
  rig.steerSpindles[1].rotation.y = steeringOverridden ? 0 : sample.steerLeft;
  rig.root.position.set(sample.x, 0, sample.z);
  rig.root.rotation.y = sample.heading;
  const follow = machine.followView(state, mobileQuery.matches);
  orbit.desiredTarget.set(sample.x, dampMotion(orbit.desiredTarget.y, follow.target[1], 2.4, delta), sample.z);
  orbit.desiredDistance = dampMotion(orbit.desiredDistance, follow.distance, 2.2, delta);
  document.body.dataset.driveX = sample.x.toFixed(2);
  document.body.dataset.driveZ = sample.z.toFixed(2);
  document.body.dataset.steerActuatorCommand = sample.steer.toFixed(3);
  document.body.dataset.visualSteerLeftRad = sample.steerLeft.toFixed(3);
  document.body.dataset.visualSteerRightRad = sample.steerRight.toFixed(3);
}

function setPresentationRouteEnabled(enabled, { reset = false } = {}) {
  presentationRoute.enabled = Boolean(enabled) && !reducedMotion && Boolean(rig);
  if (reset) resetPresentationPose();
  if (presentationRoute.enabled) {
    const sample = sampleFigureEight(presentationRoute.phase);
    machine.applyState(rig, machine.solveState(state));
    applyPresentationVisualSample(sample);
  }
  clearAutoOverrides(controlOverrides);
  setControlOutputs();
  updatePresentationTelemetry();
}

function syncReducedMotion(announce = false) {
  const nextReducedMotion = forceReducedMotion || motionPreference.matches;
  const changed = nextReducedMotion !== reducedMotion;
  reducedMotion = nextReducedMotion;
  document.body.dataset.reducedMotion = String(reducedMotion);
  document.body.dataset.motionProfile = reducedMotion ? "reduced" : "full";
  if (reducedMotion) {
    presentationRoute.enabled = false;
    setPresentationRouteEnabled(false);
    if (announce && changed) setOutputValue(motionStatus, "Reduced motion · auto stopped");
  } else {
    updatePresentationTelemetry();
    if (announce && changed) setOutputValue(motionStatus, "Manual · auto available");
  }
  updateDiagnostics();
}

const handleMotionPreferenceChange = () => syncReducedMotion(true);
if (motionPreference.addEventListener) motionPreference.addEventListener("change", handleMotionPreferenceChange);
else motionPreference.addListener(handleMotionPreferenceChange);

function updatePresentationRoute(delta, now = performance.now()) {
  if (!presentationRoute.enabled || !rig) return;
  const next = advanceFigureEight(presentationRoute.phase, delta);
  presentationRoute.phase = next.phase;
  presentationRoute.mechanismProgress = (presentationRoute.mechanismProgress + delta / (machine.showcaseDurationMs / 1000)) % 1;
  presentationRoute.distanceM += 0.72 * delta;
  const wheelRates = next.sample.wheelSpeedScales.map((scale) => -(0.72 * scale) / 0.13);
  for (let index = 0; index < presentationRoute.wheelRotations.length; index += 1) {
    presentationRoute.wheelRotations[index] += wheelRates[index] * delta;
  }
  const commands = { ...machine.showcase(presentationRoute.mechanismProgress), steer: next.sample.steer };
  const overrideIds = activeAutoOverrides(controlOverrides, now);
  for (const control of machine.controls) {
    if (!overrideIds.includes(control.id)) state[control.id] = dampMotion(state[control.id], commands[control.id], control.id === "steer" ? 8 : 3.2, delta);
    document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
  }
  machine.applyState(rig, machine.solveState(state));
  applyPresentationVisualSample(next.sample, overrideIds.includes("steer"), delta);
  for (let index = 0; index < rig.wheelRollPivots.length; index += 1) {
    rig.wheelRollPivots[index].rotation.z = presentationRoute.wheelRotations[index];
  }
  document.body.dataset.wheelRotationRad = presentationRoute.wheelRotations[0].toFixed(3);
  document.body.dataset.wheelRotationsRad = presentationRoute.wheelRotations.map((value) => value.toFixed(3)).join(",");
  setControlOutputs();
  updatePresentationTelemetry(next.sample);
}

autonomyToggle.addEventListener("click", () => setPresentationRouteEnabled(!presentationRoute.enabled));
syncReducedMotion(false);
updatePresentationTelemetry();
function fitMachineBounds() {
  if (!model) return;
  const bounds = new THREE.Box3();
  model.updateMatrixWorld(true);
  model.traverse((node) => {
    if (node.isMesh && node.visible && !node.userData?.is_hit_volume) bounds.expandByObject(node);
  });
  if (bounds.isEmpty()) return;
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
  const verticalDistance = size.y / (2 * Math.tan(verticalFov / 2));
  const horizontalDistance = Math.max(size.x, size.z) / (2 * Math.tan(horizontalFov / 2));
  const mobileControlsOpen = mobileQuery.matches && document.body.classList.contains("mobile-controls-open");
  const padding = mobileControlsOpen ? 2.08 : mobileQuery.matches ? 1.62 : 1.34;
  orbit.desiredTarget.copy(center);
  if (mobileControlsOpen) orbit.desiredTarget.y -= size.y * 0.21;
  orbit.desiredDistance = THREE.MathUtils.clamp(Math.max(verticalDistance, horizontalDistance) * padding, 2.2, 18);
}
function applyControls() {
  if (rig) machine.applyState(rig, machine.solveState(state));
  setControlOutputs();
  fitMachineBounds();
}
for (const control of machine.controls) {
  const input = document.querySelector(`#${control.inputId}`);
  input.addEventListener("pointerdown", () => beginAutoOverride(controlOverrides, control.id));
  const releaseControl = () => endAutoOverride(controlOverrides, control.id);
  input.addEventListener("pointerup", releaseControl);
  input.addEventListener("pointercancel", releaseControl);
  input.addEventListener("change", releaseControl);
  input.addEventListener("input", (event) => {
    state[control.id] = Number(event.currentTarget.value) / control.inputDivisor;
    if (presentationRoute.enabled) holdAutoOverride(controlOverrides, control.id);
    applyControls();
    updatePresentationTelemetry();
  });
}
document.querySelector("#stow").addEventListener("click", () => {
  setPresentationRouteEnabled(false, { reset: true });
  Object.assign(state, machine.stowState);
  for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
  applyControls();
});

function focusCamera(name) {
  const preset = machine.componentView(name, state, mobileQuery.matches);
  orbit.desiredTarget.set(...preset.target);
  orbit.desiredDistance = preset.distance;
  orbit.azimuth = preset.azimuth;
  orbit.polar = preset.polar;
}
document.querySelector("#reset-view").addEventListener("click", () => focusCamera("default"));
const inspector = document.querySelector("#inspector");
const infoToggle = document.querySelector("#info-toggle");
let inspectorOpener = null;
function openInspector(component) {
  const detail = machine.components[component];
  if (detail) {
    document.querySelector("#inspector-kicker").textContent = detail.eyebrow;
    document.querySelector("#inspector-title").textContent = detail.title;
    document.querySelector("#inspector-copy").textContent = detail.body;
    const facts = detail.facts || [["Authority", detail.eyebrow], ["Configuration", machine.configurationId], ["Boundary", "Visual reconstruction; not service or safety authority"]];
    document.querySelector("#inspector-facts").replaceChildren(...facts.map(([term, value]) => {
      const row = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = term;
      dd.textContent = value;
      row.append(dt, dd);
      return row;
    }));
  }
  if (!document.body.classList.contains("inspector-open")) inspectorOpener = document.activeElement;
  document.body.classList.add("inspector-open");
  inspector.inert = false;
  infoToggle.setAttribute("aria-expanded", "true");
  requestAnimationFrame(() => document.querySelector("#inspector-close").focus());
}
function closeInspector() {
  document.body.classList.remove("inspector-open");
  inspector.inert = true;
  infoToggle.setAttribute("aria-expanded", "false");
  const restore = inspectorOpener;
  inspectorOpener = null;
  if (restore?.isConnected && typeof restore.focus === "function") restore.focus();
}
infoToggle.addEventListener("click", () => openInspector("about"));
document.querySelector("#inspector-close").addEventListener("click", closeInspector);
document.querySelector("#scrim").addEventListener("click", closeInspector);

function setControlsPanel(open) {
  const expanded = Boolean(open);
  controlsBody.hidden = !expanded;
  controlsBody.inert = !expanded;
  controlsToggle.hidden = false;
  controlsToggle.setAttribute("aria-expanded", String(expanded));
  controlsToggle.setAttribute("aria-label", expanded ? "Close machine controls" : "Open machine controls");
  controlsToggle.querySelector(".controls-action").textContent = expanded ? "Close" : (mobileQuery.matches ? "Adjust" : "Open");
  document.body.classList.toggle("mobile-controls-open", mobileQuery.matches && expanded);
  document.body.classList.toggle("controls-panel-collapsed", !expanded);
  requestAnimationFrame(syncMobileControlHeight);
  requestAnimationFrame(fitMachineBounds);
}
function syncMobileControlHeight() {
  if (!mobileQuery.matches) return document.documentElement.style.removeProperty("--mobile-controls-height");
  document.documentElement.style.setProperty("--mobile-controls-height", `${Math.ceil(controlPanel.getBoundingClientRect().height)}px`);
}
new ResizeObserver(syncMobileControlHeight).observe(controlPanel);
controlsToggle.addEventListener("click", () => setControlsPanel(controlsToggle.getAttribute("aria-expanded") !== "true"));
mobileQuery.addEventListener?.("change", () => setControlsPanel(!mobileQuery.matches));
setControlsPanel(mobileQuery.matches ? query.get("controls") === "1" : true);

document.addEventListener("keydown", (event) => {
  if (document.body.classList.contains("inspector-open")) {
    if (event.key === "Escape") { event.preventDefault(); closeInspector(); }
    else if (event.key === "Tab") {
      const focusable = [...inspector.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), [tabindex]:not([tabindex="-1"])')].filter((node) => !node.hidden);
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    return;
  }
  if (event.target instanceof HTMLElement && event.target.matches("input, select, textarea, button, [contenteditable='true']")) return;
  if (event.key === "ArrowLeft") orbit.azimuth += 0.12;
  else if (event.key === "ArrowRight") orbit.azimuth -= 0.12;
  else if (event.key === "ArrowUp") orbit.polar = Math.max(0.25, orbit.polar - 0.08);
  else if (event.key === "ArrowDown") orbit.polar = Math.min(1.52, orbit.polar + 0.08);
  else if (event.key === "+" || event.key === "=") orbit.desiredDistance = Math.max(1.6, orbit.desiredDistance * 0.9);
  else if (event.key === "-" || event.key === "_") orbit.desiredDistance = Math.min(18, orbit.desiredDistance * 1.1);
  else if (event.key === "0") focusCamera("default");
  else return;
  event.preventDefault();
});

const loadStarted = performance.now();
assetLoadTimeout = setTimeout(() => {
  showTerminalError(new Error(`${machine.identity.model} asset load exceeded ${ASSET_LOAD_TIMEOUT_MS} ms`), `The evidence-bound ${machine.identity.model} asset did not finish loading in time. No substitute was shown.`, "load-timeout");
}, ASSET_LOAD_TIMEOUT_MS);
try {
  new GLTFLoader().load(machine.assetUrl, (gltf) => {
    clearTimeout(assetLoadTimeout);
    if (terminalFailure) return;
    try {
      if (globalThis.__EQUIPMENT_EXPLORER_TEST_FAULT__ === "asset-contract") throw new Error("Injected ES1930M asset-contract failure");
      const validation = machine.validateAsset(gltf.scene);
      if (!validation.ok) throw new Error(`${machine.identity.model} asset validation failed: ${validation.missing.join(", ")}`);
      model = gltf.scene;
      model.traverse((node) => {
        if (node.isMesh) {
          if (node.userData?.is_hit_volume) {
            node.material = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false });
            node.castShadow = false;
            node.receiveShadow = false;
          } else {
            node.castShadow = true;
            node.receiveShadow = true;
          }
        }
      });
      rig = machine.createRig(model);
      applyControls();
      const selfTest = machine.selfTestRig?.(rig, state) || { ok: true, failures: [] };
      if (!selfTest.ok) throw new Error(`Interaction motion self-test failed: ${selfTest.failures.join(", ")}`);
      scene.add(model);
      runtime.loadMs = `${Math.round(performance.now() - loadStarted)} ms`;
      runtime.selection = "self-test-pass";
      document.body.dataset.machineSource = "glb";
      document.body.dataset.machineVisibleMeshes = String(model.getObjectsByProperty("isMesh", true).length);
      setPresentationRouteEnabled(presentationRoute.requested);
      loaderStatus.textContent = `${machine.identity.model} ready`;
      loaderDetail.textContent = `${machine.configurationId} validated`;
      loader.classList.add("done");
      updateDiagnostics();
    } catch (error) {
      if (model) scene.remove(model);
      model = null;
      rig = null;
      showTerminalError(error, `The ${machine.identity.model} asset failed its hierarchy or motion contract. No substitute was shown.`, "contract-failed");
    }
  }, undefined, (error) => {
    clearTimeout(assetLoadTimeout);
    showTerminalError(error, `The evidence-bound ${machine.identity.model} asset could not be loaded. No procedural substitute was used.`, "load-failed");
  });
} catch (error) {
  clearTimeout(assetLoadTimeout);
  showTerminalError(error, `The evidence-bound ${machine.identity.model} asset loader could not start. No procedural substitute was used.`, "loader-start-failed");
}

function animate(now) {
  if (terminalFailure) return;
  animationFrameId = requestAnimationFrame(animate);
  runtimeFrameCount += 1;
  document.body.dataset.runtimeFrameCount = String(runtimeFrameCount);
  document.body.dataset.runtimeLastFrameMs = Number(now).toFixed(3);
  const delta = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;
  updatePresentationRoute(delta, now);
  updateCamera(delta);
  renderer.render(scene, camera);
  runtime.frames += 1;
  runtime.frameDurations.push(delta * 1000);
  if (now - fpsStart > 1500) {
    runtime.fps = `${Math.round(runtime.frames * 1000 / (now - fpsStart))} fps`;
    const sortedDurations = runtime.frameDurations.slice().sort((a, b) => a - b);
    runtime.p95 = `p95 ${sortedDurations[Math.min(sortedDurations.length - 1, Math.floor(sortedDurations.length * 0.95))].toFixed(1)} ms`;
    runtime.frames = 0;
    runtime.frameDurations.length = 0;
    fpsStart = now;
    updateDiagnostics();
  }
}
if (!terminalFailure) animationFrameId = requestAnimationFrame(animate);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  fitMachineBounds();
});
setControlOutputs();
updateDiagnostics();
