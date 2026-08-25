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
- [x] Keep `LiftCylinder` as a contract-only node until its anchors are supported
- [x] Disable the circular range overlay until it can be traced from the manufacturer chart
- [x] Strengthen the GLB validator against receipt hashes, AABB, wheelbase, platform size, hit meshes, scale, and extra scenes
- [x] Generate mechanical receipt facts; keep browser/visual review separately recorded
- [x] Unify showcase release and GLB cache identity
- [x] Prove desktop and 390 × 844 working poses with the real GLB

### M3 — 600S vertical slice (current)

- [x] Remove the third-party CDN startup dependency with a hash-pinned local Three.js runtime
- [x] Add adaptive pixel-ratio, shadow, and frame-rate profiles for desktop and mobile
- [x] Establish neutral product lighting, a lower three-quarter camera, and display-only material tuning
- [ ] Replace blockout wheels with optimized tread, sidewall, rim, and hub geometry
- [ ] Replace boxy exterior covers with evidence-bounded beveled/curved shells and visible panel seams
- [ ] Add platform mesh flooring, gate treatment, fasteners, wear pads, reflectors, and owned decals after slot 12 is resolved
- [ ] Add restrained surface variation through reusable roughness/normal textures; keep the GLB texture budget at or below 4 MB
- [ ] Refine pivot, turntable, and platform geometry only after slots 09–12 are resolved
- [ ] Improve hover/select treatment
- [ ] Validate keyboard access and reduced motion with the real GLB
- [ ] Capture a Chrome performance trace and current-generation source-comparison visual proof

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
