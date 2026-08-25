import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { GLB_URL, SHOWCASE_RELEASE, TELESCOPE_TRAVEL_M } from "./assets/models/600s.version.js?v=0.3.0";

document.body.dataset.viewerStarted = "true";
const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
const compactRender = window.matchMedia?.("(max-width: 800px)").matches ?? false;
const lowMemoryDevice = Number(navigator.deviceMemory) > 0 && Number(navigator.deviceMemory) <= 4;
const renderProfile = lowMemoryDevice ? "economy" : compactRender ? "mobile" : "desktop";
const maximumPixelRatio = lowMemoryDevice ? 1.15 : compactRender ? 1.35 : 1.75;
const shadowMapSize = lowMemoryDevice || compactRender ? 1024 : 2048;
const minimumFrameInterval = lowMemoryDevice ? 1000 / 30 : compactRender ? 1000 / 45 : 0;
const app = document.querySelector("#app");
const loader = document.querySelector("#loader");
const loaderStatus = document.querySelector("#loader-status");
const loaderDetail = document.querySelector("#loader-detail");
const errorPanel = document.querySelector("#error");
document.body.dataset.renderProfile = renderProfile;

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
  loader.hidden = true;
  errorPanel.hidden = false;
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
  const wheelX = [-1.9, 1.9];
  const wheelZ = [-1.08, 1.08];
  wheelX.forEach((x, axleIndex) => wheelZ.forEach((z) => {
    const pivot = new THREE.Group();
    pivot.position.set(x, 0.75, z);
    const wheel = cylinder(`Wheel_${axleIndex}_${z > 0 ? "L" : "R"}`, 0.67, 0.48, [0, 0, 0], [Math.PI / 2, 0, 0], palette.tire, "chassis", 32);
    const hub = cylinder("WheelHub", 0.23, 0.5, [0, 0, 0], [Math.PI / 2, 0, 0], palette.metal, "chassis", 24);
    pivot.add(wheel, hub);
    chassis.add(pivot);
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
    hitVolumes,
    source: "procedural-fixture",
  };
}

const requiredNodes = [
  "600S_ROOT", "Chassis", "Frame", "AxleFront", "AxleRear",
  "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR", "TurntablePivot",
  "Turntable", "SlewRing", "UpperFrame", "EngineCover", "TankCover",
  "Counterweight", "Controls", "BoomPivot", "MainBoom", "Telescope",
  "MidBoom", "FlyBoom", "PlatformPivot", "PlatformRotator", "Platform",
  "LiftCylinder", "LiftCylinderLowerAnchor", "LiftCylinderUpperAnchor",
  "LiftCylinderBarrel", "LiftCylinderRod", "LiftCylinderBasePin", "LiftCylinderRodPin",
  "TowerLinkLower", "TowerLinkUpper", "Powertrack", "PlatformSwingGate",
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
  JLG_Black_PowderCoat: { color: "#111516", roughness: 0.64, metalness: 0.18 },
  JLG_Tire_Rubber: { color: "#111313", roughness: 0.94, metalness: 0 },
  JLG_Zinc_Steel: { color: "#777b76", roughness: 0.38, metalness: 0.68 },
  JLG_Dark_Steel: { color: "#252b2a", roughness: 0.44, metalness: 0.72 },
  JLG_Rim_OffWhite: { color: "#c0bfae", roughness: 0.42, metalness: 0.58 },
  JLG_Hydraulic_Black: { color: "#111515", roughness: 0.7, metalness: 0.12 },
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

function tuneBlockoutMaterials(root) {
  const materials = new Set();
  root.traverse((node) => {
    if (!node.isMesh || node.userData.is_hit_volume) return;
    const nodeMaterials = Array.isArray(node.material) ? node.material : [node.material];
    nodeMaterials.forEach((value) => materials.add(value));
  });
  materials.forEach((value) => applyMaterialProfile(value, materialProfiles[value.name]));

  const boomCream = materialProfiles.JLG_Boom_Cream;
  ["BaseBoomShell", "MidBoomShell", "FlyBoomShell"].forEach((name) => {
    applyDisplayMaterial(root.getObjectByName(name), boomCream, "DisplayCream");
  });
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
  mergedBuckets += mergeRigidGroup(nodes.Wheel_FL);
  mergedBuckets += mergeRigidGroup(nodes.Wheel_FR);
  mergedBuckets += mergeRigidGroup(nodes.Chassis, [nodes.Wheel_FL, nodes.Wheel_FR]);
  mergedBuckets += mergeRigidGroup(nodes.LiftCylinder, [nodes.LiftCylinderRod, nodes.LiftCylinderRodPin]);
  mergedBuckets += mergeRigidGroup(nodes.PlatformPivot);
  mergedBuckets += mergeRigidGroup(nodes.Telescope, [nodes.PlatformPivot]);
  mergedBuckets += mergeRigidGroup(nodes.BoomPivot, [nodes.Telescope]);
  mergedBuckets += mergeRigidGroup(nodes.Turntable, [nodes.BoomPivot, nodes.LiftCylinder]);
  nodes["600S_ROOT"].updateMatrixWorld(true);
  let visibleMeshes = 0;
  nodes["600S_ROOT"].traverse((node) => {
    if (node.isMesh && !node.userData.is_hit_volume) visibleMeshes += 1;
  });
  return { mergedBuckets, visibleMeshes };
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
  gltf.scene.userData.source = `blender-detailed-v${SHOWCASE_RELEASE}`;
  const extras = nodes["600S_ROOT"].userData || {};
  const travel = Number(extras.telescope_travel_m);
  if (extras.asset_version !== SHOWCASE_RELEASE || extras.units !== "meters") {
    throw new Error(`600S GLB release contract failed: expected ${SHOWCASE_RELEASE} in meters`);
  }
  if (!Number.isFinite(travel) || Math.abs(travel - TELESCOPE_TRAVEL_M) > 0.001) {
    throw new Error(`600S GLB telescope contract failed: ${travel}`);
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
  const optimization = optimizeDetailedRig(nodes);
  document.body.dataset.machineVisibleMeshes = String(optimization.visibleMeshes);
  document.body.dataset.machineMergedBuckets = String(optimization.mergedBuckets);

  return {
    machine: gltf.scene,
    chassis: nodes.Chassis,
    turntablePivot: nodes.TurntablePivot,
    boomPivot: nodes.BoomPivot,
    telescope: nodes.Telescope,
    telescopeHomeX: nodes.Telescope.position.x,
    telescopeTravelM: travel,
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
    hitVolumes,
    visibleMeshCount: optimization.visibleMeshes,
    source: `blender-detailed-v${SHOWCASE_RELEASE}`,
  };
}

document.body.dataset.machineSource = "procedural-fallback";
let rig = createProcedural600S();

function loadBlockoutRig() {
  return new Promise((resolve) => {
    loaderStatus.textContent = "Loading equipment model";
    loaderDetail.textContent = "Fetching the optimized 600S detailed reconstruction";
    new GLTFLoader().load(GLB_URL, (gltf) => {
      try {
        loaderStatus.textContent = "Preparing materials and shadows";
        loaderDetail.textContent = `Applying the ${renderProfile} render profile`;
        const loadedRig = configureBlockoutRig(gltf);
        scene.add(loadedRig.machine);
        scene.remove(rig.machine);
        rig = loadedRig;
        document.body.dataset.machineSource = loadedRig.source;
        projectOverview.facts[0] = ["Model", `Blender detailed reconstruction v${SHOWCASE_RELEASE} · ${loadedRig.visibleMeshCount} runtime meshes`];
      } catch (error) {
        console.warn("600S GLB contract validation failed; retaining procedural degraded fixture.", error);
        document.body.dataset.machineSource = "procedural-contract-fallback";
        projectOverview.facts[0] = ["Model", "Procedural degraded fixture"];
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
      console.warn("600S GLB failed to load; retaining procedural degraded fixture.", error);
      document.body.dataset.machineSource = "procedural-load-fallback";
      projectOverview.facts[0] = ["Model", "Procedural degraded fixture"];
      loaderStatus.textContent = "Using simplified fallback";
      loaderDetail.textContent = "The Blender model could not be loaded";
      resolve();
    });
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
const suffixes = { boomAngle: "°", telescope: "%", turntableAngle: "°", steeringAngle: "°" };

Object.entries(inputs).forEach(([key, input]) => {
  input.addEventListener("input", () => {
    targets[key] = Number(input.value);
    outputs[key].value = `${Math.round(targets[key])}${suffixes[key]}`;
    document.querySelector("#motion-status").value = "Positioning";
  });
});

function syncInputs() {
  Object.entries(inputs).forEach(([key, input]) => {
    input.value = String(Math.round(targets[key]));
    outputs[key].value = `${Math.round(targets[key])}${suffixes[key]}`;
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

document.querySelector("#stow").addEventListener("click", () => {
  Object.keys(targets).forEach((key) => { targets[key] = 0; });
  syncInputs();
});

function defaultOrbitRadius() {
  return innerWidth <= 800 ? 29 : 18;
}

function defaultOrbitTargetY(boomAngle = 0) {
  return 1.85 + Math.sin(THREE.MathUtils.degToRad(boomAngle)) * 2.35;
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
  lastX: 0,
  lastY: 0,
  idle: 0,
  pinch: 0,
  pinchRadius: defaultOrbitRadius(),
};
const canvas = renderer.domElement;
const pointers = new Map();
let focusedComponent = null;

canvas.addEventListener("contextmenu", (event) => event.preventDefault());
canvas.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 && event.pointerType !== "touch") return;
  event.preventDefault();
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
    canvas.style.cursor = hitComponentAt(event.clientX, event.clientY) ? "pointer" : "grab";
    return;
  }
  if (pointers.has(event.pointerId)) pointers.set(event.pointerId, [event.clientX, event.clientY]);
  if (pointers.size >= 2) {
    const active = [...pointers.values()];
    const distance = Math.hypot(active[0][0] - active[1][0], active[0][1] - active[1][1]);
    orbit.radiusGoal = THREE.MathUtils.clamp(orbit.pinchRadius * orbit.pinch / distance, 7, 27);
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
  const wasClick = pointers.size === 1 && !orbit.moved;
  pointers.delete(event.pointerId);
  try { canvas.releasePointerCapture(event.pointerId); } catch {}
  orbit.dragging = false;
  orbit.pinch = 0;
  const hit = wasClick ? hitComponentAt(event.clientX, event.clientY) : null;
  if (hit) focusComponent(hit);
  canvas.style.cursor = hit ? "pointer" : "grab";
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  orbit.radiusGoal = THREE.MathUtils.clamp(orbit.radiusGoal * Math.exp(event.deltaY * 0.0012), 7, 27);
  orbit.idle = 0;
}, { passive: false });

function resetView() {
  focusedComponent = null;
  document.querySelectorAll("[data-focus]").forEach((button) => {
    button.classList.remove("active");
    button.setAttribute("aria-pressed", "false");
  });
  orbit.targetGoal.set(0.8, defaultOrbitTargetY(machineState.boomAngle), 0);
  orbit.radiusGoal = defaultOrbitRadius();
  orbit.theta = 0.76;
  orbit.phi = 1.44;
  orbit.vTheta = 0;
  orbit.vPhi = 0;
}
document.querySelector("#reset-view").addEventListener("click", resetView);

const componentContent = {
  chassis: {
    title: "Chassis",
    copy: "The mobile base carries the axles, steering assemblies, lower controls, and the rotating upper structure.",
    facts: [["Visible system", "Frame, axles, drive hubs, wheels, steering linkage, and deck"], ["Configuration", "4WD hydrostatic with two-wheel front steer"], ["Boundary", "Undimensioned offsets remain visually reconstructed"]],
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
    copy: "The primary lifting structure changes elevation at its base pivot while a nested section extends the platform outward.",
    facts: [["Motion", "Lift, two-anchor cylinder solve, and capped visual telescope travel"], ["Hierarchy", "BoomPivot → MainBoom → Telescope → MidBoom → FlyBoom"], ["Boundary", "Travel and cylinder stroke are visual reconstructions"]],
    radius: 9.5,
  },
  platform: {
    title: "Platform",
    copy: "The work platform is parented to the telescoping section so it follows the boom through elevation, extension, and swing.",
    facts: [["Visible system", "Rapid-replace deck, orange rails, swing gate, console, footswitch, SkyGuard, and labels"], ["Hierarchy", "FlyBoom → PlatformPivot → Platform"], ["Leveling", "Visual counter-rotation; rotator dimensions remain reconstructed"]],
    radius: 6.2,
  },
};

const inspector = document.querySelector("#inspector");
const infoToggle = document.querySelector("#info-toggle");
const projectOverview = {
  kicker: "Project note",
  title: "A visual replica,<br>not an engineering model.",
  copy: "This unofficial study is designed to explain visible product systems through a simplified, interactive model based on public reference material.",
  facts: [["Model", "Loading Blender detailed reconstruction"], ["Purpose", "Portfolio and educational visualization"], ["Boundary", "Not a service, training, fabrication, or safety reference"]],
};
function openInspector(component) {
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
}
function closeInspector() {
  document.body.classList.remove("inspector-open");
  inspector.inert = true;
  infoToggle.setAttribute("aria-expanded", "false");
}
infoToggle.addEventListener("click", () => openInspector());
document.querySelector("#inspector-close").addEventListener("click", closeInspector);
document.querySelector("#scrim").addEventListener("click", closeInspector);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeInspector();
});

function focusComponent(component) {
  focusedComponent = component;
  document.querySelectorAll("[data-focus]").forEach((button) => {
    const selected = button.dataset.focus === component;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  const worldPosition = new THREE.Vector3();
  const node = component === "chassis" ? rig.chassis : component === "turntable" ? rig.turntablePivot : component === "boom" ? rig.boomPivot : rig.platformMount;
  node.getWorldPosition(worldPosition);
  if (component === "platform") worldPosition.y += 0.2;
  if (component === "boom") worldPosition.x += 2.2;
  orbit.targetGoal.copy(worldPosition);
  orbit.radiusGoal = componentContent[component].radius;
  orbit.idle = 0;
  openInspector(component);
}
document.querySelectorAll("[data-focus]").forEach((button) => button.addEventListener("click", () => focusComponent(button.dataset.focus)));

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
function hitComponentAt(x, y) {
  const rect = canvas.getBoundingClientRect();
  pointer.set(((x - rect.left) / rect.width) * 2 - 1, -((y - rect.top) / rect.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  return raycaster.intersectObjects(rig.hitVolumes, false)[0]?.object?.userData?.component ?? null;
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

function updateRig(dt) {
  const speed = reducedMotion ? 18 : 6;
  Object.keys(machineState).forEach((key) => {
    machineState[key] = THREE.MathUtils.damp(machineState[key], targets[key], speed, dt);
  });
  rig.boomPivot.rotation.z = THREE.MathUtils.degToRad(machineState.boomAngle);
  if (rig.platformPivot) rig.platformPivot.rotation.z = -THREE.MathUtils.degToRad(machineState.boomAngle);
  rig.telescope.position.x = rig.telescopeHomeX + (machineState.telescope / 100) * rig.telescopeTravelM;
  rig.turntablePivot.rotation.y = THREE.MathUtils.degToRad(machineState.turntableAngle);
  rig.steeringPivots.forEach((pivot) => { pivot.rotation.y = THREE.MathUtils.degToRad(machineState.steeringAngle); });
  updateLiftCylinder();
  if (!focusedComponent) orbit.targetGoal.y = defaultOrbitTargetY(machineState.boomAngle);
  const moving = Object.keys(machineState).some((key) => Math.abs(machineState[key] - targets[key]) > 0.1);
  const stowed = Object.values(targets).every((value) => Math.abs(value) < 0.1);
  document.querySelector("#motion-status").value = moving ? "Positioning" : stowed ? "Stowed" : "Holding";
}

function updateCamera(dt) {
  if (!orbit.dragging) {
    orbit.theta += orbit.vTheta;
    orbit.phi = THREE.MathUtils.clamp(orbit.phi + orbit.vPhi, 0.42, 1.48);
    orbit.vTheta *= 0.91;
    orbit.vPhi *= 0.91;
  }
  orbit.idle += dt;
  if (orbit.idle > 4 && !reducedMotion) orbit.theta += dt * 0.025;
  orbit.radius = THREE.MathUtils.damp(orbit.radius, orbit.radiusGoal, 5, dt);
  orbit.target.lerp(orbit.targetGoal, 1 - Math.exp(-5 * dt));
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
});

const clock = new THREE.Clock();
let lastRenderedAt = 0;
function animate(now = 0) {
  requestAnimationFrame(animate);
  if (minimumFrameInterval && now - lastRenderedAt < minimumFrameInterval) return;
  lastRenderedAt = now;
  const dt = Math.min(clock.getDelta(), 0.1);
  updateRig(dt);
  updateCamera(dt);
  renderer.render(scene, camera);
}

resetView();
updateCamera(0.016);
renderer.render(scene, camera);
animate();
setTimeout(() => document.querySelector("#interaction-hint").classList.add("fade"), 6500);
loadBlockoutRig().finally(() => {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.body.dataset.loadMs = String(Math.round(performance.now() - (window.__showcaseBootAt || 0)));
    loader.classList.add("done");
    const focus = new URLSearchParams(location.search).get("focus");
    if (focus && componentContent[focus]) focusComponent(focus);
  }));
});
}
