import * as THREE from "three";

export const ES1930M_MECHANISM = Object.freeze({
  levels: 5,
  armLength: 1.11,
  basePivotY: 0.30,
  deckOffsetY: 0.10,
  stowedDeckY: 0.90,
  indoorDeckY: 5.64,
  outdoorDeckY: 4.57,
  extensionTravel: 0.55,
  cylinderStroke: 0.6855,
  cylinderClosedPins: 0.43,
  steeringCylinderStrokeEachDirection: 0.08,
  rearFixedX: -0.552743210183,
  cylinderLower: Object.freeze(new THREE.Vector3(0.073884411905, 0.168081864473, 0)),
  kickerPivotFraction: 0.5,
  cylinderUpperFraction: 0.9,
  kickerRollerOffset: 0.10,
});

const X_AXIS = new THREE.Vector3(1, 0, 0);
const Y_AXIS = new THREE.Vector3(0, 1, 0);

function clampUnit(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function pointAlong(start, end, fraction) {
  return start.clone().lerp(end, fraction);
}

export function solveES1930MState(liftInput, deckInput = 0, steerInput = 0) {
  const lift = clampUnit(liftInput);
  const deck = clampUnit(deckInput);
  const steer = Math.max(-1, Math.min(1, Number(steerInput) || 0));
  const floorY = THREE.MathUtils.lerp(ES1930M_MECHANISM.stowedDeckY, ES1930M_MECHANISM.indoorDeckY, lift);
  const rise = (floorY - ES1930M_MECHANISM.basePivotY - ES1930M_MECHANISM.deckOffsetY) / ES1930M_MECHANISM.levels;
  const span = Math.sqrt(ES1930M_MECHANISM.armLength ** 2 - rise ** 2);
  const boundaries = Array.from({ length: ES1930M_MECHANISM.levels + 1 }, (_, index) => ({
    rear: new THREE.Vector3(ES1930M_MECHANISM.rearFixedX, ES1930M_MECHANISM.basePivotY + index * rise, 0),
    front: new THREE.Vector3(ES1930M_MECHANISM.rearFixedX + span, ES1930M_MECHANISM.basePivotY + index * rise, 0),
  }));
  const levelOne = boundaries[0];
  const levelTwo = boundaries[1];
  const levelOneAStart = levelOne.rear;
  const levelOneAEnd = levelTwo.front;
  const kickerPivot = pointAlong(levelOneAStart, levelOneAEnd, ES1930M_MECHANISM.kickerPivotFraction);
  const cylinderUpper = pointAlong(levelOneAStart, levelOneAEnd, ES1930M_MECHANISM.cylinderUpperFraction);
  const armDirection = levelOneAEnd.clone().sub(levelOneAStart).normalize();
  const kickerRoller = kickerPivot.clone().add(new THREE.Vector3(-armDirection.y, armDirection.x, 0).multiplyScalar(ES1930M_MECHANISM.kickerRollerOffset));
  const cylinderPinDistance = cylinderUpper.distanceTo(ES1930M_MECHANISM.cylinderLower);
  return Object.freeze({
    lift,
    deck,
    steer,
    floorY,
    rise,
    span,
    boundaries,
    cylinderPinDistance,
    cylinderUpper,
    kickerPivot,
    kickerRoller,
    deckTranslation: deck * ES1930M_MECHANISM.extensionTravel,
    potholeDeployment: THREE.MathUtils.smoothstep(lift, 0.015, 0.10),
  });
}

function required(root, name) {
  const node = root.getObjectByName(name);
  if (!node) throw new Error(`ES1930M asset is missing ${name}`);
  return node;
}

function optional(root, name) {
  return root.getObjectByName(name) || null;
}

function alignLocalX(node, start, end) {
  const authoredLateral = node.position.z;
  const direction = new THREE.Vector3().subVectors(end, start);
  node.position.copy(start).add(end).multiplyScalar(0.5);
  node.position.z = authoredLateral;
  node.quaternion.setFromUnitVectors(X_AXIS, direction.normalize());
}

function alignCylinderY(node, start, end, authoredLength) {
  if (!node) return;
  const direction = new THREE.Vector3().subVectors(end, start);
  node.position.copy(start).add(end).multiplyScalar(0.5);
  node.quaternion.setFromUnitVectors(Y_AXIS, direction.clone().normalize());
  node.scale.set(1, direction.length() / authoredLength, 1);
}

export function createES1930MRig(root) {
  const links = [];
  const pins = [];
  for (let level = 1; level <= ES1930M_MECHANISM.levels; level += 1) {
    const levelLinks = {};
    for (const branch of ["A", "B"]) {
      for (const plane of ["Right", "Left"]) {
        levelLinks[`${branch}_${plane}`] = required(root, `Level${String(level).padStart(2, "0")}_${branch}_${plane}`);
      }
    }
    links.push(levelLinks);
    pins.push({
      lowerLeft: required(root, `Level${String(level).padStart(2, "0")}_PIN_LOWER_L`),
      lowerRight: required(root, `Level${String(level).padStart(2, "0")}_PIN_LOWER_R`),
      upperLeft: required(root, `Level${String(level).padStart(2, "0")}_PIN_UPPER_L`),
      upperRight: required(root, `Level${String(level).padStart(2, "0")}_PIN_UPPER_R`),
      center: required(root, `Level${String(level).padStart(2, "0")}_PIN_CENTER`),
    });
  }
  const potholeBars = [optional(root, "PotholeBar_R"), optional(root, "PotholeBar_L")].filter(Boolean);
  const rig = {
    root,
    links,
    pins,
    platform: required(root, "PlatformAssembly"),
    extension: required(root, "ExtensionDeck"),
    lowerSlides: [required(root, "LowerSlideBlock_RIGHT_PLANE"), required(root, "LowerSlideBlock_LEFT_PLANE")],
    upperSlides: [required(root, "UpperSlideBlock_RIGHT_PLANE"), required(root, "UpperSlideBlock_LEFT_PLANE")],
    rearAnchors: [required(root, "PIVOT_STACK_LOWER_REAR_RIGHT_PLANE"), required(root, "PIVOT_STACK_LOWER_REAR_LEFT_PLANE")],
    cylinderBarrel: required(root, "LiftCylinderBarrel"),
    cylinderRod: required(root, "LiftCylinderRod"),
    kickerWebs: [required(root, "KickerArmWeb_SCISSOR_CYLINDER"), required(root, "KickerArmWeb_CYLINDER_ROLLER"), required(root, "KickerArmWeb_ROLLER_SCISSOR")],
    kickerPivotMarker: required(root, "PIVOT_KICKER_TO_SCISSOR"),
    kickerRollerMarker: required(root, "PIVOT_KICKER_ROLLER"),
    cylinderUpperMarker: required(root, "PIVOT_LIFT_CYLINDER_UPPER"),
    steerBarrel: required(root, "SteerCylinderBarrel"),
    steerSpindles: [required(root, "SteerSpindle_R"), required(root, "SteerSpindle_L")],
    potholeBars,
    potholeInitialY: potholeBars.map((node) => node.position.y),
    hitVolumes: Object.fromEntries(["Chassis_Hit", "Scissor_Hit", "Platform_Hit", "Steering_Hit"].map((name) => [name, required(root, name)])),
  };
  return rig;
}

export function selfTestES1930MRig(rig, restoreState) {
  const failures = [];
  for (const sample of [[0, 0, -1], [0.5, 1, 0], [1, 1, 1]]) {
    const solved = solveES1930MState(...sample);
    applyES1930MState(rig, solved);
    for (const marker of rig.rearAnchors) {
      if (Math.abs(marker.position.x - ES1930M_MECHANISM.rearFixedX) > 1e-6) failures.push("rear anchor drift");
    }
    if (Math.abs(rig.lowerSlides[0].position.x - rig.lowerSlides[1].position.x) > 1e-6) failures.push("lower slide pair split");
    if (Math.abs(rig.lowerSlides[0].position.x - solved.boundaries[0].front.x) > 1e-6) failures.push("front track mismatch");
    if (Math.abs(rig.hitVolumes.Platform_Hit.position.y - (1.44 + rig.platform.position.y)) > 1e-6) failures.push("platform hit-volume drift");
    if (Math.abs(rig.cylinderUpperMarker.position.x - solved.cylinderUpper.x) > 1e-6 || Math.abs(rig.cylinderUpperMarker.position.y - solved.cylinderUpper.y) > 1e-6) failures.push("cylinder attachment drift");
  }
  applyES1930MState(rig, restoreState);
  return Object.freeze({ ok: failures.length === 0, failures: Object.freeze([...new Set(failures)]) });
}

export function applyES1930MState(rig, state) {
  for (let index = 0; index < ES1930M_MECHANISM.levels; index += 1) {
    const lower = state.boundaries[index];
    const upper = state.boundaries[index + 1];
    for (const plane of ["Right", "Left"]) {
      alignLocalX(rig.links[index][`A_${plane}`], lower.rear, upper.front);
      alignLocalX(rig.links[index][`B_${plane}`], lower.front, upper.rear);
    }
    const center = lower.rear.clone().lerp(upper.front, 0.5);
    const lateralStart = new THREE.Vector3(0, 0, -0.31);
    const lateralEnd = new THREE.Vector3(0, 0, 0.31);
    for (const [node, point] of [
      [rig.pins[index].lowerLeft, lower.rear],
      [rig.pins[index].lowerRight, lower.front],
      [rig.pins[index].upperLeft, upper.rear],
      [rig.pins[index].upperRight, upper.front],
      [rig.pins[index].center, center],
    ]) {
      alignCylinderY(node, lateralStart.clone().add(point), lateralEnd.clone().add(point), 0.62);
    }
  }
  for (const slide of rig.lowerSlides) slide.position.x = state.boundaries[0].front.x;
  for (const slide of rig.upperSlides) slide.position.x = state.boundaries.at(-1).front.x;
  rig.platform.position.y = state.floorY - ES1930M_MECHANISM.stowedDeckY;
  rig.extension.position.x = state.deckTranslation;

  const lower = ES1930M_MECHANISM.cylinderLower;
  const upper = state.cylinderUpper;
  const barrelEnd = lower.clone().lerp(upper, 0.72);
  const rodStart = lower.clone().lerp(upper, 0.48);
  alignCylinderY(rig.cylinderBarrel, lower, barrelEnd, ES1930M_MECHANISM.cylinderClosedPins * 0.72);
  alignCylinderY(rig.cylinderRod, rodStart, upper, ES1930M_MECHANISM.cylinderClosedPins * 0.52);
  alignLocalX(rig.kickerWebs[0], state.kickerPivot, upper);
  alignLocalX(rig.kickerWebs[1], upper, state.kickerRoller);
  alignLocalX(rig.kickerWebs[2], state.kickerRoller, state.kickerPivot);
  rig.kickerPivotMarker.position.copy(state.kickerPivot);
  rig.kickerRollerMarker.position.copy(state.kickerRoller);
  rig.cylinderUpperMarker.position.copy(upper);

  rig.steerBarrel.position.z = state.steer * ES1930M_MECHANISM.steeringCylinderStrokeEachDirection;
  for (const spindle of rig.steerSpindles) spindle.rotation.y = 0;

  const scissorHit = rig.hitVolumes.Scissor_Hit;
  const scissorTop = state.floorY - ES1930M_MECHANISM.deckOffsetY;
  scissorHit.position.x = ES1930M_MECHANISM.rearFixedX + state.span / 2;
  scissorHit.position.y = (ES1930M_MECHANISM.basePivotY + scissorTop) / 2;
  scissorHit.scale.x = Math.max(state.span / 1.12, 0.34);
  scissorHit.scale.y = Math.max((scissorTop - ES1930M_MECHANISM.basePivotY) / 0.55, 1);
  const platformHit = rig.hitVolumes.Platform_Hit;
  platformHit.position.x = 0.02 + state.deckTranslation / 2;
  platformHit.position.y = 1.44 + rig.platform.position.y;
  platformHit.scale.x = (1.38 + state.deckTranslation) / 1.38;

  rig.potholeBars.forEach((node, index) => {
    node.position.y = rig.potholeInitialY[index] - 0.035 * state.potholeDeployment;
  });
  rig.root.updateMatrixWorld(true);
}
