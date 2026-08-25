# 600S detailed reconstruction breakdown

## Frozen target

This asset represents one configuration, not a generic mixture of 600S variants:

- Configuration: `600S-PVC2607-US-B3-2WS-D29-FF-RRP3696`
- Product vintage: current PVC 2607, June/July 2026 evidence set
- Market and serial family: ANSI US, B3 branch
- Running gear: four-wheel hydrostatic drive, two-wheel front steer
- Engine: Deutz D2.9 Tier 4 Final, 49 hp selection
- Tires: standard 355/55D625 foam-filled selection
- Platform: B3 rapid-replace 36 × 96 swing-gate assembly
- Options: none intentionally authored

The identifier freezes a reproducible parts/manual branch; it is not an invented exact serial number.

## Section-by-section implementation

### Chassis and running gear

Current nodes cover the frame and belly pan, front and rear axle housings, differential forms,
front steering knuckles, fixed rear axle ends, two steer-cylinder visual solvers, a moving tie-rod
solver, fork pockets, tie-down
points, boom rest, side steps, and four driven wheel assemblies. Each wheel contains a foam-filled
tire form, 18 tread blocks, off-white rim, drive hub, and nine visible lug fasteners.

Evidence: parts publication 3122579800 pages 20–64 and the current specification envelope.
The 2.50 m wheelbase and 0.29 m lower-frame clearance are mechanically validated. Undimensioned
axle, knuckle, tread, and fork-pocket forms are visual reconstructions.

### Turntable and B3 exterior

Current nodes cover the slew ring, upper frame, B3 engine and tank hoods, seams and latches,
counterweight, rear cooling grille, engine tray, fuel and hydraulic tanks/fill caps, main valve
bank and coils, ground controls, service-label fields, electrical module, and amber beacon.

Evidence: parts publication 3122579800 pages 70–242 and the current specification. The 1.22 m
published tailswing is enforced through the modeled counterweight envelope. Internal packaging,
valve spacing, label content, and harness routes are not service measurements.

### Boom, telescope, and elevation linkage

The hierarchy is `BoomPivot → MainBoom → Telescope → MidBoom → FlyBoom → PlatformPivot`.
Visible detail includes the base/mid/fly shells, wear-pad collars, service ports, boom head,
powertrack base/moving/bend groups, push tube and support, distinct tower and tension links, hinge
pins, boom sensors, telescope cylinder/rope/sheave cues, cable/hydraulic bundles, and an
evidence-bounded lift cylinder.

Evidence: parts pages 520 and 540; service pages 641 and 648; operation nomenclature page 28.
The 0.90 m telescope control is deliberately split into 0.36 m MidBoom and 0.54 m FlyBoom
visual transforms. Mechanical validation retains 1.207 m as the smaller section overlap at 100
percent. Neither the total nor the split is a manufacturer-published stroke or factory ratio.
Section lengths, pivot offsets, anchor coordinates, rope paths, and cylinder stroke remain
reconstructed.

### Lift cylinder visual solver

The lower anchor follows the turntable and the upper anchor follows `MainBoom`. At runtime the
cylinder group is aligned between those anchors. The barrel stays fixed-length; the rod length and
rod-pin position solve to the changing anchor distance. This avoids the mechanically false behavior
of rigidly attaching the complete cylinder to the moving boom.

Evidence: parts page 734 and service page 648 establish the assembly relationship. The solver is
only a visual linkage and must not be used for service, fabrication, force, pressure, or stroke data.

The tower link, tension link, both steering cylinders, front tie rod, and platform-level cylinder
use the same evidence-bounded two-anchor principle. The manuals establish their topology; the
exported anchor coordinates remain reconstructed.

### Platform and operator station

The platform uses the verified 0.91 × 2.44 m envelope and includes the rapid-replace support,
rotator, deck/toeboards, floor slats, orange posts and rails, swing gate and latch, control console,
toggle and joystick cues, emergency stop, footswitch, manual box, SkyGuard SkyLine, lanyard points,
capacity/warning label fields, rotator hoses, and platform harness cues.

Evidence: parts pages 568–620 and 654–680; service page 659; operation page 135. Platform leveling
retains the operator-set starting angle while a visible leveling-cylinder cue follows the rotator
pin. This follows the current service description and is not automatic leveling to gravity.
Rotator dimensions, hose routing, rail tube dimensions, and control placement are visually
reconstructed unless explicitly identified by the published envelope.

### Visible hydraulic and electrical systems

The detailed release depicts steering hoses, chassis harness rails, a main valve bank, lift-cylinder
hoses, twin boom hydraulic bundles, rotator hoses, engine/ground-control harnesses, boom angle and
telescope sensors, upper boom cable, platform harness, and footswitch harness. They make system
relationships legible during inspection without pretending to reproduce a service schematic in 3D.
Hydraulic hose, electrical loom, boom power/control cable, telescope wire rope, and powertrack
carrier have separate material identities.

Evidence: parts pages 724–804 and 898–1054 plus service schematic pages 973–1018. Every route is
tagged reconstructed unless the publication verifies the visible assembly itself. No pressure,
voltage, pinout, fault-isolation, or diagnostic behavior is simulated.

## Current proof and remaining gap

The GLB validator enforces one rooted scene, 100 critical parent edges, 400 named nodes, five moving
hit volumes, identity export scale, configuration/provenance extras, published stowed dimensions,
platform size, wheelbase, clearance, tailswing, triangle budget, and telescope overlap. Safari proof
has covered real-GLB load, lift, extension, stow, platform leveling, mobile controls, and the component
inspector. The authored GLB contains 345 mesh records for traceable detail, then the viewer merges only
same-material geometry inside rigid motion groups. The observed v1.1 runtime contains 80 visible meshes
(including independently authored model/product marks and generic hazard-band cues),
while front steering, boom lift, telescope extension, platform leveling, lift-cylinder solving, and all
five hit volumes remain separate.

Fresh local runtime 1.1.2 evidence covers real-GLB load, all four simultaneous motion controls,
uncaught runtime-error instrumentation at zero, five-of-five individual ray-hit self-tests, direct
canvas selection of all five named volumes, 60 fps with an 18.3 ms p95 frame sample on the tested
desktop, and the moving platform-level/powertrack view. Fresh Safari proof covers the exact 390 × 844
layout with collapsed controls, the real v1.1 GLB, 30 fps mobile pacing, and zero instrumented errors.
Earlier v1.0 Safari evidence remains the latest keyboard-focus and reduced-motion interaction proof.
Independently typeset product/model marks,
a generic independently authored hazard-band cue, and restrained per-part powder-coat/boom/deck
finishes are runtime presentation assets rather than copied manufacturer artwork.

Remaining acceptance work is narrower: a captured Chrome performance trace and fixed-camera paired
source overlays. The source comparison also confirms that the 0.90 m evidence-safe telescope cap cannot
represent the real machine's full outreach. Those gaps must not be inferred away from the mechanical
validator or the runtime diagnostic self-test.
