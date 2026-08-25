# JLG Equipment Explorer

A static Three.js prototype for an unofficial, educational product visualization of access equipment. Version 1 starts with a procedural 600S-style blockout so the interaction, articulation hierarchy, and responsive interface can be proven before a Blender asset is ready.

## Run locally

From this directory:

```sh
npm start
```

Then open `http://localhost:8080`.

The prototype loads Three.js from jsDelivr, so the first run needs network access. There is no build step and no package install.

## What is ready

- Orbit, wheel zoom, pinch zoom, inertia, idle drift, and reset
- Procedural 600S-style proxy with named, articulated assemblies
- Boom lift, telescope, turntable, and steering controls
- Stow sequence, range guide, clickable component focus, and inspector copy
- Responsive desktop/mobile interface and reduced-motion support
- WebGL failure state and loading state
- A documented Blender-to-GLB node contract
- A documented, local-only official Blender MCP setup
- An owned Blender structural blockout loaded as the primary `600s.glb`
- Real GLB swing, lift, telescope, steering, stow, orbit, and component selection
- Research and source-ledger templates that separate verified public facts from working assumptions

## Project structure

```text
.
├── index.html
├── viewer.css
├── viewer.js
├── assets/
│   └── models/
│       └── README.md
└── docs/
    ├── BUILD_PLAN.md
    ├── BLENDER_MCP.md
    ├── MODEL_CONTRACT.md
    └── research/
        ├── 600s.md
        └── 600s/
            ├── REFERENCES.md
            ├── DIMENSIONS.md
            ├── ARTICULATION.md
            └── reference-board/
                └── README.md
```

## Deliberate boundary

The proxy model is a visual interaction blockout, not an engineering model. Dimensions, motion limits, load information, and operating envelopes must not be treated as fabrication, service, training, or safety data. Public specifications should be captured in the research ledger with a URL, publication identifier, access date, and verification status before they become authoritative UI copy.

## Next gate

Keep the accepted structural blockout and procedural fallback stable while
resolving reference-board slots 09–12. Refine the boom pivot, turntable, and
platform only when those sources support the change. Then validate keyboard
access, reduced motion, performance, and source-comparison visuals before
extracting a reusable machine layer.
