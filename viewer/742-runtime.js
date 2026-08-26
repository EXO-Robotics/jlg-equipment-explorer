import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import JLG742_MACHINE from "../machines/742/machine.js?v=1.1.12";
import { telehandlerDragDelta } from "./pointer-gestures.mjs?v=1.0.10";
import { advanceFigureEight, JLG742_FIGURE_EIGHT, sampleFigureEight } from "./presentation-route.mjs?v=1.0.10";

const ROUTE_RELEASE = "1.7.2";
const DEFAULT_ASSET_LOAD_TIMEOUT_MS = 15000;
const TEST_FAULTS = new Set(["bootstrap-timeout", "asset-timeout", "loader-start", "runtime-error", "unhandled-rejection"]);
const machine = JLG742_MACHINE;
const query = new URLSearchParams(location.search);
const loopbackTestHost = ["127.0.0.1", "localhost", "::1"].includes(location.hostname);
const requestedTestFault = query.get("ee-test-fault");
const testFault = loopbackTestHost && TEST_FAULTS.has(requestedTestFault) ? requestedTestFault : null;
const assetLoadTimeoutMs = testFault === "asset-timeout" ? 120 : DEFAULT_ASSET_LOAD_TIMEOUT_MS;
if (testFault === "bootstrap-timeout") await new Promise(() => {});
const forceReducedMotion = query.get("reduce") === "1";
const motionPreference = matchMedia("(prefers-reduced-motion: reduce)");
let reducedMotion = forceReducedMotion || motionPreference.matches;
const COMPACT_VIEWPORT_QUERY = "(max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)";
const mobileQuery = matchMedia(COMPACT_VIEWPORT_QUERY);
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
const motionStatus = document.querySelector("#motion-status");
const motionAnnouncement = document.querySelector("#motion-announcement");
const autonomyMode = document.querySelector("#autonomy-mode");
const autonomyNote = document.querySelector("#autonomy-note");
const showcasePhase = document.querySelector("#showcase-phase");
const showcaseLoop = document.querySelector("#showcase-loop");
const showcaseButton = document.querySelector("#showcase");

const state = { ...machine.stowState };
const runtime = { errors: 0, fps: "sampling", frameP95Ms: "sampling", frameWorstMs: "sampling", visibleStalls: 0, loadMs: "pending", selection: "pending" };
const frameTimes = [];
let model = null;
let rig = null;
let selected = null;
let selectionVolumes = [];
let lastFrame = performance.now();
let fpsStart = lastFrame;
let showcaseStarted = null;
let terminalFailure = false;
let motionAnnouncementTimer = null;
let skipNextVisibleFrame = true;
let animationFrameId = null;
let runtimeFrameCount = 0;
const showcaseRoute = {
  phase: 0,
  distanceM: 0,
  wheelRotations: Object.fromEntries(["FL", "FR", "RL", "RR"].map((corner) => [corner, 0])),
};
const routeWheelCorners = Object.freeze(["FR", "FL", "RR", "RL"]);

function recordError(error) {
  runtime.errors += 1;
  document.body.dataset.runtimeErrorCount = String(runtime.errors);
  if (error) console.error(error);
  updateDiagnostics();
}
function showTerminalError(error, message, source = "runtime-failed") {
  if (terminalFailure) return;
  terminalFailure = true;
  showcaseStarted = null;
  document.body.dataset.showcaseActive = "false";
  clearTimeout(motionAnnouncementTimer);
  if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
  animationFrameId = null;
  document.body.dataset.machineSource = source;
  document.body.dataset.viewerRuntimeActive = "false";
  const useRuntimeFrameCount = runtimeFrameCount >= 2;
  const terminalFrameCount = useRuntimeFrameCount ? runtimeFrameCount : Number(document.body.dataset.bootFrameCount || 0);
  document.body.dataset.terminalFrameCount = String(terminalFrameCount);
  document.body.dataset.terminalFrameSource = useRuntimeFrameCount ? "runtime" : "boot";
  recordError(error);
  document.body.classList.remove("inspector-open", "mobile-controls-open");
  document.body.classList.add("viewer-terminal-error");
  document.body.dataset.viewerTerminal = "true";
  loader.hidden = true;
  errorPanel.hidden = false;
  errorCopy.textContent = message;
  app.setAttribute("inert", "");
  document.querySelector(".interface")?.setAttribute("inert", "");
  document.querySelector("#inspector")?.setAttribute("inert", "");
  controlsBody.inert = true;
  controlPanel.setAttribute("aria-disabled", "true");
  controlPanel.querySelectorAll("button, input").forEach((control) => { control.disabled = true; });
  errorPanel.setAttribute("tabindex", "-1");
  errorPanel.focus({ preventScroll: true });
}
addEventListener("error", (event) => showTerminalError(event.error, "The 742 viewer stopped after an unexpected runtime error. No substitute was shown.", "unexpected-runtime-error"));
addEventListener("unhandledrejection", (event) => showTerminalError(event.reason, "The 742 viewer stopped after an unexpected runtime error. No substitute was shown.", "unhandled-rejection"));
document.body.dataset.runtimeErrorCount = "0";
document.body.dataset.viewerStarted = "true";
document.body.dataset.viewerRuntimeActive = "true";
document.body.dataset.configurationId = machine.configurationId;
document.body.dataset.testFault = testFault || "none";
document.body.dataset.showcaseActive = "false";
let testFaultTriggered = false;
if (testFault === "runtime-error" || testFault === "unhandled-rejection") {
  globalThis.__EQUIPMENT_EXPLORER_TEST_HOOK__ = Object.freeze({
    fault: testFault,
    trigger() {
      if (terminalFailure || testFaultTriggered) return false;
      testFaultTriggered = true;
      document.body.dataset.testFaultTriggered = "true";
      if (testFault === "runtime-error") {
        setTimeout(() => { throw new Error("Injected 742 unexpected runtime error"); }, 0);
      } else {
        setTimeout(() => { Promise.reject(new Error("Injected 742 unhandled rejection")); }, 0);
      }
      return true;
    },
  });
}

try {
  if (document.body.dataset.machine !== machine.id) throw new Error(`Equipment route identity mismatch: ${document.body.dataset.machine}`);
  if (document.body.dataset.runtimeRelease !== ROUTE_RELEASE) throw new Error(`742 runtime cache identity mismatch: expected ${ROUTE_RELEASE}`);
} catch (error) {
  showTerminalError(error, "The 742 route and its dedicated runtime do not share the same cache identity. Reload the page to request one coherent release.", "identity-failed");
}

function updateDiagnostics() {
  diagnostics.hidden = !diagnosticsEnabled;
  diagnostics.value = `machine ${machine.id} · config ${machine.configurationId} · source ${document.body.dataset.machineSource || "loading"} · selection ${runtime.selection} · errors ${runtime.errors} · load ${runtime.loadMs} · ${runtime.fps} · samples ${frameTimes?.length ?? 0} · p95 ${runtime.frameP95Ms} · worst ${runtime.frameWorstMs} · visible stalls ${runtime.visibleStalls} · profile ${document.body.dataset.renderProfile || "pending"} · motion ${reducedMotion ? "reduced" : "full"}`;
}
function resetPerformanceWindow(reason, now = performance.now()) {
  frameTimes.length = 0;
  runtime.fps = "sampling";
  runtime.frameP95Ms = "sampling";
  runtime.frameWorstMs = "sampling";
  runtime.visibleStalls = 0;
  lastFrame = now;
  fpsStart = now;
  skipNextVisibleFrame = true;
  document.body.dataset.frameP95Ms = "sampling";
  document.body.dataset.frameWorstMs = "sampling";
  document.body.dataset.visibleStallCount = "0";
  document.body.dataset.frameSampleCount = "0";
  document.body.dataset.performanceWindowMs = "0";
  document.body.dataset.performanceWindowReason = reason;
  updateDiagnostics();
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
  showTerminalError(new Error("WebGL unavailable"), "This interactive study needs WebGL and a valid owned 742 asset.", "webgl-failed");
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
document.body.dataset.motionProfile = reducedMotion ? "reduced" : "full";

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111719);
scene.fog = new THREE.Fog(0x111719, 14, 28);
const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.04, 100);
scene.add(new THREE.HemisphereLight(0xdce9f1, 0x262a25, 2.0));
let shadowLight = null;
for (const [color, intensity, position] of [[0xffefd4, 4.0, [-5, 9, 7]], [0x9fc9e2, 2.0, [5, 4, 6]], [0xff8b43, 1.5, [5, 4, -5]]]) {
  const light = new THREE.DirectionalLight(color, intensity);
  light.position.set(...position);
  light.castShadow = intensity > 3;
  if (light.castShadow) shadowLight = light;
  scene.add(light);
}
function applyShadowProfile() {
  if (!shadowLight) return;
  const shortLandscape = innerHeight <= 500 && innerWidth > innerHeight;
  const size = shortLandscape || compact ? 512 : 1024;
  const coverage = 20;
  if (shadowLight.shadow.mapSize.x !== size) {
    shadowLight.shadow.mapSize.set(size, size);
    shadowLight.shadow.map?.dispose();
    shadowLight.shadow.map = null;
  }
  Object.assign(shadowLight.shadow.camera, { left: -coverage, right: coverage, top: coverage, bottom: -coverage, near: 0.5, far: 36 });
  shadowLight.shadow.camera.updateProjectionMatrix();
  shadowLight.shadow.bias = -0.00025;
  shadowLight.shadow.normalBias = 0.025;
  document.body.dataset.shadowProfile = `${size}px-${coverage}m`;
  document.body.dataset.renderProfile = shortLandscape ? "short-landscape" : compact && innerHeight > innerWidth ? "portrait" : compact ? "compact" : "desktop";
  document.body.dataset.viewportCssPx = `${innerWidth}x${innerHeight}`;
  document.body.dataset.pixelRatio = renderer.getPixelRatio().toFixed(2);
}
applyShadowProfile();
const floor = new THREE.Mesh(new THREE.CircleGeometry(18, 96), new THREE.MeshStandardMaterial({ color: 0x242a2a, roughness: 0.96, metalness: 0 }));
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);
const grid = new THREE.GridHelper(34, 34, 0x5c5f56, 0x30342f);
grid.position.y = 0.004;
grid.material.transparent = true;
grid.material.opacity = 0.12;
scene.add(grid);

function adaptView(view, name = "default") {
  const portrait = compact && innerHeight > innerWidth;
  const shortLandscape = compact && innerWidth > innerHeight && innerHeight <= 500;
  const scale = portrait ? (name === "default" ? 2.75 : name === "follow" ? 1.24 : 1.14) : shortLandscape ? 1.24 : 1;
  return { ...view, distance: view.distance * scale };
}
const defaultView = adaptView(machine.componentView("default", state, compact), "default");
const distanceLimits = machine.orbitLimits || { minDistance: 1.6, maxDistance: 11 };
const interactionMinDistance = Math.max(distanceLimits.minDistance, 4.4);
const absoluteMaxDistance = 72;
let effectiveMaxDistance = Math.min(absoluteMaxDistance, Math.max(distanceLimits.maxDistance, defaultView.distance * 1.05));
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
function setProgrammaticViewDistance(distance) {
  const safeDistance = THREE.MathUtils.clamp(distance, interactionMinDistance, absoluteMaxDistance / 1.05);
  effectiveMaxDistance = Math.min(absoluteMaxDistance, Math.max(distanceLimits.maxDistance, safeDistance * 1.05));
  orbit.desiredDistance = safeDistance;
  document.body.dataset.orbitBaseMaxDistanceM = distanceLimits.maxDistance.toFixed(2);
  document.body.dataset.orbitMinDistanceM = interactionMinDistance.toFixed(2);
  document.body.dataset.orbitEffectiveMaxDistanceM = effectiveMaxDistance.toFixed(2);
  document.body.dataset.orbitDesiredDistanceM = orbit.desiredDistance.toFixed(2);
}
setProgrammaticViewDistance(defaultView.distance);
function updateCamera(delta = 1) {
  const ease = reducedMotion ? 1 : Math.min(1, delta * 7);
  orbit.target.lerp(orbit.desiredTarget, ease);
  orbit.distance = THREE.MathUtils.lerp(orbit.distance, orbit.desiredDistance, ease);
  document.body.dataset.orbitCameraDistanceM = orbit.distance.toFixed(3);
  document.body.dataset.orbitAzimuthRad = orbit.azimuth.toFixed(6);
  document.body.dataset.orbitPolarRad = orbit.polar.toFixed(6);
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
  orbit.desiredDistance = THREE.MathUtils.clamp(orbit.desiredDistance * Math.exp(event.deltaY * 0.001), interactionMinDistance, effectiveMaxDistance);
  document.body.dataset.orbitDesiredDistanceM = orbit.desiredDistance.toFixed(2);
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
    pointerType: event.pointerType || "mouse",
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
    orbit.desiredDistance = THREE.MathUtils.clamp(pinchStartOrbitDistance * pinchStartDistance / distance, interactionMinDistance, effectiveMaxDistance);
    document.body.dataset.orbitDesiredDistanceM = orbit.desiredDistance.toFixed(2);
    return;
  }
  const dx = active.x - previousX;
  const dy = active.y - previousY;
  const drag = telehandlerDragDelta(dx, dy, active.pointerType);
  orbit.velocityAzimuth = drag.azimuth;
  orbit.velocityPolar = drag.polar;
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
const SELECTION_TIE_DISTANCE_M = 0.025;
// The 25 mm tie band is smaller than a visible modeled part at this scale; it
// only resolves coincident proxy skins and never lets a rear proxy beat a
// frontmost rendered component.
function isWorldVisible(object) {
  let current = object;
  while (current) {
    if (!current.visible) return false;
    current = current.parent;
  }
  return true;
}
function nearestHitPerVolume(intersections) {
  const nearest = new Map();
  for (const intersection of intersections) {
    if (!isWorldVisible(intersection.object)) continue;
    const previous = nearest.get(intersection.object);
    if (!previous || intersection.distance < previous.distance) nearest.set(intersection.object, intersection);
  }
  return [...nearest.values()];
}
function orderedSelectionIntersections(intersections) {
  const visible = nearestHitPerVolume(intersections).sort((a, b) => a.distance - b.distance || a.object.name.localeCompare(b.object.name));
  if (visible.length < 2) return visible;
  const nearestDistance = visible[0].distance;
  const semanticTie = visible.filter((hit) => hit.distance <= nearestDistance + SELECTION_TIE_DISTANCE_M)
    .sort((a, b) => (b.object.userData.selectionPriority - a.object.userData.selectionPriority) || a.distance - b.distance || a.object.name.localeCompare(b.object.name));
  const tiedObjects = new Set(semanticTie.map((hit) => hit.object));
  return [...semanticTie, ...visible.filter((hit) => !tiedObjects.has(hit.object))];
}
function nearestVisibleComponentIntersection(activeRaycaster) {
  if (!model) return null;
  return activeRaycaster.intersectObject(model, true).find((hit) => {
    if (!hit.object.isMesh || hit.object.userData?.is_hit_volume || !isWorldVisible(hit.object)) return false;
    const materials = Array.isArray(hit.object.material) ? hit.object.material : [hit.object.material];
    if (!materials.some((material) => material?.visible !== false && (!material.transparent || material.opacity > 0.01))) return false;
    const component = semanticComponentFor(hit.object);
    if (!machine.components[component]) return false;
    hit.semanticComponent = component;
    return true;
  }) || null;
}
function resolveSelectionIntersection(intersections, visibleSurfaceHit = null) {
  const ordered = orderedSelectionIntersections(intersections);
  if (!visibleSurfaceHit) return ordered[0] || null;
  return ordered.find((hit) => hit.object.userData.component === visibleSurfaceHit.semanticComponent) || null;
}
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
  document.body.dataset.selectionPolicy = `frontmost-rendered-component-then-nearest-proxy-${SELECTION_TIE_DISTANCE_M}m-semantic-tie`;
  return volumes;
}
function runSelectionOrderingFixtures() {
  const object = (name, priority, component = name) => ({ name, visible: true, parent: null, userData: { selectionPriority: priority, component } });
  const front = object("front", 0);
  const rear = object("rear", 5);
  const lowTie = object("low-tie", 1);
  const highTie = object("high-tie", 4);
  const fixtures = [
    { intersections: [{ object: rear, distance: 2 }, { object: front, distance: 1 }], visible: null, expected: "front" },
    { intersections: [{ object: lowTie, distance: 1 }, { object: highTie, distance: 1.01 }], visible: null, expected: "high-tie" },
    { intersections: [{ object: front, distance: 1 }, { object: front, distance: 1.8 }, { object: rear, distance: 2 }], visible: null, expected: "front" },
    { intersections: [{ object: rear, distance: 0.8 }, { object: front, distance: 1 }], visible: { semanticComponent: "front" }, expected: "front" },
    { intersections: [{ object: rear, distance: 0.8 }], visible: { semanticComponent: "front" }, expected: null },
  ];
  const outcomes = fixtures.map((fixture, index) => {
    const observed = resolveSelectionIntersection(fixture.intersections, fixture.visible);
    const minimumDistance = Math.min(...fixture.intersections.map((candidate) => candidate.distance));
    const tieCandidateCount = fixture.intersections.filter((hit) => hit.distance <= minimumDistance + SELECTION_TIE_DISTANCE_M).length;
    const expectedObject = fixture.expected ? fixture.intersections.find((hit) => hit.object.name === fixture.expected)?.object : null;
    return Object.freeze({
      case: index + 1,
      hits: fixture.intersections.map((hit) => Object.freeze({ volume: hit.object.name, component: hit.object.userData.component, distanceM: hit.distance, priority: hit.object.userData.selectionPriority })),
      visibleSurfaceComponent: fixture.visible?.semanticComponent || null,
      basis: fixture.visible ? "visible-surface" : tieCandidateCount > 1 ? "distance-tie" : "nearest-distance",
      expectedComponent: expectedObject?.userData.component || null,
      observedComponent: observed?.object?.userData.component || null,
      expectedVolume: fixture.expected,
      observedVolume: observed?.object?.name || null,
      pass: (observed?.object?.name || null) === fixture.expected,
    });
  });
  const passed = outcomes.filter((outcome) => outcome.pass).length;
  document.body.dataset.selectionFixtureCases = `${passed}/${fixtures.length}`;
  document.body.dataset.selectionFixtureOutcomes = JSON.stringify(outcomes);
  return passed === fixtures.length;
}
function runSelectionVolumeSelfTest() {
  if (!model || selectionVolumes.length !== machine.interactionVolumes.length) return false;
  model.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const probe = new THREE.Raycaster();
  const center = new THREE.Vector3();
  const volumeCenters = new Map();
  const passed = selectionVolumes.filter((hit) => {
    new THREE.Box3().setFromObject(hit).getCenter(center);
    volumeCenters.set(hit, center.clone());
    const projected = center.clone().project(camera);
    probe.setFromCamera(new THREE.Vector2(projected.x, projected.y), camera);
    return probe.intersectObject(hit, false)[0]?.object === hit && Number.isInteger(hit.userData.selectionPriority);
  }).length;
  let overlappingRayCount = 0;
  let nearestRayCount = 0;
  const overlapOutcomes = [];
  for (let firstIndex = 0; firstIndex < selectionVolumes.length; firstIndex += 1) {
    for (let secondIndex = firstIndex + 1; secondIndex < selectionVolumes.length; secondIndex += 1) {
      const first = selectionVolumes[firstIndex];
      const second = selectionVolumes[secondIndex];
      const origin = volumeCenters.get(first);
      const direction = volumeCenters.get(second).clone().sub(origin);
      const centerDistance = direction.length();
      if (centerDistance < 0.001) continue;
      direction.normalize();
      probe.set(origin.clone().addScaledVector(direction, -50), direction);
      probe.near = 0;
      probe.far = centerDistance + 100;
      const intersections = probe.intersectObjects(selectionVolumes, false);
      const independentNearest = new Map();
      for (const intersection of intersections) {
        if (!isWorldVisible(intersection.object)) continue;
        const previous = independentNearest.get(intersection.object);
        if (!previous || intersection.distance < previous.distance) independentNearest.set(intersection.object, intersection);
      }
      const independentHits = [...independentNearest.values()];
      if (independentHits.length < 2) continue;
      overlappingRayCount += 1;
      const visibleSurfaceHit = nearestVisibleComponentIntersection(probe);
      let independentSurfaceComponent = null;
      for (const surfaceHit of probe.intersectObject(model, true)) {
        if (!surfaceHit.object.isMesh || surfaceHit.object.userData?.is_hit_volume || !isWorldVisible(surfaceHit.object)) continue;
        const materials = Array.isArray(surfaceHit.object.material) ? surfaceHit.object.material : [surfaceHit.object.material];
        if (!materials.some((material) => material?.visible !== false && (!material.transparent || material.opacity > 0.01))) continue;
        const component = semanticComponentFor(surfaceHit.object);
        if (!machine.components[component]) continue;
        independentSurfaceComponent = component;
        break;
      }
      const surfaceComponentHits = independentSurfaceComponent
        ? independentHits.filter((hit) => hit.object.userData.component === independentSurfaceComponent)
        : [];
      let independentlyExpected;
      let expectedBasis;
      if (surfaceComponentHits.length) {
        independentlyExpected = surfaceComponentHits.sort((a, b) => a.distance - b.distance || a.object.name.localeCompare(b.object.name))[0];
        expectedBasis = "visible-surface";
      } else {
        const minimumDistance = Math.min(...independentHits.map((hit) => hit.distance));
        const eligibleTieHits = independentHits.filter((hit) => hit.distance <= minimumDistance + SELECTION_TIE_DISTANCE_M);
        const expectedPriority = Math.max(...eligibleTieHits.map((hit) => hit.object.userData.selectionPriority));
        independentlyExpected = eligibleTieHits
          .filter((hit) => hit.object.userData.selectionPriority === expectedPriority)
          .sort((a, b) => a.distance - b.distance || a.object.name.localeCompare(b.object.name))[0];
        expectedBasis = eligibleTieHits.length > 1 ? "distance-tie" : "nearest-distance";
      }
      const resolved = resolveSelectionIntersection(intersections, visibleSurfaceHit);
      if (resolved?.object === independentlyExpected.object) nearestRayCount += 1;
      overlapOutcomes.push(Object.freeze({
        ray: overlapOutcomes.length + 1,
        pairComponents: [first.userData.component, second.userData.component],
        hitComponents: independentHits.map((hit) => hit.object.userData.component),
        hitDistancesM: independentHits.map((hit) => Number(hit.distance.toFixed(4))),
        visibleSurfaceComponent: independentSurfaceComponent,
        expectedComponent: independentlyExpected.object.userData.component,
        resolvedComponent: resolved?.object.userData.component || null,
        expectedVolume: independentlyExpected.object.name,
        resolvedVolume: resolved?.object.name || null,
        basis: expectedBasis,
        pass: resolved?.object === independentlyExpected.object,
      }));
    }
  }
  const fixturesPassed = runSelectionOrderingFixtures();
  const selfTestPassed = passed === selectionVolumes.length && overlappingRayCount > 0 && nearestRayCount === overlappingRayCount && fixturesPassed;
  document.body.dataset.selectionSelftest = selfTestPassed ? "pass" : "fail";
  document.body.dataset.selectionVolumeCount = String(selectionVolumes.length);
  document.body.dataset.selectionOverlapRays = String(overlappingRayCount);
  document.body.dataset.selectionNearestRays = String(nearestRayCount);
  document.body.dataset.selectionOverlapOutcomes = JSON.stringify(overlapOutcomes);
  return selfTestPassed;
}
function setComponentSelection(component) {
  selected = component || null;
  document.querySelectorAll("[data-focus]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.focus === component)));
  if (component) document.body.dataset.selectedComponent = component;
  else delete document.body.dataset.selectedComponent;
}
function clearComponentSelection() {
  setComponentSelection(null);
  delete document.body.dataset.lastSelectionVolume;
  runtime.selection = selectionVolumes.length ? `${selectionVolumes.length}/${selectionVolumes.length} ready` : "pending";
  updateDiagnostics();
}
function selectAt(clientX, clientY) {
  if (!model || !selectionVolumes.length) return;
  const rect = renderer.domElement.getBoundingClientRect();
  pointerNdc.set((clientX - rect.left) / rect.width * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointerNdc, camera);
  const semanticHits = raycaster.intersectObjects(selectionVolumes, false);
  const visibleSurfaceHit = nearestVisibleComponentIntersection(raycaster);
  const hit = resolveSelectionIntersection(semanticHits, visibleSurfaceHit);
  if (visibleSurfaceHit) {
    document.body.dataset.lastRenderedSurfaceComponent = visibleSurfaceHit.semanticComponent;
    document.body.dataset.lastRenderedSurfaceMesh = visibleSurfaceHit.object.name;
  } else {
    delete document.body.dataset.lastRenderedSurfaceComponent;
    delete document.body.dataset.lastRenderedSurfaceMesh;
  }
  document.body.dataset.lastSelectionResolutionBasis = visibleSurfaceHit && hit?.object.userData.component === visibleSurfaceHit.semanticComponent ? "visible-surface" : "nearest-proxy";
  const component = hit?.object.userData.component || null;
  runtime.selection = component || "miss";
  if (component) {
    document.body.dataset.lastSelectionVolume = hit.object.name;
    setComponentSelection(component);
    openInspector(component);
  } else {
    setComponentSelection(null);
  }
  updateDiagnostics();
}

function announceMotion(message) {
  if (!message || terminalFailure) return;
  clearTimeout(motionAnnouncementTimer);
  motionAnnouncementTimer = null;
  motionAnnouncement.textContent = "";
  requestAnimationFrame(() => { if (!terminalFailure) motionAnnouncement.textContent = message; });
}
function scheduleMotionAnnouncement(message) {
  clearTimeout(motionAnnouncementTimer);
  motionAnnouncementTimer = setTimeout(() => announceMotion(message), 350);
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
function setControlOutputs(solved = machine.solveState(state)) {
  const presentation = machine.presentState(state);
  for (const control of machine.controls) {
    let value = presentation.outputs[control.id];
    let ariaValue = value;
    if (control.id === "steer") {
      const degrees = Object.fromEntries(Object.entries(solved.wheelAngles).map(([wheel, radians]) => [wheel, THREE.MathUtils.radToDeg(radians)]));
      const magnitudes = Object.values(degrees).map(Math.abs);
      const maximum = Math.max(...magnitudes);
      const residual = Math.max(...magnitudes) - Math.min(...magnitudes);
      const frontToe = Math.abs(Math.abs(degrees.FL) - Math.abs(degrees.FR));
      const rearToe = Math.abs(Math.abs(degrees.RL) - Math.abs(degrees.RR));
      const direction = state.steer < 0 ? "left" : "right";
      const shortDirection = state.steer < 0 ? "L" : "R";
      if (Math.abs(state.steer) < 0.01) {
        value = "Center";
        ariaValue = "All wheel headings centered";
      } else if (state.steerMode === "circle") {
        value = `${maximum.toFixed(1)}° ${shortDirection} inner`;
        ariaValue = `Circle steer ${direction}; actual wheel headings FL ${degrees.FL.toFixed(1)} degrees, FR ${degrees.FR.toFixed(1)} degrees, RL ${degrees.RL.toFixed(1)} degrees, RR ${degrees.RR.toFixed(1)} degrees; published service steering limit 55 degrees`;
      } else if (state.steerMode === "crab") {
        value = `${maximum.toFixed(1)}° ${shortDirection} · spread ${residual.toFixed(1)}°`;
        ariaValue = `Reconstructed crab steer ${direction}; actual wheel headings FL ${degrees.FL.toFixed(1)} degrees, FR ${degrees.FR.toFixed(1)} degrees, RL ${degrees.RL.toFixed(1)} degrees, RR ${degrees.RR.toFixed(1)} degrees; wheel-heading spread ${residual.toFixed(1)} degrees; fixed-linkage result, not factory controller calibration`;
      } else {
        value = `${maximum.toFixed(1)}° ${shortDirection} front`;
        ariaValue = `Reconstructed front steer ${direction}; actual front wheel headings FL ${degrees.FL.toFixed(1)} degrees and FR ${degrees.FR.toFixed(1)} degrees; rear wheels held aligned at RL ${degrees.RL.toFixed(1)} degrees and RR ${degrees.RR.toFixed(1)} degrees; fixed-linkage result, not factory controller calibration`;
      }
      document.body.dataset.wheelAnglesDeg = Object.entries(degrees).map(([wheel, angle]) => `${wheel}:${angle.toFixed(3)}`).join(",");
      document.body.dataset.crabResidualDeg = residual.toFixed(3);
      document.body.dataset.frontToeDeg = frontToe.toFixed(3);
      document.body.dataset.rearToeDeg = rearToe.toFixed(3);
    }
    const output = document.querySelector(`#${control.outputId}`);
    const input = document.querySelector(`#${control.inputId}`);
    output.value = value;
    setEngineeringValueText(input, ariaValue);
  }
  document.body.dataset.zone = presentation.zone;
  const centered = Math.abs(state.steer) <= 0.01;
  document.body.dataset.steerModeAlignment = centered ? "centered" : "center-required";
  const status = showcaseStarted !== null && !reducedMotion
    ? "Autonomous"
    : presentation.status;
  motionStatus.value = status;
  showcasePhase.textContent = showcaseStarted !== null && !reducedMotion ? "Figure 8" : status;
  return Object.freeze({ ...presentation, status });
}
function applyControls() {
  const solved = machine.solveState(state);
  if (rig) machine.applyState(rig, solved);
  return setControlOutputs(solved);
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
  let requiredDistance = interactionMinDistance;
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
      ? (compact ? 1.90 : 1.75)
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
  setProgrammaticViewDistance(view.distance);
  activeViewName = "follow";
  clearComponentSelection();
}
for (const control of machine.controls) {
  document.querySelector(`#${control.inputId}`).addEventListener("input", (event) => {
    stopShowcase();
    state[control.id] = Number(event.currentTarget.value) / control.inputDivisor;
    const presentation = applyControls();
    if (machine.followView && (control.id === "lift" || control.id === "telescope")) updateFollowView(control.id);
    scheduleMotionAnnouncement(`${control.label}: ${presentation.outputs[control.id]}. ${presentation.status}.`);
  });
}
document.querySelector("#stow").addEventListener("click", () => {
  stopShowcase();
  resetShowcaseRoute();
  Object.assign(state, machine.stowState);
  for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
  document.querySelectorAll("[data-steer-mode]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.steerMode === state.steerMode)));
  const presentation = applyControls();
  clearComponentSelection();
  announceMotion(presentation.status);
});

document.querySelectorAll("[data-steer-mode]").forEach((button) => button.addEventListener("click", () => {
  stopShowcase();
  if (Math.abs(state.steer) > 0.01) {
    document.body.dataset.steerModeAlignment = "center-required";
    document.querySelectorAll("[data-steer-mode]").forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate.dataset.steerMode === state.steerMode)));
    motionStatus.value = "Center steering";
    announceMotion("Center all wheel headings before changing steering mode.");
    return;
  }
  state.steerMode = button.dataset.steerMode;
  document.querySelectorAll("[data-steer-mode]").forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
  const presentation = applyControls();
  announceMotion(`${button.textContent.trim()} steering selected. ${presentation.status}.`);
}));

let lastShowcaseFrameAt = 0;
function syncShowcaseControls() {
  const active = showcaseStarted !== null && !reducedMotion;
  document.body.dataset.showcaseActive = String(active);
  showcaseButton.setAttribute("aria-pressed", String(active));
  showcaseButton.textContent = reducedMotion ? "Auto off" : active ? "Auto" : "Manual";
  showcaseButton.setAttribute("aria-label", reducedMotion ? "Automatic drive unavailable" : active ? "Switch to manual drive" : "Switch to automatic drive");
  autonomyMode.value = reducedMotion ? "Reduced motion" : active ? "Auto loop" : "Manual";
  autonomyNote.textContent = active
    ? "Driving a full figure-eight with reconstructed steering and mechanism motion."
    : "Visualization only - drive and mechanism motion are reconstructed; not a machine capability.";
  showcaseLoop.textContent = `${Math.round((showcaseRoute.phase / (Math.PI * 2)) * 100)}%`;
}
function resetShowcaseRoute() {
  showcaseRoute.phase = 0;
  showcaseRoute.distanceM = 0;
  for (const corner of Object.keys(showcaseRoute.wheelRotations)) showcaseRoute.wheelRotations[corner] = 0;
  if (!rig) return;
  rig.driveCarrier.position.set(0, 0, 0);
  rig.driveCarrier.rotation.set(0, 0, 0);
  for (const pivot of Object.values(rig.wheelRollPivots)) pivot.rotation.y = 0;
  document.body.dataset.driveX = "0.00";
  document.body.dataset.driveZ = "0.00";
  document.body.dataset.driveLoop = "0";
  document.body.dataset.wheelRotationsRad = "0.000,0.000,0.000,0.000";
}
function stopShowcase() {
  showcaseStarted = null;
  syncShowcaseControls();
}
function syncReducedMotion(announce = false) {
  const nextReducedMotion = forceReducedMotion || motionPreference.matches;
  const changed = nextReducedMotion !== reducedMotion;
  reducedMotion = nextReducedMotion;
  document.body.dataset.motionProfile = reducedMotion ? "reduced" : "full";
  showcaseButton.disabled = terminalFailure || reducedMotion;
  if (reducedMotion) {
    showcaseStarted = null;
    orbit.velocityAzimuth = 0;
    orbit.velocityPolar = 0;
    showcaseButton.setAttribute("aria-describedby", "motion-boundary reduced-motion-note");
  } else {
    showcaseButton.removeAttribute("aria-describedby");
  }
  syncShowcaseControls();
  if (announce && changed) announceMotion(reducedMotion ? "Reduced motion enabled. Automatic showcase stopped; manual controls remain available." : "Reduced motion disabled. Automatic showcase is available.");
  updateDiagnostics();
}
showcaseButton?.addEventListener("click", () => {
  if (reducedMotion) return;
  if (showcaseStarted !== null) {
    stopShowcase();
    announceMotion("Automatic 742 mechanism showcase stopped. Manual controls remain available.");
    return;
  }
  showcaseStarted = performance.now();
  const sample = sampleFigureEight(showcaseRoute.phase, JLG742_FIGURE_EIGHT);
  rig.driveCarrier.position.set(sample.x, 0, sample.z);
  rig.driveCarrier.rotation.set(0, sample.heading, 0);
  syncShowcaseControls();
  announceMotion("Automatic 742 figure-eight showcase started.");
});
const handleMotionPreferenceChange = () => syncReducedMotion(true);
if (motionPreference.addEventListener) motionPreference.addEventListener("change", handleMotionPreferenceChange);
else motionPreference.addListener?.(handleMotionPreferenceChange);
syncReducedMotion(false);

let activeViewName = "default";
function focusCamera(name) {
  const preset = adaptView(machine.componentView(name, state, compact), name);
  orbit.azimuth = preset.azimuth;
  orbit.polar = preset.polar;
  const posedComponent = name === "default" ? framedPosedModelView() : framedPosedModelView(name);
  const view = posedComponent || preset;
  orbit.desiredTarget.set(...view.target);
  setProgrammaticViewDistance(view.distance);
  activeViewName = name;
}
function resetView() {
  clearComponentSelection();
  focusCamera("default");
  announceMotion("View reset to frame the current machine pose.");
}
globalThis.__EQUIPMENT_EXPLORER_EVIDENCE__ = Object.freeze({
  frameComponent(component) {
    if (!machine.components[component]) return false;
    clearComponentSelection();
    focusCamera(component);
    updateCamera(1);
    renderer.render(scene, camera);
    return true;
  },
  resetView() {
    resetView();
    updateCamera(1);
    renderer.render(scene, camera);
  },
});
document.querySelector("#reset-view").addEventListener("click", resetView);
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

function setControlsPanel(open) {
  if (terminalFailure) {
    controlsBody.inert = true;
    controlsToggle.hidden = true;
    return;
  }
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
}
function syncMobileControlHeight() {
  if (!mobileQuery.matches) return document.documentElement.style.removeProperty("--mobile-controls-height");
  document.documentElement.style.setProperty("--mobile-controls-height", `${Math.ceil(controlPanel.getBoundingClientRect().height)}px`);
}
new ResizeObserver(syncMobileControlHeight).observe(controlPanel);
controlsToggle.addEventListener("click", () => setControlsPanel(controlsToggle.getAttribute("aria-expanded") !== "true"));
mobileQuery.addEventListener?.("change", () => {
  compact = mobileQuery.matches;
  setControlsPanel(!mobileQuery.matches);
});
setControlsPanel(mobileQuery.matches ? query.get("controls") === "1" : true);

app.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") orbit.azimuth += 0.12;
  else if (event.key === "ArrowRight") orbit.azimuth -= 0.12;
  else if (event.key === "ArrowUp") orbit.polar = Math.max(0.25, orbit.polar - 0.08);
  else if (event.key === "ArrowDown") orbit.polar = Math.min(1.52, orbit.polar + 0.08);
  else if (event.key === "+" || event.key === "=") orbit.desiredDistance = Math.max(interactionMinDistance, orbit.desiredDistance * 0.9);
  else if (event.key === "-" || event.key === "_") orbit.desiredDistance = Math.min(effectiveMaxDistance, orbit.desiredDistance * 1.1);
  else if (event.key === "0") resetView();
  else return;
  document.body.dataset.orbitDesiredDistanceM = orbit.desiredDistance.toFixed(2);
  event.preventDefault();
});

function loadMachineAsset() {
  const loadStarted = performance.now();
  const loadTimeout = setTimeout(() => {
    showTerminalError(new Error(`742 asset load exceeded ${assetLoadTimeoutMs} ms`), "The evidence-bound 742 asset did not finish loading in time. No substitute was shown.", "load-timeout");
  }, assetLoadTimeoutMs);
  try {
    if (testFault === "loader-start") throw new Error("Injected 742 loader-start failure");
    new GLTFLoader().load(machine.assetUrl, (gltf) => {
      clearTimeout(loadTimeout);
      if (terminalFailure) return;
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
        showTerminalError(error, `The ${machine.identity.model} asset failed its hierarchy or semantic-selection contract. No substitute was shown.`, "contract-failed");
      }
    }, undefined, (error) => {
      clearTimeout(loadTimeout);
      showTerminalError(error, `The evidence-bound ${machine.identity.model} asset could not be loaded. No procedural substitute was used.`, "load-failed");
    });
  } catch (error) {
    clearTimeout(loadTimeout);
    showTerminalError(error, `The evidence-bound ${machine.identity.model} asset loader could not start. No procedural substitute was used.`, "loader-start-failed");
  }
}

function animate(now) {
  if (terminalFailure) return;
  animationFrameId = requestAnimationFrame(animate);
  runtimeFrameCount += 1;
  document.body.dataset.runtimeFrameCount = String(runtimeFrameCount);
  document.body.dataset.runtimeLastFrameMs = Number(now).toFixed(3);
  if (document.hidden) {
    lastFrame = now;
    fpsStart = now;
    return;
  }
  const renderedInterval = now - lastFrame;
  const delta = Math.min(renderedInterval / 1000, 0.05);
  if (!skipNextVisibleFrame && renderedInterval > 0) {
    frameTimes.push(renderedInterval);
    if (frameTimes.length > 180) frameTimes.shift();
  }
  skipNextVisibleFrame = false;
  lastFrame = now;
  if (!pointers.size && !reducedMotion) {
    orbit.azimuth += orbit.velocityAzimuth;
    orbit.polar = THREE.MathUtils.clamp(orbit.polar + orbit.velocityPolar, 0.25, 1.52);
    orbit.velocityAzimuth *= 0.88;
    orbit.velocityPolar *= 0.88;
  }
  if (showcaseStarted !== null && machine.showcase && !reducedMotion) {
    const elapsed = (now - showcaseStarted) / (machine.showcaseDurationMs ?? 14000);
    if (elapsed >= 1) showcaseStarted = now;
    const loopProgress = elapsed % 1;
    const showcaseState = { ...machine.showcase(loopProgress) };
    const route = advanceFigureEight(showcaseRoute.phase, delta, JLG742_FIGURE_EIGHT);
    showcaseRoute.phase = route.phase;
    showcaseRoute.distanceM += JLG742_FIGURE_EIGHT.speedMps * delta;
    showcaseState.steer = route.sample.steer;
    showcaseState.steerMode = "circle";
    Object.assign(state, showcaseState);
    for (const control of machine.controls) document.querySelector(`#${control.inputId}`).value = state[control.id] * control.inputDivisor;
    document.querySelectorAll("[data-steer-mode]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.steerMode === state.steerMode)));
    applyControls();
    rig.driveCarrier.position.set(route.sample.x, 0, route.sample.z);
    rig.driveCarrier.rotation.set(0, route.sample.heading, 0);
    routeWheelCorners.forEach((corner, index) => {
      showcaseRoute.wheelRotations[corner] -= JLG742_FIGURE_EIGHT.speedMps * route.sample.wheelSpeedScales[index] * delta / JLG742_FIGURE_EIGHT.wheelRadiusM;
      rig.wheelRollPivots[corner].rotation.y = showcaseRoute.wheelRotations[corner];
    });
    orbit.desiredTarget.set(route.sample.x, Math.max(1.05, orbit.desiredTarget.y), route.sample.z);
    showcaseLoop.textContent = `${Math.round((route.phase / (Math.PI * 2)) * 100)}%`;
    document.body.dataset.driveX = route.sample.x.toFixed(2);
    document.body.dataset.driveZ = route.sample.z.toFixed(2);
    document.body.dataset.driveHeading = String(Math.round(((THREE.MathUtils.radToDeg(route.sample.heading) % 360) + 360) % 360));
    document.body.dataset.driveLoop = String(Math.round((route.phase / (Math.PI * 2)) * 100));
    document.body.dataset.wheelRotationsRad = ["FL", "FR", "RL", "RR"].map((corner) => showcaseRoute.wheelRotations[corner].toFixed(3)).join(",");
    if (machine.followView && now - lastShowcaseFrameAt > 100) {
      updateFollowView("showcase");
      lastShowcaseFrameAt = now;
    }
  }
  updateCamera(delta);
  renderer.render(scene, camera);
  if (now - fpsStart > 1500) {
    if (frameTimes.length) {
      const sorted = [...frameTimes].sort((a, b) => a - b);
      const windowMs = sorted.reduce((sum, sample) => sum + sample, 0);
      runtime.fps = `${Math.round(frameTimes.length * 1000 / windowMs)} fps`;
      const p95Index = Math.max(0, Math.min(sorted.length - 1, Math.ceil(sorted.length * 0.95) - 1));
      runtime.frameP95Ms = `${sorted[p95Index].toFixed(1)} ms`;
      runtime.frameWorstMs = `${sorted.at(-1).toFixed(1)} ms`;
      runtime.visibleStalls = sorted.filter((sample) => sample >= 250).length;
      document.body.dataset.frameP95Ms = runtime.frameP95Ms;
      document.body.dataset.frameWorstMs = runtime.frameWorstMs;
      document.body.dataset.visibleStallCount = String(runtime.visibleStalls);
      document.body.dataset.frameSampleCount = String(frameTimes.length);
      document.body.dataset.performanceWindowMs = String(Math.round(windowMs));
    }
    fpsStart = now;
    updateDiagnostics();
  }
}
function startInjectedLoaderAfterFrames(remainingFrames = 2) {
  if (terminalFailure) return;
  if (remainingFrames > 0) {
    requestAnimationFrame(() => startInjectedLoaderAfterFrames(remainingFrames - 1));
    return;
  }
  loadMachineAsset();
}
resetPerformanceWindow("startup");
animationFrameId = requestAnimationFrame(animate);
if (!terminalFailure) {
  if (testFault === "loader-start") startInjectedLoaderAfterFrames();
  else loadMachineAsset();
}
addEventListener("resize", () => {
  compact = mobileQuery.matches;
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(innerWidth, innerHeight);
  applyShadowProfile();
  if (activeViewName === "follow") {
    updateFollowView("resize");
  } else {
    focusCamera(activeViewName);
  }
  syncMobileControlHeight();
});
document.addEventListener("visibilitychange", () => {
  resetPerformanceWindow(document.hidden ? "visibility-hidden" : "visibility-visible");
});
setControlOutputs();
updateDiagnostics();
