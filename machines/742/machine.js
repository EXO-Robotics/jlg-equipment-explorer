import * as THREE from "three";
import { JLG742_CAMERAS, jlg742ComponentView, jlg742FollowView } from "./cameras.js?v=1.1.3";
import { JLG742_COMPONENTS } from "./inspector.js?v=1.1.3";
import { apply742State, create742Rig, JLG742_MECHANISM, solve742State } from "./articulation.js?v=1.1.4";
import { JLG742_GLB_URL, JLG742_RELEASE } from "./version.js?v=1.1.4";

export const JLG742_MACHINE = Object.freeze({
  id: "742",
  release: JLG742_RELEASE,
  assetUrl: JLG742_GLB_URL,
  configurationId: "742-PVC2411-US-STD-OC-D36-FF370-C50-PF481",
  identity: Object.freeze({ manufacturer: "JLG", model: "742", family: "Telehandler", pvc: "2411", market: "ANSI/US" }),
  specifications: Object.freeze({ capacityKg: 3175, liftHeightM: 12.8, reachM: 8.86, widthM: 2.46, lengthLessForksM: 5.76, heightM: 2.43, massKg: 9645 }),
  controls: Object.freeze([
    Object.freeze({ id: "lift", inputId: "lift-control", outputId: "lift-value", inputDivisor: 100, label: "Boom lift" }),
    Object.freeze({ id: "telescope", inputId: "telescope-control", outputId: "telescope-value", inputDivisor: 100, label: "Boom telescope" }),
    Object.freeze({ id: "tilt", inputId: "tilt-control", outputId: "tilt-value", inputDivisor: 100, label: "Carriage tilt" }),
    Object.freeze({ id: "steer", inputId: "steer-control", outputId: "steer-value", inputDivisor: 100, label: "Steering angle" }),
    Object.freeze({ id: "level", inputId: "level-control", outputId: "level-value", inputDivisor: 100, label: "Frame level" }),
  ]),
  components: JLG742_COMPONENTS,
  cameras: JLG742_CAMERAS,
  requiredNodes: Object.freeze(["742_ROOT","GroundRunningGear","FrameLevelPivot","Chassis","OpenCab","BoomLiftPivot","BoomBase","BoomMid","BoomFly","CarriageTiltPivot","Carriage","SteerPivot_FL","SteerPivot_FR","SteerPivot_RL","SteerPivot_RR"]),
  interactionVolumes: Object.freeze(["Chassis_Hit","Cab_Hit","Boom_Hit","Carriage_Hit","Steering_Hit","Hydraulics_Hit"]),
  stowState: Object.freeze({ lift: 0, telescope: 0, tilt: 0, steer: 0, level: 0, steerMode: "circle" }),
  defaultCamera: "default",
  orbitLimits: Object.freeze({ minDistance: 2.2, maxDistance: 24 }),
  showcaseDurationMs: 48000,
  validateAsset(root) {
    const missing = this.requiredNodes.filter((name) => !root.getObjectByName(name));
    const assetRoot = root.getObjectByName("742_ROOT");
    if (assetRoot?.userData?.configuration_id !== this.configurationId) missing.push("configuration identity");
    return Object.freeze({ ok: missing.length === 0, missing });
  },
  createRig: create742Rig,
  solveState: solve742State,
  applyState: apply742State,
  followView: jlg742FollowView,
  componentView: jlg742ComponentView,
  presentState(state) {
    const degrees = THREE.MathUtils.radToDeg;
    const displayDegrees = (value) => `${Math.abs(value - Math.round(value)) < 0.05 ? Math.round(value) : value.toFixed(1)}°`;
    const angle = degrees(THREE.MathUtils.lerp(JLG742_MECHANISM.boomMinimum, JLG742_MECHANISM.boomMaximum, state.lift));
    const extension = state.telescope * (JLG742_MECHANISM.midTravel + JLG742_MECHANISM.flyTravel);
    const tiltDegrees = state.tilt < 0
      ? state.tilt * degrees(JLG742_MECHANISM.carriageTiltDown)
      : state.tilt * degrees(JLG742_MECHANISM.carriageTiltUp);
    const stowed = state.lift < 0.01 && state.telescope < 0.01 && Math.abs(state.tilt) < 0.01 && Math.abs(state.steer) < 0.01 && Math.abs(state.level) < 0.01;
    return Object.freeze({
      outputs: Object.freeze({
        lift: displayDegrees(angle), telescope: `${extension.toFixed(2)} m visual`,
        tilt: `${Math.round(tiltDegrees)}°`, steer: Math.abs(state.steer) < 0.01 ? "Center" : `${Math.round(Math.abs(state.steer) * degrees(JLG742_MECHANISM.steerMaximum))}° ${state.steer < 0 ? "L" : "R"}`,
        level: Math.abs(state.level) < 0.01 ? "Level" : `${Math.round(Math.abs(state.level) * degrees(JLG742_MECHANISM.frameLevelMaximum))}° ${state.level < 0 ? "L" : "R"}`,
      }),
      zone: stowed ? "stowed" : state.telescope > 0.75 ? "extended" : "active",
      status: stowed ? "Stowed study" : `${state.steerMode} steer · visual mechanism active`,
    });
  },
  showcase(t) {
    const smooth = (a, b, x) => { const p = Math.max(0, Math.min(1, (x-a)/(b-a))); return p*p*(3-2*p); };
    return {
      // Forty-eight seconds keeps the primary boom phases within the published
      // service-manual motion-time bands: lift 12.3 s, extend 11.0 s,
      // retract 11.5 s and lower 9.0 s. Steering/level motion remains a
      // presentation-only visual overlay rather than an operational sequence.
      lift: smooth(0.02,0.27625,t) * (1-smooth(0.79,0.9775,t)),
      telescope: smooth(0.27625,0.50542,t) * (1-smooth(0.55,0.78958,t)),
      tilt: Math.sin(t*Math.PI*2) * 0.35,
      steer: Math.sin(t*Math.PI*4) * 0.55,
      level: Math.sin(t*Math.PI*2) * 0.38,
      steerMode: t < 0.34 ? "circle" : t < 0.67 ? "crab" : "front",
    };
  },
});

export default JLG742_MACHINE;
