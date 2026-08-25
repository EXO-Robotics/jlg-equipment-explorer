import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import ES1930M_MACHINE from "../machines/es1930m/machine.js";

const MACHINES = Object.freeze({ es1930m: ES1930M_MACHINE });
const machine = MACHINES[document.body.dataset.machine];
if (!machine) throw new Error(`Unknown equipment route: ${document.body.dataset.machine}`);

document.body.dataset.viewerStarted = "true";
document.body.dataset.configurationId = machine.configurationId;
const query = new URLSearchParams(location.search);
const reducedMotion = query.get("reduce") === "1" || matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const compact = matchMedia?.("(max-width: 800px)").matches;
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
const runtime = { errors: 0, frames: 0, fps: "sampling", loadMs: "pending", selection: "pending" };
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
  diagnostics.value = `machine ${machine.id} · config ${machine.configurationId} · source ${document.body.dataset.machineSource || "loading"} · selection ${runtime.selection} · errors ${runtime.errors} · load ${runtime.loadMs} · ${runtime.fps}`;
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
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, compact ? 1.35 : 1.75));
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
  light.shadow.mapSize.set(compact ? 1024 : 2048, compact ? 1024 : 2048);
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

const orbit = { azimuth: -0.72, polar: 1.18, distance: compact ? 5.3 : 4.5, target: new THREE.Vector3(0, 1.05, 0), desiredTarget: new THREE.Vector3(0, 1.05, 0), desiredDistance: compact ? 5.3 : 4.5 };
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

let pointer = null;
renderer.domElement.addEventListener("pointerdown", (event) => {
  pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, moved: 0 };
  renderer.domElement.setPointerCapture(event.pointerId);
});
renderer.domElement.addEventListener("pointermove", (event) => {
  if (!pointer || pointer.id !== event.pointerId) return;
  const dx = event.clientX - pointer.x;
  const dy = event.clientY - pointer.y;
  pointer.x = event.clientX;
  pointer.y = event.clientY;
  pointer.moved += Math.abs(dx) + Math.abs(dy);
  orbit.azimuth -= dx * 0.006;
  orbit.polar = THREE.MathUtils.clamp(orbit.polar + dy * 0.006, 0.25, 1.52);
});
renderer.domElement.addEventListener("pointerup", (event) => {
  if (pointer && pointer.moved < 8) selectAt(event.clientX, event.clientY);
  pointer = null;
});
renderer.domElement.addEventListener("wheel", (event) => {
  event.preventDefault();
  orbit.desiredDistance = THREE.MathUtils.clamp(orbit.desiredDistance * Math.exp(event.deltaY * 0.001), 1.6, 11);
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
  const hit = raycaster.intersectObject(model, true).find((candidate) => candidate.object.visible);
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
function applyControls() {
  if (rig) machine.applyState(rig, machine.solveState(state));
  setControlOutputs();
}
for (const control of machine.controls) {
  document.querySelector(`#${control.inputId}`).addEventListener("input", (event) => {
    state[control.id] = Number(event.currentTarget.value) / control.inputDivisor;
    const followedView = machine.followView?.(state, compact, control.id);
    if (followedView && control.id === "lift") {
      orbit.desiredTarget.set(...followedView.target);
      orbit.desiredDistance = followedView.distance;
    }
    applyControls();
  });
}
document.querySelector("#stow").addEventListener("click", () => {
  Object.assign(state, machine.stowState);
  for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
  applyControls();
});

function focusCamera(name) {
  const preset = machine.componentView(name, state, compact);
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
function openInspector(component) {
  const detail = machine.components[component];
  if (detail) {
    document.querySelector("#inspector-kicker").textContent = detail.eyebrow;
    document.querySelector("#inspector-title").textContent = detail.title;
    document.querySelector("#inspector-copy").textContent = detail.body;
  }
  document.body.classList.add("inspector-open");
  inspector.inert = false;
  infoToggle.setAttribute("aria-expanded", "true");
  requestAnimationFrame(() => document.querySelector("#inspector-close").focus());
}
function closeInspector() {
  document.body.classList.remove("inspector-open");
  inspector.inert = true;
  infoToggle.setAttribute("aria-expanded", "false");
  infoToggle.focus();
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
}
function syncMobileControlHeight() {
  if (!mobileQuery.matches) return document.documentElement.style.removeProperty("--mobile-controls-height");
  document.documentElement.style.setProperty("--mobile-controls-height", `${Math.ceil(controlPanel.getBoundingClientRect().height)}px`);
}
new ResizeObserver(syncMobileControlHeight).observe(controlPanel);
controlsToggle.addEventListener("click", () => setMobileControls(controlsToggle.getAttribute("aria-expanded") !== "true"));
mobileQuery.addEventListener?.("change", () => setMobileControls(false));
setMobileControls(query.get("controls") === "1");

app.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("inspector-open")) return closeInspector();
  if (event.key === "ArrowLeft") orbit.azimuth += 0.12;
  else if (event.key === "ArrowRight") orbit.azimuth -= 0.12;
  else if (event.key === "ArrowUp") orbit.polar = Math.max(0.25, orbit.polar - 0.08);
  else if (event.key === "ArrowDown") orbit.polar = Math.min(1.52, orbit.polar + 0.08);
  else if (event.key === "+" || event.key === "=") orbit.desiredDistance = Math.max(1.6, orbit.desiredDistance * 0.9);
  else if (event.key === "-" || event.key === "_") orbit.desiredDistance = Math.min(11, orbit.desiredDistance * 1.1);
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
      }
      node.castShadow = true;
      node.receiveShadow = true;
    }
  });
  scene.add(model);
  rig = machine.createRig(model);
  applyControls();
  runtime.loadMs = `${Math.round(performance.now() - loadStarted)} ms`;
  runtime.selection = "ready";
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
  if (now - fpsStart > 1500) {
    runtime.fps = `${Math.round(runtime.frames * 1000 / (now - fpsStart))} fps`;
    runtime.frames = 0;
    fpsStart = now;
    updateDiagnostics();
  }
}
requestAnimationFrame(animate);
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
setControlOutputs();
updateDiagnostics();
