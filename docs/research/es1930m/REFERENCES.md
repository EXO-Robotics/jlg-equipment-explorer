# ES1930M source ledger

Freeze date: 2026-08-25
Target: `ES1930M-PVC2404-US-STD-FR-FLA130-NM`

This ledger records evidence for one North American, English-language, standard-production JLG ES1930M. It does not combine the optional integrated mid-rail deck, HVAC platform, ceiling-tile platform, alternate batteries, or other special-option branches with the standard machine.

## Authority classes

- `verified`: directly stated or unambiguously depicted by an applicable first-party source.
- `derived`: calculated from verified values with the method recorded.
- `reconstructed`: visually bounded but not dimensioned by the admitted evidence.
- `deferred`: unresolved or prohibited from driving geometry.

Manual illustrations establish topology and visible relationships. They are not scale drawings or fabrication dimensions.

## Primary sources

| ID | Source | Applicability | Local proof |
|---|---|---|---|
| R01 | [Current JLG ES1930M product page](https://www.jlg.com/en/equipment/scissor-lifts/micro-sized-series/es1930m) | Current product identity, standard-machine gallery and public headline specifications | Accessed 2026-08-25 |
| R02 | JLG specification 3131313, R0625_05 | Current specification linked from R01; dimensions, capacity, standard equipment and options | 2 pages; SHA-256 in `SOURCE_MANIFEST.json` |
| R03 | JLG parts 3122602400, PVC 2404, released 2026-03-30 | Current component identity, option branches and exploded relationships | 246 pages; SHA-256 frozen |
| R04 | JLG service 3122602300, PVC 2404, released 2026-07-15 | Current dimensions, cylinder specifications, mechanisms, routing and embedded schematics | 318 pages; SHA-256 frozen |
| R05 | JLG operation 3122602200, PVC 2404, released 2026-06-01 | Current controls, behavior, operating specifications and platform-extension boundary | 120 pages; SHA-256 frozen |

R03-R05 were obtained through JLG Online Express's public ES1930M catalog. Transient signed delivery URLs are not committed.

## Cross-PVC sources

| ID | Publication | Catalog PVC | Permitted use | Prohibited use |
|---|---:|---:|---|---|
| B01 | Hydraulic schematic 3122602600 | 1001 | Compare circuit identity and published cylinder/system values against R04 Figure 89 | No PVC 2404 geometry or configuration authority |
| B02 | Electrical schematic 3122602500 | 1001 | Compare harness identifiers and system topology against R04 Figure 90 | No PVC 2404 routing or option authority |

The current PVC 2404 service manual already embeds hydraulic and electrical schematics. B01 and B02 therefore remain corroborating comparison sources, not gap-filling primary sources.

## Page-level mechanical index

| System | Primary pages | Established facts |
|---|---|---|
| Overall dimensions and capacity | R02 pp. 1-2; R04 pp. 15-21; R05 pp. 89-91 | Standard envelope, platform, extension, weight, turning radius, capacity and cylinder specifications |
| Steering | R03 pp. 12-20, 112-113; R04 pp. 206-207, 229 | Two steering spindles joined by one double-rod hydraulic steer cylinder; drive motors/hubs are carried by the steer assemblies |
| Pothole protection | R03 pp. 22-23; R04 pp. 119-120 | Active linked protection bars and deployment state; exact runtime linkage coordinates remain reconstructed |
| Scissor stack | R03 pp. 68-71; R04 pp. 196-198, 201-202, 217-221 | Five numbered inboard/outboard arm levels, lower/upper slide blocks, fixed front pin branch, rear sliding branch, angle sensor, kicker arm, prop arm, pivot-pin families and cable guides. R04 p. 197 uses conflicting front/rear channel words; Figures 58, 59 and 62 plus the current raised side view control the presentation direction. |
| Lift cylinder | R03 pp. 70-71, 110-111; R04 pp. 21, 203-205, 230 | One cylinder, 685.5 mm stroke, single-acting pressure extension/gravity retraction, check/holding and manual-descent valves, kicker-arm relationship |
| Platform | R03 pp. 74-106; R04 pp. 199-202; R05 pp. 51-58 | Main platform, 21.6/21.7 in extension, rollers, fixed rails, self-closing gate, control station and extension-before-lower warning |
| Hydraulics | R03 pp. 116-119; R04 pp. 143-152, 309 | Powerpack, lift/steer circuits, pressure settings, hose relationships and current hydraulic schematic |
| Electrical and routing | R03 pp. 121-207; R04 pp. 158-165, 310-318 | Current harness identities, arm-stack routing constraints, control modules, platform cable and seven-sheet current schematic |

## First-party visual references

The reference-board inventory records two current standard-machine views and two explicitly excluded option configurations. The binaries stay under ignored `tmp/es1930m`; only URLs, hashes, identities and permitted uses are committed.

## Evidence gaps

- No admitted source publishes fabrication coordinates for scissor pivots, slide tracks, kicker-arm anchors or cylinder anchors.
- The current diagrams establish five arm levels and pin topology but are not scale drawings.
- No admitted source publishes a steer-angle curve or explicit Ackermann relationship. Zero inside turning radius is a performance envelope, not a license to invent steering angles.
- Hose and harness routes may be represented only at the relationship level established by R03/R04; undimensioned bends and clip positions remain reconstructed.
- Tire tread, door-shell radii, weld profiles, rail tube dimensions and many fastener locations are visually reconstructed unless separately cited.
