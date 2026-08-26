# Build plan

## Visual thesis

An industrial product study presented like a dark technical stage: one safety-orange machine, precise typography, restrained controls, and no simulated jobsite clutter.

## Content plan

1. Primary workspace: full-canvas interactive machine.
2. Operate: four constrained transformations plus stow and view reset.
3. Explore: component focus with short technical explanations.
4. Context: headline public specifications and a visible non-engineering disclaimer.

## Interaction thesis

- The camera should feel physical through drag inertia, pinch zoom, and slow idle drift.
- Machine controls should interpolate smoothly rather than snap.
- Selecting a component should move the camera and reveal one focused explanation.

## Milestones

### M0 — Foundation (complete)

- Static, no-build Three.js viewer
- Procedural 600S-style proxy
- Articulation, picking, responsive UI, and documentation contracts

### M1 — Evidence freeze (complete)

- [x] Capture official product-page URLs and access dates
- [x] Record the current PVC 2607 manual identifiers and quarantine the PVC 2601 schematics
- [x] Save a 12-slot reference-board inventory without redistributing restricted assets
- [x] Resolve current/legacy dimensional applicability and the restricted/unrestricted capacity labels
- [x] Download and inspect the current parts, service, and operation manuals outside the deployable repository
- [x] Capture the exact current boom, chassis/turntable, pivot, and platform pages
- [x] Freeze one current B3/2WS/D2.9/foam-filled/36x96 rapid-platform configuration
- [x] Resolve the platform-detail gate with the current B3 platform and console assemblies

### M2 — Blender blockout v0.1 (complete)

Stowed envelope, hierarchy, selection, and transform integration accepted; working-pose silhouette deferred to M2.1.

- [x] Establish the 8.71 × 2.48 × 2.50 m overall envelope in meters
- [x] Match the 2.50 m wheelbase and 0.91 × 2.44 m platform envelope
- [x] Export the exact required hierarchy and five interaction volumes
- [x] Prove swing, lift, telescope, steering, stow, orbit, and component selection in the existing viewer
- [x] Prove the 390 × 844 mobile layout with the real GLB
- [x] Replace primary proxy geometry with the owned blockout GLB while retaining the procedural fallback as a degraded fixture

### M2.1 — Motion integration hardening (complete)

- [x] Separate GLB and procedural motion profiles
- [x] Cap GLB telescope travel so the inner section stays nested through 100%
- [x] Counter-rotate `PlatformPivot` against boom lift
- [x] Constrain modeled ground clearance and tailswing to the published outer dimensions
- [x] Replace the contract-only lift cylinder with a two-anchor visual solver once the current service/parts assemblies support the relationship
- [x] Disable the circular range overlay until it can be traced from the manufacturer chart
- [x] Strengthen the GLB validator against receipt hashes, AABB, wheelbase, platform size, hit meshes, scale, and extra scenes
- [x] Generate mechanical receipt facts; keep browser/visual review separately recorded
- [x] Unify showcase release and GLB cache identity
- [x] Prove desktop and 390 × 844 working poses with the real GLB

### M3 — 600S vertical slice (current)

- [x] Remove the third-party CDN startup dependency with a hash-pinned local Three.js runtime
- [x] Add adaptive pixel-ratio, shadow, and frame-rate profiles for desktop and mobile
- [x] Consolidate 408 authored detail meshes into 92 observed runtime meshes without collapsing articulation, wheel-roll/hose solvers, or hit volumes
- [x] Establish neutral product lighting, a lower three-quarter camera, and display-only material tuning
- [x] Replace blockout wheels with modeled foam-filled tire, tread, rim, drive-hub, lug, and front-steer geometry
- [x] Replace boxy exterior covers with evidence-bounded B3 profiled shells, panel seams, latches, service labels, and rear cooling grille
- [x] Add platform flooring, swing-gate treatment, control console, footswitch, SkyGuard, lanyard points, labels, and orange rail finish
- [x] Add visible hydraulic/electrical cues for the steering circuit, main valve bank, lift cylinder, boom, platform rotator, ground controls, engine, and platform harness
- [ ] Add restrained surface variation through reusable roughness/normal textures; keep the GLB texture budget at or below 4 MB
- [x] Refine the evidence-supported pivot, slew ring, tower links, rapid-replace platform support, and rotator relationship while classifying undimensioned offsets as reconstructed
- [x] Improve hover/select treatment with hit-volume-aligned moving outlines
- [x] Validate keyboard access and reduced motion with the real GLB in Safari
- [ ] Capture a Chrome performance trace and current-generation source-comparison visual proof

### M3.1 — v1.1 mechanism-authority pass (mechanical complete; visual review current)

- [x] Freeze and validate a page-level mechanism evidence pack with source hashes
- [x] Reject legacy cylinder `1683618` and legacy 228 in/57-link powertrack claims as current authority
- [x] Drive distinct MidBoom and FlyBoom transforms under one explicitly reconstructed control
- [x] Add current telescope cylinder, extend/retract rope, and sheave topology cues
- [x] Replace static tower/tension, steering-cylinder, tie-rod, and platform-level dressing with moving two-anchor solvers
- [x] Split powertrack into base run, moving run, bend, support, and push-tube groups without claiming an exact link count
- [x] Separate hydraulic, electrical, control-cable, wire-rope, and carrier material identities
- [x] Correct the current-gallery fly section to orange while retaining cream base/mid sections
- [x] Pass the v1.1 mechanical, hierarchy, evidence, static-viewer, five-volume direct-selection, and desktop runtime gates
- [x] Capture fresh v1.1 390 × 844 mobile proof
- [ ] Capture fixed-camera source overlays

### M4 — Reusable machine layer

- Move specification, node mappings, limits, component copy, and focus poses into machine configuration
- Add 600AJ only after the 600S slice passes
- Add ES1930M after the articulating-boom pipeline is stable

## Explicit non-goals

- Hydraulic, load, stability, collision, or safety simulation
- Drivetrain and terrain physics
- Internal assemblies not supported by public references
- Fabrication-grade dimensions
- Redistribution of manufacturer BIM or commercial meshes without permission
