# JLG Equipment Explorer

A static Three.js showcase for unofficial, educational product visualization of access equipment. The root keeps the owned 600S boom lift as the flagship, `/es1930m/` hosts the micro scissor study, and `/742/` adds an owned, evidence-bounded telehandler reconstruction.

## Run locally

From this directory:

```sh
npm start
```

Then open `http://localhost:8080/?v=1.1.13`.

The telehandler showcase is available at `http://localhost:8080/742/?diagnostics=1`.

The required Three.js r160 runtime is version-pinned under `vendor/three-r160`, so the viewer has no startup dependency on a third-party CDN. There is no build step, package install, or network requirement for the interactive model. The separate browser-evidence runner does use the exact Playwright development dependency pinned in `package-lock.json`.

Validate the current GLBs, source ledgers, route contracts, and receipts with `npm run check`. The standard 742 gate is host-portable: it parses the actual committed GLB with Python's standard library, applies the production JavaScript solver output to the exported node rig, and verifies the named stow, lift, reach, steering, hose, and clearance contracts without starting Blender. The pinned Blender 5.1.1 posed-GLB validator remains a distinct CI and authoring companion and runs explicitly in the Pages workflow alongside the double deterministic rebuild. For the 742, `npm run receipt:742` independently replays the portable automated validators and writes a hash-bound candidate receipt; it records the Blender companion contract without claiming that companion ran locally. It deliberately leaves browser, visual, accessibility-semantics-and-keyboard, performance, cross-route regression, deterministic rebuild, and deployment gates pending unless their separate evidence is supplied.

Repository and CI checks run the 742 source ledger in explicit manifest-only mode; their output is `NOT_VERIFIED` for the external binaries. A fail-closed binary recheck requires the separately retained evidence directory:

```sh
python3 -B scripts/validate_742_evidence.py \
  --sources-dir /path/to/frozen-742-evidence \
  --require-source-binaries
```

The candidate receipt and manufacturer source binaries are not included in the Pages site. Before an authorized deployment, CI downloads the private `742-frozen-source-evidence` artifact from the exact Actions run named by `JLG742_SOURCE_EVIDENCE_RUN_ID` and replays all 11 source hashes. The deployment workflow itself then performs the pinned-Blender deterministic double rebuild and the separate pinned-Blender posed-GLB companion gate against its exact source commit. After deployment it retrieves the public build manifest and verifies every listed public response—not only the 742 subset—at HTTP 200 with the exact manifest SHA-256 and byte count. The external schema-3 attestation binds the private source replay, current-workflow rebuild, complete deployed manifest, candidate receipt, exact source commit, and deployment workflow run without packaging private source binaries.

To close the human gates, first write a pending receipt, commit the exact candidate, and take its `candidate_tree_sha256`. Repeat the checklist in `docs/review/742/CAPTURE_REQUIREMENTS.json` against that frozen candidate. Each browser gate requires schema-2 raw evidence: exact browser/OS/GPU metadata, the repository lockfile plus bundled Chromium revision and canonical full application/resource-bundle digest, DOM and full applicable accessibility-tree snapshots, exact screenshot and automation-trace records, and raw frame-interval arrays for the performance gate. One generic boolean report cannot satisfy multiple gates. The twelve Blender PNGs and browser-capture artifacts use separate exact allowlists. Ten mechanism renders are individually tied to named semantic claims; stowed and cab renders remain distinct gates. The browser-capture allowlist remains empty in the pending candidate and is excluded from its candidate-tree digest; after capture, the completed human-review binding records that populated allowlist by exact path, hash, and byte count and requires every admitted capture to be consumed by a semantically validated gate. The accessibility gate proves browser semantics, exact unit-bearing engineering text exposed through Chromium AX relationships, and keyboard behavior only—it does not claim VoiceOver, NVDA, or physical assistive-technology testing. Regression evidence binds the current 600S release and the ES1930M 1.0.4 asset with its separately qualified 1.0.7 runtime.

The repository-owned browser replay is:

```sh
npm ci
npm run capture:742:install
npm run capture:742 -- --port=8092
```

After the observations and final visual comparisons have actually been repeated, the explicit command below updates only candidate/commit bindings and manifest records, then semantically parses every gate. It rolls back all writes on failure; binding cannot create observations by itself.

```sh
python3 -B scripts/bind_742_review.py \
  --reviewed-source-commit <40-character-commit> \
  --confirm-browser-observations-reviewed \
  --confirm-visual-observations-reviewed
```

Before release qualification, generate a byte-identical rebuild attestation with the retained Blender version:

```sh
python3 -B scripts/verify_742_deterministic_rebuild.py \
  --blender /path/to/Blender \
  --output /path/to/742-deterministic-rebuild-attestation.json

BLENDER_BIN="/path/to/Blender" \
  python3 -B scripts/run_742_posed_glb_gate.py \
  > /path/to/742-blender-posed-glb-result.json
```

The rebuild attestation and posed-GLB companion result are separate records. The standard portable gate remains authoritative for ordinary restricted `npm run check` execution; release CI additionally requires the pinned Blender companion command to succeed.
The deterministic rebuild contract applies to the exported GLB bytes. The `.blend` source container remains hash-bound as a candidate input, but Blender may rewrite session/container identity bytes across clean saves even when repeated exports are byte-identical; the receipt and rebuild proof do not claim byte-deterministic `.blend` serialization.

`scripts/validate_742_receipt.py --require-release` is the combined final gate. It requires `--sources-dir` for a fresh replay of every frozen binary, a receipt originally written with that same verification, every semantically parsed review gate, the byte-identical GLB rebuild attestation, and the separate Pages deployment attestation:

```sh
python3 -B scripts/validate_742_receipt.py \
  --sources-dir /path/to/frozen-742-evidence \
  --deployment-attestation /path/to/742-pages-http-attestation.json \
  --rebuild-attestation /path/to/742-deterministic-rebuild-attestation.json \
  --require-release
```

`--require-deployed` also requires the frozen-source directory, a fresh replay, and all review gates. `--require-release` additionally requires the deterministic rebuild proof generated in the current deployment workflow and the schema-3 deployment attestation. If the retained source set, current-run rebuild proof, source commit, review binding, public manifest, or any public response is absent or inconsistent, deployment/release qualification fails closed. Manufacturer binaries are never placed in the Pages bundle.

## What is ready

- Orbit, wheel zoom, pinch zoom, inertia, idle drift, and reset
- Procedural 600S-style proxy with named, articulated assemblies
- Boom lift, telescope, turntable, and steering controls
- Autonomous oval presentation route with bicycle-model steering, rolling wheels, live heading/loop telemetry, route recovery, pause-to-manual control, and six-second per-channel overrides
- Stow sequence, clickable component focus, and inspector copy
- Responsive desktop/mobile interface and reduced-motion support
- Keyboard orbit, zoom, component inspection, reset, focus-trapped inspector, and visible focus treatment
- WebGL failure state, loading progress, and a delayed-start diagnostic
- Adaptive desktop/mobile/economy render profiles for pixel ratio, shadows, and frame rate
- Neutral product-lighting look development with display-only material tuning
- Independently typeset runtime markings, per-part finish variation, moving hover/focus outlines, and opt-in diagnostics
- A documented Blender-to-GLB node contract
- A documented, local-only official Blender MCP setup
- A native `/742/` route with five articulated channels, three selectable steering modes, deterministic showcase motion, seven component views, pinch/inertia orbit controls, and p95 frame diagnostics
- An owned 742 reconstruction covering detailed rough-terrain running gear, open cab/interior, compound engine bodywork, three boom sections, visible hydraulic cues, 50-inch carriage, and 48-inch pallet forks; exact geometry metrics are derived by the GLB validator and bound into the current candidate receipt
- A complete hash-frozen PVC 2411 operation/service/parts/hydraulic/electrical source family, current spec/brochure, three official gallery views, and a research-only BIM boundary
- An owned Blender detailed reconstruction loaded as the primary `600s.glb`
- PVC 2607 configuration identity frozen as `600S-PVC2607-US-B3-2WS-D29-FF-RRP3696`
- Detailed B3 enclosure, chassis, four-wheel 4WD/2WS running gear, three-section boom, staged powertrack, platform controls, SkyGuard, and evidence-bounded linkage solvers
- Separate coupled MidBoom/FlyBoom transforms, moving steering cylinders/tie rod, tower/tension links, starting-angle platform leveling, and positive nested overlap through the visual travel cap
- Distinct hydraulic-hose, electrical-loom, control-cable, telescope-wire-rope, and powertrack-carrier material identities
- A hash-bound mechanism evidence pack with page-level current-PVC claims and explicit cross-PVC quarantine
- Research and source-ledger templates that separate verified public facts from working assumptions

## Project structure

```text
.
├── index.html
├── viewer.css
├── viewer.js
├── assets/models/
├── scripts/
├── source/blender/
├── vendor/three-r160/
└── docs/
    ├── BUILD_PLAN.md
    ├── BLENDER_MCP.md
    ├── MODEL_CONTRACT.md
    └── research/600s/
```

## Deliberate boundary

The Blender reconstruction is a visual interaction model, not an engineering model. Dimensions, motion limits, load information, hydraulic or electrical routing, and operating envelopes must not be treated as fabrication, service, training, or safety data. Public specifications are captured in the research ledger with a URL, publication identifier, access date, and verification status before they become authoritative UI copy.

## License and use

Copyright © 2026 EXO-Robotics. All rights reserved.

This is a publicly viewable portfolio repository, not an open-source project.
No permission is granted to run, copy, modify, redistribute, deploy, or use the
original project materials commercially or internally without a separate
written license. This restriction applies to every person and organization,
including JLG Industries and its affiliates.

GitHub may permit users to view and fork a public repository under its terms,
but that does not grant a license to use its contents. See [`LICENSE`](LICENSE)
for the controlling notice and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the separately licensed
Three.js runtime and third-party ownership boundaries.

## Current acceptance gate

The v1.1 mechanical, hierarchy, provenance, and static viewer contracts pass. A fresh local desktop and mobile browser run loaded the exact v1.1 GLB, exercised all four motion controls, passed the five-volume self-test, and recorded zero runtime errors. Fixed-camera paired source overlays remain a separate visual gate. Fabrication dimensions and safety/service simulation remain out of scope.

The 742 receipt is a local candidate record, not deployment proof. Its human-review state is valid only for the exact candidate tree and reviewed source commit recorded in the receipt; any source change requires a new pending transition and fresh binding. Public availability requires a separate post-deployment HTTP attestation, and the repository never self-certifies an unpublished candidate as deployed.
