# 600S articulation authority

This file separates currently verified product motion from prototype-only controls.

## Verified current behavior

| System | Published evidence | Viewer status |
|---|---|---|
| Turntable swing | 360 degrees continuous (R01/R02) | implemented as a bounded demonstration slider; continuous-mode UI deferred |
| Main boom elevation | visibly shown through the R02 reach diagram | implemented visually; exact angular limits are not yet verified |
| Telescope extension | PVC 2607 verifies Base/Mid/Fly sections, cylinder `1001309294`, extend/retract ropes, and sheaves | one control drives separate `MidBoom` and `FlyBoom` visual transforms; exact stroke and ratio remain unresolved |
| Platform leveling | PVC 2607 service page 36 establishes electronic starting-angle retention through a level cylinder and two angle sensors | starting-angle counter-rotation plus a moving two-anchor level-cylinder cue; not gravity auto-leveling |
| Platform rotation | 160 degrees hydraulic (R02) | node contract prepared; control deferred |
| Steering | frozen 2WS parts branch establishes two steer cylinders, one tie rod, knuckles, and kingpins | front wheels, both cylinder rod ends, and tie-rod ends move together; exact angle/anchors are reconstructed |
| Axle oscillation | 8 in / 20 cm (R01/R02) | not implemented |

## Current visual motion limits

These are interaction-test values, not JLG operating data. The Blender GLB and the procedural degraded fixture have independent travel profiles.

| Control | GLB blockout | Procedural fixture | Authority status |
|---|---:|---:|---|
| Boom slider | 0 to 72 degrees | 0 to 72 degrees | visual approximation |
| Telescope slider | 0 to 100% mapped to 1.52 m Mid + 2.28 m Fly visual staging | 0 to 100% mapped to 3.8 m | visual approximation; GLB total, full nested-shell lengths, and split are overlap-bounded presentation values |
| Turntable slider | -180 to +180 degrees | -180 to +180 degrees | UI representation of verified continuous swing, not a physical stop |
| Steering slider | -28 to +28 degrees | -28 to +28 degrees | visual approximation |
| Platform leveling | retain starting angle and solve visible level cylinder | counter-rotate `PlatformPivot` | visual only; not gravity auto-leveling |

The production UI retains a visible `presentation-only motion limits` disclaimer because these values remain unverified.

## Reach-envelope policy

- R02 contains separate 600 lb unrestricted and 1,000 lb restricted work zones.
- A future web overlay may be traced as an illustrative silhouette only.
- The overlay must be labeled approximate and non-operational.
- Do not expose load-placement advice, stability calculations, collision claims, or safe-working determinations.
- Do not extrapolate beyond the visible manufacturer chart.

## Manual questions still open for M3 geometry

1. Current main-boom minimum and maximum elevation angles.
2. Current telescope physical stroke, nested-section rest position, and Mid-to-Fly transform ratio.
3. Dimensioned platform-level cylinder, rotator, and sensor-pin coordinates.
4. Platform-rotator center, neutral pose, and allowed direction split within the published 160 degrees.
5. Exact steering modes available on the modeled configuration.
6. Dimensioned lift-cylinder base and rod-end anchor positions; current anchors establish only a visually supported relationship.
7. Whether standalone PVC 2601 schematics apply to the PVC 2607 machine beyond provisional taxonomy.
8. Frozen-B3 powertrack clamp branch, link count, pitch, and attachment coordinates.

## Animation hierarchy

```text
600S_ROOT
└── TurntablePivot          Y swing axis
    └── Turntable
        ├── BoomPivot       Z lift axis
        │   └── MainBoom
        │       └── Telescope       controller only
        │           └── MidBoom     +X visual stage
        │               └── FlyBoom +X visual stage
        │                   ├── PlatformLevelCylinder
        │                   └── PlatformPivot
        │                       └── Platform
        ├── LiftCylinder
        ├── TowerLink
        └── TensionLink
```

`LiftCylinder`, `TowerLink`, `TensionLink`, both steer cylinders, the front tie
rod, and `PlatformLevelCylinder` use two-anchor visual solvers. Anchors follow the
verified parent relationships, but their coordinates, strokes, bores, pressures,
forces, and detailed service geometry remain reconstructed. The solvers are visual
kinematics only—not hydraulic physics, inverse-kinematics authority, fabrication,
diagnostic, or service claims.
