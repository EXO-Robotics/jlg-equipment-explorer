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
            │   └── Telescope
            │       └── PlatformPivot
            │           └── Platform
            └── LiftCylinder
```

Optional visible nodes may be added freely. Animation code must only require the nodes above.

## Pivot rules

- `TurntablePivot`: local origin at the center of the slew bearing; local Y is the swing axis.
- `BoomPivot`: local origin at the physical boom hinge; local Z is the lift axis.
- `Telescope`: local X points from the boom pivot toward the platform; extension is positive X.
- Front wheel nodes: local Y is the steering axis.
- `PlatformPivot`: local origin is the platform-leveling/rotation center.
- `Platform`: should remain a distinct child even while leveling is deferred.

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
- Apply object scale before export.
- Keep the root at world origin with the ground plane at Y = 0.
- Export +Y up and +Z forward using Blender's glTF exporter defaults.
- Avoid negative scales, unapplied mirrored transforms, and material names generated from temporary imports.

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
