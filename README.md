# JLG Equipment Explorer

A static Three.js showcase for unofficial, educational product visualization of access equipment. The root keeps the owned 600S boom lift as the flagship, `/es1930m/` hosts the micro scissor study, and `/742/` adds an owned, evidence-bounded telehandler reconstruction.

## Run locally

From this directory:

```sh
npm start
```

Then open `http://localhost:8080/?v=1.1.5`.

The telehandler showcase is available at `http://localhost:8080/742/?diagnostics=1`.

The required Three.js r160 runtime is version-pinned under `vendor/three-r160`, so the viewer has no startup dependency on a third-party CDN. There is no build step, package install, or network requirement for the interactive model.

Validate the current GLBs, source ledgers, route contracts, and receipts with `npm run check`. For the 742, `npm run receipt:742` independently replays the automated validators and writes a hash-bound candidate receipt. It deliberately leaves browser, visual, accessibility, performance, cross-route regression, and deployment gates pending unless a canonical review manifest binds each gate to an artifact, exact commit, browser, and operating-system environment.

Repository and CI checks run the 742 source ledger in explicit manifest-only mode; their output is `NOT_VERIFIED` for the external binaries. A fail-closed binary recheck requires the separately retained evidence directory:

```sh
python3 -B scripts/validate_742_evidence.py \
  --sources-dir /path/to/frozen-742-evidence \
  --require-source-binaries
```

The candidate receipt is not included in the Pages site. After an authorized Pages deployment, CI probes the public route and exact GLB over HTTP, validates them against the local candidate, and uploads a separate `742-pages-attestation` workflow artifact. That external attestation does not convert pending human gates into passes.

To close the human gates, first write a pending receipt and take its `candidate_tree_sha256`. A review manifest supplied through `python3 -B scripts/write_742_receipt.py --review-manifest <path>` must name that exact tree, an existing 40-character reviewed commit, browser and OS environment, and every canonical gate. Each passed gate must reference a repository-contained artifact by exact path, SHA-256, and byte count. Partial or unbound human review is rejected rather than inferred.

`scripts/validate_742_receipt.py --require-release` is the combined final gate: it requires `--sources-dir` to replay all frozen binaries, a receipt written with that verification, every artifact-backed human gate, and the separate Pages deployment attestation. The Pages workflow itself requests only deployment attestation, so publishing cannot silently turn pending human judgments into release approval.

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

The v1.1 mechanical, hierarchy, provenance, and static viewer contracts pass. A fresh desktop browser run loaded the exact v1.1 GLB, exercised all four motion controls, passed the five-volume self-test, and recorded zero runtime errors. Mobile layout and fixed-camera source overlays remain separate visual gates. Fabrication dimensions and safety/service simulation remain out of scope.

The 742 receipt is a local candidate record, not deployment proof. Automated checks may pass while its human review gates remain explicitly pending. Public availability is proven only by the separate post-deployment HTTP attestation produced by the Pages workflow; the repository never self-certifies an unpublished candidate as deployed.
