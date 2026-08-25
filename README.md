# JLG Equipment Explorer

A static Three.js showcase for an unofficial, educational product visualization of access equipment. Version 1.0 loads an owned, evidence-bounded Blender reconstruction of the current-generation 600S as the primary machine and keeps a procedural model only as a degraded fixture.

## Run locally

From this directory:

```sh
npm start
```

Then open `http://localhost:8080/?v=1.0.0`.

The required Three.js r160 runtime is version-pinned under `vendor/three-r160`, so the viewer has no startup dependency on a third-party CDN. There is no build step, package install, or network requirement for the interactive model.

Validate the current GLB, source, receipt, release identity, and cache manifest with `npm run check`. After an intentional Blender export, regenerate computed receipt facts with `npm run receipt`; review flags are preserved only when both the GLB and source `.blend` hashes are unchanged.

## What is ready

- Orbit, wheel zoom, pinch zoom, inertia, idle drift, and reset
- Procedural 600S-style proxy with named, articulated assemblies
- Boom lift, telescope, turntable, and steering controls
- Stow sequence, clickable component focus, and inspector copy
- Responsive desktop/mobile interface and reduced-motion support
- Keyboard orbit, zoom, component inspection, reset, focus-trapped inspector, and visible focus treatment
- WebGL failure state, loading progress, and a delayed-start diagnostic
- Adaptive desktop/mobile/economy render profiles for pixel ratio, shadows, and frame rate
- Neutral product-lighting look development with display-only material tuning
- Independently typeset runtime markings, per-part finish variation, moving hover/focus outlines, and opt-in diagnostics
- A documented Blender-to-GLB node contract
- A documented, local-only official Blender MCP setup
- An owned Blender detailed reconstruction loaded as the primary `600s.glb`
- PVC 2607 configuration identity frozen as `600S-PVC2607-US-B3-2WS-D29-FF-RRP3696`
- Detailed B3 enclosure, chassis, four-wheel 4WD/2WS running gear, three-section boom, powertrack, platform controls, SkyGuard, and evidence-bounded lift-cylinder solver
- Independent GLB and procedural motion profiles, platform leveling, and nested telescope travel
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

The v1.0 mechanical, hierarchy, provenance, and static viewer contracts pass. Browser review remains a separate gate: verify the real GLB on desktop and mobile, exercise motion and keyboard access, inspect the five-volume self-test and error counter, then record only the visual comparisons actually observed. Fabrication dimensions and safety/service simulation remain out of scope.
