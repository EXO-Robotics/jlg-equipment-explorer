# 742 local review evidence

This directory is intentionally pending during the fourth-wave mechanical and
runtime repair. `review-manifest.json` does not pass a human gate until the final
candidate is committed, every required observation is repeated, and the binder
semantically validates the captured evidence against that exact commit and
candidate-tree digest.

The eight allowlisted Blender PNGs represent eight distinct views: stowed, cab
close-up, maximum lift, maximum-lift fork close-up, maximum reach,
retract-chain cutaway, rigid steering-linkage cutaway, and boom-angle-sensor
close-up. The extended visual gate uses six of those views—both maximum-lift
views, maximum reach, retract-chain cutaway, steering cutaway, and sensor
close-up. Stowed and cab close-up remain separate gates. Each render is
independently authored and bound
by exact path, SHA-256, byte count, and PNG dimensions in
`OWNED_RENDER_ALLOWLIST.json`.

Browser proof uses a separate `BROWSER_CAPTURE_ALLOWLIST.json`. It admits only
fresh local browser screenshots and JSON automation traces by exact path, hash,
size, kind, MIME type, dimensions, and provenance. It does not weaken the
manufacturer-binary hash rejection or reuse the Blender-render provenance
contract.

`CAPTURE_REQUIREMENTS.json` is the recapture checklist. Completed schema-2 gate
records must contain:

- exact browser version, user agent, OS version/build, and actually observable
  WebGL GPU metadata (or an explicit unavailable reason);
- DOM snapshots, browser accessibility-tree snapshots where applicable,
  ordered interaction transcripts, exact screenshots, and an automation trace;
- at least 180 raw visible-tab frame intervals at desktop, portrait, and short
  landscape, with p95 and worst values recomputed from those arrays;
- independent expected semantic-selection winners for all 15 component pairs,
  compared with 15 separately observed winners;
- interaction, responsive layout, modal keyboard/focus, drag, pinch, and
  reduced-motion regression checks for the exact current 600S release and exact
  ES1930M 1.0.4 release.

The local performance gate is deliberately bounded: each identified local
browser profile must have at least 180 raw samples, p95 no greater than 50 ms,
and zero visible intervals at or above 250 ms. The evidence must report the
actual recomputed values, browser/OS identity, and observable WebGL GPU
metadata. This threshold applies only to the captured local browser and is not
a promise about physical or low-end mobile GPUs.

The accessibility gate covers DOM semantics, the Chromium accessibility tree,
keyboard focus containment, Escape restoration, slider value text, and reduced
motion. It does not claim a VoiceOver, NVDA, physical assistive-technology, or
physical-device session. No review artifact claims deployment, operational,
load, stability, service, safety, or manufacturer-equivalence proof.
