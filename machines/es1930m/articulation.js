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
  cylinderLower: Object.freeze(new THREE.Vector3(-0.31, 0.29, 0)),
  kickerPivot: Object.freeze(new THREE.Vector3(0.27, 0.31, 0)),
  kickerRadius: 0.56,
  reconstructedMaximumSteerRadians: THREE.MathUtils.degToRad(38),
  reconstructedOuterSteerFactor: 31 / 38,
});

const X_AXIS = new THREE.Vector3(1, 0, 0);
const Y_AXIS = new THREE.Vector3(0, 1, 0);

function clampUnit(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function circleIntersectionPositiveY(anchor, center, anchorRadius, centerRadius) {
  const dx = center.x - anchor.x;
  const dy = center.y - anchor.y;
  const separation = Math.hypot(dx, dy);
  if (!separation || separation > anchorRadius + centerRadius || separation < Math.abs(anchorRadius - centerRadius)) {
    throw new Error("ES1930M reconstructed cylinder and kicker circles do not intersect");
  }
  const along = (anchorRadius ** 2 - centerRadius ** 2 + separation ** 2) / (2 * separation);
  const height = Math.sqrt(Math.max(anchorRadius ** 2 - along ** 2, 0));
  const baseX = anchor.x + along * dx / separation;
  const baseY = anchor.y + along * dy / separation;
  const a = new THREE.Vector3(baseX - height * dy / separation, baseY + height * dx / separation, 0);
  const b = new THREE.Vector3(baseX + height * dy / separation, baseY - height * dx / separation, 0);
  return a.y >= b.y ? a : b;
}

export function solveES1930MState(liftInput, deckInput = 0, steerInput = 0) {
  const lift = clampUnit(liftInput);
  const deck = clampUnit(deckInput);
  const steer = Math.max(-1, Math.min(1, Number(steerInput) || 0));
  const floorY = THREE.MathUtils.lerp(ES1930M_MECHANISM.stowedDeckY, ES1930M_MECHANISM.indoorDeckY, lift);
  const rise = (floorY - ES1930M_MECHANISM.basePivotY - ES1930M_MECHANISM.deckOffsetY) / ES1930M_MECHANISM.levels;
  const span = Math.sqrt(ES1930M_MECHANISM.armLength ** 2 - rise ** 2);
  const boundaries = Array.from({ length: ES1930M_MECHANISM.levels + 1 }, (_, index) => ({
    left: new THREE.Vector3(-span / 2, ES1930M_MECHANISM.basePivotY + index * rise, 0),
    right: new THREE.Vector3(span / 2, ES1930M_MECHANISM.basePivotY + index * rise, 0),
  }));
  const cylinderPinDistance = ES1930M_MECHANISM.cylinderClosedPins + lift * ES1930M_MECHANISM.cylinderStroke;
  const cylinderUpper = circleIntersectionPositiveY(
    ES1930M_MECHANISM.cylinderLower,
    ES1930M_MECHANISM.kickerPivot,
    cylinderPinDistance,
    ES1930M_MECHANISM.kickerRadius,
  );
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
    lowerSlides: [required(root, "LowerSlideBlock_LEFT"), required(root, "LowerSlideBlock_RIGHT")],
    cylinderBarrel: required(root, "LiftCylinderBarrel"),
    cylinderRod: required(root, "LiftCylinderRod"),
    kicker: required(root, "KickerArm"),
    cylinderUpperMarker: required(root, "PIVOT_LIFT_CYLINDER_UPPER"),
    steerBarrel: required(root, "SteerCylinderBarrel"),
    steerSpindles: [required(root, "SteerSpindle_R"), required(root, "SteerSpindle_L")],
    potholeBars,
    potholeInitialY: potholeBars.map((node) => node.position.y),
  };
  return rig;
}

export function applyES1930MState(rig, state) {
  for (let index = 0; index < ES1930M_MECHANISM.levels; index += 1) {
    const lower = state.boundaries[index];
    const upper = state.boundaries[index + 1];
    for (const plane of ["Right", "Left"]) {
      alignLocalX(rig.links[index][`A_${plane}`], lower.left, upper.right);
      alignLocalX(rig.links[index][`B_${plane}`], lower.right, upper.left);
    }
    const center = new THREE.Vector3(0, (lower.left.y + upper.right.y) / 2, 0);
    const lateralStart = new THREE.Vector3(0, 0, -0.31);
    const lateralEnd = new THREE.Vector3(0, 0, 0.31);
    for (const [node, point] of [
      [rig.pins[index].lowerLeft, lower.left],
      [rig.pins[index].lowerRight, lower.right],
      [rig.pins[index].upperLeft, upper.left],
      [rig.pins[index].upperRight, upper.right],
      [rig.pins[index].center, center],
    ]) {
      alignCylinderY(node, lateralStart.clone().add(point), lateralEnd.clone().add(point), 0.62);
    }
  }
  rig.lowerSlides[0].position.x = state.boundaries[0].left.x;
  rig.lowerSlides[1].position.x = state.boundaries[0].right.x;
  rig.platform.position.y = state.floorY - ES1930M_MECHANISM.stowedDeckY;
  rig.extension.position.x = state.deckTranslation;

  const lower = ES1930M_MECHANISM.cylinderLower;
  const upper = state.cylinderUpper;
  const barrelEnd = lower.clone().lerp(upper, 0.72);
  const rodStart = lower.clone().lerp(upper, 0.48);
  alignCylinderY(rig.cylinderBarrel, lower, barrelEnd, ES1930M_MECHANISM.cylinderClosedPins * 0.72);
  alignCylinderY(rig.cylinderRod, rodStart, upper, ES1930M_MECHANISM.cylinderClosedPins * 0.52);
  alignCylinderY(rig.kicker, ES1930M_MECHANISM.kickerPivot, upper, ES1930M_MECHANISM.kickerRadius);
  rig.cylinderUpperMarker.position.copy(upper);

  rig.steerBarrel.position.z = state.steer * ES1930M_MECHANISM.steeringCylinderStrokeEachDirection;
  const direction = Math.sign(state.steer) || 1;
  const magnitude = Math.abs(state.steer) * ES1930M_MECHANISM.reconstructedMaximumSteerRadians;
  const rightIsInner = direction > 0;
  rig.steerSpindles[0].rotation.y = direction * magnitude * (rightIsInner ? 1 : ES1930M_MECHANISM.reconstructedOuterSteerFactor);
  rig.steerSpindles[1].rotation.y = direction * magnitude * (rightIsInner ? ES1930M_MECHANISM.reconstructedOuterSteerFactor : 1);

  rig.potholeBars.forEach((node, index) => {
    node.position.y = rig.potholeInitialY[index] - 0.035 * state.potholeDeployment;
  });
  rig.root.updateMatrixWorld(true);
}
