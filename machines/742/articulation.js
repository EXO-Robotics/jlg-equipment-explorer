import * as THREE from "three";

export const JLG742_MECHANISM = Object.freeze({
  boomMinimum: THREE.MathUtils.degToRad(3),
  boomMaximum: THREE.MathUtils.degToRad(69),
  midTravel: 3.604,
  flyTravel: 3.604,
  carriageTiltDown: THREE.MathUtils.degToRad(5),
  carriageTiltUp: THREE.MathUtils.degToRad(12),
  steerMaximum: THREE.MathUtils.degToRad(55),
  wheelbase: 3.42,
  wheelCenterTrack: 2.1005,
  frameLevelMaximum: THREE.MathUtils.degToRad(10),
});

function unit(value) { return Math.max(0, Math.min(1, Number(value) || 0)); }
function signed(value) { return Math.max(-1, Math.min(1, Number(value) || 0)); }
function required(root, name) {
  const node = root.getObjectByName(name);
  if (!node) throw new Error(`742 asset is missing ${name}`);
  return node;
}

export function solve742State(input) {
  const lift = unit(input.lift);
  const telescope = unit(input.telescope);
  const tilt = signed(input.tilt);
  const steer = signed(input.steer);
  const level = signed(input.level);
  const steerMode = ["circle", "crab", "front"].includes(input.steerMode) ? input.steerMode : "circle";
  const boomAngle = THREE.MathUtils.lerp(JLG742_MECHANISM.boomMinimum, JLG742_MECHANISM.boomMaximum, lift);
  const steerAngle = steer * JLG742_MECHANISM.steerMaximum;
  const carriageTiltAngle = tilt < 0
    ? tilt * JLG742_MECHANISM.carriageTiltDown
    : tilt * JLG742_MECHANISM.carriageTiltUp;
  const wheelAngles = solveWheelAngles(steerAngle, steerMode);
  return Object.freeze({
    lift, telescope, tilt, steer, level, steerMode, boomAngle,
    midTranslation: telescope * JLG742_MECHANISM.midTravel,
    flyTranslation: telescope * JLG742_MECHANISM.flyTravel,
    carriageAngle: -boomAngle + carriageTiltAngle,
    carriageTiltAngle,
    frameAngle: level * JLG742_MECHANISM.frameLevelMaximum,
    steerAngle, wheelAngles,
  });
}

function ackermannOuter(inner, axleSpan) {
  const magnitude = Math.abs(inner);
  if (magnitude < 1e-7) return 0;
  const radiusToCenter = JLG742_MECHANISM.wheelCenterTrack / 2 + axleSpan / Math.tan(magnitude);
  return Math.atan(axleSpan / (radiusToCenter + JLG742_MECHANISM.wheelCenterTrack / 2));
}

function solveWheelAngles(steerAngle, mode) {
  if (Math.abs(steerAngle) < 1e-7) return Object.freeze({ FL: 0, FR: 0, RL: 0, RR: 0 });
  if (mode === "crab") {
    return Object.freeze({ FL: steerAngle, FR: steerAngle, RL: steerAngle, RR: steerAngle });
  }
  const positive = steerAngle > 0;
  const inner = Math.abs(steerAngle);
  const axleSpan = mode === "circle" ? JLG742_MECHANISM.wheelbase / 2 : JLG742_MECHANISM.wheelbase;
  const outer = ackermannOuter(inner, axleSpan);
  if (mode === "front") {
    return positive
      ? Object.freeze({ FL: outer, FR: inner, RL: 0, RR: 0 })
      : Object.freeze({ FL: -inner, FR: -outer, RL: 0, RR: 0 });
  }
  return positive
    ? Object.freeze({ FL: outer, FR: inner, RL: -outer, RR: -inner })
    : Object.freeze({ FL: -inner, FR: -outer, RL: inner, RR: outer });
}

export function create742Rig(root) {
  const dynamicNames = [
    "LiftCylinderBarrel", "LiftCylinderRod", "LiftCylinderRodPin",
    "TelescopeCylinderBarrel", "TelescopeCylinderRod", "CompensationCylinderBarrel", "CompensationCylinderRod",
    "CarriageTiltCylinderBarrel", "CarriageTiltCylinderRod", "CarriageTiltLink",
    "FrameLevelCylinderBarrel", "FrameLevelCylinderRod", "RearAxleStabilizerBarrel", "RearAxleStabilizerRod",
    "FrontSteerCylinderBarrel", "FrontSteerCylinderRodLeft", "FrontSteerCylinderRodRight",
    "RearSteerCylinderBarrel", "RearSteerCylinderRodLeft", "RearSteerCylinderRodRight",
    "BoomAngleSensorLink", "BoomAngleSensorBoomJoint",
    ...Array.from({ length: 2 }, (_, lane) => Array.from({ length: 3 }, (_, segment) => `LiftHose_${lane}_${segment}`)).flat(),
    ...Array.from({ length: 4 }, (_, lane) => Array.from({ length: 3 }, (_, segment) => `BoomHose_${lane}_${segment}`)).flat(),
    "ExtendChain_L", "ExtendChain_R", "RetractChain_C",
  ];
  const dynamic = Object.fromEntries(dynamicNames.map((name) => [name, required(root, name)]));
  return Object.freeze({
    root: required(root, "742_ROOT"),
    frame: required(root, "FrameLevelPivot"),
    boom: required(root, "BoomLiftPivot"),
    mid: required(root, "BoomMid"),
    fly: required(root, "BoomFly"),
    carriage: required(root, "CarriageTiltPivot"),
    wheels: Object.freeze({
      FL: required(root, "SteerPivot_FL"), FR: required(root, "SteerPivot_FR"),
      RL: required(root, "SteerPivot_RL"), RR: required(root, "SteerPivot_RR"),
    }),
    dynamic: Object.freeze(dynamic),
    authored: Object.freeze({
      midX: required(root, "BoomMid").position.x,
      flyX: required(root, "BoomFly").position.x,
      lengths: Object.freeze(Object.fromEntries(dynamicNames.map((name) => [
        name, Number(dynamic[name].userData.authored_length_m) || 1,
      ]))),
    }),
  });
}

function applyWheelAngles(rig, state) {
  // The authored root basis maps local +Z to world -Y.
  for (const corner of ["FL", "FR", "RL", "RR"]) {
    rig.wheels[corner].rotation.z = -state.wheelAngles[corner];
  }
}

const Y_AXIS = new THREE.Vector3(0, 1, 0);
const FRAME_LEVEL_PIVOT = new THREE.Vector3(0, 0, -0.82);
function logical(x, y, z = 0) { return new THREE.Vector3(x, z, -y); }
function rotateLogicalBoom(point, angle) { return point.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), angle); }

function setBeam(rig, name, start, end) {
  const node = rig.dynamic[name];
  const direction = end.clone().sub(start);
  const length = direction.length();
  if (length < 1e-6) throw new Error(`742 ${name} collapsed below a visible length`);
  node.position.copy(start).addScaledVector(direction, 0.5);
  node.quaternion.setFromUnitVectors(Y_AXIS, direction.normalize());
  node.scale.set(1, length / rig.authored.lengths[name], 1);
}

function setSegmentedPath(rig, prefix, points) {
  for (let index = 0; index < points.length - 1; index += 1) {
    setBeam(rig, `${prefix}_${index}`, points[index], points[index + 1]);
  }
}

function applyActuatorRig(rig, state) {
  const pivot = logical(-2.158, 1.838);
  const liftBase = logical(-1.80, 0.70);
  const liftAnchor = pivot.clone().add(rotateLogicalBoom(logical(2.412, -0.20), state.boomAngle));
  const liftDirection = liftAnchor.clone().sub(liftBase);
  const barrelEnd = liftBase.clone().addScaledVector(liftDirection, 0.72);
  const rodStart = liftBase.clone().addScaledVector(liftDirection, 0.55);
  setBeam(rig, "LiftCylinderBarrel", liftBase, barrelEnd);
  setBeam(rig, "LiftCylinderRod", rodStart, liftAnchor);
  rig.dynamic.LiftCylinderRodPin.position.copy(liftAnchor);

  for (let lane = 0; lane < 2; lane += 1) {
    const lateral = lane === 0 ? -0.16 : -0.23;
    const hoseEnd = liftAnchor.clone().add(logical(0, 0, lateral));
    const start = logical(-1.88, lane === 0 ? 0.74 : 0.70, lateral);
    const delta = hoseEnd.clone().sub(start);
    setSegmentedPath(rig, `LiftHose_${lane}`, [
      start,
      start.clone().addScaledVector(delta, 0.34).add(logical(0, -0.12, 0)),
      start.clone().addScaledVector(delta, 0.70).add(logical(0, -0.09, 0)),
      hoseEnd,
    ]);
  }

  const telescopeBase = logical(0.55, -0.22, 0);
  const telescopeEnd = logical(3.36 + state.midTranslation, -0.22, 0);
  const telescopeDelta = telescopeEnd.clone().sub(telescopeBase);
  setBeam(rig, "TelescopeCylinderBarrel", telescopeBase, telescopeBase.clone().addScaledVector(telescopeDelta, 0.62));
  setBeam(rig, "TelescopeCylinderRod", telescopeBase.clone().addScaledVector(telescopeDelta, 0.48), telescopeEnd);

  const compensationBase = logical(-2.00, 1.50, -0.31);
  const compensationAnchor = pivot.clone().add(rotateLogicalBoom(logical(0.80, 0.30, -0.31), state.boomAngle));
  const compensationDelta = compensationAnchor.clone().sub(compensationBase);
  setBeam(rig, "CompensationCylinderBarrel", compensationBase, compensationBase.clone().addScaledVector(compensationDelta, 0.68));
  setBeam(rig, "CompensationCylinderRod", compensationBase.clone().addScaledVector(compensationDelta, 0.52), compensationAnchor);

  const midX = rig.authored.midX + state.midTranslation;
  const flyX = rig.authored.flyX + state.flyTranslation;
  const movingHoseEndX = midX + flyX + 5.05;
  const hoseLaterals = [-0.27, -0.20, 0.20, 0.27];
  hoseLaterals.forEach((lateral, lane) => {
    const start = logical(0.15, -0.34, lateral);
    const end = logical(movingHoseEndX, -0.28, lateral);
    const delta = end.clone().sub(start);
    setSegmentedPath(rig, `BoomHose_${lane}`, [
      start,
      start.clone().addScaledVector(delta, 0.34).add(logical(0, -0.08, 0)),
      start.clone().addScaledVector(delta, 0.69).add(logical(0, -0.06, 0)),
      end,
    ]);
  });
  for (const [side, lateral] of [["L", -0.24], ["R", 0.24]]) {
    setBeam(rig, `ExtendChain_${side}`, logical(0.40, -0.22, lateral), logical(midX + flyX + 4.70, -0.22, lateral));
  }
  setBeam(rig, "RetractChain_C", logical(5.10, -0.29, 0), logical(midX + flyX + 0.20, -0.29, 0));

  const carriagePivot = logical(5.296, -0.80);
  const tiltBase = logical(4.216, -1.21, 0.42);
  const movingRodAnchor = carriagePivot.clone().add(rotateLogicalBoom(logical(-0.1494, 0.3705, 0.42), state.carriageAngle));
  const movingLinkAnchor = carriagePivot.clone().add(rotateLogicalBoom(logical(-0.08, 0.58, 0.42), state.carriageAngle));
  const tiltDelta = movingRodAnchor.clone().sub(tiltBase);
  setBeam(rig, "CarriageTiltCylinderBarrel", tiltBase, tiltBase.clone().addScaledVector(tiltDelta, 0.66));
  setBeam(rig, "CarriageTiltCylinderRod", tiltBase.clone().addScaledVector(tiltDelta, 0.50), movingRodAnchor);
  setBeam(rig, "CarriageTiltLink", movingRodAnchor, movingLinkAnchor);

  const levelBase = logical(-0.0133, 0.6054, 0.4865);
  const levelAnchor = logical(0.1121, 1.2428, 1.1607).sub(FRAME_LEVEL_PIVOT)
    .applyAxisAngle(new THREE.Vector3(1, 0, 0), state.frameAngle).add(FRAME_LEVEL_PIVOT);
  const levelDelta = levelAnchor.clone().sub(levelBase);
  setBeam(rig, "FrameLevelCylinderBarrel", levelBase, levelBase.clone().addScaledVector(levelDelta, 0.67));
  setBeam(rig, "FrameLevelCylinderRod", levelBase.clone().addScaledVector(levelDelta, 0.52), levelAnchor);

  const rasBase = logical(-1.95, 0.64, -0.45);
  const rasAnchor = logical(-1.55, 0.92, -0.65).sub(FRAME_LEVEL_PIVOT)
    .applyAxisAngle(new THREE.Vector3(1, 0, 0), state.frameAngle).add(FRAME_LEVEL_PIVOT);
  const rasDelta = rasAnchor.clone().sub(rasBase);
  setBeam(rig, "RearAxleStabilizerBarrel", rasBase, rasBase.clone().addScaledVector(rasDelta, 0.67));
  setBeam(rig, "RearAxleStabilizerRod", rasBase.clone().addScaledVector(rasDelta, 0.52), rasAnchor);

  const sensorBase = logical(-2.15, 1.64, -0.56);
  const sensorAnchor = pivot.clone().add(rotateLogicalBoom(logical(0.35, -0.10, -0.56), state.boomAngle));
  setBeam(rig, "BoomAngleSensorLink", sensorBase, sensorAnchor);
  rig.dynamic.BoomAngleSensorBoomJoint.position.copy(sensorAnchor);
}

function steeringJoint(centerX, centerLateral, angle) {
  const inward = centerLateral < 0 ? 0.16 : -0.16;
  const offset = new THREE.Vector3(-0.12, inward, 0).applyAxisAngle(new THREE.Vector3(0, 0, 1), -angle);
  return new THREE.Vector3(centerX, centerLateral, -0.59).add(offset);
}

function applySteeringLinkages(rig, state) {
  for (const [axle, x, left, right] of [
    ["Front", 1.71, "FL", "FR"], ["Rear", -1.71, "RL", "RR"],
  ]) {
    const leftJoint = steeringJoint(x, -1.05025, state.wheelAngles[left]);
    const rightJoint = steeringJoint(x, 1.05025, state.wheelAngles[right]);
    const leftCap = new THREE.Vector3(x, -0.46, -0.76);
    const rightCap = new THREE.Vector3(x, 0.46, -0.76);
    setBeam(rig, `${axle}SteerCylinderBarrel`, leftCap, rightCap);
    setBeam(rig, `${axle}SteerCylinderRodLeft`, leftCap, leftJoint);
    setBeam(rig, `${axle}SteerCylinderRodRight`, rightCap, rightJoint);
  }
}

export function apply742State(rig, state) {
  rig.frame.rotation.x = state.frameAngle;
  rig.boom.rotation.y = state.boomAngle;
  rig.mid.position.x = rig.authored.midX + state.midTranslation;
  rig.fly.position.x = rig.authored.flyX + state.flyTranslation;
  rig.carriage.rotation.y = state.carriageAngle;
  applyWheelAngles(rig, state);
  applyActuatorRig(rig, state);
  applySteeringLinkages(rig, state);
  rig.root.updateMatrixWorld(true);
}
