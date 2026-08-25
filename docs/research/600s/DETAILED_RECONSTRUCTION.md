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
front steering knuckles, fixed rear axle ends, steering cylinders/tie rod, fork pockets, tie-down
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
powertrack links, upper and lower tower links, hinge pins, boom sensors, cable/hydraulic bundles,
and an evidence-bounded lift cylinder.

Evidence: parts pages 520 and 540; service pages 641 and 648; operation nomenclature page 28.
The 0.90 m telescope travel is deliberately a presentation cap with 0.667 m of validated overlap
remaining at 100 percent. It is not a manufacturer-published stroke. Section lengths, pivot offsets,
anchor coordinates, and cylinder stroke remain reconstructed.

### Lift cylinder visual solver

The lower anchor follows the turntable and the upper anchor follows `MainBoom`. At runtime the
cylinder group is aligned between those anchors. The barrel stays fixed-length; the rod length and
rod-pin position solve to the changing anchor distance. This avoids the mechanically false behavior
of rigidly attaching the complete cylinder to the moving boom.

Evidence: parts page 734 and service page 648 establish the assembly relationship. The solver is
only a visual linkage and must not be used for service, fabrication, force, pressure, or stroke data.

### Platform and operator station

The platform uses the verified 0.91 × 2.44 m envelope and includes the rapid-replace support,
rotator, deck/toeboards, floor slats, orange posts and rails, swing gate and latch, control console,
toggle and joystick cues, emergency stop, footswitch, manual box, SkyGuard SkyLine, lanyard points,
capacity/warning label fields, rotator hoses, and platform harness cues.

Evidence: parts pages 568–620 and 654–680; service page 659; operation page 135. Platform leveling
is a presentation counter-rotation. Rotator construction, hose routing, rail tube dimensions, and
control placement are visually reconstructed unless explicitly identified by the published envelope.

### Visible hydraulic and electrical systems

The detailed release depicts steering hoses, chassis harness rails, a main valve bank, lift-cylinder
hoses, twin boom hydraulic bundles, rotator hoses, engine/ground-control harnesses, boom angle and
telescope sensors, upper boom cable, platform harness, and footswitch harness. They make system
relationships legible during inspection without pretending to reproduce a service schematic in 3D.

Evidence: parts pages 724–804 and 898–1054 plus service schematic pages 973–1018. Every route is
tagged reconstructed unless the publication verifies the visible assembly itself. No pressure,
voltage, pinout, fault-isolation, or diagnostic behavior is simulated.

## Current proof and remaining gap

The GLB validator enforces one rooted scene, 62 critical parent edges, 359 named nodes, five moving
hit volumes, identity export scale, configuration/provenance extras, published stowed dimensions,
platform size, wheelbase, clearance, tailswing, triangle budget, and telescope overlap. Safari proof
has covered real-GLB load, lift, extension, stow, platform leveling, mobile controls, and the component
inspector. The authored GLB contains 325 mesh records for traceable detail, then the viewer merges only
same-material geometry inside rigid motion groups. The observed v0.3 runtime contains 50 visible meshes,
while front steering, boom lift, telescope extension, platform leveling, lift-cylinder solving, and all
five hit volumes remain separate.

Remaining acceptance work is narrower: direct browser-console inspection, direct canvas ray-hit
coverage across all five hit volumes, keyboard/reduced-motion proof, performance tracing, improved
owned markings, restrained surface texture variation, and source-comparison captures. Those gates
must not be inferred from the mechanical validator.
