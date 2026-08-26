# ES1930M visual comparison record

Review date: 2026-08-25
Frozen configuration: `ES1930M-PVC2404-US-STD-FR-FLA130-NM`

## Evidence and method

The visual authority is limited to JLG assets V01 (stowed three-quarter) and V02 (raised side), supported by the PVC 2404 parts/service illustrations. Manufacturer binaries remain in ignored local research storage and are identified by hash in `reference-board/README.md`; they are not redistributed.

Four deterministic stowed review renders are produced from the frozen `.blend` by `scripts/render_es1930m_preview.py`. The browser runtime was separately reviewed at stowed, intermediate, outdoor-height, and full indoor-height states because the source blend stores the neutral/stowed authored pose.

| Authored view | Local review-render SHA-256 | First-party coverage | Result |
|---|---|---|---|
| front-right | `156b728ce6546ff34f8751ff0b3fc2c886506dc3eca07550a346d58b49e233e3` | partial V01 | accepted for envelope and component placement |
| front-left | `680e50b6318722137c6e379184b3a5b746406d8a5bb9a3e447c89542300ce7ec` | no exact matching JLG view | reconstruction-only blind side |
| rear-right | `788f0b960251c89035780ac81e03acc159643be41e620fbc51e1651b63e9d319` | partial V01 | accepted for envelope; fine detail simplified |
| rear-left | `b9a2b77bb49ed9c10a28216e5c5ec2eef6dcf99fe34be8b128b4c8555c6a439e` | closest to V01 | accepted for stowed silhouette |
| raised side-right | browser runtime, not a committed bitmap | V02 | five-level topology, level platform and height behavior accepted |

The render hashes identify one local review run, not release artifacts. Regeneration may change pixels across Blender versions; the reproducible authority is the hash-bound `.blend`, script, GLB, mechanism contract, and receipt.

## Confirmed visual relationships

- compact rectangular chassis and narrow overall stance;
- five packed scissor levels with two lateral planes;
- fixed-rail standard platform, entry gate, main deck and extension-deck separation;
- platform control box, ground-control area, compartment doors, four-wheel layout and pothole-protection members;
- tan scissor members, orange platform/rails, dark chassis and nonmarking tire presentation;
- PVC 2404 Figure 8-7 model badges on both long platform toe boards, JLG identity marks on both platform end boards, and JLG door marks on both chassis access panels; all marks are independently typeset rather than copied decal artwork;
- raised platform remains level while link span contracts continuously.

## Known visual deviations and authority limits

- The authored equal-link pantograph is a closure-preserving reconstruction. JLG imagery shows more varied arm profiles, gussets, pin bosses and stacked offsets than this presentation asset.
- Chassis shells, door seams, wheel hubs/tread, welds, fasteners, non-brand safety labels, hoses and wiring are simplified. Brand/model placement is now bound to PVC 2404 Parts Figure 8-7 and the standard-machine gallery, but the typography, backing shapes and exact dimensions remain an owned visual approximation and must not be used as decal or service authority.
- Platform rails are square-profile presentation geometry and do not claim measured tube section, weld geometry or exact gate hardware.
- The lift-cylinder/kicker installation follows verified topology and published cylinder stroke, but its anchor coordinates and leverage are reconstructed.
- Blind-side compartment interiors lack enough first-party photography for photogrammetric acceptance. Their system identity is sourced from manuals; their exact spatial placement is not.
- Steering spindle angles are deliberately held neutral. Only the published 80 mm-per-direction actuator presentation is active until a PVC 2404 spindle/link graph supports a defensible wheel-angle curve.

## Acceptance boundary

This review accepts the asset as a technically sourced interactive reconstruction at the same evidence standard as the showcase: configuration, topology, published envelopes, component identity, independent transforms, and provenance are explicit. It does not accept the model as a dimensionally exact digital twin, service model, training simulator, fabrication reference, or safety analysis.
