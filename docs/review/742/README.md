# 742 local review evidence

This directory is prepared for the final Wave 7 candidate review.
`review-manifest.json` does not pass a human gate until the pending candidate is
committed, every required observation is repeated, and the binder semantically
validates the captured evidence against that exact commit and candidate-tree
digest.

The twelve allowlisted Blender PNGs represent twelve distinct views: stowed,
cab close-up, maximum lift, maximum-lift fork close-up, maximum reach,
retract-chain cutaway, front steering-linkage cutaway, rear steering-linkage
cutaway, circle-steering plan, crab-steering plan, source-correct front steering
plan, and boom-angle-sensor close-up. The schema-2 extended visual gate uses all
ten mechanism-specific views. Each view has one required semantic ID and exact
pixel-literal claim. The steering records identify visible through-rods, rigid
tie bars, and highlighted pivots; distinguish front, rear, circle, and crab
states; preserve every visibly printed reconstructed wheel heading and
toe/scrub diagnostic; and require the front plan's `REAR HELD ALIGNED` guidance.
An ICR construction may be claimed only for the front and circle renders where
construction lines are visibly drawn. The superseded
`front-steering-limited-plan.png` is forbidden by path. Each observation
embeds its distinct allowlisted artifact's exact path, SHA-256, and byte count;
an allowlist count or an unreferenced render cannot satisfy the gate. Stowed and
cab close-up remain separate gates. Every render is independently authored and
also bound by exact path, SHA-256, byte count, and PNG dimensions in
`OWNED_RENDER_ALLOWLIST.json`.

The committed `extended-visual-fidelity.json` is a pending template: candidate
tree and reviewed commit are `PENDING`, captured OS is null, and every
observation is false. It becomes passing evidence only after the mechanical and
runtime freeze, a reviewer confirms every named claim against the pixels, and
the binder supplies the exact candidate and environment identities.

Browser proof uses a separate `BROWSER_CAPTURE_ALLOWLIST.json`. The pending
candidate commits an empty allowlist, and the allowlist is deliberately excluded
from the candidate-tree digest and reviewed-commit path set because it is
populated only after capture against that immutable candidate. A completed
human-review binding records the populated allowlist's exact path, SHA-256, and
byte count. Every admitted screenshot and trace must also be referenced and
semantically validated by exactly one of the completed browser gate artifacts.
The allowlist admits only fresh local browser screenshots and JSON automation
traces by exact path, hash, size, kind, MIME type, dimensions, and provenance.
It does not weaken the manufacturer-binary hash rejection or reuse the
Blender-render provenance contract.

The authoritative recapture uses the exact Playwright 1.62.1 dependency in
`package-lock.json` and its bundled Chromium revision 1234. Run `npm ci`,
`npm run capture:742:install`, and then `npm run capture:742 -- --port=8092`.
Completed evidence records the exact lockfile identity plus browser executable
revision, version, basename, SHA-256, and byte count, plus a canonical manifest
and root digest over the full Chromium application/resource bundle in every
gate and trace.
Absolute module/browser overrides remain available for rehearsal, but the
review validator rejects override-backed output as final evidence.

`CAPTURE_REQUIREMENTS.json` is the recapture checklist. Completed schema-2 gate
records must contain:

- exact browser version, user agent, OS version/build, and actually observable
  WebGL GPU metadata (or an explicit unavailable reason);
- DOM snapshots, full unignored browser accessibility-tree snapshots where
  applicable, exact engineering-unit text reconciled through raw AX details
  relationships, status/live-region nodes, structured assertion outcomes,
  exact screenshots, and a hash-bound automation trace produced by the
  committed capture runner;
- at least 180 raw visible-tab frame intervals at desktop, portrait, and short
  landscape, with p95 and worst values recomputed from those arrays and the
  same captured-window metrics rendered visibly in its screenshot;
- independent expected semantic-selection winners for all 15 component pairs,
  compared with 15 separately observed winners, five fixed policy fixtures,
  and six direct visible-canvas component selections;
- interaction, responsive layout, modal keyboard/focus, drag, pinch, and
  reduced-motion regression checks for the exact current 600S release and exact
  ES1930M runtime release 1.0.8 (with its separately receipted 1.0.4 asset).

The local performance gate is deliberately bounded: each identified local
browser profile must have at least 180 raw samples, p95 no greater than 50 ms,
and zero visible intervals at or above 250 ms. The evidence must report the
actual recomputed values, browser/OS identity, and observable WebGL GPU
metadata. This threshold applies only to the captured local browser and is not
a promise about physical or low-end mobile GPUs.

The accessibility gate covers DOM semantics, the Chromium accessibility tree,
keyboard focus containment, Escape restoration, exact unit-bearing slider
engineering text exposed through AX details, status/live regions, and live
reduced-motion transitions. Fatal-path evidence records changing RAF baselines
and frozen terminal counters. It does not claim a VoiceOver, NVDA, physical
assistive-technology, or physical-device session. No review artifact claims
deployment, operational, load, stability, service, safety, or
manufacturer-equivalence proof.
