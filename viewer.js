import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import {
  GLB_URL,
  SHOWCASE_RELEASE,
  TELESCOPE_TRAVEL_M,
  TELESCOPE_MID_TRAVEL_M,
  TELESCOPE_FLY_TRAVEL_M,
} from "./assets/models/600s.version.js?v=1.1.14";

document.body.dataset.viewerStarted = "true";
const query = new URLSearchParams(location.search);
const forceReducedMotion = query.get("reduce") === "1";
const motionPreference = window.matchMedia?.("(prefers-reduced-motion: reduce)") ?? null;
let reducedMotion = forceReducedMotion || Boolean(motionPreference?.matches);
const COMPACT_VIEWPORT_QUERY = "(max-width: 800px), (max-height: 500px) and (orientation: landscape) and (max-width: 1000px)";
const compactRender = window.matchMedia?.(COMPACT_VIEWPORT_QUERY).matches ?? false;
const lowMemoryDevice = Number(navigator.deviceMemory) > 0 && Number(navigator.deviceMemory) <= 4;
const renderProfile = lowMemoryDevice ? "economy" : compactRender ? "mobile" : "desktop";
const maximumPixelRatio = lowMemoryDevice ? 1.15 : compactRender ? 1.35 : 1.75;
const shadowMapSize = lowMemoryDevice || compactRender ? 1024 : 2048;
const minimumFrameInterval = lowMemoryDevice ? 1000 / 30 : compactRender ? 1000 / 45 : 0;
const ASSET_LOAD_TIMEOUT_MS = 15000;
const app = document.querySelector("#app");
const loader = document.querySelector("#loader");
const loaderStatus = document.querySelector("#loader-status");
const loaderDetail = document.querySelector("#loader-detail");
const errorPanel = document.querySelector("#error");
const diagnosticsOutput = document.querySelector("#diagnostics");
const controlPanel = document.querySelector(".control-panel");
const controlsBody = document.querySelector("#machine-controls-body");
const controlsToggle = document.querySelector("#controls-toggle");
const mobileControlsQuery = window.matchMedia(COMPACT_VIEWPORT_QUERY);
const diagnosticsEnabled = query.get("diagnostics") === "1";
const runtimeDiagnostics = {
  errors: 0,
  selectionHits: "pending",
  frameRate: "sampling",
  loadMs: "pending",
};
let terminalFailure = false;
let animationFrameId = null;
let runtimeFrameCount = 0;
document.body.dataset.renderProfile = renderProfile;
document.body.dataset.reducedMotion = String(reducedMotion);

function updateMobileControlHeight() {
  if (!mobileControlsQuery.matches || !controlPanel) {
    document.documentElement.style.removeProperty("--mobile-controls-height");
    return;
  }
  document.documentElement.style.setProperty("--mobile-controls-height", `${Math.ceil(controlPanel.getBoundingClientRect().height)}px`);
}

function setMobileControls(open) {
  const isMobile = mobileControlsQuery.matches;
  const expanded = isMobile ? open : true;
  controlsBody.hidden = !expanded;
  controlsBody.inert = !expanded;
  controlsToggle.hidden = !isMobile;
  controlsToggle.setAttribute("aria-expanded", String(expanded));
  controlsToggle.setAttribute("aria-label", expanded ? "Close machine controls" : "Adjust machine controls");
  controlsToggle.textContent = expanded ? "Close" : "Adjust";
  document.body.classList.toggle("mobile-controls-open", isMobile && expanded);
  requestAnimationFrame(updateMobileControlHeight);
}

controlsToggle.addEventListener("click", () => {
  setMobileControls(controlsToggle.getAttribute("aria-expanded") !== "true");
});
const handleMobileControlsChange = () => setMobileControls(false);
if (mobileControlsQuery.addEventListener) mobileControlsQuery.addEventListener("change", handleMobileControlsChange);
else mobileControlsQuery.addListener(handleMobileControlsChange);
setMobileControls(false);

function recordRuntimeError(error) {
  runtimeDiagnostics.errors += 1;
  document.body.dataset.runtimeErrorCount = String(runtimeDiagnostics.errors);
  if (error) console.error(error);
  updateDiagnostics();
}

function showTerminalError(error, message, source = "runtime-failed") {
  if (terminalFailure) return;
  terminalFailure = true;
  if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
  animationFrameId = null;
  document.body.classList.remove("inspector-open", "mobile-controls-open");
  document.body.classList.add("viewer-terminal-error");
  document.body.dataset.viewerTerminal = "true";
  document.body.dataset.machineSource = source;
  document.body.dataset.viewerRuntimeActive = "false";
  const useRuntimeFrameCount = runtimeFrameCount >= 2;
  const terminalFrameCount = useRuntimeFrameCount ? runtimeFrameCount : Number(document.body.dataset.bootFrameCount || 0);
  document.body.dataset.terminalFrameCount = String(terminalFrameCount);
  document.body.dataset.terminalFrameSource = useRuntimeFrameCount ? "runtime" : "boot";
  recordRuntimeError(error);
  loader.hidden = true;
  document.querySelector("#error-copy").textContent = message;
  errorPanel.hidden = false;
  app.setAttribute("inert", "");
  document.querySelector(".interface")?.setAttribute("inert", "");
  document.querySelector("#inspector")?.setAttribute("inert", "");
  controlsBody.inert = true;
  controlPanel.setAttribute("aria-disabled", "true");
  controlPanel.querySelectorAll("button, input").forEach((control) => { control.disabled = true; });
  errorPanel.focus({ preventScroll: true });
}
window.addEventListener("error", (event) => showTerminalError(event.error, "The 600S viewer stopped after an unexpected runtime error. No substitute was shown."));
window.addEventListener("unhandledrejection", (event) => showTerminalError(event.reason, "The 600S viewer stopped after an unexpected runtime error. No substitute was shown."));
document.body.dataset.viewerRuntimeActive = "true";

function updateDiagnostics() {
  if (!diagnosticsOutput) return;
  diagnosticsOutput.hidden = !diagnosticsEnabled;
  diagnosticsOutput.value = [
    `source ${document.body.dataset.machineSource || "initializing"}`,
    `meshes ${document.body.dataset.machineVisibleMeshes || "pending"}`,
    `selection ${runtimeDiagnostics.selectionHits}`,
    `errors ${runtimeDiagnostics.errors}`,
    `load ${runtimeDiagnostics.loadMs}`,
    `render ${renderProfile} / ${runtimeDiagnostics.frameRate}`,
    `reduced motion ${reducedMotion ? "on" : "off"}`,
  ].join(" · ");
}
document.body.dataset.runtimeErrorCount = "0";
updateDiagnostics();

function pixelRatio() {
  return Math.min(devicePixelRatio || 1, maximumPixelRatio);
}

function createRenderer() {
  try {
    const test = document.createElement("canvas");
    if (!window.WebGLRenderingContext || !(test.getContext("webgl2") || test.getContext("webgl"))) return null;
    return new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  } catch {
    return null;
  }
}

const renderer = createRenderer();
if (!renderer) {
  showTerminalError(new Error("WebGL unavailable"), "This interactive study needs a browser with WebGL enabled.", "webgl-unavailable");
} else {
renderer.setPixelRatio(pixelRatio());
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.02;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x121719);
scene.fog = new THREE.Fog(0x121719, 32, 68);

const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 100);
const hemi = new THREE.HemisphereLight(0xd9e8f2, 0x34362f, 1.8);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xfff7e8, 3.4);
key.position.set(-9, 13, 10);
key.castShadow = true;
key.shadow.mapSize.set(shadowMapSize, shadowMapSize);
key.shadow.camera.left = -14;
key.shadow.camera.right = 14;
key.shadow.camera.top = 14;
key.shadow.camera.bottom = -8;
key.shadow.camera.near = 1;
key.shadow.camera.far = 38;
key.shadow.bias = -0.00025;
key.shadow.normalBias = 0.025;
scene.add(key);
const fill = new THREE.DirectionalLight(0x9ebbd0, 1.6);
fill.position.set(8, 6, 10);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xff9a55, 1.35);
rim.position.set(10, 6, -8);
scene.add(rim);
const lightTarget = new THREE.Object3D();
const keyOffset = new THREE.Vector3(-9, 13, 10);
const fillOffset = new THREE.Vector3(8, 6, 10);
const rimOffset = new THREE.Vector3(10, 6, -8);
key.target = lightTarget;
fill.target = lightTarget;
rim.target = lightTarget;
scene.add(lightTarget);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(18, 96),
  new THREE.MeshStandardMaterial({ color: 0x242a2a, roughness: 0.96, metalness: 0 })
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
scene.add(floor);

const grid = new THREE.GridHelper(34, 34, 0x5c5f56, 0x30342f);
grid.position.y = 0.004;
grid.material.transparent = true;
grid.material.opacity = 0.12;
scene.add(grid);

const palette = {
  orange: new THREE.MeshStandardMaterial({ color: 0xe99914, roughness: 0.63, metalness: 0.08 }),
  dark: new THREE.MeshStandardMaterial({ color: 0x242823, roughness: 0.75, metalness: 0.16 }),
  tire: new THREE.MeshStandardMaterial({ color: 0x111311, roughness: 0.93 }),
  metal: new THREE.MeshStandardMaterial({ color: 0x777b72, roughness: 0.5, metalness: 0.46 }),
  glass: new THREE.MeshStandardMaterial({ color: 0x242b28, roughness: 0.2, metalness: 0.1 }),
};

function box(name, size, position, material, component) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  if (component) mesh.userData.component = component;
  return mesh;
}

function cylinder(name, radius, length, position, rotation, material, component, segments = 28) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, segments), material);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.rotation.set(...rotation);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  if (component) mesh.userData.component = component;
  return mesh;
}

function rail(parent, a, b, thickness = 0.035) {
  const direction = new THREE.Vector3().subVectors(b, a);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(thickness, thickness, direction.length(), 10), palette.metal);
  mesh.position.copy(a).add(b).multiplyScalar(0.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
  mesh.castShadow = true;
  mesh.userData.component = "platform";
  parent.add(mesh);
}

function createProcedural600S() {
  const machine = new THREE.Group();
  machine.name = "JLG_600S_PROXY";
  machine.userData.source = "procedural-fixture";
  const hitVolumes = [];
  const hitMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
  hitMaterial.colorWrite = false;
  function addHitVolume(parent, name, size, position, component) {
    const hit = new THREE.Mesh(new THREE.BoxGeometry(...size), hitMaterial);
    hit.name = name;
    hit.position.set(...position);
    hit.userData.component = component;
    parent.add(hit);
    hitVolumes.push(hit);
    return hit;
  }

  const chassis = new THREE.Group();
  chassis.name = "Chassis";
  chassis.add(box("Frame", [5.5, 0.62, 1.65], [0, 1.02, 0], palette.dark, "chassis"));
  chassis.add(box("LowerDeck", [4.6, 0.18, 1.78], [0.1, 1.39, 0], palette.orange, "chassis"));

  const steeringPivots = [];
  const rollingWheels = [];
  const wheelX = [-1.9, 1.9];
  const wheelZ = [-1.08, 1.08];
  wheelX.forEach((x, axleIndex) => wheelZ.forEach((z) => {
    const pivot = new THREE.Group();
    pivot.name = `WheelPivot_${axleIndex}_${z > 0 ? "L" : "R"}`;
    pivot.position.set(x, 0.75, z);
    const roll = new THREE.Group();
    roll.name = `${pivot.name}_Roll`;
    const wheel = cylinder(`Wheel_${axleIndex}_${z > 0 ? "L" : "R"}`, 0.67, 0.48, [0, 0, 0], [Math.PI / 2, 0, 0], palette.tire, "chassis", 32);
    const hub = cylinder("WheelHub", 0.23, 0.5, [0, 0, 0], [Math.PI / 2, 0, 0], palette.metal, "chassis", 24);
    roll.add(wheel, hub);
    pivot.add(roll);
    chassis.add(pivot);
    rollingWheels.push(roll);
    if (axleIndex === 1) steeringPivots.push(pivot);
  }));
  machine.add(chassis);

  const turntablePivot = new THREE.Group();
  turntablePivot.name = "TurntablePivot";
  turntablePivot.position.set(-0.65, 1.48, 0);
  const turntable = new THREE.Group();
  turntable.name = "Turntable";
  turntable.add(cylinder("SlewRing", 0.72, 0.24, [0, 0.12, 0], [0, 0, 0], palette.metal, "turntable", 36));
  turntable.add(box("UpperStructure", [2.7, 0.86, 1.52], [0.1, 0.66, 0], palette.orange, "turntable"));
  turntable.add(box("Counterweight", [1.05, 1.18, 1.64], [-1.35, 0.79, 0], palette.orange, "turntable"));
  turntable.add(box("EngineHousing", [1.18, 0.76, 1.28], [-0.28, 1.33, 0], palette.dark, "turntable"));
  turntablePivot.add(turntable);
  machine.add(turntablePivot);

  const boomPivot = new THREE.Group();
  boomPivot.name = "BoomPivot";
  boomPivot.position.set(0.72, 1.7, 0);
  turntable.add(boomPivot);

  const baseBoom = new THREE.Group();
  baseBoom.name = "BaseBoom";
  baseBoom.add(box("BaseBoomShell", [4.8, 0.58, 0.67], [2.4, 0, 0], palette.orange, "boom"));
  baseBoom.add(cylinder("BoomPivotPin", 0.34, 0.94, [0, 0, 0], [Math.PI / 2, 0, 0], palette.metal, "boom", 24));
  boomPivot.add(baseBoom);

  const telescope = new THREE.Group();
  telescope.name = "TelescopeBoom";
  telescope.position.x = 3.8;
  telescope.add(box("TelescopeShell", [4.7, 0.42, 0.51], [2.35, 0, 0], palette.dark, "boom"));
  baseBoom.add(telescope);

  const platformPivot = new THREE.Group();
  platformPivot.name = "PlatformPivot";
  platformPivot.position.set(4.75, -0.12, 0);
  telescope.add(platformPivot);
  const platformMount = new THREE.Group();
  platformMount.name = "Platform";
  platformPivot.add(platformMount);
  platformMount.add(box("PlatformDeck", [1.42, 0.13, 1.02], [0.7, -0.38, 0], palette.orange, "platform"));
  platformMount.add(box("ControlConsole", [0.34, 0.38, 0.78], [1.14, 0.25, -0.03], palette.dark, "platform"));
  const corners = [[0.05,-.45],[1.35,-.45],[.05,.45],[1.35,.45]];
  corners.forEach(([x,z]) => rail(platformMount, new THREE.Vector3(x,-.3,z), new THREE.Vector3(x,.75,z)));
  rail(platformMount, new THREE.Vector3(.05,.75,-.45), new THREE.Vector3(1.35,.75,-.45));
  rail(platformMount, new THREE.Vector3(.05,.75,.45), new THREE.Vector3(1.35,.75,.45));
  rail(platformMount, new THREE.Vector3(.05,.75,-.45), new THREE.Vector3(.05,.75,.45));
  rail(platformMount, new THREE.Vector3(1.35,.75,-.45), new THREE.Vector3(1.35,.75,.45));

  const cylinderBody = cylinder("LiftCylinder", 0.14, 2.15, [0.55, -0.75, 0], [0, 0, Math.PI / 3], palette.metal, "boom", 18);
  boomPivot.add(cylinderBody);

  addHitVolume(chassis, "Chassis_Hit", [6.2, 1.75, 2.75], [0, 0.95, 0], "chassis");
  addHitVolume(turntable, "Turntable_Hit", [3.9, 2.55, 2.25], [-0.25, 0.95, 0], "turntable");
  addHitVolume(baseBoom, "Boom_Hit", [5.2, 1.25, 1.25], [2.4, 0, 0], "boom");
  addHitVolume(telescope, "Telescope_Hit", [5.1, 1.05, 1.05], [2.35, 0, 0], "boom");
  addHitVolume(platformMount, "Platform_Hit", [1.85, 1.65, 1.4], [0.72, 0.18, 0], "platform");

  machine.position.set(-0.7, 0, 0);
  scene.add(machine);
  return {
    machine,
    chassis,
    turntablePivot,
    boomPivot,
    telescope,
    telescopeHomeX: telescope.position.x,
    telescopeTravelM: 3.8,
    platformPivot,
    platformMount,
    steeringPivots,
    steeringTrackM: Math.abs(wheelZ[0] - wheelZ[1]),
    rollingWheels,
    hitVolumes,
    source: "procedural-fixture",
  };
}

const requiredNodes = [
  "600S_ROOT", "Chassis", "Frame", "AxleFront", "AxleRear",
  "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR", "TurntablePivot",
  "Wheel_FL_Roll", "Wheel_FR_Roll", "Wheel_RL_Roll", "Wheel_RR_Roll",
  "Turntable", "SlewRing", "UpperFrame", "EngineCover", "TankCover",
  "Counterweight", "Controls", "BoomPivot", "MainBoom", "Telescope",
  "BaseBoomExitWearTop", "BaseBoomExitWearBottom", "BaseBoomExitWear_L", "BaseBoomExitWear_R",
  "MidBoom", "MidBoomTopPlate", "MidBoomSideReveal_L", "MidBoomSideReveal_R",
  "MidBoomExitWearTop", "MidBoomExitWearBottom", "MidBoomExitWear_L", "MidBoomExitWear_R",
  "FlyBoom", "FlyBoomTopPlate", "FlyBoomSideReveal_L", "FlyBoomSideReveal_R",
  "PlatformPivot", "PlatformRotator", "Platform",
  "LiftCylinder", "LiftCylinderLowerAnchor", "LiftCylinderUpperAnchor",
  "LiftCylinderBarrel", "LiftCylinderRod", "LiftCylinderBasePin", "LiftCylinderRodPin",
  "TowerLink", "TowerLinkLowerAnchor", "TowerLinkUpperAnchor", "TowerLinkBody",
  "TensionLink", "TensionLinkLowerAnchor", "TensionLinkUpperAnchor", "TensionLinkBody",
  "SteerTieRod", "SteerTieRodLowerAnchor", "SteerTieRodUpperAnchor", "SteerTieRodBody",
  "SteerCylinder_L", "SteerCylinder_L_LowerAnchor", "SteerCylinder_L_UpperAnchor", "SteerCylinder_L_Rod",
  "SteerCylinder_R", "SteerCylinder_R_LowerAnchor", "SteerCylinder_R_UpperAnchor", "SteerCylinder_R_Rod",
  "PlatformLevelCylinder", "PlatformLevelCylinderLowerAnchor", "PlatformLevelCylinderUpperAnchor", "PlatformLevelCylinderRod",
  "Powertrack", "PowertrackMovingRun", "PowertrackBend", "PowertrackSupport", "PowertrackPushTube", "PlatformSwingGate",
  "SteerHydraulicHose_L", "SteerHydraulicHose_L_LowerAnchor", "SteerHydraulicHose_L_UpperAnchor", "SteerHydraulicHose_L_Flexible", "SteerHydraulicHose_L_Segment_02",
  "SteerHydraulicHose_R", "SteerHydraulicHose_R_LowerAnchor", "SteerHydraulicHose_R_UpperAnchor", "SteerHydraulicHose_R_Flexible", "SteerHydraulicHose_R_Segment_02",
  "PlatformConsole", "PlatformFootswitch",
];
const interactionComponents = {
  Chassis_Hit: "chassis",
  Turntable_Hit: "turntable",
  Boom_Hit: "boom",
  Telescope_Hit: "boom",
  Platform_Hit: "platform",
};

const materialProfiles = {
  JLG_Blockout_Orange: { color: "#f27624", roughness: 0.48, metalness: 0.04 },
  JLG_Blockout_OrangeDeep: { color: "#bd4518", roughness: 0.55, metalness: 0.04 },
  JLG_Blockout_Dark: { color: "#151a1b", roughness: 0.72, metalness: 0.08 },
  JLG_Blockout_Tire: { color: "#111313", roughness: 0.94, metalness: 0 },
  JLG_Blockout_Metal: { color: "#747c7d", roughness: 0.4, metalness: 0.64 },
  JLG_Orange_PowderCoat: { color: "#f36f21", roughness: 0.42, metalness: 0.04 },
  JLG_Orange_Shadow: { color: "#a93612", roughness: 0.56, metalness: 0.05 },
  JLG_Boom_Cream: { color: "#d8c992", roughness: 0.48, metalness: 0.03 },
  JLG_Boom_Inner_Cream: { color: "#bfae74", roughness: 0.54, metalness: 0.04 },
  JLG_Boom_Wear: { color: "#252a28", roughness: 0.60, metalness: 0.24 },
  JLG_Black_PowderCoat: { color: "#111516", roughness: 0.64, metalness: 0.18 },
  JLG_Tire_Rubber: { color: "#111313", roughness: 0.94, metalness: 0 },
  JLG_Zinc_Steel: { color: "#777b76", roughness: 0.38, metalness: 0.68 },
  JLG_Dark_Steel: { color: "#252b2a", roughness: 0.44, metalness: 0.72 },
  JLG_Rim_OffWhite: { color: "#c0bfae", roughness: 0.42, metalness: 0.58 },
  JLG_Hydraulic_Black: { color: "#111515", roughness: 0.7, metalness: 0.12 },
  JLG_Electrical_Loom: { color: "#202525", roughness: 0.84, metalness: 0.02 },
  JLG_Control_Cable: { color: "#2d3230", roughness: 0.78, metalness: 0.03 },
  JLG_Wire_Rope: { color: "#777c78", roughness: 0.42, metalness: 0.78 },
  JLG_Powertrack_Carrier: { color: "#171b1a", roughness: 0.80, metalness: 0.06 },
  JLG_Sensor_Black: { color: "#171a1a", roughness: 0.48, metalness: 0.04 },
  JLG_Control_Red: { color: "#b1140c", roughness: 0.42, metalness: 0.02 },
  JLG_Beacon_Amber: { color: "#ff6a0a", roughness: 0.18, metalness: 0 },
  JLG_Label_White: { color: "#eee9d8", roughness: 0.55, metalness: 0.02 },
  JLG_Warning_Yellow: { color: "#f5a514", roughness: 0.5, metalness: 0.01 },
};

function applyMaterialProfile(material, profile) {
  if (!material || !profile) return;
  material.color.set(profile.color);
  material.roughness = profile.roughness;
  material.metalness = profile.metalness;
  material.needsUpdate = true;
}

function applyDisplayMaterial(node, profile, suffix) {
  if (!node?.isMesh || Array.isArray(node.material)) return;
  node.material = node.material.clone();
  node.material.name = `${node.material.name}_${suffix}`;
  applyMaterialProfile(node.material, profile);
}

const markingTextureCache = new Map();
function createMarkingTexture(text, foreground) {
  const cacheKey = `${text}|${foreground}`;
  if (markingTextureCache.has(cacheKey)) return markingTextureCache.get(cacheKey);
  const markingCanvas = document.createElement("canvas");
  markingCanvas.width = 512;
  markingCanvas.height = 128;
  const context = markingCanvas.getContext("2d");
  context.clearRect(0, 0, markingCanvas.width, markingCanvas.height);
  context.fillStyle = foreground;
  context.font = "italic 900 82px Arial, Helvetica, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, markingCanvas.width / 2, markingCanvas.height / 2 + 3);
  const texture = new THREE.CanvasTexture(markingCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  markingTextureCache.set(cacheKey, texture);
  return texture;
}

function addSideMarking(parent, name, text, size, position, side, foreground) {
  if (!parent) return;
  const material = new THREE.MeshBasicMaterial({
    map: createMarkingTexture(text, foreground),
    transparent: true,
    alphaTest: 0.18,
    toneMapped: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  });
  material.name = `Independent_${name}_Marking`;
  const marking = new THREE.Mesh(new THREE.PlaneGeometry(...size), material);
  marking.name = name;
  marking.position.set(...position);
  marking.rotation.y = side < 0 ? Math.PI : 0;
  marking.userData.authority = "independently-typeset-nominative-mark";
  marking.userData.not_manufacturer_artwork = true;
  parent.add(marking);
}

function createHazardTexture() {
  const stripeCanvas = document.createElement("canvas");
  stripeCanvas.width = 512;
  stripeCanvas.height = 64;
  const context = stripeCanvas.getContext("2d");
  context.fillStyle = "#e6a411";
  context.fillRect(0, 0, stripeCanvas.width, stripeCanvas.height);
  context.strokeStyle = "#171a19";
  context.lineWidth = 46;
  for (let x = -80; x < stripeCanvas.width + 80; x += 88) {
    context.beginPath();
    context.moveTo(x, stripeCanvas.height + 12);
    context.lineTo(x + 74, -12);
    context.stroke();
  }
  const texture = new THREE.CanvasTexture(stripeCanvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function addHazardBands(turntable) {
  const material = new THREE.MeshBasicMaterial({ map: createHazardTexture(), toneMapped: false });
  material.name = "Independent_HazardBand_Presentation";
  [-1, 1].forEach((side) => {
    const band = new THREE.Mesh(new THREE.PlaneGeometry(1.48, 0.105), material);
    band.name = `HazardBand_${side < 0 ? "L" : "R"}`;
    band.position.set(-1.58, 0.49, side * 1.052);
    band.rotation.y = side < 0 ? Math.PI : 0;
    band.userData.authority = "independently-authored-generic-safety-pattern";
    band.userData.not_operational_label = true;
    turntable.add(band);
  });
}

function addOwnedPresentationMarkings(nodes) {
  const dark = "#151a1b";
  [-1, 1].forEach((side) => {
    addSideMarking(nodes.Turntable, `600S_Marking_${side < 0 ? "L" : "R"}`, "600S", [0.66, 0.19], [-1.71, 0.74, side * 1.048], side, "#f4efe1");
    addSideMarking(nodes.MainBoom, `JLG_Lift_Marking_${side < 0 ? "L" : "R"}`, "JLG LIFT", [1.40, 0.28], [2.68, 0.04, side * 0.348], side, dark);
    addSideMarking(nodes.Platform, `JLG_Platform_Marking_${side < 0 ? "L" : "R"}`, "JLG", [0.58, 0.18], [0.46, -0.515, side * 1.221], side, dark);
  });
  addHazardBands(nodes.Turntable);
}

function tuneBlockoutMaterials(root) {
  const materials = new Set();
  root.traverse((node) => {
    if (!node.isMesh || node.userData.is_hit_volume) return;
    const nodeMaterials = Array.isArray(node.material) ? node.material : [node.material];
    nodeMaterials.forEach((value) => materials.add(value));
  });
  materials.forEach((value) => applyMaterialProfile(value, materialProfiles[value.name]));

  const boomCream = materialProfiles.JLG_Boom_Cream;
  ["BaseBoomShell", "MidBoomShell"].forEach((name) => {
    applyDisplayMaterial(root.getObjectByName(name), boomCream, "DisplayCream");
  });
  const finishVariations = [
    ["EngineCover", { color: "#ef6821", roughness: 0.40, metalness: 0.04 }, "WarmPowderCoat"],
    ["TankCover", { color: "#e95f1e", roughness: 0.46, metalness: 0.04 }, "TankPowderCoat"],
    ["Counterweight", { color: "#e85d1d", roughness: 0.51, metalness: 0.05 }, "CastPowderCoat"],
    ["LowerDeck", { color: "#e86520", roughness: 0.58, metalness: 0.06 }, "DeckPowderCoat"],
    ["PlatformDeck", { color: "#e76220", roughness: 0.62, metalness: 0.06 }, "WearDeckPowderCoat"],
    ["MidBoomShell", { color: "#bfae74", roughness: 0.54, metalness: 0.04 }, "NestedCream"],
    ["MidBoomTopPlate", { color: "#e1d3a4", roughness: 0.49, metalness: 0.03 }, "NestedTopPlate"],
    ["FlyBoomShell", { color: "#e96720", roughness: 0.48, metalness: 0.04 }, "CurrentFlyOrange"],
    ["FlyBoomTopPlate", { color: "#a93612", roughness: 0.56, metalness: 0.05 }, "FlyTopReveal"],
  ];
  finishVariations.forEach(([name, profile, suffix]) => applyDisplayMaterial(root.getObjectByName(name), profile, suffix));
}

function isInsideExcludedBranch(node, group, excludedRoots) {
  let current = node;
  while (current && current !== group) {
    if (excludedRoots.includes(current)) return true;
    current = current.parent;
  }
  return false;
}

function geometrySignature(geometry) {
  const attributes = Object.entries(geometry.attributes)
    .map(([name, attribute]) => `${name}:${attribute.itemSize}:${attribute.normalized}:${attribute.array.constructor.name}`)
    .sort()
    .join("|");
  return `${geometry.index ? "indexed" : "plain"}|${attributes}`;
}

function mergeRigidGroup(group, excludedRoots = []) {
  if (!group) return 0;
  group.updateWorldMatrix(true, true);
  const groupInverse = new THREE.Matrix4().copy(group.matrixWorld).invert();
  const localMatrix = new THREE.Matrix4();
  const buckets = new Map();

  group.traverse((node) => {
    if (!node.isMesh || node.userData.is_hit_volume || Array.isArray(node.material)) return;
    if (isInsideExcludedBranch(node, group, excludedRoots)) return;
    const key = `${node.material.uuid}|${geometrySignature(node.geometry)}`;
    if (!buckets.has(key)) buckets.set(key, { material: node.material, geometries: [], sources: [] });
    localMatrix.multiplyMatrices(groupInverse, node.matrixWorld);
    const geometry = node.geometry.clone();
    geometry.applyMatrix4(localMatrix);
    buckets.get(key).geometries.push(geometry);
    buckets.get(key).sources.push(node);
  });

  let mergedCount = 0;
  buckets.forEach((bucket) => {
    if (bucket.geometries.length < 2) {
      bucket.geometries.forEach((value) => value.dispose());
      return;
    }
    const geometry = mergeGeometries(bucket.geometries, false);
    bucket.geometries.forEach((value) => value.dispose());
    if (!geometry) return;
    const mesh = new THREE.Mesh(geometry, bucket.material);
    mesh.name = `RuntimeMerged_${group.name}_${mergedCount + 1}`;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
    bucket.sources.forEach((source) => source.removeFromParent());
    mergedCount += 1;
  });
  return mergedCount;
}

function optimizeDetailedRig(nodes) {
  let mergedBuckets = 0;
  const wheelRollNodes = [nodes.Wheel_FL_Roll, nodes.Wheel_FR_Roll, nodes.Wheel_RL_Roll, nodes.Wheel_RR_Roll];
  wheelRollNodes.forEach((roll) => { mergedBuckets += mergeRigidGroup(roll); });
  mergedBuckets += mergeRigidGroup(nodes.Chassis, [
    nodes.Wheel_FL, nodes.Wheel_FR, nodes.Wheel_RL, nodes.Wheel_RR,
    nodes.SteerTieRod, nodes.SteerCylinder_L, nodes.SteerCylinder_R,
    nodes.SteerHydraulicHose_L, nodes.SteerHydraulicHose_R,
  ]);
  mergedBuckets += mergeRigidGroup(nodes.LiftCylinder, [nodes.LiftCylinderRod, nodes.LiftCylinderRodPin]);
  mergedBuckets += mergeRigidGroup(nodes.SteerCylinder_L, [nodes.SteerCylinder_L_Rod]);
  mergedBuckets += mergeRigidGroup(nodes.SteerCylinder_R, [nodes.SteerCylinder_R_Rod]);
  mergedBuckets += mergeRigidGroup(nodes.PlatformLevelCylinder, [nodes.PlatformLevelCylinderRod]);
  mergedBuckets += mergeRigidGroup(nodes.PlatformPivot);
  mergedBuckets += mergeRigidGroup(nodes.FlyBoom, [nodes.PlatformPivot, nodes.PlatformLevelCylinder]);
  mergedBuckets += mergeRigidGroup(nodes.MidBoom, [nodes.FlyBoom]);
  mergedBuckets += mergeRigidGroup(nodes.Telescope, [nodes.MidBoom]);
  mergedBuckets += mergeRigidGroup(nodes.BoomPivot, [nodes.Telescope]);
  mergedBuckets += mergeRigidGroup(nodes.Turntable, [
    nodes.BoomPivot, nodes.LiftCylinder, nodes.TowerLink, nodes.TensionLink,
  ]);
  nodes["600S_ROOT"].updateMatrixWorld(true);
  let visibleMeshes = 0;
  nodes["600S_ROOT"].traverse((node) => {
    if (node.isMesh && !node.userData.is_hit_volume) visibleMeshes += 1;
  });
  return { mergedBuckets, visibleMeshes };
}

function prepareHitVolumes(hitVolumes) {
  hitVolumes.forEach((hit) => {
    if (hit.userData.selectionOutline) return;
    const material = new THREE.LineBasicMaterial({
      color: 0xf3a51f,
      transparent: true,
      opacity: 0,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    const outline = new THREE.LineSegments(new THREE.EdgesGeometry(hit.geometry), material);
    outline.name = `${hit.name}_SelectionOutline`;
    outline.visible = false;
    outline.raycast = () => {};
    outline.renderOrder = 20;
    hit.add(outline);
    hit.userData.selectionOutline = outline;
  });
}

function updateHitVolumeEmphasis(hoveredHit = null) {
  if (!rig?.hitVolumes) return;
  rig.hitVolumes.forEach((hit) => {
    const outline = hit.userData.selectionOutline;
    if (!outline) return;
    const isHovered = hit === hoveredHit;
    const isFocused = Boolean(focusedComponent && hit.userData.component === focusedComponent);
    outline.visible = isHovered || isFocused;
    outline.material.opacity = isHovered ? 0.92 : isFocused ? 0.38 : 0;
  });
}

function configureBlockoutRig(gltf) {
  const nodes = Object.fromEntries(requiredNodes.map((name) => [name, gltf.scene.getObjectByName(name)]));
  const missingNodes = requiredNodes.filter((name) => !nodes[name]);
  const hitVolumes = Object.entries(interactionComponents).map(([name, component]) => {
    const hit = gltf.scene.getObjectByName(name);
    if (!hit) missingNodes.push(name);
    if (hit) {
      hit.userData.component = component;
      hit.material.transparent = true;
      hit.material.opacity = 0;
      hit.material.depthWrite = false;
      hit.material.colorWrite = false;
    }
    return hit;
  }).filter(Boolean);
  if (missingNodes.length) throw new Error(`600S GLB contract failed: ${[...new Set(missingNodes)].join(", ")}`);

  gltf.scene.traverse((node) => {
    if (!node.isMesh || node.userData.is_hit_volume) return;
    node.castShadow = true;
    node.receiveShadow = true;
  });
  gltf.scene.userData.source = `blender-showcase-v${SHOWCASE_RELEASE}`;
  const extras = nodes["600S_ROOT"].userData || {};
  const travel = Number(extras.telescope_travel_m);
  const midTravel = Number(extras.telescope_mid_travel_m);
  const flyTravel = Number(extras.telescope_fly_travel_m);
  if (extras.asset_version !== SHOWCASE_RELEASE || extras.units !== "meters") {
    throw new Error(`600S GLB release contract failed: expected ${SHOWCASE_RELEASE} in meters`);
  }
  if (!Number.isFinite(travel) || Math.abs(travel - TELESCOPE_TRAVEL_M) > 0.001) {
    throw new Error(`600S GLB telescope contract failed: ${travel}`);
  }
  if (!Number.isFinite(midTravel) || Math.abs(midTravel - TELESCOPE_MID_TRAVEL_M) > 0.001 ||
      !Number.isFinite(flyTravel) || Math.abs(flyTravel - TELESCOPE_FLY_TRAVEL_M) > 0.001 ||
      Math.abs(midTravel + flyTravel - travel) > 0.001) {
    throw new Error(`600S GLB coupled telescope contract failed: ${midTravel} + ${flyTravel}`);
  }
  if (nodes.Telescope.userData.runtime_solver !== "evidence_bounded_coupled_visual") {
    throw new Error("600S telescope staging evidence boundary failed");
  }
  if (extras.platform_leveling !== "counter_rotate_local_z") {
    throw new Error("600S GLB platform-leveling contract failed");
  }
  if (extras.configuration_id !== "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696") {
    throw new Error(`600S GLB configuration contract failed: ${extras.configuration_id}`);
  }
  if (nodes.LiftCylinder.userData.runtime_solver !== "two_anchor_visual") {
    throw new Error("600S lift-cylinder solver contract failed");
  }
  tuneBlockoutMaterials(gltf.scene);
  addOwnedPresentationMarkings(nodes);
  const optimization = optimizeDetailedRig(nodes);
  prepareHitVolumes(hitVolumes);
  document.body.dataset.machineVisibleMeshes = String(optimization.visibleMeshes);
  document.body.dataset.machineMergedBuckets = String(optimization.mergedBuckets);
  document.body.dataset.wheelRollHierarchy = [
    [nodes.Wheel_FL_Roll, nodes.Wheel_FL], [nodes.Wheel_FR_Roll, nodes.Wheel_FR],
    [nodes.Wheel_RL_Roll, nodes.Wheel_RL], [nodes.Wheel_RR_Roll, nodes.Wheel_RR],
  ].every(([roll, owner]) => roll.parent === owner) ? "separated" : "invalid";
  document.body.dataset.hoseSolverCount = String([
    nodes.SteerHydraulicHose_L_Flexible, nodes.SteerHydraulicHose_R_Flexible,
  ].filter((node) => node.userData.runtime_solver === "two_anchor_visual_hose").length);
  document.body.dataset.telescopeLayerCueCount = String([
    nodes.BaseBoomExitWearTop, nodes.BaseBoomExitWearBottom, nodes.BaseBoomExitWear_L, nodes.BaseBoomExitWear_R,
    nodes.MidBoomTopPlate, nodes.MidBoomSideReveal_L, nodes.MidBoomSideReveal_R,
    nodes.MidBoomExitWearTop, nodes.MidBoomExitWearBottom, nodes.MidBoomExitWear_L, nodes.MidBoomExitWear_R,
    nodes.FlyBoomTopPlate, nodes.FlyBoomSideReveal_L, nodes.FlyBoomSideReveal_R,
  ].filter(Boolean).length);

  return {
    machine: gltf.scene,
    chassis: nodes.Chassis,
    turntablePivot: nodes.TurntablePivot,
    boomPivot: nodes.BoomPivot,
    telescope: nodes.Telescope,
    midBoom: nodes.MidBoom,
    midBoomHomeX: nodes.MidBoom.position.x,
    flyBoom: nodes.FlyBoom,
    flyBoomHomeX: nodes.FlyBoom.position.x,
    telescopeTravelM: travel,
    telescopeMidTravelM: midTravel,
    telescopeFlyTravelM: flyTravel,
    platformPivot: nodes.PlatformPivot,
    platformMount: nodes.Platform,
    liftCylinder: nodes.LiftCylinder,
    liftCylinderLowerAnchor: nodes.LiftCylinderLowerAnchor,
    liftCylinderUpperAnchor: nodes.LiftCylinderUpperAnchor,
    liftCylinderRod: nodes.LiftCylinderRod,
    liftCylinderRodPin: nodes.LiftCylinderRodPin,
    liftCylinderRodStart: 0.82,
    liftCylinderRodNominalLength: 0.70,
    steeringPivots: [nodes.Wheel_FL, nodes.Wheel_FR],
    steeringTrackM: Math.abs(nodes.Wheel_FL.position.z - nodes.Wheel_FR.position.z),
    rollingWheels: [nodes.Wheel_FL_Roll, nodes.Wheel_FR_Roll, nodes.Wheel_RL_Roll, nodes.Wheel_RR_Roll],
    visualLinks: [
      { group: nodes.TowerLink, lower: nodes.TowerLinkLowerAnchor, upper: nodes.TowerLinkUpperAnchor, body: nodes.TowerLinkBody, nominalLength: 1.0 },
      { group: nodes.TensionLink, lower: nodes.TensionLinkLowerAnchor, upper: nodes.TensionLinkUpperAnchor, body: nodes.TensionLinkBody, nominalLength: 1.0 },
      { group: nodes.SteerTieRod, lower: nodes.SteerTieRodLowerAnchor, upper: nodes.SteerTieRodUpperAnchor, body: nodes.SteerTieRodBody, nominalLength: 1.64 },
    ],
    visualCylinders: [
      { group: nodes.SteerCylinder_L, lower: nodes.SteerCylinder_L_LowerAnchor, upper: nodes.SteerCylinder_L_UpperAnchor, rod: nodes.SteerCylinder_L_Rod, rodStart: 0.32, nominalRodLength: 0.40 },
      { group: nodes.SteerCylinder_R, lower: nodes.SteerCylinder_R_LowerAnchor, upper: nodes.SteerCylinder_R_UpperAnchor, rod: nodes.SteerCylinder_R_Rod, rodStart: 0.32, nominalRodLength: 0.40 },
      { group: nodes.PlatformLevelCylinder, lower: nodes.PlatformLevelCylinderLowerAnchor, upper: nodes.PlatformLevelCylinderUpperAnchor, rod: nodes.PlatformLevelCylinderRod, rodStart: 0.44, nominalRodLength: 0.44 },
    ],
    visualHoses: [
      { group: nodes.SteerHydraulicHose_L_Flexible, lower: nodes.SteerHydraulicHose_L_LowerAnchor, upper: nodes.SteerHydraulicHose_L_UpperAnchor, body: nodes.SteerHydraulicHose_L_Segment_02, nominalLength: Number(nodes.SteerHydraulicHose_L_Flexible.userData.nominal_length_m) },
      { group: nodes.SteerHydraulicHose_R_Flexible, lower: nodes.SteerHydraulicHose_R_LowerAnchor, upper: nodes.SteerHydraulicHose_R_UpperAnchor, body: nodes.SteerHydraulicHose_R_Segment_02, nominalLength: Number(nodes.SteerHydraulicHose_R_Flexible.userData.nominal_length_m) },
    ],
    hitVolumes,
    visibleMeshCount: optimization.visibleMeshes,
    source: `blender-showcase-v${SHOWCASE_RELEASE}`,
  };
}

document.body.dataset.machineSource = "procedural-fallback";
let rig = createProcedural600S();
prepareHitVolumes(rig.hitVolumes);

function loadBlockoutRig() {
  return new Promise((resolve) => {
    const loadTimeout = setTimeout(() => {
      showTerminalError(new Error(`600S asset load exceeded ${ASSET_LOAD_TIMEOUT_MS} ms`), "The evidence-bound 600S asset did not finish loading in time. No substitute was shown.", "load-timeout");
      resolve();
    }, ASSET_LOAD_TIMEOUT_MS);
    loaderStatus.textContent = "Loading equipment model";
    loaderDetail.textContent = "Fetching the optimized 600S detailed reconstruction";
    try {
      new GLTFLoader().load(GLB_URL, (gltf) => {
      clearTimeout(loadTimeout);
      if (terminalFailure) { resolve(); return; }
      try {
        if (globalThis.__EQUIPMENT_EXPLORER_TEST_FAULT__ === "asset-contract") throw new Error("Injected 600S asset-contract failure");
        loaderStatus.textContent = "Preparing materials and shadows";
        loaderDetail.textContent = `Applying the ${renderProfile} render profile`;
        const loadedRig = configureBlockoutRig(gltf);
        if (autonomy.enabled) {
          loadedRig.machine.position.copy(rig.machine.position);
          loadedRig.machine.rotation.y = rig.machine.rotation.y;
        }
        scene.add(loadedRig.machine);
        scene.remove(rig.machine);
        rig = loadedRig;
        document.body.dataset.machineSource = loadedRig.source;
        updateHitVolumeEmphasis();
        updateDiagnostics();
        projectOverview.facts[0] = ["Model", `Blender Showcase reconstruction v${SHOWCASE_RELEASE} · ${loadedRig.visibleMeshCount} runtime meshes`];
      } catch (error) {
        showTerminalError(error, "The evidence-bound 600S asset failed its hierarchy or motion contract. No substitute was shown.", "contract-failed");
      }
      resolve();
    }, (event) => {
      if (event.total > 0) {
        const progress = Math.min(100, Math.round((event.loaded / event.total) * 100));
        loaderDetail.textContent = `${progress}% · ${(event.loaded / 1024).toFixed(0)} KB`;
      } else {
        loaderDetail.textContent = `${(event.loaded / 1024).toFixed(0)} KB received`;
      }
    }, (error) => {
      clearTimeout(loadTimeout);
      showTerminalError(error, "The evidence-bound 600S asset could not be loaded. No procedural substitute was used.", "load-failed");
      resolve();
      });
    } catch (error) {
      clearTimeout(loadTimeout);
      showTerminalError(error, "The evidence-bound 600S asset loader could not start. No procedural substitute was used.", "loader-start-failed");
      resolve();
    }
  });
}

const machineState = { boomAngle: 0, telescope: 0, turntableAngle: 0, steeringAngle: 0 };
const targets = { ...machineState };
const inputs = {
  boomAngle: document.querySelector("#boom-control"),
  telescope: document.querySelector("#extend-control"),
  turntableAngle: document.querySelector("#rotate-control"),
  steeringAngle: document.querySelector("#steer-control"),
};
const outputs = {
  boomAngle: document.querySelector("#boom-value"),
  telescope: document.querySelector("#extend-value"),
  turntableAngle: document.querySelector("#rotate-value"),
  steeringAngle: document.querySelector("#steer-value"),
};
const motionStatus = document.querySelector("#motion-status");
const autonomyToggle = document.querySelector("#autonomy-toggle");
const autonomyMode = document.querySelector("#autonomy-mode");
const autonomyNote = document.querySelector("#autonomy-note");
const driveHeadingOutput = document.querySelector("#drive-heading");
const driveLoopOutput = document.querySelector("#drive-loop");
let lastMotionStatus = motionStatus.value || motionStatus.textContent;
const suffixes = { boomAngle: "°", telescope: "%", turntableAngle: "°", steeringAngle: "°" };
const controlNames = { boomAngle: "Boom", telescope: "Extend", turntableAngle: "Rotate", steeringAngle: "Steer" };
const fixedPoseQuery = ["boom", "extend", "rotate", "steer"].some((key) => query.has(key));
let autonomyLocked = reducedMotion || fixedPoseQuery;
const autonomy = {
  enabled: !autonomyLocked && query.get("auto") !== "0",
  phase: 0,
  activeControl: null,
  overrideUntil: Object.fromEntries(Object.keys(targets).map((key) => [key, 0])),
  wheelRotation: 0,
  x: 0,
  z: 0,
  heading: 0,
  routeError: 0,
};
const AUTONOMY_OVERRIDE_MS = 6000;
const AUTONOMY_PATH = {
  radiusX: 7.5,
  radiusZ: 6.5,
  centerZ: -6.5,
  speed: 0.72,
  lookaheadPhase: 0.25,
  wheelbase: 2.5,
  wheelRadius: 0.62,
};

function setMotionStatus(value) {
  if (value === lastMotionStatus) return;
  lastMotionStatus = value;
  motionStatus.value = value;
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

Object.entries(inputs).forEach(([key, input]) => {
  input.addEventListener("pointerdown", () => { autonomy.activeControl = key; });
  const releaseControl = () => {
    if (autonomy.activeControl === key) autonomy.activeControl = null;
  };
  input.addEventListener("pointerup", releaseControl);
  input.addEventListener("pointercancel", releaseControl);
  input.addEventListener("change", releaseControl);
  input.addEventListener("input", () => {
    targets[key] = Number(input.value);
    if (autonomy.enabled) autonomy.overrideUntil[key] = performance.now() + AUTONOMY_OVERRIDE_MS;
    outputs[key].value = `${Math.round(targets[key])}${suffixes[key]}`;
    setEngineeringValueText(input, outputs[key].value);
    setMotionStatus(autonomy.enabled ? "Manual override" : "Positioning");
  });
});

function syncInputs() {
  Object.entries(inputs).forEach(([key, input]) => {
    input.value = String(Math.round(targets[key]));
    outputs[key].value = `${Math.round(targets[key])}${suffixes[key]}`;
    setEngineeringValueText(input, outputs[key].value);
  });
}

function applyQueryPose() {
  const params = new URLSearchParams(location.search);
  const mapping = { boom: "boomAngle", extend: "telescope", rotate: "turntableAngle", steer: "steeringAngle" };
  Object.entries(mapping).forEach(([query, key]) => {
    if (!params.has(query)) return;
    const value = Number(params.get(query));
    if (!Number.isFinite(value)) return;
    const input = inputs[key];
    targets[key] = THREE.MathUtils.clamp(value, Number(input.min), Number(input.max));
  });
  syncInputs();
}
applyQueryPose();

function activeOverrideKeys(now = performance.now()) {
  return Object.keys(targets).filter((key) => autonomy.activeControl === key || now < autonomy.overrideUntil[key]);
}

function activeOverrideKey(now = performance.now()) {
  return activeOverrideKeys(now)[0] || null;
}

function normalizedHeadingDegrees(radians) {
  return (Math.round(THREE.MathUtils.radToDeg(radians)) + 360) % 360;
}

function updateAutonomyTelemetry(now = performance.now()) {
  const overrideKeys = autonomy.enabled ? activeOverrideKeys(now) : [];
  const recovering = autonomy.enabled && !overrideKeys.length && autonomy.routeError > 0.6;
  const overrideLabel = overrideKeys.map((key) => controlNames[key]).join(" + ");
  const mode = autonomyLocked ? "Static pose" : autonomy.enabled ? overrideKeys.length ? `Override · ${overrideLabel}` : recovering ? "Route recovery" : "Auto loop" : "Manual";
  if (autonomyMode.value !== mode) autonomyMode.value = mode;
  const note = autonomyLocked
    ? reducedMotion ? "Reduced motion keeps the route stationary." : "Query poses keep the route stationary."
    : autonomy.enabled ? recovering ? "Steering back onto the presentation route." : "Move a slider for a 6 s override." : "All machine controls are live.";
  if (autonomyNote.textContent !== note) autonomyNote.textContent = note;
  const heading = `${String(normalizedHeadingDegrees(autonomy.heading)).padStart(3, "0")}°`;
  const loop = `${Math.round((autonomy.phase / (Math.PI * 2)) * 100)}%`;
  if (driveHeadingOutput.value !== heading) driveHeadingOutput.value = heading;
  if (driveLoopOutput.value !== loop) driveLoopOutput.value = loop;
  autonomyToggle.disabled = autonomyLocked;
  const pressed = String(autonomy.enabled);
  if (autonomyToggle.getAttribute("aria-pressed") !== pressed) autonomyToggle.setAttribute("aria-pressed", pressed);
  const buttonLabel = autonomyLocked ? "Static" : autonomy.enabled ? "Pause auto" : "Start auto";
  if (autonomyToggle.textContent !== buttonLabel) autonomyToggle.textContent = buttonLabel;
  document.body.dataset.autonomyMode = autonomyLocked ? "static" : autonomy.enabled ? overrideKeys.length ? "override" : recovering ? "recovering" : "auto" : "manual";
  document.body.dataset.autonomyOverrides = overrideKeys.join(",") || "none";
  document.body.dataset.driveHeading = String(normalizedHeadingDegrees(autonomy.heading));
  document.body.dataset.driveLoop = String(Math.round((autonomy.phase / (Math.PI * 2)) * 100));
  document.body.dataset.driveRouteErrorM = autonomy.routeError.toFixed(2);
}

function setAutonomyEnabled(enabled) {
  autonomy.enabled = Boolean(enabled) && !autonomyLocked;
  autonomy.activeControl = null;
  Object.keys(autonomy.overrideUntil).forEach((key) => { autonomy.overrideUntil[key] = 0; });
  setMotionStatus(autonomy.enabled ? "Autonomous" : "Manual");
  updateAutonomyTelemetry();
}

function syncReducedMotion(announce = false) {
  const nextReducedMotion = forceReducedMotion || Boolean(motionPreference?.matches);
  const changed = nextReducedMotion !== reducedMotion;
  const wasAutonomous = autonomy.enabled;
  reducedMotion = nextReducedMotion;
  autonomyLocked = reducedMotion || fixedPoseQuery;
  document.body.dataset.reducedMotion = String(reducedMotion);
  if (reducedMotion) {
    Object.keys(targets).forEach((key) => { targets[key] = machineState[key]; });
    orbit.vTheta = 0;
    orbit.vPhi = 0;
    setAutonomyEnabled(false);
    syncInputs();
    if (announce && changed) setMotionStatus(wasAutonomous ? "Reduced motion · auto stopped" : "Reduced motion");
  } else {
    updateAutonomyTelemetry();
    if (announce && changed) setMotionStatus(autonomyLocked ? "Static query pose" : "Manual · auto available");
  }
  updateDiagnostics();
}

const handleMotionPreferenceChange = () => syncReducedMotion(true);
if (motionPreference?.addEventListener) motionPreference.addEventListener("change", handleMotionPreferenceChange);
else motionPreference?.addListener?.(handleMotionPreferenceChange);

autonomyToggle.addEventListener("click", () => setAutonomyEnabled(!autonomy.enabled));
updateAutonomyTelemetry();

document.querySelector("#stow").addEventListener("click", () => {
  setAutonomyEnabled(false);
  Object.keys(targets).forEach((key) => { targets[key] = 0; });
  autonomy.phase = 0;
  autonomy.x = 0;
  autonomy.z = 0;
  autonomy.heading = 0;
  autonomy.routeError = 0;
  autonomy.wheelRotation = 0;
  rig.machine.position.set(0, 0, 0);
  rig.machine.rotation.y = 0;
  document.body.dataset.driveX = "0.00";
  document.body.dataset.driveZ = "0.00";
  syncInputs();
  resetView();
  updateAutonomyTelemetry();
});

function defaultOrbitRadius() {
  return innerWidth <= 800 ? 24 : 18;
}

function adaptiveOrbitRadius(telescope = 0) {
  const telescopeProgress = THREE.MathUtils.clamp(telescope / 100, 0, 1);
  return defaultOrbitRadius() + telescopeProgress * (innerWidth <= 800 ? 10 : 2);
}

function defaultOrbitTargetY(boomAngle = 0) {
  return 1.85 + Math.sin(THREE.MathUtils.degToRad(boomAngle)) * 3.0;
}

function defaultOrbitTargetPose(state = machineState) {
  const telescopeProgress = THREE.MathUtils.clamp(state.telescope / 100, 0, 1);
  const displayTravel = rig?.telescopeTravelM || TELESCOPE_TRAVEL_M;
  const boomHeading = autonomy.heading + THREE.MathUtils.degToRad(state.turntableAngle);
  const longitudinalOffset = 0.8 + telescopeProgress * displayTravel * 0.72;
  return new THREE.Vector3(
    rig.machine.position.x + Math.cos(boomHeading) * longitudinalOffset,
    defaultOrbitTargetY(state.boomAngle) + Math.sin(THREE.MathUtils.degToRad(state.boomAngle)) * telescopeProgress * displayTravel * 0.18,
    rig.machine.position.z - Math.sin(boomHeading) * longitudinalOffset
  );
}

const orbit = {
  theta: 0.76,
  phi: 1.44,
  radius: defaultOrbitRadius(),
  target: new THREE.Vector3(0.8, defaultOrbitTargetY(), 0),
  targetGoal: new THREE.Vector3(0.8, defaultOrbitTargetY(), 0),
  radiusGoal: defaultOrbitRadius(),
  vTheta: 0,
  vPhi: 0,
  dragging: false,
  moved: false,
  userZoomed: false,
  lastX: 0,
  lastY: 0,
  idle: 0,
  pinch: 0,
  pinchRadius: defaultOrbitRadius(),
};
const canvas = renderer.domElement;
document.body.dataset.canvasInteraction = "navigation-only";
const pointers = new Map();
let focusedComponent = null;
let hoveredHit = null;

canvas.addEventListener("contextmenu", (event) => event.preventDefault());
canvas.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 && event.pointerType !== "touch") return;
  event.preventDefault();
  app.focus({ preventScroll: true });
  pointers.set(event.pointerId, [event.clientX, event.clientY]);
  orbit.idle = 0;
  orbit.moved = false;
  try { canvas.setPointerCapture(event.pointerId); } catch {}
  if (pointers.size === 1) {
    orbit.dragging = true;
    orbit.lastX = event.clientX;
    orbit.lastY = event.clientY;
  } else {
    const active = [...pointers.values()];
    orbit.dragging = false;
    orbit.pinch = Math.hypot(active[0][0] - active[1][0], active[0][1] - active[1][1]) || 1;
    orbit.pinchRadius = orbit.radiusGoal;
  }
}, { passive: false });

canvas.addEventListener("pointermove", (event) => {
  event.preventDefault();
  if (!pointers.size) {
    const hit = hitComponentAt(event.clientX, event.clientY);
    hoveredHit = hit?.object ?? null;
    updateHitVolumeEmphasis(hoveredHit);
    canvas.style.cursor = "grab";
    return;
  }
  if (pointers.has(event.pointerId)) pointers.set(event.pointerId, [event.clientX, event.clientY]);
  if (pointers.size >= 2) {
    const active = [...pointers.values()];
    const distance = Math.hypot(active[0][0] - active[1][0], active[0][1] - active[1][1]);
    orbit.radiusGoal = THREE.MathUtils.clamp(orbit.pinchRadius * orbit.pinch / distance, 7, 38);
    orbit.userZoomed = true;
    orbit.idle = 0;
    return;
  }
  if (!orbit.dragging) return;
  const dx = event.clientX - orbit.lastX;
  const dy = event.clientY - orbit.lastY;
  orbit.lastX = event.clientX;
  orbit.lastY = event.clientY;
  orbit.moved ||= Math.abs(dx) + Math.abs(dy) > 3;
  orbit.theta -= dx * 0.0045;
  orbit.phi = THREE.MathUtils.clamp(orbit.phi - dy * 0.0035, 0.42, 1.48);
  orbit.vTheta = -dx * 0.0036;
  orbit.vPhi = -dy * 0.0028;
  orbit.idle = 0;
}, { passive: false });

function endPointer(event) {
  pointers.delete(event.pointerId);
  try { canvas.releasePointerCapture(event.pointerId); } catch {}
  orbit.dragging = false;
  orbit.pinch = 0;
  hoveredHit = null;
  updateHitVolumeEmphasis();
  canvas.style.cursor = "grab";
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("pointerleave", () => {
  if (pointers.size) return;
  hoveredHit = null;
  updateHitVolumeEmphasis();
  canvas.style.cursor = "grab";
});
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  orbit.radiusGoal = THREE.MathUtils.clamp(orbit.radiusGoal * Math.exp(event.deltaY * 0.0012), 7, 38);
  orbit.userZoomed = true;
  orbit.idle = 0;
}, { passive: false });

function resetView() {
  focusedComponent = null;
  document.querySelectorAll("[data-focus]").forEach((button) => {
    button.classList.remove("active");
    button.setAttribute("aria-pressed", "false");
  });
  orbit.targetGoal.copy(defaultOrbitTargetPose(targets));
  orbit.radiusGoal = adaptiveOrbitRadius(targets.telescope);
  orbit.userZoomed = false;
  orbit.theta = 0.76;
  orbit.phi = 1.44;
  orbit.vTheta = 0;
  orbit.vPhi = 0;
  updateHitVolumeEmphasis(hoveredHit);
}
document.querySelector("#reset-view").addEventListener("click", resetView);

app.addEventListener("keydown", (event) => {
  const focusKeys = { "1": "chassis", "2": "turntable", "3": "boom", "4": "platform" };
  let handled = true;
  if (event.key === "ArrowLeft") orbit.theta -= 0.12;
  else if (event.key === "ArrowRight") orbit.theta += 0.12;
  else if (event.key === "ArrowUp") orbit.phi = THREE.MathUtils.clamp(orbit.phi - 0.08, 0.42, 1.48);
  else if (event.key === "ArrowDown") orbit.phi = THREE.MathUtils.clamp(orbit.phi + 0.08, 0.42, 1.48);
  else if (event.key === "+" || event.key === "=") { orbit.radiusGoal = THREE.MathUtils.clamp(orbit.radiusGoal - 1.2, 7, 38); orbit.userZoomed = true; }
  else if (event.key === "-" || event.key === "_") { orbit.radiusGoal = THREE.MathUtils.clamp(orbit.radiusGoal + 1.2, 7, 38); orbit.userZoomed = true; }
  else if (focusKeys[event.key]) focusComponent(focusKeys[event.key]);
  else if (event.key === "0") resetView();
  else handled = false;
  if (!handled) return;
  event.preventDefault();
  orbit.idle = 0;
});

const componentContent = {
  chassis: {
    title: "Chassis",
    copy: "The mobile base carries the axles, steering assemblies, lower controls, and the rotating upper structure.",
    facts: [["Visible system", "Frame, axles, drive hubs, wheels, two moving steer cylinders, tie rod, and deck"], ["Configuration", "4WD hydrostatic with two-wheel front steer"], ["Boundary", "Steering anchors and angles remain visual reconstructions"]],
    radius: 8.5,
  },
  turntable: {
    title: "Turntable",
    copy: "The upper structure rotates around the slew axis while carrying the counterweight, power enclosure, and boom assembly.",
    facts: [["Visible system", "B3 hoods, counterweight, slew ring, tanks, controls, valve and harness cues"], ["Motion", "Interactive rotation around the vertical axis"], ["Boundary", "No stability, pressure, or collision calculation"]],
    radius: 8,
  },
  boom: {
    title: "Telescopic boom",
    copy: "The primary lifting structure changes elevation at its base pivot while separate Mid and Fly sleeves extend the platform outward.",
    facts: [["Motion", "Lift, coupled Mid/Fly staging, moving tower/tension links, and carrier travel"], ["Hierarchy", "BoomPivot → MainBoom → Telescope controller → MidBoom → FlyBoom"], ["Boundary", "The 3.80 m display cap and 1.52 / 2.28 m stage split are reconstructions, not JLG stroke data"]],
    radius: 9.5,
  },
  platform: {
    title: "Platform",
    copy: "The work platform is parented to the telescoping section so it follows the boom through elevation, extension, and swing.",
    facts: [["Visible system", "Rapid-replace support, load-cell cue, rotator, level cylinder, deck, controls, SkyGuard, and labels"], ["Hierarchy", "FlyBoom → rotator/level linkage → PlatformPivot → Platform"], ["Leveling", "Visual starting-angle retention; not automatic leveling to gravity"]],
    radius: 6.2,
  },
};

const inspector = document.querySelector("#inspector");
const infoToggle = document.querySelector("#info-toggle");
const inspectorClose = document.querySelector("#inspector-close");
let focusBeforeInspector = null;
const projectOverview = {
  kicker: "Project note",
  title: "A visual replica,<br>not an engineering model.",
  copy: "This unofficial study is designed to explain visible product systems through a simplified, interactive model based on public reference material.",
  facts: [["Model", "Loading Blender detailed reconstruction"], ["Purpose", "Portfolio and educational visualization"], ["Boundary", "Not a service, training, fabrication, or safety reference"]],
};
function openInspector(component) {
  if (!document.body.classList.contains("inspector-open")) focusBeforeInspector = document.activeElement;
  if (component) {
    const data = componentContent[component];
    document.querySelector("#inspector-kicker").textContent = "Component view";
    document.querySelector("#inspector-title").innerHTML = data.title;
    document.querySelector("#inspector-copy").textContent = data.copy;
    document.querySelector("#inspector-facts").innerHTML = data.facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join("");
  } else {
    document.querySelector("#inspector-kicker").textContent = projectOverview.kicker;
    document.querySelector("#inspector-title").innerHTML = projectOverview.title;
    document.querySelector("#inspector-copy").textContent = projectOverview.copy;
    document.querySelector("#inspector-facts").innerHTML = projectOverview.facts.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join("");
  }
  document.body.classList.add("inspector-open");
  inspector.inert = false;
  infoToggle.setAttribute("aria-expanded", "true");
  requestAnimationFrame(() => inspectorClose.focus());
}
function closeInspector() {
  if (!document.body.classList.contains("inspector-open")) return;
  document.body.classList.remove("inspector-open");
  inspector.inert = true;
  infoToggle.setAttribute("aria-expanded", "false");
  const restoreTarget = focusBeforeInspector;
  focusBeforeInspector = null;
  if (restoreTarget instanceof HTMLElement) restoreTarget.focus({ preventScroll: true });
}
infoToggle.addEventListener("click", () => openInspector());
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
  const focusable = [...inspector.querySelectorAll("button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex='-1'])")];
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
});

function focusComponent(component) {
  setAutonomyEnabled(false);
  focusedComponent = component;
  document.querySelectorAll("[data-focus]").forEach((button) => {
    const selected = button.dataset.focus === component;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  const worldPosition = new THREE.Vector3();
  const node = component === "chassis" ? rig.chassis : component === "turntable" ? rig.turntablePivot : component === "boom" ? rig.boomPivot : rig.platformMount;
  node.updateWorldMatrix(true, true);
  node.getWorldPosition(worldPosition);
  if (component === "platform") worldPosition.y += 0.2;
  let componentRadius = componentContent[component].radius;
  if (component === "boom") {
    const bounds = new THREE.Box3().setFromObject(node);
    const size = bounds.getSize(new THREE.Vector3());
    bounds.getCenter(worldPosition);
    const halfFovTangent = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    const verticalRadius = size.y / Math.max(2 * halfFovTangent, 0.001);
    const horizontalRadius = size.x / Math.max(2 * halfFovTangent * camera.aspect, 0.001);
    componentRadius = THREE.MathUtils.clamp(Math.max(componentRadius, verticalRadius, horizontalRadius) * 1.12, 7, 38);
  }
  orbit.targetGoal.copy(worldPosition);
  orbit.radiusGoal = componentRadius;
  orbit.userZoomed = false;
  orbit.idle = 0;
  updateHitVolumeEmphasis(hoveredHit);
  openInspector(component);
}
document.querySelectorAll("[data-focus]").forEach((button) => button.addEventListener("click", () => focusComponent(button.dataset.focus)));

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const selectionPriority = {
  Platform_Hit: 4,
  Telescope_Hit: 3,
  Boom_Hit: 2,
  Turntable_Hit: 1,
  Chassis_Hit: 0,
};
function hitComponentAt(x, y) {
  const rect = canvas.getBoundingClientRect();
  pointer.set(((x - rect.left) / rect.width) * 2 - 1, -((y - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const intersection = raycaster.intersectObjects(rig.hitVolumes, false)
    .sort((a, b) => (selectionPriority[b.object.name] - selectionPriority[a.object.name]) || a.distance - b.distance)[0];
  return intersection ? { component: intersection.object.userData.component, object: intersection.object, intersection } : null;
}

function runSelectionVolumeSelfTest() {
  rig.machine.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const selfTestRaycaster = new THREE.Raycaster();
  const center = new THREE.Vector3();
  let passed = 0;
  rig.hitVolumes.forEach((hit) => {
    new THREE.Box3().setFromObject(hit).getCenter(center);
    const projected = center.clone().project(camera);
    selfTestRaycaster.setFromCamera(new THREE.Vector2(projected.x, projected.y), camera);
    const intersection = selfTestRaycaster.intersectObjects([hit], false)[0];
    const expected = interactionComponents[hit.name];
    if (intersection?.object === hit && hit.userData.component === expected) passed += 1;
  });
  const total = rig.hitVolumes.length;
  const result = total === 5 && passed === total ? "pass" : "fail";
  document.body.dataset.selectionSelftest = result;
  runtimeDiagnostics.selectionHits = `${passed}/${total} ${result}`;
  updateDiagnostics();
  return result === "pass";
}

const cylinderLowerWorld = new THREE.Vector3();
const cylinderUpperWorld = new THREE.Vector3();
const cylinderLowerLocal = new THREE.Vector3();
const cylinderUpperLocal = new THREE.Vector3();
const cylinderDirection = new THREE.Vector3();
const cylinderAxis = new THREE.Vector3(1, 0, 0);

function updateLiftCylinder() {
  const cylinder = rig.liftCylinder;
  const lowerAnchor = rig.liftCylinderLowerAnchor;
  const upperAnchor = rig.liftCylinderUpperAnchor;
  if (!cylinder || !lowerAnchor || !upperAnchor || !cylinder.parent) return;

  rig.machine.updateMatrixWorld(true);
  lowerAnchor.getWorldPosition(cylinderLowerWorld);
  upperAnchor.getWorldPosition(cylinderUpperWorld);
  cylinderLowerLocal.copy(cylinderLowerWorld);
  cylinderUpperLocal.copy(cylinderUpperWorld);
  cylinder.parent.worldToLocal(cylinderLowerLocal);
  cylinder.parent.worldToLocal(cylinderUpperLocal);
  cylinderDirection.subVectors(cylinderUpperLocal, cylinderLowerLocal);
  const solvedLength = cylinderDirection.length();
  if (solvedLength < 0.001) return;

  const rodLength = Math.max(0.2, solvedLength - rig.liftCylinderRodStart);
  cylinder.position.copy(cylinderLowerLocal);
  cylinder.quaternion.setFromUnitVectors(cylinderAxis, cylinderDirection.normalize());
  cylinder.scale.set(1, 1, 1);
  rig.liftCylinderRod.position.x = rig.liftCylinderRodStart + rodLength * 0.5;
  rig.liftCylinderRod.scale.set(1, 1, rodLength / rig.liftCylinderRodNominalLength);
  rig.liftCylinderRodPin.position.x = solvedLength;
}

function solveVisualLink(link) {
  if (!link?.group || !link.lower || !link.upper || !link.body || !link.group.parent) return;
  link.lower.getWorldPosition(cylinderLowerWorld);
  link.upper.getWorldPosition(cylinderUpperWorld);
  cylinderLowerLocal.copy(cylinderLowerWorld);
  cylinderUpperLocal.copy(cylinderUpperWorld);
  link.group.parent.worldToLocal(cylinderLowerLocal);
  link.group.parent.worldToLocal(cylinderUpperLocal);
  cylinderDirection.subVectors(cylinderUpperLocal, cylinderLowerLocal);
  const solvedLength = cylinderDirection.length();
  if (solvedLength < 0.001) return;
  link.group.position.copy(cylinderLowerLocal);
  link.group.quaternion.setFromUnitVectors(cylinderAxis, cylinderDirection.normalize());
  link.group.scale.set(1, 1, 1);
  link.body.position.x = solvedLength * 0.5;
  link.body.scale.set(1, 1, solvedLength / link.nominalLength);
}

function solveVisualCylinder(cylinder) {
  if (!cylinder?.group || !cylinder.lower || !cylinder.upper || !cylinder.rod || !cylinder.group.parent) return;
  cylinder.lower.getWorldPosition(cylinderLowerWorld);
  cylinder.upper.getWorldPosition(cylinderUpperWorld);
  cylinderLowerLocal.copy(cylinderLowerWorld);
  cylinderUpperLocal.copy(cylinderUpperWorld);
  cylinder.group.parent.worldToLocal(cylinderLowerLocal);
  cylinder.group.parent.worldToLocal(cylinderUpperLocal);
  cylinderDirection.subVectors(cylinderUpperLocal, cylinderLowerLocal);
  const solvedLength = cylinderDirection.length();
  if (solvedLength < 0.001) return;
  const rodLength = Math.max(0.12, solvedLength - cylinder.rodStart);
  cylinder.group.position.copy(cylinderLowerLocal);
  cylinder.group.quaternion.setFromUnitVectors(cylinderAxis, cylinderDirection.normalize());
  cylinder.group.scale.set(1, 1, 1);
  cylinder.rod.position.x = cylinder.rodStart + rodLength * 0.5;
  cylinder.rod.scale.set(1, 1, rodLength / cylinder.nominalRodLength);
}

function updateEvidenceBoundedLinkages() {
  if (!rig.machine) return;
  rig.machine.updateMatrixWorld(true);
  rig.visualLinks?.forEach(solveVisualLink);
  rig.visualHoses?.forEach(solveVisualLink);
  rig.visualCylinders?.forEach(solveVisualCylinder);
}

function ackermannSteeringAngles(centerAngleDegrees) {
  const centerAngle = THREE.MathUtils.degToRad(centerAngleDegrees);
  if (Math.abs(centerAngle) < 0.0001) return [0, 0];
  const wheelbase = AUTONOMY_PATH.wheelbase;
  const halfTrack = Math.max(0.1, (rig.steeringTrackM || 2.08) * 0.5);
  const turnRadius = Math.abs(wheelbase / Math.tan(centerAngle));
  const visualLimit = THREE.MathUtils.degToRad(28);
  const inner = Math.min(visualLimit, Math.atan(wheelbase / Math.max(0.2, turnRadius - halfTrack)));
  const outer = Math.min(visualLimit, Math.atan(wheelbase / (turnRadius + halfTrack)));
  if (centerAngle > 0) return [inner, outer];
  return [-outer, -inner];
}

const lightingAnchor = new THREE.Vector3();
function updatePresentationLighting() {
  if (!rig?.machine) return;
  rig.machine.getWorldPosition(lightingAnchor);
  lightingAnchor.y += 1.35;
  lightTarget.position.copy(lightingAnchor);
  key.position.copy(lightingAnchor).add(keyOffset);
  fill.position.copy(lightingAnchor).add(fillOffset);
  rim.position.copy(lightingAnchor).add(rimOffset);
  lightTarget.updateMatrixWorld();
}

function updateAutonomy(dt, now) {
  if (!autonomy.enabled) {
    updateAutonomyTelemetry(now);
    return;
  }

  autonomy.phase = Math.atan2(
    autonomy.x / AUTONOMY_PATH.radiusX,
    (autonomy.z - AUTONOMY_PATH.centerZ) / AUTONOMY_PATH.radiusZ
  );
  if (autonomy.phase < 0) autonomy.phase += Math.PI * 2;
  const phase = autonomy.phase;
  const dx = AUTONOMY_PATH.radiusX * Math.cos(phase);
  const dz = -AUTONOMY_PATH.radiusZ * Math.sin(phase);
  const ddx = -AUTONOMY_PATH.radiusX * Math.sin(phase);
  const ddz = -AUTONOMY_PATH.radiusZ * Math.cos(phase);
  const derivativeLength = Math.max(0.001, Math.hypot(dx, dz));
  const curvature = (dx * ddz - dz * ddx) / Math.pow(derivativeLength, 3);

  const lookaheadPhase = phase + AUTONOMY_PATH.lookaheadPhase;
  const targetX = AUTONOMY_PATH.radiusX * Math.sin(lookaheadPhase);
  const targetZ = AUTONOMY_PATH.centerZ + AUTONOMY_PATH.radiusZ * Math.cos(lookaheadPhase);
  const desiredHeading = Math.atan2(-(targetZ - autonomy.z), targetX - autonomy.x);
  const headingError = Math.atan2(
    Math.sin(desiredHeading - autonomy.heading),
    Math.cos(desiredHeading - autonomy.heading)
  );
  const steeringCommand = THREE.MathUtils.clamp(
    THREE.MathUtils.radToDeg(Math.atan(-AUTONOMY_PATH.wheelbase * curvature) + headingError),
    -24,
    24
  );

  const driveSpeed = activeOverrideKeys(now).includes("steeringAngle") ? 0.2 : AUTONOMY_PATH.speed;
  autonomy.heading += (driveSpeed / AUTONOMY_PATH.wheelbase) *
    Math.tan(THREE.MathUtils.degToRad(machineState.steeringAngle)) * dt;
  autonomy.x += Math.cos(autonomy.heading) * driveSpeed * dt;
  autonomy.z -= Math.sin(autonomy.heading) * driveSpeed * dt;
  const projectedPhase = Math.atan2(
    autonomy.x / AUTONOMY_PATH.radiusX,
    (autonomy.z - AUTONOMY_PATH.centerZ) / AUTONOMY_PATH.radiusZ
  );
  const routePhase = projectedPhase < 0 ? projectedPhase + Math.PI * 2 : projectedPhase;
  const routeX = AUTONOMY_PATH.radiusX * Math.sin(routePhase);
  const routeZ = AUTONOMY_PATH.centerZ + AUTONOMY_PATH.radiusZ * Math.cos(routePhase);
  autonomy.routeError = Math.hypot(autonomy.x - routeX, autonomy.z - routeZ);

  autonomy.wheelRotation -= (driveSpeed * dt) / AUTONOMY_PATH.wheelRadius;
  rig.machine.position.x = autonomy.x;
  rig.machine.position.z = autonomy.z;
  rig.machine.rotation.y = autonomy.heading;

  const commands = {
    boomAngle: 21 + Math.sin(phase - 0.6) * 8,
    telescope: 60 + Math.sin(phase * 2 + 0.8) * 32,
    turntableAngle: Math.sin(phase + 1.2) * 34,
    steeringAngle: steeringCommand,
  };
  Object.keys(targets).forEach((key) => {
    if (autonomy.activeControl === key || now < autonomy.overrideUntil[key]) return;
    targets[key] = THREE.MathUtils.damp(targets[key], commands[key], key === "steeringAngle" ? 8 : 2.8, dt);
  });
  syncInputs();
  updateAutonomyTelemetry(now);
  document.body.dataset.driveX = autonomy.x.toFixed(2);
  document.body.dataset.driveZ = autonomy.z.toFixed(2);
}

function updateRig(dt) {
  Object.keys(machineState).forEach((key) => {
    machineState[key] = reducedMotion ? targets[key] : THREE.MathUtils.damp(machineState[key], targets[key], 6, dt);
  });
  rig.boomPivot.rotation.z = THREE.MathUtils.degToRad(machineState.boomAngle);
  if (rig.platformPivot) rig.platformPivot.rotation.z = -THREE.MathUtils.degToRad(machineState.boomAngle);
  const telescopeProgress = machineState.telescope / 100;
  if (rig.midBoom && rig.flyBoom) {
    rig.midBoom.position.x = rig.midBoomHomeX + telescopeProgress * rig.telescopeMidTravelM;
    rig.flyBoom.position.x = rig.flyBoomHomeX + telescopeProgress * rig.telescopeFlyTravelM;
  } else {
    rig.telescope.position.x = rig.telescopeHomeX + telescopeProgress * rig.telescopeTravelM;
  }
  rig.turntablePivot.rotation.y = THREE.MathUtils.degToRad(machineState.turntableAngle);
  const steerAngles = ackermannSteeringAngles(machineState.steeringAngle);
  rig.steeringPivots.forEach((pivot, index) => { pivot.rotation.y = steerAngles[index] ?? 0; });
  rig.rollingWheels?.forEach((pivot) => { pivot.rotation.z = autonomy.wheelRotation; });
  document.body.dataset.steerLeftDeg = THREE.MathUtils.radToDeg(steerAngles[0] || 0).toFixed(1);
  document.body.dataset.steerRightDeg = THREE.MathUtils.radToDeg(steerAngles[1] || 0).toFixed(1);
  updateLiftCylinder();
  updateEvidenceBoundedLinkages();
  if (!focusedComponent) {
    orbit.targetGoal.copy(defaultOrbitTargetPose());
    if (!orbit.userZoomed) orbit.radiusGoal = adaptiveOrbitRadius(machineState.telescope);
  }
  const moving = Object.keys(machineState).some((key) => Math.abs(machineState[key] - targets[key]) > 0.1);
  const stowed = Object.values(targets).every((value) => Math.abs(value) < 0.1);
  const overrideKey = autonomy.enabled ? activeOverrideKey() : null;
  setMotionStatus(autonomy.enabled ? overrideKey ? "Manual override" : autonomy.routeError > 0.6 ? "Route recovery" : "Autonomous" : moving ? "Positioning" : stowed ? "Stowed" : "Holding");
}

function updateCamera(dt) {
  if (!orbit.dragging && !reducedMotion) {
    orbit.theta += orbit.vTheta;
    orbit.phi = THREE.MathUtils.clamp(orbit.phi + orbit.vPhi, 0.42, 1.48);
    orbit.vTheta *= 0.91;
    orbit.vPhi *= 0.91;
  }
  if (reducedMotion) {
    orbit.vTheta = 0;
    orbit.vPhi = 0;
  }
  orbit.idle += dt;
  if (orbit.idle > 4 && !reducedMotion) orbit.theta += dt * 0.025;
  if (reducedMotion) {
    orbit.radius = orbit.radiusGoal;
    orbit.target.copy(orbit.targetGoal);
  } else {
    orbit.radius = THREE.MathUtils.damp(orbit.radius, orbit.radiusGoal, 5, dt);
    orbit.target.lerp(orbit.targetGoal, 1 - Math.exp(-5 * dt));
  }
  document.body.dataset.orbitCameraDistanceM = orbit.radius.toFixed(3);
  document.body.dataset.orbitDesiredDistanceM = orbit.radiusGoal.toFixed(3);
  const sinPhi = Math.sin(orbit.phi);
  camera.position.set(
    orbit.target.x + orbit.radius * sinPhi * Math.sin(orbit.theta),
    orbit.target.y + orbit.radius * Math.cos(orbit.phi),
    orbit.target.z + orbit.radius * sinPhi * Math.cos(orbit.theta)
  );
  camera.lookAt(orbit.target);
}

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(innerWidth, innerHeight);
  updateMobileControlHeight();
});

const clock = new THREE.Clock();
let lastRenderedAt = 0;
let collectFrameSamples = false;
const frameSamples = [];
function animate(now = 0) {
  if (terminalFailure) return;
  animationFrameId = requestAnimationFrame(animate);
  runtimeFrameCount += 1;
  document.body.dataset.runtimeFrameCount = String(runtimeFrameCount);
  document.body.dataset.runtimeLastFrameMs = Number(now).toFixed(3);
  if (document.hidden) {
    clock.getDelta();
    return;
  }
  if (minimumFrameInterval && now - lastRenderedAt < minimumFrameInterval) return;
  const renderedInterval = lastRenderedAt ? now - lastRenderedAt : 0;
  lastRenderedAt = now;
  const dt = Math.min(clock.getDelta(), 0.1);
  updateAutonomy(dt, now);
  updateRig(dt);
  updatePresentationLighting();
  updateCamera(dt);
  renderer.render(scene, camera);
  if (collectFrameSamples && renderedInterval > 0 && renderedInterval < 250) {
    frameSamples.push(renderedInterval);
    if (frameSamples.length >= 120) {
      collectFrameSamples = false;
      const sorted = [...frameSamples].sort((a, b) => a - b);
      const average = frameSamples.reduce((sum, value) => sum + value, 0) / frameSamples.length;
      const p95 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))];
      const fps = Math.round(1000 / average);
      runtimeDiagnostics.frameRate = `${fps} fps / p95 ${p95.toFixed(1)} ms`;
      document.body.dataset.sampledFps = String(fps);
      document.body.dataset.frameP95Ms = p95.toFixed(1);
      updateDiagnostics();
    }
  }
}

resetView();
updateCamera(0.016);
renderer.render(scene, camera);
animationFrameId = requestAnimationFrame(animate);
setTimeout(() => document.querySelector("#interaction-hint").classList.add("fade"), 6500);
loadBlockoutRig().finally(() => {
  if (terminalFailure) return;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (terminalFailure) return;
    const loadMs = Math.round(performance.now() - (window.__showcaseBootAt || 0));
    document.body.dataset.loadMs = String(loadMs);
    runtimeDiagnostics.loadMs = `${loadMs} ms`;
    collectFrameSamples = true;
    runSelectionVolumeSelfTest();
    updateDiagnostics();
    loader.classList.add("done");
    const focus = new URLSearchParams(location.search).get("focus");
    if (focus && componentContent[focus]) focusComponent(focus);
  }));
});
}
