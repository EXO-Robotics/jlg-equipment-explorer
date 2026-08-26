# Blender to GLB contract

The web viewer should depend on a small, stable node hierarchy rather than Blender-specific object organization.

## Required nodes

```text
600S_ROOT
├── Chassis
│   ├── Frame
│   ├── AxleFront
│   ├── AxleRear
│   ├── Wheel_FL
│   │   └── Wheel_FL_Roll
│   ├── Wheel_FR
│   │   └── Wheel_FR_Roll
│   ├── Wheel_RL
│   │   └── Wheel_RL_Roll
│   └── Wheel_RR
│       └── Wheel_RR_Roll
└── TurntablePivot
    └── Turntable
        ├── EngineCover
        ├── Counterweight
        ├── Controls
        └── BoomPivot
            ├── MainBoom
            │   ├── Powertrack
            │   └── Telescope
            │       └── MidBoom
            │           └── FlyBoom
            │               └── PlatformPivot
            │                   ├── PlatformRotator
            │                   └── Platform
            │                       ├── PlatformSwingGate
            │                       ├── PlatformConsole
            │                       └── PlatformFootswitch
            ├── TowerLink
            └── TensionLink

Turntable also owns the evidence-bounded `LiftCylinder`, `TowerLink`, and
`TensionLink` visual-solver assemblies so the viewer can
solve it between a turntable-side lower anchor and boom-side upper anchor as the
boom moves. A rigid cylinder parented to the moving boom is not acceptable for the
detailed release.
```

Optional visible nodes may be added freely. Animation code must only require the nodes above.

## Pivot rules

- `TurntablePivot`: local origin at the center of the slew bearing; local Y is the swing axis.
- `BoomPivot`: local origin at the physical boom hinge; local Z is the lift axis.
- `Telescope`: stable UI/controller boundary. `MidBoom` and `FlyBoom` each translate
  in positive local X under one evidence-bounded coupled visual control. The
  exported split is presentation-only and must not be labeled as a factory ratio.
- Front wheel nodes: local Y is the steering axis. Their `*_Roll` children own only
  the tire, rim, drive hub, lugs, and tread meshes; knuckles and steering anchors
  remain on the yaw-only parent so they cannot tumble with tire rotation.
- `PlatformPivot`: local origin is the reconstructed platform-leveling/rotation
  center; the viewer preserves the operator-set starting angle and solves a
  visible `PlatformLevelCylinder`. This is not gravity auto-leveling.
- `Platform`: remains a distinct child of `PlatformPivot`. Platform rotation about the rotator axis is still deferred.

## Interaction volumes

Selection must not depend on render topology. The GLB may include simple non-rendered meshes with these exact names, or the viewer may create equivalent primitives after load:

```text
Chassis_Hit
Turntable_Hit
Boom_Hit
Telescope_Hit
Platform_Hit
```

Hit meshes should be boxes or low-segment capsules, should follow the articulated parent they represent, and should remain independent of material or topology changes in the visible model.
`Telescope_Hit` maps to the viewer's `boom` component while following `FlyBoom`,
the furthest independently translating telescope stage.

## Units and transforms

- Model in meters.
- Export identity object scale. If a node is scaled, apply that scale before export.
- Keep the root at world origin with the ground plane at Y = 0.
- Export +Y up and +Z forward using Blender's glTF exporter defaults.
- Avoid negative scales, unapplied mirrored transforms, and material names generated from temporary imports.
- Every detailed node must carry an `authority` extra with one of `verified`, `derived`, `reconstructed`, or `deferred`.
- The target configuration is frozen in `assets/models/600s.configuration.json`; a model built from a different steering, engine, tire, hood, platform, market, or serial-family branch is a different asset.

## Web budget

- Target 20k–60k rendered triangles for the final machine.
- Prefer one 2K texture atlas or a small set of reusable PBR materials.
- Keep draw calls below 100 on the machine.
- Use mesh compression only after an uncompressed GLB is proven in the viewer.
- Runtime-only product/model markings must be independently typeset and tagged `independently-typeset-nominative-mark`; copied manufacturer artwork is not admitted.
- Hover and focused-component outlines must be children of the five hit volumes so they follow articulation without changing selection topology.

## Acceptance checks

1. GLB loads with no console error.
2. All required nodes resolve by exact name.
3. Lift, extension, swing, and steering occur around the intended pivots.
4. Each component can be selected with a practical hit target.
5. The stowed pose matches the public reference board visually.
6. Mobile orbit and controls remain usable at 390 × 844 CSS pixels.
7. The final asset's provenance and license are recorded.
8. Dedicated component hit volumes resolve and remain aligned through the full visual motion range.
9. The inner boom remains nested through 100% of the GLB's visual telescope travel.
10. Platform deck world-up stays within about 2° of vertical at 0°, 36°, and 72° lift.
11. Lower-chassis ground clearance remains 0.29 m and modeled tailswing remains 1.22 m, within the reconstruction drift tolerance.
12. `LiftCylinder` must use the evidence-bounded two-anchor visual solver. Its exported lower and upper anchors are visually reconstructed, not fabrication measurements, and false fixed-to-boom cylinder motion is not acceptable.
13. Keyboard orbit, zoom, component focus, reset, dialog focus restoration, and reduced-motion snapping remain functional with the real GLB.
14. Runtime diagnostics identify the actual model source, self-test all five hit volumes, count uncaught runtime errors, and sample frame pacing without presenting the result as engineering validation.
15. `MidBoom` and `FlyBoom` receive independent positive-X transforms under the
    single telescope control; both retain positive overlap at 100% visual travel.
16. `TowerLink`, `TensionLink`, both steer cylinders, `SteerTieRod`, and
    `PlatformLevelCylinder` resolve as empty two-anchor visual-solver groups.
17. Electrical loom, control cable, telescope wire rope, hydraulic hose, and
    powertrack carrier resolve as distinct material identities.
18. Any displayed powertrack link count is presentation sampling, not a physical
    link-count claim.
19. All four `Wheel_*_Roll` transforms remain distinct from steering/axle transforms;
    steer knuckles, rear axle ends, cylinder anchors, and tie-rod anchors must not
    inherit tire roll.
20. Both reconstructed steering hoses retain a fixed chassis leg and a two-anchor
    moving visual leg whose wheel-side endpoint follows the steering pivot.
21. `PowertrackBend` and `PowertrackMovingRun` inherit the same telescope stage so
    their relative spacing cannot open during FlyBoom travel.
22. The fly-attached `PowertrackPushTube` retains at least 0.004 m of three-axis
    AABB engagement with the mid-stage carrier bend in both stowed and full
    evidence-bounded telescope poses; the engagement check is topological and
    does not promote reconstructed bracket coordinates to fabrication data.
