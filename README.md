# JLG Equipment Explorer

A static Three.js prototype for an unofficial, educational product visualization of access equipment. Version 0.2 loads an owned Blender 600S structural blockout as the primary machine and keeps a procedural model only as a degraded fixture.

## Run locally

From this directory:

```sh
npm start
```

Then open `http://localhost:8080/?v=0.2.0`.

The required Three.js r160 runtime is version-pinned under `vendor/three-r160`, so the viewer has no startup dependency on a third-party CDN. There is no build step, package install, or network requirement for the interactive model.

Validate the current GLB, source, receipt, release identity, and cache manifest with `npm run check`. After an intentional Blender export, regenerate computed receipt facts with `npm run receipt`; review flags are preserved only when both the GLB and source `.blend` hashes are unchanged.

## What is ready

- Orbit, wheel zoom, pinch zoom, inertia, idle drift, and reset
- Procedural 600S-style proxy with named, articulated assemblies
- Boom lift, telescope, turntable, and steering controls
- Stow sequence, clickable component focus, and inspector copy
- Responsive desktop/mobile interface and reduced-motion support
- WebGL failure state, loading progress, and a delayed-start diagnostic
- Adaptive desktop/mobile/economy render profiles for pixel ratio, shadows, and frame rate
- Neutral product-lighting look development with display-only material tuning
- A documented Blender-to-GLB node contract
- A documented, local-only official Blender MCP setup
- An owned Blender structural blockout loaded as the primary `600s.glb`
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

The Blender blockout is a visual interaction model, not an engineering model. Dimensions, motion limits, load information, and operating envelopes must not be treated as fabrication, service, training, or safety data. Public specifications should be captured in the research ledger with a URL, publication identifier, access date, and verification status before they become authoritative UI copy.

## Next gate

Keep the mechanically validated M2.1 blockout stable while resolving reference-board slots
09–12. The next realism pass may safely refine materials, lighting, tire tread,
rounded enclosure surfaces, mesh flooring, fasteners, and decals from current-generation
appearance references. Refine boom-pivot, turntable, cylinder, telescope, and platform-rotator
geometry only when the missing sources support those changes. Then validate keyboard access,
reduced motion, performance, and source-comparison visuals before extracting a reusable machine layer.
