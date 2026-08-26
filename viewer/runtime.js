import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import ES1930M_MACHINE from "../machines/es1930m/machine.js?v=1.0.2";
import { pointerDistance, scaledPinchDistance } from "./pointer-gestures.mjs?v=1.0.2";

const MACHINES = Object.freeze({ es1930m: ES1930M_MACHINE });
const machine = MACHINES[document.body.dataset.machine];
if (!machine) throw new Error(`Unknown equipment route: ${document.body.dataset.machine}`);

document.body.dataset.viewerStarted = "true";
document.body.dataset.configurationId = machine.configurationId;
const query = new URLSearchParams(location.search);
const reducedMotion = query.get("reduce") === "1" || matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const app = document.querySelector("#app");
const loader = document.querySelector("#loader");
const loaderStatus = document.querySelector("#loader-status");
const loaderDetail = document.querySelector("#loader-detail");
const errorPanel = document.querySelector("#error");
const errorCopy = document.querySelector("#error-copy");
const controlsBody = document.querySelector("#machine-controls-body");
const controlsToggle = document.querySelector("#controls-toggle");
const controlPanel = document.querySelector(".control-panel");
const mobileQuery = matchMedia("(max-width: 800px)");
const diagnostics = document.querySelector("#diagnostics");
const diagnosticsEnabled = query.get("diagnostics") === "1";

const state = { ...machine.stowState };
const runtime = { errors: 0, frames: 0, fps: "sampling", p95: "sampling", frameDurations: [], loadMs: "pending", selection: "pending" };
let model = null;
let rig = null;
let selected = null;
let lastFrame = performance.now();
let fpsStart = lastFrame;

function recordError(error) {
  runtime.errors += 1;
  document.body.dataset.runtimeErrorCount = String(runtime.errors);
  if (error) console.error(error);
  updateDiagnostics();
}
addEventListener("error", (event) => recordError(event.error));
addEventListener("unhandledrejection", (event) => recordError(event.reason));
document.body.dataset.runtimeErrorCount = "0";

function updateDiagnostics() {
  diagnostics.hidden = !diagnosticsEnabled;
  diagnostics.value = `machine ${machine.id} · config ${machine.configurationId} · source ${document.body.dataset.machineSource || "loading"} · selection ${runtime.selection} · errors ${runtime.errors} · load ${runtime.loadMs} · ${runtime.fps} · ${runtime.p95}`;
}

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
  loader.hidden = true;
  errorPanel.hidden = false;
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
const floor = new THREE.Mesh(new THREE.CircleGeometry(8, 80), new THREE.MeshStandardMaterial({ color: 0x242a29, roughness: 0.96 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);
const grid = new THREE.GridHelper(14, 28, 0x5d625c, 0x303633);
grid.position.y = 0.003;
grid.material.transparent = true;
grid.material.opacity = 0.12;
scene.add(grid);

const orbit = { azimuth: -0.72, polar: 1.18, distance: mobileQuery.matches ? 5.3 : 4.5, target: new THREE.Vector3(0, 1.05, 0), desiredTarget: new THREE.Vector3(0, 1.05, 0), desiredDistance: mobileQuery.matches ? 5.3 : 4.5 };
function updateCamera(delta = 1) {
  const ease = reducedMotion ? 1 : Math.min(1, delta * 7);
  orbit.target.lerp(orbit.desiredTarget, ease);
  orbit.distance = THREE.MathUtils.lerp(orbit.distance, orbit.desiredDistance, ease);
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
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: 0 });
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
  orbit.azimuth -= dx * 0.006;
  orbit.polar = THREE.MathUtils.clamp(orbit.polar + dy * 0.006, 0.25, 1.52);
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
  if (component) openInspector(component);
  updateDiagnostics();
}

function setControlOutputs() {
  const presentation = machine.presentState(state);
  for (const control of machine.controls) document.querySelector(`#${control.outputId}`).value = presentation.outputs[control.id];
  document.body.dataset.zone = presentation.zone;
  document.querySelector("#motion-status").value = presentation.status;
}
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
  document.querySelector(`#${control.inputId}`).addEventListener("input", (event) => {
    state[control.id] = Number(event.currentTarget.value) / control.inputDivisor;
    applyControls();
  });
}
document.querySelector("#stow").addEventListener("click", () => {
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
document.querySelectorAll("[data-focus]").forEach((button, index) => button.addEventListener("click", () => {
  document.querySelectorAll("[data-focus]").forEach((candidate) => candidate.setAttribute("aria-pressed", "false"));
  button.setAttribute("aria-pressed", "true");
  focusCamera(button.dataset.focus);
  openInspector(button.dataset.focus);
  selected = index;
}));

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

function setMobileControls(open) {
  const expanded = mobileQuery.matches ? open : true;
  controlsBody.hidden = !expanded;
  controlsBody.inert = !expanded;
  controlsToggle.hidden = !mobileQuery.matches;
  controlsToggle.setAttribute("aria-expanded", String(expanded));
  controlsToggle.textContent = expanded ? "Close" : "Adjust";
  document.body.classList.toggle("mobile-controls-open", mobileQuery.matches && expanded);
  requestAnimationFrame(syncMobileControlHeight);
  requestAnimationFrame(fitMachineBounds);
}
function syncMobileControlHeight() {
  if (!mobileQuery.matches) return document.documentElement.style.removeProperty("--mobile-controls-height");
  document.documentElement.style.setProperty("--mobile-controls-height", `${Math.ceil(controlPanel.getBoundingClientRect().height)}px`);
}
new ResizeObserver(syncMobileControlHeight).observe(controlPanel);
controlsToggle.addEventListener("click", () => setMobileControls(controlsToggle.getAttribute("aria-expanded") !== "true"));
mobileQuery.addEventListener?.("change", () => setMobileControls(false));
setMobileControls(query.get("controls") === "1");

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
  else if (/^[1-4]$/.test(event.key)) document.querySelectorAll("[data-focus]")[Number(event.key) - 1]?.click();
  else return;
  event.preventDefault();
});

const loadStarted = performance.now();
new GLTFLoader().load(machine.assetUrl, (gltf) => {
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
  scene.add(model);
  rig = machine.createRig(model);
  applyControls();
  const selfTest = machine.selfTestRig?.(rig, state) || { ok: true, failures: [] };
  if (!selfTest.ok) throw new Error(`Interaction motion self-test failed: ${selfTest.failures.join(", ")}`);
  runtime.loadMs = `${Math.round(performance.now() - loadStarted)} ms`;
  runtime.selection = "self-test-pass";
  document.body.dataset.machineSource = "glb";
  document.body.dataset.machineVisibleMeshes = String(model.getObjectsByProperty("isMesh", true).length);
  loaderStatus.textContent = `${machine.identity.model} ready`;
  loaderDetail.textContent = `${machine.configurationId} validated`;
  loader.classList.add("done");
  updateDiagnostics();
}, undefined, (error) => {
  recordError(error);
  loader.hidden = true;
  errorPanel.hidden = false;
  errorCopy.textContent = `The evidence-bound ${machine.identity.model} asset could not be loaded. No procedural substitute was used.`;
  document.body.dataset.machineSource = "load-failed";
});

function animate(now) {
  requestAnimationFrame(animate);
  const delta = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;
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
requestAnimationFrame(animate);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  fitMachineBounds();
});
setControlOutputs();
updateDiagnostics();
