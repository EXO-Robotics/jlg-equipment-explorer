# 600S dimensional authority

Baseline source: R02 in `REFERENCES.md`, JLG part 3131050, revision R0626_04.

JLG labels all dimensions on the sheet as approximate. Here, **verified** means directly published by JLG for the current product sheet; it does not mean fabrication tolerance or metrology-grade accuracy.

## Verified published dimensions

| Property | Imperial | Metric as published | Modeling use |
|---|---:|---:|---|
| Platform width | 36 in | 0.91 m | platform outside envelope |
| Platform length | 96 in | 2.44 m | platform outside envelope |
| Machine width | 8 ft 2 in | 2.48 m | maximum stowed body/wheel envelope |
| Tailswing | 4 ft | 1.22 m | rear turntable extension beyond the 2.48 m drive-chassis envelope during swing |
| Machine height | 8 ft 2.4 in | 2.50 m | stowed maximum height |
| Machine length | 28 ft 7 in | 8.71 m | stowed end-to-end envelope |
| Wheelbase | 8 ft 2.7 in | 2.5 m | axle-center spacing |
| Ground clearance | 11.3 in | 0.29 m | minimum published clearance reference |
| Platform height | 59 ft 8 in | 18.18 m | maximum published platform height |
| Horizontal outreach | 50 ft 2 in | 15.29 m | maximum published horizontal outreach |

## Verified published performance values

| Property | Published value | Modeling/viewer implication |
|---|---:|---|
| Swing | 360 degrees continuous | turntable may rotate continuously in the visual study |
| Restricted platform capacity | 1,000 lb / 454 kg | label only with the restricted qualifier |
| Unrestricted platform capacity | 600 lb / 272 kg | primary unrestricted-capacity value |
| Platform rotator | 160 degrees hydraulic | future platform-pivot limit; not yet implemented |
| Axle oscillation | 8 in / 20 cm | visible mechanism reference; simulation deferred |
| Weight | 21,647 lb / 9,819 kg | informational only; configuration-dependent footnote applies |
| Standard tire designation | 14(IN355)X17.5(55D625), foam filled | tire proportion/detail reference |

## Blender scale

- Use meters.
- Use 1 Blender unit = 1 meter.
- Ground contact is Y = 0 after web export.
- Establish the first blockout from the 8.71 m stowed length, 2.48 m width, 2.50 m height, and 2.5 m published wheelbase.
- Constrain the rear turntable swing radius to 2.46 m as a derived blockout target: 1.24 m chassis half-width plus 1.22 m published tailswing.
- Resolve the 2.5 m rounded metric wheelbase against the 8 ft 2.7 in imperial value visually; do not invent extra precision in public copy.

## Derived values

Derived values are reproducible calculations from the R02 published dimensions. They are useful for blockout checks but are not additional manufacturer claims.

| Derivation | Value | Formula |
|---|---:|---|
| Width / stowed length | 0.285 | 2.48 / 8.71 |
| Stowed height / stowed length | 0.287 | 2.50 / 8.71 |
| Wheelbase / stowed length | 0.287 | 2.50 / 8.71 |
| Platform length / machine width | 0.984 | 2.44 / 2.48 |
| Ground clearance / machine height | 0.116 | 0.29 / 2.50 |

The current parts/service pages now support the assembly relationships below, but do not dimension them. The v1.0 model therefore records their implemented values as `reconstructed`, not as additional derived or manufacturer dimensions:

- turntable pivot offset from the axle centers
- counterweight radius and compound profile (bounded by published tailswing)
- main-boom hinge position
- main-boom and nested-section visible lengths
- platform-pivot offset
- lift-cylinder lower and upper anchor coordinates

## Visual approximations

These features may be reconstructed proportionally from same-generation imagery. They must not be presented as exact dimensions:

- engine-cover curvature and panel breaks
- counterweight curvature and taper
- axle-housing and undercarriage shapes
- boom cross-section corner radii
- railing tube placement and diameter
- control-box shape and mounting details
- tread-block layout
- lift-cylinder barrel/rod diameters
- pins, hoses, lamps, handles, steps, and fasteners

## Conflicts and exclusions

- Legacy manuals publish materially different stowed dimensions for earlier generations. They are not conflicts to average; they are different applicability sets.
- `1,000 lb` without the restricted qualifier is incomplete. Production copy must say `1,000 lb restricted` or present both capacity zones.
- The reach chart is acceptable for a visual, explicitly approximate overlay. It must never become an operational envelope, load chart, or safety reference.
