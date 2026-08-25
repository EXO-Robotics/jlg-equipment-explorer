// Compatibility description for the proven pre-interface 600S runtime.
// The root viewer remains its execution authority until parity gates permit extraction.
import { SHOWCASE_RELEASE } from "../../assets/models/600s.version.js";

export const MACHINE_600S_COMPATIBILITY = Object.freeze({
  id: "600s",
  release: SHOWCASE_RELEASE,
  route: "../600s/",
  legacyRoute: "../",
  assetUrl: "../assets/models/600s.glb",
  configurationId: "600S-PVC2607-US-B3-2WS-D29-FF-RRP3696",
  identity: Object.freeze({ manufacturer: "JLG", model: "600S", family: "Telescopic Boom Lift", pvc: "2607", market: "ANSI/US" }),
  controls: Object.freeze(["boom", "extend", "rotate", "steer"]),
  components: Object.freeze(["chassis", "turntable", "boom", "platform"]),
  compatibilityMode: "legacy-root-runtime",
  extractionGate: "existing receipt, runtime hash, articulation, selection, responsive and browser checks must remain passing",
});

export default MACHINE_600S_COMPATIBILITY;
