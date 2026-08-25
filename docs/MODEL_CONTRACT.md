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
│   ├── Wheel_FR
│   ├── Wheel_RL
│   └── Wheel_RR
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
            ├── TowerLinkLower
            └── TowerLinkUpper

Turntable also owns the evidence-bounded `LiftCylinder` assembly so the viewer can
solve it between a turntable-side lower anchor and boom-side upper anchor as the
boom moves. A rigid cylinder parented to the moving boom is not acceptable for the
detailed release.
```

Optional visible nodes may be added freely. Animation code must only require the nodes above.

## Pivot rules

- `TurntablePivot`: local origin at the center of the slew bearing; local Y is the swing axis.
- `BoomPivot`: local origin at the physical boom hinge; local Z is the lift axis.
- `Telescope`: local X points from the boom pivot toward the platform; extension is positive X. It is the motion group for the nested `MidBoom` and `FlyBoom` reconstruction.
- Front wheel nodes: local Y is the steering axis.
- `PlatformPivot`: local origin is the platform-leveling/rotation center; the viewer counter-rotates local Z against boom lift.
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
`Telescope_Hit` maps to the viewer's `boom` component while following the
independently translating `Telescope` node.

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
