# Source reconciliation

The freeze deliberately uses one matched manual family: PVC 2411. JLG indexes a newer PVC 2605 operation publication, but a matching 2605 service/parts/schematic family was not present at freeze time. Mixing it with PVC 2411 would weaken applicability.

The current specification and brochure are the authority for published dimensions, capacities, engine identity, steering modes, standard tire, and available attachments. PVC 2411 parts/service/operation publications establish topology, named systems, and the open-cab branch. Gallery assets establish visible current-product shape and finish. BIM files are visual-reference-only because they are monolithic, high-density manufacturer geometry and do not expose a trustworthy articulated hierarchy.

Conflicts and boundaries:

- The specification says 72 hp; parts group labels use 74HP. UI uses the current specification value. Parts labels are not converted into a performance claim.
- Standard carriage widths include 50, 60, and 72 in. The frozen reconstruction chooses the first standard 50 in carriage and does not present alternatives as simultaneously installed.
- The hydraulic schematic establishes evidence-derived cylinder sizes/strokes: lift 150/90/1070 mm, telescope 85/65/3604 mm, head tilt 120/60/388 mm, compensation 120/60/278 mm, frame sway 120/55/168 mm, and rear-axle stabilization 120/55/200 mm. The owned endpoint rigs reconcile closely to every stroke except RAS: only 0.1056 m of its 0.200 m stroke is used because the explorer does not simulate the free/slow/locked stabilization states.
- The service publication establishes a 55-degree steering limit. Inner/outer wheel curves are still independently computed from the 3.42 m published wheelbase and 2.1005 m temporary-reference track; they are not a factory steering calibration.
- The temporary BIM cross-pose solve suggests a boom pivot near `(-2.158, 1.838, 0)` in the owned coordinate frame. That coordinate informs the silhouette and height reconciliation only; no BIM geometry is present in the source or export, and the owned 69-degree endpoint remains governed by the published load-chart axis.
- Parts/service topology places the retract chain bottom-front inside the first section, extend chains along the underside/interior of the second section, and auxiliary lines inside/under the boom. The owned cues follow that topology, while exact anchors, bends, chain pitch, and sheave diameters remain reconstructed.
- The published 2.46 m width is enforced on the base-machine geometry excluding mirrors. The owned left mirror produces an approximately 2.58 m overall visual envelope, which is reported separately rather than folded into the published width.
- The specification's 8.86 m maximum forward reach and 12.8 m maximum lift height are tested as distinct poses. The reach gate uses a 3-degree/full-extension state and a 24 in load center; the height gate uses 69 degrees with level forks. Neither pose carries a load/capacity claim.
- Downward carriage tilt is limited to 5 degrees in the presentation so the fork geometry retains flat-floor clearance even at the displayed frame-level extremes. This is a visual collision boundary, not an inferred machine interlock.
- Frame leveling rotates around an independently reconstructed longitudinal axis at 0.82 m visual height rather than the ground origin. JLG publishes the function and 10-degree limit; the implementation does not label that coordinate as an axle centerline.
- Manual diagrams are not treated as scale drawings.
- Official imagery and BIM geometry are not redistributed.
