# 600S articulation authority

This file separates currently verified product motion from prototype-only controls.

## Verified current behavior

| System | Published evidence | Viewer status |
|---|---|---|
| Turntable swing | 360 degrees continuous (R01/R02) | implemented as a bounded demonstration slider; continuous-mode UI deferred |
| Main boom elevation | visibly shown through the R02 reach diagram | implemented visually; exact angular limits are not yet verified |
| Telescope extension | visibly shown through the R02 reach diagram | implemented as normalized 0-100% visual travel; physical stroke is not yet verified |
| Platform rotation | 160 degrees hydraulic (R02) | node contract prepared; control deferred |
| Steering | 2WS and 4WS turning radii published (R02) | front-wheel visual steering implemented; exact wheel angle and 4WS modes are not verified |
| Axle oscillation | 8 in / 20 cm (R01/R02) | not implemented |

## Current procedural-fixture limits

These are interaction-test values, not JLG operating data:

| Control | Fixture value | Authority status |
|---|---:|---|
| Boom slider | 0 to 72 degrees | visual approximation |
| Telescope slider | 0 to 100% mapped to 3.8 m proxy travel | visual approximation |
| Turntable slider | -180 to +180 degrees | UI representation of verified continuous swing, not a physical stop |
| Steering slider | -28 to +28 degrees | visual approximation |

The production UI must retain a visible `prototype motion limits` disclaimer until current manual evidence replaces the unverified values.

## Reach-envelope policy

- R02 contains separate 600 lb unrestricted and 1,000 lb restricted work zones.
- A future web overlay may be traced as an illustrative silhouette only.
- The overlay must be labeled approximate and non-operational.
- Do not expose load-placement advice, stability calculations, collision claims, or safe-working determinations.
- Do not extrapolate beyond the visible manufacturer chart.

## Manual questions to resolve before GLB integration

1. Current main-boom minimum and maximum elevation angles.
2. Current telescope physical stroke and nested-section rest position.
3. Platform-leveling relationship during boom elevation.
4. Platform-rotator center, neutral pose, and allowed direction split within the published 160 degrees.
5. Exact steering modes available on the modeled configuration.
6. Lift-cylinder base and rod-end anchor positions.
7. Whether current PVC 2601 schematics apply to the PVC 2607 machine.

## Animation hierarchy

```text
600S_ROOT
└── TurntablePivot          Y swing axis
    └── Turntable
        └── BoomPivot       Z lift axis
            ├── MainBoom
            │   └── Telescope       +X extension
            │       └── PlatformPivot
            │           └── Platform
            └── LiftCylinder
```

The cylinder may use a visual aim/scale solution; no hydraulic physics or inverse-kinematics claim is required.
