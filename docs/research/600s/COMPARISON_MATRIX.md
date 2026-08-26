# 600S current-generation visual comparison matrix

This matrix defines the source-comparison gate for the frozen configuration `600S-PVC2607-US-B3-2WS-D29-FF-RRP3696`. It does not redistribute JLG media and does not convert photographs, exploded views, or schematics into fabrication dimensions.

## Capture set

| Gate | Official source | Viewer pose | Required view | Compare | Current status |
|---|---|---|---|---|---|
| Elevated silhouette | JLG gallery asset `140381` | `?boom=72&extend=100&rotate=0` | clean side/elevated | orange/cream split, boom taper and nesting, platform scale, wheel/chassis mass, overall working silhouette | partial: hierarchy/color split/working pose read correctly; capped viewer extension is intentionally shorter than the published machine's full working reach |
| Working three-quarter | JLG gallery asset `139098` | `?boom=36&extend=70&rotate=-28` | rear three-quarter | counterweight depth, hood crown, boom-pivot relationship, platform orientation, running-gear stance | partial: current B3 massing and platform leveling agree broadly; enclosure curvature and undimensioned pivot/section proportions remain reconstructed |
| Chassis detail | JLG gallery asset `138896` | `?focus=chassis&rotate=-22&steer=12` | close rear three-quarter | B3 covers, grille, 355/55D625 tire value, tread rhythm, rim/hub/lugs, axle and lower-deck cues | partial: four-wheel stance, hood/counterweight split, grille, hubs/lugs and tread are present; tire chevron, molded cover curvature, exact decal fields and axle detail remain simplified |
| Stowed envelope | current specification `3131050` revision `R0626_04` plus current gallery | default pose | side and three-quarter | 8.71 × 2.48 × 2.50 m outer envelope, 2.50 m wheelbase, 0.29 m frame clearance, 1.22 m tailswing, 0.91 × 2.44 m platform | mechanical pass and fresh Safari baseline review; paired fixed-camera overlay remains pending |

The query poses are presentation controls, not manufacturer operating positions. Asset `140381` is suitable for silhouette comparison but does not dimension the mechanism. Assets `139098` and `138896` are suitable for visible proportion and assembly comparison only.

## Section criteria

| Section | Pass criteria | Authority boundary |
|---|---|---|
| Chassis | correct four-wheel stance; front-only visual steer; believable axle, hub, lug, tread, fork-pocket, step, tie-down, and belly-pan relationships | wheelbase and clearance are published; undimensioned offsets and fastener geometry are reconstructed |
| Turntable | B3 twin-cover/counterweight silhouette; rear grille; cover seams/latches; ground-control, tank, valve, and harness cues read at showcase distance | tailswing is published; enclosure curvature, internal packaging, valve spacing, and routes are reconstructed |
| Boom | base/mid/fly nesting remains legible; tower links, pivot pin, cylinder, powertrack, wear collars, bundles, and sensors move with the correct parent groups | boom angles, section lengths, anchor coordinates, and 0.90 m viewer travel are visual values |
| Platform | verified 36 × 96 envelope; orange rails, swing gate, console, footswitch, SkyGuard, lanyard points, rotator support, hose/harness cues, and toeboards are visible | envelope is published; detailed construction and control placement are reconstructed |
| Materials and markings | orange powder coat, cream boom sections, dark steel/rubber, zinc/metal cues, subtle part-to-part roughness, and readable model/product marks support recognition | runtime marks are independently typeset nominative identifiers, not copied JLG artwork or manufacturer endorsement |

## Acceptance method

1. Open each official asset directly from the recorded JLG source in `REFERENCES.md`; do not commit the source image.
2. Capture the viewer at a fixed viewport and the corresponding query pose.
3. Record only visible agreement or disagreement. Do not infer hidden dimensions from perspective.
4. Classify each issue as `verified envelope drift`, `derived geometry drift`, `reconstructed visual drift`, or `source/configuration ambiguity`.
5. Accept the visual gate only when stowed and working poses have been reviewed at desktop and 390 × 844 mobile size and discrepancies are either corrected or explicitly deferred.

## Fresh v1.0 review notes — 2026-08-25

- Official assets `140381`, `139098`, and `138896` were re-opened from the recorded JLG DAM URLs and compared against the live Safari v1.0 stowed and working poses.
- Strongest agreement: recognizable current orange/cream/dark material split; B3 hood/counterweight massing; three-section boom read; underside powertrack; four-wheel stance; orange rapid platform; model/product marking locations.
- Most important remaining visual gaps: the viewer's evidence-safe 0.90 m telescope cap cannot reproduce full outreach; the official molded covers are smoother and more compound-curved; the current tire chevron and sidewall are richer; the boom head/pivot package, exact label fields, and hose loops remain simplified.
- The v1.0 additions improve recognition without crossing authority boundaries: independently typeset nominative marks, a generic independently authored hazard-band cue, restrained per-part finish variation, and visible moving hit-volume outlines.

The receipt may record showcase runtime acceptance when its mechanical and browser gates pass, but
it does not establish factory-exact visual equivalence. Fixed-camera paired overlays and a
manufacturer-authoritative full-reach reconstruction remain open evidence gates.

## v1.1 mechanism-authority pass — 2026-08-25

- Corrected the current telescope identity to cylinder `1001309294` and rejected
  legacy cylinder `1683618` dimensions as current-PVC geometry authority.
- Replaced one rigid telescope translation with separate MidBoom and FlyBoom
  visual transforms while retaining a clearly labeled 0.90 m presentation cap.
- Replaced static tower-link, steering-cylinder, and tie-rod dressing with moving
  two-anchor visual linkages; added a visible platform-level cylinder.
- Rebuilt the powertrack as static, moving, bend, support, and push-tube groups.
  The displayed link sampling is deliberately not labeled as the physical count.
- Corrected the current official gallery color read to cream base/mid sections and
  an orange fly section, boom head, rotator/support area, and platform.
- Separated hydraulic hose, electrical loom, power/control cable, telescope wire
  rope, and carrier materials so system identity is no longer hidden by one black
  hydraulic material.

Fresh local desktop proof loaded GLB hash prefix `d480ff121514`, exercised lift,
coupled extension, swing, and steering together, passed five of five selection
volume self-tests, and recorded zero runtime errors. This is runtime proof, not a
fixed-camera dimensional overlay or mobile acceptance.

Runtime 1.1.2 then directly selected all five named hit volumes from the default
camera. The chassis volume was shortened below the turntable deck and nested
platform/telescope/boom volumes receive deterministic semantic priority, removing
the earlier turntable-click interception without coupling selection to render meshes.

Runtime 1.1.3 corrects the detached-chassis artifacts visible in the prior base close-up.
Four shiny cylindrical tie-down placeholders are now flush dark rail pockets; the side
steps overlap the lower deck and have visible supports; and the boom-rest saddle/pad is
carried by two chassis-mounted posts so it remains connected when the boom lifts. Exact
GLB `cce862032f8d` passed fifteen attachment-overlap checks plus the existing mechanical,
motion, selection, stowed, and working-pose desktop gates. Mobile remains a separate gate
for this exact asset hash.

Runtime 1.1.4 corrects the visibly disconnected underside carrier samples. Exact GLB
`4dd98f412238` limits neighboring display seams to 0.002 m and proves zero positive
gap between the fixed and moving sampled runs at full visual extension. Desktop
stowed, 20-degree raised-boom, and 35-degree/full-extension views passed with the
real GLB, five selection volumes, and zero runtime errors. The displayed pitch and
sample counts remain explicitly non-authoritative because current PVC 2607 sources
establish carrier topology but not the exact frozen-machine link dimensions/count.
