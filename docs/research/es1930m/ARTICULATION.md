# ES1930M articulation evidence and solver contract

## Verified topology

PVC 2404 parts Figure 3-1 and service Figures 72-74 establish a five-level scissor stack. The service procedure identifies ten numbered arm groups, removed top-down and installed bottom-up:

1. outboard 1 and inboard 1;
2. outboard 2/4 and inboard 2;
3. outboard 3 and inboard 3;
4. outboard 2/4 and inboard 4;
5. outboard 5 and inboard 5.

The stack also contains lower slide blocks, upper platform slide blocks, four pivot-pin families, a separate kicker arm, prop arm, arm-angle sensor, cable guides, and one lift cylinder. Parts installation `1001333761`, arm kit `1001324232`, lift cylinder `1001322163`, and kicker arm `1001322659` bind these relationships to the current PVC 2404 source.

## Required authored pivot graph

Each arm mesh must reference explicit transform nodes; mesh origins are not kinematic authority. The eventual GLB contract must include:

```text
ES1930M_ROOT
|- Chassis
|  |- FrontSteerAssembly
|  |- RearWheelAssembly
|  |- PotholeProtection
|  |- BatteryCompartments
|  `- GroundControls
|- ScissorAssembly
|  |- Level01
|  |- Level02
|  |- Level03
|  |- Level04
|  |- Level05
|  |- KickerArm
|  `- ArmAngleSensor
|- LiftCylinder
`- PlatformAssembly
   |- MainDeck
   |- ExtensionDeck
   |- FixedRails
   |- SelfClosingGate
   `- PlatformControls
```

For each level and both visible planes, author lower, center and upper pivot markers. Shared joints must resolve to one world-space point even when represented by markers under different link transforms. Lower and upper slide blocks must be explicit nodes constrained to authored track axes.

## Lift solver

The normalized presentation input `lift` selects one continuous branch between the stowed and elevated authored states. It must not independently keyframe arm rotations.

The solver is constraint driven:

1. choose the target platform vertical position from the evidence-bounded presentation range;
2. solve the authored five-level linkage branch for its link angles and slide positions;
3. apply arm transforms around explicit pivot markers;
4. derive platform position from the upper constraints while keeping platform pitch and roll at zero;
5. solve the kicker arm and lift-cylinder endpoints from the resulting pivot state;
6. update routed display cables/hoses only after the rigid mechanism closes.

The familiar ideal relation `h = sum(L_i * sin(theta_i))` is a diagnostic intuition, not the machine contract. Unequal authored pivot offsets, slide tracks and the kicker mechanism mean the runtime must solve its actual pivot graph.

## Lift-cylinder boundary

R04 establishes a 685.5 mm single-acting cylinder that extends hydraulically and retracts under gravity. It connects through lower and upper pivot pins to the scissor/kicker mechanism and includes a holding/check valve plus manual-descent valve. Exact anchor coordinates and leverage are not published and remain reconstructed.

### Frozen connected reconstruction H1

PVC 2404 service pp. 196-198 establishes a rear frame pivot and a lateral pair of lower slide blocks in the front channel. Pages 201-202 establish one platform pin pair and one upper-slide-block pair; their matching rear-fixed/front-track assignment is reconstructed because the procedure does not name the ends. Pages 203-205 and 217-221 establish a lower cylinder pin, upper cylinder pin, kicker pivot and separate kicker roller pin.

The browser therefore keeps the rear boundary fixed, places both lower blocks at the one front-track coordinate, and derives every boundary from a single five-level pantograph state. The cylinder upper pin and the three-point kicker presentation are derived from Level01; cylinder pin distance emerges from that posed graph. H1 attachment fractions are calibrated only so the endpoint distance change falls within the published 685.5 +/- 1.5 mm stroke. They are visual reconstruction coordinates, not JLG fabrication data or a claimed factory leverage curve.

The viewer may reproduce the physical relationship and measured cylinder stroke but must not simulate pressure, stability, load sensing, failure, manual descent, or safe operating behavior.

## Extension deck

The frozen standard platform uses a foot-actuated extension with published 0.55 m travel. Parts Figure 4-3 establishes two front rollers, two rear rollers, bumpers, pads, supports, spring/rod/bracket and platform-extension weldment `1001324255`. The extension deck translates relative to the main platform. Rails and gate must follow their actual attachment branch rather than being globally translated without evidence.

R05 warns that the platform extension must be completely retracted before lowering. The showcase should expose this as product context, not enforce or advertise a safety simulation.

## Steering

PVC 2404 parts/service evidence shows a single double-rod steer cylinder joining two steering lugs on left and right spindles. The drive motor/hub assemblies ride with those steer spindles. This is not a same-angle visual wheel rotation.

The future steering solver must use the authored cylinder/spindle pivot graph and preserve the published 80 mm per-direction cylinder stroke. Zero inside turning radius and 1.40 m outside radius are envelope checks. No Ackermann curve, maximum wheel angle or tie-rod geometry may be invented.

## Sampled validator

At lift values 0.00 through 1.00 in 0.01 increments, require:

- every authored arm-link length remains invariant;
- every shared pivot closes within the declared meter epsilon;
- corresponding left/right planes remain mirror symmetric;
- slide blocks remain on their authored track axes and within reconstructed bounds;
- platform pitch and roll remain within the visual-level tolerance;
- cylinder pin distance remains compatible with its 685.5 mm stroke envelope;
- the solver remains on one continuous branch with no link inversion;
- transform deltas remain below the continuity threshold;
- the declared broad-phase collision proxies do not report non-adjacent arm crossing, arm-body intrusion through the platform underside outside the intended upper-pin neighborhood, escape beyond the published machine-width/length envelope, or loss of lateral clearance between the center cylinder and either scissor plane.

These checks validate the authored reconstruction. They do not establish real-machine structural, stability or safety performance.

The collision pass is deliberately a centerline/section proxy rather than a triangle-level mesh collision test. Same-level arm crossings and adjacent-level shared endpoints are required parts of the pantograph and are excluded. The upper 30 percent of each top link is also excluded from the deck-underside proxy because the links terminate in the platform slide/pin structure. Chassis-to-link clearance is bounded by the authored lower-pivot height and exported stowed-pose GLB envelope, not asserted as measured JLG clearance. The proxy dimensions in `mechanism.json` are reconstruction values and must never be cited as factory dimensions.

## Frozen reconstructed branch

`machines/es1930m/mechanism.json` freezes the first implementation branch. It uses five equal reconstructed 1.11 m pin-center links per vertical chain, a 0.30 m lower-pivot height, and a 0.10 m upper-pivot-to-deck offset. These values close at the published 0.90 m reconstructed stowed deck height and the verified 5.64 m indoor deck height without exceeding link length. They are implementation coordinates, not JLG dimensions.

The cylinder installation is likewise a circle-intersection reconstruction: its fixed lower pin, kicker pivot, and kicker-pin radius are authored coordinates, while the change in cylinder pin distance is constrained to the published 0.6855 m stroke. This preserves a mechanically continuous relationship without claiming that the chosen leverage geometry is a measured factory installation.

`scripts/validate_es1930m_kinematics.py` samples 101 lift states, checks both crossing links in every level, shared-center closure, mirror symmetry, branch monotonicity, transform continuity, exact presentation-cylinder stroke, and 4,141 collision/envelope proxy assertions. `scripts/validate_es1930m_glb.py` separately checks the exported node hierarchy, explicit marker/link counts, asset envelope, interaction volumes, and hash-bound runtime contract. The analytic solver check and exported-asset check remain separate evidence; neither is a substitute for physical-machine validation.
