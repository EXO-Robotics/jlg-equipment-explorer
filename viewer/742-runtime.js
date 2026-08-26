import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import JLG742_MACHINE from "../machines/742/machine.js?v=1.1.3";

const ROUTE_RELEASE = "1.5.0";
const machine = JLG742_MACHINE;
if (document.body.dataset.machine !== machine.id) throw new Error(`Equipment route identity mismatch: ${document.body.dataset.machine}`);
if (document.body.dataset.runtimeRelease !== ROUTE_RELEASE) throw new Error(`742 runtime cache identity mismatch: expected ${ROUTE_RELEASE}`);

document.body.dataset.viewerStarted = "true";
document.body.dataset.configurationId = machine.configurationId;
const query = new URLSearchParams(location.search);
const reducedMotion = query.get("reduce") === "1" || matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const mobileQuery = matchMedia("(max-width: 800px), (max-height: 500px) and (max-width: 1000px)");
let compact = mobileQuery.matches;
const app = document.querySelector("#app");
const loader = document.querySelector("#loader");
const loaderStatus = document.querySelector("#loader-status");
const loaderDetail = document.querySelector("#loader-detail");
const errorPanel = document.querySelector("#error");
const errorCopy = document.querySelector("#error-copy");
const controlsBody = document.querySelector("#machine-controls-body");
const controlsToggle = document.querySelector("#controls-toggle");
const controlPanel = document.querySelector(".control-panel");
const diagnostics = document.querySelector("#diagnostics");
const diagnosticsEnabled = query.get("diagnostics") === "1";

const state = { ...machine.stowState };
const runtime = { errors: 0, frames: 0, fps: "sampling", frameP95Ms: "sampling", loadMs: "pending", selection: "pending" };
let model = null;
let rig = null;
let selected = null;
let selectionVolumes = [];
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
  diagnostics.value = `machine ${machine.id} · config ${machine.configurationId} · source ${document.body.dataset.machineSource || "loading"} · selection ${runtime.selection} · errors ${runtime.errors} · load ${runtime.loadMs} · ${runtime.fps} · p95 ${runtime.frameP95Ms}`;
}

function pixelRatio() {
  const shortLandscape = innerHeight <= 500 && innerWidth > innerHeight;
  return Math.min(devicePixelRatio || 1, shortLandscape ? 1.2 : compact ? 1.35 : 1.75);
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
renderer.setPixelRatio(pixelRatio());
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
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.04, 100);
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

function adaptView(view, name = "default") {
  const portrait = compact && innerHeight > innerWidth;
  const shortLandscape = compact && innerWidth > innerHeight && innerHeight <= 500;
  const scale = portrait ? (name === "default" ? 2.10 : name === "follow" ? 1.24 : 1.14) : shortLandscape ? 1.24 : 1;
  return { ...view, distance: view.distance * scale };
}
const defaultView = adaptView(machine.componentView("default", state, compact), "default");
const distanceLimits = machine.orbitLimits || { minDistance: 1.6, maxDistance: 11 };
const orbit = {
  azimuth: defaultView.azimuth ?? -0.72,
  polar: defaultView.polar ?? 1.18,
  distance: defaultView.distance,
  target: new THREE.Vector3(...defaultView.target),
  desiredTarget: new THREE.Vector3(...defaultView.target),
  desiredDistance: defaultView.distance,
  velocityAzimuth: 0,
  velocityPolar: 0,
};
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
  scene.fog.near = Math.max(14, orbit.distance * 0.88);
  scene.fog.far = Math.max(30, orbit.distance * 2.2);
}
updateCamera();

renderer.domElement.addEventListener("wheel", (event) => {
  event.preventDefault();
  orbit.desiredDistance = THREE.MathUtils.clamp(orbit.desiredDistance * Math.exp(event.deltaY * 0.001), distanceLimits.minDistance, distanceLimits.maxDistance);
}, { passive: false });

const pointers = new Map();
let pinchStartDistance = 0;
let pinchStartOrbitDistance = orbit.desiredDistance;
let gestureUsedPinch = false;
renderer.domElement.addEventListener("contextmenu", (event) => event.preventDefault());
renderer.domElement.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 && event.pointerType !== "touch") return;
  event.preventDefault();
  app.focus({ preventScroll: true });
  pointers.set(event.pointerId, {
    x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: 0,
  });
  try { renderer.domElement.setPointerCapture(event.pointerId); } catch {}
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    gestureUsedPinch = true;
    pinchStartDistance = Math.hypot(a.x - b.x, a.y - b.y) || 1;
    pinchStartOrbitDistance = orbit.desiredDistance;
  }
}, { passive: false });
renderer.domElement.addEventListener("pointermove", (event) => {
  const active = pointers.get(event.pointerId);
  if (!active) return;
  event.preventDefault();
  const previousX = active.x;
  const previousY = active.y;
  active.x = event.clientX;
  active.y = event.clientY;
  active.moved = Math.max(active.moved, Math.hypot(active.x - active.startX, active.y - active.startY));
  if (pointers.size >= 2) {
    const [a, b] = [...pointers.values()];
    const distance = Math.hypot(a.x - b.x, a.y - b.y) || 1;
    orbit.desiredDistance = THREE.MathUtils.clamp(pinchStartOrbitDistance * pinchStartDistance / distance, distanceLimits.minDistance, distanceLimits.maxDistance);
    return;
  }
  const dx = active.x - previousX;
  const dy = active.y - previousY;
  orbit.velocityAzimuth = -dx * 0.006;
  orbit.velocityPolar = dy * 0.006;
  orbit.azimuth += orbit.velocityAzimuth;
  orbit.polar = THREE.MathUtils.clamp(orbit.polar + orbit.velocityPolar, 0.25, 1.52);
}, { passive: false });
function endPointer(event, cancelled = false) {
  const active = pointers.get(event.pointerId);
  const wasOnlyPointer = pointers.size === 1;
  pointers.delete(event.pointerId);
  try { renderer.domElement.releasePointerCapture(event.pointerId); } catch {}
  const wasClick = !cancelled && active && wasOnlyPointer && !gestureUsedPinch && active.moved < 8;
  if (pointers.size < 2) {
    pinchStartDistance = 0;
    if (!pointers.size) gestureUsedPinch = false;
  }
  if (wasClick) selectAt(event.clientX, event.clientY);
}
renderer.domElement.addEventListener("pointerup", (event) => endPointer(event));
renderer.domElement.addEventListener("pointercancel", (event) => endPointer(event, true));

const raycaster = new THREE.Raycaster();
const pointerNdc = new THREE.Vector2();
const selectionPriority = new Map(["chassis", "steering", "boom", "hydraulics", "cab", "carriage"].map((component, index) => [component, index]));
function prepareInteractionVolumes(root) {
  if (new Set(machine.interactionVolumes).size !== machine.interactionVolumes.length) throw new Error("Duplicate semantic selection-volume name");
  const volumes = machine.interactionVolumes.map((name) => {
    const matches = [];
    root.traverse((node) => { if (node.name === name) matches.push(node); });
    if (matches.length !== 1) throw new Error(`${name} must resolve to exactly one semantic selection volume`);
    const hit = matches[0];
    const component = hit.userData?.component;
    if (!hit.isMesh || hit.userData?.is_hit_volume !== true || !machine.components[component] || !selectionPriority.has(component)) {
      throw new Error(`${name} has an invalid semantic selection contract`);
    }
    hit.material = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false, colorWrite: false });
    hit.castShadow = false;
    hit.receiveShadow = false;
    hit.userData.selectionPriority = selectionPriority.get(component);
    return hit;
  });
  const priorities = volumes.map((hit) => hit.userData.selectionPriority);
  if (new Set(priorities).size !== priorities.length) throw new Error("Semantic selection priorities must be unique");
  return volumes;
}
function runSelectionVolumeSelfTest() {
  if (!model || selectionVolumes.length !== machine.interactionVolumes.length) return false;
  model.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const probe = new THREE.Raycaster();
  const center = new THREE.Vector3();
  const passed = selectionVolumes.filter((hit) => {
    new THREE.Box3().setFromObject(hit).getCenter(center);
    const projected = center.clone().project(camera);
    probe.setFromCamera(new THREE.Vector2(projected.x, projected.y), camera);
    return probe.intersectObject(hit, false)[0]?.object === hit && Number.isInteger(hit.userData.selectionPriority);
  }).length;
  document.body.dataset.selectionSelftest = passed === selectionVolumes.length ? "pass" : "fail";
  document.body.dataset.selectionVolumeCount = String(selectionVolumes.length);
  return passed === selectionVolumes.length;
}
function selectAt(clientX, clientY) {
  if (!model || !selectionVolumes.length) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointerNdc.set((clientX - rect.left) / rect.width * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointerNdc, camera);
  const hit = raycaster.intersectObjects(selectionVolumes, false)
    .sort((a, b) => (b.object.userData.selectionPriority - a.object.userData.selectionPriority) || a.distance - b.distance)[0];
  const component = hit?.object.userData.component || null;
  runtime.selection = component || "miss";
  if (component) {
    document.body.dataset.lastSelectionVolume = hit.object.name;
    openInspector(component);
  }
  updateDiagnostics();
}

function setControlOutputs() {
  const presentation = machine.presentState(state);
  for (const control of machine.controls) {
    const value = presentation.outputs[control.id];
    document.querySelector(`#${control.outputId}`).value = value;
    document.querySelector(`#${control.inputId}`).setAttribute("aria-valuetext", value);
  }
  document.body.dataset.zone = presentation.zone;
  document.querySelector("#motion-status").value = presentation.status;
}
function applyControls() {
  if (rig) machine.applyState(rig, machine.solveState(state));
  setControlOutputs();
}
const posedBounds = new THREE.Box3();
const meshBounds = new THREE.Box3();
const posedCenter = new THREE.Vector3();
const posedSize = new THREE.Vector3();
const corner = new THREE.Vector3();
const relativeCorner = new THREE.Vector3();
const viewDirection = new THREE.Vector3();
const viewRight = new THREE.Vector3();
const viewUp = new THREE.Vector3();
function semanticComponentFor(node) {
  let current = node;
  while (current && current !== model) {
    if (current.userData?.component) return current.userData.component;
    current = current.parent;
  }
  return null;
}
function framedPosedModelView(component = null) {
  if (!model) return null;
  model.updateWorldMatrix(true, true);
  posedBounds.makeEmpty();
  model.traverse((node) => {
    if (!node.isMesh || node.userData?.is_hit_volume || !node.visible || (component && semanticComponentFor(node) !== component)) return;
    node.geometry.computeBoundingBox();
    meshBounds.copy(node.geometry.boundingBox).applyMatrix4(node.matrixWorld);
    posedBounds.union(meshBounds);
  });
  if (posedBounds.isEmpty()) return null;
  posedBounds.getCenter(posedCenter);
  posedBounds.getSize(posedSize);
  const sinPolar = Math.sin(orbit.polar);
  viewDirection.set(sinPolar * Math.cos(orbit.azimuth), Math.cos(orbit.polar), sinPolar * Math.sin(orbit.azimuth)).normalize();
  viewRight.crossVectors(new THREE.Vector3(0, 1, 0), viewDirection).normalize();
  viewUp.crossVectors(viewDirection, viewRight).normalize();
  const tanHalfY = Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5));
  const tanHalfX = tanHalfY * camera.aspect;
  let requiredDistance = distanceLimits.minDistance;
  for (const x of [posedBounds.min.x, posedBounds.max.x]) for (const y of [posedBounds.min.y, posedBounds.max.y]) for (const z of [posedBounds.min.z, posedBounds.max.z]) {
    corner.set(x, y, z);
    relativeCorner.copy(corner).sub(posedCenter);
    const towardCamera = relativeCorner.dot(viewDirection);
    requiredDistance = Math.max(
      requiredDistance,
      towardCamera + Math.abs(relativeCorner.dot(viewRight)) / tanHalfX,
      towardCamera + Math.abs(relativeCorner.dot(viewUp)) / tanHalfY,
    );
  }
  const tallPose = posedSize.y > 6;
  const widePose = posedSize.x > 9;
  const margin = component
    ? (compact ? 1.12 : 1.10)
    : tallPose
      ? (compact ? 1.48 : 1.35)
      : widePose
        ? (compact ? 1.42 : 1.85)
      : compact && innerHeight > innerWidth
        ? 1.14
        : compact
          ? 1.15
          : 1.10;
  if (!component) {
    document.body.dataset.poseBoundsM = posedSize.toArray().map((value) => value.toFixed(2)).join("x");
    document.body.dataset.poseFrameDistanceM = (requiredDistance * margin).toFixed(2);
  }
  if (widePose && !compact) {
    posedCenter.addScaledVector(viewRight, -posedSize.x * 0.14);
  }
  return { target: posedCenter.toArray(), distance: requiredDistance * margin };
}
function updateFollowView(controlId) {
  const framed = framedPosedModelView();
  const fallback = adaptView(machine.followView(state, compact, controlId), "follow");
  const view = framed || fallback;
  orbit.desiredTarget.set(...view.target);
  orbit.desiredDistance = view.distance;
  activeViewName = "follow";
}
for (const control of machine.controls) {
  document.querySelector(`#${control.inputId}`).addEventListener("input", (event) => {
    state[control.id] = Number(event.currentTarget.value) / control.inputDivisor;
    applyControls();
    if (machine.followView && (control.id === "lift" || control.id === "telescope")) updateFollowView(control.id);
  });
}
document.querySelector("#stow").addEventListener("click", () => {
  showcaseStarted = null;
  Object.assign(state, machine.stowState);
  for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
  document.querySelectorAll("[data-steer-mode]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.steerMode === state.steerMode)));
  applyControls();
});

document.querySelectorAll("[data-steer-mode]").forEach((button) => button.addEventListener("click", () => {
  state.steerMode = button.dataset.steerMode;
  document.querySelectorAll("[data-steer-mode]").forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
  applyControls();
}));

let showcaseStarted = null;
let lastShowcaseFrameAt = 0;
document.querySelector("#showcase")?.addEventListener("click", () => { showcaseStarted = performance.now(); });

let activeViewName = "default";
function focusCamera(name) {
  const preset = adaptView(machine.componentView(name, state, compact), name);
  orbit.azimuth = preset.azimuth;
  orbit.polar = preset.polar;
  const posedComponent = name === "default" ? null : framedPosedModelView(name);
  orbit.desiredTarget.set(...(posedComponent || preset).target);
  orbit.desiredDistance = (posedComponent || preset).distance;
  activeViewName = name;
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
const inspectorClose = document.querySelector("#inspector-close");
const modalBackground = [app, document.querySelector(".interface")];
let focusBeforeInspector = null;
function setInert(element, inert) {
  if (inert) element.setAttribute("inert", "");
  else element.removeAttribute("inert");
}
function writeInspectorFacts(facts) {
  const list = document.querySelector("#inspector-facts");
  list.replaceChildren(...(facts || []).map(([label, value]) => {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = label;
    detail.textContent = value;
    row.append(term, detail);
    return row;
  }));
}
function openInspector(component) {
  const detail = machine.components[component];
  if (detail) {
    document.querySelector("#inspector-kicker").textContent = detail.eyebrow;
    document.querySelector("#inspector-title").textContent = detail.title;
    document.querySelector("#inspector-copy").textContent = detail.body;
    writeInspectorFacts(detail.facts);
  }
  if (!document.body.classList.contains("inspector-open")) focusBeforeInspector = document.activeElement;
  document.body.classList.add("inspector-open");
  modalBackground.forEach((element) => setInert(element, true));
  setInert(inspector, false);
  infoToggle.setAttribute("aria-expanded", "true");
  requestAnimationFrame(() => inspectorClose.focus({ preventScroll: true }));
}
function closeInspector() {
  if (!document.body.classList.contains("inspector-open")) return;
  document.body.classList.remove("inspector-open");
  setInert(inspector, true);
  modalBackground.forEach((element) => setInert(element, false));
  infoToggle.setAttribute("aria-expanded", "false");
  const restoreTarget = focusBeforeInspector;
  focusBeforeInspector = null;
  if (restoreTarget instanceof HTMLElement && restoreTarget.isConnected) restoreTarget.focus({ preventScroll: true });
}
infoToggle.addEventListener("click", () => openInspector("about"));
inspectorClose.addEventListener("click", closeInspector);
document.querySelector("#scrim").addEventListener("click", closeInspector);
document.addEventListener("keydown", (event) => {
  if (!document.body.classList.contains("inspector-open")) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeInspector();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = [...inspector.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex='-1'])")]
    .filter((element) => element.getClientRects().length);
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && (document.activeElement === first || !inspector.contains(document.activeElement))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (document.activeElement === last || !inspector.contains(document.activeElement))) {
    event.preventDefault();
    first.focus();
  }
});

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
mobileQuery.addEventListener?.("change", () => {
  compact = mobileQuery.matches;
  setMobileControls(false);
});
setMobileControls(query.get("controls") === "1");

const componentNav = document.querySelector(".component-nav");
const navOverflowCue = document.querySelector("#nav-overflow-cue");
function updateNavOverflowCue() {
  const canScroll = componentNav.scrollWidth > componentNav.clientWidth + 2;
  const hasMore = componentNav.scrollLeft + componentNav.clientWidth < componentNav.scrollWidth - 2;
  navOverflowCue.hidden = !compact || !canScroll || !hasMore;
  componentNav.dataset.overflow = canScroll ? hasMore ? "more" : "end" : "none";
}
componentNav.addEventListener("scroll", updateNavOverflowCue, { passive: true });
new ResizeObserver(updateNavOverflowCue).observe(componentNav);
requestAnimationFrame(updateNavOverflowCue);

app.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") orbit.azimuth += 0.12;
  else if (event.key === "ArrowRight") orbit.azimuth -= 0.12;
  else if (event.key === "ArrowUp") orbit.polar = Math.max(0.25, orbit.polar - 0.08);
  else if (event.key === "ArrowDown") orbit.polar = Math.min(1.52, orbit.polar + 0.08);
  else if (event.key === "+" || event.key === "=") orbit.desiredDistance = Math.max(distanceLimits.minDistance, orbit.desiredDistance * 0.9);
  else if (event.key === "-" || event.key === "_") orbit.desiredDistance = Math.min(distanceLimits.maxDistance, orbit.desiredDistance * 1.1);
  else if (event.key === "0") focusCamera("default");
  else if (/^[1-7]$/.test(event.key)) document.querySelectorAll("[data-focus]")[Number(event.key) - 1]?.click();
  else return;
  event.preventDefault();
});

const loadStarted = performance.now();
new GLTFLoader().load(machine.assetUrl, (gltf) => {
  try {
    const validation = machine.validateAsset(gltf.scene);
    if (!validation.ok) throw new Error(`${machine.identity.model} asset validation failed: ${validation.missing.join(", ")}`);
    const candidateModel = gltf.scene;
    const candidateVolumes = prepareInteractionVolumes(candidateModel);
    let visibleMeshes = 0;
    candidateModel.traverse((node) => {
      if (!node.isMesh || node.userData?.is_hit_volume) return;
      node.castShadow = true;
      node.receiveShadow = true;
      visibleMeshes += 1;
    });
    const candidateRig = machine.createRig(candidateModel);
    machine.applyState(candidateRig, machine.solveState(state));
    model = candidateModel;
    rig = candidateRig;
    selectionVolumes = candidateVolumes;
    scene.add(model);
    applyControls();
    if (!runSelectionVolumeSelfTest()) throw new Error(`${machine.identity.model} semantic selection self-test failed`);
    runtime.loadMs = `${Math.round(performance.now() - loadStarted)} ms`;
    runtime.selection = `${selectionVolumes.length}/${selectionVolumes.length} ready`;
    document.body.dataset.machineSource = "glb-validated";
    document.body.dataset.machineVisibleMeshes = String(visibleMeshes);
    loaderStatus.textContent = `${machine.identity.model} ready`;
    loaderDetail.textContent = `${machine.configurationId} validated`;
    loader.classList.add("done");
    updateDiagnostics();
  } catch (error) {
    if (model) scene.remove(model);
    model = null;
    rig = null;
    selectionVolumes = [];
    recordError(error);
    controlsBody.inert = true;
    controlPanel.setAttribute("aria-disabled", "true");
    loader.hidden = true;
    errorPanel.hidden = false;
    errorPanel.setAttribute("role", "alert");
    errorCopy.textContent = `The ${machine.identity.model} asset failed its hierarchy or semantic-selection contract. No substitute was shown.`;
    document.body.dataset.machineSource = "contract-failed";
  }
}, undefined, (error) => {
  recordError(error);
  controlsBody.inert = true;
  controlPanel.setAttribute("aria-disabled", "true");
  loader.hidden = true;
  errorPanel.hidden = false;
  errorPanel.setAttribute("role", "alert");
  errorCopy.textContent = `The evidence-bound ${machine.identity.model} asset could not be loaded. No procedural substitute was used.`;
  document.body.dataset.machineSource = "load-failed";
});

function animate(now) {
  requestAnimationFrame(animate);
  if (document.hidden) {
    lastFrame = now;
    fpsStart = now;
    return;
  }
  const renderedInterval = now - lastFrame;
  const delta = Math.min(renderedInterval / 1000, 0.05);
  if (renderedInterval >= 4 && renderedInterval < 250) {
    frameTimes.push(renderedInterval);
    if (frameTimes.length > 180) frameTimes.shift();
  }
  lastFrame = now;
  if (!pointers.size && !reducedMotion) {
    orbit.azimuth += orbit.velocityAzimuth;
    orbit.polar = THREE.MathUtils.clamp(orbit.polar + orbit.velocityPolar, 0.25, 1.52);
    orbit.velocityAzimuth *= 0.88;
    orbit.velocityPolar *= 0.88;
  }
  if (showcaseStarted !== null && machine.showcase) {
    const elapsed = (now - showcaseStarted) / (machine.showcaseDurationMs ?? 14000);
    if (elapsed >= 1) showcaseStarted = now;
    Object.assign(state, machine.showcase(elapsed % 1));
    for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
    document.querySelectorAll("[data-steer-mode]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.steerMode === state.steerMode)));
    applyControls();
    if (machine.followView && now - lastShowcaseFrameAt > 100) {
      updateFollowView("showcase");
      lastShowcaseFrameAt = now;
    }
  }
  updateCamera(delta);
  renderer.render(scene, camera);
  runtime.frames += 1;
  if (now - fpsStart > 1500) {
    runtime.fps = `${Math.round(runtime.frames * 1000 / (now - fpsStart))} fps`;
    if (frameTimes.length) {
      const sorted = [...frameTimes].sort((a, b) => a - b);
      runtime.frameP95Ms = `${sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))].toFixed(1)} ms`;
      document.body.dataset.frameP95Ms = runtime.frameP95Ms;
    }
    runtime.frames = 0;
    fpsStart = now;
    updateDiagnostics();
  }
}
const frameTimes = [];
requestAnimationFrame(animate);
addEventListener("resize", () => {
  compact = mobileQuery.matches;
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(innerWidth, innerHeight);
  if (activeViewName === "follow") {
    updateFollowView("resize");
  } else {
    focusCamera(activeViewName);
  }
  syncMobileControlHeight();
});
document.addEventListener("visibilitychange", () => {
  frameTimes.length = 0;
  runtime.frames = 0;
  lastFrame = performance.now();
  fpsStart = lastFrame;
  runtime.frameP95Ms = "sampling";
  updateDiagnostics();
});
setControlOutputs();
updateDiagnostics();
