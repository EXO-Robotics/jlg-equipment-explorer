import { ES1930M_CAMERAS, es1930mComponentView, es1930mFollowView } from "./cameras.js";
import { ES1930M_COMPONENTS } from "./inspector.js";
import { applyES1930MState, createES1930MRig, solveES1930MState } from "./articulation.js";
import { ES1930M_GLB_URL, ES1930M_RELEASE } from "./version.js";

export const ES1930M_MACHINE = Object.freeze({
  id: "es1930m",
  release: ES1930M_RELEASE,
  assetUrl: ES1930M_GLB_URL,
  configurationId: "ES1930M-PVC2404-US-STD-FR-FLA130-NM",
  identity: Object.freeze({ manufacturer: "JLG", model: "ES1930M", family: "Micro-Sized Series", pvc: "2404", market: "ANSI/US" }),
  specifications: Object.freeze({ indoorPlatformHeightM: 5.64, outdoorPlatformHeightM: 4.57, capacityKg: 227, widthM: 0.76, lengthM: 1.48, stowedHeightM: 1.98, nominalMassKg: 1351 }),
  controls: Object.freeze([
    Object.freeze({ id: "lift", inputId: "lift-control", outputId: "lift-value", inputDivisor: 100, label: "Platform lift", min: 0, max: 1, step: 0.001, authority: "verified envelope; reconstructed linkage coordinates" }),
    Object.freeze({ id: "deck", inputId: "deck-control", outputId: "deck-value", inputDivisor: 100, label: "Extension deck", min: 0, max: 1, step: 0.001, displayMaximum: "0.55 m", authority: "verified travel" }),
    Object.freeze({ id: "steer", inputId: "steer-control", outputId: "steer-value", inputDivisor: 100, label: "Steering", min: -1, max: 1, step: 0.001, authority: "verified cylinder stroke; reconstructed spindle angles" }),
  ]),
  components: ES1930M_COMPONENTS,
  cameras: ES1930M_CAMERAS,
  requiredNodes: Object.freeze(["ES1930M_ROOT", "Chassis", "ScissorAssembly", "LiftCylinder", "PlatformAssembly", "ExtensionDeck", "FrontSteerAssembly", "PotholeProtection"]),
  interactionVolumes: Object.freeze(["Chassis_Hit", "Scissor_Hit", "Platform_Hit", "Steering_Hit"]),
  stowState: Object.freeze({ lift: 0, deck: 0, steer: 0 }),
  defaultCamera: "default",
  validateAsset(root) {
    const missing = this.requiredNodes.filter((name) => !root.getObjectByName(name));
    const assetRoot = root.getObjectByName("ES1930M_ROOT");
    if (assetRoot?.userData?.configuration_id !== this.configurationId) missing.push("configuration identity");
    return Object.freeze({ ok: missing.length === 0, missing });
  },
  createRig: createES1930MRig,
  solveState(state) {
    return solveES1930MState(state.lift, state.deck, state.steer);
  },
  applyState: applyES1930MState,
  followView: es1930mFollowView,
  componentView: es1930mComponentView,
  presentState(state) {
    const outdoorRatio = (4.57 - 0.90) / (5.64 - 0.90);
    const stowed = state.lift < 0.01 && state.deck < 0.01 && Math.abs(state.steer) < 0.01;
    return Object.freeze({
      outputs: Object.freeze({
        lift: `${Math.round(state.lift * 100)}%`,
        deck: `${(state.deck * 0.55).toFixed(2)} m`,
        steer: Math.abs(state.steer) < 0.01 ? "Center" : `${Math.round(Math.abs(state.steer) * 80)} mm ${state.steer < 0 ? "L" : "R"}`,
      }),
      zone: state.lift > outdoorRatio ? "indoor-only" : state.lift > 0.02 ? "outdoor-limit" : "stowed",
      status: stowed ? "Stowed" : state.lift > outdoorRatio ? "Indoor height zone" : "Mechanism active",
    });
  },
});

export default ES1930M_MACHINE;
