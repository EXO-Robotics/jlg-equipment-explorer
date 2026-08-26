#!/usr/bin/env node
// Executable bridge to the exact production solver in machines/742/articulation.js.
// Blender and Python validation call this bridge instead of maintaining a
// second kinematic implementation.

import { readFileSync } from "node:fs";
import { JLG742_MECHANISM, solve742RigGeometry, solve742State } from "../machines/742/solver.js";

const input = process.argv[2] === "-" ? readFileSync(0, "utf8") : process.argv[2];
if (!input) throw new Error("usage: node scripts/solve_742_pose.mjs '<state-json>'");
const request = JSON.parse(input);
const states = Array.isArray(request) ? request : [request];
const results = states.map((state) => {
  const solved = solve742State(state);
  const geometry = solve742RigGeometry(solved);
  return {
    state: {
      ...solved,
      wheelAngles: solved.wheelAngles,
    },
    geometry,
    mechanism: {
      barrelLengths: JLG742_MECHANISM.barrelLengths,
      rodOverlap: JLG742_MECHANISM.rodOverlap,
    },
  };
});
process.stdout.write(JSON.stringify(Array.isArray(request) ? results : results[0]));
